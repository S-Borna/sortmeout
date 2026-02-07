"""
Template rules for onboarding and quick setup.

Provides pre-built rule templates that users can apply with one click
to get started with common file organization patterns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _template(
    name: str,
    description: str,
    category: str,
    conditions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    match_mode: str = "all",
    folder_hint: str = "~/Downloads",
) -> Dict[str, Any]:
    """Helper to create a template dict."""
    return {
        "name": name,
        "description": description,
        "category": category,
        "match_mode": match_mode,
        "conditions": conditions,
        "actions": actions,
        "enabled": True,
        "folder_hint": folder_hint,
    }


# ============================================================
# TEMPLATE DEFINITIONS
# ============================================================

TEMPLATES: List[Dict[str, Any]] = [
    # --- Downloads Organization ---
    _template(
        name="Organize Images",
        description="Move image files (JPG, PNG, GIF, HEIC, WebP) to a Pictures folder.",
        category="Downloads",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["jpg", "jpeg", "png", "gif", "heic", "webp", "tiff", "bmp", "svg"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Pictures/Downloads"}},
        ],
    ),
    _template(
        name="Organize Documents",
        description="Move document files (PDF, DOCX, XLSX, PPTX, TXT) to Documents.",
        category="Downloads",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf", "pages", "numbers", "key"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Documents/Downloads"}},
        ],
    ),
    _template(
        name="Organize Videos",
        description="Move video files to a Videos folder.",
        category="Downloads",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["mp4", "mov", "avi", "mkv", "wmv", "flv", "webm", "m4v"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Movies/Downloads"}},
        ],
    ),
    _template(
        name="Organize Audio",
        description="Move audio files to a Music folder.",
        category="Downloads",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "aiff"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Music/Downloads"}},
        ],
    ),
    _template(
        name="Organize Archives",
        description="Move compressed archives to an Archives folder.",
        category="Downloads",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["zip", "tar", "gz", "bz2", "7z", "rar", "dmg", "iso", "xz"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Downloads/Archives"}},
        ],
    ),
    _template(
        name="Organize Installers",
        description="Move macOS installers (.dmg, .pkg) to an Installers folder.",
        category="Downloads",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["dmg", "pkg", "app"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Downloads/Installers"}},
        ],
    ),

    # --- Cleanup ---
    _template(
        name="Archive Old Downloads",
        description="Move files older than 30 days from Downloads to an Old Downloads folder.",
        category="Cleanup",
        conditions=[
            {"attribute": "date_modified", "operator": "not_within_last", "value": "30 days"},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Downloads/Old"}},
        ],
    ),
    _template(
        name="Trash Old Screenshots",
        description="Move screenshots older than 7 days to Trash.",
        category="Cleanup",
        conditions=[
            {"attribute": "name", "operator": "starts_with", "value": "Screenshot"},
            {"attribute": "date_created", "operator": "not_within_last", "value": "7 days"},
        ],
        actions=[
            {"action_type": "trash", "params": {}},
        ],
        folder_hint="~/Desktop",
    ),
    _template(
        name="Delete Large Temp Files",
        description="Trash files larger than 500 MB that haven't been modified in 14 days.",
        category="Cleanup",
        conditions=[
            {"attribute": "size", "operator": "greater_than", "value": "500MB"},
            {"attribute": "date_modified", "operator": "not_within_last", "value": "14 days"},
        ],
        actions=[
            {"action_type": "trash", "params": {}},
            {"action_type": "notify", "params": {"message": "Trashed large old file: {full_name}"}},
        ],
    ),

    # --- Tagging ---
    _template(
        name="Tag Recent Downloads",
        description="Add a 'Downloaded' tag to recently downloaded files.",
        category="Tags",
        conditions=[
            {"attribute": "date_added", "operator": "within_last", "value": "1 day"},
        ],
        actions=[
            {"action_type": "add_tags", "params": {"tags": ["Downloaded"]}},
        ],
    ),
    _template(
        name="Tag Large Files",
        description="Add a 'Large' tag to files bigger than 100 MB.",
        category="Tags",
        conditions=[
            {"attribute": "size", "operator": "greater_than", "value": "100MB"},
        ],
        actions=[
            {"action_type": "add_tags", "params": {"tags": ["Large"]}},
        ],
    ),
    _template(
        name="Color-code by Type",
        description="Set Finder label color based on file type: Green for docs, Blue for images.",
        category="Tags",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["pdf", "doc", "docx", "txt"]},
        ],
        actions=[
            {"action_type": "set_label", "params": {"label": "green"}},
        ],
    ),

    # --- Desktop Cleanup ---
    _template(
        name="Clean Desktop Weekly",
        description="Move files that have been on the Desktop for more than 7 days to a sorted folder.",
        category="Desktop",
        conditions=[
            {"attribute": "date_added", "operator": "not_within_last", "value": "7 days"},
        ],
        actions=[
            {"action_type": "sort_into_subfolder",
             "params": {"pattern": "Desktop Cleanup/{year}-{month}"}},
        ],
        folder_hint="~/Desktop",
    ),
    _template(
        name="Sort Desktop by Date",
        description="Automatically sort Desktop files into year/month subfolders.",
        category="Desktop",
        conditions=[],
        match_mode="all",
        actions=[
            {"action_type": "sort_into_subfolder",
             "params": {"pattern": "{year}/{month}"}},
        ],
        folder_hint="~/Desktop",
    ),

    # --- Notifications ---
    _template(
        name="Notify on Large Downloads",
        description="Get a notification when a file larger than 1 GB appears in Downloads.",
        category="Notifications",
        conditions=[
            {"attribute": "size", "operator": "greater_than", "value": "1GB"},
        ],
        actions=[
            {"action_type": "notify",
             "params": {"title": "Large Download", "message": "{full_name} ({size})"}},
        ],
    ),

    # --- Development ---
    _template(
        name="Organize Code Projects",
        description="Move code files to a Projects folder by extension type.",
        category="Development",
        conditions=[
            {"attribute": "extension", "operator": "in_list",
             "value": ["py", "js", "ts", "rb", "go", "rs", "java", "swift", "c", "cpp", "h"]},
        ],
        actions=[
            {"action_type": "move", "params": {"destination": "~/Documents/Code"}},
        ],
    ),
]


def get_templates() -> List[Dict[str, Any]]:
    """Get all available rule templates."""
    return TEMPLATES


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get templates filtered by category."""
    return [t for t in TEMPLATES if t["category"].lower() == category.lower()]


