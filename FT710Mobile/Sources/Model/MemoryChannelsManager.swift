import Foundation

/// Manages FT-710 memory channels (10 slots, server-backed).
/// Loaded on connect via fullState, updated via broadcast.
@MainActor
final class MemoryChannelsManager: ObservableObject {
    @Published var channels: [MemoryChannel?] = Array(repeating: nil, count: 10)

    struct MemoryChannel: Codable, Identifiable, Equatable {
        var id: Int { index }
        let index: Int
        var name: String
        var freq: Int
        var mode: String

        var freqDisplay: String {
            String(format: "%d.%03d.%03d", freq / 1_000_000, (freq % 1_000_000) / 1000, freq % 1000)
        }
    }

    func loadFromServer(_ raw: [[String: Any]]) {
        channels = Array(repeating: nil, count: 10)
        for (i, item) in raw.enumerated() where i < 10 {
            if let freq = item["freq"] as? Int {
                channels[i] = MemoryChannel(
                    index: i,
                    name: item["name"] as? String ?? "CH\(i+1)",
                    freq: freq,
                    mode: item["mode"] as? String ?? "USB"
                )
            }
        }
    }
}
