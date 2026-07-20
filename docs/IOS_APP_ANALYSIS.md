# FT-710 iOS App (FT710Mobile) — 深度分析报告

**分析日期**: 2026-07-20(替代 2026-07-14 旧版,旧版结论已全部过期)
**分析方法**: 5 路并行代码审计(网络/音频/状态/UI/构建测试),所有结论经实际代码核对并附 file:line 证据;服务端对照 `server.py` / `radio_state.py` / `config.py`,web 端对照 `static/ft710_main.js` / `ft710_ui.js` / `modules/ptt_manager.js` / `rx_worklet_processor.js` / `tx_capture_worklet.js`
**状态**: 已完成

---

## 0. 总体结论

- **Happy path 协议对接健康**:4 路 WebSocket 端点(`/WSradio` `/WSaudioRX` `/WSaudioTX` `/WSspectrum`)、音频 1 字节 codec tag(0x00 PCM / 0x01 Opus)、1701B 频谱帧、48kHz/20ms 帧、`{"type":"set"}` 控制消息、`ft710_auth` cookie + `?token=` 认证——两端逐字段核对均匹配。
- **问题集中在三条线**:PTT 安全、认证失败路径、大量功能"写了 UI/代码但没接线"。
- **工程健康度差**:25 个 UI 文件 14 个是死代码;测试有效覆盖率 0%;`FT710Mobile/` 自带三份文档(CLAUDE.md/README.md/docs/ARCHITECTURE.md)已腐化成另一个项目(SunsdrMobile)的描述。

---

## 1. 实际架构与数据流

```
FT710MobileApp (登录页 → Keychain 密码 → RadioViewModel)
  └─ RadioViewModel (@MainActor, ViewModel/RadioViewModel.swift) 总协调器
      ├─ ConnectionManager → 4× WebSocketConnection (WSS, ?token= 认证, 3s 固定重连)
      │    ctrl:/WSradio  audioRX:/WSaudioRX  audioTX:/WSaudioTX  spectrum:/WSspectrum
      ├─ RadioState (applyFullState 逐键镜像服务端 to_dict;增量=同映射部分赋值)
      ├─ AudioPlaybackManager (RX: tag 分发 → OpusDecoder → vDSP → AVAudioPlayerNode @48kHz)
      ├─ AudioCaptureManager (TX: inputNode tap → 960样本/20ms 帧 → PCM tag 0x00)
      ├─ SpectrumProcessor (1701B 帧 → wf1 → 瀑布 UIImage + FFT 线)
      └─ MemoryChannelsManager (本地 10 槽数组)
```

认证流:POST `https://<host>/api/auth/login` → 取 `ft710_auth` cookie(`RadioViewModel.swift:148`)→ `updateCredentials(password: token)` 重建 4 条 socket(`ConnectionManager.swift:27-31`)→ `connectAll()`。

**注意**: `FT710Mobile/CLAUDE.md`、`README.md`、`docs/ARCHITECTURE.md` 描述的是另一个项目(SunsdrMobile:/WSCTRX 端点、cmd:val 文本协议、端口 8889、16kHz TX、512-bin 频谱),均不可信,以本报告为准。

---

## 2. P0 — 安全与崩溃级问题

### 2.1 PTT 释放竞态 → 电台可卡死在发射态
`ContentView.swift:230-234`: `onEnded` 只在 `txStatus > 0` 时发 `ptt:false`,而 `txStatus` 完全依赖服务端回显。WAN 延迟下快速点按:松开瞬间回显未到 → **ptt:false 被静默丢弃,电台持续发射**。web 端 `ft710_ui.js:889-897` 是无条件发送 + 本地乐观置零,iOS 两者皆无。对照 SDD 第 15 章 7 层防护,iOS 仅有残缺的 Layer 1/2。

