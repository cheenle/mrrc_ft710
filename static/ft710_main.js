/**
 * FT-710 Web Control — Main Controller
 * =====================================
 * WebSocket connection, state management, message dispatch.
 * Connects to /WSradio endpoint with auth token.
 *
 * Depends on: settings_manager.js (loaded first) for getAuthToken()
 */

// ── Auth ────────────────────────────────────────────────────────────
function getAuthToken() {
    const m = document.cookie.match(new RegExp('(?:^|;\\s*)ft710_auth=([^;]*)'));
    return m ? m[1] : '';
}

function handleAuthExpired() {
    if (window.__authRedirecting) return;
    window.__authRedirecting = true;
    try { if (wsRadio) wsRadio.close(); } catch(e) {}
    window.location.replace('/login?next=' + encodeURIComponent(window.location.pathname));
}

// ── WebSocket ───────────────────────────────────────────────────────
let wsRadio = null;
let wsSpectrum = null;
let wsReconnectTimer = null;
let wsReconnectDelay = 1000;
const WS_RECONNECT_MAX = 30000;
let pingTimer = null;

function wsUrlWithAuth(path) {
    const token = getAuthToken();
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return proto + '//' + host + path + (token ? '?token=' + encodeURIComponent(token) : '');
}

// Same-auth URL for static files (uses http/https, not ws/wss)
function staticUrlWithAuth(path) {
    const token = getAuthToken();
    const proto = window.location.protocol;
    const host = window.location.host;
    return proto + '//' + host + path + (token ? '?token=' + encodeURIComponent(token) : '');
}

function connectWebSocket() {
    if (wsRadio && wsRadio.readyState === WebSocket.OPEN) return;

    const url = wsUrlWithAuth('/WSradio');
    console.log('Connecting to', url);
    wsRadio = new WebSocket(url);
    wsRadio.binaryType = 'arraybuffer';

    wsRadio.onopen = function() {
        console.log('WebSocket connected');
        wsReconnectDelay = 1000;
        updateConnectionStatus(true);
        startPing();
        // Also connect spectrum + audio
        connectSpectrumSocket();
        connectAudioRX();
        connectAudioTX();
    };

    wsRadio.onmessage = function(event) {
        try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } catch(e) {
            console.debug('WS message error:', e);
        }
    };

    wsRadio.onclose = function(event) {
        console.log('WebSocket closed:', event.code);
        updateConnectionStatus(false);
        stopPing();
        if (event.code === 4001) {
            handleAuthExpired();
            return;
        }
        scheduleReconnect();
    };

    wsRadio.onerror = function(e) {
        console.warn('WebSocket error');
    };
}

// ── Spectrum WebSocket ──────────────────────────────────────────────
function connectSpectrumSocket() {
    if (wsSpectrum && wsSpectrum.readyState === WebSocket.OPEN) return;
    const url = wsUrlWithAuth('/WSspectrum');
    wsSpectrum = new WebSocket(url);
    wsSpectrum.binaryType = 'arraybuffer';
    wsSpectrum.onmessage = function(event) {
        if (event.data instanceof ArrayBuffer) {
            handleSpectrumBinary(event.data);
        }
    };
    wsSpectrum.onclose = function() {
        wsSpectrum = null;
    };
    wsSpectrum.onerror = function() {};
}

function handleSpectrumBinary(buffer) {
    const data = new Uint8Array(buffer);
    // Minimum: 1 version byte + 850 wf1 = 851 bytes
    if (data.length < 851) {
        console.debug('Spectrum frame too short:', data.length);
        return;
    }

    const version = data[0];
    if (version < 1 || version > 2) {
        console.debug('Spectrum frame unknown version:', version);
        return;
    }

    const wf1 = Array.from(data.slice(1, 851));

    // If we have wf2 data (v2+), extract it for potential future use
    if (data.length >= 1701) {
        const wf2 = Array.from(data.slice(851, 1701));
        window._lastWf2 = wf2;
    }

    // Update waterfall
    if (typeof renderWaterfallRow === 'function') {
        renderWaterfallRow(wf1);
    }

    // Update S-meter from scope data peak
    if (typeof radioState !== 'undefined') {
        updateSMeterFromSpectrum(wf1);
    }
}

