#!/usr/bin/env swift

import AppKit
import AVFoundation
import Foundation
import Vision

struct Config {
    var intervalSeconds: Double = 5.0
    var outputPath: String = "\(NSHomeDirectory())/.openclaw-expression-monitor/latest.json"
    var historyPath: String = "\(NSHomeDirectory())/.openclaw-expression-monitor/history.jsonl"
    var frameOutputPath: String = "\(NSHomeDirectory())/.openclaw-expression-monitor/latest.jpg"
    var maxSamples: Int?
    var quiet: Bool = false
}

struct ExpressionMetrics: Encodable {
    let mouthOpenRatio: Double
    let smileScore: Double
    let eyeOpenRatio: Double
}

struct SampleRecord: Encodable {
    let timestamp: String
    let status: String
    let faceDetected: Bool
    let faceCount: Int
    let expression: String
    let moodTrend: String
    let confidence: Double
    let largestFaceAreaRatio: Double
    let metrics: ExpressionMetrics?
}

enum MonitorError: Error, CustomStringConvertible {
    case invalidArguments(String)
    case helpRequested(String)
    case cameraAccessDenied
    case cameraUnavailable
    case cannotAddInput
    case cannotAddOutput

    var description: String {
        switch self {
        case .invalidArguments(let message):
            return message
        case .helpRequested(let message):
            return message
        case .cameraAccessDenied:
            return "camera access denied"
        case .cameraUnavailable:
            return "no usable video camera found"
        case .cannotAddInput:
            return "failed to add camera input to AVCaptureSession"
        case .cannotAddOutput:
            return "failed to add video output to AVCaptureSession"
        }
    }
}

final class FrameReceiver: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    private let lock = NSLock()
    private var latestPixelBuffer: CVPixelBuffer?
    private var latestCaptureDate: Date?

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            return
        }
        lock.lock()
        latestPixelBuffer = pixelBuffer
        latestCaptureDate = Date()
        lock.unlock()
    }

    func snapshot() -> (CVPixelBuffer, Date)? {
        lock.lock()
        defer { lock.unlock() }
        guard let pixelBuffer = latestPixelBuffer, let captureDate = latestCaptureDate else {
            return nil
        }
        return (pixelBuffer, captureDate)
    }
}

final class MoodTrendTracker {
    private let maxCount: Int
    private var moods: [String] = []

    init(maxCount: Int = 12) {
        self.maxCount = maxCount
    }

    func update(for expression: String) -> String {
        let mood = mapExpressionToMood(expression)
        if mood != "unknown" {
            moods.append(mood)
            if moods.count > maxCount {
                moods.removeFirst(moods.count - maxCount)
            }
        }
        return currentTrend()
    }

    func currentTrend() -> String {
        guard !moods.isEmpty else {
            return "unknown"
        }
        var counts: [String: Int] = [:]
        for mood in moods {
            counts[mood, default: 0] += 1
        }
        return counts.max { lhs, rhs in
            if lhs.value == rhs.value {
                return lhs.key > rhs.key
            }
            return lhs.value < rhs.value
        }?.key ?? "unknown"
    }