### 2.2 iOS 无任何 PTT 看门狗 / 超时
web 端 `ptt_manager.js:20-57` 有释放后 500ms×3 验证重发 TX0、`:105-123` 有 `beforeunload`/`pagehide` 强制 RX;iOS 无 scenePhase 监听(`FT710MobileApp.swift` 全文无)、无最大 TX 时长、DragGesture 被系统手势/来电中断时 `onEnded` 可能不触发。服务端兜底(`server.py:1664-1673` 最后 ctrl 断开强制 RX、`1814-1825` TX-owner 断开强制 RX)仅在断连时生效且多客户端在线时失效;`config.py:289 PTT_SAFETY_TIMEOUT` 被 import 但**从未实现**。

### 2.3 认证失败路径断裂 → 服务端重启后 App 永久卡死
- 服务端在 `ws.accept()` **之前** close(4001)(`server.py:1627` 等),按 ASGI/uvicorn 行为实际变成 HTTP 403 握手拒绝,**4001 永远到不了客户端**。iOS 只在 `didCloseWith` 查 4001(`WebSocketConnection.swift:152`)→ 死代码;实际走 `didCompleteWithError` → 每 3s 无限重连 4 条 socket,无任何"认证过期"提示。web 端对 1006 有成熟处理(`ft710_main.js:84-90`:auth-check 后决定重连或回登录页)。
- `reconnect()`(`RadioViewModel.swift:72`)拿 `connection.password` 重新登录,但该字段登录成功后已被会话 token 覆盖(`:157`)→ 拿 token 当密码 → 401 → 永远无法恢复,只能杀 App。

### 2.4 密码输错即锁死
`FT710MobileApp.swift:20-25`: `onLogin` 无条件 `isLoggedIn = true`;错误密码已写 Keychain,下次启动自动登录照旧失败,App 内无改密码入口 → **只能删 App 重装**。

### 2.5 两处确定性崩溃隐患(静态分析,建议真机验证)
- `AudioPlaybackManager.stop()`(`AudioPlaybackManager.swift:98-105`)不 detach `playerNode`;`start()` 每次 `engine.attach(playerNode)`(`:83`)→ 重复 attach 抛 NSException。reconnect、powerOff/On 循环均可达。
- `AudioCaptureManager` 采集引擎 `engine.start()` 失败后 `enginePrimed` 保持 false,下次 `prepare()` 对同一 inputNode 重复 `installTap` → NSException(`AudioCaptureManager.swift:77-84`)。且全 App 无 `requestRecordPermission` 调用,麦克风被拒场景无处理。

### 2.6 瀑布流误触即 QSY
`WaterfallView.swift:70-74`: `DragGesture(minimumDistance: 0).onEnded` 直接 `setFrequency`,任何滑动/误触都改频率。web 端瀑布流无点击调谐。点到带外直接 QSY——iOS 独有的发射安全风险。

---

## 3. P1 — 协议不一致(功能实际残废)

### 3.1 存储频道(mem)子协议全线脱节
- 服务端用 `null` 补空槽(`server.py:173-178`,`MEM_CHANNEL_COUNT=6` 在 `config.py:293`);Swift 的 `as? [[String: Any]]` 遇任一 `NSNull` 整体返回 nil(`RadioViewModel.swift:431,443`)→ **只要有一个空槽,iOS 频道列表永远为空**(常态)。
- 键名:服务端 `label`,iOS 读 `name`(`MemoryChannelsManager.swift:27`)→ 名字永远回落 "CH1…"。
- 槽位:服务端 6,iOS 写死 10(`MemoryChannelsManager.swift:7`)。
- `saveMemory()`(`RadioViewModel.swift:239-241`)只写本地数组,从不发 `memSave`(`server.py:798-801`),重新登录即丢;且任何 `memChannels` 广播全量覆盖本地。
- recall 未用服务端原子 `memRecall`(`server.py:734-790`,含 mode 后 ±1400Hz SSB 边带二次校频 + 2s 轮询跳过窗),iOS 发两条独立 set → recall 后频率可能偏移。

