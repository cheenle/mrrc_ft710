import XCTest
@testable import FT710Mobile

final class OpusCodecTests: XCTestCase {
    
    // MARK: - OpusEncoder Tests
    
    func testOpusEncoderInit() {
        let encoder = OpusEncoder()
        XCTAssertNotNil(encoder)
    }
    
    func testOpusEncoderEncode() {
        let encoder = OpusEncoder()
        
        // Create 16-bit PCM data (10ms at 16kHz = 160 samples)
        let samples: [Int16] = Array(repeating: 0, count: 160)
        let encoded = encoder.encode(samples)
        
        // Should return some data (even if minimal)
        XCTAssertNotNil(encoded)
        if let data = encoded {
            XCTAssertGreaterThan(data.count, 0)
        }
    }
    
    func testOpusEncoderEmptyInput() {
        let encoder = OpusEncoder()
        let samples: [Int16] = []
        let encoded = encoder.encode(samples)
        
        // Should handle empty input gracefully
        XCTAssertNil(encoded)
    }
    
    // MARK: - OpusDecoder Tests
    
    func testOpusDecoderInit() {
        let decoder = OpusDecoder()
        XCTAssertNotNil(decoder)
    }
    
    func testOpusDecoderDecode() {
        let decoder = OpusDecoder()
        
        // Create some dummy Opus data
        let opusData = Data([0x4F, 0x70, 0x75, 0x73]) // "Opus" magic bytes
        
        let decoded = decoder.decode(opusData)
        
        // Should return PCM data or nil if decoding fails
        // We're testing that it doesn't crash
        XCTAssertNotNil(decoded)
    }
    
    func testOpusDecoderInvalidData() {
        let decoder = OpusDecoder()
        
        // Invalid Opus data
        let invalidData = Data([0x00, 0x01, 0x02])
        
        let decoded = decoder.decode(invalidData)
        
        // Should handle invalid data gracefully
        XCTAssertNil(decoded)
    }
    
    // MARK: - C Bridge Tests
    
    func testCBridgeInit() {
        let result = create_encoder(48000, 1, 20)
        XCTAssertGreaterThan(result, 0)
        
        // Cleanup
        destroy_encoder(result)
    }
    
    func testCBridgeEncodeDecode() {
        // Create encoder
        let enc = create_encoder(48000, 1, 20)
        XCTAssertGreaterThan(enc, 0)
        
        // Create decoder
        let dec = create_decoder(48000, 1)
        XCTAssertGreaterThan(dec, 0)
        
        // Create test PCM data (silence)
        let pcmSize = 960 // 20ms at 48kHz
        var pcmData = [Int16](repeating: 0, count: pcmSize)
        
        // Encode
        let maxPacketSize = 1000
        var packetData = [UInt8](repeating: 0, count: maxPacketSize)
        let encodedLen = opus_encode(
            enc,
            &pcmData,
            pcmSize,
            &packetData,
            maxPacketSize
        )
        
        // Should succeed
        XCTAssertGreaterThanOrEqual(encodedLen, 0)
        
        if encodedLen > 0 {
            // Resize packet data to actual size
            let actualPacket = Data(packetData[0..<encodedLen])
            
            // Decode
            var decodedData = [Int16](repeating: 0, count: pcmSize)
            let decodedLen = opus_decode(
                dec,
                actualPacket,
                encodedLen,
                &decodedData,
                pcmSize,
                0
            )
            
            // Should succeed and return correct number of samples
            XCTAssertEqual(decodedLen, pcmSize)
        }
        
        // Cleanup
        destroy_encoder(enc)
        destroy_decoder(dec)
    }
}
