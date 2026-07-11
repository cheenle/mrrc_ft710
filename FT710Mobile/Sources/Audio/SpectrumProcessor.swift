import UIKit

/// Processes raw 512-byte spectrum frames into waterfall UIImage rows.
/// All heavy computation runs on a background queue; only the final image
/// is published on the main actor.
final class SpectrumProcessor: @unchecked Sendable {
    private let binCount = 512
    private let rowHistory = 100

    // Web-matching waterfall parameters
    private let wfDecimate = 5   // accumulate 5 frames → 1 waterfall row
    private let wfPctl: Float = 0.30
    private let wfHeadroom: Float = 2
    private let wfGain: Float = 8.0
    private let wfBias: Float = 52

    // Colour LUT matching web frontend
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

    private var accum = [Float](repeating: 0, count: 512)
    private var accumCount = 0
    private var pixelBuffer = [UInt32]()
    private var lastDraw = Date()
    private var skipCounter = 0
    private let queue = DispatchQueue(label: "spectrum.processor", qos: .userInteractive)

    /// Called from any thread with raw 512-byte spectrum data.
    func feed(data: Data, onImage: @escaping (UIImage) -> Void) {
        guard data.count == binCount else { return }

        // Skip every other frame — dispatching + accumulating still costs CPU
        skipCounter += 1
        if skipCounter & 1 == 0 { return }

        // Accumulate on serial background queue
        queue.async { [weak self] in
            guard let self else { return }
            let bins = [UInt8](data)
            for k in 0..<self.binCount { self.accum[k] += Float(bins[k]) }
            self.accumCount += 1
            guard self.accumCount >= self.wfDecimate else { return }

            // Throttle to ~10 fps (plenty for visual waterfall, saves CPU)
            let now = Date()
            if now.timeIntervalSince(self.lastDraw) < 0.10 { return }
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

        // Normalise in-place
        var avg = snapshot
        for k in 0..<binCount { avg[k] *= inv }

        // Adaptive noise floor
        var sorted = avg.sorted()
        let floor = sorted[Int(Float(binCount) * wfPctl)] + wfHeadroom

        // Build pixel row
        let pixels = UnsafeMutablePointer<UInt32>.allocate(capacity: binCount)
        let lut = Self.lut
        for x in 0..<binCount {
            var v = wfBias + (avg[x] - floor) * wfGain
            v = max(0, min(255, v))
            pixels[x] = lut[Int(v)]
        }

        // Scroll buffer + insert new row
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

        // Build CGImage
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
