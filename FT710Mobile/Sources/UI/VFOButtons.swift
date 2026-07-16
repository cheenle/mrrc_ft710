import SwiftUI

/// VFO buttons: VFO-A, VFO-B, A=B, SPLIT
struct VFOButtons: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        HStack(spacing: 4) {
            VFOBareButton(title: "VFO-A", isActive: viewModel.state.activeVFO == "A") {
                viewModel.setVFO("A")
            }
            VFOBareButton(title: "VFO-B", isActive: viewModel.state.activeVFO == "B") {
                viewModel.setVFO("B")
            }
            VFOBareButton(title: "A=B", isActive: false) {
                viewModel.copyVFO()
            }
            VFOBareButton(title: "SPLIT", isActive: viewModel.state.split) {
                viewModel.setSplit(!viewModel.state.split)
            }
        }
        .padding(.horizontal, 6)
    }
}

struct VFOBareButton: View {
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
