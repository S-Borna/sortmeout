"""
SortMeOut AI Chat Window - Premium Edition
A beautifully crafted chat interface with modern design.
"""

import os
import sys
import json
import threading
import queue
from pathlib import Path
from datetime import datetime

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
        NSWindowStyleMaskFullSizeContentView,
        NSBackingStoreBuffered,
        NSTextView,
        NSScrollView,
        NSTextField,
        NSButton,
        NSFont,
        NSColor,
        NSView,
        NSBox,
        NSBoxCustom,
        NSBezelStyleRounded,
        NSMutableAttributedString,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
        NSParagraphStyleAttributeName,
        NSAttributedString,
        NSViewWidthSizable,
        NSViewHeightSizable,
        NSViewMinYMargin,
        NSViewMaxYMargin,
        NSApplicationActivationPolicyRegular,
        NSFloatingWindowLevel,
        NSTimer,
        NSRunLoop,
        NSDefaultRunLoopMode,
        NSMenu,
        NSMenuItem,
        NSImage,
        NSImageNameComputer,
        NSFontWeightMedium,
        NSFontWeightSemibold,
        NSFontWeightBold,
        NSTextAlignmentLeft,
        NSTextAlignmentRight,
        NSLineBreakByWordWrapping,
        NSMutableParagraphStyle,
        NSVisualEffectView,
        NSVisualEffectMaterialSidebar,
        NSVisualEffectMaterialHUDWindow,
        NSVisualEffectMaterialPopover,
        NSVisualEffectBlendingModeBehindWindow,
        NSWindowTitleHidden,
        NSWindowCollectionBehaviorFullScreenPrimary,
        NSBezierPath,
        NSShadow,
        NSGraphicsContext,
        NSCompositingOperationSourceOver,
    )
    from Foundation import (
        NSObject,
        NSMakeRect,
        NSSize,
        NSDate,
        NSMakePoint,
        NSMutableDictionary,
    )
    from Quartz import CGColorCreateGenericRGB
    import objc

    HAS_APPKIT = True
except ImportError as e:
    print(f"AppKit import error: {e}")
    HAS_APPKIT = False

CONFIG_DIR = os.path.expanduser("~/.config/sortmeout")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")


# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    """Premium color palette for the chat interface."""
    
    # Background colors
    WINDOW_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.11, 0.11, 0.12, 1.0)
    CHAT_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.08, 0.08, 0.09, 1.0)
    INPUT_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.15, 0.15, 0.16, 1.0)
    
    # Message bubbles
    USER_BUBBLE = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.25, 0.52, 0.96, 1.0)
    USER_BUBBLE_GRADIENT = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.18, 0.42, 0.85, 1.0)
    AI_BUBBLE = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.18, 0.18, 0.20, 1.0)
    AI_BUBBLE_BORDER = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.25, 0.25, 0.28, 1.0)
    
    # Text colors
    TEXT_PRIMARY = NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 1.0, 1.0, 1.0)
    TEXT_SECONDARY = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.7, 0.7, 0.75, 1.0)
    TEXT_MUTED = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0.5, 0.55, 1.0)
    
    # Accent colors
    ACCENT_PRIMARY = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.58, 1.0, 1.0)
    ACCENT_SUCCESS = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.30, 0.85, 0.55, 1.0)
    ACCENT_WARNING = NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.75, 0.25, 1.0)
    ACCENT_ERROR = NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.40, 0.40, 1.0)
    
    # Button colors
    BUTTON_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.25, 0.52, 0.96, 1.0)
    BUTTON_HOVER = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.60, 1.0, 1.0)
    BUTTON_DISABLED = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.25, 0.25, 0.28, 1.0)
    
    # Dividers and borders
    DIVIDER = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.22, 0.22, 0.24, 1.0)
    BORDER_SUBTLE = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.20, 0.20, 0.22, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════════

