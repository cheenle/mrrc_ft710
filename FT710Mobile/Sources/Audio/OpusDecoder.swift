import Foundation

/// Opus decoder wrapper using C bridge to libopus
final class OpusDecoder {
    private var handle: Int = 0
    private let sampleRate: UInt32 = 48000
    private let channels: UInt32 = 1

    init() {
        handle = my_create_decoder(sampleRate, channels)
        if handle != 0 {
            print("🎵 Opus decoder created: 48kHz mono")
        } else {
            print("⚠️ Opus decoder creation failed")
        }
    }

    deinit {
        if handle != 0 {
            my_destroy_decoder(handle)
        }
    }

    /// Decode Opus data to 16-bit PCM samples
    func decode(_ opusData: Data) -> [Int16]? {
        guard handle != 0, !opusData.isEmpty else { return nil }

        let maxPCMSize = 960 * 10  // Max 10 frames worth of PCM
        var pcm = [Int16](repeating: 0, count: maxPCMSize)

        let opusPtr = opusData.withUnsafeBytes { $0.baseAddress!.assumingMemoryBound(to: UInt8.self) }
        let decodedLen = my_opus_decode(handle, opusPtr, Int32(opusData.count), &pcm, Int32(maxPCMSize), 0)

        guard decodedLen > 0 else { return nil }

        return Array(pcm[0..<Int(decodedLen)])
    }
}

// MARK: - C Bridge Functions

@_silgen_name("my_create_decoder")
func my_create_decoder(_ sampleRate: UInt32, _ channels: UInt32) -> Int

@_silgen_name("my_destroy_decoder")
func my_destroy_decoder(_ handle: Int)

@_silgen_name("my_opus_decode")
func my_opus_decode(_ handle: Int, _ packet: UnsafePointer<UInt8>, _ packetSize: Int32, _ pcm: UnsafeMutablePointer<Int16>, _ pcmSize: Int32, _ decodeFEC: Int32) -> Int32
