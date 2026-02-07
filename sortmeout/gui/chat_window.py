"""
SortMeOut AI Chat Window — Premium Edition v2
Polished native macOS chat interface with animated thinking,
AI personality, user identity, and website-matched design system.
"""

import os
import re
import sys
import subprocess
import threading
import queue
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
        NSMutableAttributedString,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
        NSParagraphStyleAttributeName,
        NSBackgroundColorAttributeName,
        NSAttributedString,
        NSViewWidthSizable,
        NSViewHeightSizable,
        NSViewMinYMargin,
        NSViewMinXMargin,
        NSViewMaxXMargin,
        NSViewMaxYMargin,
        NSApplicationActivationPolicyRegular,
        NSTimer,
        NSMenu,
        NSMenuItem,
        NSFontWeightRegular,
        NSFontWeightMedium,
        NSFontWeightSemibold,
        NSFontWeightBold,
        NSTextAlignmentCenter,
        NSLineBreakByWordWrapping,
        NSMutableParagraphStyle,
        NSWindowTitleHidden,
    )
    from Foundation import (
        NSObject,
        NSMakeRect,
        NSSize,
    )
    import objc

    HAS_APPKIT = True
except ImportError as e:
    print(f"AppKit import error: {e}")
    HAS_APPKIT = False

CONFIG_DIR = os.path.expanduser("~/.config/sortmeout")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — mirrors website/css/styles.css :root tokens
# Website: https://sortmeout.pages.dev
#
#   --color-primary:       #6366F1
#   --color-primary-dark:  #4F46E5
#   --color-primary-light: #818CF8
#   --color-secondary:     #8B5CF6
#   --color-gray-950:      #030712
#   --color-gray-900:      #111827
#   --color-gray-800:      #1F2937
#   --color-gray-700:      #374151
#   --color-gray-400:      #9CA3AF
#   --color-gray-500:      #6B7280
#   --color-success:       #10B981
#   --color-warning:       #F59E0B
#   --color-error:         #EF4444
# ═══════════════════════════════════════════════════════════════════════════════


def _c(r, g, b, a=1.0):
    """Shorthand color constructor."""
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


class Colors:
    """Website-matched color palette — LIGHT theme mirroring landing page.

    Mirrors the landing page design system exactly:
    - Backgrounds: white / gray-50 / gray-100
    - Text: gray-900 dark on light
    - Accents: primary (#6366F1) → secondary (#8B5CF6) gradient
    - Borders: gray-200 (#E5E7EB)
    """

    # Backgrounds — white / gray-50 / gray-100 (website hero + content palette)
    WINDOW_BG   = _c(1.0, 1.0, 1.0)          # #FFFFFF  white
    CHAT_BG     = _c(0.976, 0.980, 0.984)     # #F9FAFB  gray-50
    INPUT_BG    = _c(0.953, 0.957, 0.965)     # #F3F4F6  gray-100
    HEADER_BG   = _c(1.0, 1.0, 1.0)          # #FFFFFF  white (clean header)

    # Text — gray-900 / gray-500 / gray-400 (dark text on light bg)
    TEXT_PRIMARY   = _c(0.067, 0.094, 0.153)  # #111827  gray-900
    TEXT_SECONDARY = _c(0.420, 0.447, 0.502)  # #6B7280  gray-500
    TEXT_MUTED     = _c(0.612, 0.639, 0.686)  # #9CA3AF  gray-400
    TEXT_ON_INDIGO = _c(1.0, 1.0, 1.0)
    TEXT_PLACEHOLDER = _c(0.612, 0.639, 0.686)  # gray-400

    # Accents — primary / primary-dark / primary-light / secondary
    ACCENT        = _c(0.389, 0.400, 0.945)  # #6366F1  primary
    ACCENT_DARK   = _c(0.310, 0.275, 0.898)  # #4F46E5  primary-dark
    ACCENT_LIGHT  = _c(0.506, 0.549, 0.973)  # #818CF8  primary-light
    ACCENT_VIOLET = _c(0.545, 0.361, 0.965)  # #8B5CF6  secondary
    ACCENT_PINK   = _c(0.925, 0.286, 0.600)  # #EC4899  accent (website)

    # Semantic
    SUCCESS = _c(0.063, 0.725, 0.506)  # #10B981
    WARNING = _c(0.961, 0.620, 0.043)  # #F59E0B
    ERROR   = _c(0.937, 0.267, 0.267)  # #EF4444

    # Buttons
    BTN_PRIMARY  = _c(0.389, 0.400, 0.945)   # primary
    BTN_HOVER    = _c(0.467, 0.475, 0.960)   # brighter primary
    BTN_DISABLED = _c(0.820, 0.835, 0.859)   # #D1D5DB  gray-300

    # Structure
    DIVIDER       = _c(0.898, 0.906, 0.922)  # #E5E7EB  gray-200
    BORDER_SUBTLE = _c(0.898, 0.906, 0.922)  # #E5E7EB  gray-200
    BORDER_FOCUS  = _c(0.389, 0.400, 0.945, 0.4)  # primary at 40%
    CODE_BG       = _c(0.953, 0.957, 0.965)  # #F3F4F6  gray-100

    # Markdown
    HEADING_COLOR = _c(0.067, 0.094, 0.153)  # #111827  gray-900
    BULLET_COLOR  = _c(0.389, 0.400, 0.945)  # #6366F1  primary
    HR_COLOR      = _c(0.820, 0.835, 0.859)  # #D1D5DB  gray-300

    # Thinking indicator
    DOT_DIM    = _c(0.820, 0.835, 0.859, 0.5)   # gray-300 dimmed
    DOT_BRIGHT = _c(0.389, 0.400, 0.945, 1.0)   # primary