### 3.2 其余协议问题
| 问题 | 证据 | 影响 |
|---|---|---|
| `setIPO` 发 `"ipo"` 字段,服务端 set 链无此分支 | `RadioViewModel.swift:320`;server.py 全文 grep 零匹配 | 静默吞掉,UI "点了没反应";且 iOS 内部 ipo 索引(0-3)与 ipoLabels 键(0/10/20/30)自相矛盾 |
| 主界面 TUNE 按钮发 `"tuner"`(天调开关)而非 `"tune"`(TX2 载波+AC003) | `ContentView.swift:236` → `toggleTuner()`;web 对照 `ft710_ui.js:1155-1161`、`server.py:911-927` | 主 UI 无法发起调谐;与 DSP 行 ATU 按钮功能重复 |
| "A=B" 按钮实际只是切换 VFO;`copyVFO()` 方向(A→B)与服务端 `vfo_equal`(B→A)相反 | `ContentView.swift:179`;`RadioViewModel.swift:346-348`;`server.py:1223-1227` | 三端三种行为 |
| `modeNumToName` 缺 `0x0F DATA-FM-N` | `RadioState.swift:114-118` vs `config.py:84` | 该模式显示成 "USB" |
| squelch 量程三处不一致 | `RadioViewModel.swift:303` 注释 0-255;`MainRXView.swift:42-44` 0...100;服务端钳 0-100(`server.py:1025`) | 超界值被静默截断 |

---

## 4. P1 — 音频管线问题

### 4.1 TX 重采样拒绝上采样 → 蓝牙/44.1k 路由下 TX 变调
`AudioCaptureManager.swift:157`: `guard inRate > outRate else { return input }`——原生输入率 <48kHz 时原样返回,帧仍按 48kHz/960 组帧标记;服务端无条件按 48→44.1k 重采样(`audio_handler.py:533`)。后果:44.1kHz 音高上移 ~8.8%;蓝牙 HFP(8/16kHz,AudioSession 显式允许 `.allowBluetooth`)完全不可辨。web 端 `tx_capture_worklet.js:82-97` 是相位累加器双向重采样。叠加 session 未设 `preferredSampleRate(48000)`(`AudioSessionManager.swift:16-23`),触发面更大。路由切换后采样率过期(无 `AVAudioEngineConfigurationChangeNotification` 监听)。

### 4.2 RX 无 jitter buffer / 无 PLC
`AudioPlaybackManager.swift:163-171` 每帧到达即 `scheduleBuffer`,无预缓冲/重排/丢弃——网络抖动后积压音频**永久滞后越积越多**(音频频谱电平不同步)。web 端有 time-based jitter buffer(prebuffer 220ms、max 800ms 丢最旧,`rx_worklet_processor.js:33-35`)。解码侧无 PLC(`decodeFEC=0` 且不喂空包,`OpusDecoder.swift:32`),丢包即爆音。

### 4.3 录音功能整体失效
`toggleRecording()`(`RadioViewModel.swift:354-360`)翻转的 `audioCapture.isRecording` 在 `AudioCaptureManager` 内**无任何读取者**;真正实现录音的 `AudioPlaybackManager.startRecording/stopRecording`(`:53-63`)全项目无调用方。且 `makeWAV`(`:204-217`)头部字段错位:声道数写成 16、SampleRate 槽位填错、fmt 体写 14B 声明 16B——产出的 WAV 打不开;逐样本 `data.append` 对长录音是性能灾难。

### 4.4 TX Opus 整条链路死代码
`useOpus: Bool = false`(`AudioCaptureManager.swift:20`)全项目无置 true 路径 → TX 永远 PCM ~768kbps(web 是 64kbps Opus)。且 iOS 编码器配 28kbps CBR 与 web 的 64kbps 约定已分叉。

### 4.5 其余音频问题
- `OpusDecoder.swift:31-32` / `OpusEncoder.swift:32-33`:指针逃逸 `withUnsafeBytes` 闭包(UB)。
- tap 实时线程上做数组拷贝/重采样/960 次逐样本 `Data.append`/O(n) `removeFirst`(`AudioCaptureManager.swift:94-141`)→ glitch 风险。
- `OpusBridge.h:13-15` 错误码定义与真实 libopus 不符(当前无功能影响,埋雷);`my_create_encoder` 的 `frameSize` 参数从未使用。
- 认证失败后 `Task.detached { audioPlayback.start() }` 仍无条件执行(`RadioViewModel.swift:166-168`)。
- 服务端 TX 单 owner 制(`server.py:1745-1747`):浏览器先连 /WSaudioTX 时 iOS 按 PTT 无声且无提示。

