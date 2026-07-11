import SwiftUI

/// FT710 S-meter bar with green-yellow-red gradient, S-unit label, and TX indicator.
/// Uses raw sMeter (0-255) scaled to fraction of full scale.
struct SMeterView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        let raw = viewModel.state.sMeter
        let sUnit = viewModel.state.sUnit
        let ptt = viewModel.state.isTransmitting
        let fraction = CGFloat(raw) / 255.0

        VStack(spacing: 1) {
            HStack(spacing: 4) {
                Text("S")
                    .font(.caption2.monospaced())
                    .foregroundColor(.radioMuted)
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color.white.opacity(0.08))
                        RoundedRectangle(cornerRadius: 2)
                            .fill(LinearGradient(colors: [.green, .yellow, .red],
                                                 startPoint: .leading, endPoint: .trailing))
                            .frame(width: geo.size.width * fraction)
                            .animation(.easeOut(duration: 0.3), value: raw)
                    }
                }
                .frame(height: 8)

                Text(ptt ? "TX" : sUnit)
                    .font(.caption2.monospaced().bold())
                    .foregroundColor(ptt ? .radioRed : .radioGreen)
                    .frame(width: 48, alignment: .trailing)
            }
        }
        .padding(.horizontal, 12)
    }
}
