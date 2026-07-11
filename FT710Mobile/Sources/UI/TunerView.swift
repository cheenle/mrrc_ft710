import SwiftUI

/// Tuner control view for FT-710.
/// Shows tuner status (OFF/ON/Tuning) with a toggle button.
struct TunerView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        let tunerStatus = viewModel.state.tunerStatus
        let isTuning = tunerStatus == 2
        let isOn = tunerStatus == 1

        HStack(spacing: 12) {
            Image(systemName: "antenna.radiowaves.left.and.right")
                .foregroundColor(isOn || isTuning ? .radioAccent : .radioMuted)

            VStack(alignment: .leading, spacing: 2) {
                Text("Tuner").font(.caption).foregroundColor(.radioMuted)
                Text(tunerLabel(tunerStatus))
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(isTuning ? .radioAccent : isOn ? .radioGreen : .radioMuted)
            }

            Spacer()

            Button(action: {
                viewModel.setTuner(isOn ? 0 : 1)
            }) {
                Text(isTuning ? "..." : (isOn ? "OFF" : "ON"))
                    .font(.caption.weight(.bold))
                    .foregroundColor(.black)
                    .padding(.horizontal, 12).padding(.vertical, 6)
                    .background(isTuning ? Color.radioAccent : (isOn ? Color.radioGreen : Color.radioSurface))
                    .cornerRadius(6)
            }
            .disabled(isTuning)
        }
        .padding(.horizontal, 12).padding(.vertical, 6)
        .background(Color.radioSurface).cornerRadius(8)
        .padding(.horizontal, 12)
    }

    private func tunerLabel(_ status: Int) -> String {
        switch status {
        case 0: return "OFF"
        case 1: return "ON"
        case 2: return "TUNING..."
        default: return "?"
        }
    }
}
