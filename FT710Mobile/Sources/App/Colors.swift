import SwiftUI

// MARK: - OLED Dark Radio Color Palette

extension Color {
    static let radioBg      = Color(hex: "#1a1a1a")  // web bg-primary
    static let radioSurface = Color(hex: "#242424")  // web bg-secondary (cards)
    static let radioElevated = Color(hex: "#2a2a2a") // web bg-tertiary
    static let radioCard    = Color(hex: "#333333")  // web bg-card
    static let radioBorder  = Color(hex: "#444444")  // web border
    static let radioText    = Color(hex: "#eeeeee")  // web text-primary
    static let radioMuted   = Color(hex: "#999999")  // web text-secondary
    static let radioDim      = Color(hex: "#666666") // web text-muted
    static let radioAccent  = Color(hex: "#f59e0b")  // amber/orange
    static let radioGreen   = Color(hex: "#22c55e")  // success / S-meter
    static let radioRed     = Color(hex: "#ef4444")  // PTT / errors / danger
    static let radioWarning = Color(hex: "#eab308")  // warning
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
