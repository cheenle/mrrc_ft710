import AVFoundation
import Accelerate

/// Captures microphone audio at 48 kHz Float32, accumulates 20ms frames,
/// and emits PCM (or Opus) binary for TX over /WSaudioTX.
///
/// Engine and tap are kept alive across PTT presses for zero-latency TX start.
/// Only `isCapturing` is toggled — the engine runs continuously once primed.
final class AudioCaptureManager: NSObject, ObservableObject, @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let targetSampleRate: Double = 48000
    private let frameMs = 20.0
    private var frameSize: Int { Int(targetSampleRate * frameMs / 1000.0) }  // 960

    private var accumulator: [Float] = []
    private var enginePrimed = false

    // ── Opus encoder ──────────────────────────────────────────
    private let opusEncoder = OpusEncoder()
    var useOpus: Bool = false

    @Published var isCapturing = false
    @Published var isRecording = false
    @Published var txLevel: Float = 0.0
    @Published var captureError: String?
    var micGain: Float = 1.0 {
        didSet { micGain = max(0.0, min(2.0, micGain)) }
    }

    var onFrame: ((Data) -> Void)?

    // MARK: - Start / Stop (keeps engine alive)

    /// Pre-start audio engine in background so first PTT is instant.
    /// Call once after power-on / reconnect.
    func prepare() {
        guard !enginePrimed else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.primeEngine()
        }
    }

    /// Start TX capture (instant — engine already primed).
    func start() {
        guard !isCapturing else { return }
        isCapturing = true
        accumulator.removeAll(keepingCapacity: true)
    }

    /// Stop TX capture (instant — engine stays alive).
    func stop() {
        isCapturing = false
        accumulator.removeAll()
    }

    /// Full shutdown — call on power off only.
    func shutdown() {
        isCapturing = false
        guard enginePrimed else { return }
        engine.stop()
        engine.inputNode.removeTap(onBus: 0)
        enginePrimed = false
        accumulator.removeAll()
        print("🎤 TX engine shutdown")
    }

    // MARK: - Private

    private func primeEngine() {
        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)
        let nativeRate = inputFormat.sampleRate

        print("🎤 TX engine priming @ native \(Int(nativeRate))Hz  frame=\(frameSize)samples")

        // Tap once, keep forever — guarded by isCapturing in closure
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, _ in
            guard let self = self, self.isCapturing else { return }
            self.processBuffer(buffer, nativeRate: nativeRate)
        }

        do {
            try engine.start()
            enginePrimed = true
            print("🎤 TX engine primed (instant PTT ready)")
        } catch {
            captureError = "Mic start: \(error.localizedDescription)"
            print("⚠️ \(captureError!)")
            NotificationCenter.default.post(name: .audioError, object: nil,
                                            userInfo: ["error": captureError ?? "Unknown"])
        }
    }

    private func processBuffer(_ buffer: AVAudioPCMBuffer, nativeRate: Double) {
        guard let channelData = buffer.floatChannelData?.pointee else { return }

        let frameLength = Int(buffer.frameLength)
        let samples = UnsafeBufferPointer(start: channelData, count: frameLength)

        // Convert to target sample rate if needed
        let converted: [Float]
        if abs(nativeRate - targetSampleRate) < 1.0 {
            converted = Array(samples)
        } else {
            converted = resample(Array(samples), from: nativeRate, to: targetSampleRate)
        }

        let gained = converted.map { $0 * micGain }

        // RMS
        var rms: Float = 0
        vDSP_rmsqv(gained, 1, &rms, vDSP_Length(gained.count))
        DispatchQueue.main.async { [weak self] in self?.txLevel = rms }

        // Accumulate and emit complete frames
        accumulator.append(contentsOf: gained)

        while accumulator.count >= frameSize {
            let frame = Array(accumulator.prefix(frameSize))
            accumulator.removeFirst(frameSize)

            if useOpus {
                let int16Samples = floatToInt16(frame)
                if let opusFrame = opusEncoder.encode(int16Samples) {
                    var data = Data(capacity: 1 + opusFrame.count)
                    data.append(0x01)
                    data.append(opusFrame)
                    onFrame?(data)
                }
            } else {
                let int16Samples = floatToInt16(frame)
                var data = Data(capacity: 1 + int16Samples.count * 2)
                data.append(0x00)
                for s in int16Samples {
                    var sample = s
                    data.append(withUnsafeBytes(of: &sample) { Data($0) })
                }
                onFrame?(data)
            }
        }
    }

    // MARK: - Helpers

    private func floatToInt16(_ samples: [Float]) -> [Int16] {
        var out = [Int16](repeating: 0, count: samples.count)
        var clamped = samples.map { max(-1.0, min(1.0, $0)) }
        var scale = Float(32767.0)
        vDSP_vsmul(clamped, 1, &scale, &clamped, 1, vDSP_Length(samples.count))
        for i in 0..<samples.count {
            out[i] = Int16(clamped[i])
        }
        return out
    }

    private func resample(_ input: [Float], from inRate: Double, to outRate: Double) -> [Float] {
        guard !input.isEmpty, inRate > outRate else { return input }

        var filtered = [Float](repeating: 0, count: input.count)
        for i in 1..<(input.count - 1) {
            filtered[i] = (input[i-1] + input[i] + input[i+1]) / 3.0
        }
        filtered[0] = (input[0] + input[1]) / 2.0
        filtered[filtered.count - 1] = (input[input.count - 2] + input[input.count - 1]) / 2.0

        let ratio = outRate / inRate
        let outLen = max(1, Int(Double(input.count) * ratio))
        var out = [Float](repeating: 0, count: outLen)
        let step = 1.0 / ratio

        for i in 0..<outLen {
            let pos = Double(i) * step
            let idx = Int(pos)
            let frac = Float(pos - Double(idx))
            let a = filtered[min(idx, filtered.count - 1)]
            let b = filtered[min(idx + 1, filtered.count - 1)]
            out[i] = a + (b - a) * frac
        }

        return out
    }
}
