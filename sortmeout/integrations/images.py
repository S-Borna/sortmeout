"""
Image creation and editing integration for SortMeOut.

Capabilities:
    - AI image generation via DALL-E 3 (text → high-quality image)
    - Resize, crop, rotate, flip
    - Filters: blur, sharpen, brightness, contrast, grayscale, sepia, invert
    - Add text overlay / watermark
    - Format conversion (PNG, JPEG, WEBP, TIFF, BMP)
    - Compress / optimize images
    - Batch operations
    - Image info (dimensions, format, size, color mode)

Requires:
    - Pillow (pip install Pillow) — local editing
    - openai (pip install openai) — AI image generation (optional)
"""

from __future__ import annotations

import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# ── Optional dependency: Pillow ──
try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont, ImageOps

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# ── Optional dependency: OpenAI (for DALL-E 3) ──
try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ── Default output directory ──
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/Pictures/SortMeOut")


class ImageEditor:
    """Local image editing powered by Pillow."""

    def __init__(self):
        if not HAS_PILLOW:
            raise ImportError(
                "Pillow is required for image editing. Install with: pip install Pillow"
            )

    # ──────────────────────────────────────────────────────────────
    # INFO
    # ──────────────────────────────────────────────────────────────

    def get_info(self, path: str) -> Dict[str, Any]:
        """Get image metadata: dimensions, format, size, color mode."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                file_size = p.stat().st_size
                return {
                    "path": str(p),
                    "format": img.format or p.suffix.upper().lstrip("."),
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "size_bytes": file_size,
                    "size_human": self._human_size(file_size),
                    "has_alpha": img.mode in ("RGBA", "LA", "PA"),
                    "is_animated": getattr(img, "is_animated", False),
                    "dpi": img.info.get("dpi", None),
                }
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # RESIZE / CROP / ROTATE
    # ──────────────────────────────────────────────────────────────

    def resize(
        self,
        path: str,
        width: int = 0,
        height: int = 0,
        output: Optional[str] = None,
        keep_aspect: bool = True,
    ) -> Dict[str, Any]:
        """Resize an image. If only width or height is given, maintains aspect ratio."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                orig_w, orig_h = img.size

                if keep_aspect:
                    if width and not height:
                        ratio = width / orig_w
                        height = int(orig_h * ratio)
                    elif height and not width:
                        ratio = height / orig_h
                        width = int(orig_w * ratio)
                    elif not width and not height:
                        return {"error": "Provide width and/or height"}

                if width <= 0 or height <= 0:
                    return {"error": "Invalid dimensions"}

                resized = img.resize(
                    (width, height),
                    Image.Resampling.LANCZOS,  # High-quality downscaling
                )

                out_path = output or self._auto_output(p, "resized")
                self._save_image(resized, out_path, img.format)

                return {
                    "success": True,
                    "path": out_path,
                    "original_size": f"{orig_w}x{orig_h}",
                    "new_size": f"{width}x{height}",
                }
        except Exception as e:
            return {"error": str(e)}

    def crop(
        self,
        path: str,
        left: int,
        top: int,
        right: int,
        bottom: int,
        output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Crop image to specified box (left, top, right, bottom)."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                cropped = img.crop((left, top, right, bottom))
                out_path = output or self._auto_output(p, "cropped")
                self._save_image(cropped, out_path, img.format)

                return {
                    "success": True,
                    "path": out_path,
                    "crop_box": f"({left}, {top}, {right}, {bottom})",
                    "new_size": f"{cropped.width}x{cropped.height}",
                }
        except Exception as e:
            return {"error": str(e)}

    def rotate(
        self,
        path: str,
        degrees: float,
        output: Optional[str] = None,
        expand: bool = True,
    ) -> Dict[str, Any]:
        """Rotate image by specified degrees (counter-clockwise). Expand=True grows canvas."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                rotated = img.rotate(degrees, expand=expand, resample=Image.Resampling.BICUBIC)
                out_path = output or self._auto_output(p, f"rotated_{int(degrees)}")
                self._save_image(rotated, out_path, img.format)

                return {
                    "success": True,
                    "path": out_path,
                    "degrees": degrees,
                    "new_size": f"{rotated.width}x{rotated.height}",
                }
        except Exception as e:
            return {"error": str(e)}

    def flip(
        self,
        path: str,
        direction: str = "horizontal",
        output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Flip image horizontally or vertically."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                if direction == "horizontal":
                    flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                elif direction == "vertical":
                    flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                else:
                    return {
                        "error": f"Invalid direction: {direction} (use 'horizontal' or 'vertical')"
                    }

                out_path = output or self._auto_output(p, f"flipped_{direction}")
                self._save_image(flipped, out_path, img.format)

                return {"success": True, "path": out_path, "direction": direction}
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # FILTERS & ADJUSTMENTS
    # ──────────────────────────────────────────────────────────────

    def apply_filter(
        self,
        path: str,
        filter_name: str,
        intensity: float = 1.0,
        output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply a filter to an image.

        Available filters:
            blur, sharpen, detail, edge_enhance, emboss, contour, smooth,
            grayscale, sepia, invert, brightness, contrast, saturation,
            auto_contrast, equalize
        """
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                # Ensure RGB for most operations
                work_img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()

                filter_name = filter_name.lower().strip()

                if filter_name == "blur":
                    radius = max(1, int(intensity * 5))
                    work_img = work_img.filter(ImageFilter.GaussianBlur(radius=radius))

                elif filter_name == "sharpen":
                    enhancer = ImageEnhance.Sharpness(work_img)
                    work_img = enhancer.enhance(1.0 + intensity)

                elif filter_name == "detail":
                    work_img = work_img.filter(ImageFilter.DETAIL)

                elif filter_name == "edge_enhance":
                    work_img = work_img.filter(ImageFilter.EDGE_ENHANCE_MORE)

                elif filter_name == "emboss":
                    work_img = work_img.filter(ImageFilter.EMBOSS)

                elif filter_name == "contour":
                    work_img = work_img.filter(ImageFilter.CONTOUR)

                elif filter_name == "smooth":
                    work_img = work_img.filter(ImageFilter.SMOOTH_MORE)

                elif filter_name == "grayscale":
                    work_img = ImageOps.grayscale(work_img)

                elif filter_name == "sepia":
                    gray = ImageOps.grayscale(work_img)
                    sepia_r = gray.point(lambda x: min(255, int(x * 1.2)))
                    sepia_g = gray.point(lambda x: min(255, int(x * 1.0)))
                    sepia_b = gray.point(lambda x: min(255, int(x * 0.8)))
                    work_img = Image.merge("RGB", (sepia_r, sepia_g, sepia_b))

                elif filter_name == "invert":
                    if work_img.mode == "RGBA":
                        r, g, b, a = work_img.split()
                        rgb = Image.merge("RGB", (r, g, b))
                        rgb = ImageOps.invert(rgb)
                        r2, g2, b2 = rgb.split()
                        work_img = Image.merge("RGBA", (r2, g2, b2, a))
                    else:
                        work_img = ImageOps.invert(work_img)

                elif filter_name == "brightness":
                    enhancer = ImageEnhance.Brightness(work_img)
                    work_img = enhancer.enhance(intensity)

                elif filter_name == "contrast":
                    enhancer = ImageEnhance.Contrast(work_img)
                    work_img = enhancer.enhance(intensity)

                elif filter_name == "saturation":
                    enhancer = ImageEnhance.Color(work_img)
                    work_img = enhancer.enhance(intensity)

                elif filter_name == "auto_contrast":
                    work_img = ImageOps.autocontrast(work_img)

                elif filter_name == "equalize":
                    work_img = ImageOps.equalize(work_img)

                else:
                    return {
                        "error": f"Unknown filter: {filter_name}",
                        "available": [
                            "blur",
                            "sharpen",
                            "detail",
                            "edge_enhance",
                            "emboss",
                            "contour",
                            "smooth",
                            "grayscale",
                            "sepia",
                            "invert",
                            "brightness",
                            "contrast",
                            "saturation",
                            "auto_contrast",
                            "equalize",
                        ],
                    }

                out_path = output or self._auto_output(p, filter_name)
                self._save_image(work_img, out_path, img.format)

                return {
                    "success": True,
                    "path": out_path,
                    "filter": filter_name,
                    "intensity": intensity,
                }
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # TEXT OVERLAY / WATERMARK
    # ──────────────────────────────────────────────────────────────

    def add_text(
        self,
        path: str,
        text: str,
        position: str = "bottom-right",
        font_size: int = 40,
        color: str = "white",
        opacity: int = 255,
        output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add text overlay or watermark to an image.

        Args:
            path: Image path
            text: Text to overlay
            position: "top-left", "top-right", "bottom-left", "bottom-right", "center"
            font_size: Font size in points
            color: Text color name (white, black, red, etc.)
            opacity: 0-255 (0=transparent, 255=opaque)
            output: Output path (defaults to auto-named)
        """
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            with Image.open(p) as img:
                # Convert to RGBA for transparency support
                overlay = img.convert("RGBA")
                txt_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(txt_layer)

                # Get font (use system font on macOS)
                font = self._get_font(font_size)

                # Calculate text size
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Calculate position
                x, y = self._calc_text_position(overlay.size, (text_width, text_height), position)

                # Parse color
                fill_color = self._parse_color(color, opacity)

                # Draw text with slight shadow for readability
                shadow_color = (0, 0, 0, min(opacity, 128))
                draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
                draw.text((x, y), text, font=font, fill=fill_color)

                # Composite
                result = Image.alpha_composite(overlay, txt_layer)

                # Convert back to original mode if needed
                if img.mode != "RGBA":
                    result = result.convert(img.mode)

                out_path = output or self._auto_output(p, "text")
                self._save_image(result, out_path, img.format)

                return {
                    "success": True,
                    "path": out_path,
                    "text": text,
                    "position": position,
                }
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # FORMAT CONVERSION & COMPRESSION
    # ──────────────────────────────────────────────────────────────

    def convert(
        self,
        path: str,
        format: str,
        output: Optional[str] = None,
        quality: int = 95,
    ) -> Dict[str, Any]:
        """Convert image to a different format (png, jpeg, webp, tiff, bmp)."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        fmt = format.lower().strip().lstrip(".")
        format_map = {
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "png": "PNG",
            "webp": "WEBP",
            "tiff": "TIFF",
            "tif": "TIFF",
            "bmp": "BMP",
            "gif": "GIF",
            "ico": "ICO",
        }

        pil_format = format_map.get(fmt)
        if not pil_format:
            return {"error": f"Unsupported format: {fmt}", "supported": list(format_map.keys())}

        try:
            with Image.open(p) as img:
                # Handle transparency for JPEG
                if pil_format == "JPEG" and img.mode in ("RGBA", "LA", "PA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif pil_format == "JPEG" and img.mode != "RGB":
                    img = img.convert("RGB")

                ext = fmt if fmt != "jpeg" else "jpg"
                out_path = output or str(p.with_suffix(f".{ext}"))

                save_kwargs = {}
                if pil_format in ("JPEG", "WEBP"):
                    save_kwargs["quality"] = quality
                    if pil_format == "JPEG":
                        save_kwargs["optimize"] = True
                if pil_format == "PNG":
                    save_kwargs["optimize"] = True

                img.save(out_path, format=pil_format, **save_kwargs)

                return {
                    "success": True,
                    "path": out_path,
                    "format": pil_format,
                    "size": self._human_size(os.path.getsize(out_path)),
                }
        except Exception as e:
            return {"error": str(e)}

    def compress(
        self,
        path: str,
        quality: int = 70,
        max_width: int = 0,
        output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compress/optimize an image to reduce file size.

        Args:
            path: Input image path
            quality: JPEG/WEBP quality (1-100, lower = smaller)
            max_width: Optionally resize to max width (0 = no resize)
            output: Output path
        """
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        try:
            original_size = p.stat().st_size

            with Image.open(p) as img:
                work = img.copy()

                # Optional resize
                if max_width > 0 and work.width > max_width:
                    ratio = max_width / work.width
                    new_height = int(work.height * ratio)
                    work = work.resize(
                        (max_width, new_height),
                        Image.Resampling.LANCZOS,
                    )

                # Determine output format
                out_path = output or self._auto_output(p, "compressed")

                # JPEG conversion for best compression
                if work.mode in ("RGBA", "LA", "PA"):
                    background = Image.new("RGB", work.size, (255, 255, 255))
                    background.paste(work, mask=work.split()[-1])
                    work = background
                elif work.mode != "RGB":
                    work = work.convert("RGB")

                # Save with compression
                if out_path.lower().endswith((".jpg", ".jpeg")):
                    work.save(out_path, "JPEG", quality=quality, optimize=True)
                elif out_path.lower().endswith(".webp"):
                    work.save(out_path, "WEBP", quality=quality)
                elif out_path.lower().endswith(".png"):
                    work.save(out_path, "PNG", optimize=True)
                else:
                    work.save(out_path, "JPEG", quality=quality, optimize=True)

                new_size = os.path.getsize(out_path)
                reduction = (
                    ((original_size - new_size) / original_size * 100) if original_size > 0 else 0
                )

                return {
                    "success": True,
                    "path": out_path,
                    "original_size": self._human_size(original_size),
                    "new_size": self._human_size(new_size),
                    "reduction": f"{reduction:.1f}%",
                    "quality": quality,
                }
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────

    def _auto_output(self, original: Path, suffix: str) -> str:
        """Generate output path based on original filename."""
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        name = original.stem
        ext = original.suffix or ".png"
        out = os.path.join(DEFAULT_OUTPUT_DIR, f"{name}_{suffix}{ext}")
        # Avoid overwriting
        counter = 1
        while os.path.exists(out):
            out = os.path.join(DEFAULT_OUTPUT_DIR, f"{name}_{suffix}_{counter}{ext}")
            counter += 1
        return out

    def _save_image(self, img: Any, path: str, original_format: Optional[str] = None) -> None:
        """Save image, determining format from extension."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        ext = Path(path).suffix.lower()
        fmt_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".webp": "WEBP",
            ".tiff": "TIFF",
            ".tif": "TIFF",
            ".bmp": "BMP",
            ".gif": "GIF",
        }
        fmt = fmt_map.get(ext, original_format or "PNG")

        save_kwargs = {}
        if fmt == "JPEG":
            if img.mode in ("RGBA", "LA", "PA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            save_kwargs["quality"] = 95
            save_kwargs["optimize"] = True
        elif fmt == "PNG":
            save_kwargs["optimize"] = True

        img.save(path, format=fmt, **save_kwargs)

    def _get_font(self, size: int) -> Any:
        """Get a font, trying system fonts first, falling back to default."""
        # macOS system fonts
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/System/Library/Fonts/SFNS.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue

        # Fallback to default
        try:
            return ImageFont.truetype("Helvetica", size)
        except Exception:
            return ImageFont.load_default()

    def _calc_text_position(
        self,
        image_size: Tuple[int, int],
        text_size: Tuple[int, int],
        position: str,
        margin: int = 20,
    ) -> Tuple[int, int]:
        """Calculate (x, y) for text placement."""
        w, h = image_size
        tw, th = text_size

        positions = {
            "top-left": (margin, margin),
            "top-right": (w - tw - margin, margin),
            "bottom-left": (margin, h - th - margin),
            "bottom-right": (w - tw - margin, h - th - margin),
            "center": ((w - tw) // 2, (h - th) // 2),
            "top-center": ((w - tw) // 2, margin),
            "bottom-center": ((w - tw) // 2, h - th - margin),
        }
        return positions.get(position, positions["bottom-right"])

    def _parse_color(self, color: str, opacity: int = 255) -> tuple:
        """Parse color name or hex to RGBA tuple."""
        colors = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "green": (0, 180, 0),
            "blue": (0, 100, 255),
            "yellow": (255, 255, 0),
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
            "pink": (255, 192, 203),
            "gray": (128, 128, 128),
            "grey": (128, 128, 128),
            "cyan": (0, 255, 255),
        }

        color = color.lower().strip()
        if color in colors:
            r, g, b = colors[color]
            return (r, g, b, opacity)

        # Try hex color
        if color.startswith("#") and len(color) in (4, 7):
            try:
                if len(color) == 4:
                    r = int(color[1] * 2, 16)
                    g = int(color[2] * 2, 16)
                    b = int(color[3] * 2, 16)
                else:
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                return (r, g, b, opacity)
            except ValueError:
                pass

        return (255, 255, 255, opacity)  # Default to white

    @staticmethod
    def _human_size(size: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size) < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class ImageGenerator:
    """AI-powered image generation via DALL-E 3.

    DALL-E 3 produces significantly higher quality than basic generators.
    Supports:
        - Natural language prompts
        - Multiple sizes (1024x1024, 1024x1792, 1792x1024)
        - HD quality mode
        - Style control (vivid vs natural)
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key.

        Args:
            api_key: OpenAI API key. Falls back to .env file, config file,
                     or OPENAI_API_KEY env var (in that order).
        """
        self.api_key = api_key or self._load_api_key()
        self._client = None
        self.output_dir = DEFAULT_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _load_api_key() -> str:
        """Load OpenAI API key from .env, config file, or environment."""
        # 1. Try .env file (same as Anthropic key)
        env_file = os.path.expanduser("~/.config/sortmeout/.env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            if key:
                                return key
            except Exception:
                pass

        # 2. Try dedicated config file
        config_file = os.path.expanduser("~/Documents/Config/OpenAI/openai_api_key.txt")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    key = f.read().strip()
                    if key:
                        return key
            except Exception:
                pass

        # 3. Fall back to environment variable
        return os.environ.get("OPENAI_API_KEY", "")

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            if not HAS_OPENAI:
                raise ImportError(
                    "OpenAI package required for AI image generation. "
                    "Install with: pip install openai"
                )
            if not self.api_key:
                raise ValueError(
                    "OpenAI API key required for AI image generation. "
                    "Set OPENAI_API_KEY environment variable or pass api_key parameter."
                )
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if AI image generation is available."""
        return HAS_OPENAI and bool(self.api_key)

    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "hd",
        style: str = "vivid",
        filename: Optional[str] = None,
        n: int = 1,
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt using DALL-E 3.

        Args:
            prompt: Natural language description of the desired image.
                   Be detailed for best results. DALL-E 3 excels at:
                   - Photorealistic scenes
                   - Artistic illustrations
                   - Product mockups
                   - Concept art
                   - Detailed compositions
            size: Image dimensions:
                  - "1024x1024" (square, default)
                  - "1024x1792" (portrait)
                  - "1792x1024" (landscape)
            quality: "hd" (detailed, higher cost) or "standard"
            style: "vivid" (dramatic, hyper-real) or "natural" (more realistic)
            filename: Output filename (auto-generated if not provided)
            n: Number of images (DALL-E 3 only supports 1 per call)

        Returns:
            Dict with success status, file path, revised prompt.
        """
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1,  # DALL-E 3 only supports n=1
                response_format="url",
            )

            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt

            # Download and save the image
            import urllib.request

            if not filename:
                safe_name = (
                    "".join(c for c in prompt[:50] if c.isalnum() or c in " -_")
                    .strip()
                    .replace(" ", "_")
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"ai_{safe_name}_{timestamp}.png"

            out_path = os.path.join(self.output_dir, filename)

            # Download image
            urllib.request.urlretrieve(image_url, out_path)

            # Open in Preview
            subprocess.Popen(["open", out_path])

            file_size = os.path.getsize(out_path)

            return {
                "success": True,
                "path": out_path,
                "prompt": prompt,
                "revised_prompt": revised_prompt,
                "size": size,
                "quality": quality,
                "style": style,
                "file_size": ImageEditor._human_size(file_size),
            }

        except openai.BadRequestError as e:
            # Content policy violation
            return {
                "success": False,
                "error": f"Content policy: {str(e)[:200]}",
                "hint": "Try rephrasing your prompt. Avoid copyrighted characters, real people, or sensitive content.",
            }
        except openai.AuthenticationError:
            return {
                "success": False,
                "error": "Invalid OpenAI API key. Check your OPENAI_API_KEY.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def edit_with_ai(
        self,
        path: str,
        prompt: str,
        size: str = "1024x1024",
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Edit/modify an existing image using DALL-E 2 image editing.

        Note: This uses DALL-E 2's edit endpoint which requires a
        square PNG image with transparency (mask) indicating where to edit.
        For simpler modifications, use ImageEditor's filters instead.

        Args:
            path: Source image path
            prompt: Description of the desired modification
            size: Output size
            filename: Output filename
        """
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"Image not found: {path}"}

        try:
            # Prepare image — DALL-E edit needs square PNG ≤ 4MB
            if HAS_PILLOW:
                with Image.open(p) as img:
                    # Make square
                    side = min(img.width, img.height, 1024)
                    left = (img.width - side) // 2
                    top = (img.height - side) // 2
                    img = img.crop((left, top, left + side, top + side))
                    img = img.resize((1024, 1024), Image.Resampling.LANCZOS)

                    # Save temp PNG with RGBA
                    temp_path = os.path.join(self.output_dir, "_temp_edit_input.png")
                    img.convert("RGBA").save(temp_path, "PNG")
            else:
                temp_path = str(p)

            with open(temp_path, "rb") as image_file:
                response = self.client.images.edit(
                    model="dall-e-2",
                    image=image_file,
                    prompt=prompt,
                    n=1,
                    size=size,
                    response_format="url",
                )

            image_url = response.data[0].url

            if not filename:
                safe_prompt = (
                    "".join(c for c in prompt[:30] if c.isalnum() or c in " -_")
                    .strip()
                    .replace(" ", "_")
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"ai_edit_{safe_prompt}_{timestamp}.png"

            out_path = os.path.join(self.output_dir, filename)

            import urllib.request

            urllib.request.urlretrieve(image_url, out_path)

            # Clean up temp file
            try:
                if os.path.exists(temp_path) and "_temp_" in temp_path:
                    os.remove(temp_path)
            except Exception:
                pass

            subprocess.Popen(["open", out_path])

            return {
                "success": True,
                "path": out_path,
                "source": str(p),
                "prompt": prompt,
            }

        except Exception as e:
            return {"success": False, "error": str(e)[:200]}


# ── Lazy-loaded singletons ──
_editor: Optional[ImageEditor] = None
_generator: Optional[ImageGenerator] = None


def get_editor() -> ImageEditor:
    """Get or create the singleton ImageEditor."""
    global _editor
    if _editor is None:
        _editor = ImageEditor()
    return _editor


def get_generator(api_key: Optional[str] = None) -> ImageGenerator:
    """Get or create the singleton ImageGenerator."""
    global _generator
    if _generator is None:
        _generator = ImageGenerator(api_key=api_key)
    return _generator
