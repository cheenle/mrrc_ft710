import SwiftUI

/// Quick DSP toggle buttons: NR, NB, AN, COMP, ATU
struct DSPQuickButtons: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        HStack(spacing: 4) {
            DSPButton(title: "NR", isActive: viewModel.state.noiseReduction) {
                viewModel.setNoiseReduction(!viewModel.state.noiseReduction)
            }
            DSPButton(title: "NB", isActive: viewModel.state.noiseBlanker) {
                viewModel.setNoiseBlanker(!viewModel.state.noiseBlanker)
            }
            DSPButton(title: "AN", isActive: viewModel.state.autoNotch) {
                viewModel.setAutoNotch(!viewModel.state.autoNotch)
            }
            DSPButton(title: "COMP", isActive: viewModel.state.compressor) {
                viewModel.setCompressor(!viewModel.state.compressor)
            }
            DSPButton(title: "ATU", isActive: viewModel.state.tunerStatus == 1) {
                viewModel.setTuner(viewModel.state.tunerStatus == 1 ? 0 : 1)
            }
        }
        .padding(.horizontal, 6)
    }
}

struct DSPButton: View {
    let title: String
    let isActive: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(isActive ? .black : .radioMuted)
                .frame(maxWidth: .infinity)
                .frame(height: 28)
                .background(isActive ? Color.radioAccent : Color.radioSurface)
                .cornerRadius(4)
        }
    }
}