function updateSMeterFromSpectrum(wf1) {
    // Peak signal from spectrum as approximate S-meter
    if (!wf1 || wf1.length === 0) return;
    let maxVal = 0;
    let sum = 0;
    for (let i = 0; i < wf1.length; i++) {
        if (wf1[i] > maxVal) maxVal = wf1[i];
        sum += wf1[i];
    }
    // Store for UI / diagnostics
    window._specPeak = maxVal;
    window._specAvg = sum / wf1.length;
}

function scheduleReconnect() {
    if (wsReconnectTimer) return;
    console.log('Reconnecting in', wsReconnectDelay, 'ms');
    wsReconnectTimer = setTimeout(function() {
        wsReconnectTimer = null;
        connectWebSocket();
        wsReconnectDelay = Math.min(wsReconnectDelay * 2, WS_RECONNECT_MAX);
    }, wsReconnectDelay);
}

function startPing() {
    stopPing();
    pingTimer = setInterval(function() {
        sendMsg({type: 'ping'});
    }, 15000);
}

function stopPing() {
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
}

function sendMsg(msg) {
    if (wsRadio && wsRadio.readyState === WebSocket.OPEN) {
        wsRadio.send(JSON.stringify(msg));
        return true;
    }
    return false;
}

function sendCommand(field, value) {
    return sendMsg({type: 'set', field: field, value: value});
}

// ── State ───────────────────────────────────────────────────────────
const radioState = {
    vfo_a_freq: 14200000,
    vfo_b_freq: 7050000,
    active_vfo: 'A',
    mode: 1,
    mode_name: 'USB',
    mode_display: 'USB',
    band_name: '20m',
    tx_status: 0,
    is_transmitting: false,
    s_meter: 0,
    s_meter_dbm: -54,
    s_unit: 'S0',
    comp_meter: 0,
    alc_meter: 0,
    power_meter: 0,
    swr_meter: 0,
    id_meter: 0,
    vd_meter: 0,
    af_gain: 128,
    rf_gain: 255,
    rf_power: 100,
    filter_width: 5,
    filter_hz: 2400,
    preamp: 0,
    preamp_label: 'OFF',
    attenuator: 0,
    attenuator_label: 'OFF',
    noise_blanker: false,
    noise_reduction: false,
    auto_notch: false,
    compressor: false,
    compressor_level: 50,
    tuner_status: 0,
    power_on: true,
    squelch: 0,
    mic_gain: 50,
    split: false,
    scope_span: 6,
    scope_speed: 2,
    scope_mode: 0,
    scope_start_freq: 0,
    serial_connected: false,
    last_update: 0,
    ws_connected: false,
};

const bands = [];
const uiModes = [];
const memChannels = new Array(6).fill(null);

// ── Message Handler ─────────────────────────────────────────────────
function handleMessage(msg) {
    switch (msg.type) {
        case 'fullState':
            // Merge full state data
            if (msg.data) {
                Object.assign(radioState, msg.data);
            }
            if (msg.bands) {
                bands.length = 0;
                bands.push(...msg.bands);
            }
            if (msg.modes) {
                uiModes.length = 0;
                uiModes.push(...msg.modes);
            }
            radioState.ws_connected = true;
            renderAll();
            break;

        case 'stateUpdate':
            if (msg.fields) {
                Object.assign(radioState, msg.fields);
            }
            if (msg.dirty) {
                renderUpdates(msg.dirty);
            }
            break;

        case 'value':
            if (msg.field && msg.value !== undefined) {
                radioState[msg.field] = msg.value;
                renderField(msg.field);
            }
            break;

        case 'memChannels':
            if (msg.channels) {
                memChannels.length = 0;
                memChannels.push(...msg.channels);
                renderMemoryChannels();
            }
            break;

        case 'pong':
            // Latency tracking could go here
            break;

        case 'error':
            console.warn('Server error:', msg.message);
            break;
    }
}

