"""
SortMeOut Image Studio — Native macOS Window
AI image generation (DALL·E 3), gallery, and editing tools.
Design-matched to the SortMeOut website + chat_window.py design system.
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

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
        NSTextField,
        NSTextView,
        NSScrollView,
        NSButton,
        NSFont,
        NSColor,
        NSView,
        NSImage,
        NSImageView,
        NSImageScaleProportionallyUpOrDown,
        NSPopUpButton,
        NSProgressIndicator,
        NSProgressIndicatorSpinningStyle,
        NSAttributedString,
        NSMutableAttributedString,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
        NSParagraphStyleAttributeName,
        NSViewWidthSizable,
        NSViewHeightSizable,
        NSViewMinYMargin,
        NSApplicationActivationPolicyRegular,
        NSTimer,
        NSMenu,
        NSMenuItem,
        NSFontWeightRegular,
        NSFontWeightMedium,
        NSFontWeightSemibold,
        NSFontWeightBold,
        NSTextAlignmentCenter,
        NSTextAlignmentLeft,
        NSLineBreakByWordWrapping,
        NSLineBreakByTruncatingTail,
        NSMutableParagraphStyle,
        NSWindowTitleHidden,
        NSBezelStyleRounded,
        NSOnState,
        NSOffState,
        NSBorderlessWindowMask,
        NSViewMaxYMargin,
    )
    from Foundation import (
        NSObject,
        NSMakeRect,
        NSSize,
        NSMakeSize,
        NSURL,
    )
    import objc

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

# ── Output directory ──
OUTPUT_DIR = os.path.expanduser("~/Pictures/SortMeOut")
CONFIG_DIR = os.path.expanduser("~/.config/sortmeout")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")


# ═══════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — imported from shared theme module
# ═══════════════════════════════════════════════════════════════════
from sortmeout.gui.theme import Colors, Fonts, _c


# ═══════════════════════════════════════════════════════════════════
# DELEGATE
# ═══════════════════════════════════════════════════════════════════


class ImageWindowDelegate(NSObject):
    def init(self):
        self = objc.super(ImageWindowDelegate, self).init()
        if self is None:
            return None
        self.image_window = None
        return self

    @objc.python_method
    def set_image_window(self, window):
        self.image_window = window

    def generateClicked_(self, sender):
        if self.image_window:
            self.image_window.do_generate()

    def editClicked_(self, sender):
        if self.image_window:
            self.image_window.do_edit()

    def refreshGallery_(self, sender):
        if self.image_window:
            self.image_window.load_gallery()

    def openFolder_(self, sender):
        if self.image_window:
            self.image_window.open_output_folder()

    def galleryItemClicked_(self, sender):
        if self.image_window:
            tag = sender.tag()
            self.image_window.open_gallery_item(tag)

    def _runCallback_(self, timer):
        if self.image_window and hasattr(self.image_window, "_pending_callback"):
            cb = self.image_window._pending_callback
            self.image_window._pending_callback = None
            if cb:
                try:
                    cb()
                except Exception as e:
                    print(f"Callback error: {e}")


# ═══════════════════════════════════════════════════════════════════
# IMAGE STUDIO WINDOW
# ═══════════════════════════════════════════════════════════════════


class ImageWindow:
    """Native macOS image studio: generate, browse, edit."""

    def __init__(self):
        self.window = None
        self.prompt_field = None
        self.size_popup = None
        self.quality_popup = None
        self.style_popup = None
        self.generate_btn = None
        self.status_label = None
        self.spinner = None
        self.gallery_scroll = None
        self.gallery_view = None
        self.is_generating = False
        self.gallery_images = []

        self.delegate = ImageWindowDelegate.alloc().init()
        self.delegate.set_image_window(self)

        self._create_window()
        self.load_gallery()

    def _create_window(self):
        W, H = 680, 760
        frame = NSMakeRect(250, 80, W, H)
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
        self.window.setTitle_("Image Studio")
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(NSWindowTitleHidden)
        self.window.setMinSize_(NSSize(520, 600))
        self.window.setReleasedWhenClosed_(False)
        self.window.setBackgroundColor_(Colors.WINDOW_BG)
        self.window.setMovableByWindowBackground_(True)

        content = self.window.contentView()
        content.setWantsLayer_(True)
        content.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())

        self._build_header(content, W, H)
        self._build_generate_section(content, W, H)
        self._build_gallery_section(content, W, H)

    # ──────────────────────────────────────────────────────────────
    # HEADER
    # ──────────────────────────────────────────────────────────────

    def _build_header(self, content, W, H):
        header_h = 60
        header = NSView.alloc().initWithFrame_(NSMakeRect(0, H - header_h, W, header_h))
        header.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        header.setWantsLayer_(True)
        header.layer().setBackgroundColor_(Colors.HEADER_BG.CGColor())

        # Title
        title = NSTextField.labelWithString_("🎨 Image Studio")
        title.setFont_(Fonts.h1())
        title.setTextColor_(Colors.TEXT_PRIMARY)
        title.setFrame_(NSMakeRect(20, 16, 200, 28))
        header.addSubview_(title)

        # Subtitle
        subtitle = NSTextField.labelWithString_("DALL·E 3 + Pillow")
        subtitle.setFont_(Fonts.caption())
        subtitle.setTextColor_(Colors.TEXT_MUTED)
        subtitle.setFrame_(NSMakeRect(20, 2, 200, 16))
        header.addSubview_(subtitle)

        # Open folder button
        folder_btn = NSButton.alloc().initWithFrame_(NSMakeRect(W - 140, 18, 120, 28))
        folder_btn.setTitle_("📁 Open Folder")
        folder_btn.setBezelStyle_(NSBezelStyleRounded)
        folder_btn.setFont_(Fonts.caption())
        folder_btn.setTarget_(self.delegate)
        folder_btn.setAction_(objc.selector(self.delegate.openFolder_, signature=b"v@:@"))
        folder_btn.setAutoresizingMask_(1 << 0)  # NSViewMinXMargin
        header.addSubview_(folder_btn)

        # Divider
        div = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, 1))
        div.setWantsLayer_(True)
        div.layer().setBackgroundColor_(Colors.DIVIDER.CGColor())
        div.setAutoresizingMask_(NSViewWidthSizable)
        header.addSubview_(div)

        content.addSubview_(header)

    # ──────────────────────────────────────────────────────────────
    # GENERATE SECTION
    # ──────────────────────────────────────────────────────────────

    def _build_generate_section(self, content, W, H):
        section_h = 230
        top = H - 60 - section_h
        section = NSView.alloc().initWithFrame_(NSMakeRect(0, top, W, section_h))
        section.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        section.setWantsLayer_(True)
        section.layer().setBackgroundColor_(Colors.CONTENT_BG.CGColor())

        pad = 20
        y = section_h - 10

        # Section label
        y -= 22
        label = NSTextField.labelWithString_("Generate Image")
        label.setFont_(Fonts.h3())
        label.setTextColor_(Colors.TEXT_PRIMARY)
        label.setFrame_(NSMakeRect(pad, y, 200, 20))
        section.addSubview_(label)

        # Prompt field
        y -= 64
        self.prompt_field = NSTextView.alloc().initWithFrame_(NSMakeRect(pad, y, W - pad * 2, 56))
        self.prompt_field.setFont_(Fonts.body())
        self.prompt_field.setTextColor_(Colors.TEXT_PRIMARY)
        self.prompt_field.setBackgroundColor_(Colors.INPUT_BG)
        self.prompt_field.setDrawsBackground_(True)
        self.prompt_field.setRichText_(False)
        self.prompt_field.setEditable_(True)
        self.prompt_field.setSelectable_(True)

        prompt_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(pad, y, W - pad * 2, 56))
        prompt_scroll.setDocumentView_(self.prompt_field)
        prompt_scroll.setHasVerticalScroller_(True)
        prompt_scroll.setBorderType_(1)  # NSLineBorder
        prompt_scroll.setAutoresizingMask_(NSViewWidthSizable)
        section.addSubview_(prompt_scroll)

        # Options row
        y -= 34
        opt_y = y

        # Size
        size_label = NSTextField.labelWithString_("Size:")
        size_label.setFont_(Fonts.caption())
        size_label.setTextColor_(Colors.TEXT_SECONDARY)
        size_label.setFrame_(NSMakeRect(pad, opt_y + 4, 30, 16))
        section.addSubview_(size_label)

        self.size_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(pad + 32, opt_y, 160, 24), False
        )
        self.size_popup.addItemsWithTitles_(
            [
                "1024×1024 (Square)",
                "1792×1024 (Landscape)",
                "1024×1792 (Portrait)",
            ]
        )
        self.size_popup.setFont_(Fonts.caption())
        section.addSubview_(self.size_popup)

        # Quality
        q_x = pad + 200
        q_label = NSTextField.labelWithString_("Quality:")
        q_label.setFont_(Fonts.caption())
        q_label.setTextColor_(Colors.TEXT_SECONDARY)
        q_label.setFrame_(NSMakeRect(q_x, opt_y + 4, 46, 16))
        section.addSubview_(q_label)

        self.quality_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(q_x + 48, opt_y, 90, 24), False
        )
        self.quality_popup.addItemsWithTitles_(["HD", "Standard"])
        self.quality_popup.setFont_(Fonts.caption())
        section.addSubview_(self.quality_popup)

        # Style
        s_x = q_x + 150
        s_label = NSTextField.labelWithString_("Style:")
        s_label.setFont_(Fonts.caption())
        s_label.setTextColor_(Colors.TEXT_SECONDARY)
        s_label.setFrame_(NSMakeRect(s_x, opt_y + 4, 34, 16))
        section.addSubview_(s_label)

        self.style_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(s_x + 36, opt_y, 90, 24), False
        )
        self.style_popup.addItemsWithTitles_(["Vivid", "Natural"])
        self.style_popup.setFont_(Fonts.caption())
        section.addSubview_(self.style_popup)

        # Button row
        y -= 40

        # Generate button
        self.generate_btn = NSButton.alloc().initWithFrame_(NSMakeRect(pad, y, 150, 32))
        self.generate_btn.setTitle_("✨ Generate Image")
        self.generate_btn.setBezelStyle_(NSBezelStyleRounded)
        self.generate_btn.setFont_(Fonts.body_medium())
        self.generate_btn.setTarget_(self.delegate)
        self.generate_btn.setAction_(
            objc.selector(self.delegate.generateClicked_, signature=b"v@:@")
        )
        self.generate_btn.setKeyEquivalent_("\r")
        section.addSubview_(self.generate_btn)

        # Edit button
        edit_btn = NSButton.alloc().initWithFrame_(NSMakeRect(pad + 160, y, 120, 32))
        edit_btn.setTitle_("🖌 Edit Image")
        edit_btn.setBezelStyle_(NSBezelStyleRounded)
        edit_btn.setFont_(Fonts.body_medium())
        edit_btn.setTarget_(self.delegate)
        edit_btn.setAction_(objc.selector(self.delegate.editClicked_, signature=b"v@:@"))
        section.addSubview_(edit_btn)

        # Spinner
        self.spinner = NSProgressIndicator.alloc().initWithFrame_(
            NSMakeRect(pad + 300, y + 6, 20, 20)
        )
        self.spinner.setStyle_(NSProgressIndicatorSpinningStyle)
        self.spinner.setDisplayedWhenStopped_(False)
        section.addSubview_(self.spinner)

        # Status label
        self.status_label = NSTextField.labelWithString_("")
        self.status_label.setFont_(Fonts.caption())
        self.status_label.setTextColor_(Colors.TEXT_SECONDARY)
        self.status_label.setFrame_(NSMakeRect(pad + 330, y + 6, 300, 18))
        self.status_label.setAutoresizingMask_(NSViewWidthSizable)
        section.addSubview_(self.status_label)

        # Divider
        div = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, 1))
        div.setWantsLayer_(True)
        div.layer().setBackgroundColor_(Colors.DIVIDER.CGColor())
        div.setAutoresizingMask_(NSViewWidthSizable)
        section.addSubview_(div)

        content.addSubview_(section)

    # ──────────────────────────────────────────────────────────────
    # GALLERY SECTION
    # ──────────────────────────────────────────────────────────────

    def _build_gallery_section(self, content, W, H):
        gallery_top = H - 60 - 230
        gallery_h = gallery_top

        # Gallery header bar
        bar_h = 32
        bar = NSView.alloc().initWithFrame_(NSMakeRect(0, gallery_top - bar_h, W, bar_h))
        bar.setWantsLayer_(True)
        bar.layer().setBackgroundColor_(Colors.WINDOW_BG.CGColor())
        bar.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)

        gal_label = NSTextField.labelWithString_("📸 Gallery")
        gal_label.setFont_(Fonts.h3())
        gal_label.setTextColor_(Colors.TEXT_PRIMARY)
        gal_label.setFrame_(NSMakeRect(20, 4, 120, 20))
        bar.addSubview_(gal_label)

        self.gallery_count_label = NSTextField.labelWithString_("")
        self.gallery_count_label.setFont_(Fonts.caption())
        self.gallery_count_label.setTextColor_(Colors.TEXT_MUTED)
        self.gallery_count_label.setFrame_(NSMakeRect(120, 6, 100, 16))
        bar.addSubview_(self.gallery_count_label)

        refresh_btn = NSButton.alloc().initWithFrame_(NSMakeRect(W - 100, 2, 80, 24))
        refresh_btn.setTitle_("↻ Refresh")
        refresh_btn.setBezelStyle_(NSBezelStyleRounded)
        refresh_btn.setFont_(Fonts.caption())
        refresh_btn.setTarget_(self.delegate)
        refresh_btn.setAction_(objc.selector(self.delegate.refreshGallery_, signature=b"v@:@"))
        refresh_btn.setAutoresizingMask_(1 << 0)  # NSViewMinXMargin
        bar.addSubview_(refresh_btn)

        content.addSubview_(bar)

        # Gallery scroll area
        scroll_h = gallery_top - bar_h
        self.gallery_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, W, scroll_h))
        self.gallery_scroll.setHasVerticalScroller_(True)
        self.gallery_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        self.gallery_scroll.setBackgroundColor_(Colors.CONTENT_BG)
        self.gallery_scroll.setDrawsBackground_(True)

        self.gallery_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, scroll_h))
        self.gallery_scroll.setDocumentView_(self.gallery_view)

        content.addSubview_(self.gallery_scroll)

    # ──────────────────────────────────────────────────────────────
    # GALLERY LOADING
    # ──────────────────────────────────────────────────────────────

    def load_gallery(self):
        """Scan ~/Pictures/SortMeOut for images and display them."""
        self.gallery_images = []
        output_dir = Path(OUTPUT_DIR)

        if output_dir.exists():
            for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".tiff"}:
                    try:
                        stat = f.stat()
                        self.gallery_images.append(
                            {
                                "path": str(f),
                                "name": f.name,
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                            }
                        )
                    except Exception:
                        pass

        self._render_gallery()

    def _render_gallery(self):
        """Render gallery items into the scroll view."""
        # Clear existing subviews
        for subview in list(self.gallery_view.subviews()):
            subview.removeFromSuperview()

        images = self.gallery_images[:50]  # Cap at 50
        W = self.gallery_scroll.frame().size.width

        if not images:
            self._render_empty_gallery(W)
            self.gallery_count_label.setStringValue_("")
            return

        self.gallery_count_label.setStringValue_(f"({len(images)} images)")

        # Grid layout: 3 columns
        pad = 16
        cols = 3
        spacing = 10
        card_w = (W - pad * 2 - spacing * (cols - 1)) / cols
        thumb_h = card_w * 0.75
        card_h = thumb_h + 44  # room for name + size

        rows = (len(images) + cols - 1) // cols
        total_h = rows * (card_h + spacing) + pad * 2

        # Ensure gallery_view is big enough
        scroll_h = self.gallery_scroll.frame().size.height
        view_h = max(total_h, scroll_h)
        self.gallery_view.setFrame_(NSMakeRect(0, 0, W, view_h))

        for i, img_info in enumerate(images):
            col = i % cols
            row = i // cols
            x = pad + col * (card_w + spacing)
            y = view_h - pad - (row + 1) * (card_h + spacing) + spacing

            card = self._create_gallery_card(img_info, x, y, card_w, card_h, thumb_h, i)
            self.gallery_view.addSubview_(card)

    def _render_empty_gallery(self, W):
        """Show empty state."""
        h = self.gallery_scroll.frame().size.height
        self.gallery_view.setFrame_(NSMakeRect(0, 0, W, h))

        # Icon
        icon = NSTextField.labelWithString_("🎨")
        icon.setFont_(NSFont.systemFontOfSize_(48))
        icon.setAlignment_(NSTextAlignmentCenter)
        icon.setFrame_(NSMakeRect(0, h / 2 + 20, W, 60))
        self.gallery_view.addSubview_(icon)

        # Title
        title = NSTextField.labelWithString_("No images yet")
        title.setFont_(Fonts.h2())
        title.setTextColor_(Colors.TEXT_PRIMARY)
        title.setAlignment_(NSTextAlignmentCenter)
        title.setFrame_(NSMakeRect(0, h / 2 - 10, W, 24))
        self.gallery_view.addSubview_(title)

        # Subtitle
        sub = NSTextField.labelWithString_("Generate your first image with DALL·E 3 above")
        sub.setFont_(Fonts.body())
        sub.setTextColor_(Colors.TEXT_MUTED)
        sub.setAlignment_(NSTextAlignmentCenter)
        sub.setFrame_(NSMakeRect(0, h / 2 - 34, W, 18))
        self.gallery_view.addSubview_(sub)

    def _create_gallery_card(self, img_info, x, y, w, h, thumb_h, index):
        """Create a single gallery card with thumbnail, name, and size."""
        card = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        card.setWantsLayer_(True)
        card.layer().setBackgroundColor_(Colors.CARD_BG.CGColor())
        card.layer().setCornerRadius_(8)
        card.layer().setBorderWidth_(1)
        card.layer().setBorderColor_(Colors.BORDER.CGColor())

        # Thumbnail
        thumb_view = NSImageView.alloc().initWithFrame_(NSMakeRect(0, h - thumb_h, w, thumb_h))
        thumb_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        thumb_view.setWantsLayer_(True)
        thumb_view.layer().setCornerRadius_(8)
        thumb_view.layer().setMasksToBounds_(True)

        # Load image in background to avoid blocking
        path = img_info["path"]
        ns_image = NSImage.alloc().initWithContentsOfFile_(path)
        if ns_image:
            thumb_view.setImage_(ns_image)

        card.addSubview_(thumb_view)

        # Name label
        name = NSTextField.labelWithString_(img_info["name"])
        name.setFont_(Fonts.caption())
        name.setTextColor_(Colors.TEXT_PRIMARY)
        name.setLineBreakMode_(NSLineBreakByTruncatingTail)
        name.setFrame_(NSMakeRect(6, 20, w - 12, 16))
        card.addSubview_(name)

        # Size label
        size_str = self._human_size(img_info["size"])
        mod_dt = datetime.fromtimestamp(img_info["modified"])
        time_str = mod_dt.strftime("%d/%m %H:%M")
        size_label = NSTextField.labelWithString_(f"{size_str} · {time_str}")
        size_label.setFont_(Fonts.small())
        size_label.setTextColor_(Colors.TEXT_MUTED)
        size_label.setFrame_(NSMakeRect(6, 4, w - 12, 14))
        card.addSubview_(size_label)

        # Clickable button overlay
        btn = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        btn.setTransparent_(True)
        btn.setTarget_(self.delegate)
        btn.setAction_(objc.selector(self.delegate.galleryItemClicked_, signature=b"v@:@"))
        btn.setTag_(index)
        card.addSubview_(btn)

        return card

    # ──────────────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────────────

    def do_generate(self):
        """Generate an image with DALL·E 3."""
        if self.is_generating:
            return

        prompt = self.prompt_field.string().strip()
        if not prompt:
            self._set_status("⚠️ Enter a prompt to generate an image", Colors.WARNING)
            return

        # Get options
        size_map = {
            0: "1024x1024",
            1: "1792x1024",
            2: "1024x1792",
        }
        quality_map = {0: "hd", 1: "standard"}
        style_map = {0: "vivid", 1: "natural"}

        size = size_map.get(self.size_popup.indexOfSelectedItem(), "1024x1024")
        quality = quality_map.get(self.quality_popup.indexOfSelectedItem(), "hd")
        style = style_map.get(self.style_popup.indexOfSelectedItem(), "vivid")

        self.is_generating = True
        self.generate_btn.setEnabled_(False)
        self.spinner.startAnimation_(None)
        self._set_status("Generating image with DALL·E 3…", Colors.ACCENT)

        def _do():
            try:
                from sortmeout.integrations.images import get_generator

                gen = get_generator()
                if not gen.is_available:
                    self._on_main(
                        lambda: self._generation_done(
                            {
                                "error": "OpenAI API key not set. Add OPENAI_API_KEY to ~/.config/sortmeout/.env"
                            }
                        )
                    )
                    return
                result = gen.generate(prompt=prompt, size=size, quality=quality, style=style)
                self._on_main(lambda: self._generation_done(result))
            except Exception as e:
                self._on_main(lambda: self._generation_done({"error": str(e)}))

        threading.Thread(target=_do, daemon=True).start()

    def _generation_done(self, result):
        """Handle generation result on main thread."""
        self.is_generating = False
        self.generate_btn.setEnabled_(True)
        self.spinner.stopAnimation_(None)

        if result.get("error"):
            self._set_status(f"❌ {result['error'][:100]}", Colors.ERROR)
        elif result.get("success"):
            path = result.get("path", "")
            self._set_status(f"✅ Saved to {os.path.basename(path)}", Colors.SUCCESS)
            self.prompt_field.setString_("")
            self.load_gallery()
        else:
            self._set_status("❌ Generation failed", Colors.ERROR)

    def do_edit(self):
        """Open a file picker and apply editing operations."""
        script = """
            tell application "System Events"
                activate
                set theFile to choose file with prompt "Select an image to edit:" of type {"public.image"}
                return POSIX path of theFile
            end tell
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0 or not result.stdout.strip():
                return

            image_path = result.stdout.strip()
            self._show_edit_options(image_path)
        except Exception as e:
            self._set_status(f"Error: {e}", Colors.ERROR)

    def _show_edit_options(self, image_path):
        """Show edit options dialog via osascript."""
        filename = os.path.basename(image_path)
        script = f"""
            tell application "System Events"
                activate
                set editAction to choose from list {{"Resize", "Rotate 90°", "Rotate 180°", "Flip Horizontal", "Flip Vertical", "Grayscale", "Sepia", "Blur", "Sharpen", "Auto Contrast", "Compress (70%)", "Convert to PNG", "Convert to JPEG", "Get Info"}} with prompt "Edit: {filename}" with title "Image Editor"
                if editAction is false then return ""
                return item 1 of editAction
            end tell
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return
            action = result.stdout.strip()
            if not action:
                return

            self._apply_edit(image_path, action)
        except Exception as e:
            self._set_status(f"Error: {e}", Colors.ERROR)

    def _apply_edit(self, path, action):
        """Apply an edit action to an image."""
        self._set_status(f"Applying {action}…", Colors.ACCENT)
        self.spinner.startAnimation_(None)

        def _do():
            try:
                from sortmeout.integrations.images import get_editor

                editor = get_editor()
                result = None

                if action == "Resize":
                    # Ask for width
                    script = """
                        tell application "System Events"
                            display dialog "Enter new width (height auto-calculated):" default answer "800" with title "Resize"
                            return text returned of result
                        end tell
                    """
                    r = subprocess.run(
                        ["osascript", "-e", script], capture_output=True, text=True, timeout=30
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        width = int(r.stdout.strip())
                        result = editor.resize(path, width=width)

                elif action == "Rotate 90°":
                    result = editor.rotate(path, degrees=90)

                elif action == "Rotate 180°":
                    result = editor.rotate(path, degrees=180)

                elif action == "Flip Horizontal":
                    result = editor.flip(path, direction="horizontal")

                elif action == "Flip Vertical":
                    result = editor.flip(path, direction="vertical")

                elif action == "Grayscale":
                    result = editor.apply_filter(path, filter_name="grayscale")

                elif action == "Sepia":
                    result = editor.apply_filter(path, filter_name="sepia")

                elif action == "Blur":
                    result = editor.apply_filter(path, filter_name="blur", intensity=1.0)

                elif action == "Sharpen":
                    result = editor.apply_filter(path, filter_name="sharpen", intensity=1.5)

                elif action == "Auto Contrast":
                    result = editor.apply_filter(path, filter_name="auto_contrast")

                elif action == "Compress (70%)":
                    result = editor.compress(path, quality=70)

                elif action == "Convert to PNG":
                    result = editor.convert(path, format="png")

                elif action == "Convert to JPEG":
                    result = editor.convert(path, format="jpeg")

                elif action == "Get Info":
                    result = editor.get_info(path)

                self._on_main(lambda: self._edit_done(result, action))
            except Exception as e:
                self._on_main(lambda: self._edit_done({"error": str(e)}, action))

        threading.Thread(target=_do, daemon=True).start()

    def _edit_done(self, result, action):
        """Handle edit result on main thread."""
        self.spinner.stopAnimation_(None)

        if result is None:
            self._set_status("Cancelled", Colors.TEXT_MUTED)
            return

        if result.get("error"):
            self._set_status(f"❌ {result['error'][:100]}", Colors.ERROR)
            return

        if action == "Get Info":
            info_lines = [
                f"Format: {result.get('format', '?')}",
                f"Size: {result.get('width', '?')}×{result.get('height', '?')}",
                f"Mode: {result.get('mode', '?')}",
                f"File: {result.get('size_human', '?')}",
            ]
            from AppKit import NSAlert, NSInformationalAlertStyle

            alert = NSAlert.alloc().init()
            alert.setMessageText_(f"Image Info")
            alert.setInformativeText_("\n".join(info_lines))
            alert.setAlertStyle_(NSInformationalAlertStyle)
            alert.runModal()
            self._set_status("", Colors.TEXT_MUTED)
            return

        out_path = result.get("path", "")
        self._set_status(f"✅ {action} → {os.path.basename(out_path)}", Colors.SUCCESS)
        # Open result in Preview
        if out_path:
            subprocess.Popen(["open", out_path])
        self.load_gallery()

    def open_gallery_item(self, index):
        """Open a gallery image in Preview."""
        if 0 <= index < len(self.gallery_images):
            path = self.gallery_images[index]["path"]
            subprocess.Popen(["open", path])

    def open_output_folder(self):
        """Open ~/Pictures/SortMeOut in Finder."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        subprocess.Popen(["open", OUTPUT_DIR])

    # ──────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────

    def _set_status(self, text, color=None):
        """Update the status label."""
        self.status_label.setStringValue_(text)
        if color:
            self.status_label.setTextColor_(color)

    def _on_main(self, fn):
        """Execute a function on the main thread via performSelectorOnMainThread."""
        # Store the callback and use a timer to execute it
        self._pending_callback = fn
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.01,
            self.delegate,
            objc.selector(self.delegate._runCallback_, signature=b"v@:@"),
            None,
            False,
        )

    @staticmethod
    def _human_size(size_bytes):
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def show(self):
        """Show the window."""
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        self.load_gallery()  # Refresh on show


# ═══════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE & ENTRY POINTS
# ═══════════════════════════════════════════════════════════════════

_image_window = None


def show_image_window():
    """Show the Image Studio window (singleton)."""
    global _image_window
    if not HAS_APPKIT:
        print("AppKit not available — Image Studio requires macOS with PyObjC")
        return False
    if _image_window is None:
        _image_window = ImageWindow()
    _image_window.show()
    return True


def main():
    """Standalone entry point for Image Studio."""
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
    am.addItemWithTitle_action_keyEquivalent_(
        "About Image Studio", "orderFrontStandardAboutPanel:", ""
    )
    am.addItem_(NSMenuItem.separatorItem())
    am.addItemWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
    ami.setSubmenu_(am)

    window = ImageWindow()
    window.show()
    app.activateIgnoringOtherApps_(True)
    app.run()


if __name__ == "__main__":
    main()
