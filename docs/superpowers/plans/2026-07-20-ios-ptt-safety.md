# iOS 发射安全修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 iOS app 三项发射安全 P0(PTT 释放竞态、无看门狗/后台保护、瀑布流误触 QSY)+ 首屏假开机,对齐 SDD ch15 的 web 端防护层级。

**Architecture:** 新建 `PTTManager` 状态机模块(闭包依赖注入、可单测),乐观 TX 状态驱动 UI;release 无条件发 TX0 + 500ms×3 看门狗校验服务端回显;scenePhase 进后台强制释放;瀑布流 DragGesture 换 SpatialTapGesture。服务端零改动。

**Tech Stack:** Swift 5.9 / SwiftUI / Combine / XCTest;xcodegen 2.45.4(已装,`/opt/homebrew/bin/xcodegen`)。

**Spec:** `docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md`(SDD 追溯:SC8 · NFR-008 · NFR-012 · UC-005 · AD-007 · ch15 · R4)

**与 spec 的一处偏差(已确认必要):** spec 把"测试接入工程"整体留给 spec ②,但本计划需要跑通 TDD。Task 1 新增一个**只编译 `Sources/PTT` + 新测试文件**的最小 test target——不触碰两个腐烂的旧测试文件(`RadioViewModelTests`/`OpusCodecTests`,它们仍然不进工程),也不链接 libopus,模拟器可跑。spec ② 仍负责整体测试体系修复。

**工作目录约定:** 所有命令在仓库根 `/Users/cheenle/HAM/mrrc_ft710` 执行;xcodegen/xcodebuild 命令在 `FT710Mobile/` 子目录执行(命令里带 `cd`)。

---

### Task 1: 测试基础设施 + 失败测试(TDD Red)

**Files:**
- Modify: `FT710Mobile/project.yml`
- Create: `FT710Mobile/Sources/PTT/PTTManager.swift`(stub,只含 API 空壳)
- Test: `FT710Mobile/Tests/FT710MobileTests/PTTManagerTests.swift`

- [ ] **Step 1: project.yml 增加 PTTManagerTests target 和 scheme**

在 `FT710Mobile/project.yml` 的 `targets:` 段(`FT710Mobile` target 之后)追加:

```yaml
  PTTManagerTests:
    type: bundle.unit-test
    platform: iOS
    sources:
      - path: Sources/PTT
      - path: Tests/FT710MobileTests/PTTManagerTests.swift
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.hamradio.ft710mobile.pttmanagertests
        SWIFT_VERSION: "5.9"
        GENERATE_INFOPLIST: YES
```

在 `schemes:` 段(`FT710Mobile` scheme 之后)追加:

```yaml
  PTTManagerTests:
    build:
      targets:
        PTTManagerTests: all
    test:
      config: Debug
      targets:
        - PTTManagerTests
```

注意 YAML 缩进:`PTTManagerTests` target 与 `FT710Mobile:` target 同级(2 空格),scheme 同理。

- [ ] **Step 2: 写 PTTManager stub(让测试能编译,但行为全错)**

Create `FT710Mobile/Sources/PTT/PTTManager.swift`:

```swift
import Foundation
import Combine

/// PTT state machine mirroring the web client's ptt_manager.js semantics.
/// Release is safety-critical: unconditional TX0 + watchdog verify.
/// See docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md.
@MainActor
final class PTTManager: ObservableObject {

    enum Phase: Equatable {
        case idle, keying, keyed, releasing
    }

    @Published private(set) var phase: Phase = .idle
    var isTX: Bool { phase == .keying || phase == .keyed }

    var sendPTT: (Bool) -> Void
    var sendTXAudioStop: () -> Void
    var setTXAudioActive: (Bool) -> Void
    var serverTXStatus: () -> Int
    var isCtrlConnected: () -> Bool
    var onStuckTX: () -> Void

    var watchdogInterval: TimeInterval = 0.5
    var maxRetries = 3

    init(sendPTT: @escaping (Bool) -> Void,
         sendTXAudioStop: @escaping () -> Void,
         setTXAudioActive: @escaping (Bool) -> Void,
         serverTXStatus: @escaping () -> Int,
         isCtrlConnected: @escaping () -> Bool,
         onStuckTX: @escaping () -> Void) {
        self.sendPTT = sendPTT
        self.sendTXAudioStop = sendTXAudioStop
        self.setTXAudioActive = setTXAudioActive
        self.serverTXStatus = serverTXStatus
        self.isCtrlConnected = isCtrlConnected
        self.onStuckTX = onStuckTX
    }

    func press() { /* STUB */ }
    func release() { /* STUB */ }
    func forceRelease() { /* STUB */ }
}
```