    private func mapExpressionToMood(_ expression: String) -> String {
        switch expression {
        case "open-mouth-smile", "smile":
            return "positive"
        case "tired":
            return "fatigued"
        case "neutral":
            return "neutral"
        default:
            return "unknown"
        }
    }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

func parseArguments(_ arguments: [String]) throws -> Config {
    var config = Config()
    var index = 1
    while index < arguments.count {
        let argument = arguments[index]
        switch argument {
        case "--interval-seconds":
            index += 1
            guard index < arguments.count, let value = Double(arguments[index]), value > 0 else {
                throw MonitorError.invalidArguments("invalid value for --interval-seconds")
            }
            config.intervalSeconds = value
        case "--output-path":
            index += 1
            guard index < arguments.count else {
                throw MonitorError.invalidArguments("missing value for --output-path")
            }
            config.outputPath = arguments[index]
        case "--history-path":
            index += 1
            guard index < arguments.count else {
                throw MonitorError.invalidArguments("missing value for --history-path")
            }
            config.historyPath = arguments[index]
        case "--frame-output-path":
            index += 1
            guard index < arguments.count else {
                throw MonitorError.invalidArguments("missing value for --frame-output-path")
            }
            config.frameOutputPath = arguments[index]
        case "--max-samples":
            index += 1
            guard index < arguments.count, let value = Int(arguments[index]), value > 0 else {
                throw MonitorError.invalidArguments("invalid value for --max-samples")
            }
            config.maxSamples = value
        case "--quiet":
            config.quiet = true
        case "--help":
            throw MonitorError.helpRequested(
                """
                usage: expression_monitor.swift [--interval-seconds 5] [--output-path PATH] [--history-path PATH] [--frame-output-path PATH] [--max-samples N] [--quiet]
                """
            )
        default:
            throw MonitorError.invalidArguments("unknown argument: \(argument)")
        }
        index += 1
    }
    return config
}

func requestVideoAccessIfNeeded() throws {
    switch AVCaptureDevice.authorizationStatus(for: .video) {
    case .authorized:
        return
    case .notDetermined:
        let semaphore = DispatchSemaphore(value: 0)
        var granted = false
        AVCaptureDevice.requestAccess(for: .video) { value in
            granted = value
            semaphore.signal()
        }
        semaphore.wait()
        if !granted {
            throw MonitorError.cameraAccessDenied
        }
    default:
        throw MonitorError.cameraAccessDenied
    }
}

func points(for region: VNFaceLandmarkRegion2D?) -> [CGPoint] {
    guard let region else {
        return []
    }
    return region.normalizedPoints.map { point in
        CGPoint(x: CGFloat(point.x), y: CGFloat(point.y))
    }
}

func boundingBox(for points: [CGPoint]) -> CGRect {
    guard let first = points.first else {
        return .null
    }
    var minX = first.x
    var maxX = first.x
    var minY = first.y
    var maxY = first.y
    for point in points.dropFirst() {
        minX = min(minX, point.x)
        maxX = max(maxX, point.x)
        minY = min(minY, point.y)
        maxY = max(maxY, point.y)
    }
    return CGRect(x: minX, y: minY, width: maxX - minX, height: maxY - minY)
}

func averageY(for points: [CGPoint]) -> CGFloat {
    guard !points.isEmpty else {
        return 0
    }
    return points.reduce(CGFloat.zero) { partial, point in
        partial + point.y
    } / CGFloat(points.count)
}

func largestFaceObservation(_ faces: [VNFaceObservation]) -> VNFaceObservation? {
    faces.max { lhs, rhs in
        lhs.boundingBox.width * lhs.boundingBox.height < rhs.boundingBox.width * rhs.boundingBox.height
    }
}

func eyeOpenRatio(for points: [CGPoint]) -> Double {
    let box = boundingBox(for: points)
    guard box.width > 0 else {
        return 0
    }
    return Double(box.height / box.width)
}

func analyzeExpression(from observation: VNFaceObservation) -> (String, Double, ExpressionMetrics?) {
    guard let landmarks = observation.landmarks else {
        return ("neutral", 0.35, nil)
    }

    let outerLips = points(for: landmarks.outerLips)
    let innerLips = points(for: landmarks.innerLips)
    let leftEye = points(for: landmarks.leftEye)
    let rightEye = points(for: landmarks.rightEye)
    guard !outerLips.isEmpty else {
        return ("neutral", 0.35, nil)
    }

    let outerBox = boundingBox(for: outerLips)
    let innerBox = boundingBox(for: innerLips)
    let mouthWidth = max(Double(outerBox.width), 0.0001)
    let mouthOpenRatio = max(Double(innerBox.height), Double(outerBox.height)) / mouthWidth

    let leftCorner = outerLips.min { $0.x < $1.x } ?? outerLips[0]
    let rightCorner = outerLips.max { $0.x < $1.x } ?? outerLips[outerLips.count - 1]
    let cornerYAverage = Double((leftCorner.y + rightCorner.y) / 2.0)
    let smileScore = cornerYAverage - Double(averageY(for: outerLips))

    let leftEyeRatio = eyeOpenRatio(for: leftEye)
    let rightEyeRatio = eyeOpenRatio(for: rightEye)
    let eyeRatioValues = [leftEyeRatio, rightEyeRatio].filter { $0 > 0 }
    let eyeOpenRatioAverage = eyeRatioValues.isEmpty
        ? 0.0
        : eyeRatioValues.reduce(0.0, +) / Double(eyeRatioValues.count)

    let metrics = ExpressionMetrics(
        mouthOpenRatio: mouthOpenRatio,
        smileScore: smileScore,
        eyeOpenRatio: eyeOpenRatioAverage
    )

    if eyeOpenRatioAverage > 0, eyeOpenRatioAverage < 0.09, mouthOpenRatio < 0.18 {
        return ("tired", 0.72, metrics)
    }
    if smileScore > 0.03, mouthOpenRatio > 0.18 {
        return ("open-mouth-smile", 0.9, metrics)
    }
    if smileScore > 0.028 {
        return ("smile", 0.8, metrics)
    }
    return ("neutral", 0.62, metrics)
}

func timestampString(from date: Date) -> String {
    ISO8601DateFormatter().string(from: date)
}

func writeRecord(_ record: SampleRecord, outputPath: String, historyPath: String, quiet: Bool) {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    encoder.keyEncodingStrategy = .convertToSnakeCase
    guard let data = try? encoder.encode(record) else {
        return
    }

    let latestURL = URL(fileURLWithPath: outputPath)
    let historyURL = URL(fileURLWithPath: historyPath)
    try? FileManager.default.createDirectory(at: latestURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    try? FileManager.default.createDirectory(at: historyURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    try? data.write(to: latestURL)

    if let compact = try? JSONEncoder().encode(record) {
        if let handle = try? FileHandle(forWritingTo: historyURL) {
            _ = try? handle.seekToEnd()
            try? handle.write(contentsOf: compact)
            try? handle.write(contentsOf: Data("\n".utf8))
            try? handle.close()
        } else {
            FileManager.default.createFile(atPath: historyURL.path, contents: compact + Data("\n".utf8))
        }
    }

    if !quiet {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
}

func writeFrame(_ pixelBuffer: CVPixelBuffer, frameOutputPath: String) {
    let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
    let context = CIContext()
    guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else {
        return
    }
    let rep = NSBitmapImageRep(cgImage: cgImage)
    guard let data = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.9]) else {
        return
    }
    let url = URL(fileURLWithPath: frameOutputPath)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try? data.write(to: url)
}

final class ExpressionMonitor {
    private let config: Config
    private let session = AVCaptureSession()
    private let videoOutput = AVCaptureVideoDataOutput()
    private let receiver = FrameReceiver()
    private let tracker = MoodTrendTracker()
    private var timer: DispatchSourceTimer?
    private var sampleCount = 0

    init(config: Config) {
        self.config = config
    }

    func start() throws {
        try requestVideoAccessIfNeeded()
        try configureSession()
        session.startRunning()
        scheduleTimer()
    }

    func stop() {
        timer?.cancel()
        timer = nil
        if session.isRunning {
            session.stopRunning()
        }
    }

    private func configureSession() throws {
        session.beginConfiguration()
        session.sessionPreset = .medium

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front)
            ?? AVCaptureDevice.default(for: .video) else {
            throw MonitorError.cameraUnavailable
        }

        let input = try AVCaptureDeviceInput(device: device)
        guard session.canAddInput(input) else {
            throw MonitorError.cannotAddInput
        }
        session.addInput(input)

        videoOutput.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ]
        videoOutput.alwaysDiscardsLateVideoFrames = true
        videoOutput.setSampleBufferDelegate(receiver, queue: DispatchQueue(label: "expression.monitor.video"))
        guard session.canAddOutput(videoOutput) else {
            throw MonitorError.cannotAddOutput
        }
        session.addOutput(videoOutput)
        session.commitConfiguration()
    }