// ── Connection Status ───────────────────────────────────────────────
function updateConnectionStatus(connected) {
    radioState.ws_connected = connected;
    const dot = document.querySelector('#status-serial .status-dot');
    if (dot) {
        if (connected && radioState.serial_connected) {
            dot.classList.add('connected');
        } else {
            dot.classList.remove('connected');
        }
    }
}

// ── Initialization ──────────────────────────────────────────────────
function bodyload() {
    connectWebSocket();
    requestWakeLock();
}

async function requestWakeLock() {
    if ('wakeLock' in navigator) {
        try {
            await navigator.wakeLock.request('screen');
        } catch(e) {}
    }
}

// ── Keyboard support ────────────────────────────────────────────────
document.addEventListener('keydown', function(e) {
    // Space = PTT
    if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        if (!radioState.is_transmitting) {
            handlePTTStart();
        } else {
            handlePTTEnd();
        }
    }
    // Arrow keys = tune
    if (e.code === 'ArrowLeft') {
        tuneBy(-(currentTuneStep || 1000));
    }
    if (e.code === 'ArrowRight') {
        tuneBy(currentTuneStep || 1000);
    }
    if (e.code === 'ArrowUp') {
        tuneBy((currentTuneStep || 1000) * 5);
    }
    if (e.code === 'ArrowDown') {
        tuneBy(-(currentTuneStep || 1000) * 5);
    }
});

window.addEventListener('load', bodyload);

// ═══════════════════════════════════════════════════════════════════════
// ── Audio RX ──────────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════

let wsAudioRX = null;
let audioRXContext = null;
let audioRXWorklet = null;
let audioRXGain = null;
let audioRXStarted = false;

// Codec tags (must match server's opus_rx.py)
const AUDIO_TAG_PCM = 0x00;
const AUDIO_TAG_OPUS = 0x01;

function connectAudioRX() {
    if (wsAudioRX && wsAudioRX.readyState === WebSocket.OPEN) return;

    const url = wsUrlWithAuth('/WSaudioRX');
    console.log('Connecting Audio RX to', url);
    wsAudioRX = new WebSocket(url);
    wsAudioRX.binaryType = 'arraybuffer';

    wsAudioRX.onopen = function() {
        console.log('Audio RX WebSocket connected');
        startAudioRXPlayback();
    };

    wsAudioRX.onmessage = function(event) {
        // Raw receipt log (first 5 only)
        if (!window.__rxMsgCount) window.__rxMsgCount = 0;
        window.__rxMsgCount++;
        if (window.__rxMsgCount <= 3) {
            console.log('WS audio msg #' + window.__rxMsgCount +
                ': type=' + typeof event.data +
                ' isArrayBuffer=' + (event.data instanceof ArrayBuffer) +
                ' isBlob=' + (event.data instanceof Blob) +
                ' size=' + (event.data.byteLength || event.data.size || '?'));
        }
        if (!window.__rxBytes) window.__rxBytes = 0;
        if (event.data instanceof ArrayBuffer) {
            window.__rxBytes += event.data.byteLength;
            const f32 = decodeRxAudioFrame(event.data);
            if (f32) {
                window.__rxFrames = (window.__rxFrames || 0) + 1;
                const pushed = (typeof audioRXWorklet !== 'undefined' && audioRXWorklet && audioRXWorklet.port);
                if (window.__rxFrames === 1) {
                    console.log('First audio frame: size=' + event.data.byteLength +
                        ', decoded=' + f32.length + ' samples, worklet=' + (pushed ? 'ready' : 'missing'));
                }
                if (window.__rxFrames % 50 === 0) {
                    console.log('Audio frames received: ' + window.__rxFrames +
                        ' ctx=' + (audioRXContext ? audioRXContext.state : 'none') +
                        ' pushed=' + (pushed ? 'yes' : 'no'));
                }
                if (pushed) {
                    try {
                        audioRXWorklet.port.postMessage({type: 'push', payload: f32});
                    } catch(e) { console.debug('push error:', e); }
                }
            }
        } else if (event.data instanceof Blob) {
            console.warn('WS audio: got Blob, expected ArrayBuffer — check binaryType');
        } else if (typeof event.data === 'string') {
            console.warn('WS audio: got string: ' + event.data.substring(0, 50));
        }
    };

    wsAudioRX.onclose = function() {
        console.log('Audio RX WebSocket closed');
        wsAudioRX = null;
    };

    wsAudioRX.onerror = function() {};
}

