# FT710Mobile iOS App — 现状总结

**基准日期**: 2026-07-20(替代 2026-07-14 旧版,旧版结论已全部过期)
**权威来源**: 本文档是 `docs/IOS_APP_ANALYSIS.md`(2026-07-20 深度审计)的摘要视图;任何细节冲突以分析报告为准。报告中每条结论均经实际代码核对并附 file:line 证据。
**项目**: Yaesu FT-710 远程控制系统的 iOS 客户端,位于 `FT710Mobile/`(SwiftUI,iOS 17+),服务端为仓库根目录的 `server.py` 等 Python FastAPI 模块。

---

## 一句话定位

FT710Mobile 是通过 4 路 WebSocket 连接 FT-710 服务端的 iOS 远程控制客户端:Happy path 协议对接健康(控制、RX 音频、频谱可用),但 PTT 安全、认证失败路径存在 P0 级缺陷,大量功能"写了代码但没接线",工程健康度差(测试 0 覆盖、14/24 UI 文件是死代码)。

---

## 功能清单

### ✅ 可用

- **基础控制**:频率设定/步进、模式、滤波、DSP 开关(NR/NB/AN/COMP)、VFO-A/B、SPLIT、天调开关、各类增益(AF/RF/功率/麦克)——`{"type":"set"}` 协议两端逐字段核对匹配。
- **RX 音频**:服务端 Opus 编码(48kHz/20ms,tag 0x01)广播,iOS `OpusDecoder` 经 C 桥调 libopus 真实解码播放(`AudioPlaybackManager.swift:110-128`);PCM(tag 0x00)回退路径同在。
- **频谱/瀑布流**:1701B 帧解析、瀑布图 + FFT 线显示;S-meter 标定与服务端一致。

### 🟡 半残(有 UI/代码,行为错误或场景受限)

- **存储频道(mem)**:服务端 `null` 空槽导致 iOS 整体解析失败(列表常空)、键名 `label` vs `name` 错位、槽位 6 vs 10 不一致、`saveMemory` 只写本地从不发 `memSave`、recall 未用服务端原子 `memRecall`——子协议全线脱节(分析报告 §3.1)。
- **TUNE 按钮**:主界面 TUNE 发的是 `"tuner"`(天调开关)而非 `"tune"`(TX2 载波调谐),无法从主 UI 发起调谐(分析报告 §3.2)。
- **录音**:`toggleRecording()` 翻转的标志位无任何读取者;真正实现录音的 `startRecording/stopRecording` 无调用方,且 `makeWAV` 头部字段错位,产出的 WAV 打不开(分析报告 §4.3)。
- **TX 音频(特定路由变调)**:重采样函数拒绝上采样(`AudioCaptureManager.swift:157`),蓝牙 HFP(8/16kHz)或 44.1kHz 路由下 TX 音高上移甚至不可辨;内置麦克风 48kHz 路由下 TX PCM 可用(分析报告 §4.1)。

### ❌ 缺失

- **PTT 看门狗**:无释放后验证重发、无最大 TX 时长;`config.py:289 PTT_SAFETY_TIMEOUT` 服务端也从未实现(分析报告 §2.2)。
- **后台保护**:无 scenePhase 监听、无 `UIBackgroundModes`,App 进后台 4 条 socket 全部挂起且无前台重连钩子(分析报告 §2.2、§6)。
- **RX jitter buffer / PLC**:每帧到达即播放,网络抖动后音频永久滞后越积越多;丢包即爆音(web 端有 220ms 预缓冲 + 800ms 上限的 jitter buffer,分析报告 §4.2)。
- **TX Opus**:`useOpus = false` 且无置 true 路径,TX 恒为 PCM ~768kbps,Opus 编码链路整体死代码(详见 `docs/IOS_OPUS_INTEGRATION.md`)。

---

## 质量现状

