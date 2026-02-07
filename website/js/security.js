/**
 * SortMeOut Security Shield v2.0
 * Balanced protection — guards against bots and scraping
 * without breaking real user functionality.
 * © 2026 SortMeOut - Proprietary & Confidential
 */

(function () {
    'use strict';

    // ==========================================
    // Configuration
    // ==========================================
    const CONFIG = {
        enableKeyboardProtection: true, // Block DevTools shortcuts
        enableBasicBotProtection: true, // Block known automation tools
        enableDomProtection: true,      // Block injected scripts
    };

    // Allowed external script domains (Stripe, analytics, etc.)
    const ALLOWED_SCRIPT_DOMAINS = [
        'sortmeout',
        'stripe.com',
        'js.stripe.com',
        'googleapis.com',
        'gstatic.com',
        'google-analytics.com',
        'googletagmanager.com',
    ];

    // ==========================================
    // Keyboard Protection (DevTools shortcuts)
    // ==========================================

    if (CONFIG.enableKeyboardProtection) {
        document.addEventListener('keydown', function (e) {
            // Block: F12, Ctrl/Cmd+Shift+I/J/C, Ctrl/Cmd+U
            if (
                e.key === 'F12' ||
                (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C')) ||
                (e.ctrlKey && e.key === 'U') ||
                (e.metaKey && e.altKey && (e.key === 'I' || e.key === 'J')) ||
                (e.metaKey && e.key === 'U')
            ) {
                e.preventDefault();
                return false;
            }
        });
    }

    // ==========================================
    // Bot / Automation Detection
    // ==========================================

    if (CONFIG.enableBasicBotProtection) {
        function isBot() {
            // PhantomJS
            if (window._phantom || window.callPhantom) return true;
            // Selenium
            if (window.document.documentElement.getAttribute('webdriver')) return true;
            if (navigator.webdriver) return true;
            // Headless Chrome
            if (/HeadlessChrome/.test(navigator.userAgent)) return true;
            return false;
        }

        if (isBot()) {
            document.body.innerHTML =
                '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;"><h1>Access Denied</h1></div>';
            throw new Error('Automation detected');
        }
    }

    // ==========================================
    // DOM Protection (block injected scripts)
    // ==========================================

    if (CONFIG.enableDomProtection) {
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(function (node) {
                        if (node.tagName === 'SCRIPT' && node.src) {
                            const allowed = ALLOWED_SCRIPT_DOMAINS.some(
                                domain => node.src.includes(domain)
                            );
                            if (!allowed) {
                                node.remove();
                            }
                        }
                    });
                }
            });
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
        });
    }

    // ==========================================
    // View-source redirect
    // ==========================================

    if (window.location.protocol === 'view-source:') {
        window.location = window.location.href.replace('view-source:', '');
    }

    // ==========================================
    // Copyright meta tags
    // ==========================================

    const meta = document.createElement('meta');
    meta.setAttribute('name', 'copyright');
    meta.setAttribute('content', '© 2026 SortMeOut – All Rights Reserved');
    document.head.appendChild(meta);

    // ==========================================
    // Initialization
    // ==========================================

    window.__SECURITY__ = { status: 'protected', version: '2.0' };

})();