// Decode a tagged audio frame: 1-byte tag + payload
let _rxOpusDecoder = null;
function getRxOpusDecoder() {
    if (_rxOpusDecoder) return _rxOpusDecoder;
    try {
        if (typeof OpusDecoder === 'undefined') return null;
        _rxOpusDecoder = new OpusDecoder(48000, 1);
        console.log('RX Opus decoder ready (48kHz mono)');
    } catch(e) {
        console.warn('RX Opus decoder creation failed:', e);
        _rxOpusDecoder = null;
    }
    return _rxOpusDecoder;
}

function decodeRxAudioFrame(data) {
    if (!data || data.byteLength < 1) return null;
    const bytes = new Uint8Array(data);
    const tag = bytes[0];
    const payload = data.slice(1);  // ArrayBuffer, offset by 1

    if (tag === AUDIO_TAG_OPUS) {
        const dec = getRxOpusDecoder();
        if (!dec) return null;
        try {
            const f32 = dec.decode_float(payload);
            const copy = new Float32Array(f32);  // Copy out of WASM heap
            // Debug: check first frame audio levels
            if (!window.__audioDbg) {
                window.__audioDbg = true;
                var peak = 0, sum = 0;
                for (var i = 0; i < copy.length; i++) {
                    var abs = Math.abs(copy[i]);
                    if (abs > peak) peak = abs;
                    sum += abs;
                }
                console.log('First Opus frame: ' + copy.length + ' samples, peak=' +
                    (peak * 100).toFixed(1) + '%, avg=' + (sum / copy.length * 100).toFixed(2) + '%');
                if (peak < 0.0001) console.warn('⚠ Audio data is near-silent — check radio AF gain / USB audio');
            }
            return copy;
        } catch(e) {
            console.debug('Opus decode error:', e);
            return null;
        }
    }

    // PCM: Int16 → Float32
    try {
        if (payload.byteLength < 2) return null;
        const i16 = new Int16Array(payload);
        const f32 = new Float32Array(i16.length);
        const scale = 1.0 / 32767.0;
        for (let i = 0; i < i16.length; i++) {
            f32[i] = i16[i] * scale;
        }
        return f32;
    } catch(e) {
        return null;
    }
}

function startAudioRXPlayback() {
    if (audioRXStarted) return;

    try {
        audioRXContext = new (window.AudioContext || window.webkitAudioContext)({
            latencyHint: 'interactive',
            sampleRate: 48000,
        });

        // Resume if suspended (Chrome autoplay policy / iOS)
        if (audioRXContext.state === 'suspended') {
            console.log('AudioContext suspended — tap anywhere to enable audio');
            // Show visible hint
            var hint = document.createElement('div');
            hint.id = 'audio-resume-hint';
            hint.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;' +
                'background:#f59e0b;color:#000;text-align:center;padding:10px;' +
                'font-weight:bold;font-size:14px;cursor:pointer;';
            hint.textContent = '🔊 点击此处启用音频  Tap to enable audio';
            hint.onclick = function() { hint.remove(); };
            document.body.appendChild(hint);
            // Resume on first user interaction
            var resumeAudio = function() {
                audioRXContext.resume().then(function() {
                    console.log('AudioContext resumed — audio should play now');
                    var h = document.getElementById('audio-resume-hint');
                    if (h) h.remove();
                }).catch(function(e) {
                    console.warn('AudioContext resume failed:', e);
                });
            };
            document.addEventListener('click', resumeAudio, {once: true});
            document.addEventListener('touchstart', resumeAudio, {once: true});
            document.addEventListener('keydown', resumeAudio, {once: true});
        }

        audioRXGain = audioRXContext.createGain();
        audioRXGain.gain.value = 1.0;

        // Use AudioWorklet for low-latency playback
        audioRXContext.audioWorklet.addModule(
            staticUrlWithAuth('/rx_worklet_processor.js?v=1')
        ).then(function() {
            audioRXWorklet = new AudioWorkletNode(audioRXContext, 'rx-player');
            audioRXWorklet.connect(audioRXGain);
            audioRXGain.connect(audioRXContext.destination);
            audioRXStarted = true;
            console.log('Audio RX playback started (AudioWorklet)');
        }).catch(function(e) {
            console.warn('AudioWorklet failed, using ScriptProcessor fallback:', e);
            setupScriptProcessorFallback();
        });
    } catch(e) {
        console.error('Audio RX init failed:', e);
    }
}

