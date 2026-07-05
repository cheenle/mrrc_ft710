// AudioWorklet TX capture → SharedArrayBuffer (zero main-thread path)
// =====================================================================
// Writes downsampled 16 kHz float32 samples directly into a SAB ring
// buffer.  The Opus Worker reads from the same SAB and sends via its own
// WebSocket — the main thread never touches audio samples.
//
// Ring buffer layout (same as modules/tx_sab_ring.js):
//   word[0] = write_pos (Uint32, producer advances atomically)
//   word[1] = read_pos  (Uint32, consumer advances atomically)
//   word[2+] = float32 sample data (power-of-2 size)

class TxCaptureSABProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super(options);
    this._inRate = sampleRate;                    // typically 48000
    this._outRate = 16000;
    this._dsRatio = Math.max(1, Math.round(this._inRate / this._outRate));
    this._decimBlock = this._dsRatio * 160;       // 480 samples @ 48k ≈ 10 ms
    this._inBuf = new Float32Array(0);

    // SAB state (set via port message)
    this._sab = null;
    this._ringMask = 0;
    this._writePtr = null;
    this._readPtr = null;
    this._data = null;
    this._enabled = false;

    // Frame accumulator for legacy postMessage path (used when SAB unavailable)
    this._frameAcc = new Float32Array(0);
    this._frameSize = Math.round(this._outRate * 0.020);  // 320 samples @ 16kHz
    this._scale = 0x7FFF;

    this.port.onmessage = (ev) => {
      var d = ev.data || {};
      if (d.type === 'sab') {
        this._sab = d.sab;
        this._ringMask = (d.ringSize || 16384) - 1;
        this._writePtr = new Uint32Array(this._sab, 0, 1);
        this._readPtr  = new Uint32Array(this._sab, 4, 1);
        this._data     = new Float32Array(this._sab, 8, this._ringMask + 1);
        this._enabled  = true;
      } else if (d.type === 'flush') {
        this._inBuf = new Float32Array(0);
        this._frameAcc = new Float32Array(0);
        if (this._writePtr) Atomics.store(this._writePtr, 0, 0);
        if (this._readPtr)  Atomics.store(this._readPtr, 0, 0);
      }
    };
  }

  // ── SAB ring write (lock-free SPSC) ──────────────────

  _writeRing(samples, n) {
    if (!this._enabled || n === 0) return;
    var wp = Atomics.load(this._writePtr);
    var rp = Atomics.load(this._readPtr);
    var mask = this._ringMask;
    var size = mask + 1;
    var used = wp - rp;
    var free = size - used;
    if (n > free) {
      // Drop oldest samples (buffer is ~1s deep — this should be rare)
      var drop = n - free;
      Atomics.store(this._readPtr, 0, rp + drop);
    }
    var idx = wp & mask;
    var first = Math.min(n, size - idx);
    var data = this._data;
    for (var i = 0; i < first; i++) data[idx + i] = samples[i];
    if (n > first) {
      for (var i = 0; i < n - first; i++) data[i] = samples[first + i];
    }
    Atomics.store(this._writePtr, 0, wp + n);
  }

  // ── Audio processing ─────────────────────────────────

  process(inputs, outputs) {
    var input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) {
      return true;
    }
    var ch = input[0];
    var R = this._dsRatio;

    // Append to input buffer
    var merged = new Float32Array(this._inBuf.length + ch.length);
    merged.set(this._inBuf);
    merged.set(ch, this._inBuf.length);
    this._inBuf = merged;

    // Downsample in fixed-size blocks
    while (this._inBuf.length >= this._decimBlock) {
      var blockOut = this._decimBlock / R;
      var decimated = new Float32Array(blockOut);
      for (var i = 0; i < blockOut; i++) {
        var sum = 0;
        var base = i * R;
        for (var j = 0; j < R; j++) {
          sum += this._inBuf[base + j];
        }
        decimated[i] = sum / R;
      }
      this._inBuf = this._inBuf.subarray(this._decimBlock);

      if (this._enabled) {
        // ── SAB path: write directly, zero main-thread involvement ──
        this._writeRing(decimated, decimated.length);
      } else {
        // ── Legacy path: accumulate 20ms frames, post Int16 ──
        var accMerged = new Float32Array(this._frameAcc.length + decimated.length);
        accMerged.set(this._frameAcc);
        accMerged.set(decimated, this._frameAcc.length);
        this._frameAcc = accMerged;
        while (this._frameAcc.length >= this._frameSize) {
          var frame = this._frameAcc.subarray(0, this._frameSize);
          this._frameAcc = this._frameAcc.subarray(this._frameSize);
          var i16 = new Int16Array(this._frameSize);
          for (var k = 0; k < this._frameSize; k++) {
            var v = frame[k] * this._scale;
            i16[k] = v > 32767 ? 32767 : (v < -32768 ? -32768 : (v | 0));
          }
          this.port.postMessage(i16);
        }
      }
    }

    return true;
  }
}

registerProcessor('tx-capture', TxCaptureSABProcessor);
