"""
File information extraction.

This module provides functions for extracting various attributes from files,
including standard file system attributes and macOS-specific metadata.
"""

from __future__ import annotations

import mimetypes
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive information about a file.

    Args:
        file_path: Path to the file.

    Returns:
        Dictionary containing file attributes.
    """
    path = Path(file_path)
    stat = path.stat()

    info = {
        # Basic attributes
        "path": str(path.absolute()),
        "name": path.stem,
        "extension": path.suffix.lstrip(".").lower(),
        "full_name": path.name,
        "parent_folder": path.parent.name,
        "parent_path": str(path.parent),

        # Size
        "size": stat.st_size,
        "size_bytes": stat.st_size,
        "size_human": _format_size(stat.st_size),

        # Dates
        "date_created": datetime.fromtimestamp(stat.st_birthtime) if hasattr(stat, "st_birthtime") else datetime.fromtimestamp(stat.st_ctime),
        "date_modified": datetime.fromtimestamp(stat.st_mtime),
        "date_accessed": datetime.fromtimestamp(stat.st_atime),

        # Type
        "is_file": path.is_file(),
        "is_directory": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "is_hidden": path.name.startswith("."),
    }

    # MIME type
    mime_type, _ = mimetypes.guess_type(str(path))
    info["mime_type"] = mime_type
    info["file_type"] = mime_type

    # Determine kind based on extension/mime
    info["kind"] = _get_file_kind(path.suffix, mime_type)

    # macOS-specific attributes
    try:
        macos_info = _get_macos_metadata(file_path)
        info.update(macos_info)
    except Exception:
        pass

    return info


def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _get_file_kind(extension: str, mime_type: Optional[str]) -> str:
    """Determine the kind of file based on extension and MIME type."""
    extension = extension.lower().lstrip(".")

    # Extension-based kinds
    kinds = {
        # Documents
        "pdf": "PDF Document",
        "doc": "Word Document",
        "docx": "Word Document",
        "xls": "Excel Spreadsheet",
        "xlsx": "Excel Spreadsheet",
        "ppt": "PowerPoint Presentation",
        "pptx": "PowerPoint Presentation",
        "txt": "Plain Text",
        "rtf": "Rich Text Document",
        "md": "Markdown Document",
        "pages": "Pages Document",
        "numbers": "Numbers Spreadsheet",
        "key": "Keynote Presentation",

        # Images
        "jpg": "JPEG Image",
        "jpeg": "JPEG Image",
        "png": "PNG Image",
        "gif": "GIF Image",
        "bmp": "BMP Image",
        "tiff": "TIFF Image",
        "tif": "TIFF Image",
        "webp": "WebP Image",
        "svg": "SVG Image",
        "ico": "Icon",
        "heic": "HEIC Image",
        "heif": "HEIF Image",
        "raw": "RAW Image",
        "psd": "Photoshop Document",
        "ai": "Illustrator Document",

        # Audio
        "mp3": "MP3 Audio",
        "wav": "WAV Audio",
        "aac": "AAC Audio",
        "flac": "FLAC Audio",
        "m4a": "M4A Audio",
        "ogg": "OGG Audio",
        "wma": "WMA Audio",
        "aiff": "AIFF Audio",

        # Video
        "mp4": "MP4 Video",
        "mov": "QuickTime Movie",
        "avi": "AVI Video",
        "mkv": "MKV Video",
        "wmv": "WMV Video",
        "flv": "FLV Video",
        "webm": "WebM Video",
        "m4v": "M4V Video",

        # Archives
        "zip": "ZIP Archive",
        "rar": "RAR Archive",
        "7z": "7-Zip Archive",
        "tar": "TAR Archive",
        "gz": "Gzip Archive",
        "bz2": "Bzip2 Archive",
        "dmg": "Disk Image",
        "iso": "ISO Image",

        # Code
        "py": "Python Script",
        "js": "JavaScript",
        "ts": "TypeScript",
        "html": "HTML Document",
        "css": "CSS Stylesheet",
        "json": "JSON File",
        "xml": "XML File",
        "yaml": "YAML File",
        "yml": "YAML File",
        "sh": "Shell Script",
        "java": "Java Source",
        "cpp": "C++ Source",
        "c": "C Source",
        "h": "Header File",
        "swift": "Swift Source",
        "rb": "Ruby Script",
        "go": "Go Source",
        "rs": "Rust Source",

        # Applications
        "app": "Application",
        "exe": "Windows Executable",
        "pkg": "Installer Package",

        # Other
        "torrent": "Torrent File",
        "ics": "Calendar Event",
        "vcf": "Contact Card",
    }

    if extension in kinds:
        return kinds[extension]

    # MIME-based fallback
    if mime_type:
        if mime_type.startswith("image/"):
            return "Image"
        elif mime_type.startswith("video/"):
            return "Video"
        elif mime_type.startswith("audio/"):
            return "Audio"
        elif mime_type.startswith("text/"):
            return "Text Document"
        elif mime_type.startswith("application/"):
            return "Application"

    return "Document"


def _get_macos_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get macOS-specific metadata using mdls command.

    Args:
        file_path: Path to the file.

    Returns:
        Dictionary of macOS metadata.
    """
    info = {}

    try:
        # Get Spotlight metadata
        result = subprocess.run(
            ["mdls", "-plist", "-", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            import plistlib
            metadata = plistlib.loads(result.stdout.encode())

            # Extract useful attributes
            attr_mapping = {
                "kMDItemWhereFroms": "where_from",
                "kMDItemUserTags": "tags",
                "kMDItemFinderComment": "finder_comment",
                "kMDItemContentType": "uti",
                "kMDItemKind": "kind_macos",
                "kMDItemDateAdded": "date_added",
                "kMDItemDownloadedDate": "date_downloaded",
                "kMDItemPixelHeight": "pixel_height",
                "kMDItemPixelWidth": "pixel_width",
                "kMDItemDurationSeconds": "duration_seconds",
                "kMDItemTitle": "title",
                "kMDItemAuthors": "authors",
                "kMDItemCreator": "creator",
                "kMDItemDescription": "description",
            }

            for mdls_key, our_key in attr_mapping.items():
                if mdls_key in metadata and metadata[mdls_key] is not None:
                    value = metadata[mdls_key]
                    # Handle lists
                    if isinstance(value, list) and len(value) == 1:
                        value = value[0]
                    info[our_key] = value

    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    except Exception:
        pass

    # Get tags using xattr if not found via mdls
    if "tags" not in info:
        try:
            tags = _get_finder_tags(file_path)
            if tags:
                info["tags"] = tags
        except Exception:
            pass

    return info


def _get_finder_tags(file_path: str) -> List[str]:
    """
    Get Finder tags from a file using xattr.

    Args:
        file_path: Path to the file.

    Returns:
        List of tag names.
    """
    try:
        import plistlib

        result = subprocess.run(
            ["xattr", "-p", "com.apple.metadata:_kMDItemUserTags", file_path],
            capture_output=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout:
            # Parse the binary plist
            tags_data = plistlib.loads(result.stdout)
            return [tag.split("\n")[0] for tag in tags_data if tag]
    except Exception:
        pass

    return []


def get_file_contents(file_path: str, max_bytes: int = 1024 * 1024) -> Optional[str]:
    """
    Read file contents (for text files).

    Args:
        file_path: Path to the file.
        max_bytes: Maximum bytes to read.

    Returns:
        File contents as string, or None if not readable.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except Exception:
        return None


def get_download_source(file_path: str) -> Optional[str]:
    """
    Get the URL from which a file was downloaded.

    Args:
        file_path: Path to the file.

    Returns:
        Download URL or None.
    """
    info = _get_macos_metadata(file_path)
    where_from = info.get("where_from")

    if isinstance(where_from, list):
        return where_from[0] if where_from else None
    return where_from


def is_complete_download(file_path: str) -> bool:
    """
    Check if a file is a complete download (not still being downloaded).

    Args:
        file_path: Path to the file.

    Returns:
        True if download is complete.
    """
    path = Path(file_path)

    # Check for common incomplete download extensions
    incomplete_extensions = {
        ".crdownload",  # Chrome
        ".part",  # Firefox, wget
        ".download",  # Safari
        ".tmp",
        ".partial",
    }

    if path.suffix.lower() in incomplete_extensions:
        return False

    # Check for .download companion file (Safari)
    if (path.parent / f"{path.name}.download").exists():
        return False

    return True
