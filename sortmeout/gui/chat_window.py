"""
SortMeOut AI Chat Window - Persistent chat interface.
Uses a simpler approach that works reliably.
"""

import os
import sys
import json
import threading
import queue
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from AppKit import (
        NSApplication,
        NSApp,
        NSWindow,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskMiniaturizable,
        NSBackingStoreBuffered,
        NSTextView,
        NSScrollView,
        NSTextField,
        NSButton,
        NSFont,
        NSColor,
        NSView,
        NSBezelStyleRounded,
        NSMutableAttributedString,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
        NSAttributedString,
        NSViewWidthSizable,
        NSViewHeightSizable,
        NSViewMinYMargin,
        NSApplicationActivationPolicyRegular,
        NSFloatingWindowLevel,
        NSTimer,
        NSRunLoop,
        NSDefaultRunLoopMode,
        NSMenu,
        NSMenuItem,
    )
    from Foundation import NSObject, NSMakeRect, NSSize, NSDate
    import objc

    HAS_APPKIT = True
except ImportError as e:
    print(f"AppKit import error: {e}")
    HAS_APPKIT = False

CONFIG_DIR = os.path.expanduser("~/.config/sortmeout")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")


def load_api_key():
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except:
            pass
    return os.environ.get("ANTHROPIC_API_KEY")


class ChatWindowDelegate(NSObject):
    """Delegate class to handle button actions."""

    def init(self):
        self = objc.super(ChatWindowDelegate, self).init()
        if self is None:
            return None
        self.chat_window = None
        return self

    @objc.python_method
    def set_chat_window(self, chat_window):
        self.chat_window = chat_window

    def sendClicked_(self, sender):
        """Handle send button click or Enter key."""
        if self.chat_window:
            self.chat_window.do_send()

    def checkQueue_(self, timer):
        """Check for responses from AI thread."""
        if self.chat_window:
            self.chat_window.check_queue()