function setupScriptProcessorFallback() {
    try {
        const bufSize = 2048;
        const sp = audioRXContext.createScriptProcessor(bufSize, 1, 1);
        let queue = [];
        let queuedSamples = 0;
        const prebufferSamples = 60 * 48; // 60ms @ 48kHz
        let priming = true;

        sp.onaudioprocess = function(event) {
            const out = event.outputBuffer.getChannelData(0);
            const needed = out.length;
            let written = 0;

            // Prime: wait for enough samples
            if (priming) {
                if (queuedSamples < prebufferSamples) {
                    out.fill(0);
                    return;
                }
                priming = false;
            }

            while (written < needed && queue.length > 0) {
                const chunk = queue[0];
                const n = Math.min(chunk.length, needed - written);
                out.set(chunk.subarray(0, n), written);
                written += n;
                queuedSamples -= n;
                if (n >= chunk.length) {
                    queue.shift();
                } else {
                    queue[0] = chunk.subarray(n);
                }
            }

            if (written < needed) {
                out.fill(0, written);
                queuedSamples = 0;
                queue = [];
                priming = true;
            }
        };

        sp.connect(audioRXGain);
        audioRXGain.connect(audioRXContext.destination);
        audioRXStarted = true;

        // Override the worklet push to use ScriptProcessor queue
        window._spQueue = queue;
        const origWorklet = audioRXWorklet;
        audioRXWorklet = {
            port: {
                postMessage: function(msg) {
                    if (msg.type === 'push' && msg.payload) {
                        window._spQueue.push(msg.payload);
                        window._spQueueTotal = (window._spQueueTotal || 0) + msg.payload.length;
                    }
                }
            }
        };
        console.log('Audio RX playback started (ScriptProcessor fallback)');
    } catch(e) {
        console.error('ScriptProcessor fallback failed:', e);
    }
}

// ═══════════════════════════════════════════════════════════════════════
// ── Audio TX ──────────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════

let wsAudioTX = null;
let txAudioStream = null;
let txOpusWorker = null;
let txAudioRunning = false;

function connectAudioTX() {
    if (wsAudioTX && wsAudioTX.readyState === WebSocket.OPEN) return;

    const url = wsUrlWithAuth('/WSaudioTX');
    console.log('Connecting Audio TX to', url);
    wsAudioTX = new WebSocket(url);
    wsAudioTX.binaryType = 'arraybuffer';

    wsAudioTX.onopen = function() {
        console.log('Audio TX WebSocket connected');
    };

    wsAudioTX.onclose = function() {
        console.log('Audio TX WebSocket closed');
        wsAudioTX = null;
    };

    wsAudioTX.onerror = function() {};
}

