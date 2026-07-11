import SwiftUI

// MARK: - OLED Dark Radio Color Palette

extension Color {
    static let radioBg      = Color(hex: "#020617")  // deepest background
    static let radioSurface = Color(hex: "#0F172A")  // cards / surfaces
    static let radioElevated = Color(hex: "#1E293B") // elevated elements
    static let radioBorder  = Color(hex: "#1E293B")  // subtle borders
    static let radioText    = Color(hex: "#F8FAFC")  // primary text
    static let radioMuted   = Color(hex: "#94A3B8")  // secondary text
    static let radioAccent  = Color(hex: "#F59E0B")  // amber/orange
    static let radioGreen   = Color(hex: "#22C55E")  // signal / S-meter
    static let radioRed     = Color(hex: "#EF4444")  // PTT / errors
    static let radioCyan    = Color(hex: "#00E5FF")  // spectrum
}

extension Color {
    init(hex: String) {
        let s = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var v: UInt64 = 0
        Scanner(string: s).scanHexInt64(&v)
        let r = Double((v >> 16) & 0xFF) / 255
        let g = Double((v >> 8) & 0xFF) / 255
        let b = Double(v & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}
