import SwiftUI

/// Top header bar: frequency display, band presets with step control, status indicators.
struct HeaderView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @State private var selectedStep: Int = 1000
    @State private var showFreqInput = false
    @State private var freqInputText = ""

    private var currentBandIndex: Int {
        RadioState.bands.firstIndex(where: { abs($0.freq - viewModel.state.frequency) < 50_000 }) ?? 4
    }

    var body: some View {
        VStack(spacing: 2) {
            // ── Row 1: hamburger + status + power ─────────────────
            HStack(spacing: 10) {
                Button(action: {}) {
                    Image(systemName: "line.3.horizontal")
                        .font(.title2)
                        .foregroundColor(.gray)
                }

                ConnectionDot(label: "CTRL", connected: viewModel.state.ctrlConnected)
                ConnectionDot(label: "RX",   connected: viewModel.state.audioRXConnected)
                ConnectionDot(label: "TX",   connected: viewModel.state.audioTXConnected)
                ConnectionDot(label: "FFT",  connected: viewModel.state.spectrumConnected)

                Text(viewModel.state.mode)
                    .font(.caption.weight(.bold))
                    .foregroundColor(.orange)
                    .padding(.horizontal, 5)
                    .padding(.vertical, 1)
                    .background(Color.orange.opacity(0.2))
                    .cornerRadius(3)

                if viewModel.state.ptt {
                    Text(String(format: "%.0fW", viewModel.state.txPowerWatts))
                        .font(.caption.monospaced().bold())
                        .foregroundColor(.red)
                } else {
                    Text("S\(viewModel.state.signalLevel)")
                        .font(.caption.monospaced())
                        .foregroundColor(.green)
                }

                Text(viewModel.state.latency)
                    .font(.caption.monospaced())
                    .foregroundColor(.gray)

                Spacer()

                Button(action: {
                    viewModel.state.powerOn ? viewModel.powerOff() : viewModel.powerOnAsync()
                }) {
                    Image(systemName: viewModel.state.powerOn ? "power.circle.fill" : "power.circle")
                        .font(.title2)
                        .foregroundColor(viewModel.state.powerOn ? .green : .gray)
                }
            }
            .padding(.horizontal, 12)

            // ── Row 2: Frequency with step arrows ─────────────────
            HStack(spacing: 10) {
                Button(action: { viewModel.stepFrequency(up: false, step: selectedStep) }) {
                    Image(systemName: "chevron.left")
                        .font(.title2.weight(.bold))
                        .foregroundColor(.orange)
                        .padding(8)
                        .background(Color.orange.opacity(0.12))
                        .cornerRadius(6)
                }

                Spacer()

                Button(action: {
                    freqInputText = "\(Int(Double(viewModel.state.frequency) / 1000.0))"
                    showFreqInput = true
                }) {
                    FrequencyDisplayView(freqHz: viewModel.state.frequency)
                }
                .alert("输入频率 (kHz)", isPresented: $showFreqInput) {
                    TextField("kHz 或 Hz", text: $freqInputText).keyboardType(.numberPad)
                    Button("取消", role: .cancel) {}
                    Button("确认") {
                        if var val = Int(freqInputText), val > 0 {
                            if val < 100_000 { val *= 1000 }
                            viewModel.setFrequency(val)
                        }
                    }
                }

                Spacer()

                Button(action: { viewModel.stepFrequency(up: true, step: selectedStep) }) {
                    Image(systemName: "chevron.right")
                        .font(.title2.weight(.bold))
                        .foregroundColor(.orange)
                        .padding(8)
                        .background(Color.orange.opacity(0.12))
                        .cornerRadius(6)
                }
            }
            .padding(.horizontal, 12)

            // ── Row 3: Band (left) + Step (right) ──────────────
            HStack {
                Picker("波段", selection: Binding(
                    get: { currentBandIndex },
                    set: { idx in
                        guard idx >= 0, idx < RadioState.bands.count else { return }
                        viewModel.selectBand(RadioState.bands[idx].freq)
                    }
                )) {
                    ForEach(Array(RadioState.bands.enumerated()), id: \.offset) { i, band in
                        Text(band.name).tag(i)
                    }
                }
                .pickerStyle(.menu)
                .tint(.orange)

                Spacer()

                Picker("步进", selection: $selectedStep) {
                    Text("1K").tag(1000)
                    Text("5K").tag(5000)
                    Text("10K").tag(10000)
                    Text("50K").tag(50000)
                    Text("100K").tag(100000)
                }
                .pickerStyle(.menu)
                .tint(.orange)
            }
            .font(.caption)
            .padding(.horizontal, 24)
            .padding(.bottom, 2)
        }
        .padding(.top, 4)
        .background(Color.black.opacity(0.95))
    }

}

// MARK: - Band Selector (rotary)

struct BandSelectorView: View {
    let currentFreq: Int
    let onSelect: ((name: String, freq: Int)) -> Void

    private var currentIndex: Int {
        RadioState.bands.firstIndex(where: { abs($0.freq - currentFreq) < 50_000 }) ?? 4
    }

    private var currentBand: String {
        RadioState.bands[currentIndex].name
    }

    var body: some View {
        HStack(spacing: 2) {
            Button(action: { select(offset: -1) }) {
                Image(systemName: "chevron.left")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.orange)
            }
            .padding(.horizontal, 4)

            Button(action: { select(offset: 1) }) {
                Text(currentBand)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(.orange)
                    .frame(minWidth: 36)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.orange.opacity(0.15))
                    .cornerRadius(5)
            }

            Button(action: { select(offset: 1) }) {
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.bold))
                    .foregroundColor(.orange)
            }
            .padding(.horizontal, 4)
        }
    }

    private func select(offset: Int) {
        var idx = (currentIndex + offset) % RadioState.bands.count
        if idx < 0 { idx += RadioState.bands.count }
        onSelect(RadioState.bands[idx])
    }
}

struct ConnectionDot: View {
    let label: String
    let connected: Bool

    var body: some View {
        HStack(spacing: 2) {
            Circle()
                .fill(connected ? Color.green : Color.red)
                .frame(width: 5, height: 5)
            Text(label)
                .font(.system(size: 8))
                .foregroundColor(.gray)
        }
    }
}
