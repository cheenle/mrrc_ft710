# FT710Mobile iOS App — 测试指南

**更新日期**: 2026-07-20(全文重写;旧版描述的"测试覆盖范围"与"覆盖率目标"全部不存在)
**结论先行**: 当前工程**没有任何可运行的测试**,有效覆盖率 0%。第一个可跑的测试 target(PTTManagerTests)随 spec ① 落地,状态**待实施**。

---

## 1. 现状(截至 2026-07-20)

### 工程里没有 test target

`FT710Mobile/project.yml` 只声明了 app target,没有任何 unit-test target;生成的 pbxproj 里 `FT710MobileTests` 出现 0 次。因此旧文档教的 `xcodebuild test -scheme FT710Mobile ...` 必然失败——不是测试坏了,是测试根本没接进工程。

### 两个旧测试文件已腐烂(勿直接接入工程)

`FT710Mobile/Tests/FT710MobileTests/` 下两个文件:

- **`RadioViewModelTests.swift` — 编译即失败**:它针对一套不存在的 API 写成——`RadioViewModel(serverHost:password:)` 构造器、`state.frequency` / `state.mode == .LSB` 枚举 / `state.bandwidth`、`incrementFrequency` / `decrementFrequency` / `toggleMode` / `setPTT` / `setAFGain` / `toggleAGCAuto` / `setVolume` / `setSquelch` / `toggleNotchFilter` / `setDSPNoiseReduction`、`showError` / `handleAudioError` / `handleConnectionError` 等,在真实代码里全部不存在。断言逻辑也错:它假设 setter 会本地改状态,而真实 setter 只是发 WebSocket 命令、状态靠服务端回显更新——即使能编译,断言也必然失败。
- **`OpusCodecTests.swift` — 编译即失败,且本质上只能在真机跑**:调用的 C 符号 `create_encoder` / `create_decoder` / `opus_encode` / `opus_decode` / `destroy_*` 不存在(实际桥接符号是 `my_create_encoder` 等,见 `Sources/Audio/OpusBridge.h`);160 个样本喂 48kHz 编码器必然返回 BAD_ARG(48kHz/20ms 一帧是 960 样本);且它必须链接 libopus,而 `libopus.a` 仅 arm64 真机 slice——模拟器上链接都过不了。

### 覆盖缺口

网络、音频、PTT、频谱四条关键路径零覆盖,详细清单见 §5。

## 2. 第一个可跑的测试:PTTManagerTests(**待实施**)

spec ①(iOS 发射安全)的 Task 1 会新增一个最小 test target。设计与计划:

- [spec 设计](superpowers/specs/2026-07-20-ios-ptt-safety-design.md)
- [实施计划 Task 1](superpowers/plans/2026-07-20-ios-ptt-safety.md)

设计要点(计划原文):

- 只编译 `Sources/PTT` + `Tests/FT710MobileTests/PTTManagerTests.swift`,**不链接 libopus、不依赖 app target** → 模拟器可跑;
- 两个腐烂的旧测试文件不进工程(它们的去留由 spec ② 的测试体系重建处理);
- 8 个用例:press 未连接拒绝 / 乐观 keyed / 快速 press→release 必发 TX0(竞态回归)/ 回显 RX 不重发 / 看门狗重发至回显 / 重试耗尽上报 onStuckTX / 看门狗期间 press 取消重试 / forceRelease 幂等。

运行方式(**spec ① Task 1 落地后才可用**):

