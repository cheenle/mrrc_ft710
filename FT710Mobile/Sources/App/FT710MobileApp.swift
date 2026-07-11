import SwiftUI
import Security
import UIKit

@main
struct FT710MobileApp: App {
    @AppStorage("serverHost") private var savedHost: String = "radio.vlsc.net:8888"
    @State private var isLoggedIn: Bool = false
    @State private var viewModel: RadioViewModel?

    var body: some Scene {
        WindowGroup {
            if isLoggedIn, let vm = viewModel {
                ContentView()
                    .environmentObject(vm)
                    .preferredColorScheme(.dark)
                    .onAppear { UIApplication.shared.isIdleTimerDisabled = true }
                    .onDisappear { UIApplication.shared.isIdleTimerDisabled = false }
            } else {
                LoginView { host, pass in
                    savedHost = host
                    savePassword(pass, for: host)
                    viewModel = RadioViewModel(serverHost: host, password: pass)
                    isLoggedIn = true
                }
                .preferredColorScheme(.dark)
                .onAppear {
                    if !savedHost.isEmpty, let pass = loadPassword(for: savedHost) {
                        viewModel = RadioViewModel(serverHost: savedHost, password: pass)
                        isLoggedIn = true
                    }
                }
            }
        }
    }

    // MARK: - Keychain

    private let keychainAccount = "ft710_mobile"

    private func savePassword(_ pass: String, for host: String) {
        guard !pass.isEmpty else { return }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrServer as String: host,
            kSecAttrAccount as String: keychainAccount,
            kSecValueData as String: pass.data(using: .utf8)!,
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    private func loadPassword(for host: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrServer as String: host,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}
