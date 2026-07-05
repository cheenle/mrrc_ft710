/**
 * FT-710 Settings Manager
 * ========================
 * Cookie and localStorage persistence for user preferences.
 * Handles auth token reading for WebSocket connections.
 */

(function() {
    'use strict';

    const SETTINGS_KEY = 'ft710_user_settings';
    const DEFAULT_SETTINGS = {
        callsign: '',
        tuneStep: 1000,
        afGain: 128,
        rfPower: 100,
        lastFreq: 14200000,
        lastMode: 'USB',
        lastBand: '20m',
    };

    let settings = {};

    function load() {
        try {
            const raw = localStorage.getItem(SETTINGS_KEY);
            if (raw) {
                settings = Object.assign({}, DEFAULT_SETTINGS, JSON.parse(raw));
            } else {
                settings = Object.assign({}, DEFAULT_SETTINGS);
            }
        } catch(e) {
            settings = Object.assign({}, DEFAULT_SETTINGS);
        }
        return settings;
    }

    function save(newSettings) {
        Object.assign(settings, newSettings);
        try {
            localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
        } catch(e) {}
    }

    function get(key, defaultValue) {
        return settings.hasOwnProperty(key) ? settings[key] : defaultValue;
    }

    // ── Auth Cookie Helper ────────────────────────────────────────
    function getAuthToken() {
        const match = document.cookie.match(/(?:^|;\s*)ft710_auth=([^;]*)/);
        return match ? match[1] : '';
    }

    // ── Initialize ────────────────────────────────────────────────
    load();

    window.FT710Settings = {
        get: get,
        save: save,
        load: load,
        getAll: function() { return Object.assign({}, settings); },
        getAuthToken: getAuthToken,
    };

    console.log('Settings Manager initialized');
})();
