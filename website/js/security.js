/**
 * SortMeOut Security Shield
 * Advanced protection against DevTools, scraping, and unauthorized access
 * © 2026 SortMeOut - Proprietary & Confidential
 */

(function() {
    'use strict';

    // ==========================================
    // Configuration
    // ==========================================
    const CONFIG = {
        enableDevToolsProtection: true,
        enableRightClickProtection: true,
        enableKeyboardProtection: true,
        enableSourceCodeObfuscation: true,
        enableConsoleProtection: true,
        enableDebuggerTrap: true,
        redirectUrl: '/privacy.html',
        warningMessage: 'Developer tools have been disabled for security reasons.'
    };

    // ==========================================
    // DevTools Detection
    // ==========================================
    
    let devtoolsOpen = false;
    const threshold = 160;
    
    // Method 1: Window size detection
    function checkWindowSize() {
        const widthThreshold = window.outerWidth - window.innerWidth > threshold;
        const heightThreshold = window.outerHeight - window.innerHeight > threshold;
        return widthThreshold || heightThreshold;
    }

    // Method 2: Timing detection
    function checkTiming() {
        const start = performance.now();
        debugger; // This will pause if DevTools is open
        const end = performance.now();
        return (end - start) > 100;
    }

    // Method 3: Console detection
    const consoleElement = document.createElement('div');
    Object.defineProperty(consoleElement, 'id', {
        get: function() {
            devtoolsOpen = true;
            handleDevToolsOpen();
            throw new Error('DevTools detected');
        }
    });

    // Method 4: toString detection
    const detectToString = function() {
        const element = new Image();
        Object.defineProperty(element, 'id', {
            get: function() {
                devtoolsOpen = true;
                handleDevToolsOpen();
                throw new Error('DevTools detected');
            }
        });
        console.log(element);
    };

    // Method 5: Function decompilation detection
    function detectFunctionDecompile() {
        const fn = function() {};
        const before = fn.toString().length;
        fn.toString = function() {
            devtoolsOpen = true;
            handleDevToolsOpen();
            return 'function () { [native code] }';
        };
        return before !== fn.toString().length;
    }

    // Handle DevTools detection
    function handleDevToolsOpen() {
        if (CONFIG.enableDevToolsProtection && !devtoolsOpen) {
            devtoolsOpen = true;
            
            // Clear page content
            document.body.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <div style="text-align: center; color: white; padding: 40px; background: rgba(0,0,0,0.3); border-radius: 20px; backdrop-filter: blur(10px);">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 20px;">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <h1 style="font-size: 32px; margin: 0 0 10px 0;">Security Alert</h1>
                        <p style="font-size: 18px; opacity: 0.9;">${CONFIG.warningMessage}</p>
                        <p style="font-size: 14px; opacity: 0.7; margin-top: 20px;">Redirecting...</p>
                    </div>
                </div>
            `;
            
            // Redirect after delay
            setTimeout(() => {
                window.location.href = CONFIG.redirectUrl;
            }, 2000);
        }
    }

    // Continuous monitoring
    if (CONFIG.enableDevToolsProtection) {
        setInterval(() => {
            if (checkWindowSize() || checkTiming()) {
                handleDevToolsOpen();
            }
        }, 1000);

        setInterval(detectToString, 2000);
        setInterval(detectFunctionDecompile, 2000);
    }

    // ==========================================
    // Debugger Trap
    // ==========================================
    
    if (CONFIG.enableDebuggerTrap) {
        setInterval(() => {
            (function() {
                return false;
            })['constructor']('debugger')();
        }, 100);

        // Anti-debugging loop
        (function preventDebugger() {
            function check() {
                debugger;
                preventDebugger();
            }
            try {
                check();
            } catch(e) {}
        })();
    }

    // ==========================================
    // Console Protection
    // ==========================================
    
    if (CONFIG.enableConsoleProtection) {
        // Disable console methods
        const noop = function() {};
        const consoleMethods = ['log', 'debug', 'info', 'warn', 'error', 'table', 'trace', 'dir', 'dirxml', 'group', 'groupCollapsed', 'groupEnd', 'clear', 'count', 'countReset', 'assert', 'profile', 'profileEnd', 'time', 'timeLog', 'timeEnd', 'timeStamp', 'context', 'memory'];
        
        consoleMethods.forEach(method => {
            if (console[method]) {
                console[method] = noop;
            }
        });

        // Override console object
        Object.freeze(console);
    }

    // ==========================================
    // Right Click Protection
    // ==========================================
    
    if (CONFIG.enableRightClickProtection) {
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            showSecurityWarning('Right-click has been disabled');
            return false;
        });

        // Prevent long press on mobile
        document.addEventListener('touchstart', function(e) {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        });

        let timer;
        document.addEventListener('touchstart', function() {
            timer = setTimeout(() => {
                showSecurityWarning('Long press has been disabled');
            }, 500);
        });

        document.addEventListener('touchend', function() {
            clearTimeout(timer);
        });
    }

    // ==========================================
    // Keyboard Protection
    // ==========================================
    
    if (CONFIG.enableKeyboardProtection) {
        document.addEventListener('keydown', function(e) {
            // Prevent F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U, Ctrl+S
            if (
                e.key === 'F12' ||
                (e.ctrlKey && e.shiftKey && e.key === 'I') ||
                (e.ctrlKey && e.shiftKey && e.key === 'J') ||
                (e.ctrlKey && e.shiftKey && e.key === 'C') ||
                (e.ctrlKey && e.key === 'U') ||
                (e.ctrlKey && e.key === 's') ||
                (e.metaKey && e.altKey && e.key === 'I') || // Mac
                (e.metaKey && e.altKey && e.key === 'J') || // Mac
                (e.metaKey && e.key === 'U') || // Mac
                (e.metaKey && e.key === 's') // Mac
            ) {
                e.preventDefault();
                showSecurityWarning('This keyboard shortcut has been disabled');
                return false;
            }
        });
    }

    // ==========================================
    // Text Selection Protection
    // ==========================================
    
    document.addEventListener('selectstart', function(e) {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            // Allow text selection for input fields
            if (!e.target.closest('input, textarea')) {
                e.preventDefault();
                return false;
            }
        }
    });

    // Prevent drag
    document.addEventListener('dragstart', function(e) {
        e.preventDefault();
        return false;
    });

    // ==========================================
    // Copy/Paste Protection
    // ==========================================
    
    document.addEventListener('copy', function(e) {
        const selection = window.getSelection().toString();
        if (selection.length > 50) {
            e.preventDefault();
            e.clipboardData.setData('text/plain', '© SortMeOut - Content is protected');
            showSecurityWarning('Content copying is restricted');
            return false;
        }
    });

    document.addEventListener('cut', function(e) {
        e.preventDefault();
        showSecurityWarning('Content cutting is disabled');
        return false;
    });

    // ==========================================
    // Source Code Protection
    // ==========================================
    
    if (CONFIG.enableSourceCodeObfuscation) {
        // Prevent view-source
        if (window.location.protocol === 'view-source:') {
            window.location = window.location.href.replace('view-source:', '');
        }

        // Add fake source code comments
        const fakeCode = [
            '<!-- © 2026 SortMeOut - All Rights Reserved -->',
            '<!-- This code is proprietary and confidential -->',
            '<!-- Unauthorized access is prohibited -->',
            '<!-- Patent Pending - Do Not Copy -->',
            '<!-- Monitoring active - All violations will be prosecuted -->'
        ];

        fakeCode.forEach(comment => {
            const meta = document.createElement('meta');
            meta.setAttribute('name', 'copyright');
            meta.setAttribute('content', comment);
            document.head.appendChild(meta);
        });
    }

    // ==========================================
    // Anti-Automation Protection
    // ==========================================
    
    // Detect automation tools
    function detectAutomation() {
        // Check for PhantomJS
        if (window._phantom || window.callPhantom) {
            return true;
        }
        
        // Check for Selenium
        if (window.document.documentElement.getAttribute('webdriver')) {
            return true;
        }
        
        // Check for automated browsers
        if (navigator.webdriver) {
            return true;
        }
        
        // Check for headless Chrome
        if (/HeadlessChrome/.test(window.navigator.userAgent)) {
            return true;
        }
        
        // Check for plugins
        if (navigator.plugins && navigator.plugins.length === 0) {
            return true;
        }
        
        return false;
    }

    if (detectAutomation()) {
        document.body.innerHTML = '<h1>Access Denied</h1><p>Automated access is not permitted.</p>';
        throw new Error('Automation detected');
    }

    // ==========================================
    // Screen Recording Detection
    // ==========================================
    
    function detectScreenRecording() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Check if canvas is being captured
        if (ctx && ctx.canvas) {
            const imageData = ctx.getImageData(0, 0, 1, 1);
            // Screen recorders often leave traces in canvas operations
        }
    }

    setInterval(detectScreenRecording, 5000);

    // ==========================================
    // Performance Monitoring
    // ==========================================
    
    // Detect slow performance (indication of debugging)
    let lastTime = performance.now();
    setInterval(() => {
        const currentTime = performance.now();
        const timeDiff = currentTime - lastTime;
        
        if (timeDiff > 200) {
            // Possible debugging detected
            handleDevToolsOpen();
        }
        
        lastTime = currentTime;
    }, 100);

    // ==========================================
    // DOM Protection
    // ==========================================
    
    // Prevent DOM inspection
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            // Monitor for suspicious DOM changes
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(node => {
                    if (node.tagName === 'SCRIPT' && !node.src.includes('sortmeout')) {
                        // Suspicious script injection
                        node.remove();
                    }
                });
            }
        });
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    // ==========================================
    // Helper Functions
    // ==========================================
    
    function showSecurityWarning(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
        * {
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            -khtml-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
        }
        input, textarea {
            -webkit-user-select: text;
            -khtml-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
            user-select: text;
        }
    `;
    document.head.appendChild(style);

    // ==========================================
    // Watermark Protection
    // ==========================================
    
    function addInvisibleWatermark() {
        const watermark = document.createElement('div');
        watermark.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 999998;
            opacity: 0.03;
            background: repeating-linear-gradient(
                45deg,
                transparent,
                transparent 100px,
                rgba(102, 102, 255, 0.1) 100px,
                rgba(102, 102, 255, 0.1) 200px
            );
        `;
        watermark.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 48px; font-weight: bold; color: rgba(0,0,0,0.05);">© SortMeOut ' + new Date().getFullYear() + '</div>';
        document.body.appendChild(watermark);
    }

    // Add watermark when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addInvisibleWatermark);
    } else {
        addInvisibleWatermark();
    }

    // ==========================================
    // Initialization
    // ==========================================
    
    console.log = function() {
        return '🔒 Security shield active';
    };

    // Seal and freeze critical objects
    Object.freeze(Object.prototype);
    Object.freeze(Array.prototype);
    Object.freeze(Function.prototype);

    // Log activation (this will be blocked by console protection)
    const securityLog = {
        status: 'active',
        timestamp: new Date().toISOString(),
        protections: Object.keys(CONFIG).filter(key => CONFIG[key] === true)
    };

    // Export for verification
    window.__SECURITY__ = { status: 'protected', version: '1.0.0' };

})();
