import SwiftUI

/// Settings sheet: server config, connection status, RF power, scope span,
/// AGC, PRE/ATT, DSP (NB/NR/AN/COMP), tuner, squelch, AF/RG/Mic gain, about.
struct SettingsView: View {
    @EnvironmentObject var viewModel: RadioViewModel
    @Environment(\.dismiss) private var dismiss
    @AppStorage("serverHost") private var serverHost: String = "radio.vlsc.net:8888"

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Server
                    SettingsCard(title: "Server", icon: "server.rack") {
                        HStack {
                            Image(systemName: "network").foregroundColor(.radioMuted).frame(width: 20)
                            TextField("Host:Port", text: $serverHost)
                                .font(.subheadline.monospaced()).autocapitalization(.none).disableAutocorrection(true)
                        }
                        Button("Reconnect") {
                            dismiss()
                            // Wait for sheet dismiss animation to finish before reconnecting
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                                viewModel.reconnect()
                            }
                        }.foregroundColor(.radioAccent).buttonStyle(.borderedProminent)
                    }

                    // Connection Status
                    SettingsCard(title: "Connection", icon: "wifi") {
                        StatusLine(icon: "antenna.radiowaves.left.and.right", label: "Ctrl", dot: viewModel.state.ctrlConnected)
                        StatusLine(icon: "water.waves", label: "Spectrum", dot: viewModel.state.spectrumConnected)
                        StatusLine(icon: "speaker.wave.2", label: "RX Audio", dot: viewModel.state.audioRXConnected)
                        StatusLine(icon: "mic", label: "TX Audio", dot: viewModel.state.audioTXConnected)
                        StatusLine(icon: "cpu", label: "Serial", dot: viewModel.state.serialConnected)
                    }

                    // RF Power
                    SettingsCard(title: "Transmit", icon: "antenna.radiowaves.left.and.right") {
                        HStack {
                            Text("RF Power").font(.subheadline)
                            Spacer()
                            Text("\(viewModel.state.rfPower)W").font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                        }
                        Slider(value: Binding(
                            get: { Double(viewModel.state.rfPower) },
                            set: { viewModel.setRFPower(Int($0)) }
                        ), in: 5...100, step: 5).tint(.radioRed)
                    }

                    // AGC
                    SettingsCard(title: "AGC", icon: "gauge.medium") {
                        AGCSelector(viewModel: viewModel)
                    }

                    // PRE / ATT
                    SettingsCard(title: "PRE / ATT", icon: "slider.horizontal.3") {
                        PREATTControl(pre: viewModel.state.preamp, att: viewModel.state.attenuator,
                                      setPre: { viewModel.setPreamp($0) }, setAtt: { viewModel.setAttenuator($0) },
                                      powered: viewModel.state.powerOn)
                    }

                    // DSP
                    SettingsCard(title: "DSP", icon: "waveform") {
                        HStack {
                            Image(systemName: "shield.checkmark").foregroundColor(.radioMuted).frame(width: 20)
                            Text("Noise Blanker (NB)").font(.subheadline)
                            Spacer()
                            Toggle("", isOn: Binding(get: { viewModel.state.noiseBlanker }, set: { viewModel.setNoiseBlanker($0) })).labelsHidden().toggleStyle(.switch)
                        }
                        HStack {
                            Image(systemName: "ear").foregroundColor(.radioMuted).frame(width: 20)
                            Text("Noise Reduction (NR)").font(.subheadline)
                            Spacer()
                            Toggle("", isOn: Binding(get: { viewModel.state.noiseReduction }, set: { viewModel.setNoiseReduction($0) })).labelsHidden().toggleStyle(.switch)
                        }
                        HStack {
                            Image(systemName: "waveform.line.dotted").foregroundColor(.radioMuted).frame(width: 20)
                            Text("Auto Notch (AN)").font(.subheadline)
                            Spacer()
                            Toggle("", isOn: Binding(get: { viewModel.state.autoNotch }, set: { viewModel.setAutoNotch($0) })).labelsHidden().toggleStyle(.switch)
                        }
                        HStack {
                            Image(systemName: "gauge").foregroundColor(.radioMuted).frame(width: 20)
                            Text("Compressor (COMP)").font(.subheadline)
                            Spacer()
                            Toggle("", isOn: Binding(get: { viewModel.state.compressor }, set: { viewModel.setCompressor($0) })).labelsHidden().toggleStyle(.switch)
                        }
                    }

                    // Gain
                    SettingsCard(title: "Gain", icon: "slider.horizontal.3") {
                        // TX microphone gain (local phone processing)
                        HStack {
                            Text("TX Mic Gain").font(.subheadline)
                            Spacer()
                            Text("\(Int(viewModel.audioCapture.micGain * 100))%")
                                .font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                        }
                        Slider(value: Binding(
                            get: { Double(viewModel.audioCapture.micGain) },
                            set: { viewModel.audioCapture.micGain = Float($0) }
                        ), in: 0...2.0, step: 0.1).tint(.radioAccent)

                        InlineGainSlider(label: "AF Gain", value: viewModel.state.afGain, max: 255) { viewModel.setAFGain($0) }
                        InlineGainSlider(label: "RF Gain", value: viewModel.state.rfGain, max: 255) { viewModel.setRFGain($0) }
                        InlineGainSlider(label: "Mic Gain (Radio)", value: viewModel.state.micGain, max: 100) { viewModel.setMicGain($0) }
                    }

                    // Other
                    SettingsCard(title: "Other", icon: "gearshape") {
                        HStack {
                            Text("Squelch").font(.subheadline)
                            Spacer()
                            Text("\(viewModel.state.squelch)").font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                        }
                        Slider(value: Binding(
                            get: { Double(viewModel.state.squelch) },
                            set: { viewModel.setSquelch(Int($0)) }
                        ), in: 0...50.0, step: 1).tint(.radioAccent)

                        HStack {
                            Text("Tuner").font(.subheadline)
                            Spacer()
                            Text(viewModel.state.tunerStatus == 0 ? "OFF" : (viewModel.state.tunerStatus == 1 ? "ON" : "TUNING"))
                                .font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                        }
                        Button("Start Tuner") {
                            viewModel.setTuner(1)
                        }.foregroundColor(.radioAccent).buttonStyle(.bordered)

                        ScopeSpanSelector(viewModel: viewModel)
                    }

                    // About
                    SettingsCard(title: "About", icon: "info.circle") {
                        AboutRow(label: "Version", value: "1.0.0")
                        AboutRow(label: "Backend", value: "FT-710 / mrrc_ft710")
                        AboutRow(label: "Radio", value: "Yaesu FT-710")
                    }

                    // Disconnect
                    Button(role: .destructive) { viewModel.powerOff() }
                    label: {
                        Text("Disconnect")
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                    }
                    .buttonStyle(.borderedProminent).tint(.red)
                    .padding(.top, 8)
                }
                .padding(.horizontal)
                .padding(.vertical)
            }
            .scrollContentBackground(.hidden)
            .background(Color.radioBg)
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .foregroundColor(.radioAccent)
                }
            }
        }
    }
}