class Typography:
    """Premium typography settings."""
    
    @staticmethod
    def heading():
        return NSFont.systemFontOfSize_weight_(20, NSFontWeightSemibold)
    
    @staticmethod
    def subheading():
        return NSFont.systemFontOfSize_weight_(14, NSFontWeightMedium)
    
    @staticmethod
    def body():
        return NSFont.systemFontOfSize_weight_(14, NSFontWeightMedium)
    
    @staticmethod
    def body_regular():
        return NSFont.systemFontOfSize_(14)
    
    @staticmethod
    def caption():
        return NSFont.systemFontOfSize_(11)
    
    @staticmethod
    def timestamp():
        return NSFont.monospacedDigitSystemFontOfSize_weight_(10, NSFontWeightMedium)
    
    @staticmethod
    def code():
        return NSFont.monospacedSystemFontOfSize_weight_(13, NSFontWeightMedium)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_api_key():
    """Load API key from config."""
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except:
            pass
    return os.environ.get("ANTHROPIC_API_KEY")


def format_time(dt=None):
    """Format timestamp elegantly."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%H:%M")


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

class PremiumInputField(NSTextField):
    """Custom styled input field with premium appearance."""
    
    @objc.python_method
    def setup_style(self):
        self.setBezeled_(False)
        self.setDrawsBackground_(True)
        self.setBackgroundColor_(Colors.INPUT_BG)
        self.setTextColor_(Colors.TEXT_PRIMARY)
        self.setFont_(Typography.body())
        self.setFocusRingType_(1)  # None
        
        # Rounded corners via layer
        self.setWantsLayer_(True)
        self.layer().setCornerRadius_(12)
        self.layer().setBorderWidth_(1)
        self.layer().setBorderColor_(Colors.BORDER_SUBTLE.CGColor())


class PremiumButton(NSButton):
    """Custom styled button with premium appearance."""
    
    @objc.python_method  
    def setup_style(self, primary=True):
        self.setWantsLayer_(True)
        self.setBordered_(False)
        self.setFont_(Typography.subheading())
        
        if primary:
            self.layer().setBackgroundColor_(Colors.BUTTON_BG.CGColor())
            self.setContentTintColor_(Colors.TEXT_PRIMARY)
        else:
            self.layer().setBackgroundColor_(Colors.INPUT_BG.CGColor())
            self.setContentTintColor_(Colors.TEXT_SECONDARY)
        
        self.layer().setCornerRadius_(10)


# ═══════════════════════════════════════════════════════════════════════════════
# DELEGATE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

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

    def clearChat_(self, sender):
        """Clear chat history."""
        if self.chat_window:
            self.chat_window.clear_chat()


# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM CHAT WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class ChatWindow:
    """Premium chat window for SortMeOut AI."""

    def __init__(self):
        self.window = None
        self.chat_view = None
        self.input_field = None
        self.send_button = None
        self.status_label = None
        self.status_indicator = None
        self.header_view = None
        self.assistant = None
        self.is_processing = False
        self.response_queue = queue.Queue()
        self.timer = None
        self.message_count = 0
        self.animation_state = 0

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
        """Create the premium chat window."""
        # Window frame - elegant proportions
        frame = NSMakeRect(150, 150, 480, 680)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskFullSizeContentView
        )

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        
        # Premium window setup
        self.window.setTitle_("SortMeOut AI")
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(NSWindowTitleHidden)
        self.window.setMinSize_(NSSize(400, 500))
        self.window.setReleasedWhenClosed_(False)
        self.window.setBackgroundColor_(Colors.WINDOW_BG)
        self.window.setMovableByWindowBackground_(True)
        
        # Enable vibrancy for modern look
        self.window.setOpaque_(False)

        content = self.window.contentView()
        content.setWantsLayer_(True)
        content.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())
        
        content_height = 680
        
        # ─────────────────────────────────────────────────────────────────────
        # HEADER SECTION (60px)
        # ─────────────────────────────────────────────────────────────────────
        header_height = 60
        header_frame = NSMakeRect(0, content_height - header_height, 480, header_height)
        self.header_view = NSView.alloc().initWithFrame_(header_frame)
        self.header_view.setWantsLayer_(True)
        self.header_view.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())
        self.header_view.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        
        # App icon/avatar
        icon_frame = NSMakeRect(20, 12, 36, 36)
        icon_view = NSView.alloc().initWithFrame_(icon_frame)
        icon_view.setWantsLayer_(True)
        icon_view.layer().setCornerRadius_(18)
        icon_view.layer().setBackgroundColor_(Colors.ACCENT_PRIMARY.CGColor())
        self.header_view.addSubview_(icon_view)
        
        # Icon label (emoji)
        icon_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 12, 36, 36))
        icon_label.setStringValue_("🤖")
        icon_label.setBezeled_(False)
        icon_label.setDrawsBackground_(False)
        icon_label.setEditable_(False)
        icon_label.setSelectable_(False)
        icon_label.setAlignment_(1)  # Center
        icon_label.setFont_(NSFont.systemFontOfSize_(18))
        self.header_view.addSubview_(icon_label)
        
        # Title
        title_frame = NSMakeRect(66, 28, 300, 22)
        title_label = NSTextField.alloc().initWithFrame_(title_frame)
        title_label.setStringValue_("SortMeOut AI")
        title_label.setBezeled_(False)
        title_label.setDrawsBackground_(False)
        title_label.setEditable_(False)
        title_label.setSelectable_(False)
        title_label.setTextColor_(Colors.TEXT_PRIMARY)
        title_label.setFont_(Typography.heading())
        self.header_view.addSubview_(title_label)
        
        # Subtitle/Status
        subtitle_frame = NSMakeRect(66, 10, 300, 18)
        self.header_status = NSTextField.alloc().initWithFrame_(subtitle_frame)
        self.header_status.setStringValue_("Redo att hjälpa dig")
        self.header_status.setBezeled_(False)
        self.header_status.setDrawsBackground_(False)
        self.header_status.setEditable_(False)
        self.header_status.setSelectable_(False)
        self.header_status.setTextColor_(Colors.TEXT_MUTED)
        self.header_status.setFont_(Typography.caption())
        self.header_view.addSubview_(self.header_status)
        
        # Status indicator dot
        dot_frame = NSMakeRect(450, 26, 10, 10)
        self.status_dot = NSView.alloc().initWithFrame_(dot_frame)
        self.status_dot.setWantsLayer_(True)
        self.status_dot.layer().setCornerRadius_(5)
        self.status_dot.layer().setBackgroundColor_(Colors.ACCENT_SUCCESS.CGColor())
        self.status_dot.setAutoresizingMask_(NSViewMinYMargin)
        self.header_view.addSubview_(self.status_dot)
        
        content.addSubview_(self.header_view)
        
        # Header divider
        divider_frame = NSMakeRect(20, content_height - header_height - 1, 440, 1)
        divider = NSView.alloc().initWithFrame_(divider_frame)
        divider.setWantsLayer_(True)
        divider.layer().setBackgroundColor_(Colors.DIVIDER.CGColor())
        divider.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        content.addSubview_(divider)
        
        # ─────────────────────────────────────────────────────────────────────
        # CHAT AREA
        # ─────────────────────────────────────────────────────────────────────
        chat_top = content_height - header_height - 10
        chat_height = chat_top - 80  # Leave room for input
        
        scroll_frame = NSMakeRect(0, 75, 480, chat_height)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setBorderType_(0)  # No border
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setDrawsBackground_(True)
        scroll_view.setBackgroundColor_(Colors.CHAT_BG)
        
        # Custom scroller appearance
        scroll_view.setScrollerStyle_(1)  # Overlay
        scroll_view.verticalScroller().setKnobStyle_(2)  # Dark
        
        text_frame = NSMakeRect(0, 0, 460, chat_height)
        self.chat_view = NSTextView.alloc().initWithFrame_(text_frame)
        self.chat_view.setEditable_(False)
        self.chat_view.setSelectable_(True)
        self.chat_view.setRichText_(True)
        self.chat_view.setFont_(Typography.body_regular())
        self.chat_view.setBackgroundColor_(Colors.CHAT_BG)
        self.chat_view.setTextColor_(Colors.TEXT_PRIMARY)
        self.chat_view.setTextContainerInset_(NSSize(20, 20))
        self.chat_view.setAllowsUndo_(True)
        self.chat_view.setUsesFontPanel_(False)
        self.chat_view.setVerticallyResizable_(True)
        self.chat_view.setHorizontallyResizable_(False)
        self.chat_view.textContainer().setWidthTracksTextView_(True)
        self.chat_view.textContainer().setContainerSize_(NSSize(440, 1e7))
        
        scroll_view.setDocumentView_(self.chat_view)
        content.addSubview_(scroll_view)
        
        # ─────────────────────────────────────────────────────────────────────
        # INPUT SECTION
        # ─────────────────────────────────────────────────────────────────────
        input_section_frame = NSMakeRect(0, 0, 480, 75)
        input_section = NSView.alloc().initWithFrame_(input_section_frame)
        input_section.setWantsLayer_(True)
        input_section.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())
        input_section.setAutoresizingMask_(NSViewWidthSizable | NSViewMaxYMargin)
        
        # Input container with rounded corners
        input_container_frame = NSMakeRect(16, 16, 448, 44)
        input_container = NSView.alloc().initWithFrame_(input_container_frame)
        input_container.setWantsLayer_(True)
        input_container.layer().setCornerRadius_(22)
        input_container.layer().setBackgroundColor_(Colors.INPUT_BG.CGColor())
        input_container.layer().setBorderWidth_(1)
        input_container.layer().setBorderColor_(Colors.BORDER_SUBTLE.CGColor())
        input_container.setAutoresizingMask_(NSViewWidthSizable)
        
        # Input field (inside container)
        input_frame = NSMakeRect(16, 8, 360, 28)
        self.input_field = NSTextField.alloc().initWithFrame_(input_frame)
        self.input_field.setPlaceholderString_("Skriv ett meddelande...")
        self.input_field.setBezeled_(False)
        self.input_field.setDrawsBackground_(False)
        self.input_field.setTextColor_(Colors.TEXT_PRIMARY)
        self.input_field.setFont_(Typography.body())
        self.input_field.setFocusRingType_(1)  # None
        self.input_field.setEditable_(True)
        self.input_field.setSelectable_(True)
        self.input_field.setAutoresizingMask_(NSViewWidthSizable)
        input_container.addSubview_(self.input_field)
        
        # Send button (inside container)
        button_frame = NSMakeRect(390, 6, 50, 32)
        self.send_button = NSButton.alloc().initWithFrame_(button_frame)
        self.send_button.setTitle_("➤")
        self.send_button.setBordered_(False)
        self.send_button.setWantsLayer_(True)
        self.send_button.layer().setCornerRadius_(16)
        self.send_button.layer().setBackgroundColor_(Colors.BUTTON_BG.CGColor())
        self.send_button.setFont_(NSFont.systemFontOfSize_(16))
        self.send_button.setContentTintColor_(Colors.TEXT_PRIMARY)
        self.send_button.setTarget_(self.delegate)
        self.send_button.setAction_("sendClicked:")
        self.send_button.setAutoresizingMask_(NSViewMinYMargin)
        input_container.addSubview_(self.send_button)
        
        input_section.addSubview_(input_container)
        content.addSubview_(input_section)
        
        # Set input field action (Enter key)
        self.input_field.setTarget_(self.delegate)
        self.input_field.setAction_("sendClicked:")

        # ─────────────────────────────────────────────────────────────────────
        # WELCOME MESSAGE
        # ─────────────────────────────────────────────────────────────────────
        self._add_welcome_message()

    def _add_welcome_message(self):
        """Add styled welcome message."""
        self._add_message(
            "SortMeOut AI",
            """Välkommen! 👋