function startTXAudio() {
    if (txAudioRunning) return;
    if (!wsAudioTX || wsAudioTX.readyState !== WebSocket.OPEN) {
        connectAudioTX();
    }

    console.log('Starting TX audio capture...');

    // Start Opus worker for encoding
    if (!txOpusWorker) {
        txOpusWorker = new Worker('/tx_opus_worker.js');
        txOpusWorker.onmessage = function(ev) {
            const d = ev.data || {};
            if (d.type === 'tx_audio' && d.data instanceof ArrayBuffer) {
                if (wsAudioTX && wsAudioTX.readyState === WebSocket.OPEN) {
                    wsAudioTX.send(d.data);
                }
            }
        };
    }

    // Capture mic via getUserMedia, encode, send
    navigator.mediaDevices.getUserMedia({
        audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
        }
    }).then(function(stream) {
        txAudioStream = stream;

        // Create AudioContext for capture
        const ctx = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000,
        });

        if (ctx.state === 'suspended') {
            ctx.resume().catch(function(){});
        }

        const source = ctx.createMediaStreamSource(stream);
        const sp = ctx.createScriptProcessor(320, 1, 1); // 20ms @ 16kHz

        sp.onaudioprocess = function(event) {
            if (!txAudioRunning) return;
            const input = event.inputBuffer.getChannelData(0);
            // Convert Float32 → Int16 for the Opus worker
            if (txOpusWorker) {
                const i16 = new Int16Array(input.length);
                for (let i = 0; i < input.length; i++) {
                    const v = input[i] * 32767;
                    i16[i] = v > 32767 ? 32767 : (v < -32768 ? -32768 : (v | 0));
                }
                txOpusWorker.postMessage({
                    type: 'frame',
                    frame: i16.buffer,
                }, [i16.buffer]);
            }
        };

        source.connect(sp);
        sp.connect(ctx.destination); // Required by some browsers
        txAudioRunning = true;
        if (txOpusWorker) txOpusWorker.postMessage({type: 'start'});
        console.log('TX audio capture started');
    }).catch(function(e) {
        console.error('TX audio mic access failed:', e);
        // Fallback: direct Int16 PCM without Opus
        startTXAudioFallback();
    });
}

function startTXAudioFallback() {
    // Simplified TX without Opus Worker — send Int16 PCM directly
    navigator.mediaDevices.getUserMedia({
        audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
        }
    }).then(function(stream) {
        txAudioStream = stream;
        const ctx = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000,
        });
        if (ctx.state === 'suspended') ctx.resume().catch(function(){});

        const source = ctx.createMediaStreamSource(stream);
        const sp = ctx.createScriptProcessor(320, 1, 1);

        sp.onaudioprocess = function(event) {
            if (!txAudioRunning) return;
            const input = event.inputBuffer.getChannelData(0);
            const i16 = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                const v = input[i] * 32767;
                i16[i] = v > 32767 ? 32767 : (v < -32768 ? -32768 : (v | 0));
            }
            // Tag as PCM (0x00) + data
            const tagged = new Uint8Array(1 + i16.byteLength);
            tagged[0] = 0x00;
            tagged.set(new Uint8Array(i16.buffer), 1);
            if (wsAudioTX && wsAudioTX.readyState === WebSocket.OPEN) {
                wsAudioTX.send(tagged.buffer);
            }
        };

        source.connect(sp);
        sp.connect(ctx.destination);
        txAudioRunning = true;
        console.log('TX audio capture started (PCM fallback)');
    }).catch(function(e) {
        console.error('TX audio fallback failed:', e);
        txAudioRunning = false;
    });
}

function stopTXAudio() {
    txAudioRunning = false;
    if (txOpusWorker) txOpusWorker.postMessage({type: 'stop'});
    if (txAudioStream) {
        txAudioStream.getTracks().forEach(function(t) { t.stop(); });
        txAudioStream = null;
    }
    if (wsAudioTX && wsAudioTX.readyState === WebSocket.OPEN) {
        wsAudioTX.send('s:');
    }
    console.log('TX audio stopped');
}

// ── Bandwidth display ─────────────────────────────────────────────────
(function() {
    window.__rxBytes = 0;
    window.__txBytes = 0;
    setInterval(function() {
        const rxKbps = ((window.__rxBytes || 0) * 8) / 1000;
        window.__rxBytes = 0;
        const el = document.getElementById('status-bitrate');
        if (el) {
            el.textContent = 'RX ' + rxKbps.toFixed(0) + 'K';
        }
    }, 1000);
})();
