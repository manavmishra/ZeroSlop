#!/usr/bin/env swift
// Offline, silent H.264 encoder for the repository's rendered demo frames.
// Requires macOS and Apple's command-line tools; no package or network access.
//
// swift growth/encode-demo.swift --frames /tmp/zero-slop-frames \
//   --output /tmp/zero-slop-demo.mp4 --width 1920 --height 1080 --fps 30
//
// Input: same-size PNGs, sorted by filename (use zero-padded frame numbers).
// Alternative: --manifest FILE.json with [{"file":"frame.png","durationMs":1000}].
// Manifest paths resolve relative to the manifest; durations round cumulatively
// to the nearest output frame. Holds reuse one decoded frame without extra PNGs.
// Output: one constant-duration frame per PNG, H.264 MP4, no audio track.
// An existing output is never overwritten. An incomplete output is removed.

import AVFoundation
import CoreGraphics
import Foundation
import ImageIO

struct EncodingError: Error, CustomStringConvertible {
    let description: String
    init(_ message: String) { description = message }
}

struct TimedFrame: Decodable {
    let file: String
    let durationMs: Double
}

struct FrameSegment {
    let url: URL
    let count: Int
}

func main() throws {
    let arguments = Array(CommandLine.arguments.dropFirst())
    let usage = "Usage: swift growth/encode-demo.swift (--frames DIR | --manifest FILE.json) --output FILE.mp4 [--width 1920] [--height 1080] [--fps 30] [--bitrate 12000000]"
    if arguments == ["--help"] {
        print(usage)
        return
    }
    guard arguments.count % 2 == 0 else { throw EncodingError(usage) }
    var options: [String: String] = [:]
    let allowed = Set(["--frames", "--manifest", "--output", "--width", "--height", "--fps", "--bitrate"])
    for index in stride(from: 0, to: arguments.count, by: 2) {
        let key = arguments[index]
        guard allowed.contains(key), options[key] == nil else {
            throw EncodingError("Unknown or repeated option: \(key)\n\(usage)")
        }
        options[key] = arguments[index + 1]
    }
    guard (options["--frames"] != nil) != (options["--manifest"] != nil),
          let output = options["--output"] else {
        throw EncodingError(usage)
    }
    guard let width = Int(options["--width"] ?? "1920"),
          let height = Int(options["--height"] ?? "1080"),
          let fps = Int32(options["--fps"] ?? "30"),
          let bitrate = Int(options["--bitrate"] ?? "12000000"),
          width > 0, height > 0, width % 2 == 0, height % 2 == 0,
          fps > 0, fps <= 120, bitrate > 0 else {
        throw EncodingError("Width and height must be positive even integers; fps must be 1–120; bitrate must be positive.")
    }
    let outputURL = URL(fileURLWithPath: output).standardizedFileURL
    guard outputURL.pathExtension.lowercased() == "mp4" else {
        throw EncodingError("Output must have the .mp4 extension.")
    }
    let manager = FileManager.default
    guard !manager.fileExists(atPath: outputURL.path) else {
        throw EncodingError("Output already exists; choose a new path: \(outputURL.path)")
    }
    let segments: [FrameSegment]
    if let manifest = options["--manifest"] {
        let manifestURL = URL(fileURLWithPath: manifest).standardizedFileURL
        let entries = try JSONDecoder().decode([TimedFrame].self, from: Data(contentsOf: manifestURL))
        var elapsedMs = 0.0
        var previousFrame = 0
        var timedSegments: [FrameSegment] = []
        for entry in entries {
            guard entry.durationMs.isFinite, entry.durationMs > 0 else {
                throw EncodingError("Manifest durations must be positive milliseconds.")
            }
            elapsedMs += entry.durationMs
            let endFrame = Int((elapsedMs * Double(fps) / 1000).rounded())
            let frameURL = URL(fileURLWithPath: entry.file, relativeTo: manifestURL.deletingLastPathComponent()).standardizedFileURL
            guard frameURL.pathExtension.lowercased() == "png" else {
                throw EncodingError("Manifest frame is not a PNG: \(entry.file)")
            }
            if endFrame > previousFrame {
                timedSegments.append(FrameSegment(url: frameURL, count: endFrame - previousFrame))
            }
            previousFrame = endFrame
        }
        segments = timedSegments
    } else {
        segments = try manager.contentsOfDirectory(
            at: URL(fileURLWithPath: options["--frames"]!),
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ).filter { $0.pathExtension.lowercased() == "png" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
            .map { FrameSegment(url: $0, count: 1) }
    }
    guard !segments.isEmpty else { throw EncodingError("No output frames found.") }
    let totalFrames = segments.reduce(0) { $0 + $1.count }

    let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
    writer.shouldOptimizeForNetworkUse = true
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
        AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: width,
        AVVideoHeightKey: height,
        AVVideoColorPropertiesKey: [
            AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
            AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
            AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2,
        ],
        AVVideoCompressionPropertiesKey: [
            AVVideoAverageBitRateKey: bitrate,
            AVVideoExpectedSourceFrameRateKey: fps,
            AVVideoMaxKeyFrameIntervalKey: fps * 2,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
            AVVideoAllowFrameReorderingKey: true,
        ],
    ])
    input.expectsMediaDataInRealTime = false
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: width,
        kCVPixelBufferHeightKey as String: height,
        kCVPixelBufferCGImageCompatibilityKey as String: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
    ])
    guard writer.canAdd(input) else { throw EncodingError("H.264 video input is not supported.") }
    writer.add(input)
    guard writer.startWriting() else {
        throw EncodingError(writer.error?.localizedDescription ?? "Could not start H.264 encoding.")
    }
    writer.startSession(atSourceTime: .zero)
    var completed = false
    defer {
        if !completed {
            writer.cancelWriting()
            try? manager.removeItem(at: outputURL)
        }
    }
    guard let pool = adaptor.pixelBufferPool else { throw EncodingError("Pixel buffer pool is unavailable.") }
    let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
    var frameIndex = 0
    for segment in segments {
        let frameURL = segment.url
        try autoreleasepool {
            guard let source = CGImageSourceCreateWithURL(frameURL as CFURL, nil),
                  let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
                throw EncodingError("Cannot decode \(frameURL.lastPathComponent).")
            }
            guard image.width == width, image.height == height else {
                throw EncodingError("\(frameURL.lastPathComponent) is \(image.width)×\(image.height); expected \(width)×\(height).")
            }
            var pixelBuffer: CVPixelBuffer?
            guard CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, pool, &pixelBuffer) == kCVReturnSuccess,
                  let pixelBuffer else { throw EncodingError("Cannot allocate a video frame.") }
            CVBufferSetAttachment(pixelBuffer, kCVImageBufferCGColorSpaceKey, colorSpace, .shouldPropagate)
            CVBufferSetAttachment(pixelBuffer, kCVImageBufferColorPrimariesKey, kCVImageBufferColorPrimaries_ITU_R_709_2, .shouldPropagate)
            CVBufferSetAttachment(pixelBuffer, kCVImageBufferTransferFunctionKey, kCVImageBufferTransferFunction_sRGB, .shouldPropagate)
            CVPixelBufferLockBaseAddress(pixelBuffer, [])
            defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, []) }
            guard let context = CGContext(
                data: CVPixelBufferGetBaseAddress(pixelBuffer),
                width: width, height: height, bitsPerComponent: 8,
                bytesPerRow: CVPixelBufferGetBytesPerRow(pixelBuffer),
                space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue
            ) else { throw EncodingError("Cannot create the video drawing context.") }
            context.setFillColor(CGColor(gray: 1, alpha: 1))
            context.fill(CGRect(x: 0, y: 0, width: width, height: height))
            context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
            for _ in 0..<segment.count {
                while !input.isReadyForMoreMediaData {
                    guard writer.status == .writing else {
                        throw EncodingError(writer.error?.localizedDescription ?? "Encoding stopped unexpectedly.")
                    }
                    Thread.sleep(forTimeInterval: 0.002)
                }
                guard adaptor.append(pixelBuffer, withPresentationTime: CMTime(value: Int64(frameIndex), timescale: fps)) else {
                    throw EncodingError(writer.error?.localizedDescription ?? "Could not append frame \(frameIndex).")
                }
                frameIndex += 1
                if frameIndex % Int(fps * 5) == 0 { print("Encoded \(frameIndex)/\(totalFrames) frames") }
            }
        }
    }
    let duration = CMTime(value: Int64(totalFrames), timescale: fps)
    writer.endSession(atSourceTime: duration)
    input.markAsFinished()
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    finished.wait()
    guard writer.status == .completed else {
        throw EncodingError(writer.error?.localizedDescription ?? "Could not finish the MP4 container.")
    }
    completed = true
    let bytes = (try manager.attributesOfItem(atPath: outputURL.path)[.size] as? Int64) ?? 0
    print("Wrote \(outputURL.path): \(width)×\(height), \(fps) fps, \(totalFrames) frames, \(String(format: "%.3f", duration.seconds)) s, \(bytes) bytes; H.264, silent, fast-start")
}

do {
    try main()
} catch {
    FileHandle.standardError.write(Data("encode-demo: \(error)\n".utf8))
    exit(1)
}
