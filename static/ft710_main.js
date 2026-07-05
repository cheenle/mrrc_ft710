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
        // Also connect spectrum
        connectSpectrumSocket();
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
