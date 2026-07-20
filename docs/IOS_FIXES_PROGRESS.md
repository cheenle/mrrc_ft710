# FT710Mobile iOS 修复进度核实记录

**核实日期**: 2026-07-20(替代 2026-07-14 旧版进度报告)
**核实方法**: 逐项对照旧版(2026-07-14)进度报告的"已修复/待办"声称与当前代码真相,全部经实际 Read 核对并附 file:line 证据;权威基准为 `docs/IOS_APP_ANALYSIS.md`(2026-07-20 深度审计)。
**结论速览**: 5 项声称中,1 项属实且超出预期(Opus C 桥),1 项半完成且说法错误(PTT 统一),1 项旧标"待办"实际已完成(音频会话),2 项部分完成或毫无进展(错误处理、单元测试)。

---

## 核实总表

| # | 事项 | 旧文档声称 | 核实结论 | 关键证据 |
|---|------|-----------|----------|----------|
| 1 | Opus C 桥 | ✅ 已完成;libopus 链接⏳待办 | **属实且超出**: 桥完整、libopus 已链接进工程、RX 链路真的在解码 Opus | 见 §1 |
| 2 | PTT 按钮统一 | ✅ 已完成(删 PTTButtonView,统一 PTTBar) | **半完成且说法错误**: 三份实现并存,活的是第三份内联实现;释放竞态未修 | 见 §2 |
| 3 | 音频会话统一 | ⏳ 待办 | **实际已完成**: AudioSessionManager 统一 playAndRecord | 见 §3 |
| 4 | 错误处理 | ⏳ 待办 | **部分完成**: alert 机制在,但 `.audioError` 通知没人接 | 见 §4 |
| 5 | 单元测试 | ⏳ 待办 | **仍是 0**: 未接入工程、API 全错、断言必败 | 见 §5 |

---

## 1. Opus C 桥 — 声称✅ → 属实且超出

**旧声称**: "Created C-bridge wrapper for libopus… iOS app can now encode/decode Opus **if libopus is linked**"(并把 "Link libopus in Xcode" 列为 P0 待办)。

**代码真相**: 桥不仅存在,libopus 链接也已完成,RX 链路真实在用:

- C 桥完整: `FT710Mobile/Sources/Audio/OpusBridge.c:15-31`(`my_create_encoder`,28kbps CBR)、`:43-48`(`my_opus_encode`)、`:50-61`(`my_create_decoder`)、`:73-78`(`my_opus_decode`),头文件 `OpusBridge.h:18-27` 声明齐全。
- Swift 侧经 `@_silgen_name` 绑定: `OpusDecoder.swift:42-49`、`OpusEncoder.swift:43-50`。
- **libopus 已链接进工程**(旧文档的最大待办项,实际已做): `FT710Mobile/project.yml:41-43` 配置了 `HEADER_SEARCH_PATHS`、`LIBRARY_SEARCH_PATHS`、`OTHER_LDFLAGS: "-lopus"`;静态库在 `Sources/Audio/opus-ios/lib/libopus.a`。
- **RX 真的在解码 Opus**: `AudioPlaybackManager.swift:110-128` 按帧首字节 tag 分发,0x01 走 `opusDecoder.decode()`(`:114`)→ `processPCM` 播放,0x00 走 PCM 直通。

**遗留(不影响"已完成"结论,但是已知缺陷)**:

- TX 方向编码链路是死代码: `AudioCaptureManager.swift:20` `useOpus: Bool = false`,全项目无置 true 路径。
- `OpusBridge.h:13-15` 自定义错误码与真实 libopus 不符(真实 `OPUS_BAD_ARG = -1`、`OPUS_INVALID_STATE = -6`;桥里 -1 写成 INVALID_STATE),当前无功能影响,埋雷。
- `OpusDecoder.swift:31-32` / `OpusEncoder.swift:32-33` 存在指针逃逸 `withUnsafeBytes` 闭包的 UB 写法。

