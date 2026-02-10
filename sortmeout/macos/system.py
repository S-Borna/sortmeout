"""
macOS system commands for AI assistant.

Provides high-level functions for system operations:
notifications, clipboard, screenshots, system info,
volume control, dark mode, and more.
"""

from __future__ import annotations

import os
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Finder integration
# ---------------------------------------------------------------------------

def reveal_in_finder(path: str) -> bool:
    """Reveal a file or folder in Finder (select it)."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return False
    try:
        subprocess.run(["open", "-R", path], check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error("reveal_in_finder failed: %s", e)
        return False


def quick_look(path: str) -> bool:
    """Open a file in Quick Look preview."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return False
    try:
        subprocess.Popen(["qlmanage", "-p", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        logger.error("quick_look failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Compression
# ---------------------------------------------------------------------------

def compress(path: str) -> Optional[str]:
    """Compress a file or folder to a .zip archive. Returns archive path."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return None
    try:
        p = Path(path)
        archive_name = f"{p.stem}.zip"
        archive_path = str(p.parent / archive_name)
        # Use ditto for proper macOS zip (preserves resource forks, metadata)
        subprocess.run(
            ["ditto", "-c", "-k", "--sequesterRsrc", path, archive_path],
            check=True, capture_output=True,
        )
        return archive_path
    except Exception as e:
        logger.error("compress failed: %s", e)
        return None


def decompress(path: str, destination: Optional[str] = None) -> Optional[str]:
    """Decompress a .zip archive. Returns extraction path."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return None
    try:
        p = Path(path)
        dest = destination or str(p.parent / p.stem)
        os.makedirs(dest, exist_ok=True)
        subprocess.run(
            ["ditto", "-x", "-k", path, dest],
            check=True, capture_output=True,
        )
        return dest
    except Exception as e:
        logger.error("decompress failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def send_notification(title: str, message: str = "", sound: str = "default") -> bool:
    """Send a macOS notification via osascript."""
    try:
        script = f'display notification "{_escape(message)}" with title "{_escape(title)}"'
        if sound:
            script += f' sound name "{sound}"'
        subprocess.run(
            ["osascript", "-e", script],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except Exception as e:
        logger.error("send_notification failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------

def clipboard_copy(text: str) -> bool:
    """Copy text to the macOS clipboard."""
    try:
        process = subprocess.Popen(
            ["pbcopy"], stdin=subprocess.PIPE,
        )
        process.communicate(input=text.encode("utf-8"))
        return process.returncode == 0
    except Exception as e:
        logger.error("clipboard_copy failed: %s", e)
        return False


def clipboard_paste() -> Optional[str]:
    """Get current clipboard contents."""
    try:
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5,
        )
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        logger.error("clipboard_paste failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def take_screenshot(save_path: Optional[str] = None, region: bool = False) -> Optional[str]:
    """Take a screenshot. Returns the file path."""
    try:
        if not save_path:
            from datetime import datetime
            desktop = os.path.expanduser("~/Desktop")
            ts = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
            save_path = os.path.join(desktop, f"Screenshot_{ts}.png")

        cmd = ["screencapture"]
        if region:
            cmd.append("-i")  # Interactive selection
        cmd.append(save_path)

        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        if os.path.exists(save_path):
            return save_path
        return None
    except Exception as e:
        logger.error("take_screenshot failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# System appearance
# ---------------------------------------------------------------------------

def toggle_dark_mode() -> str:
    """Toggle between dark and light mode. Returns the new mode."""
    try:
        script = '''
        tell application "System Events"
            tell appearance preferences
                set dark mode to not dark mode
                return dark mode as text
            end tell
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        mode = result.stdout.strip()
        return "dark" if mode == "true" else "light"
    except Exception as e:
        logger.error("toggle_dark_mode failed: %s", e)
        return "unknown"


def get_dark_mode() -> bool:
    """Check if dark mode is currently enabled."""
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() == "Dark"
    except (subprocess.SubprocessError, OSError):
        # `defaults read` returns non-zero when AppleInterfaceStyle key
        # doesn't exist, which means the system is in Light mode.
        # This is expected behavior, not an error.
        return False


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------

def set_volume(level: int) -> bool:
    """Set system volume (0-100)."""
    level = max(0, min(100, level))
    try:
        # macOS volume is 0-7 in osascript, map 0-100 → 0-100 output volume
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except Exception as e:
        logger.error("set_volume failed: %s", e)
        return False


def get_volume() -> Optional[int]:
    """Get current system volume (0-100)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, timeout=5,
        )
        return int(result.stdout.strip())
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.debug("Could not read system volume: %s", e)
        return None


def toggle_mute() -> bool:
    """Toggle mute/unmute."""
    try:
        # Check current mute state
        result = subprocess.run(
            ["osascript", "-e", "output muted of (get volume settings)"],
            capture_output=True, text=True, timeout=5,
        )
        is_muted = result.stdout.strip() == "true"
        new_state = "false" if is_muted else "true"
        subprocess.run(
            ["osascript", "-e", f"set volume output muted {new_state}"],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except Exception as e:
        logger.error("toggle_mute failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------

def get_disk_space() -> Dict[str, Any]:
    """Get disk usage for the main volume."""
    try:
        result = subprocess.run(
            ["df", "-H", "/"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            return {
                "filesystem": parts[0],
                "total": parts[1],
                "used": parts[2],
                "available": parts[3],
                "percent_used": parts[4],
            }
        return {}
    except Exception as e:
        logger.error("get_disk_space failed: %s", e)
        return {}


def get_battery_info() -> Dict[str, Any]:
    """Get battery status."""
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout
        info: Dict[str, Any] = {}

        # Parse percentage
        import re
        pct_match = re.search(r"(\d+)%", output)
        if pct_match:
            info["percentage"] = int(pct_match.group(1))

        # Parse charging status
        if "AC Power" in output:
            info["power_source"] = "AC Power"
        elif "Battery Power" in output:
            info["power_source"] = "Battery"
        else:
            info["power_source"] = "Unknown"

        if "charging" in output.lower():
            info["charging"] = True
        elif "discharging" in output.lower():
            info["charging"] = False
        elif "charged" in output.lower():
            info["charging"] = False
            info["fully_charged"] = True

        # Parse time remaining
        time_match = re.search(r"(\d+:\d+) remaining", output)
        if time_match:
            info["time_remaining"] = time_match.group(1)

        return info
    except Exception as e:
        logger.error("get_battery_info failed: %s", e)
        return {}


def get_wifi_info() -> Dict[str, Any]:
    """Get current WiFi information."""
    try:
        # macOS 15+ uses the new airport path, fallback to old
        airport_paths = [
            "/usr/sbin/networksetup",
        ]
        # Use networksetup for reliable info
        result = subprocess.run(
            ["networksetup", "-getairportnetwork", "en0"],
            capture_output=True, text=True, timeout=5,
        )
        info: Dict[str, Any] = {}
        if "Current Wi-Fi Network" in result.stdout:
            info["network"] = result.stdout.split(": ", 1)[1].strip()
            info["connected"] = True
        elif "You are not associated with an AirPort network" in result.stdout:
            info["connected"] = False
            info["network"] = None
        else:
            info["connected"] = False
            info["network"] = None

        return info
    except Exception as e:
        logger.error("get_wifi_info failed: %s", e)
        return {}


# ---------------------------------------------------------------------------
# System actions
# ---------------------------------------------------------------------------

def lock_screen() -> bool:
    """Lock the screen."""
    try:
        subprocess.Popen([
            "osascript", "-e",
            'tell application "System Events" to keystroke "q" using {command down, control down}'
        ])
        return True
    except Exception as e:
        logger.error("lock_screen failed: %s", e)
        return False


def text_to_speech(text: str, voice: Optional[str] = None) -> bool:
    """Speak text aloud using macOS 'say' command."""
    try:
        cmd = ["say"]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)
        subprocess.Popen(cmd)
        return True
    except Exception as e:
        logger.error("text_to_speech failed: %s", e)
        return False


def kill_process(name: str) -> bool:
    """Kill a process by name."""
    try:
        subprocess.run(
            ["pkill", "-f", name],
            capture_output=True, timeout=5,
        )
        return True
    except Exception as e:
        logger.error("kill_process failed: %s", e)
        return False


def eject_volume(volume_name: str) -> bool:
    """Eject a mounted volume."""
    try:
        # Try diskutil first
        result = subprocess.run(
            ["diskutil", "eject", volume_name],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True
        # Fallback to osascript
        subprocess.run(
            ["osascript", "-e",
             f'tell application "Finder" to eject disk "{_escape(volume_name)}"'],
            check=True, capture_output=True, timeout=10,
        )
        return True
    except Exception as e:
        logger.error("eject_volume failed: %s", e)
        return False


def create_symlink(source: str, link_path: str) -> bool:
    """Create a symbolic link."""
    source = os.path.expanduser(source)
    link_path = os.path.expanduser(link_path)
    try:
        os.symlink(source, link_path)
        return True
    except Exception as e:
        logger.error("create_symlink failed: %s", e)
        return False


def set_wallpaper(image_path: str) -> bool:
    """Set the desktop wallpaper."""
    image_path = os.path.expanduser(image_path)
    if not os.path.exists(image_path):
        return False
    try:
        script = f'''
        tell application "System Events"
            tell every desktop
                set picture to "{image_path}"
            end tell
        end tell
        '''
        subprocess.run(
            ["osascript", "-e", script],
            check=True, capture_output=True, timeout=10,
        )
        return True
    except Exception as e:
        logger.error("set_wallpaper failed: %s", e)
        return False


def toggle_hidden_files() -> str:
    """Toggle showing/hiding hidden files in Finder. Returns new state."""
    try:
        result = subprocess.run(
            ["defaults", "read", "com.apple.finder", "AppleShowAllFiles"],
            capture_output=True, text=True, timeout=5,
        )
        currently_showing = result.stdout.strip().upper() in ("YES", "TRUE", "1")
        new_value = "NO" if currently_showing else "YES"
        subprocess.run(
            ["defaults", "write", "com.apple.finder", "AppleShowAllFiles", new_value],
            check=True, capture_output=True, timeout=5,
        )
        subprocess.run(["killall", "Finder"], capture_output=True, timeout=5)
        return "visible" if new_value == "YES" else "hidden"
    except Exception as e:
        logger.error("toggle_hidden_files failed: %s", e)
        return "unknown"


def get_running_apps() -> list[str]:
    """Get a list of currently running applications."""
    try:
        script = '''
        tell application "System Events"
            set appNames to name of every application process whose background only is false
            set output to ""
            repeat with appName in appNames
                set output to output & appName & linefeed
            end repeat
            return output
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        apps = [a.strip() for a in result.stdout.strip().split("\n") if a.strip()]
        return sorted(apps)
    except Exception as e:
        logger.error("get_running_apps failed: %s", e)
        return []


def get_folder_size(path: str) -> Optional[str]:
    """Get human-readable folder size."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return None
    try:
        result = subprocess.run(
            ["du", "-sh", path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.split("\t")[0].strip()
        return None
    except Exception as e:
        logger.error("get_folder_size failed: %s", e)
        return None


def empty_trash_system() -> bool:
    """Empty the Trash using Finder AppleScript."""
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "Finder" to empty trash'],
            check=True, capture_output=True, timeout=30,
        )
        return True
    except Exception as e:
        logger.error("empty_trash_system failed: %s", e)
        return False


def get_file_info_detailed(path: str) -> Dict[str, Any]:
    """Get detailed file information including Spotlight metadata."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return {"error": "File not found"}

    p = Path(path)
    stat = p.stat()
    from datetime import datetime

    info: Dict[str, Any] = {
        "name": p.name,
        "path": str(p),
        "size": _human_size(stat.st_size),
        "size_bytes": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "is_directory": p.is_dir(),
        "is_symlink": p.is_symlink(),
        "extension": p.suffix,
    }

    if p.is_dir():
        # Count contents
        try:
            contents = list(p.iterdir())
            info["item_count"] = len(contents)
            info["folder_size"] = get_folder_size(str(p))
        except PermissionError:
            info["item_count"] = "Permission denied"
    else:
        # Get Spotlight metadata for files
        try:
            from sortmeout.macos.spotlight import get_metadata
            md = get_metadata(str(p))
            if md:
                for key in ["kMDItemKind", "kMDItemContentType",
                             "kMDItemPixelWidth", "kMDItemPixelHeight",
                             "kMDItemDurationSeconds", "kMDItemAuthors",
                             "kMDItemTitle", "kMDItemWhereFroms",
                             "kMDItemPageCount"]:
                    if key in md and md[key] is not None:
                        clean_key = key.replace("kMDItem", "")
                        info[clean_key] = md[key]
        except Exception as e:
            # Spotlight metadata is optional enrichment — don't fail the whole info request
            logger.debug("Could not read Spotlight metadata for %s: %s", p, e)

    # Get Finder tags
    try:
        from sortmeout.macos.tags import get_tags
        tags = get_tags(str(p))
        if tags:
            info["tags"] = tags
    except Exception as e:
        logger.debug("Could not read Finder tags for %s: %s", p, e)

    return info


def search_files(query: str, folder: Optional[str] = None, limit: int = 20) -> list[Dict[str, str]]:
    """Search for files using Spotlight (mdfind). Returns list of results."""
    try:
        cmd = ["mdfind"]
        if folder:
            folder = os.path.expanduser(folder)
            cmd.extend(["-onlyin", folder])
        cmd.append(query)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
        )

        paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        results = []
        for p in paths[:limit]:
            path_obj = Path(p)
            results.append({
                "name": path_obj.name,
                "path": str(path_obj),
                "is_dir": path_obj.is_dir(),
            })
        return results
    except Exception as e:
        logger.error("search_files failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape(s: str) -> str:
    """Escape string for AppleScript."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def _human_size(size: int) -> str:
    """Convert bytes to human readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
