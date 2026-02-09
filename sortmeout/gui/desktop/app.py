"""
SortMeOut Desktop — Full-featured macOS desktop application.

Architecture:
    PyObjC (NSWindow + WKWebView) renders a modern HTML/CSS/JS frontend.
    Python ↔ JavaScript communication via WKScriptMessageHandler bridge.
    All 100+ backend features are exposed through the bridge layer.

Design:
    - Enterprise-grade UI inspired by Claude Desktop, Notion, Spotify
    - Dark theme with purple accent (matches SortMeOut brand)
    - Sidebar navigation, dashboard widgets, full-screen AI chat
    - Smooth animations, glassmorphism, responsive layout
"""

from __future__ import annotations

import json
import os
import sys
import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Detect AppKit availability ──
try:
    import objc
    from AppKit import (
        NSApplication,
        NSApp,
        NSWindow,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskFullSizeContentView,
        NSBackingStoreBuffered,
        NSScreen,
        NSColor,
        NSImage,
        NSApplicationActivationPolicyRegular,
        NSObject,
        NSMenu,
        NSMenuItem,
        NSToolbar,
        NSWindowTitleHidden,
        NSStatusBar,
    )
    from WebKit import (
        WKWebView,
        WKWebViewConfiguration,
        WKUserContentController,
        WKPreferences,
    )
    from Foundation import (
        NSMakeRect,
        NSURL,
        NSURLRequest,
        NSString,
        NSBundle,
    )

    HAS_APPKIT = True
except ImportError as e:
    logger.warning("AppKit/WebKit not available: %s", e)
    HAS_APPKIT = False


# ── Web directory (supports PyInstaller bundle) ──
if getattr(sys, "frozen", False):
    # Running inside PyInstaller bundle
    _base = sys._MEIPASS
    WEB_DIR = os.path.join(_base, "sortmeout", "gui", "desktop", "web")
else:
    WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class DesktopApp:
    """Main SortMeOut desktop application."""

    def __init__(self):
        if not HAS_APPKIT:
            raise RuntimeError("macOS AppKit required. Run on macOS with PyObjC installed.")
        self.window: Optional[NSWindow] = None
        self.webview: Optional[WKWebView] = None
        self.bridge: Optional[BridgeHandler] = None
        self._app = NSApplication.sharedApplication()

    def run(self):
        """Launch the desktop application."""
        self._app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        self._setup_menu()
        self._create_window()
        self._app.activateIgnoringOtherApps_(True)
        self._app.run()

    def _setup_menu(self):
        """Create the application menu bar."""
        menubar = NSMenu.alloc().init()

        # App menu
        app_menu_item = NSMenuItem.alloc().init()
        menubar.addItem_(app_menu_item)
        app_menu = NSMenu.alloc().init()

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit SortMeOut", "terminate:", "q"
        )
        app_menu.addItem_(quit_item)
        app_menu_item.setSubmenu_(app_menu)

        # Edit menu (for copy/paste in WebView)
        edit_menu_item = NSMenuItem.alloc().init()
        menubar.addItem_(edit_menu_item)
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")

        for title, action, key in [
            ("Undo", "undo:", "z"),
            ("Redo", "redo:", "Z"),
            ("Cut", "cut:", "x"),
            ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"),
            ("Select All", "selectAll:", "a"),
        ]:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
            edit_menu.addItem_(item)
        edit_menu_item.setSubmenu_(edit_menu)

        # View menu
        view_menu_item = NSMenuItem.alloc().init()
        menubar.addItem_(view_menu_item)
        view_menu = NSMenu.alloc().initWithTitle_("View")
        reload_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Reload", "reloadWebView:", "r"
        )
        view_menu.addItem_(reload_item)
        view_menu_item.setSubmenu_(view_menu)

        self._app.setMainMenu_(menubar)

    def _create_window(self):
        """Create the main application window with WKWebView."""
        # ── Window ──
        screen = NSScreen.mainScreen().frame()
        w, h = 1280, 820
        x = (screen.size.width - w) / 2
        y = (screen.size.height - h) / 2
        rect = NSMakeRect(x, y, w, h)

        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskFullSizeContentView
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("SortMeOut")
        self.window.setMinSize_((900, 600))
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(NSWindowTitleHidden)

        # Dark background
        bg = NSColor.colorWithRed_green_blue_alpha_(0.067, 0.067, 0.09, 1.0)  # #111117
        self.window.setBackgroundColor_(bg)

        # ── WebView configuration ──
        config = WKWebViewConfiguration.alloc().init()
        prefs = config.preferences()
        prefs.setValue_forKey_(True, "developerExtrasEnabled")
        prefs.setValue_forKey_(True, "javaScriptCanAccessClipboard")

        # Script message handler (JS → Python bridge)
        content_controller = config.userContentController()
        self.bridge = BridgeHandler.alloc().init()
        content_controller.addScriptMessageHandler_name_(self.bridge, "sortmeout")

        # ── WebView ──
        content_rect = self.window.contentView().bounds()
        self.webview = WKWebView.alloc().initWithFrame_configuration_(content_rect, config)
        self.webview.setAutoresizingMask_(0x12)  # Width + Height flexible
        self.webview.setValue_forKey_(False, "drawsBackground")

        # Store reference for bridge callbacks
        self.bridge.webview = self.webview

        # Load the HTML frontend
        index_path = os.path.join(WEB_DIR, "index.html")
        if os.path.exists(index_path):
            url = NSURL.fileURLWithPath_(index_path)
            web_dir_url = NSURL.fileURLWithPath_isDirectory_(WEB_DIR, True)
            self.webview.loadFileURL_allowingReadAccessToURL_(url, web_dir_url)
        else:
            logger.error("index.html not found at %s", index_path)
            # Fallback: inline error page
            self.webview.loadHTMLString_baseURL_(
                "<h1 style='color:white;font-family:sans-serif;padding:40px'>"
                "Error: web/index.html not found</h1>",
                None,
            )

        self.window.contentView().addSubview_(self.webview)
        self.window.makeKeyAndOrderFront_(None)

        # Set window delegate for app termination
        delegate = WindowDelegate.alloc().init()
        self.window.setDelegate_(delegate)


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE — JavaScript ↔ Python communication
# ═══════════════════════════════════════════════════════════════════════════════


