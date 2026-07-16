import SwiftUI

/// Tuning controls: ◀◀ ◀ step ▶ ▶▶
struct TuningControls: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var selectedStep: Int = 1000

    var body: some View {
        HStack(spacing: 4) {
            Button(action: { viewModel.stepFrequency(up: false, step: selectedStep) }) {
                Image(systemName: "chevron.left.double")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.radioAccent)
                    .frame(width: 32, height: 28)
                    .background(Color.radioSurface)
                    .cornerRadius(4)
            }

            Button(action: { viewModel.stepFrequency(up: false) }) {
                Image(systemName: "chevron.left")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.radioAccent)
                    .frame(width: 32, height: 28)
                    .background(Color.radioSurface)
                    .cornerRadius(4)
            }

            // Step selector
            Button(action: {
                let steps = [10, 50, 100, 500, 1000, 5000, 10000]
                if let idx = steps.firstIndex(of: selectedStep / 1000) {
                    let nextIdx = (idx + 1) % steps.count
                    selectedStep = steps[nextIdx] * 1000
                }
            }) {
                Text("\(selectedStep / 1000)K")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundColor(.radioAccent)
                    .frame(width: 44, height: 28)
                    .background(Color.radioAccent.opacity(0.2))
                    .cornerRadius(4)
            }

            Button(action: { viewModel.stepFrequency(up: true) }) {
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.radioAccent)
                    .frame(width: 32, height: 28)
                    .background(Color.radioSurface)
                    .cornerRadius(4)
            }

            Button(action: { viewModel.stepFrequency(up: true, step: selectedStep) }) {
                Image(systemName: "chevron.right.double")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.radioAccent)
                    .frame(width: 32, height: 28)
                    .background(Color.radioSurface)
                    .cornerRadius(4)
            }
        }
        .padding(.horizontal, 6)
    }
}
