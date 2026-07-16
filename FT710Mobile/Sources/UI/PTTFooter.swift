import SwiftUI

/// PTT footer with TX indicator
struct PTTFooter: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        VStack(spacing: 0) {
            if viewModel.state.txStatus > 0 {
                Rectangle()
                    .fill(Color.red.opacity(0.08))
                    .frame(height: 8)
            }

            HStack(spacing: 8) {
                // PTT button
                Button(action: {
                    if viewModel.state.txStatus > 0 {
                        viewModel.setPTT(false)
                    } else {
                        viewModel.setPTT(true)
                    }
                }) {
                    Text(viewModel.state.txStatus > 0 ? "● TX ●" : "PTT")
                        .font(.system(size: 24, weight: .heavy, design: .rounded))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 48)
                        .background(viewModel.state.txStatus > 0 ? Color.red : Color.red.opacity(0.8))
                        .cornerRadius(8)
                }

                // TUNE button
                Button(action: { viewModel.toggleTuner() }) {
                    Text("TUNE")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                        .frame(width: 60, height: 48)
                        .background(Color.yellow)
                        .cornerRadius(8)
                }

                // REC button
                Button(action: { viewModel.toggleRecording() }) {
                    Text("REC")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(viewModel.audioCapture.isRecording ? .red : .radioText)
                        .frame(width: 60, height: 48)
                        .background(Color.radioSurface)
                        .cornerRadius(8)
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.radioBg.opacity(0.97))
        }
    }
}
