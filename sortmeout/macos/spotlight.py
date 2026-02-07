"""
macOS Spotlight integration.

Provides functions for searching and retrieving Spotlight metadata.
"""

from __future__ import annotations

import plistlib
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_spotlight_value(value: str) -> str:
    """Sanitize a value for use in Spotlight query strings.

    Escapes double-quotes and backslashes to prevent query injection.
    """
    return value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")


def get_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get all Spotlight metadata for a file.

    Args:
        file_path: Path to the file.

    Returns:
        Dictionary of metadata attributes.
    """
    try:
        result = subprocess.run(
            ["mdls", "-plist", "-", file_path],
            capture_output=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {}

        metadata = plistlib.loads(result.stdout)
        return metadata

    except Exception as e:
        logger.error("Failed to get metadata for %s: %s", file_path, e)
        return {}


def get_attribute(file_path: str, attribute: str) -> Optional[Any]:
    """
    Get a specific Spotlight attribute for a file.

    Args:
        file_path: Path to the file.
        attribute: Spotlight attribute name (e.g., "kMDItemKind").

    Returns:
        Attribute value or None.
    """
    try:
        result = subprocess.run(
            ["mdls", "-name", attribute, "-raw", file_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        value = result.stdout.strip()
        if value == "(null)":
            return None

        return value

    except Exception as e:
        logger.debug("Failed to get attribute %s: %s", attribute, e)
        return None


def search_spotlight(
    query: str,
    folder: Optional[str] = None,
    limit: int = 100,
    attributes: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search for files using Spotlight.

    Args:
        query: Spotlight query string (e.g., "kMDItemKind == 'PDF Document'").
        folder: Optional folder to search in.
        limit: Maximum number of results.
        attributes: Specific attributes to retrieve.

    Returns:
        List of matching files with their metadata.
    """
    try:
        cmd = ["mdfind"]

        if folder:
            cmd.extend(["-onlyin", folder])

        cmd.append(query)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return []

        files = result.stdout.strip().split("\n")[:limit]

        if not attributes:
            return [{"path": f} for f in files if f]

        # Get attributes for each file
        results = []
        for file_path in files:
            if not file_path:
                continue

            metadata = {"path": file_path}
            for attr in attributes:
                value = get_attribute(file_path, attr)
                if value is not None:
                    metadata[attr] = value

            results.append(metadata)

        return results

    except Exception as e:
        logger.error("Spotlight search failed: %s", e)
        return []


def find_by_kind(kind: str, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files by their kind (e.g., "PDF Document", "JPEG image").

    Args:
        kind: File kind to search for.
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    query = f'kMDItemKind == "{_sanitize_spotlight_value(kind)}"'
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def find_by_extension(extension: str, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files by extension.

    Args:
        extension: File extension (without dot).
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    extension = extension.lstrip(".")
    query = f'kMDItemFSName == "*.{_sanitize_spotlight_value(extension)}"'
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def find_by_tag(tag: str, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files by Finder tag.

    Args:
        tag: Tag name to search for.
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    query = f'kMDItemUserTags == "{_sanitize_spotlight_value(tag)}"'
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def find_by_content(text: str, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files containing specific text.

    Args:
        text: Text to search for in file contents.
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    query = f'kMDItemTextContent == "{_sanitize_spotlight_value(text)}"c'  # c for case-insensitive
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def find_modified_after(date: datetime, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files modified after a specific date.

    Args:
        date: Cutoff date.
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    date_str = date.strftime("%Y-%m-%d")
    query = f'kMDItemFSContentChangeDate >= $time.iso({date_str})'
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def find_created_after(date: datetime, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files created after a specific date.

    Args:
        date: Cutoff date.
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    date_str = date.strftime("%Y-%m-%d")
    query = f'kMDItemFSCreationDate >= $time.iso({date_str})'
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def find_by_author(author: str, folder: Optional[str] = None, limit: int = 100) -> List[str]:
    """
    Find files by author.

    Args:
        author: Author name to search for.
        folder: Optional folder to search in.
        limit: Maximum number of results.

    Returns:
        List of file paths.
    """
    query = f'kMDItemAuthors == "{_sanitize_spotlight_value(author)}"c'
    results = search_spotlight(query, folder, limit)
    return [r["path"] for r in results]


def get_download_source(file_path: str) -> Optional[str]:
    """
    Get the URL from which a file was downloaded.

    Args:
        file_path: Path to the file.

    Returns:
        Download URL or None.
    """
    metadata = get_metadata(file_path)
    where_froms = metadata.get("kMDItemWhereFroms", [])

    if where_froms:
        return where_froms[0] if isinstance(where_froms, list) else where_froms

    return None


def get_uti(file_path: str) -> Optional[str]:
    """
    Get the Uniform Type Identifier for a file.

    Args:
        file_path: Path to the file.

    Returns:
        UTI string or None.
    """
    return get_attribute(file_path, "kMDItemContentType")


def file_matches_uti(file_path: str, uti: str) -> bool:
    """
    Check if a file conforms to a UTI.

    Args:
        file_path: Path to the file.
        uti: UTI to check against.

    Returns:
        True if file conforms to UTI.
    """
    file_uti = get_uti(file_path)
    if not file_uti:
        return False

    # Check if file UTI equals or conforms to target UTI
    if file_uti == uti:
        return True

    # Use mdls to check conformance
    type_tree = get_attribute(file_path, "kMDItemContentTypeTree")
    if type_tree:
        if isinstance(type_tree, str):
            type_tree = [type_tree]
        return uti in type_tree

    return False


# Common UTI constants
UTI_PDF = "com.adobe.pdf"
UTI_IMAGE = "public.image"
UTI_MOVIE = "public.movie"
UTI_AUDIO = "public.audio"
UTI_TEXT = "public.plain-text"
UTI_RTF = "public.rtf"
UTI_HTML = "public.html"
UTI_XML = "public.xml"
UTI_JSON = "public.json"
UTI_ZIP = "com.pkware.zip-archive"
UTI_FOLDER = "public.folder"
UTI_APPLICATION = "com.apple.application-bundle"
