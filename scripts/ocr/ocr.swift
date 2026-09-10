import Foundation
import Vision
import AppKit
// Usage: ocr <image> [<image> ...]  -> prints "=====FILE <path>" then recognized lines top-to-bottom, left-to-right
func upscale(_ cg: CGImage, _ factor: Int) -> CGImage {
    let w = cg.width * factor, h = cg.height * factor
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return cg }
    ctx.interpolationQuality = .high
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
    return ctx.makeImage() ?? cg
}
let args = Array(CommandLine.arguments.dropFirst())
for path in args {
    guard let img = NSImage(contentsOfFile: path), let cg0 = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("=====FILE \(path)\n[unreadable image]"); continue }
    let cg = cg0.width < 1800 ? upscale(cg0, 2) : cg0
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([req]) } catch { print("=====FILE \(path)\n[vision error: \(error)]"); continue }
    var items: [(CGFloat, CGFloat, CGFloat, String)] = []
    for o in (req.results ?? []) {
        if let c = o.topCandidates(1).first { items.append((o.boundingBox.midY, o.boundingBox.minX, o.boundingBox.height, c.string)) }
    }
    // group into rows: same row if vertical centers within half a line height
    items.sort { $0.0 > $1.0 }
    var rows: [[(CGFloat, CGFloat, CGFloat, String)]] = []
    for it in items {
        if let last = rows.last, let ref = last.first, abs(ref.0 - it.0) < max(ref.2, it.2) * 0.6 { rows[rows.count - 1].append(it) } else { rows.append([it]) }
    }
    print("=====FILE \(path)")
    for r in rows { print(r.sorted { $0.1 < $1.1 }.map { $0.3 }.joined(separator: "  |  ")) }
}
