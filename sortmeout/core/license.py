"""
SortMeOut License Authority.

Central licensing system for SortMeOut.
Handles trial tracking, license validation, and feature gating.

This is the SINGLE SOURCE OF TRUTH for all license-related logic.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
import hashlib


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
    
    TRIAL_DURATION_DAYS = 14
    LICENSE_FILE = "license.json"
    
    _instance: Optional['LicenseAuthority'] = None
    
    def __new__(cls) -> 'LicenseAuthority':
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
        self._state: LicenseState = LicenseState.TRIAL_EXPIRED
        self._trial_start: Optional[datetime] = None
        self._pro_license_key: Optional[str] = None
        
        self._ensure_license_dir()
        self._load_or_initialize()
    
    def _ensure_license_dir(self):
        """Ensure license directory exists."""
        self._license_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_or_initialize(self):
        """Load existing license or initialize trial on first launch."""
        if self._license_file.exists():
            self._load_license()
        else:
            # FIRST LAUNCH - Start trial
            self._initialize_trial()
    
    def _initialize_trial(self):
        """Initialize trial on first application launch."""
        self._trial_start = datetime.now()
        self._state = LicenseState.TRIAL_ACTIVE
        self._save_license()
    
    def _load_license(self):
        """Load license state from file."""
        try:
            with open(self._license_file, 'r') as f:
                data = json.load(f)
            
            # Load trial start
            trial_start_str = data.get('trial_start')
            if trial_start_str:
                self._trial_start = datetime.fromisoformat(trial_start_str)
            
            # Load pro license key
            self._pro_license_key = data.get('pro_license_key')
            
            # Determine current state
            self._evaluate_state()
            
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file - treat as expired (not a new trial)
            self._state = LicenseState.TRIAL_EXPIRED
    
    def _save_license(self):
        """Save license state to file."""
        data = {
            'trial_start': self._trial_start.isoformat() if self._trial_start else None,
            'pro_license_key': self._pro_license_key,
            'last_check': datetime.now().isoformat(),
        }
        
        with open(self._license_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _evaluate_state(self):
        """Evaluate and set the current license state."""
        # Check for Pro license first
        if self._pro_license_key and self._validate_pro_key(self._pro_license_key):
            self._state = LicenseState.PRO_ACTIVE
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
        Validate a Pro license key.
        
        Simple offline validation. No server required.
        """
        if not key or len(key) < 20:
            return False
        
        # Basic checksum validation
        # Format: SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM
        parts = key.split('-')
        if len(parts) != 5 or parts[0] != 'SORTMEOUT':
            return False
        
        # Validate checksum
        payload = '-'.join(parts[:4])
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
        Activate Pro license.
        
        Args:
            license_key: The Pro license key.
            
        Returns:
            True if activation successful, False otherwise.
        """
        if self._validate_pro_key(license_key):
            self._pro_license_key = license_key
            self._state = LicenseState.PRO_ACTIVE
            self._save_license()
            return True
        return False
    
    def deactivate_pro(self):
        """Deactivate Pro license (e.g., for license transfer)."""
        self._pro_license_key = None
        self._evaluate_state()
        self._save_license()
    
    # ========================================
    # FEATURE GATES (THE ONLY GATES)
    # ========================================
    
    def can_execute_ai(self) -> bool:
        """
        Check if AI execution is allowed.
        
        AI is the PRIMARY value of SortMeOut.
        When license is not active, AI is COMPLETELY disabled.
        """
        return self.is_active
    
    def can_execute_automation(self) -> bool:
        """
        Check if automation execution is allowed.
        
        When license is not active, automation is COMPLETELY disabled.
        """
        return self.is_active
    
    def can_read_file_contents(self) -> bool:
        """
        Check if reading file contents is allowed.
        
        When license is not active, file content reading is COMPLETELY disabled.
        """
        return self.is_active
    
    def can_watch_filesystem(self) -> bool:
        """
        Check if filesystem watching is allowed.
        
        When license is not active, filesystem watching is COMPLETELY disabled.
        """
        return self.is_active
    
    # ========================================
    # SHELL MODE MESSAGE
    # ========================================
    
    @staticmethod
    def get_expired_message() -> str:
        """
        Get the standard message for expired trial.
        
        This is the ONLY message to show. No variations.
        """
        return (
            "Your trial has ended.\n"
            "SortMeOut's AI assistant and automation features "
            "require an active Pro license."
        )
    
    def get_status_message(self) -> str:
        """Get current license status message."""
        state = self.state
        
        if state == LicenseState.PRO_ACTIVE:
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


def can_execute_ai() -> bool:
    """Check if AI execution is allowed."""
    return get_license().can_execute_ai()


def can_execute_automation() -> bool:
    """Check if automation execution is allowed."""
    return get_license().can_execute_automation()


def can_read_file_contents() -> bool:
    """Check if reading file contents is allowed."""
    return get_license().can_read_file_contents()


def can_watch_filesystem() -> bool:
    """Check if filesystem watching is allowed."""
    return get_license().can_watch_filesystem()
