import SwiftUI

/// Single-row cycling controls: Mode · Band · Filter · ATT · IPO
/// Each button cycles through its options on tap (轮转方式).
struct QuickControlsRow: View {
    @EnvironmentObject var viewModel: RadioViewModel

    // MARK: - Mode

    private var modeIndex: Int {
        RadioState.uiModes.firstIndex(of: viewModel.state.modeName) ?? 1
    }

    private func cycleMode() {
        let idx = (modeIndex + 1) % RadioState.uiModes.count
        viewModel.setMode(RadioState.uiModes[idx])
    }

    // MARK: - Band

    private var bandIndex: Int {
        RadioState.bands.firstIndex(where: {
            $0.start <= viewModel.state.activeFreq && viewModel.state.activeFreq <= $0.end
        }) ?? 5
    }

    private func cycleBand() {
        let idx = (bandIndex + 1) % RadioState.bands.count
        viewModel.setBand(RadioState.bands[idx].defaultFreq)
    }

    // MARK: - Filter

    private var filterWidths: [(Int, Int)] {
        RadioState.filterWidthsForMode(viewModel.state.modeName)
    }

    private var filterIndex: Int {
        guard let hz = viewModel.state.filterHz else { return 0 }
        return filterWidths.firstIndex(where: { $0.1 == hz }) ?? 0
    }

    private func cycleFilter() {
        let idx = (filterIndex + 1) % filterWidths.count
        viewModel.setFilter(filterWidths[idx].0)
    }

    // MARK: - ATT (CAT index: 0=OFF, 1=6dB, 2=12dB, 3=18dB)

    private let attValues: [Int] = [0, 1, 2, 3]
    private let attLabels = ["ATT OFF", "ATT 6dB", "ATT 12dB", "ATT 18dB"]

    private var attIndex: Int {
        attValues.firstIndex(of: viewModel.state.attenuator) ?? 0
    }

    private func cycleATT() {
        let idx = (attIndex + 1) % attValues.count
        viewModel.setAttenuator(attValues[idx])
    }

    // MARK: - IPO (preamp: 0=OFF, 1=AMP1, 2=AMP2)

    private let ipoValues: [Int] = [0, 1, 2]
    private let ipoLabels = ["IPO OFF", "IPO AMP1", "IPO AMP2"]

    private var ipoIndex: Int {
        ipoValues.firstIndex(of: viewModel.state.preamp) ?? 0
    }

    private func cycleIPO() {
        let idx = (ipoIndex + 1) % ipoValues.count
        viewModel.setPreamp(ipoValues[idx])
    }

    // MARK: - Body

    var body: some View {
        HStack(spacing: 4) {
            CycleTapButton(
                label: viewModel.state.modeDisplay,
                color: .radioAccent,
                action: cycleMode
            )
            CycleTapButton(
                label: RadioState.bands[bandIndex].name,
                color: .radioAccent,
                action: cycleBand
            )
            CycleTapButton(
                label: formatFilter(),
                color: .radioAccent,
                action: cycleFilter
            )
            CycleTapButton(
                label: attLabels[attIndex],
                color: attValues[attIndex] == 0 ? .radioMuted : .radioAccent,
                action: cycleATT
            )
            CycleTapButton(
                label: ipoLabels[ipoIndex],
                color: ipoValues[ipoIndex] == 0 ? .radioMuted : .radioAccent,
                action: cycleIPO
            )
        }
        .padding(.horizontal, 6)
    }

    private func formatFilter() -> String {
        guard let hz = viewModel.state.filterHz else { return "—" }
        return hz >= 1000 ? "\(hz/1000)k" : "\(hz)"
    }
}

// MARK: - Cycle Tap Button (轮转：点按循环)

struct CycleTapButton: View {
    let label: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(label)
                .font(.system(size: 11, weight: .bold, design: .monospaced))
                .foregroundColor(.black)
                .frame(maxWidth: .infinity)
                .frame(height: 28)
                .background(color)
                .cornerRadius(6)
        }
    }
}
