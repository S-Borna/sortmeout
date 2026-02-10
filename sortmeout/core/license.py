"""
SortMeOut License Authority.

Central licensing system for SortMeOut.
Handles trial tracking, license validation, and feature gating.

This is the SINGLE SOURCE OF TRUTH for all license-related logic.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta, date
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
import hashlib

logger = logging.getLogger(__name__)


# ========================================
# AI EXECUTION GATE CONSTANTS
# ========================================

# Rate limits per license tier
TRIAL_AI_DAILY_LIMIT = 5  # Trial: 5/day
PRO_AI_DAILY_LIMIT = 30  # Pro: 30/day

# Image generation limits per license tier
TRIAL_IMAGE_DAILY_LIMIT = 3  # Trial: 3 images/day
PRO_IMAGE_DAILY_LIMIT = 3  # Pro: 3 images/day

# ========================================
# PRICING
# ========================================
PRO_PRICE_USD = 9.99  # Monthly subscription price

# The ONLY error message for blocked AI. No variations.
AI_BLOCKED_MESSAGE = "AI Assistant requires an active Pro license."

# License verification API
LICENSE_API_URL = "https://api.sortmeout.saidborna.com"


class LicenseState(Enum):
    """License states. ONLY these three states exist."""

    TRIAL_ACTIVE = "trial_active"
    TRIAL_EXPIRED = "trial_expired"
    PRO_ACTIVE = "pro_active"


class LicenseAuthority:
    """
    Central license authority for SortMeOut.

    This is the ONLY class that manages license state.
    All feature gates MUST go through this class.
    """

    TRIAL_DURATION_DAYS = 7
    LICENSE_FILE = "license.json"

    _instance: Optional["LicenseAuthority"] = None

    def __new__(cls) -> "LicenseAuthority":
        """Singleton pattern - only one license authority exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._license_dir = Path(os.path.expanduser("~/.config/sortmeout"))
        self._license_file = self._license_dir / self.LICENSE_FILE
        self._fingerprint_file = self._license_dir / ".fingerprint"  # Hidden file
        self._state: LicenseState = LicenseState.TRIAL_EXPIRED
        self._trial_start: Optional[datetime] = None
        self._pro_license_key: Optional[str] = None
        self._trial_consumed: bool = False  # True if trial was used and Pro was later deactivated
        self._machine_id: Optional[str] = None  # Hardware fingerprint

        # Rate limit tracking
        self._ai_usage_date: Optional[str] = None  # ISO date string
        self._ai_usage_count: int = 0
        self._image_usage_date: Optional[str] = None
        self._image_usage_count: int = 0

        self._ensure_license_dir()
        self._machine_id = self._get_machine_fingerprint()
        self._load_or_initialize()

    def _ensure_license_dir(self):
        """Ensure license directory exists."""
        self._license_dir.mkdir(parents=True, exist_ok=True)

    def _get_machine_fingerprint(self) -> str:
        """
        Generate a unique machine fingerprint.

        Uses macOS hardware UUID which persists across:
        - Config folder deletion
        - App reinstall
        - macOS updates

        Only changes if user gets new hardware.
        """
        try:
            # Get macOS Hardware UUID (unique per machine)
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        # Extract UUID from line like: "IOPlatformUUID" = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
                        uuid = line.split('"')[-2]
                        # Hash it for privacy
                        return hashlib.sha256(uuid.encode()).hexdigest()[:32]
        except Exception as e:
            # Fingerprint failure is non-fatal — fallback below.
            # Logged at debug because ioreg may legitimately fail in sandboxed envs.
            logger.debug("Hardware UUID retrieval failed, using fallback: %s", e)

        # Fallback: use hostname + username hash
        fallback = f"{os.uname().nodename}-{os.getenv('USER', 'unknown')}"
        return hashlib.sha256(fallback.encode()).hexdigest()[:32]

    def _check_fingerprint_fraud(self) -> bool:
        """
        Check if this machine has already used a trial.

        Returns True if fraud detected (trial already used on this machine).
        """
        if not self._fingerprint_file.exists():
            return False

        try:
            with open(self._fingerprint_file, "r") as f:
                data = json.load(f)

            stored_id = data.get("machine_id")
            trial_used = data.get("trial_used", False)

            # If same machine and trial was used, it's fraud attempt
            if stored_id == self._machine_id and trial_used:
                return True
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Corrupt fingerprint file, resetting fraud detection: %s", e)
        except OSError as e:
            logger.warning("Cannot read fingerprint file %s: %s", self._fingerprint_file, e)

        return False

    def _mark_trial_used(self):
        """Mark that this machine has used its trial."""
        data = {
            "machine_id": self._machine_id,
            "trial_used": True,
            "first_trial": datetime.now().isoformat(),
        }
        try:
            with open(self._fingerprint_file, "w") as f:
                json.dump(data, f)
        except OSError as e:
            # Critical: if we can't mark trial as used, users could get infinite trials.
            # Log at error level so this surfaces in diagnostics.
            logger.error(
                "Failed to write trial fingerprint to %s: %s. "
                "Fraud prevention may be compromised.",
                self._fingerprint_file, e
            )

    def _load_or_initialize(self):
        """Load existing license or initialize trial on first launch."""
        if self._license_file.exists():
            self._load_license()
        else:
            # FIRST LAUNCH - Start trial
            self._initialize_trial()

    def _initialize_trial(self):
        """
        Initialize trial on first application launch.

        Fraud protection: Checks machine fingerprint to prevent
        users from deleting config to get infinite trials.
        """
        # Check for fraud (config deleted but same machine)
        if self._check_fingerprint_fraud():
            # This machine already had a trial - no new trial
            self._state = LicenseState.TRIAL_EXPIRED
            self._trial_consumed = True
            self._save_license()
            return

        # Legitimate first launch
        self._trial_start = datetime.now()
        self._state = LicenseState.TRIAL_ACTIVE
        self._mark_trial_used()  # Record fingerprint
        self._save_license()

    def _load_license(self):
        """Load license state from file."""
        try:
            with open(self._license_file, "r") as f:
                data = json.load(f)

            # Load trial start
            trial_start_str = data.get("trial_start")
            if trial_start_str:
                self._trial_start = datetime.fromisoformat(trial_start_str)

            # Load pro license key
            self._pro_license_key = data.get("pro_license_key")

            # Load trial consumed flag
            self._trial_consumed = data.get("trial_consumed", False)

            # Load rate limit tracking
            self._ai_usage_date = data.get("ai_usage_date")
            self._ai_usage_count = data.get("ai_usage_count", 0)
            self._image_usage_date = data.get("image_usage_date")
            self._image_usage_count = data.get("image_usage_count", 0)

            # Determine current state
            self._evaluate_state()

        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file - treat as expired (not a new trial)
            self._state = LicenseState.TRIAL_EXPIRED

    def _save_license(self):
        """Save license state to file."""
        data = {
            "trial_start": self._trial_start.isoformat() if self._trial_start else None,
            "pro_license_key": self._pro_license_key,
            "trial_consumed": self._trial_consumed,
            "last_check": datetime.now().isoformat(),
            "ai_usage_date": self._ai_usage_date,
            "ai_usage_count": self._ai_usage_count,
            "image_usage_date": self._image_usage_date,
            "image_usage_count": self._image_usage_count,
        }

        with open(self._license_file, "w") as f:
            json.dump(data, f, indent=2)

    def _evaluate_state(self):
        """Evaluate and set the current license state."""
        # Check for Pro license first (any non-empty key = Pro active)
        # This supports both legacy format keys AND opaque payloads
        if self._pro_license_key and self._pro_license_key.strip():
            self._state = LicenseState.PRO_ACTIVE
            return

        # If trial was consumed (Pro was activated then deactivated), force expired
        if self._trial_consumed:
            self._state = LicenseState.TRIAL_EXPIRED
            return

        # Check trial status
        if self._trial_start is None:
            self._state = LicenseState.TRIAL_EXPIRED
            return

        trial_end = self._trial_start + timedelta(days=self.TRIAL_DURATION_DAYS)

        if datetime.now() < trial_end:
            self._state = LicenseState.TRIAL_ACTIVE
        else:
            self._state = LicenseState.TRIAL_EXPIRED

    def _validate_pro_key(self, key: str) -> bool:
        """
        Validate a Pro license key (legacy format).

        Simple offline validation. No server required.
        """
        if not key or len(key) < 20:
            return False

        # Basic checksum validation
        # Format: SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM
        parts = key.split("-")
        if len(parts) != 5 or parts[0] != "SORTMEOUT":
            return False

        # Validate checksum
        payload = "-".join(parts[:4])
        expected_checksum = hashlib.sha256(payload.encode()).hexdigest()[:8].upper()

        return parts[4] == expected_checksum

    # ========================================
    # PUBLIC API
    # ========================================

    @property
    def state(self) -> LicenseState:
        """Get current license state."""
        self._evaluate_state()
        return self._state

    @property
    def is_active(self) -> bool:
        """Check if license allows full functionality."""
        return self.state in (LicenseState.TRIAL_ACTIVE, LicenseState.PRO_ACTIVE)

    @property
    def trial_days_remaining(self) -> int:
        """Get remaining trial days. Returns 0 if expired or Pro."""
        if self._trial_start is None:
            return 0

        if self.state == LicenseState.PRO_ACTIVE:
            return 0

        trial_end = self._trial_start + timedelta(days=self.TRIAL_DURATION_DAYS)
        remaining = (trial_end - datetime.now()).days
        return max(0, remaining)

    def activate_pro(self, license_key: str) -> bool:
        """
        Activate Pro license with validated key format.

        Args:
            license_key: The Pro license key (SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM format).

        Returns:
            True if activation successful, False otherwise.
        """
        if self._validate_pro_key(license_key):
            self._pro_license_key = license_key
            self._state = LicenseState.PRO_ACTIVE
            self._save_license()
            return True
        return False

    def activate_pro_license(self, payload: str) -> bool:
        """
        Activate Pro license with a SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM key.

        This is the PAYMENT HOOK for Stripe.
        After successful payment, user receives a license key and enters it here.

        Validates:
        1. Key format (SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM)
        2. Checksum integrity
        3. Optional: server-side verification if network available

        Args:
            payload: License key from Stripe checkout.

        Returns:
            True if activation successful, False otherwise.
        """
        if not payload or not payload.strip():
            return False

        key = payload.strip().upper()

        # Validate key format and checksum
        if not self._validate_pro_key(key):
            return False

        # Store the key and activate
        self._pro_license_key = key
        self._state = LicenseState.PRO_ACTIVE
        self._save_license()

        # Attempt server verification in background (non-blocking)
        # If server is unreachable, key still works offline via checksum
        self._verify_with_server_async(key)

        return True

    def deactivate_pro(self):
        """Deactivate Pro license (e.g., for license transfer)."""
        self._pro_license_key = None
        self._evaluate_state()
        self._save_license()

    def deactivate_pro_license(self) -> None:
        """
        Deactivate Pro license immediately.

        This is the PAYMENT HOOK for subscription cancellation.

        Effects (IMMEDIATE, no grace period):
        - State becomes TRIAL_EXPIRED (not TRIAL_ACTIVE)
        - AI execution = OFF
        - Automation continues (freemium)
        - Filesystem watching continues (freemium)

        Trial expiration is FINAL. This does NOT restart trial.
        """
        self._pro_license_key = None
        # Mark trial as consumed - prevents returning to TRIAL_ACTIVE
        self._trial_consumed = True
        # Force TRIAL_EXPIRED, not TRIAL_ACTIVE (trial is consumed)
        self._state = LicenseState.TRIAL_EXPIRED
        self._save_license()

    def _verify_with_server_async(self, license_key: str) -> None:
        """
        Verify license key with server in background thread.
        Non-blocking — if server is unreachable, offline validation stands.
        """
        import threading

        def _verify():
            try:
                self.verify_license_online(license_key)
            except Exception as e:
                # Offline is acceptable — local checksum validation is sufficient.
                # Logged at debug because network unavailability is a normal condition.
                logger.debug("Background license verification skipped (offline): %s", e)

        thread = threading.Thread(target=_verify, daemon=True)
        thread.start()

    def verify_license_online(self, license_key: str) -> Optional[dict]:
        """
        Verify license key against the server.

        Makes a POST to the license API to check if the key is valid
        and the subscription is active.

        Args:
            license_key: The SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM key.

        Returns:
            Server response dict if successful, None if unreachable.
            Response contains: {valid: bool, status: str, email: str}
        """
        import urllib.request
        import urllib.error

        try:
            data = json.dumps({"license_key": license_key}).encode("utf-8")
            req = urllib.request.Request(
                f"{LICENSE_API_URL}/api/verify",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            if result.get("valid") is False and result.get("status") == "cancelled":
                # Subscription was cancelled — deactivate locally
                self.deactivate_pro_license()

            return result

        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            # Server unreachable — offline mode, keep current state
            logger.debug("License server unreachable: %s", e)
            return None
        except (json.JSONDecodeError, KeyError) as e:
            # Server returned unexpected data
            logger.warning("License server returned invalid response: %s", e)
            return None

    # ========================================
    # FEATURE GATES (THE ONLY GATES)
    # ========================================

    def can_execute_ai(self) -> Tuple[bool, str]:
        """
        SINGLE AI GATE - ALL AI execution MUST pass through this function.

        Returns:
            Tuple of (allowed: bool, message: str)
            - If allowed: (True, "")
            - If blocked: (False, AI_BLOCKED_MESSAGE)

        Rules:
        - TRIAL_ACTIVE: allowed if under daily limit (5/day, matches website/terms)
        - PRO_ACTIVE: allowed if under daily limit (30/day)
        - TRIAL_EXPIRED: never allowed
        - CREATOR: unlimited

        This function does NOT:
        - Send prompts
        - Generate tokens
        - Queue execution
        - Retry
        - Cache
        """
        state = self.state

        # Check for Creator (unlimited)
        if self._pro_license_key and "CREATOR" in self._pro_license_key:
            return (True, "")

        # PRO_ACTIVE: allowed if under daily limit
        if state == LicenseState.PRO_ACTIVE:
            if self._check_rate_limit(PRO_AI_DAILY_LIMIT):
                return (True, "")
            else:
                return (False, "Daily AI limit reached (30/day). Resets at midnight.")

        # TRIAL_ACTIVE: allowed if under daily limit
        if state == LicenseState.TRIAL_ACTIVE:
            if self._check_rate_limit(TRIAL_AI_DAILY_LIMIT):
                return (True, "")
            else:
                remaining = TRIAL_AI_DAILY_LIMIT
                return (
                    False,
                    f"Daily AI limit reached ({remaining}/day). Upgrade to Pro for {PRO_AI_DAILY_LIMIT}/day!",
                )

        # TRIAL_EXPIRED or any other state: blocked
        return (False, AI_BLOCKED_MESSAGE)

    def _check_rate_limit(self, limit: int) -> bool:
        """
        Check if user is under daily AI limit.
        Resets counter if date has changed.

        Args:
            limit: Daily limit to check against

        Returns:
            True if under limit, False if limit reached.
        """
        today = date.today().isoformat()

        # Reset counter if new day
        if self._ai_usage_date != today:
            self._ai_usage_date = today
            self._ai_usage_count = 0
            self._save_license()

        return self._ai_usage_count < limit

    def record_ai_execution(self) -> None:
        """
        Record an AI execution for rate limiting.
        Call this AFTER successful AI execution.
        """
        # Creator has no limit, but still track for stats
        today = date.today().isoformat()

        if self._ai_usage_date != today:
            self._ai_usage_date = today
            self._ai_usage_count = 0

        self._ai_usage_count += 1
        self._save_license()

    def get_ai_remaining(self) -> int:
        """
        Get remaining AI executions for today.
        """
        # Creator = unlimited
        if self._pro_license_key and "CREATOR" in self._pro_license_key:
            return 999

        today = date.today().isoformat()
        if self._ai_usage_date != today:
            # New day, return full limit
            if self.state == LicenseState.PRO_ACTIVE:
                return PRO_AI_DAILY_LIMIT
            elif self.state == LicenseState.TRIAL_ACTIVE:
                return TRIAL_AI_DAILY_LIMIT
            return 0

        # Return remaining based on tier
        if self.state == LicenseState.PRO_ACTIVE:
            return max(0, PRO_AI_DAILY_LIMIT - self._ai_usage_count)
        elif self.state == LicenseState.TRIAL_ACTIVE:
            return max(0, TRIAL_AI_DAILY_LIMIT - self._ai_usage_count)
        return 0

    def can_generate_image(self) -> Tuple[bool, str]:
        """
        IMAGE GENERATION GATE - ALL DALL-E calls MUST pass through this.

        Returns:
            Tuple of (allowed: bool, message: str)

        Rules:
        - TRIAL_ACTIVE: 5 images/day
        - PRO_ACTIVE: 10 images/day
        - TRIAL_EXPIRED: never allowed
        - CREATOR: unlimited
        """
        state = self.state

        # Creator = unlimited
        if self._pro_license_key and "CREATOR" in self._pro_license_key:
            return (True, "")

        if state == LicenseState.PRO_ACTIVE:
            if self._check_image_rate_limit(PRO_IMAGE_DAILY_LIMIT):
                return (True, "")
            return (
                False,
                f"Daily image limit reached ({PRO_IMAGE_DAILY_LIMIT}/day). Resets at midnight.",
            )

        if state == LicenseState.TRIAL_ACTIVE:
            if self._check_image_rate_limit(TRIAL_IMAGE_DAILY_LIMIT):
                return (True, "")
            return (
                False,
                f"Daily image limit reached ({TRIAL_IMAGE_DAILY_LIMIT}/day). Upgrade to Pro for {PRO_IMAGE_DAILY_LIMIT}/day!",
            )

        return (False, AI_BLOCKED_MESSAGE)

    def _check_image_rate_limit(self, limit: int) -> bool:
        """Check if user is under daily image generation limit."""
        today = date.today().isoformat()

        if self._image_usage_date != today:
            self._image_usage_date = today
            self._image_usage_count = 0
            self._save_license()

        return self._image_usage_count < limit

    def record_image_generation(self) -> None:
        """Record an image generation for rate limiting."""
        today = date.today().isoformat()

        if self._image_usage_date != today:
            self._image_usage_date = today
            self._image_usage_count = 0

        self._image_usage_count += 1
        self._save_license()

    def get_images_remaining(self) -> int:
        """Get remaining image generations for today."""
        if self._pro_license_key and "CREATOR" in self._pro_license_key:
            return 999

        today = date.today().isoformat()
        if self._image_usage_date != today:
            if self.state == LicenseState.PRO_ACTIVE:
                return PRO_IMAGE_DAILY_LIMIT
            elif self.state == LicenseState.TRIAL_ACTIVE:
                return TRIAL_IMAGE_DAILY_LIMIT
            return 0

        if self.state == LicenseState.PRO_ACTIVE:
            return max(0, PRO_IMAGE_DAILY_LIMIT - self._image_usage_count)
        elif self.state == LicenseState.TRIAL_ACTIVE:
            return max(0, TRIAL_IMAGE_DAILY_LIMIT - self._image_usage_count)
        return 0

    def can_execute_automation(self) -> bool:
        """
        Check if automation execution is allowed.

        FREEMIUM MODEL: Automation is ALWAYS allowed.
        This keeps users engaged even after trial expires.
        Revenue comes from AI features (Pro).
        """
        return True  # Always allowed - freemium

    def can_read_file_contents(self) -> bool:
        """
        Check if reading file contents is allowed.

        FREEMIUM MODEL: Basic file operations always allowed.
        """
        return True  # Always allowed - freemium

    def can_watch_filesystem(self) -> bool:
        """
        Check if filesystem watching is allowed.

        FREEMIUM MODEL: Watching is always allowed.
        """
        return True  # Always allowed - freemium

    # ========================================
    # SHELL MODE MESSAGE
    # ========================================

    @staticmethod
    def get_expired_message() -> str:
        """
        Get the standard message for expired trial.

        This is the ONLY message to show. No variations.
        """
        return AI_BLOCKED_MESSAGE

    def get_status_message(self) -> str:
        """Get current license status message."""
        state = self.state

        if state == LicenseState.PRO_ACTIVE:
            # Check for creator license
            if self._pro_license_key and "CREATOR" in self._pro_license_key.upper():
                return "✨ Creator License"
            return "Pro License Active"
        elif state == LicenseState.TRIAL_ACTIVE:
            days = self.trial_days_remaining
            return f"Trial: {days} day{'s' if days != 1 else ''} remaining"
        else:
            return "Trial Expired"


# ========================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ========================================


def get_license() -> LicenseAuthority:
    """Get the singleton license authority instance."""
    return LicenseAuthority()


def can_execute_ai() -> Tuple[bool, str]:
    """
    SINGLE AI GATE - Check if AI execution is allowed.

    Returns:
        Tuple of (allowed: bool, message: str)
        - If allowed: (True, "")
        - If blocked: (False, AI_BLOCKED_MESSAGE)
    """
    return get_license().can_execute_ai()


def record_ai_execution() -> None:
    """Record an AI execution for rate limiting (trial only)."""
    get_license().record_ai_execution()


def get_ai_blocked_message() -> str:
    """Get the standard AI blocked message."""
    return AI_BLOCKED_MESSAGE


def can_generate_image() -> Tuple[bool, str]:
    """Check if image generation is allowed."""
    return get_license().can_generate_image()


def record_image_generation() -> None:
    """Record an image generation for rate limiting."""
    get_license().record_image_generation()


def can_execute_automation() -> bool:
    """Check if automation execution is allowed."""
    return get_license().can_execute_automation()


def can_read_file_contents() -> bool:
    """Check if reading file contents is allowed."""
    return get_license().can_read_file_contents()


def can_watch_filesystem() -> bool:
    """Check if filesystem watching is allowed."""
    return get_license().can_watch_filesystem()


# ========================================
# PAYMENT HOOK CONVENIENCE FUNCTIONS
# ========================================


def activate_pro_license(payload: str) -> bool:
    """
    Activate Pro license with opaque payload.

    This is the PRIMARY PAYMENT HOOK.
    Payment providers (Stripe, Paddle, etc.) call this after successful payment.

    Args:
        payload: Opaque activation payload from payment provider.

    Returns:
        True if activation successful, False otherwise.
    """
    return get_license().activate_pro_license(payload)


def deactivate_pro_license() -> None:
    """
    Deactivate Pro license immediately.

    This is the CANCELLATION HOOK.
    Payment providers call this on subscription cancellation.

    Effects are IMMEDIATE:
    - AI = OFF
    - Automation = OFF
    - App enters SHELL MODE
    """
    get_license().deactivate_pro_license()


def is_pro_active() -> bool:
    """Check if Pro license is currently active."""
    return get_license().state == LicenseState.PRO_ACTIVE