- [ ] **Step 3: 写完整测试文件**

Create `FT710Mobile/Tests/FT710MobileTests/PTTManagerTests.swift`:

```swift
import XCTest

@MainActor
final class PTTManagerTests: XCTestCase {

    /// Records all injected-callback invocations for assertions.
    private final class Harness {
        var sentPTT: [Bool] = []
        var txAudioStopCount = 0
        var captureActive: [Bool] = []
        var stuckTXCount = 0
        var echoStatus = 0          // simulated server tx_status echo
        var connected = true

        func make(interval: TimeInterval = 0.01, retries: Int = 3) -> PTTManager {
            let mgr = PTTManager(
                sendPTT: { [weak self] tx in self?.sentPTT.append(tx) },
                sendTXAudioStop: { [weak self] in self?.txAudioStopCount += 1 },
                setTXAudioActive: { [weak self] on in self?.captureActive.append(on) },
                serverTXStatus: { [weak self] in self?.echoStatus ?? 0 },
                isCtrlConnected: { [weak self] in self?.connected ?? true },
                onStuckTX: { [weak self] in self?.stuckTXCount += 1 }
            )
            mgr.watchdogInterval = interval
            mgr.maxRetries = retries
            return mgr
        }
    }

    func testPressRefusedWhenDisconnected() {
        let h = Harness(); h.connected = false
        let mgr = h.make()
        mgr.press()
        XCTAssertEqual(mgr.phase, .idle)
        XCTAssertTrue(h.sentPTT.isEmpty)
        XCTAssertTrue(h.captureActive.isEmpty)
    }

    func testPressIsOptimistic() {
        let h = Harness()
        let mgr = h.make()
        mgr.press()
        XCTAssertEqual(mgr.phase, .keyed)
        XCTAssertEqual(h.sentPTT, [true])
        XCTAssertEqual(h.captureActive, [true])
        XCTAssertTrue(mgr.isTX)
    }

    /// Regression for analysis §2.1: rapid press→release must ALWAYS send
    /// ptt:false — the old code dropped it when the tx_status echo hadn't arrived.
    func testRapidPressReleaseAlwaysSendsTX0() {
        let h = Harness(); h.echoStatus = 0  // echo hasn't caught up — the bug scenario
        let mgr = h.make()
        mgr.press()
        mgr.release()
        XCTAssertEqual(h.sentPTT, [true, false])
        XCTAssertEqual(h.captureActive, [true, false])
        XCTAssertEqual(h.txAudioStopCount, 1)
    }

    func testReleaseWithRXEchoGoesIdleWithoutRetry() async throws {
        let h = Harness(); h.echoStatus = 0
        let mgr = h.make()
        mgr.press(); mgr.release()
        try await Task.sleep(nanoseconds: 50_000_000)  // > 1 watchdog tick
        XCTAssertEqual(mgr.phase, .idle)
        XCTAssertEqual(h.sentPTT, [true, false])  // no re-send
        XCTAssertEqual(h.stuckTXCount, 0)
    }

    func testWatchdogResendsUntilRXEcho() async throws {
        let h = Harness(); h.echoStatus = 1  // radio still TX
        let mgr = h.make()
        mgr.press(); mgr.release()
        try await Task.sleep(nanoseconds: 25_000_000)  // ~2 ticks
        h.echoStatus = 0                              // radio finally RX
        try await Task.sleep(nanoseconds: 30_000_000)
        XCTAssertEqual(mgr.phase, .idle)
        XCTAssertGreaterThanOrEqual(h.sentPTT.filter({ $0 == false }).count, 2)
        XCTAssertEqual(h.stuckTXCount, 0)
    }

    func testWatchdogGivesUpAfterMaxRetriesAndReports() async throws {
        let h = Harness(); h.echoStatus = 1
        let mgr = h.make()
        mgr.press(); mgr.release()
        try await Task.sleep(nanoseconds: 100_000_000)  // > 3 ticks
        // 1 original release + 3 watchdog re-sends = 4 TX0
        XCTAssertEqual(h.sentPTT.filter({ $0 == false }).count, 4)
        XCTAssertEqual(h.stuckTXCount, 1)
        XCTAssertEqual(mgr.phase, .idle)
    }

    func testPressDuringWatchdogCancelsRetries() async throws {
        let h = Harness(); h.echoStatus = 1
        let mgr = h.make(interval: 0.03)
        mgr.press(); mgr.release()
        try await Task.sleep(nanoseconds: 35_000_000)  // ~1 tick: 1 re-send
        let countBefore = h.sentPTT.count
        h.echoStatus = 0
        mgr.press()  // re-key during watchdog window
        XCTAssertEqual(mgr.phase, .keyed)
        try await Task.sleep(nanoseconds: 100_000_000)  // watchdog must stay cancelled
        XCTAssertEqual(h.sentPTT.count, countBefore + 1)  // only the press's `true`
        XCTAssertEqual(h.sentPTT.last, true)
    }

    func testForceReleaseFromIdleIsIdempotent() async throws {
        let h = Harness(); h.echoStatus = 0
        let mgr = h.make()
        mgr.forceRelease()
        mgr.forceRelease()
        XCTAssertEqual(h.sentPTT, [false, false])  // one TX0 per call, no crash
        XCTAssertEqual(h.txAudioStopCount, 2)
        try await Task.sleep(nanoseconds: 50_000_000)
        XCTAssertEqual(mgr.phase, .idle)
        XCTAssertEqual(h.sentPTT.count, 2)  // echo RX → watchdog exits clean
    }
}
```