// MARK: - Reusable Components

struct SettingsCard<Content: View>: View {
    let title: String
    let icon: String
    let content: () -> Content

    init(title: String, icon: String, @ViewBuilder content: @escaping () -> Content) {
        self.title = title
        self.icon = icon
        self.content = content
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: icon).foregroundColor(.radioAccent)
                Text(title).font(.headline).foregroundColor(.radioText)
            }
            content()
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.radioCard)
        .cornerRadius(12)
    }
}

struct StatusLine: View {
    let icon: String
    let label: String
    let dot: Bool
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon).frame(width: 20).foregroundColor(.radioMuted)
            Text(label).font(.subheadline)
            Spacer()
            Circle().fill(dot ? Color.green : Color.red).frame(width: 8, height: 8)
        }
    }
}

struct AboutRow: View {
    let label: String
    let value: String
    var body: some View {
        HStack {
            Text(label).font(.subheadline).foregroundColor(.radioText)
            Spacer()
            Text(value).font(.subheadline.monospaced()).foregroundColor(.radioMuted)
        }
    }
}

struct PREATTControl: View {
    let pre: Int
    let att: Int
    let setPre: (Int) -> Void
    let setAtt: (Int) -> Void
    let powered: Bool

    var body: some View {
        HStack {
            Text("PRE").font(.subheadline)
            Spacer()
            HStack(spacing: 4) {
                Button("-") { if pre > 0 { setPre(pre - 1) } }
                Text("\(pre) dB").font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                Button("+") { setPre(pre + 1) }
            }.disabled(!powered)
        }
        HStack {
            Text("ATT").font(.subheadline)
            Spacer()
            HStack(spacing: 4) {
                Button("-") { if att > 0 { setAtt(att - 1) } }
                Text("\(att) dB").font(.subheadline.monospaced()).foregroundColor(.radioAccent)
                Button("+") { setAtt(att + 1) }
            }.disabled(!powered)
        }
    }
}

struct AGCSelector: View {
    @ObservedObject var viewModel: RadioViewModel
    var body: some View {
        Picker("AGC Mode", selection: Binding(
            get: { viewModel.state.agc },
            set: { viewModel.setAGC($0) }
        )) {
            Text("Off").tag(0)
            Text("Fast").tag(1)
            Text("Med").tag(2)
            Text("Max").tag(3)
        }.pickerStyle(.segmented).tint(.radioAccent)
    }
}

struct InlineGainSlider: View {
    let label: String
    let value: Int
    let max: Int
    let action: (Int) -> Void
    var body: some View {
        HStack {
            Text(label).font(.subheadline)
            Spacer()
            Text("\(value)").font(.subheadline.monospaced()).foregroundColor(.radioAccent)
        }
        Slider(value: Binding(
            get: { Double(value) },
            set: { action(Int($0)) }
        ), in: 0...Double(max), step: 1).tint(.radioAccent)
    }
}

struct ScopeSpanSelector: View {
    @ObservedObject var viewModel: RadioViewModel
    var body: some View {
        Picker("Scope Span", selection: Binding(
            get: { viewModel.state.scopeSpan },
            set: { viewModel.setScopeSpan($0) }
        )) {
            ForEach(Array(RadioState.scopeSpanLabels.keys.sorted()), id: \.self) { k in
                Text(RadioState.scopeSpanLabels[k] ?? "?").tag(k)
            }
        }.pickerStyle(.menu).tint(.radioAccent)
    }
}
