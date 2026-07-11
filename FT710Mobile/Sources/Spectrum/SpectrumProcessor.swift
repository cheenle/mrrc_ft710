import UIKit

/// Processes FT-710 scope spectrum frames (1B version + 850B wf1 + 850B wf2)
/// into a scrolling waterfall UIImage. All CPU work on background queue.
final class SpectrumProcessor: @unchecked Sendable {
    private let binCount = 850
    private let rowHistory = 100
    private let wfDecimate = 2     // accumulate 2 frames → 1 row (~15 fps waterfall)
    private let wfGain: Float = 12.0
    private let wfBias: Float = 40
    private let wfPctl: Float = 0.35

    // Colour LUT matching web frontend (dark blue → cyan → yellow → red)
    private static let lut: [UInt32] = {
        var t = [UInt32](repeating: 0, count: 256)
        for i in 0..<256 {
            let f = Float(i) / 255.0
            let r, g, b: UInt8
            if f < 0.25 {
                let u = f / 0.25
                r = 0; g = 0; b = UInt8(40 + u * 160)
            } else if f < 0.5 {
                let u = (f - 0.25) / 0.25
                r = 0; g = UInt8(u * 200); b = UInt8(200 + u * 55)
            } else if f < 0.75 {
                let u = (f - 0.5) / 0.25
                r = UInt8(u * 255); g = UInt8(200 + u * 55); b = UInt8(255 * (1 - u))
            } else {
                let u = (f - 0.75) / 0.25
                r = 255; g = UInt8(255 * (1 - u)); b = 0
            }
            t[i] = UInt32(r) << 16 | UInt32(g) << 8 | UInt32(b) | 0xFF000000
        }
        return t
    }()

    private var accum = [Float](repeating: 0, count: 850)
    private var accumCount = 0
    private var pixelBuffer = [UInt32]()
    private var lastDraw = Date()
    private let queue = DispatchQueue(label: "spectrum.processor", qos: .userInteractive)

    /// Feed a raw spectrum frame (1B version + 850B wf1 + 850B wf2 = 1701 bytes).
    func feed(data: Data, onImage: @escaping (UIImage) -> Void) {
        // Expect 1701 bytes: 1B version + 850B wf1 + 850B wf2
        guard data.count >= binCount + 1 else { return }

        let bytes = [UInt8](data)
        let version = bytes[0]
        guard version == 0x01 else { return }

        // Use wf1 (bytes 1..851) for the waterfall
        let wf1 = bytes[1...binCount]

        queue.async { [weak self] in
            guard let self else { return }
            for k in 0..<self.binCount { self.accum[k] += Float(wf1[k]) }
            self.accumCount += 1
            guard self.accumCount >= self.wfDecimate else { return }

            let now = Date()
            if now.timeIntervalSince(self.lastDraw) < 0.066 { return } // ~15 fps max
            self.lastDraw = now

            let snapshot = self.accum
            let count = self.accumCount
            self.accum = [Float](repeating: 0, count: self.binCount)
            self.accumCount = 0

            self.processFrame(snapshot: snapshot, count: count, onImage: onImage)
        }
    }

    private func processFrame(snapshot: [Float], count: Int, onImage: @escaping (UIImage) -> Void) {
        let w = binCount, h = rowHistory
        let inv = 1.0 / Float(count)

        var avg = snapshot
        for k in 0..<w { avg[k] *= inv }

        // Adaptive noise floor
        var sorted = avg.sorted()
        let floor = sorted[Int(Float(w) * wfPctl)] + 2

        // Build pixel row
        let pixels = UnsafeMutablePointer<UInt32>.allocate(capacity: w)
        let lut = Self.lut
        for x in 0..<w {
            var v = wfBias + (avg[x] - floor) * wfGain
            v = max(0, min(255, v))
            pixels[x] = lut[Int(v)]
        }

        // Scroll buffer
        var buf = pixelBuffer
        if buf.count != w * h {
            buf = [UInt32](repeating: 0xFF000000, count: w * h)
        }
        buf.withUnsafeMutableBufferPointer { bp in
            guard let base = bp.baseAddress else { return }
            for y in stride(from: h - 1, to: 0, by: -1) {
                memmove(base + y * w, base + (y - 1) * w, w * 4)
            }
            memcpy(base, pixels, w * 4)
        }
        pixels.deallocate()

        // Build CGImage → UIImage
        let img = buf.withUnsafeMutableBytes { raw -> UIImage? in
            guard let provider = CGDataProvider(data: NSData(bytes: raw.baseAddress!, length: raw.count)),
                  let cgImg = CGImage(width: w, height: h,
                                      bitsPerComponent: 8, bitsPerPixel: 32,
                                      bytesPerRow: w * 4,
                                      space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                      bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue)
                                          .union(.byteOrder32Little),
                                      provider: provider, decode: nil,
                                      shouldInterpolate: false, intent: .defaultIntent)
            else { return nil }
            return UIImage(cgImage: cgImg)
        }

        pixelBuffer = buf
        if let img {
            DispatchQueue.main.async { onImage(img) }
        }
    }
}