    private func scheduleTimer() {
        let timer = DispatchSource.makeTimerSource(queue: DispatchQueue.global(qos: .userInitiated))
        timer.schedule(deadline: .now(), repeating: config.intervalSeconds)
        timer.setEventHandler { [weak self] in
            self?.sampleOnce()
        }
        self.timer = timer
        timer.resume()
    }

    private func sampleOnce() {
        let record: SampleRecord
        if let (pixelBuffer, captureDate) = receiver.snapshot() {
            writeFrame(pixelBuffer, frameOutputPath: config.frameOutputPath)
            record = analyze(pixelBuffer: pixelBuffer, captureDate: captureDate)
        } else {
            record = SampleRecord(
                timestamp: timestampString(from: Date()),
                status: "warming_up",
                faceDetected: false,
                faceCount: 0,
                expression: "no-frame",
                moodTrend: tracker.currentTrend(),
                confidence: 0.0,
                largestFaceAreaRatio: 0.0,
                metrics: nil
            )
        }

        writeRecord(
            record,
            outputPath: config.outputPath,
            historyPath: config.historyPath,
            quiet: config.quiet
        )

        sampleCount += 1
        if let maxSamples = config.maxSamples, sampleCount >= maxSamples {
            stop()
            exit(0)
        }
    }

