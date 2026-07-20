# FT710Mobile iOS App — 修复路线图

**基准**: [IOS_APP_ANALYSIS.md](IOS_APP_ANALYSIS.md)(2026-07-20 深度审计,所有问题附 file:line 证据),本路线图以其 §9 优先级表为骨架
**更新日期**: 2026-07-20(全文重写,替代 2026-07-14 旧版。旧版基于错误结论——Opus "未实现需选型"、PTTBar/PTTButtonView 二选一、bitcode 优化等——已全部作废)
**阅读方式**: 这是路线图,不是逐行修补手册。每项给状态、一句话方案/问题、出处;具体实现以 spec/plan 或后续设计为准。

## 状态约定

| 状态 | 含义 |
|---|---|
| 待实施(spec ①) | 设计与计划已批准,照计划执行即可 |
| 待设计(spec ②) | 问题已定位,设计文档尚未编写 |
| 待排期 | 已识别,无 spec,按 P1 → P2 顺序排期 |
| 已完成 | 已落地并验证 |

---

## P0 — 发射安全(spec ①,待实施)

发射安全三项 + 首屏假开机一项。spec 与实施计划已批准(2026-07-20):

- 设计: [docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md](superpowers/specs/2026-07-20-ios-ptt-safety-design.md)
- 计划: [docs/superpowers/plans/2026-07-20-ios-ptt-safety.md](superpowers/plans/2026-07-20-ios-ptt-safety.md)(6 个 Task,TDD;服务端零改动)

| 问题 | 一句话方案 | 出处 |
|---|---|---|
| PTT 释放竞态:松开瞬间 `txStatus` 回显未到 → `ptt:false` 被静默丢弃,电台持续发射 | 新建 `PTTManager` 状态机(闭包注入、可单测):release 无条件发 TX0,UI 改读乐观 `phase` 而非服务端回显 | 分析 §2.1;spec §2.1 |
| 无 PTT 看门狗、无后台保护:手势被系统中断/切后台时无人兜底 | release 后 500ms×3 看门狗校验服务端回显、仍 TX 则重发并上报;`scenePhase != .active` 时 `forceRelease()`;release 同时发 `'s:'` TX 音频收尾帧 | 分析 §2.2;spec §2.1/§2.2 |
| 瀑布流误触即 QSY:`DragGesture(minimumDistance: 0)` 把任何滑动都变成 setFrequency | 换 `SpatialTapGesture`,只认轻点,拖动被天然过滤 | 分析 §2.6;spec §2.3 |
| 首屏假开机(顺手修):`powerOn` 默认 true,电源图标亮绿但实际未连接 | 默认值改 false | 分析 §6;spec §1.4 |

实施后按 spec §5 / 计划 Task 6 做真机验证(快速点按、TX 中切后台、断网兜底等 7 条),并在分析报告对应节标注"已修复"。

## P0 — 可用性 + 崩溃(spec ②,待设计)

问题已在分析报告中定位,spec ② 尚未编写:

| 问题 | 出处 |
|---|---|
| 认证失败路径断裂:服务端在 `ws.accept()` 之前 close(4001),按 ASGI 行为实际变成 HTTP 403 握手拒绝,**4001 永远到不了客户端**;iOS 只在 `didCloseWith` 查 4001 → 死代码,实际每 3s 无限重连 4 条 socket 且无任何"认证过期"提示;`reconnect()` 拿登录成功后已被会话 token 覆盖的 `connection.password` 当密码重新登录 → 401 → 永远无法恢复,只能杀 App | 分析 §2.3 |
| 密码锁死:`onLogin` 无条件 `isLoggedIn = true`,错误密码已写 Keychain,App 内无改密码入口 → 只能删 App 重装 | 分析 §2.4 |
| 两处确定性崩溃隐患(建议真机验证):`AudioPlaybackManager.stop()` 不 detach playerNode,`start()` 每次 attach → 重复 attach 抛 NSException;`AudioCaptureManager` 引擎 `start()` 失败后 `prepare()` 对同一 inputNode 重复 installTap → NSException;全 App 无 `requestRecordPermission` 调用 | 分析 §2.5 |

参考实现:web 端对 1006 的成熟处理(auth-check 后决定重连或回登录页,`static/ft710_main.js:84-90`)。

## P1 — 功能(待排期)

协议不一致与音频管线缺陷,特征都是"UI/代码写了但没接线或实际残废":