- [ ] **Step 4: xcodegen 重新生成工程**

Run: `cd FT710Mobile && xcodegen`
Expected: `⚙️ Generating project ... Created project` 无 error。

验证 scheme 存在:
Run: `cd FT710Mobile && xcodebuild -list -project FT710Mobile.xcodeproj`
Expected: Schemes 列表含 `FT710Mobile` 和 `PTTManagerTests`。

- [ ] **Step 5: 跑测试确认失败(TDD Red)**

Run: `cd FT710Mobile && xcodebuild test -project FT710Mobile.xcodeproj -scheme PTTManagerTests -destination 'platform=iOS Simulator,name=iPhone 15' -quiet 2>&1 | tail -30`

Expected: 编译成功,以下测试 FAIL:
- `testPressIsOptimistic`(stub 不发命令、phase 不变)
- `testRapidPressReleaseAlwaysSendsTX0`
- `testWatchdogResendsUntilRXEcho`
- `testWatchdogGivesUpAfterMaxRetriesAndReports`
- `testPressDuringWatchdogCancelsRetries`
- `testForceReleaseFromIdleIsIdempotent`

(`testPressRefusedWhenDisconnected` 和 `testReleaseWithRXEchoGoesIdleWithoutRetry` 在 stub 下恰好通过,正常。)

若模拟器 `iPhone 15` 不存在:`xcodebuild -showdestinations -project FT710Mobile.xcodeproj -scheme PTTManagerTests` 挑一个已装的 iPhone 模拟器替换。

**本 task 不 commit(red 状态)。**

---

### Task 2: PTTManager 完整实现(TDD Green)

**Files:**
- Modify: `FT710Mobile/Sources/PTT/PTTManager.swift`(替换三个 stub 方法 + 加私有实现)

- [ ] **Step 1: 替换实现**

把 `FT710Mobile/Sources/PTT/PTTManager.swift` 中三个 stub 方法:

```swift
    func press() { /* STUB */ }
    func release() { /* STUB */ }
    func forceRelease() { /* STUB */ }
```

替换为完整实现(并在类末尾、`init` 之后加私有方法):