class Fonts:
    """Typography scale."""

    @staticmethod
    def h1():
        return NSFont.systemFontOfSize_weight_(20, NSFontWeightBold)

    @staticmethod
    def h2():
        return NSFont.systemFontOfSize_weight_(17, NSFontWeightSemibold)

    @staticmethod
    def h3():
        return NSFont.systemFontOfSize_weight_(15, NSFontWeightSemibold)

    @staticmethod
    def body():
        return NSFont.systemFontOfSize_weight_(13.5, NSFontWeightRegular)

    @staticmethod
    def body_medium():
        return NSFont.systemFontOfSize_weight_(13.5, NSFontWeightMedium)

    @staticmethod
    def bold():
        return NSFont.systemFontOfSize_weight_(13.5, NSFontWeightSemibold)

    @staticmethod
    def caption():
        return NSFont.systemFontOfSize_weight_(11, NSFontWeightMedium)

    @staticmethod
    def caption_regular():
        return NSFont.systemFontOfSize_(11)

    @staticmethod
    def code():
        return NSFont.monospacedSystemFontOfSize_weight_(12.5, NSFontWeightMedium)

    @staticmethod
    def title():
        return NSFont.systemFontOfSize_weight_(16, NSFontWeightSemibold)

    @staticmethod
    def sender():
        return NSFont.systemFontOfSize_weight_(12, NSFontWeightSemibold)

    @staticmethod
    def timestamp():
        return NSFont.monospacedDigitSystemFontOfSize_weight_(10.5, NSFontWeightRegular)


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN RENDERER
# ═══════════════════════════════════════════════════════════════════════════════


