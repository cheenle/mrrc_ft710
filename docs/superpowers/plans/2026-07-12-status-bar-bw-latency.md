# Status Bar Bandwidth & Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Add real-time network bandwidth (4-channel WS total) and latency (control RTT + audio jitter buffer) to status bar.

**Architecture:** Modify 3 files — HTML (add 2 span elements), JS main (unified bandwidth counter + RTT measurement + latency display), JS worklet (periodic jitter buffer stats report).

**Tech Stack:** Vanilla JS, AudioWorklet API

## Global Constraints

- Match existing code style (var declarations, inline functions, no ES6 modules)
- Graceful degradation if DOM elements missing
- All 4 WS channels tracked: control, spectrum, audioRX, audioTX

---

### Task 1: Add status bar HTML elements

**Files:**
- Modify: `static/index.html` (status-bar section)

- [ ] Add `#status-bitrate` and `#status-latency` spans to `.status-bar`

```html
<span class="status-item" id="status-bitrate">↓0 ↑0</span>
<span class="status-item" id="status-latency">RTT -- J--</span>
```

Insert after the `#status-serial` span.

- [ ] Commit

---

### Task 2: Add jitter buffer stats reporting to worklet

**Files:**
- Modify: `static/rx_worklet_processor.js`

- [ ] Add periodic stats reporting in `process()` — every ~2s, report `bufferMs`

In the constructor, add:
```javascript
this._statsCounter = 0;
this._statsInterval = Math.round(sampleRate * 2 / 128); // every ~2s
```

In `process()`, before `return true`:
```javascript
this._statsCounter++;
if (this._statsCounter >= this._statsInterval) {
    this._statsCounter = 0;
    var bufferMs = (this.queuedSamples / sampleRate) * 1000;
    this.port.postMessage({type: 'stats', bufferMs: Math.round(bufferMs)});
}
```

- [ ] Commit

---

### Task 3: Implement bandwidth + latency tracking in main JS

**Files:**
- Modify: `static/ft710_main.js`

Sub-steps:

- [ ] **3a: Replace bandwidth IIFE with unified 4-channel tracker**

Replace lines 966-977 with:

```javascript
// ── Bandwidth + Latency display ─────────────────────────────────────
(function() {
    window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
    setInterval(function() {
        var b = window.__netBytes;
        var rxTotal = b.rxCtrl + b.rxSpec + b.rxAudio;
        var txTotal = b.txCtrl + b.txAudio;
        var rxKbps = (rxTotal * 8) / 1000;
        var txKbps = (txTotal * 8) / 1000;
        b.rxCtrl = b.rxSpec = b.rxAudio = b.txCtrl = b.txAudio = 0;
        var el = document.getElementById('status-bitrate');
        if (el) {
            el.textContent = '↓' + rxKbps.toFixed(0) + 'K ↑' + txKbps.toFixed(0) + 'K';
        }
        var rtt = window.__lastRtt || 0;
        var jitter = window.__jitterMs || 0;
        var el2 = document.getElementById('status-latency');
        if (el2) {
            el2.textContent = 'RTT ' + rtt + 'ms J' + jitter + 'ms';
        }
    }, 1000);
})();
```

- [ ] **3b: Track RX bytes in wsRadio.onmessage**

After `handleMessage(msg)` in `wsRadio.onmessage`, add:
```javascript
if (!window.__netBytes) window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
window.__netBytes.rxCtrl += event.data.length;
```

- [ ] **3c: Track TX bytes in sendMsg**

After `wsRadio.send(JSON.stringify(msg))`, add:
```javascript
if (!window.__netBytes) window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
window.__netBytes.txCtrl += JSON.stringify(msg).length;
```

- [ ] **3d: Track spectrum RX bytes**

In `wsSpectrum.onmessage`, add before `handleSpectrumBinary`:
```javascript
if (!window.__netBytes) window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
window.__netBytes.rxSpec += event.data.byteLength;
```

- [ ] **3e: Track audio RX bytes (replace old __rxBytes)**

In `wsAudioRX.onmessage` (first instance, line 548-562), replace:
```javascript
if (!window.__rxBytes) window.__rxBytes = 0;
window.__rxBytes += msg.data.byteLength;
```
with:
```javascript
if (!window.__netBytes) window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
window.__netBytes.rxAudio += msg.data.byteLength;
```

Also replace the second instance in the ScriptProcessor fallback path (around line 679-680):
```javascript
if (!window.__rxBytes) window.__rxBytes = 0;
window.__rxBytes += msg.data.byteLength;
```
with:
```javascript
if (!window.__netBytes) window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
window.__netBytes.rxAudio += msg.data.byteLength;
```

- [ ] **3f: Track audio TX bytes**

In `txOpusWorker.onmessage` handler (line 736-743), after `wsAudioTX.send(d.data)`, add:
```javascript
if (!window.__netBytes) window.__netBytes = { rxCtrl: 0, rxSpec: 0, rxAudio: 0, txCtrl: 0, txAudio: 0 };
window.__netBytes.txAudio += d.data.byteLength;
```

- [ ] **3g: Record ping time in startPing**

Replace the ping interval callback with:
```javascript
pingTimer = setInterval(function() {
    window.__pingSent = performance.now();
    sendMsg({type: 'ping'});
}, 15000);
```

- [ ] **3h: Calculate RTT on pong**

Replace the pong case comment in handleMessage:
```javascript
case 'pong':
    if (window.__pingSent) {
        window.__lastRtt = Math.round(performance.now() - window.__pingSent);
        window.__pingSent = 0;
    }
    break;
```

- [ ] **3i: Receive jitter buffer stats from worklet**

In the AudioWorklet setup (line 610), extend `rxNode.port.onmessage` or add a second handler. Add after the config postMessage:
```javascript
rxNode.port.onmessage = function(ev) {
    if (ev.data && ev.data.type === 'stats') {
        window.__jitterMs = Math.round(ev.data.bufferMs || 0);
    }
};
```

Note: The worklet already uses `this.port.onmessage` in its constructor for push/config messages. The main thread side `rxNode.port.onmessage` receives messages FROM the worklet, which is separate. So adding this handler on the main thread side is correct and won't conflict.

- [ ] Commit
