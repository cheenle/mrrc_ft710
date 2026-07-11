import SwiftUI

struct MemoryChannelsView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @StateObject private var memManager = MemoryChannelsManager()

    let columns = Array(repeating: GridItem(.flexible(), spacing: 4), count: 5)

    var body: some View {
        VStack(spacing: 2) {
            Text("MEMORY").font(.system(size: 9, weight: .bold)).foregroundColor(.radioMuted)
            LazyVGrid(columns: columns, spacing: 4) {
                ForEach(0..<10, id: \.self) { i in
                    if let ch = memManager.channels[i] {
                        Button(action: {
                            viewModel.setFrequency(ch.freq)
                            viewModel.setMode(ch.mode)
                        }) {
                            VStack(spacing: 0) {
                                Text(ch.name).font(.system(size: 9, weight: .bold))
                                    .foregroundColor(.radioAccent).lineLimit(1)
                                Text(ch.freqDisplay).font(.system(size: 7, design: .monospaced))
                                    .foregroundColor(.radioMuted)
                            }
                            .frame(maxWidth: .infinity).padding(.vertical, 4)
                            .background(Color.radioSurface).cornerRadius(4)
                        }
                    } else {
                        VStack(spacing: 0) {
                            Text("---").font(.system(size: 8)).foregroundColor(.radioMuted.opacity(0.3))
                        }
                        .frame(maxWidth: .infinity).padding(.vertical, 4)
                        .background(Color.white.opacity(0.02)).cornerRadius(4)
                    }
                }
            }
        }.padding(.horizontal, 12)
    }
}