class MarkdownRenderer:
    """Convert markdown text to richly styled NSAttributedString."""

    def __init__(self, base_indent=0.0, text_color=None):
        self.base_indent = base_indent
        self.text_color = text_color or Colors.TEXT_PRIMARY

    def render(self, text):
        result = NSMutableAttributedString.alloc().init()
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            if not line.strip():
                self._spacing(result, 6)
                i += 1
                continue

            if line.strip() in ("---", "***", "___"):
                self._hr(result)
                i += 1
                continue

            hm = re.match(r'^(#{1,3})\s+(.+)$', line)
            if hm:
                self._header(result, hm.group(2), len(hm.group(1)))
                i += 1
                continue

            bm = re.match(r'^(\s*)[-*]\s+(.+)$', line)
            if bm:
                self._bullet(result, bm.group(2), len(bm.group(1)) // 2)
                i += 1
                continue

            nm = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
            if nm:
                self._numbered(result, nm.group(3), nm.group(2), len(nm.group(1)) // 2)
                i += 1
                continue

            self._paragraph(result, line)
            i += 1

        return result

    def _spacing(self, result, pts):
        p = NSMutableParagraphStyle.alloc().init()
        p.setParagraphSpacingBefore_(pts)
        p.setLineBreakMode_(NSLineBreakByWordWrapping)
        a = {NSFontAttributeName: NSFont.systemFontOfSize_(4), NSParagraphStyleAttributeName: p}
        result.appendAttributedString_(NSAttributedString.alloc().initWithString_attributes_("\n", a))

    def _hr(self, result):
        p = NSMutableParagraphStyle.alloc().init()
        p.setParagraphSpacingBefore_(8)
        p.setParagraphSpacing_(8)
        p.setFirstLineHeadIndent_(self.base_indent)
        p.setHeadIndent_(self.base_indent)
        p.setLineBreakMode_(NSLineBreakByWordWrapping)
        a = {
            NSFontAttributeName: NSFont.systemFontOfSize_(6),
            NSForegroundColorAttributeName: Colors.HR_COLOR,
            NSParagraphStyleAttributeName: p,
        }
        result.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_("\u2500" * 40 + "\n", a)
        )

    def _header(self, result, text, level):
        fmap = {1: Fonts.h1(), 2: Fonts.h2(), 3: Fonts.h3()}
        smap = {1: 14, 2: 10, 3: 8}
        p = NSMutableParagraphStyle.alloc().init()
        p.setParagraphSpacingBefore_(smap.get(level, 8))
        p.setParagraphSpacing_(4)
        p.setFirstLineHeadIndent_(self.base_indent)
        p.setHeadIndent_(self.base_indent)
        p.setLineBreakMode_(NSLineBreakByWordWrapping)
        a = {
            NSFontAttributeName: fmap.get(level, Fonts.h3()),
            NSForegroundColorAttributeName: Colors.HEADING_COLOR,
            NSParagraphStyleAttributeName: p,
        }
        hs = self._inline(text, a)
        hs.appendAttributedString_(NSAttributedString.alloc().initWithString_attributes_("\n", a))
        result.appendAttributedString_(hs)

    def _bullet(self, result, text, indent_level=0):
        extra = indent_level * 16
        bi = self.base_indent + 8 + extra
        ti = self.base_indent + 22 + extra
        p = NSMutableParagraphStyle.alloc().init()
        p.setParagraphSpacingBefore_(3)
        p.setParagraphSpacing_(2)
        p.setFirstLineHeadIndent_(bi)
        p.setHeadIndent_(ti)
        p.setLineBreakMode_(NSLineBreakByWordWrapping)

        da = {
            NSFontAttributeName: NSFont.systemFontOfSize_(8),
            NSForegroundColorAttributeName: Colors.BULLET_COLOR,
            NSParagraphStyleAttributeName: p,
        }
        result.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_("\u25CF  ", da)
        )

        ta = {
            NSFontAttributeName: Fonts.body(),
            NSForegroundColorAttributeName: self.text_color,
            NSParagraphStyleAttributeName: p,
        }
        result.appendAttributedString_(self._inline(text, ta))
        result.appendAttributedString_(NSAttributedString.alloc().initWithString_attributes_("\n", ta))

    def _numbered(self, result, text, number, indent_level=0):
        extra = indent_level * 16
        ni = self.base_indent + 8 + extra
        ti = self.base_indent + 26 + extra
        p = NSMutableParagraphStyle.alloc().init()
        p.setParagraphSpacingBefore_(3)
        p.setParagraphSpacing_(2)
        p.setFirstLineHeadIndent_(ni)
        p.setHeadIndent_(ti)
        p.setLineBreakMode_(NSLineBreakByWordWrapping)

        na = {
            NSFontAttributeName: Fonts.body_medium(),
            NSForegroundColorAttributeName: Colors.ACCENT,
            NSParagraphStyleAttributeName: p,
        }
        result.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(f"{number}.  ", na)
        )

        ta = {
            NSFontAttributeName: Fonts.body(),
            NSForegroundColorAttributeName: self.text_color,
            NSParagraphStyleAttributeName: p,
        }
        result.appendAttributedString_(self._inline(text, ta))
        result.appendAttributedString_(NSAttributedString.alloc().initWithString_attributes_("\n", ta))

    def _paragraph(self, result, text):
        p = NSMutableParagraphStyle.alloc().init()
        p.setLineSpacing_(3)
        p.setParagraphSpacingBefore_(2)
        p.setParagraphSpacing_(2)
        p.setFirstLineHeadIndent_(self.base_indent)
        p.setHeadIndent_(self.base_indent)
        p.setLineBreakMode_(NSLineBreakByWordWrapping)
        a = {
            NSFontAttributeName: Fonts.body(),
            NSForegroundColorAttributeName: self.text_color,
            NSParagraphStyleAttributeName: p,
        }
        s = self._inline(text, a)
        s.appendAttributedString_(NSAttributedString.alloc().initWithString_attributes_("\n", a))
        result.appendAttributedString_(s)

    def _inline(self, text, base_attrs):
        """Parse **bold**, *italic*, `code`, and plain text."""
        result = NSMutableAttributedString.alloc().init()
        pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|([^*`]+))'
        for m in re.finditer(pattern, text):
            bold_t = m.group(2)
            italic_t = m.group(3)
            code_t = m.group(4)
            plain_t = m.group(5)
            if bold_t is not None:
                a = dict(base_attrs)
                a[NSFontAttributeName] = Fonts.bold()
                a[NSForegroundColorAttributeName] = Colors.TEXT_PRIMARY
                result.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_attributes_(bold_t, a)
                )
            elif italic_t is not None:
                a = dict(base_attrs)
                a[NSForegroundColorAttributeName] = Colors.TEXT_SECONDARY
                result.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_attributes_(italic_t, a)
                )
            elif code_t is not None:
                a = dict(base_attrs)
                a[NSFontAttributeName] = Fonts.code()
                a[NSForegroundColorAttributeName] = Colors.ACCENT_DARK
                a[NSBackgroundColorAttributeName] = Colors.CODE_BG
                result.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_attributes_(f" {code_t} ", a)
                )
            elif plain_t is not None:
                result.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_attributes_(plain_t, base_attrs)
                )
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _get_user_name():
    """Get the user's first name from config, macOS, or fallback."""
    # 1. Check SortMeOut config
    config_path = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, "r") as f:
                cfg = json.load(f)
            name = cfg.get("user_name", "").strip()
            if name:
                return name.split()[0]
        except Exception:
            pass
    # 2. macOS full name
    try:
        r = subprocess.run(["id", "-F"], capture_output=True, text=True, timeout=2)
        name = r.stdout.strip()
        if name:
            return name.split()[0]
    except Exception:
        pass
    return os.environ.get("USER", "You").capitalize()


def _get_ai_name():
    """Get the AI assistant's custom name from config, or default."""
    config_path = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, "r") as f:
                cfg = json.load(f)
            name = cfg.get("assistant_name", "").strip()
            if name:
                return name
        except Exception:
            pass
    return "SortMeOut AI"


def _save_ai_name(name):
    """Save the AI assistant's custom name to config."""
    config_path = os.path.join(CONFIG_DIR, "config.json")
    try:
        import json
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
        cfg["assistant_name"] = name.strip()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception:
        return False


def load_api_key():
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return os.environ.get("ANTHROPIC_API_KEY")


def format_time(dt=None):
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%H:%M")


# ═══════════════════════════════════════════════════════════════════════════════
# DELEGATE
# ═══════════════════════════════════════════════════════════════════════════════


class ChatWindowDelegate(NSObject):

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
        if self.chat_window:
            self.chat_window.do_send()

    def checkQueue_(self, timer):
        if self.chat_window:
            self.chat_window.check_queue()

    def clearChat_(self, sender):
        if self.chat_window:
            self.chat_window.clear_chat()


# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM CHAT WINDOW v2
# ═══════════════════════════════════════════════════════════════════════════════


class ChatWindow:
    """Premium AI chat window with animated thinking, AI personality, and
    user identity — design-matched to the SortMeOut website."""

    # AI avatar
    AI_EMOJI = "\U0001F916"  # 🤖

    def __init__(self):
        self.window = None
        self.chat_view = None
        self.input_field = None
        self.send_button = None
        self.header_status = None
        self.status_dot = None
        self.assistant = None
        self.is_processing = False
        self.response_queue = queue.Queue()
        self.timer = None
        self.message_count = 0
        self.animation_state = 0

        # Thinking indicator tracking
        self.thinking_range_start = None

        # User identity
        self.user_name = _get_user_name()
        self.user_initial = self.user_name[0].upper() if self.user_name else "U"

        # AI identity (user-customizable)
        self.ai_name = _get_ai_name()

        self.delegate = ChatWindowDelegate.alloc().init()
        self.delegate.set_chat_window(self)

        api_key = load_api_key()
        if api_key:
            try:
                from sortmeout.ai.assistant import FileAssistant
                self.assistant = FileAssistant(api_key=api_key)
            except Exception as e:
                print(f"Assistant init error: {e}")

        self._create_window()
        self._start_timer()

    # ──────────────────────────────────────────────────────────────────

    def _create_window(self):
        W, H = 520, 740
        frame = NSMakeRect(200, 100, W, H)
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
        self.window.setTitle_(self.ai_name)
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(NSWindowTitleHidden)
        self.window.setMinSize_(NSSize(440, 520))
        self.window.setReleasedWhenClosed_(False)
        self.window.setBackgroundColor_(Colors.WINDOW_BG)
        self.window.setMovableByWindowBackground_(True)
        self.window.setOpaque_(False)

        content = self.window.contentView()
        content.setWantsLayer_(True)
        content.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())

        self._build_header(content, W, H)
        self._build_chat_area(content, W, H)
        self._build_input_bar(content, W)
        self._add_welcome_message()

    # ──────────────────────────────────────────────────────────────────
    # HEADER — centered to avoid macOS traffic-light collision
    # ──────────────────────────────────────────────────────────────────

    def _build_header(self, content, W, H):
        HH = 64
        header = NSView.alloc().initWithFrame_(NSMakeRect(0, H - HH, W, HH))
        header.setWantsLayer_(True)
        header.layer().setBackgroundColor_(Colors.HEADER_BG.CGColor())
        header.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)

        # Gradient accent line at bottom (mirrors website gradient-primary: indigo → violet)
        accent = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, 2))
        accent.setWantsLayer_(True)
        gradient_layer = objc.lookUpClass('CAGradientLayer').layer()
        gradient_layer.setFrame_(accent.bounds())
        gradient_layer.setStartPoint_((0, 0.5))
        gradient_layer.setEndPoint_((1, 0.5))
        gradient_layer.setColors_([
            Colors.ACCENT.CGColor(),        # #6366F1 indigo
            Colors.ACCENT_VIOLET.CGColor(), # #8B5CF6 violet
        ])
        accent.layer().addSublayer_(gradient_layer)
        accent.setAutoresizingMask_(NSViewWidthSizable)
        header.addSubview_(accent)

        # ─── Centered content container ───
        # Keeps icon + title group clear of macOS traffic-light buttons
        grp_w = 220
        grp_x = (W - grp_w) / 2
        container = NSView.alloc().initWithFrame_(NSMakeRect(grp_x, 0, grp_w, HH))
        container.setAutoresizingMask_(NSViewMinXMargin | NSViewMaxXMargin)

        # AI avatar circle with sparkle
        icon_size = 34
        icon_y = (HH - icon_size) / 2
        icon_bg = NSView.alloc().initWithFrame_(NSMakeRect(0, icon_y, icon_size, icon_size))
        icon_bg.setWantsLayer_(True)
        icon_bg.layer().setCornerRadius_(icon_size / 2)
        icon_bg.layer().setBackgroundColor_(Colors.ACCENT.CGColor())
        container.addSubview_(icon_bg)

        icon_lbl = NSTextField.alloc().initWithFrame_(NSMakeRect(0, icon_y, icon_size, icon_size))
        icon_lbl.setStringValue_("\u2726")  # ✦
        icon_lbl.setBezeled_(False)
        icon_lbl.setDrawsBackground_(False)
        icon_lbl.setEditable_(False)
        icon_lbl.setSelectable_(False)
        icon_lbl.setAlignment_(NSTextAlignmentCenter)
        icon_lbl.setTextColor_(Colors.TEXT_ON_INDIGO)
        icon_lbl.setFont_(NSFont.systemFontOfSize_weight_(16, NSFontWeightMedium))
        container.addSubview_(icon_lbl)

        # Title
        tx = icon_size + 10
        title = NSTextField.alloc().initWithFrame_(NSMakeRect(tx, 34, grp_w - tx, 20))
        self.header_title = title
        title.setStringValue_(self.ai_name)
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setSelectable_(False)
        title.setTextColor_(Colors.TEXT_PRIMARY)
        title.setFont_(Fonts.title())
        container.addSubview_(title)

        # Status subtitle
        self.header_status = NSTextField.alloc().initWithFrame_(NSMakeRect(tx, 16, grp_w - tx, 16))
        self.header_status.setStringValue_("Ready to help")
        self.header_status.setBezeled_(False)
        self.header_status.setDrawsBackground_(False)
        self.header_status.setEditable_(False)
        self.header_status.setSelectable_(False)
        self.header_status.setTextColor_(Colors.TEXT_MUTED)
        self.header_status.setFont_(Fonts.caption_regular())
        container.addSubview_(self.header_status)

        header.addSubview_(container)

        # Status dot (stays at right edge)
        self.status_dot = NSView.alloc().initWithFrame_(NSMakeRect(W - 28, 28, 8, 8))
        self.status_dot.setWantsLayer_(True)
        self.status_dot.layer().setCornerRadius_(4)
        self.status_dot.layer().setBackgroundColor_(Colors.SUCCESS.CGColor())
        self.status_dot.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        header.addSubview_(self.status_dot)

        content.addSubview_(header)

    # ──────────────────────────────────────────────────────────────────
    # CHAT AREA
    # ──────────────────────────────────────────────────────────────────

    def _build_chat_area(self, content, W, H):
        HH = 66
        IH = 68
        ch = H - HH - IH

        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, IH, W, ch))
        scroll.setHasVerticalScroller_(True)
        scroll.setHasHorizontalScroller_(False)
        scroll.setBorderType_(0)
        scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll.setDrawsBackground_(True)
        scroll.setBackgroundColor_(Colors.CHAT_BG)
        scroll.setScrollerStyle_(1)
        scroll.verticalScroller().setKnobStyle_(1)  # dark knob for light bg

        tw = W - 40
        self.chat_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, tw, ch))
        self.chat_view.setEditable_(False)
        self.chat_view.setSelectable_(True)
        self.chat_view.setRichText_(True)
        self.chat_view.setFont_(Fonts.body())
        self.chat_view.setBackgroundColor_(Colors.CHAT_BG)
        self.chat_view.setTextColor_(Colors.TEXT_PRIMARY)
        self.chat_view.setTextContainerInset_(NSSize(16, 16))
        self.chat_view.setAllowsUndo_(True)
        self.chat_view.setUsesFontPanel_(False)
        self.chat_view.setVerticallyResizable_(True)
        self.chat_view.setHorizontallyResizable_(False)
        self.chat_view.textContainer().setWidthTracksTextView_(True)
        self.chat_view.textContainer().setContainerSize_(NSSize(tw, 1e7))

        scroll.setDocumentView_(self.chat_view)
        content.addSubview_(scroll)

    # ──────────────────────────────────────────────────────────────────
    # INPUT BAR
    # ──────────────────────────────────────────────────────────────────

    def _build_input_bar(self, content, W):
        IH = 68
        bar = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, IH))
        bar.setWantsLayer_(True)
        bar.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())
        bar.setAutoresizingMask_(NSViewWidthSizable | NSViewMaxYMargin)

        top = NSView.alloc().initWithFrame_(NSMakeRect(0, IH - 1, W, 1))
        top.setWantsLayer_(True)
        top.layer().setBackgroundColor_(Colors.DIVIDER.CGColor())
        top.setAutoresizingMask_(NSViewWidthSizable)
        bar.addSubview_(top)

        self.input_pill = NSView.alloc().initWithFrame_(NSMakeRect(14, 14, W - 28, 40))
        self.input_pill.setWantsLayer_(True)
        self.input_pill.layer().setCornerRadius_(20)
        self.input_pill.layer().setBackgroundColor_(Colors.INPUT_BG.CGColor())
        self.input_pill.layer().setBorderWidth_(1.5)
        self.input_pill.layer().setBorderColor_(Colors.BORDER_SUBTLE.CGColor())
        self.input_pill.setAutoresizingMask_(NSViewWidthSizable)
        bar.addSubview_(self.input_pill)

        self.input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(16, 6, W - 100, 28))
        self.input_field.setPlaceholderString_("Organize files, create rules, ask anything\u2026")
        self.input_field.setBezeled_(False)
        self.input_field.setDrawsBackground_(False)
        self.input_field.setTextColor_(Colors.TEXT_PRIMARY)
        self.input_field.setFont_(Fonts.body())
        self.input_field.setFocusRingType_(1)  # suppress default focus ring
        self.input_field.setEditable_(True)
        self.input_field.setSelectable_(True)
        self.input_field.setAutoresizingMask_(NSViewWidthSizable)
        self.input_pill.addSubview_(self.input_field)

        bs = 30
        bx = W - 28 - bs - 6
        self.send_button = NSButton.alloc().initWithFrame_(NSMakeRect(bx, 5, bs, bs))
        self.send_button.setTitle_("\u2191")  # ↑
        self.send_button.setBordered_(False)
        self.send_button.setWantsLayer_(True)
        self.send_button.layer().setCornerRadius_(bs / 2)
        self.send_button.layer().setBackgroundColor_(Colors.BTN_PRIMARY.CGColor())
        # Send button glow shadow (website btn-primary box-shadow glow)
        self.send_button.layer().setShadowColor_(Colors.ACCENT.CGColor())
        self.send_button.layer().setShadowOpacity_(0.4)
        self.send_button.layer().setShadowRadius_(6)
        self.send_button.layer().setShadowOffset_((0, 0))
        self.send_button.setFont_(NSFont.systemFontOfSize_weight_(16, NSFontWeightBold))
        self.send_button.setContentTintColor_(Colors.TEXT_ON_INDIGO)
        self.send_button.setTarget_(self.delegate)
        self.send_button.setAction_("sendClicked:")
        self.send_button.setAutoresizingMask_(NSViewMinXMargin)
        self.input_pill.addSubview_(self.send_button)

        content.addSubview_(bar)

        self.input_field.setTarget_(self.delegate)
        self.input_field.setAction_("sendClicked:")

    # ──────────────────────────────────────────────────────────────────
    # THINKING INDICATOR — animated dots in the chat area
    # ──────────────────────────────────────────────────────────────────

    def _show_thinking(self):
        """Insert an animated thinking block below the user's message."""
        storage = self.chat_view.textStorage()
        self.thinking_range_start = storage.length()
        self._render_thinking_frame()

    def _render_thinking_frame(self):
        """Build (or rebuild) the thinking indicator with animated dots."""
        if self.thinking_range_start is None:
            return

        storage = self.chat_view.textStorage()
        storage.beginEditing()

        # Remove previous frame
        current_end = storage.length()
        if current_end > self.thinking_range_start:
            storage.deleteCharactersInRange_((self.thinking_range_start, current_end - self.thinking_range_start))

        block = NSMutableAttributedString.alloc().init()
        phase = self.animation_state % 30

        # ── Spacing ──
        sp = NSMutableParagraphStyle.alloc().init()
        sp.setParagraphSpacingBefore_(14)
        block.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                "\n", {NSFontAttributeName: NSFont.systemFontOfSize_(2), NSParagraphStyleAttributeName: sp}
            )
        )

        # ── AI sender line with face ──
        lp = NSMutableParagraphStyle.alloc().init()
        lp.setLineBreakMode_(NSLineBreakByWordWrapping)
        lp.setParagraphSpacing_(6)

        # AI emoji avatar
        block.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                f"{self.AI_EMOJI}  ",
                {
                    NSFontAttributeName: NSFont.systemFontOfSize_(14),
                    NSForegroundColorAttributeName: Colors.ACCENT,
                    NSParagraphStyleAttributeName: lp,
                },
            )
        )
        # Name
        block.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                self.ai_name,
                {
                    NSFontAttributeName: Fonts.sender(),
                    NSForegroundColorAttributeName: Colors.ACCENT,
                    NSParagraphStyleAttributeName: lp,
                },
            )
        )
        block.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                "\n",
                {NSFontAttributeName: Fonts.sender(), NSParagraphStyleAttributeName: lp},
            )
        )

        # ── Animated dots ──
        dp = NSMutableParagraphStyle.alloc().init()
        dp.setLineBreakMode_(NSLineBreakByWordWrapping)
        dp.setFirstLineHeadIndent_(10)
        dp.setHeadIndent_(10)
        dp.setParagraphSpacing_(4)

        for i in range(3):
            # Wave animation: each dot peaks at a different phase
            dot_phase = (phase - i * 8) % 30
            if 0 <= dot_phase < 12:
                t = dot_phase / 12.0
                brightness = 0.3 + 0.7 * (1.0 - abs(t * 2.0 - 1.0))
            else:
                brightness = 0.2

            # Light theme: dots go from gray-300 (dim) to primary indigo (bright)
            r = 0.82 - 0.43 * brightness   # 0.82 → 0.39
            g = 0.84 - 0.44 * brightness   # 0.84 → 0.40
            b = 0.86 + 0.085 * brightness  # 0.86 → 0.945
            a = 0.45 + 0.55 * brightness

            dot_color = _c(r, g, b, a)
            block.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(
                    "\u25CF",
                    {
                        NSFontAttributeName: NSFont.systemFontOfSize_(16),
                        NSForegroundColorAttributeName: dot_color,
                        NSParagraphStyleAttributeName: dp,
                    },
                )
            )
            if i < 2:
                block.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_attributes_(
                        "  ",
                        {
                            NSFontAttributeName: NSFont.systemFontOfSize_(10),
                            NSParagraphStyleAttributeName: dp,
                        },
                    )
                )

        # Status text after dots
        status_texts = ["Analyzing", "Thinking", "Processing", "Reasoning"]
        idx = (phase // 8) % len(status_texts)
        block.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                f"   {status_texts[idx]}\u2026\n",
                {
                    NSFontAttributeName: Fonts.caption_regular(),
                    NSForegroundColorAttributeName: Colors.TEXT_MUTED,
                    NSParagraphStyleAttributeName: dp,
                },
            )
        )

        storage.appendAttributedString_(block)
        storage.endEditing()
        self.chat_view.scrollToEndOfDocument_(None)

    def _hide_thinking(self):
        """Remove the thinking indicator from the chat area."""
        if self.thinking_range_start is not None:
            storage = self.chat_view.textStorage()
            end = storage.length()
            length = end - self.thinking_range_start
            if length > 0:
                storage.beginEditing()
                storage.deleteCharactersInRange_((self.thinking_range_start, length))
                storage.endEditing()
            self.thinking_range_start = None

    # ──────────────────────────────────────────────────────────────────
    # WELCOME
    # ──────────────────────────────────────────────────────────────────

    def _add_welcome_message(self):
        greeting = f"Hey {self.user_name}! " if self.user_name != "You" else "Hey! "
        name_hint = ""
        if self.ai_name == "SortMeOut AI":
            name_hint = "\n\n*Tip: You can give me a name \u2014 just say \"Call yourself Jarvis\" or whatever you'd like!*"
        welcome = (
            f"{greeting}I'm **{self.ai_name}**, your AI file assistant.  {self.AI_EMOJI}\n\n"
            "Here's what I can help with:\n\n"
            "- **Organize files** \u2014 sort Downloads, Desktop, and more\n"
            "- **Create rules** \u2014 persistent automation from chat\n"
            "- **Analyze documents** \u2014 suggest the best location\n"
            "- **System control** \u2014 dark mode, volume, screenshots\n"
            "- **Clean up duplicates** \u2014 find and resolve clutter\n"
            "- **Sort by type, date, or content** \u2014 powerful filtering\n\n"
            f"Just tell me what you'd like to do.{name_hint}"
        )
        self._add_message(self.ai_name, welcome, is_ai=True, show_timestamp=False)

    # ──────────────────────────────────────────────────────────────────
    # TIMER
    # ──────────────────────────────────────────────────────────────────

    def _start_timer(self):
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.1, self.delegate, "checkQueue:", None, True
        )

    def check_queue(self):
        try:
            while True:
                mt, data = self.response_queue.get_nowait()
                if mt == "response":
                    self._hide_thinking()
                    self._add_message(self.ai_name, data, is_ai=True)
                    self._set_status("Ready to help", False)
                    self.is_processing = False
                    self.send_button.setEnabled_(True)
                    self.send_button.layer().setBackgroundColor_(Colors.BTN_PRIMARY.CGColor())
                elif mt == "status":
                    self._set_status(data, True)
                elif mt == "error":
                    self._hide_thinking()
                    self._add_message(
                        self.ai_name, f"Something went wrong: {data}", is_ai=True, is_error=True
                    )
                    self._set_status("Error occurred", False)
                    self.is_processing = False
                    self.send_button.setEnabled_(True)
                    self.send_button.layer().setBackgroundColor_(Colors.BTN_PRIMARY.CGColor())
        except queue.Empty:
            pass

        # Animate thinking dots + status dot
        if self.is_processing:
            self.animation_state = (self.animation_state + 1) % 300

            # Pulse the status dot (indigo ↔ violet)
            t = abs(((self.animation_state % 20) - 10) / 10.0)
            r = 0.389 + (0.545 - 0.389) * t
            g = 0.400 + (0.361 - 0.400) * t
            b = 0.945 + (0.965 - 0.945) * t
            self.status_dot.layer().setBackgroundColor_(_c(r, g, b, 0.5 + 0.5 * t).CGColor())

            # Rebuild thinking indicator frame with updated animation
            self._render_thinking_frame()

    # ──────────────────────────────────────────────────────────────────
    # MESSAGE RENDERING — with avatars and identity
    # ──────────────────────────────────────────────────────────────────

    def _add_message(self, sender, text, is_ai=False, show_timestamp=True, is_error=False):
        storage = self.chat_view.textStorage()
        self.message_count += 1

        # Spacing between messages
        if storage.length() > 0:
            sp = NSMutableParagraphStyle.alloc().init()
            sp.setParagraphSpacingBefore_(14)
            sa = {NSFontAttributeName: NSFont.systemFontOfSize_(2), NSParagraphStyleAttributeName: sp}
            storage.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_("\n", sa)
            )

        # ── Sender line with avatar ──
        lp = NSMutableParagraphStyle.alloc().init()
        lp.setLineBreakMode_(NSLineBreakByWordWrapping)
        lp.setParagraphSpacing_(4)

        if is_ai:
            avatar_char = self.AI_EMOJI  # 🤖
            avatar_color = Colors.ACCENT if not is_error else Colors.ERROR
            avatar_font = NSFont.systemFontOfSize_(14)
            display_name = sender
        else:
            avatar_char = self.user_initial
            avatar_color = Colors.ACCENT_VIOLET
            avatar_font = NSFont.systemFontOfSize_weight_(12, NSFontWeightBold)
            display_name = self.user_name

        # Avatar
        storage.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                f"{avatar_char}  ",
                {
                    NSFontAttributeName: avatar_font,
                    NSForegroundColorAttributeName: avatar_color,
                    NSParagraphStyleAttributeName: lp,
                },
            )
        )

        # Name
        storage.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                display_name,
                {
                    NSFontAttributeName: Fonts.sender(),
                    NSForegroundColorAttributeName: avatar_color,
                    NSParagraphStyleAttributeName: lp,
                },
            )
        )

        # Timestamp
        if show_timestamp:
            storage.appendAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(
                    f"  \u00B7  {format_time()}",
                    {
                        NSFontAttributeName: Fonts.timestamp(),
                        NSForegroundColorAttributeName: Colors.TEXT_MUTED,
                        NSParagraphStyleAttributeName: lp,
                    },
                )
            )

        storage.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                "\n",
                {NSFontAttributeName: Fonts.sender(), NSParagraphStyleAttributeName: lp},
            )
        )

        # ── Body — render markdown ──
        tc = Colors.TEXT_PRIMARY
        if is_error:
            tc = Colors.TEXT_SECONDARY

        renderer = MarkdownRenderer(base_indent=4, text_color=tc)

        # Strip EXECUTE command artifacts
        clean = re.sub(
            r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"[^"]*"(?:\s+"[^"]*")?\]', "", text
        )
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()

        storage.appendAttributedString_(renderer.render(clean))
        self.chat_view.scrollToEndOfDocument_(None)

    # ──────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────

    def _set_status(self, text, processing):
        if processing:
            self.header_status.setStringValue_(f"{text}")
            self.header_status.setTextColor_(Colors.ACCENT)
            self.status_dot.layer().setBackgroundColor_(Colors.WARNING.CGColor())
        else:
            self.header_status.setStringValue_(text)
            self.header_status.setTextColor_(Colors.TEXT_MUTED)
            self.status_dot.layer().setBackgroundColor_(Colors.SUCCESS.CGColor())

    # ──────────────────────────────────────────────────────────────────
    # SEND / PROCESS
    # ──────────────────────────────────────────────────────────────────

    def do_send(self):
        msg = self.input_field.stringValue()
        if not msg or not msg.strip():
            return
        if self.is_processing:
            return

        self.input_field.setStringValue_("")
        self._add_message(self.user_name, msg.strip(), is_ai=False)

        # Show animated thinking indicator
        self.is_processing = True
        self.animation_state = 0
        self._show_thinking()

        self.send_button.setEnabled_(False)
        self.send_button.layer().setBackgroundColor_(Colors.BTN_DISABLED.CGColor())
        self._set_status("Thinking\u2026", True)

        t = threading.Thread(target=self._process_ai, args=(msg,))
        t.daemon = True
        t.start()

    def _process_ai(self, message):
        try:
            self.response_queue.put(("status", "Analyzing\u2026"))
            if not self.assistant:
                self.response_queue.put(
                    ("error", "AI not initialized. Check your API key in ~/.config/sortmeout/.env")
                )
                return
            self.response_queue.put(("status", "Thinking\u2026"))
            response = self.assistant.chat(message)
            self.response_queue.put(("response", response))
        except Exception as e:
            self.response_queue.put(("error", str(e)))

    def clear_chat(self):
        self.chat_view.textStorage().setAttributedString_(
            NSAttributedString.alloc().initWithString_("")
        )
        self.message_count = 0
        self._add_welcome_message()

    def show(self):
        self.window.makeKeyAndOrderFront_(None)
        self.input_field.becomeFirstResponder()
        NSApp.activateIgnoringOtherApps_(True)
        self.window.setAlphaValue_(0.0)
        self.window.setAlphaValue_(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE & ENTRY POINTS
# ═══════════════════════════════════════════════════════════════════════════════

_chat_window = None


def show_chat_window():
    global _chat_window
    if not HAS_APPKIT:
        print("AppKit not available")
        return False
    if _chat_window is None:
        _chat_window = ChatWindow()
    _chat_window.show()
    return True


def main():
    if not HAS_APPKIT:
        print("AppKit not available")
        return

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    menubar = NSMenu.alloc().init()
    app.setMainMenu_(menubar)

    ami = NSMenuItem.alloc().init()
    menubar.addItem_(ami)
    am = NSMenu.alloc().init()
    am.addItemWithTitle_action_keyEquivalent_("About SortMeOut AI", "orderFrontStandardAboutPanel:", "")
    am.addItem_(NSMenuItem.separatorItem())
    am.addItemWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
    ami.setSubmenu_(am)

    emi = NSMenuItem.alloc().init()
    menubar.addItem_(emi)
    em = NSMenu.alloc().initWithTitle_("Edit")
    em.addItemWithTitle_action_keyEquivalent_("Undo", "undo:", "z")
    em.addItemWithTitle_action_keyEquivalent_("Redo", "redo:", "Z")
    em.addItem_(NSMenuItem.separatorItem())
    em.addItemWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
    em.addItemWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
    em.addItemWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
    em.addItemWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
    emi.setSubmenu_(em)

    window = ChatWindow()
    window.show()
    app.activateIgnoringOtherApps_(True)
    window.window.makeFirstResponder_(window.input_field)
    app.run()


if __name__ == "__main__":
    main()