def get_categories() -> List[str]:
    """Get list of unique template categories."""
    seen = set()
    categories = []
    for t in TEMPLATES:
        cat = t["category"]
        if cat not in seen:
            seen.add(cat)
            categories.append(cat)
    return categories


def get_template_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a template by its name (case-insensitive)."""
    name_lower = name.lower()
    for t in TEMPLATES:
        if t["name"].lower() == name_lower:
            return t
    return None


def template_to_rule_dict(
    template: Dict[str, Any],
    folder: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a template to a full rule dictionary ready to be imported.

    Args:
        template: Template dictionary.
        folder: Override folder (defaults to template's folder_hint).

    Returns:
        Rule dictionary compatible with Rule.from_dict().
    """
    return {
        "name": template["name"],
        "description": template.get("description", ""),
        "match_mode": template.get("match_mode", "all"),
        "conditions": template.get("conditions", []),
        "actions": template.get("actions", []),
        "enabled": True,
        "priority": 0,
        "folder": folder or template.get("folder_hint", "~/Downloads"),
    }


def get_onboarding_templates() -> List[Dict[str, Any]]:
    """
    Get the recommended templates for new user onboarding.

    Returns a curated subset that covers the most common use cases.
    """
    recommended = [
        "Organize Images",
        "Organize Documents",
        "Archive Old Downloads",
        "Trash Old Screenshots",
        "Tag Recent Downloads",
    ]
    return [t for t in TEMPLATES if t["name"] in recommended]