class ChatWindow:
    """Persistent chat window for SortMeOut AI."""

    def __init__(self):
        self.window = None
        self.chat_view = None
        self.input_field = None
        self.send_button = None
        self.status_label = None
        self.assistant = None
        self.is_processing = False
        self.response_queue = queue.Queue()
        self.timer = None

        # Create delegate for button actions
        self.delegate = ChatWindowDelegate.alloc().init()
        self.delegate.set_chat_window(self)

        # Initialize assistant
        api_key = load_api_key()
        if api_key:
            try:
                from sortmeout.ai.assistant import FileAssistant

                self.assistant = FileAssistant(api_key=api_key)
            except Exception as e:
                print(f"Assistant init error: {e}")

        self._create_window()
        self._start_timer()

    def _create_window(self):
        """Create the chat window."""
        frame = NSMakeRect(200, 200, 550, 650)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskMiniaturizable
        )

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("🤖 SortMeOut AI Assistent")
        self.window.setMinSize_(NSSize(450, 400))
        self.window.setReleasedWhenClosed_(False)

        content = self.window.contentView()

        # === Chat area (scrollable) ===
        scroll_frame = NSMakeRect(15, 90, 520, 500)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(1)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        text_frame = NSMakeRect(0, 0, 500, 480)
        self.chat_view = NSTextView.alloc().initWithFrame_(text_frame)
        self.chat_view.setEditable_(False)
        self.chat_view.setSelectable_(True)
        self.chat_view.setRichText_(True)
        self.chat_view.setFont_(NSFont.systemFontOfSize_(14))
        self.chat_view.setBackgroundColor_(NSColor.textBackgroundColor())
        self.chat_view.setTextContainerInset_(NSSize(12, 12))
        self.chat_view.setAllowsUndo_(True)
        self.chat_view.setUsesFontPanel_(False)
        # Viktigt: låt text växa vertikalt
        self.chat_view.setVerticallyResizable_(True)
        self.chat_view.setHorizontallyResizable_(False)
        self.chat_view.textContainer().setWidthTracksTextView_(True)
        self.chat_view.textContainer().setContainerSize_(NSSize(500, 1e7))

        scroll_view.setDocumentView_(self.chat_view)
        content.addSubview_(scroll_view)  # Lägg till scroll_view, inte chat_view

        # === Status label ===
        status_frame = NSMakeRect(15, 55, 520, 25)
        self.status_label = NSTextField.alloc().initWithFrame_(status_frame)
        self.status_label.setBezeled_(False)
        self.status_label.setDrawsBackground_(False)
        self.status_label.setEditable_(False)
        self.status_label.setSelectable_(False)
        self.status_label.setTextColor_(NSColor.systemGrayColor())
        self.status_label.setFont_(NSFont.systemFontOfSize_(12))
        self.status_label.setStringValue_("")
        self.status_label.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        content.addSubview_(self.status_label)

        # === Input field ===
        input_frame = NSMakeRect(15, 15, 430, 30)
        self.input_field = NSTextField.alloc().initWithFrame_(input_frame)
        self.input_field.setPlaceholderString_("Skriv vad du vill göra...")
        self.input_field.setFont_(NSFont.systemFontOfSize_(14))
        self.input_field.setEditable_(True)
        self.input_field.setSelectable_(True)
        self.input_field.setBezeled_(True)
        self.input_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        content.addSubview_(self.input_field)

        # === Send button ===
        button_frame = NSMakeRect(455, 15, 80, 30)
        self.send_button = NSButton.alloc().initWithFrame_(button_frame)
        self.send_button.setTitle_("Skicka")
        self.send_button.setBezelStyle_(NSBezelStyleRounded)
        self.send_button.setAutoresizingMask_(NSViewMinYMargin)
        self.send_button.setTarget_(self.delegate)
        self.send_button.setAction_("sendClicked:")
        content.addSubview_(self.send_button)

        # Set input field action (Enter key)
        self.input_field.setTarget_(self.delegate)
        self.input_field.setAction_("sendClicked:")

        # Welcome message
        self._add_message(
            "🤖 SortMeOut",
            """Hej! Jag är din AI-assistent för filorganisation.

Jag kan hjälpa dig med:
• Organisera och flytta filer automatiskt
• Analysera dokument och föreslå var de ska ligga
• Skapa nya mappar och strukturer
• Städa upp i Downloads, Desktop och andra mappar
• Hitta och sortera filer efter typ, datum eller innehåll

Skriv fritt vad du vill göra så hjälper jag dig!""",
            is_ai=True,
        )

    def _start_timer(self):
        """Start timer to check for responses."""
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.1, self.delegate, "checkQueue:", None, True
        )

    def check_queue(self):
        """Check for responses from AI thread."""
        try:
            while True:
                msg_type, data = self.response_queue.get_nowait()
                if msg_type == "response":
                    self._add_message("🤖 SortMeOut", data, is_ai=True)
                    self._set_status("")
                    self.is_processing = False
                    self.send_button.setEnabled_(True)
                elif msg_type == "status":
                    self._set_status(data)
                elif msg_type == "error":
                    self._add_message("⚠️ Fel", data, is_ai=True)
                    self._set_status("")
                    self.is_processing = False
                    self.send_button.setEnabled_(True)
        except queue.Empty:
            pass

    def _add_message(self, sender, text, is_ai=False):
        """Add a message to the chat."""
        storage = self.chat_view.textStorage()

        # Add spacing if not first message
        if storage.length() > 0:
            storage.appendAttributedString_(NSAttributedString.alloc().initWithString_("\n\n"))

        # Sender name (bold, colored)
        sender_color = NSColor.systemGrayColor() if is_ai else NSColor.systemBlueColor()
        sender_attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(14),
            NSForegroundColorAttributeName: sender_color,
        }
        sender_str = NSAttributedString.alloc().initWithString_attributes_(
            f"{sender}\n", sender_attrs
        )
        storage.appendAttributedString_(sender_str)

        # Message text
        text_attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(14),
            NSForegroundColorAttributeName: NSColor.labelColor(),
        }
        text_str = NSAttributedString.alloc().initWithString_attributes_(text, text_attrs)
        storage.appendAttributedString_(text_str)

        # Scroll to bottom
        self.chat_view.scrollToEndOfDocument_(None)

    def _set_status(self, text):
        """Set status text."""
        self.status_label.setStringValue_(text)

    def do_send(self):
        """Handle send button click or Enter key."""
        message = self.input_field.stringValue()
        if not message or not message.strip():
            return

        if self.is_processing:
            return

        # Clear input and add user message
        self.input_field.setStringValue_("")
        self._add_message("👤 Du", message.strip(), is_ai=False)

        # Start processing
        self.is_processing = True
        self.send_button.setEnabled_(False)
        self._set_status("⏳ Analyserar och tänker...")

        # Process in background
        thread = threading.Thread(target=self._process_ai, args=(message,))
        thread.daemon = True
        thread.start()

    def _process_ai(self, message):
        """Process message with AI (background thread)."""
        try:
            # Update status
            self.response_queue.put(("status", "⏳ Bearbetar din förfrågan..."))

            if not self.assistant:
                self.response_queue.put(
                    (
                        "error",
                        "AI-assistenten kunde inte initieras. Kontrollera din API-nyckel i inställningarna.",
                    )
                )
                return

            # Get response
            self.response_queue.put(("status", "🤔 Tänker..."))
            response = self.assistant.chat(message)

            self.response_queue.put(("response", response))

        except Exception as e:
            self.response_queue.put(("error", f"Ett fel uppstod: {str(e)}"))

    def show(self):
        """Show the window."""
        self.window.makeKeyAndOrderFront_(None)
        self.input_field.becomeFirstResponder()
        NSApp.activateIgnoringOtherApps_(True)


# Global instance
_chat_window = None


def show_chat_window():
    """Show the persistent chat window."""
    global _chat_window

    if not HAS_APPKIT:
        print("AppKit not available")
        return False

    if _chat_window is None:
        _chat_window = ChatWindow()

    _chat_window.show()
    return True


def main():
    """Run as standalone."""
    if not HAS_APPKIT:
        print("AppKit not available")
        return

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # Skapa Edit-meny för Cmd+C, Cmd+V etc
    menubar = NSMenu.alloc().init()
    app.setMainMenu_(menubar)

    # App-meny
    app_menu_item = NSMenuItem.alloc().init()
    menubar.addItem_(app_menu_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItemWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
    app_menu_item.setSubmenu_(app_menu)

    # Edit-meny (behövs för Cmd+C, Cmd+V)
    edit_menu_item = NSMenuItem.alloc().init()
    menubar.addItem_(edit_menu_item)
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
    edit_menu_item.setSubmenu_(edit_menu)

    window = ChatWindow()
    window.show()

    # Ensure app can receive key events
    app.activateIgnoringOtherApps_(True)

    # Make input field first responder
    window.window.makeFirstResponder_(window.input_field)

    app.run()


if __name__ == "__main__":
    main()
