import Foundation

/// A saved frequency/mode preset.
struct ChannelPreset: Codable, Identifiable, Equatable {
    var id: UUID = UUID()
    let name: String
    let frequency: Int       // Hz
    let mode: String
    let date: Date

    var freqString: String {
        let mhz = Double(frequency) / 1_000_000.0
        return String(format: "%.3f MHz", mhz)
    }
}

/// Persists channel presets to UserDefaults. Observable from UI.
@MainActor
final class FavoritesManager: ObservableObject {
    @Published var channels: [ChannelPreset] = []

    private let key = "sunsdr_favorites"
    private let maxChannels = 50

    init() { load() }

    /// Save current frequency + mode as a favorite.
    func add(name: String? = nil, frequency: Int, mode: String) {
        let label = name ?? String(format: "%.3f MHz %@", Double(frequency) / 1_000_000.0, mode)
        let preset = ChannelPreset(name: label, frequency: frequency, mode: mode, date: .now)
        // Avoid duplicates
        channels.removeAll { $0.frequency == frequency && $0.mode == mode }
        channels.insert(preset, at: 0)
        if channels.count > maxChannels { channels.removeLast() }
        save()
    }

    func remove(_ preset: ChannelPreset) {
        channels.removeAll { $0.id == preset.id }
        save()
    }

    func removeAll() {
        channels.removeAll()
        save()
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: key),
              let decoded = try? JSONDecoder().decode([ChannelPreset].self, from: data)
        else { return }
        channels = decoded
    }

    private func save() {
        guard let data = try? JSONEncoder().encode(channels) else { return }
        UserDefaults.standard.set(data, forKey: key)
    }
}
