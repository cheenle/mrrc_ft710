import SwiftUI

/// Memory channels grid: M1-M6
struct MemoryChannelsGrid: View {
    @EnvironmentObject var viewModel: RadioViewModel

    var body: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 4) {
            ForEach(0..<6, id: \.self) { index in
                Button(action: { viewModel.recallMemory(index) }) {
                    VStack(spacing: 2) {
                        Text("M\(index + 1)")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.radioAccent)
                        if let channel = viewModel.memoryChannels[index] {
                            Text(channel.freqDisplay)
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundColor(.radioText)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 40)
                    .background(Color.radioSurface)
                    .cornerRadius(4)
                }
            }
        }
        .padding(.horizontal, 6)
    }
}