详见 `docs/IOS_OPUS_INTEGRATION.md`。

## 2. PTT 按钮统一 — 声称✅ → 半完成且说法错误

**旧声称**: "Removed redundant `PTTButtonView` logic, unified on `PTTBar`. Single PTT interface, no duplication."

**代码真相**: `PTTButtonView` 没有删,`PTTBar` 也不是被统一到的目标——三份 PTT 实现并存,真正活着的是第三份:

- `FT710Mobile/Sources/UI/PTTButtonView.swift` 文件仍在(无调用点,死代码)。
- `PTTBar` / `PTTPressStyle` 仍在 `ContentView.swift:269-307`(同样无调用点,死代码)。
- **活的 PTT 是 `ContentView.swift:219-235` 的内联实现**: `DragGesture(minimumDistance: 0)`,`onChanged` 里 `txStatus == 0` 才 `setPTT(true)`(`:230`),`onEnded` 里 `txStatus > 0` 才 `setPTT(false)`(`:232-234`)。
- **PTT 释放竞态未修**: `onEnded` 的条件判断依赖服务端回显,WAN 延迟下快速点按时 `ptt:false` 会被静默丢弃,电台可卡死在发射态(分析报告 §2.1)。这正是 spec ① 的头号修复对象。

**结论**: "单 PTT 界面"在视觉层面成立(只有一个可见按钮),但"删除冗余、统一实现"的声称不成立,且安全性问题原样保留。

## 3. 音频会话统一 — 声称待办 → 实际已完成

**旧声称**: "Update `AudioPlaybackManager` and `AudioCaptureManager` to use `.playAndRecord` consistently."(P1 待办)

**代码真相**: 已统一,且收口到单一管理器:

- `AudioSessionManager.swift:16-23` `configureForTransceiver()`: 统一 `.playAndRecord` + `.voiceChat` 模式,选项 `.defaultToSpeaker` / `.allowBluetooth` / `.allowBluetoothA2DP`,IO buffer 5ms。
- RX 侧 `AudioPlaybackManager.swift:185-192` `configureSession()` 调用 `AudioSessionManager.shared.configureForTransceiver()`;TX 侧共用同一 session(采集引擎不另配 category)。
- 旧文档担心的 RX/TX 切换重配问题因此不存在(单一 playAndRecord 会话常驻)。

**遗留**: 未设 `preferredSampleRate(48000)`(`AudioSessionManager.swift:16-23`),叠加 TX 重采样拒绝上采样(`AudioCaptureManager.swift:157`),蓝牙/44.1kHz 路由下 TX 变调(分析报告 §4.1);`handleAudioRouteChange`/`isBluetoothActive`(`AudioSessionManager.swift:26-37`)无调用点(死代码)。

## 4. 错误处理 — 声称待办 → 部分完成

**旧声称**: "Add user-facing error alerts for connection/audio failures."(P1 待办)

**代码真相**: alert 机制已建成并接入 UI,但音频错误通知链路断在最后一公里:

- 已有: `RadioViewModel.swift:17-20` 定义 alert 状态,`:195-210` `showError`/`handleAudioError`/`handleConnectionError`;`ContentView.swift:16-21` 把 `ErrorAlertView` 接入主视图;控制通道错误有转发(`RadioViewModel.swift:411-416` `connection.ctrl.onError` → alert)。
- **断点**: `setupErrorObservers()`(`RadioViewModel.swift:182-192`)负责监听 `.audioError` 通知,但**从未被调用**(`init` 在 `:24-28`,只调了 `bindSockets()`)。而 `.audioError` 通知确实有发送方: `AudioPlaybackManager.swift:94`(引擎启动失败)、`AudioCaptureManager.swift:89-90`(麦克风启动失败)——发出后无人接收,音频错误永远不会弹出 alert。
- 另有: `ErrorAlertView` 的"重新连接/重试"按钮没有绑定动作(分析报告 §6);服务端 `"error"` 消息在主界面被吞(`RadioViewModel.swift:440-441` 只写 offState 才展示的 `connectionError`)。