    private func analyze(pixelBuffer: CVPixelBuffer, captureDate: Date) -> SampleRecord {
        let request = VNDetectFaceLandmarksRequest()
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up, options: [:])

        do {
            try handler.perform([request])
            let faces = request.results ?? []
            guard let face = largestFaceObservation(faces) else {
                return SampleRecord(
                    timestamp: timestampString(from: captureDate),
                    status: "ok",
                    faceDetected: false,
                    faceCount: 0,
                    expression: "no-face",
                    moodTrend: tracker.currentTrend(),
                    confidence: 0.0,
                    largestFaceAreaRatio: 0.0,
                    metrics: nil
                )
            }

            let (expression, confidence, metrics) = analyzeExpression(from: face)
            let trend = tracker.update(for: expression)
            return SampleRecord(
                timestamp: timestampString(from: captureDate),
                status: "ok",
                faceDetected: true,
                faceCount: faces.count,
                expression: expression,
                moodTrend: trend,
                confidence: confidence,
                largestFaceAreaRatio: Double(face.boundingBox.width * face.boundingBox.height),
                metrics: metrics
            )
        } catch {
            return SampleRecord(
                timestamp: timestampString(from: captureDate),
                status: "analysis_error",
                faceDetected: false,
                faceCount: 0,
                expression: "no-face",
                moodTrend: tracker.currentTrend(),
                confidence: 0.0,
                largestFaceAreaRatio: 0.0,
                metrics: nil
            )
        }
    }
}

let config: Config
do {
    config = try parseArguments(CommandLine.arguments)
} catch {
    if let help = error as? MonitorError, case let .helpRequested(message) = help {
        FileHandle.standardOutput.write(Data((message + "\n").utf8))
        exit(0)
    }
    fail(String(describing: error))
}

let monitor = ExpressionMonitor(config: config)

let signalQueue = DispatchQueue(label: "expression.monitor.signal")
signal(SIGINT, SIG_IGN)
signal(SIGTERM, SIG_IGN)
let sigintSource = DispatchSource.makeSignalSource(signal: SIGINT, queue: signalQueue)
let sigtermSource = DispatchSource.makeSignalSource(signal: SIGTERM, queue: signalQueue)
let stopHandler = {
    monitor.stop()
    exit(0)
}
sigintSource.setEventHandler(handler: stopHandler)
sigtermSource.setEventHandler(handler: stopHandler)
sigintSource.resume()
sigtermSource.resume()

do {
    try monitor.start()
    dispatchMain()
} catch {
    fail(String(describing: error))
}