---

## 5. P2 — 状态同步缺口

- `applyFullState` 未映射服务端 18 个字段:`nr_level`、`nb_level`、`vox`、`break_in`、`scope_on`、`scope_speed`、`dnr_level`、`contour_level`、`hi_swr`、`recording_status`、`rx_tx_status`、`tuner_tuning`、`scan_status`、`squelch_open`、`meter_display`、`amc_level`、`rx_audio_silent` 等(`RadioState.swift:206-244` vs `radio_state.py:252-315`)。已声明的 `@Published` 永远是假默认值——潜伏地雷。
- 仪表换算全是线性近似(`RadioState.swift:276-291`),服务端用非线性标定表(`config.py:221-274`,功率上限 110W/SWR 上限 9.9)→ **同一时刻 iOS 与 web 功率/SWR 显示不同**,且 iOS 功率显示随功率设定值漂移。S-meter 表一致,没问题。
- 滑块无拖拽防回显:Slider get 读 state、set 直接发送,服务端 dirty 回显在拖动中回写 → 抖动竞争(`SettingsView.swift:46-48` 等)。
- `stepFrequency` 基于滞后的 `state.activeFreq` 绝对值设置,快速连点丢步(`RadioViewModel.swift:249-252`)。
- `lastUpdate` 死赋值(`RadioState.swift:242-243`);`setFrequency(hz, vfo:"A")` 映射到服务端"当前活动 VFO"语义,潜伏设错 VFO(`RadioViewModel.swift:227` vs `server.py:827-832`)。
- 常量表双份硬编码(mode/band/filter/scopeSpans/S 表):`RadioState.swift:114-201` 手工镜像 `config.py`,已出现 3 处漂移;服务端 fullState 其实已下发 `bands`/`modes`(`server.py:1642-1643`)但 iOS 丢弃。

---

## 6. P2 — UI 层问题

- **主线程渲染风暴(最大卡顿风险)**:频谱 stateUpdate ≈30Hz + waterfallImage 30fps + fftData 15fps + 音频 RMS,全部经 `@Published` 中继(`RadioViewModel.swift:388-394`)→ 整个 ContentView 视图树(含 LazyVGrid、两个 Canvas)以 30Hz+ 重算 body;`SMeterView.swift:27` 的 0.3s 动画在 30Hz 更新下持续重启。`SpectrumProcessor` 每帧 COW 拷贝 340KB(`:125-137`)。
- 频谱 "Low FPS" 告警阈值 14fps(`SpectrumProcessor.swift:73`)与服务端实际 5fps 广播(`server.py:285`,其 docstring 也已过时)矛盾 → 永久误报刷屏;FFT 线每 2 帧才发 → 实际 ~2.5fps,panadapter 迟钝。
- 服务端 `"error"` 消息在主界面被吞(`RadioViewModel.swift:440-441` 只写 offState 才展示的 `connectionError`)→ "TX audio device unavailable"(`server.py:889-892`)等关键错误用户看不到。`setupErrorObservers()`(`:182-192`)从未被调用 → 音频错误通知没人接。`ErrorAlertView` 的"重新连接/重试"按钮没有绑定动作。
- 首屏假开机:`RadioState.powerOn` 默认 true 但不连接,登录后电源图标亮绿,用户要点两次才开始连接(`RadioState.swift:40`、`HeaderView.swift:51-56`)。
- ping 每 2s(web 15s)且从不校验 pong → TCP 半开时 `ctrlConnected` 长时间假阳性;重连固定 3s 无退避。
- `Info.plist:34-37` 已声明 `UIBackgroundModes = audio`(音频后台模式),但无任何 scenePhase 处理:进后台时 PTT 不强制释放、socket 状态不整理,回前台也无重连钩子(PTT 部分由 spec ① 补上)。
- `wss`/`https` 不可配置 → 无法连 `--no-ssl` 服务端;默认主机 `radio.vlsc.net:8888` 散落多处。
- 杂项:AGC tag3 "Max"/"慢" 不一致;preamp/att 索引显示为 "dB" 且 "+" 无上限;<10MHz 频率显示前导零;iOS 完全忽略 `scope_start_freq`。

