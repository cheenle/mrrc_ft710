import SwiftUI

/// Band selector — dropdown of 12 ham bands. Sets VFO A frequency on selection.
struct BandSelectorView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    private var currentIndex: Int {
        RadioState.bands.firstIndex(where: {
            $0.start <= viewModel.state.activeFreq && viewModel.state.activeFreq <= $0.end
        }) ?? 5
    }

    var body: some View {
        Picker("波段", selection: Binding(
            get: { currentIndex },
            set: { idx in
                guard idx >= 0, idx < RadioState.bands.count else { return }
                viewModel.setBand(RadioState.bands[idx].defaultFreq)
            }
        )) {
            ForEach(Array(RadioState.bands.enumerated()), id: \.offset) { i, band in
                Text(band.name).tag(i)
            }
        }
        .pickerStyle(.menu).tint(.radioAccent).font(.caption)
    }
}