- **测试有效覆盖率 0%**:两个测试文件未接入 `project.yml`(无 test target);`RadioViewModelTests.swift` 调用的 API 全部不存在,编译即失败;`OpusCodecTests.swift` 调用的 C 符号名错误且断言必败。网络/音频/PTT/频谱四条关键路径零覆盖(分析报告 §7)。
- **死代码**:24 个 UI 文件 14 个无调用点(含 `PTTButtonView.swift`、`PTTFooter.swift`、`MainRXView.swift` 等整套组件);逻辑层另有 `setupErrorObservers()`、`useOpus`、`isRecording` 等 10 处死代码。两套实现并存且语义已漂移,误导后续维护(分析报告 §8)。
- **文档腐化**:`FT710Mobile/CLAUDE.md`、`README.md`、`docs/ARCHITECTURE.md` 描述的是另一个项目(SunsdrMobile:/WSCTRX 端点、cmd:val 文本协议、端口 8889),均不可信(分析报告 §1)。

---

## 风险 Top 5

| # | 风险 | 一句话 | 分析报告 |
|---|------|--------|----------|
| 1 | PTT 释放竞态 | `onEnded` 只在 `txStatus > 0` 时发 `ptt:false`,WAN 延迟下快速点按可致电台卡死发射态 | §2.1 |
| 2 | 认证失败死循环 | 4001 永远到不了客户端;`reconnect()` 拿会话 token 当密码重新登录,服务端重启后 App 永久卡死 | §2.3 |
| 3 | 崩溃隐患 | `playerNode` 重复 attach、`installTap` 重试,两处确定性 NSException 路径(reconnect/power 循环可达) | §2.5 |
| 4 | 瀑布流误触 QSY | `DragGesture(minimumDistance: 0)` 直接 `setFrequency`,任何滑动/误触都改频率,iOS 独有发射安全风险 | §2.6 |
| 5 | 密码锁死 | `onLogin` 无条件置 `isLoggedIn = true` 并把密码写 Keychain,输错密码只能删 App 重装 | §2.4 |

---

## 进行中工作

- **spec ① iOS 发射安全修复 — 已批准,待实施**。
  - 设计文档: `docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md`(方案 A:纯 SwiftUI + PTTManager 状态机)
  - 实施计划: `docs/superpowers/plans/2026-07-20-ios-ptt-safety.md`
  - 范围: PTT 释放竞态、看门狗/scenePhase 后台保护、瀑布流误触 QSY + 首屏假开机;服务端零改动。
- **spec ② 连接生命周期 + 音频引擎崩溃修复 — 待设计**。
  - 范围: 认证失败路径(1006→auth-check→回登录页)、`reconnect()` 凭据 bug、密码锁死、`playerNode`/`installTap` 崩溃隐患(分析报告 §2.3-§2.5)。

---

## 文档地图

| 文档 | 内容 | 可信度 |
|------|------|--------|
| `docs/IOS_APP_ANALYSIS.md` | **权威基准**: 2026-07-20 深度审计,全部结论附 file:line 证据 | ✅ 可信 |
| `docs/IOS_APP_SUMMARY.md` | 本文档: 现状总结(功能/质量/风险/进行中工作) | ✅ 可信 |
| `docs/IOS_FIXES_PROGRESS.md` | 修复进度核实记录: 2026-07-14 旧声称 vs 代码真相 | ✅ 可信 |
| `docs/IOS_OPUS_INTEGRATION.md` | Opus 集成现状与 TX 启用指南 | ✅ 可信 |
| `docs/IOS_BUILD_GUIDE.md` | 构建指南;注意其 `xcodebuild test` 指引当前不可用(测试未接入工程) | ⚠️ 部分过期 |
| `docs/IOS_TESTING_GUIDE.md` | 测试指南;描述的测试套件未接入工程且 API 全错 | ⚠️ 部分过期 |
| `docs/IOS_APP_FIX_GUIDE.md` | 2026-07-14 旧修复指南,基于过期结论 | ❌ 仅历史参考 |
| `docs/superpowers/specs/2026-07-20-ios-ptt-safety-design.md` | PTT 安全修复设计(spec ①,已批准) | ✅ 可信 |
| `docs/superpowers/plans/2026-07-20-ios-ptt-safety.md` | PTT 安全修复实施计划 | ✅ 可信 |
| `FT710Mobile/CLAUDE.md` / `README.md` / `docs/ARCHITECTURE.md` | 描述的是 SunsdrMobile(另一个项目) | ❌ 已腐化,不可信 |