---

## 7. P2 — 测试与构建配置

### 测试:有效覆盖率 0%
- 测试**未接入工程**:`project.yml` 无 test target,pbxproj 中 `FT710MobileTests` 出现 0 次;`IOS_BUILD_GUIDE.md` 教的 `xcodebuild test` 必然失败。
- `RadioViewModelTests.swift` 写的是另一套 API(`state.frequency`、`mode == .LSB`、`incrementFrequency` 等全部不存在)→ 编译即失败;断言也必失败(setter 只发命令不本地改状态)。
- `OpusCodecTests.swift` 调的 C 符号(`create_encoder` 等)不存在(实际是 `my_create_encoder`),160 采样喂 48kHz 编码器必返回 BAD_ARG。
- 网络/音频/PTT/频谱四条关键路径零覆盖。

### 构建配置
- `Info.plist:45` `UIRequiredDeviceCapabilities = armv7` → 错误,iOS 17 仅 arm64。
- `libopus.a` 仅 arm64 真机 slice → **模拟器构建必然链接失败**;checked-in pbxproj 还把 `libopus.a` 放进了 Resources phase(白占体积)。
- `project.yml:30-31` `resources: - path: Resources` 会把 Info.plist 副本打进 bundle。
- `DEVELOPMENT_TEAM: VQ89MM7935` 硬编码;`SUPPORTED_PLATFORMS: iphoneos` 与 Info.plist 的 iPad 方向声明矛盾。
- `NSAllowsArbitraryLoads=true` 无效且是审核减分项(代码硬编码 https/wss;ATS 例外不绕过 TLS 校验,自签名证书照样失败——旧文档对此理解错误)。
- 陈旧产物入库:`SunsdrMobile.xcodeproj/`、`project.pbxproj.bak`。

---

## 8. 死代码清单(grep 全库确认无调用点)

UI(14/25 文件):MainRXView(连带 GainSlider/AudioLevelBar)、DSPPanelView、PTTFooter、PTTButtonView、TunerView、PerformanceMonitorView、DSPQuickButtons、MemoryChannelsGrid、MemoryChannelsView、ModeSelectorView、BandSelectorView、FilterSelectorView、VFOButtons、TuningControls、ContentView.swift:269-307 的 PTTBar/PTTPressStyle。

逻辑:`RadioViewModel.powerOn()`、`setupErrorObservers()`、`WebSocketConnection.updatePassword`、`isConnected`、`ConnectionManager.errorMessage`、`AudioCaptureManager.isRecording`、`useOpus`、`AudioSessionManager.handleAudioRouteChange`/`isBluetoothActive`、`audioOpusDetected` 通知名、`SpectrumProcessor.wfDecimate`。

**后果**:两套实现并存且语义已漂移(死文件里的步进表、AGC 标签、PTT 逻辑都是另一套),误导后续维护者。

---

## 9. 修复优先级

| 级别 | 问题 | 对应章节 |
|---|---|---|
| P0 安全 | PTT 释放竞态(学 web 无条件发+乐观更新)、iOS PTT 看门狗/scenePhase 强制 RX、瀑布流误触 QSY | §2.1 §2.2 §2.6 |
| P0 可用性 | 认证失败路径(1006→auth-check→回登录页)、reconnect 凭据 bug、密码锁死 | §2.3 §2.4 |
| P0 崩溃 | playerNode 重复 attach、installTap 重试(真机验证) | §2.5 |
| P1 功能 | mem 频道协议对齐(null 解析/label/6 槽/memSave/memRecall)、TUNE 语义、TX 重采样、RX jitter buffer、错误消息展示接线 | §3 §4 |
| P2 健康 | 删死代码、测试重建(接入工程+真实 API)、仪表标定对齐、构建配置、重写腐化文档 | §5-§8 |