Jag är din personliga AI-assistent för filorganisation. Jag kan hjälpa dig med:

✦  Organisera filer automatiskt
✦  Analysera dokument och föreslå placering  
✦  Skapa smarta mappstrukturer
✦  Städa upp i Downloads och Desktop
✦  Sortera efter typ, datum eller innehåll

Berätta vad du vill göra så hjälper jag dig!""",
            is_ai=True,
            show_timestamp=False
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
                    self._add_message("SortMeOut AI", data, is_ai=True)
                    self._set_status("Redo att hjälpa dig", processing=False)
                    self.is_processing = False
                    self.send_button.setEnabled_(True)
                    self.send_button.layer().setBackgroundColor_(Colors.BUTTON_BG.CGColor())
                elif msg_type == "status":
                    self._set_status(data, processing=True)
                elif msg_type == "error":
                    self._add_message("System", f"⚠️ {data}", is_ai=True, is_error=True)
                    self._set_status("Ett fel uppstod", processing=False)
                    self.is_processing = False
                    self.send_button.setEnabled_(True)
                    self.send_button.layer().setBackgroundColor_(Colors.BUTTON_BG.CGColor())
        except queue.Empty:
            pass
        
        # Animate status dot when processing
        if self.is_processing:
            self.animation_state = (self.animation_state + 1) % 20
            alpha = 0.5 + 0.5 * abs((self.animation_state - 10) / 10.0)
            pulse_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.75, 0.25, alpha)
            self.status_dot.layer().setBackgroundColor_(pulse_color.CGColor())

    def _add_message(self, sender, text, is_ai=False, show_timestamp=True, is_error=False):
        """Add a beautifully styled message to the chat."""
        storage = self.chat_view.textStorage()
        self.message_count += 1

        # Add spacing between messages
        if storage.length() > 0:
            spacing = NSAttributedString.alloc().initWithString_("\n\n")
            storage.appendAttributedString_(spacing)

        # Paragraph style for message
        para_style = NSMutableParagraphStyle.alloc().init()
        para_style.setLineSpacing_(4)
        para_style.setParagraphSpacing_(8)
        para_style.setLineBreakMode_(NSLineBreakByWordWrapping)

        # ── Message Header ──
        if is_ai:
            sender_icon = "🤖" if not is_error else "⚠️"
            sender_color = Colors.ACCENT_PRIMARY if not is_error else Colors.ACCENT_WARNING
        else:
            sender_icon = "👤"
            sender_color = Colors.USER_BUBBLE

        header_attrs = {
            NSFontAttributeName: Typography.subheading(),
            NSForegroundColorAttributeName: sender_color,
            NSParagraphStyleAttributeName: para_style,
        }
        
        timestamp = format_time() if show_timestamp else ""
        header_text = f"{sender_icon}  {sender}"
        if timestamp:
            header_text += f"  ·  {timestamp}"
        header_text += "\n"
        
        header_str = NSAttributedString.alloc().initWithString_attributes_(
            header_text, header_attrs
        )
        storage.appendAttributedString_(header_str)

        # ── Message Body ──
        body_para = NSMutableParagraphStyle.alloc().init()
        body_para.setLineSpacing_(3)
        body_para.setLineBreakMode_(NSLineBreakByWordWrapping)
        body_para.setFirstLineHeadIndent_(28)  # Indent under icon
        body_para.setHeadIndent_(28)
        
        body_attrs = {
            NSFontAttributeName: Typography.body_regular(),
            NSForegroundColorAttributeName: Colors.TEXT_PRIMARY,
            NSParagraphStyleAttributeName: body_para,
        }
        
        body_str = NSAttributedString.alloc().initWithString_attributes_(
            text, body_attrs
        )
        storage.appendAttributedString_(body_str)

        # Scroll to bottom with smooth animation
        self.chat_view.scrollToEndOfDocument_(None)

    def _set_status(self, text, processing=False):
        """Set status in header."""
        self.header_status.setStringValue_(text)
        
        if processing:
            self.header_status.setTextColor_(Colors.ACCENT_WARNING)
            self.status_dot.layer().setBackgroundColor_(Colors.ACCENT_WARNING.CGColor())
        else:
            self.header_status.setTextColor_(Colors.TEXT_MUTED)
            self.status_dot.layer().setBackgroundColor_(Colors.ACCENT_SUCCESS.CGColor())

    def do_send(self):
        """Handle send button click or Enter key."""
        message = self.input_field.stringValue()
        if not message or not message.strip():
            return

        if self.is_processing:
            return

        # Clear input and add user message
        self.input_field.setStringValue_("")
        self._add_message("Du", message.strip(), is_ai=False)

        # Start processing
        self.is_processing = True
        self.send_button.setEnabled_(False)
        self.send_button.layer().setBackgroundColor_(Colors.BUTTON_DISABLED.CGColor())
        self._set_status("Tänker...", processing=True)

        # Process in background
        thread = threading.Thread(target=self._process_ai, args=(message,))
        thread.daemon = True
        thread.start()

    def _process_ai(self, message):
        """Process message with AI (background thread)."""
        try:
            self.response_queue.put(("status", "Analyserar din förfrågan..."))

            if not self.assistant:
                self.response_queue.put((
                    "error",
                    "AI-assistenten kunde inte initieras. Kontrollera din API-nyckel."
                ))
                return

            self.response_queue.put(("status", "Tänker..."))
            response = self.assistant.chat(message)
            self.response_queue.put(("response", response))

        except Exception as e:
            self.response_queue.put(("error", f"Ett fel uppstod: {str(e)}"))

    def clear_chat(self):
        """Clear chat history."""
        self.chat_view.textStorage().setAttributedString_(
            NSAttributedString.alloc().initWithString_("")
        )
        self.message_count = 0
        self._add_welcome_message()

    def show(self):
        """Show the window with elegant animation."""
        self.window.makeKeyAndOrderFront_(None)
        self.input_field.becomeFirstResponder()
        NSApp.activateIgnoringOtherApps_(True)
        
        # Subtle fade-in effect
        self.window.setAlphaValue_(0.0)
        self.window.setAlphaValue_(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE & ENTRY POINTS
# ═══════════════════════════════════════════════════════════════════════════════

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
    """Run as standalone application."""
    if not HAS_APPKIT:
        print("AppKit not available")
        return

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # Create menubar
    menubar = NSMenu.alloc().init()
    app.setMainMenu_(menubar)

    # App menu
    app_menu_item = NSMenuItem.alloc().init()
    menubar.addItem_(app_menu_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItemWithTitle_action_keyEquivalent_("About SortMeOut AI", "orderFrontStandardAboutPanel:", "")
    app_menu.addItem_(NSMenuItem.separatorItem())
    app_menu.addItemWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
    app_menu_item.setSubmenu_(app_menu)

    # Edit menu (for Cmd+C, Cmd+V, etc.)
    edit_menu_item = NSMenuItem.alloc().init()
    menubar.addItem_(edit_menu_item)
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Undo", "undo:", "z")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Redo", "redo:", "Z")
    edit_menu.addItem_(NSMenuItem.separatorItem())
    edit_menu.addItemWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
    edit_menu_item.setSubmenu_(edit_menu)

    # Create and show window
    window = ChatWindow()
    window.show()

    # Ensure app is active
    app.activateIgnoringOtherApps_(True)
    window.window.makeFirstResponder_(window.input_field)

    app.run()


if __name__ == "__main__":
    main()
