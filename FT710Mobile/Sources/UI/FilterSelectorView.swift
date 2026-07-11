import SwiftUI

/// Filter width dropdown — context-sensitive to current mode (voice vs narrow tables).
struct FilterSelectorView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    private var widths: [(Int, Int)] {
        RadioState.filterWidthsForMode(viewModel.state.modeName)
    }

    private var currentLabel: String {
        if let hz = viewModel.state.filterHz { return "\(hz)Hz" }
        return "2400Hz"
    }

    var body: some View {
        Menu {
            ForEach(widths, id: \.0) { idx, hz in
                Button("\(hz) Hz") { viewModel.setFilter(idx) }
            }
        } label: {
            HStack(spacing: 3) {
                Image(systemName: "lines.measurement.horizontal").font(.caption2)
                Text(currentLabel).font(.caption2.weight(.medium))
                Image(systemName: "chevron.down").font(.system(size: 5))
            }
            .foregroundColor(.radioText).frame(height: 28).padding(.horizontal, 6)
            .background(Color.radioSurface).cornerRadius(6)
        }
    }
}
