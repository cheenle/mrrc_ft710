import SwiftUI

/// Top header: status dots + VFO A/B + S-meter reading + power toggle.
struct HeaderView: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        VStack(spacing: 1) {
            // Row 1: Status + meters
            HStack(spacing: 10) {
                Text(viewModel.state.sUnit)
                    .font(.caption.weight(.bold)).foregroundColor(.radioGreen)

                wsDot(viewModel.state.ctrlConnected, "C")
                wsDot(viewModel.state.spectrumConnected, "S")
                wsDot(viewModel.state.audioRXConnected, "R")
                wsDot(viewModel.state.audioTXConnected, "T")

                if viewModel.state.tunerStatus == 2 {
                    Text("TUNE").font(.caption.weight(.bold)).foregroundColor(.radioAccent)
                }

                if viewModel.state.serialConnected {
                    Circle().fill(Color.green).frame(width: 6, height: 6)
                }

                Spacer()

                // VFO A/B toggle
                HStack(spacing: 0) {
                    Button("A") { viewModel.setVFO("A") }
                        .font(.caption.weight(.bold))
                        .foregroundColor(viewModel.state.activeVFO == "A" ? .black : .radioMuted)
                        .frame(width: 28, height: 24)
                        .background(viewModel.state.activeVFO == "A" ? Color.radioAccent : Color.radioSurface)
                    Button("B") { viewModel.setVFO("B") }
                        .font(.caption.weight(.bold))
                        .foregroundColor(viewModel.state.activeVFO == "B" ? .black : .radioMuted)
                        .frame(width: 28, height: 24)
                        .background(viewModel.state.activeVFO == "B" ? Color.radioAccent : Color.radioSurface)
                }.cornerRadius(5)

                // Power toggle
                Button(action: {
                    viewModel.state.powerOn ? viewModel.powerOff() : viewModel.powerOnAsync()
                }) {
                    Image(systemName: viewModel.state.powerOn ? "power.circle.fill" : "power.circle")
                        .font(.body).foregroundColor(viewModel.state.powerOn ? .green : .radioMuted)
                }
            }

            // Row 2: Frequency + band
            HStack(spacing: 8) {
                Button(action: { viewModel.stepFrequency(up: false) }) {
                    Image(systemName: "chevron.left")
                        .font(.title2.weight(.bold)).foregroundColor(.radioAccent)
                }

                FrequencyDisplayView(freqHz: viewModel.state.activeFreq)
                    .onTapGesture {
                        // Frequency tap-to-edit handled via alert in MainRXView
                    }

                Button(action: { viewModel.stepFrequency(up: true) }) {
                    Image(systemName: "chevron.right")
                        .font(.title2.weight(.bold)).foregroundColor(.radioAccent)
                }

                Spacer()

                BandSelectorView()
            }.padding(.horizontal, 4)

            // Row 3: Mode + Filter + scope span
            HStack(spacing: 6) {
                ModeSelectorView()
                FilterSelectorView()
                Spacer()
                Text(viewModel.state.bandName)
                    .font(.caption.weight(.bold)).foregroundColor(.radioAccent)
            }.padding(.horizontal, 12)
        }
        .padding(.vertical, 3)
    }

    private func wsDot(_ on: Bool, _ label: String) -> some View {
        HStack(spacing: 2) {
            Circle().fill(on ? Color.green : Color.red).frame(width: 5, height: 5)
            Text(label).font(.system(size: 8)).foregroundColor(.radioMuted)
        }
    }
}