```swift
    /// Touch down. Optimistic: fire-and-forget, no server-echo wait (NFR-008 <100ms).
    /// Accepts re-press from .releasing (cancels the watchdog — legal re-key).
    func press() {
        guard phase == .idle || phase == .releasing else { return }
        // Refuse when we can't command the radio: an optimistic TX we can't
        // control is the most dangerous state.
        guard isCtrlConnected() else { return }
        cancelWatchdog()
        phase = .keying
        sendPTT(true)
        setTXAudioActive(true)
        phase = .keyed
    }

    /// Touch up. Unconditional release + watchdog (SDD ch15 Layers 2/3/7).
    func release() {
        guard phase != .idle else { return }
        sendRelease()
        startWatchdog()
    }

    /// Idempotent emergency release from ANY state (scenePhase / error paths).
    /// TX0 is fire-and-forget; one per call, harmless when already in RX.
    func forceRelease() {
        sendRelease()
        startWatchdog()
    }

    // MARK: - Private

    private var watchdogTask: Task<Void, Never>?

    private func sendRelease() {
        sendPTT(false)
        sendTXAudioStop()        // 's:' on /WSaudioTX — SDD ch15 Layer 7 (server.py:1796)
        setTXAudioActive(false)
        phase = .releasing
    }

    /// Layer 3: after release, verify the server's tx_status echo returns to
    /// RX (0); re-send TX0 up to maxRetries times, then report stuck TX.
    private func startWatchdog() {
        cancelWatchdog()
        watchdogTask = Task { [weak self] in
            guard let self else { return }
            for _ in 1...self.maxRetries {
                try? await Task.sleep(nanoseconds: UInt64(self.watchdogInterval * 1_000_000_000))
                if Task.isCancelled { return }
                if self.serverTXStatus() == 0 {
                    self.phase = .idle
                    return
                }
                self.sendPTT(false)  // re-send TX0
            }
            if self.serverTXStatus() != 0 {
                self.onStuckTX()
            }
            self.phase = .idle
        }
    }

    private func cancelWatchdog() {
        watchdogTask?.cancel()
        watchdogTask = nil
    }
```

- [ ] **Step 2: 跑测试确认全绿(TDD Green)**

Run: `cd FT710Mobile && xcodebuild test -project FT710Mobile.xcodeproj -scheme PTTManagerTests -destination 'platform=iOS Simulator,name=iPhone 15' -quiet 2>&1 | tail -20`
Expected: `Test Suite 'PTTManagerTests' passed`,8/8 PASS。

- [ ] **Step 3: 确认 app target 仍能编译**

Run: `cd FT710Mobile && xcodebuild build -project FT710Mobile.xcodeproj -scheme FT710Mobile -destination 'generic/platform=iOS' -configuration Debug CODE_SIGNING_ALLOWED=NO -quiet 2>&1 | tail -10`
Expected: `BUILD SUCCEEDED`(PTTManager.swift 经 Sources glob 自动进入 app target)。

- [ ] **Step 4: Commit**

```bash
git add FT710Mobile/project.yml FT710Mobile/FT710Mobile.xcodeproj FT710Mobile/Sources/PTT/PTTManager.swift FT710Mobile/Tests/FT710MobileTests/PTTManagerTests.swift
git commit -m "Add PTTManager state machine with release watchdog (iOS)

Unconditional TX0 on release + 500msx3 echo verify + 's:' TX-audio
stop, mirroring web ptt_manager.js (SDD ch15 Layers 2/3/7). Minimal
unit-test target compiles only Sources/PTT; 8 tests green."
```

---

### Task 3: RadioViewModel 接线 + ContentView 手势(原子改动)

**Files:**
- Modify: `FT710Mobile/Sources/ViewModel/RadioViewModel.swift`
- Modify: `FT710Mobile/Sources/UI/ContentView.swift:216-235`

(两文件必须同 task 改完才能编译:删 `setPTT` 与 ContentView 引用互换互为依赖。)

- [ ] **Step 1: RadioViewModel — 声明 pttManager(lazy)**

`RadioViewModel.swift` 第 14 行 `private var cancellables = Set<AnyCancellable>()` 之后插入:

```swift

    /// PTT state machine (safety-critical release path).
    /// Lazy so its closures can capture self after stored properties init.
    lazy var pttManager: PTTManager = makePTTManager()
```

- [ ] **Step 2: RadioViewModel — 删除 setPTT,改 forceRelease 路径**

删除第 266-278 行(`// MARK: - PTT / Tune` 注释 + 整个 `setPTT` 方法),替换为:

```swift
    // MARK: - Tune
```

`powerOff()`(第 173-179 行)改为:

```swift
    /// Power off: force RX, disconnect + stop audio + stop heartbeat.
    func powerOff() {
        pttManager.forceRelease()
        state.powerOn = false
        stopPing()
        connection.disconnectAll()
        audioPlayback.stop()
        audioCapture.shutdown()
    }
```

`reconnect()`(第 47 行)方法体第一行(`connection.disconnectAll()` 之前)插入:

```swift
        pttManager.forceRelease()
```

`powerOnAsync()` 两个失败分支都加 forceRelease:
- 网络错误分支(`self.state.powerOn = false` 那处,第 135-138 行)改为:

```swift
                if let err = error {
                    self.state.connectionError = "连接失败: \(err.localizedDescription)"
                    self.state.powerOn = false
                    self.pttManager.forceRelease()
                    return
                }
```

- 认证失败分支(`self.state.powerOn = false  // Reset power state on auth failure`,第 161-164 行)改为:

```swift
                } else {
                    self.state.connectionError = "认证失败，请检查密码"
                    self.state.powerOn = false
                    self.pttManager.forceRelease()
                }
```

- [ ] **Step 3: RadioViewModel — bindSockets 加 objectWillChange 中继 + makePTTManager**

`bindSockets()` 里 `memChannels.objectWillChange.sink ... .store(in: &cancellables)`(第 392-394 行)之后插入:

```swift

        pttManager.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }.store(in: &cancellables)
```

`bindSockets()` 方法之后(`}` 收尾后,类的末尾 `}` 之前)加:

```swift

    private func makePTTManager() -> PTTManager {
        PTTManager(
            sendPTT: { [weak self] tx in self?.sendSet("ptt", tx) },
            sendTXAudioStop: { [weak self] in self?.connection.audioTX.send(text: "s:") },
            setTXAudioActive: { [weak self] active in
                guard let self else { return }
                if active {
                    self.audioPlayback.isMuted = true
                    self.audioCapture.start()
                } else {
                    self.audioCapture.stop()
                    self.audioPlayback.isMuted = false
                }
            },
            serverTXStatus: { [weak self] in self?.state.txStatus ?? 0 },
            isCtrlConnected: { [weak self] in self?.connection.ctrlConnected ?? false },
            onStuckTX: { [weak self] in
                self?.showError(title: "PTT", message: "PTT 释放未确认，请检查电台")
            }
        )
    }
```

- [ ] **Step 4: ContentView — TX 指示改读 pttManager**

第 216 行:`if viewModel.state.txStatus > 0 {` → `if viewModel.pttManager.isTX {`

第 221 行:`Text(viewModel.state.txStatus > 0 ? "● TX ●" : "PTT")` → `Text(viewModel.pttManager.isTX ? "● TX ●" : "PTT")`

第 225 行:`.background(viewModel.state.txStatus > 0 ? Color.red : Color.red.opacity(0.8))` → `.background(viewModel.pttManager.isTX ? Color.red : Color.red.opacity(0.8))`

- [ ] **Step 5: ContentView — 手势改无条件调用**

第 227-235 行的 `.gesture(...)` 整块替换为:

```swift
                            .gesture(
                                DragGesture(minimumDistance: 0)
                                    .onChanged { _ in viewModel.pttManager.press() }
                                    .onEnded { _ in viewModel.pttManager.release() }
                            )
```

(重入防护在 `press()`/`release()` 内部 guard,手势层不再读任何回显状态。)

- [ ] **Step 6: 确认没有遗漏的 setPTT 引用**

Run: `cd FT710Mobile && grep -rn "setPTT" Sources/ Tests/`
Expected: 无任何输出(零引用)。若有输出,把该处改为 `pttManager.press()`/`pttManager.release()` 对应调用后重查。

- [ ] **Step 7: 编译 app + 跑单测**

Run: `cd FT710Mobile && xcodebuild build -project FT710Mobile.xcodeproj -scheme FT710Mobile -destination 'generic/platform=iOS' -configuration Debug CODE_SIGNING_ALLOWED=NO -quiet 2>&1 | tail -10`
Expected: `BUILD SUCCEEDED`