| 问题 | 涉及文件 | 出处 |
|---|---|---|
| mem 频道协议全线脱节:服务端用 `null` 补空槽,Swift 遇任一 NSNull 整体解析失败(只要有一个空槽,频道列表永远为空);键名服务端 `label`、iOS 读 `name`;槽位服务端 6、iOS 写死 10;`saveMemory()` 只写本地数组从不发 `memSave`,重新登录即丢;recall 未用服务端原子 `memRecall`(含 SSB 边带二次校频),recall 后频率可能偏移 | `RadioViewModel.swift:431,443`、`MemoryChannelsManager.swift:7,27`、`RadioViewModel.swift:239-241` | 分析 §3.1 |
| TUNE 语义错误:主界面 TUNE 按钮发 `"tuner"`(天调开关)而非 `"tune"`(TX2 载波 + AC003 调谐),主 UI 无法发起调谐 | `ContentView.swift:236` → `RadioViewModel.toggleTuner()` | 分析 §3.2 |
| TX 重采样拒绝上采样:`guard inRate > outRate else { return input }`,蓝牙 HFP / 44.1k 路由下 TX 变调甚至不可辨 | `AudioCaptureManager.swift:157`;对照 web `tx_capture_worklet.js:82-97` | 分析 §4.1 |
| RX 无 jitter buffer / 无 PLC:每帧到达即 scheduleBuffer,网络抖动后积压音频永久滞后、越积越多;丢包即爆音 | `AudioPlaybackManager.swift:163-171`、`OpusDecoder.swift:32`;对照 web `rx_worklet_processor.js:33-35` | 分析 §4.2 |
| 错误消息展示未接线:服务端 `"error"` 消息在主界面被吞,`setupErrorObservers()` 从未被调用,`ErrorAlertView` 的"重新连接/重试"按钮没有绑定动作 | `RadioViewModel.swift:440-441`、`:182-192`、`ErrorAlertView.swift` | 分析 §6 |

修复时一并过分析 §3.2 的小问题表(`setIPO` 字段名服务端无分支、A=B 方向与服务端相反、`modeNumToName` 缺 DATA-FM-N、squelch 量程三处不一致)。

## P2 — 工程健康(待排期)

| 事项 | 内容 | 出处 |
|---|---|---|
| 死代码清理 | 24 个 UI 文件 14 个是死代码(内含另一套 PTT/步进/AGC 实现,语义已漂移,误导维护),grep 全库确认无调用点;完整清单含逻辑层死代码见分析 §8 | 分析 §8 |
| 测试体系重建 | 工程无 test target,两个旧测试文件不可编译且断言逻辑错误,有效覆盖率 0%;按 [IOS_TESTING_GUIDE.md](IOS_TESTING_GUIDE.md) 重建 | 分析 §7 |
| 仪表标定对齐 | iOS 功率/SWR 全是线性近似,服务端用非线性标定表(`config.py:221-274`),同一时刻两端显示不同 | 分析 §5 |
| 构建配置 | `UIRequiredDeviceCapabilities = armv7`(iOS 17 仅 arm64);libopus.a 仅真机 slice → 模拟器不可构建;Resources 整目录打包带进 Info.plist 副本;`DEVELOPMENT_TEAM` 硬编码;陈旧产物 `SunsdrMobile.xcodeproj/` 入库 | 分析 §7 |
| 文档重写 | **docs/ 下三份(本文件、构建指南、测试指南)已重写完成(2026-07-20)**;`FT710Mobile/` 自带的 CLAUDE.md / README.md / docs/ARCHITECTURE.md 仍在描述另一个项目(SunsdrMobile),腐化未修,归 spec ② 范围 | 分析 §1 |

## 执行顺序建议

1. **spec ①(P0 安全)** — spec + plan 齐备,直接按 6 个 Task 执行;顺带把"测试 target 如何接入工程"的路蹚出来(最小 PTTManagerTests target)。
2. **spec ②(P0 可用性 + 崩溃)** — 待设计;建议范围:认证/密码路径、两处音频引擎崩溃、整体测试体系修复、`FT710Mobile/` 腐化文档重写。
3. **P1 功能** — mem 协议对齐与 TUNE 语义改动小、收益大,建议优先;音频管线两项(TX 重采样、RX jitter buffer)有 web 端成熟实现可对照。
4. **P2 健康** — 死代码清理宜早做(减少误读);构建配置与仪表标定可随 P1 顺带完成;测试覆盖在 spec ② 后持续补。

## 相关文档

- [IOS_APP_ANALYSIS.md](IOS_APP_ANALYSIS.md) — 全部问题的 file:line 证据与优先级总表(§9)
- [IOS_BUILD_GUIDE.md](IOS_BUILD_GUIDE.md) — 构建指南(2026-07-20 重写)
- [IOS_TESTING_GUIDE.md](IOS_TESTING_GUIDE.md) — 测试指南(2026-07-20 重写)
- spec ①: [设计](superpowers/specs/2026-07-20-ios-ptt-safety-design.md) / [实施计划](superpowers/plans/2026-07-20-ios-ptt-safety.md)