## 5. 单元测试 — 声称待办 → 仍是 0(有效覆盖率 0%)

**旧声称**: "Write tests for `OpusDecoder`, `OpusEncoder`, `RadioState`."(P2 待办)

**代码真相**: `Tests/FT710MobileTests/` 下有两个测试文件,但它们不构成任何有效覆盖:

- **测试未接入工程**: `project.yml` 全文无 test target(仅一个 `FT710Mobile` application target,`project.yml:24-43`);`IOS_BUILD_GUIDE.md` 教的 `xcodebuild test` 必然失败。
- **`RadioViewModelTests.swift` API 全错,编译即失败**: 使用了 `state.frequency`/`state.mode == .LSB`/`state.bandwidth`(`:26-28`)、`incrementFrequency`/`decrementFrequency`(`:78-86`)、`setMode(.USB)` 枚举(`:91`,真实签名是 `setMode(_ modeName: String)`)、`setBandwidth`(`:103`)、`toggleMode`(`:96`)、`toggleAGCAuto`(`:128`)、`setVolume`(`:135`)、`toggleNotchFilter`(`:149`)、`setDSPNoiseReduction`(`:156`)——以上 API 在当前 `RadioViewModel`/`RadioState` 中**全部不存在**。断言也必败: `testInitialState` 断言 `powerOn == false`(`:21`),但 `RadioState.swift:40` 默认 `true`;`testPTTActivation` 断言 `setPTT(true)` 后 `txStatus == 1`(`:110-112`),但 setter 只发命令不本地改状态。
- **`OpusCodecTests.swift` 符号名全错**: `:71-127` 调用 `create_encoder`/`destroy_encoder`/`create_decoder`/`destroy_decoder`/`opus_encode`/`opus_decode`,C 桥实际符号带 `my_` 前缀(`OpusBridge.h:18-27`),编译即失败。断言同样必败: `testOpusEncoderEncode`(`:13-25`)喂 160 个样本给 48kHz/20ms(960 样本)编码器,`opus_encode` 必返回 `OPUS_BAD_ARG`,`encode` 返回 nil 与 `XCTAssertNotNil` 冲突;`testOpusDecoderDecode`(`:43-54`)对伪造的 "Opus" 字节断言解码非 nil,实际解码必失败返回 nil。
- 网络/音频/PTT/频谱四条关键路径零覆盖。

---

## 下一步

1. **spec ① iOS 发射安全修复 — 已批准,待实施**(最高优先级)。
   - 设计: `docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md`(方案 A: 纯 SwiftUI + PTTManager 状态机)
   - 计划: `docs/superpowers/plans/2026-07-20-ios-ptt-safety.md`
   - 覆盖: 本记录 §2 的 PTT 释放竞态、看门狗/scenePhase 后台保护、瀑布流误触 QSY、首屏假开机。
2. **spec ② 连接生命周期 + 崩溃修复 — 待设计**。
   - 覆盖: 认证失败路径(1006→auth-check→回登录页)、`reconnect()` 凭据 bug(`RadioViewModel.swift:72` 拿 token 当密码)、密码锁死(`FT710MobileApp.swift:20-25`)、`playerNode` 重复 attach(`AudioPlaybackManager.swift:83` vs `:98-105`)、`installTap` 重试(`AudioCaptureManager.swift:77-84`)。
3. 后续 backlog(分析报告 §9): mem 频道协议对齐、TX 重采样、RX jitter buffer、错误通知接线(本记录 §4 断点)、删死代码、测试重建(接入工程 + 真实 API)、TX Opus 启用(见 `docs/IOS_OPUS_INTEGRATION.md`)。

---

**核实人**: Kimi Code(逐项 Read 核对)
**旧版处理**: 2026-07-14 旧版进度报告结论已全部过期,本文档整体替代。