Run: `cd FT710Mobile && xcodebuild test -project FT710Mobile.xcodeproj -scheme PTTManagerTests -destination 'platform=iOS Simulator,name=iPhone 15' -quiet 2>&1 | tail -5`
Expected: 8/8 PASS(接线未改状态机语义)。

- [ ] **Step 8: Commit**

```bash
git add FT710Mobile/Sources/ViewModel/RadioViewModel.swift FT710Mobile/Sources/UI/ContentView.swift
git commit -m "Wire PTTManager into RadioViewModel and ContentView (iOS)

PTT gesture no longer consults tx_status echo (the stuck-TX race);
TX indicator reads optimistic pttManager.phase; forceRelease on
powerOff/reconnect/auth-failure paths. Removes setPTT."
```

---

### Task 4: WaterfallView 轻点 QSY

**Files:**
- Modify: `FT710Mobile/Sources/UI/WaterfallView.swift:70-74`

- [ ] **Step 1: 替换手势**

第 70-74 行:

```swift
            .gesture(DragGesture(minimumDistance: 0).onEnded { v in
                let fract = Double(v.location.x / w)
                let clickedFreq = Int((leftEdge + fract * span).rounded())
                viewModel.setFrequency(clickedFreq)
            })
```

替换为:

```swift
            .contentShape(Rectangle())
            // Tap-to-QSY only: SpatialTapGesture ignores drags/swipes,
            // so scrolling across the waterfall can never QSY (analysis §2.6).
            .gesture(SpatialTapGesture().onEnded { value in
                let fract = Double(value.location.x / w)
                let clickedFreq = Int((leftEdge + fract * span).rounded())
                viewModel.setFrequency(clickedFreq)
            })
```

- [ ] **Step 2: 编译**

Run: `cd FT710Mobile && xcodebuild build -project FT710Mobile.xcodeproj -scheme FT710Mobile -destination 'generic/platform=iOS' -configuration Debug CODE_SIGNING_ALLOWED=NO -quiet 2>&1 | tail -5`
Expected: `BUILD SUCCEEDED`

- [ ] **Step 3: Commit**

```bash
git add FT710Mobile/Sources/UI/WaterfallView.swift
git commit -m "Waterfall: tap-only QSY via SpatialTapGesture (iOS)

DragGesture(minimumDistance: 0) turned every swipe into a QSY;
taps still tune, drags are now ignored."
```

---

### Task 5: scenePhase 强制释放 + 首屏假开机

**Files:**
- Modify: `FT710Mobile/Sources/App/FT710MobileApp.swift`
- Modify: `FT710Mobile/Sources/Model/RadioState.swift:40`

- [ ] **Step 1: FT710MobileApp 加 scenePhase**

第 7-9 行:

```swift
    @AppStorage("serverHost") private var savedHost: String = "radio.vlsc.net:8888"
    @State private var isLoggedIn: Bool = false
    @State private var viewModel: RadioViewModel?
```

改为:

```swift
    @AppStorage("serverHost") private var savedHost: String = "radio.vlsc.net:8888"
    @Environment(\.scenePhase) private var scenePhase
    @State private var isLoggedIn: Bool = false
    @State private var viewModel: RadioViewModel?
```

ContentView 分支(第 13-18 行)改为:

```swift
            if isLoggedIn, let vm = viewModel {
                ContentView()
                    .environmentObject(vm)
                    .preferredColorScheme(.dark)
                    .onAppear { UIApplication.shared.isIdleTimerDisabled = true }
                    .onDisappear { UIApplication.shared.isIdleTimerDisabled = false }
                    .onChange(of: scenePhase) { _, newPhase in
                        // SDD ch15 Layer 6 equivalent (pagehide/beforeunload):
                        // any backgrounding during TX forces release.
                        if newPhase != .active { vm.pttManager.forceRelease() }
                    }
            } else {
```

- [ ] **Step 2: RadioState.powerOn 默认值改 false**

`RadioState.swift` 第 40 行 `@Published var powerOn: Bool = true` → `@Published var powerOn: Bool = false`

(登录后 `LoginView` 路径本就走 `powerOnAsync` 连接;默认 false 消除"亮绿但未连接"的假开机,分析报告 §6。)

