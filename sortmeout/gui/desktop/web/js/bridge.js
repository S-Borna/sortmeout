/**
 * SortMeOut Desktop — JavaScript ↔ Python Bridge
 *
 * Provides a clean async API for communicating with the Python backend
 * via WKScriptMessageHandler (js → python) and evaluateJavaScript (python → js).
 */

(function () {
    'use strict';

    // ── Callback registry ──
    const _callbacks = {};
    let _callbackId = 0;

    /**
     * Bridge callback handler — called from Python via evaluateJavaScript.
     * @param {string} id   - The callback ID
     * @param {*} data       - Success payload
     * @param {*} error      - Error message (null if success)
     */
    window._bridgeCallback = function (id, data, error) {
        const cb = _callbacks[id];
        if (!cb) return;
        delete _callbacks[id];

        if (error) {
            cb.reject(new Error(error));
        } else {
            cb.resolve(data);
        }
    };

    /**
     * Send a message to the Python backend and return a Promise.
     *
     * @param {string} action  - Action name (e.g., "chat_send", "email_list")
     * @param {object} payload - Data to send
     * @param {number} timeout - Timeout in ms (default 30s)
     * @returns {Promise<object>}
     */
    function callBridge(action, payload = {}, timeout = 30000) {
        return new Promise((resolve, reject) => {
            const id = `cb_${++_callbackId}_${Date.now()}`;
            _callbacks[id] = { resolve, reject };

            // Timeout guard
            setTimeout(() => {
                if (_callbacks[id]) {
                    delete _callbacks[id];
                    reject(new Error(`Bridge timeout: ${action}`));
                }
            }, timeout);

            // Send to Python via WKScriptMessageHandler
            try {
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.sortmeout) {
                    window.webkit.messageHandlers.sortmeout.postMessage(
                        JSON.stringify({ action, payload, callbackId: id })
                    );
                } else {
                    // Dev fallback — simulate response
                    delete _callbacks[id];
                    resolve(_devFallback(action, payload));
                }
            } catch (err) {
                delete _callbacks[id];
                reject(err);
            }
        });
    }

    /**
     * Fire-and-forget message to Python (no response expected).
     */
    function fireBridge(action, payload = {}) {
        try {
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.sortmeout) {
                window.webkit.messageHandlers.sortmeout.postMessage(
                    JSON.stringify({ action, payload, callbackId: '' })
                );
            }
        } catch (e) {
            console.error('[Bridge] Fire error:', e);
        }
    }

    /**
     * Push notification from Python → JS (called via evaluateJavaScript).
     * Dispatches a CustomEvent on window.
     */
    window._bridgePush = function (event, data) {
        window.dispatchEvent(new CustomEvent('bridge:' + event, { detail: data }));
    };


    // ═══════════════════════════════════════════════════════════════════════
    // HIGH-LEVEL API — Organized by feature
    // ═══════════════════════════════════════════════════════════════════════

    const Bridge = {

        // ── AI Chat ──
        chat: {
            send: (message) => callBridge('chat_send', { message }, 120000),
            clear: () => callBridge('chat_clear'),
            getHistory: () => callBridge('chat_history'),
        },

        // ── Files ──
        files: {
            list: (path) => callBridge('files_list', { path }),
            organize: (path, dryRun) => callBridge('files_organize', { path, dryRun }, 60000),
            undo: () => callBridge('files_undo'),
            search: (query, path) => callBridge('files_search', { query, path }),
            getInfo: (path) => callBridge('files_info', { path }),
            move: (src, dst) => callBridge('files_move', { src, dst }),
            trash: (path) => callBridge('files_trash', { path }),
            tag: (path, tags) => callBridge('files_tag', { path, tags }),
        },

        // ── Email ──
        email: {
            list: (mailbox, account, count) => callBridge('email_list', { mailbox, account, count }),
            compose: (to, subject, body, attachment) => callBridge('email_compose', { to, subject, body, attachment }),
            reply: (to, subject, body) => callBridge('email_reply', { to, subject, body }),
            search: (query) => callBridge('email_search', { query }),
            searchAll: (query) => callBridge('email_search_all', { query }),
            getUnread: (account) => callBridge('email_unread', { account }),
            read: (messageId) => callBridge('email_read', { message_id: messageId }),
            markRead: (messageId) => callBridge('email_mark_read', { message_id: messageId }),
        },

        // ── Messages ──
        messages: {
            send: (to, body) => callBridge('msg_send', { to, body }),
            read: (contact, count) => callBridge('msg_read', { contact, count }),
            getChats: (count) => callBridge('msg_chats', { count }),
            getContacts: () => callBridge('msg_contacts'),
            checkPermissions: () => callBridge('msg_permissions'),
        },

        // ── Calendar ──
        calendar: {
            getEvents: (days) => callBridge('cal_events', { days }),
            createEvent: (data) => callBridge('cal_create', data),
            editEvent: (data) => callBridge('cal_edit', data),
            deleteEvent: (title) => callBridge('cal_delete', { title }),
        },

        // ── Contacts ──
        contacts: {
            search: (query) => callBridge('contacts_search', { query }),
            create: (data) => callBridge('contacts_create', data),
            edit: (name, data) => callBridge('contacts_edit', { name, ...data }),
            delete: (name) => callBridge('contacts_delete', { name }),
        },

        // ── Notes ──
        notes: {
            list: (folder) => callBridge('notes_list', { folder }),
            create: (title, body, folder) => callBridge('notes_create', { title, body, folder }),
            search: (query) => callBridge('notes_search', { query }),
            edit: (title, body) => callBridge('notes_edit', { title, body }),
            delete: (title) => callBridge('notes_delete', { title }),
        },

        // ── Presentations ──
        presentations: {
            create: (title, slides) => callBridge('pres_create', { title, slides }, 60000),
            addSlide: (file, title, body) => callBridge('pres_add_slide', { file, title, body }),
        },

        // ── Images ──
        images: {
            generate: (prompt, size, quality, style) =>
                callBridge('img_generate', { prompt, size, quality, style }, 120000),
            edit: (path, operations) =>
                callBridge('img_edit', { path, operations }, 60000),
            listGallery: () => callBridge('img_gallery'),
        },

        // ── Automation / Rules ──
        rules: {
            list: () => callBridge('rules_list'),
            create: (rule) => callBridge('rules_create', rule),
            delete: (name) => callBridge('rules_delete', { name }),
            toggle: (name, enabled) => callBridge('rules_toggle', { name, enabled }),
        },

        // ── Settings ──
        settings: {
            get: () => callBridge('settings_get'),
            update: (settings) => callBridge('settings_update', settings),
            getWatchFolders: () => callBridge('settings_watch_folders'),
            saveApiKey: (provider, key) => callBridge('settings_save_api_key', { provider, key }),
            getApiKeys: () => callBridge('settings_get_api_keys'),
            checkIntegrations: () => callBridge('settings_check_integrations'),
        },

        // ── System ──
        system: {
            status: () => callBridge('system_status'),
            openFolder: (path) => callBridge('system_open_folder', { path }),
            openFile: (path) => callBridge('system_open_file', { path }),
            clipboard: (text) => callBridge('system_clipboard', { text }),
            notify: (title, body) => fireBridge('system_notify', { title, body }),
            openPrivacySettings: () => callBridge('system_open_privacy'),
        },

        // ── Raw ──
        raw: callBridge,
        fire: fireBridge,
    };


    // ═══════════════════════════════════════════════════════════════════════
    // DEV FALLBACK — Simulated responses when not running in PyObjC
    // ═══════════════════════════════════════════════════════════════════════

    function _devFallback(action, payload) {
        console.log(`[Bridge DEV] ${action}`, payload);

        const mocks = {
            system_status: {
                ai: true,
                watcher: true,
                scheduler: true,
                monitor: false,
                version: '1.0.1',
            },
            chat_send: {
                response: `I received your message: "${payload.message || ''}". This is a dev-mode response. In production, Claude AI will answer here.`,
            },
            cal_events: {
                events: [
                    { summary: 'Team Standup', startDate: '2025-01-20T09:00:00', location: 'Zoom' },
                    { summary: 'Product Review', startDate: '2025-01-20T14:00:00', location: 'Conference Room' },
                ],
            },
            email_list: {
                emails: [
                    { from: 'boss@company.com', subject: 'Q4 Report', date: '2025-01-20', preview: 'Please review the attached...' },
                    { from: 'team@company.com', subject: 'Sprint Planning', date: '2025-01-19', preview: 'Hey everyone, let\'s discuss...' },
                ],
            },
            rules_list: {
                rules: [
                    { name: 'Organize Downloads', enabled: true, type: 'watcher', folder: '~/Downloads' },
                    { name: 'Archive Old Files', enabled: true, type: 'schedule', schedule: 'weekly' },
                ],
            },
            notes_list: {
                notes: [
                    { title: 'Project Ideas', preview: 'Collection of new project ideas...', date: '2025-01-18' },
                    { title: 'Meeting Notes', preview: 'Action items from last meeting...', date: '2025-01-17' },
                ],
            },
            settings_get: {
                darkMode: true,
                autoLaunch: false,
                notifications: true,
                model: 'claude-sonnet-4-20250514',
            },
        };

        return mocks[action] || { success: true, dev: true };
    }


    // Export
    window.Bridge = Bridge;

})();
