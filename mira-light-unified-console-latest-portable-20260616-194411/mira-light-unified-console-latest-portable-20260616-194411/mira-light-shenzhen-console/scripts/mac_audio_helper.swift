#!/usr/bin/env swift
import AVFoundation
import Foundation
import Network

final class AudioHelper {
    private let queue = DispatchQueue(label: "mira-light.mac-audio-helper")
    private var players: [String: AVAudioPlayer] = [:]
    private var keepalivePlayer: AVAudioPlayer?

    init(files: [String: String], keepalivePath: String) throws {
        for (name, path) in files {
            let player = try AVAudioPlayer(contentsOf: URL(fileURLWithPath: path))
            player.volume = 1.0
            player.prepareToPlay()
            players[name] = player
        }

        let keepalive = try AVAudioPlayer(contentsOf: URL(fileURLWithPath: keepalivePath))
        keepalive.numberOfLoops = -1
        keepalive.volume = 0.001
        keepalive.prepareToPlay()
        keepalive.play()
        keepalivePlayer = keepalive
    }

    func play(_ name: String) -> Bool {
        guard let player = players[name] else {
            return false
        }
        queue.async {
            player.stop()
            player.currentTime = 0
            player.prepareToPlay()
            player.play()
        }
        return true
    }

    func handle(_ command: String) -> String {
        let parts = command.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: " ")
        guard let verb = parts.first else {
            return "ERR empty\n"
        }
        if verb == "ping" {
            return "OK pong\n"
        }
        if verb == "play", parts.count >= 2 {
            return play(String(parts[1])) ? "OK playing\n" : "ERR unknown-profile\n"
        }
        return "ERR unknown-command\n"
    }
}

func argumentValue(_ name: String) -> String? {
    let args = CommandLine.arguments
    guard let index = args.firstIndex(of: name), index + 1 < args.count else {
        return nil
    }
    return args[index + 1]
}

let portValue = UInt16(argumentValue("--port") ?? "18777") ?? 18777
guard
    let celebratePath = argumentValue("--celebrate"),
    let clickPath = argumentValue("--click"),
    let keepalivePath = argumentValue("--keepalive")
else {
    fputs("Missing --celebrate, --click, or --keepalive\n", stderr)
    exit(2)
}

let helper: AudioHelper
do {
    helper = try AudioHelper(
        files: [
            "celebrate": celebratePath,
            "click": clickPath,
        ],
        keepalivePath: keepalivePath
    )
} catch {
    fputs("Failed to initialize audio helper: \(error)\n", stderr)
    exit(1)
}

let listener = try NWListener(using: .tcp, on: NWEndpoint.Port(rawValue: portValue)!)
listener.newConnectionHandler = { connection in
    connection.start(queue: .global(qos: .userInitiated))
    connection.receive(minimumIncompleteLength: 1, maximumLength: 256) { data, _, _, _ in
        let request = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
        let response = helper.handle(request)
        connection.send(content: response.data(using: .utf8), completion: .contentProcessed { _ in
            connection.cancel()
        })
    }
}
listener.start(queue: .global(qos: .userInitiated))
print("mira-light mac audio helper listening on 127.0.0.1:\(portValue)")
dispatchMain()
