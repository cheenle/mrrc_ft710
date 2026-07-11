import SwiftUI

/// Multi-meter bar: PWR | SWR | ALC | Id | Vd
/// Uses derived properties from RadioState (watts, ratio, percent, amps, volts).
struct MeterBarView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        let s = viewModel.state
        HStack(spacing: 4) {
            MeterItem(label: "PWR", value: String(format: "%.0fW", s.powerWatts),
                      fraction: CGFloat(s.powerWatts / 100.0), color: .radioAccent)
            MeterItem(label: "SWR", value: String(format: "%.1f", s.swrRatio),
                      fraction: CGFloat(min((s.swrRatio - 1.0) / 9.0, 1.0)),
                      color: s.swrRatio > 2.0 ? .radioRed : .yellow)
            MeterItem(label: "ALC", value: String(format: "%.0f%%", s.alcPct),
                      fraction: CGFloat(s.alcPct / 100.0), color: .radioCyan)
            MeterItem(label: "Id", value: String(format: "%.1fA", s.idAmps),
                      fraction: CGFloat(s.idAmps / 25.0), color: .green)
            MeterItem(label: "Vd", value: String(format: "%.1fV", s.vdVolts),
                      fraction: CGFloat(s.vdVolts / 15.0), color: .green)
        }
        .padding(.horizontal, 12)
    }
}

/// Single mini-meter with label, tiny bar, and value text.
struct MeterItem: View {
    let label: String
    let value: String
    let fraction: CGFloat
    let color: Color

    var body: some View {
        VStack(spacing: 1) {
            Text(label)
                .font(.system(size: 7))
                .foregroundColor(.radioMuted)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 1)
                        .fill(Color.white.opacity(0.06))
                    RoundedRectangle(cornerRadius: 1)
                        .fill(color)
                        .frame(width: geo.size.width * min(1, fraction))
                }
            }
            .frame(height: 4)
            Text(value)
                .font(.system(size: 7, design: .monospaced))
                .foregroundColor(color)
        }
    }
}