```bash
cd FT710Mobile
xcodegen                                          # 重新生成工程,使 PTTManagerTests target/scheme 生效
xcodebuild -list -project FT710Mobile.xcodeproj   # Schemes 列表应含 FT710Mobile 与 PTTManagerTests
xcodebuild test -project FT710Mobile.xcodeproj \
  -scheme PTTManagerTests \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

模拟器名不存在时:`xcodebuild -showdestinations -project FT710Mobile.xcodeproj -scheme PTTManagerTests` 挑一个已装的替换。

## 3. 如何写新测试:硬件无关原则

本项目测试腐烂的根因是"直接 `@testable import` 整个 app + 碰真实单例 / 真实 C 库"。新测试必须遵守:

1. **依赖注入,不碰硬件**:被测对象不直接持有 `AVAudioEngine` / `URLSession` / `AVAudioSession`,外部依赖以闭包(或协议)注入。范本是 PTTManager:`sendPTT` / `sendTXAudioStop` / `setTXAudioActive` / `serverTXStatus` / `isCtrlConnected` / `onStuckTX` 全部注入;测试里用一个 Harness 类记录调用、喂假回显(`echoStatus` / `connected`),完全不碰网络与音频。
2. **时间参数做成变量**:看门狗间隔之类的时间常量用 var(如 `watchdogInterval`),测试里设 0.01s 级,避免慢测试。
3. **测试 target 只收编被测源文件**:像 PTTManagerTests 只收 `Sources/PTT` 一样,每个测试 target 在 `project.yml` 里按需列 `sources`,避免把 libopus / 硬件依赖链进来——这也是模拟器能跑的前提。
4. **优先测纯逻辑**:协议解析(stateUpdate 映射、mem 频道 null 解析)、常量表(mode / band / filter 换算)、频率步进计算、频谱帧解析(1701B → bins)这类输入输出确定的代码,投入产出比最高。

新测试文件放 `Tests/FT710MobileTests/` 下,并在 `project.yml` 对应 target 的 `sources` 中显式列出(yaml 片段参照实施计划 Task 1 Step 1),改完重跑 `xcodegen`。

## 4. 人工真机验证(单测替代不了的部分)

以下路径涉及真实硬件 / 系统行为,只能"真机 + FT-710 + 服务端"人工验证:

- **音频链路**:RX 播放(PCM / Opus)、TX 采集与变调、蓝牙路由切换、音频引擎启停(含 §2.5 两处崩溃隐患的复现验证);
- **PTT 实际发射**:快速点按必回 RX、TX 中切后台 / 来电、TX 中断网后服务端 dead-man switch 兜底(清单见 spec ① §5,共 7 条);
- **频谱 / 瀑布**:渲染帧率、轻点 QSY 落点精度、滑动不改频率;
- **认证全流程**:正常登录、密码错误、服务端重启后的恢复表现。

执行时机:改动触碰 `Sources/Audio`、`Sources/Spectrum`、PTT 手势接线、认证 / 重连逻辑时,单测通过之外必须过对应的真机清单。

## 5. 关键未测路径清单(按风险排序)

| 路径 | 风险 | 可单测性 |
|---|---|---|
| 认证与重连:login → cookie → `?token=`;4001 / 1006 分支;`reconnect()` 凭据(分析 §2.3 的 token-当密码 bug) | 服务端重启后 App 永久卡死 | 高(HTTP / WS 层注入 mock 后可测) |
| PTT 状态机 | 电台卡死在发射态(P0) | 高(spec ① 落地后由 PTTManagerTests 覆盖状态机;真机覆盖硬件路径) |
| 音频管线:Opus 解码、jitter buffer(待实现,分析 §4.2)、TX 重采样(§4.1)、引擎启停(§2.5 崩溃) | 无声 / 变调 / 崩溃 | 中(解码与重采样可纯逻辑测;引擎部分只能真机) |
| 频谱帧解析:1701B 帧 → 瀑布 / FFT | 花屏 / 错位 | 高(喂固定帧字节断言输出) |
| stateUpdate / applyFullState 映射、mem 频道 null 解析(§3.1) | 状态不更新 / 频道列表永远为空 | 高(纯 JSON → 状态断言) |

测试体系整体重建属 spec ② / P2 范围,路线见 [IOS_APP_FIX_GUIDE.md](IOS_APP_FIX_GUIDE.md)。

## 相关文档

- [IOS_APP_ANALYSIS.md](IOS_APP_ANALYSIS.md) §7 — 测试与构建配置问题清单
- [IOS_BUILD_GUIDE.md](IOS_BUILD_GUIDE.md) — 构建指南(含模拟器不可行的原因)
- [IOS_APP_FIX_GUIDE.md](IOS_APP_FIX_GUIDE.md) — 修复路线图
