import SwiftUI

/// PTT + TUNE buttons for FT-710.
/// PTT is a large red circle with long-press for push-to-talk.
/// TUNE toggles a steady carrier for antenna tuning.
struct PTTButtonView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        HStack(spacing: 16) {
            // TUNE button
            Button(action: { viewModel.setTune(viewModel.state.txStatus != 2) }) {
                Text(viewModel.state.txStatus == 2 ? "TUNING" : "TUNE")
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(viewModel.state.txStatus == 2 ? .black : .radioAccent)
                    .frame(width: 80, height: 80)
                    .background(viewModel.state.txStatus == 2 ? Color.radioAccent : Color.radioAccent.opacity(0.12))
                    .clipShape(Circle())
            }

            // PTT button
            Circle()
                .fill(viewModel.state.txStatus == 1 ? Color.red : Color.red.opacity(0.3))
                .frame(width: 96, height: 96)
                .overlay(Text("TX").font(.title2.weight(.bold))
                    .foregroundColor(viewModel.state.txStatus == 1 ? .white : .red))
                .overlay(Circle().stroke(Color.red.opacity(0.5), lineWidth: 3))
                .onLongPressGesture(minimumDuration: 0.05, maximumDistance: 100) {
                    // released
                } onPressingChanged: { pressing in
                    viewModel.setPTT(pressing)
                }
        }
        .padding(.bottom, 80) // room for tab bar
    }
}
