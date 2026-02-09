"""
SortMeOut GUI Design System — shared theme for all native windows.

Mirrors the website design tokens (website/css/styles.css :root).
Single source of truth for colors, fonts, and spacing so every
window renders consistently.

Usage:
    from sortmeout.gui.theme import Colors, Fonts
"""

try:
    from AppKit import (
        NSColor,
        NSFont,
        NSFontWeightRegular,
        NSFontWeightMedium,
        NSFontWeightSemibold,
        NSFontWeightBold,
    )

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


def _c(r, g, b, a=1.0):
    """Shorthand color constructor for calibrated RGBA."""
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


class Colors:
    """Website-matched color palette — LIGHT theme mirroring landing page.

    Mirrors the landing page design system exactly:
    - Backgrounds: white / gray-50 / gray-100
    - Text: gray-900 dark on light
    - Accents: primary (#6366F1) → secondary (#8B5CF6) gradient
    - Borders: gray-200 (#E5E7EB)
    """

    # Backgrounds — white / gray-50 / gray-100
    WINDOW_BG = _c(1.0, 1.0, 1.0)  # #FFFFFF  white
    CONTENT_BG = _c(0.976, 0.980, 0.984)  # #F9FAFB  gray-50
    CHAT_BG = _c(0.976, 0.980, 0.984)  # #F9FAFB  gray-50 (alias)
    INPUT_BG = _c(0.953, 0.957, 0.965)  # #F3F4F6  gray-100
    HEADER_BG = _c(1.0, 1.0, 1.0)  # #FFFFFF  white
    CARD_BG = _c(1.0, 1.0, 1.0)  # #FFFFFF  white

    # Text — gray-900 / gray-500 / gray-400
    TEXT_PRIMARY = _c(0.067, 0.094, 0.153)  # #111827  gray-900
    TEXT_SECONDARY = _c(0.420, 0.447, 0.502)  # #6B7280  gray-500
    TEXT_MUTED = _c(0.612, 0.639, 0.686)  # #9CA3AF  gray-400
    TEXT_ON_PRIMARY = _c(1.0, 1.0, 1.0)  # white on accent
    TEXT_ON_INDIGO = _c(1.0, 1.0, 1.0)  # alias
    TEXT_PLACEHOLDER = _c(0.612, 0.639, 0.686)  # gray-400

    # Accents — primary / primary-dark / primary-light / secondary
    ACCENT = _c(0.389, 0.400, 0.945)  # #6366F1  primary
    ACCENT_DARK = _c(0.310, 0.275, 0.898)  # #4F46E5  primary-dark
    ACCENT_LIGHT = _c(0.506, 0.549, 0.973)  # #818CF8  primary-light
    ACCENT_VIOLET = _c(0.545, 0.361, 0.965)  # #8B5CF6  secondary
    ACCENT_PINK = _c(0.925, 0.286, 0.600)  # #EC4899  accent

    # Semantic
    SUCCESS = _c(0.063, 0.725, 0.506)  # #10B981
    WARNING = _c(0.961, 0.620, 0.043)  # #F59E0B
    ERROR = _c(0.937, 0.267, 0.267)  # #EF4444

    # Buttons
    BTN_PRIMARY = _c(0.389, 0.400, 0.945)  # primary
    BTN_HOVER = _c(0.467, 0.475, 0.960)  # brighter primary
    BTN_DISABLED = _c(0.820, 0.835, 0.859)  # #D1D5DB  gray-300

    # Structure
    DIVIDER = _c(0.898, 0.906, 0.922)  # #E5E7EB  gray-200
    BORDER = _c(0.898, 0.906, 0.922)  # #E5E7EB  gray-200
    BORDER_SUBTLE = _c(0.898, 0.906, 0.922)  # #E5E7EB  gray-200
    BORDER_FOCUS = _c(0.389, 0.400, 0.945, 0.4)  # primary at 40%
    CODE_BG = _c(0.953, 0.957, 0.965)  # #F3F4F6  gray-100

    # Markdown / code
    HEADING_COLOR = _c(0.067, 0.094, 0.153)  # #111827  gray-900
    BULLET_COLOR = _c(0.389, 0.400, 0.945)  # #6366F1  primary
    HR_COLOR = _c(0.820, 0.835, 0.859)  # #D1D5DB  gray-300

    # Thinking indicator
    DOT_DIM = _c(0.820, 0.835, 0.859, 0.5)  # gray-300 dimmed
    DOT_BRIGHT = _c(0.389, 0.400, 0.945, 1.0)  # primary

    # Gallery / image specific
    GALLERY_EMPTY = _c(0.953, 0.957, 0.965)  # gray-100


class Fonts:
    """Typography scale — macOS system fonts."""

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

    @staticmethod
    def small():
        return NSFont.systemFontOfSize_weight_(10, NSFontWeightRegular)
