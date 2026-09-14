#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

struct Output: Encodable {
    let face_count: Int
    let largest_face_area_ratio: Double
    let faces: [FaceBox]
}

struct FaceBox: Encodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
    let area_ratio: Double
    let center_x: Double
    let center_y: Double
    let edge_margin: Double
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

let arguments = CommandLine.arguments
guard arguments.count == 2 else {
    fail("usage: detect_faces.swift <image_path>")
}

let imageURL = URL(fileURLWithPath: arguments[1])
guard let image = NSImage(contentsOf: imageURL) else {
    fail("failed to load image: \(imageURL.path)")
}

var proposedRect = CGRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil) else {
    fail("failed to create cgImage for: \(imageURL.path)")
}

let request = VNDetectFaceRectanglesRequest()
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])
    let results = request.results ?? []
    let faceBoxes = results.map { observation in
        let box = observation.boundingBox
        let centerX = box.origin.x + box.width / 2.0
        let centerY = box.origin.y + box.height / 2.0
        let edgeMargin = min(
            box.origin.x,
            box.origin.y,
            1.0 - (box.origin.x + box.width),
            1.0 - (box.origin.y + box.height)
        )
        return FaceBox(
            x: Double(box.origin.x),
            y: Double(box.origin.y),
            width: Double(box.width),
            height: Double(box.height),
            area_ratio: Double(box.width * box.height),
            center_x: Double(centerX),
            center_y: Double(centerY),
            edge_margin: Double(edgeMargin)
        )
    }
    let largest = faceBoxes
        .map { $0.area_ratio }
        .max() ?? 0.0
    let output = Output(face_count: results.count, largest_face_area_ratio: largest, faces: faceBoxes)
    let data = try JSONEncoder().encode(output)
    FileHandle.standardOutput.write(data)
} catch {
    fail("face detection failed: \(error.localizedDescription)")
}
