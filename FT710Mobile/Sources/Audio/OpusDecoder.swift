import Foundation

/// Opus audio decoder for RX. Uses libopus via a thin C bridge.
/// Falls back to PCM passthrough if libopus is unavailable.
final class OpusDecoder {
    private let sampleRate: Int32

    init(sampleRate: Double = 48000) {
        self.sampleRate = Int32(sampleRate)
    }

    /// Decode an Opus frame to PCM Int16 samples.
    /// Returns nil on decode failure (caller should fall through to PCM).
    func decode(_ opusData: Data) -> Data? {
        // For initial implementation: libopus integration via Bridging Header.
        // The reference C wrapper API:
        //   opus_decoder_create(sampleRate, 1)
        //   opus_decode(decoder, input, len, output, maxFrameSize, 0)
        //
        // Until the C bridge is wired, return nil to use PCM path.
        // Wire libopus via SPM or a manually-linked XCFramework.
        return nil  // placeholder — C bridge wired in follow-up
    }
}