if HAS_APPKIT:

    class BridgeHandler(NSObject):
        """Handles messages from JavaScript (WKScriptMessageHandler)."""

        webview = objc.ivar()

        def userContentController_didReceiveScriptMessage_(self, controller, message):
            """Called when JS sends: window.webkit.messageHandlers.sortmeout.postMessage(...)"""
            try:
                data = message.body()
                if isinstance(data, str):
                    data = json.loads(data)

                action = data.get("action", "")
                payload = data.get("payload", {})
                callback_id = data.get("callbackId", "")

                # Process in background thread to avoid blocking UI
                threading.Thread(
                    target=self._process_message,
                    args=(action, payload, callback_id),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error("Bridge message error: %s", e)
                self._send_error(data.get("callbackId", ""), str(e))

        def _process_message(self, action: str, payload: dict, callback_id: str):
            """Process a bridge message and send result back to JS."""
            try:
                result = self._handle_action(action, payload)
                self._send_response(callback_id, result)
            except Exception as e:
                logger.error("Bridge action error [%s]: %s", action, e)
                self._send_error(callback_id, str(e))

        def _handle_action(self, action: str, payload: dict) -> dict:
            """Route action to the appropriate Python handler."""
            from sortmeout.gui.desktop.bridge import handle_bridge_action

            return handle_bridge_action(action, payload)

        def _send_response(self, callback_id: str, data: dict):
            """Send success response back to JavaScript."""
            js = f"window._bridgeCallback('{callback_id}', {json.dumps(data)}, null);"
            self._eval_js(js)

        def _send_error(self, callback_id: str, error: str):
            """Send error response back to JavaScript."""
            safe_err = json.dumps(error)
            js = f"window._bridgeCallback('{callback_id}', null, {safe_err});"
            self._eval_js(js)

        def _eval_js(self, js_code: str):
            """Evaluate JavaScript in the WebView (thread-safe)."""

            def run_on_main():
                if self.webview:
                    self.webview.evaluateJavaScript_completionHandler_(js_code, None)

            # Dispatch to main thread
            try:
                from dispatch import dispatch_async, dispatch_get_main_queue

                dispatch_async(dispatch_get_main_queue(), run_on_main)
            except ImportError:
                # Fallback: just run directly (may not be thread-safe)
                run_on_main()

    class WindowDelegate(NSObject):
        """Handle window events."""

        def windowWillClose_(self, notification):
            """Terminate app when window closes."""
            NSApp.terminate_(self)

        def windowDidBecomeKey_(self, notification):
            """Window became active."""
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def launch_desktop():
    """Launch the SortMeOut desktop application."""
    app = DesktopApp()
    app.run()


if __name__ == "__main__":
    launch_desktop()