- [ ] **Step 3: 编译 + 单测**

Run: `cd FT710Mobile && xcodebuild build -project FT710Mobile.xcodeproj -scheme FT710Mobile -destination 'generic/platform=iOS' -configuration Debug CODE_SIGNING_ALLOWED=NO -quiet 2>&1 | tail -5`
Expected: `BUILD SUCCEEDED`

Run: `cd FT710Mobile && xcodebuild test -project FT710Mobile.xcodeproj -scheme PTTManagerTests -destination 'platform=iOS Simulator,name=iPhone 15' -quiet 2>&1 | tail -5`
Expected: 8/8 PASS

- [ ] **Step 4: Commit**

```bash
git add FT710Mobile/Sources/App/FT710MobileApp.swift FT710Mobile/Sources/Model/RadioState.swift
git commit -m "Force PTT release on backgrounding; fix fake power-on default (iOS)

scenePhase != active triggers idempotent forceRelease (SDD ch15
Layer 6 equivalent). RadioState.powerOn now defaults to false so the
power icon no longer shows connected before login."
```

---

### Task 6: 真机验证 + 文档标注

**Files:**
- Modify: `docs/IOS_APP_ANALYSIS.md`

- [ ] **Step 1: 真机部署**

用 Xcode 或命令行把 Debug 包装到真机(签名用 project.yml 里的 DEVELOPMENT_TEAM):

Run: `cd FT710Mobile && xcodebuild -project FT710Mobile.xcodeproj -scheme FT710Mobile -destination 'generic/platform=iOS' -configuration Debug`
或在 Xcode 里选真机 Run。服务端需运行中且电台已连接。

- [ ] **Step 2: 人工验证清单(逐条过,记录结果)**

1. 正常按住/松开 PTT:电台 TX/RX 跟随,松开后频谱/电平恢复;
2. 快速点按 PTT 10 次:每次都回 RX(原竞态复现场景);
3. TX 中按 Home/切 App:电台立即回 RX;
4. TX 中关 WiFi:服务端 dead-man switch 触发回 RX;重开网络后 App 重连正常;
5. 瀑布流上滑动浏览:频率不变;轻点:QSY 到点击位置;
6. web 端同时开着(多客户端):iOS PTT 行为不劣化;
7. 冷启动 App:电源图标不亮绿,点"连接电台"后才进主界面。

- [ ] **Step 3: 标注分析报告已修复项**

`docs/IOS_APP_ANALYSIS.md` 中:
- `### 2.1 PTT 释放竞态 → 电台可卡死在发射态` 标题行末加 ` ✅ 已修复(2026-07-20,spec ①)`;
- `### 2.2 iOS 无任何 PTT 看门狗 / 超时` 标题行末加 ` ✅ 已修复(2026-07-20,spec ①)`;
- `### 2.6 瀑布流误触即 QSY` 标题行末加 ` ✅ 已修复(2026-07-20,spec ①)`;
- §6 UI 层问题中 "首屏假开机" 条目(`- 首屏假开机:` 开头那行)行末加 ` ✅ 已修复(2026-07-20,spec ①)`。

- [ ] **Step 4: Commit**

```bash
git add docs/IOS_APP_ANALYSIS.md
git commit -m "Mark iOS P0 safety items fixed in analysis report (spec 1)"
```

---

## Self-Review 记录(计划完成后填写)

- Spec 覆盖:§2.1 PTTManager(Task 1-2)✓ §2.2 UI 接线/scenePhase(Task 3/5)✓ §2.3 瀑布流(Task 4)✓ §3 边界(press 拒绝/forceRelease 幂等,Task 2 测试 5/8)✓ §4 测试(Task 1-2,8 用例 ≥ spec 的 5 条)✓ §5 真机验证(Task 6,7 条 ⊇ spec 6 条)✓ §6 文档同步(Task 6 Step 3)✓ §1.4 首屏(Task 5)✓
- 类型一致性:`PTTManager(Phase/isTX/press/release/forceRelease/watchdogInterval/maxRetries)` 在 Task 1 stub、Task 2 实现、Task 3 接线、Task 5 App 中一致;`makePTTManager` 只在 RadioViewModel 出现一次。
- 占位符:无。
