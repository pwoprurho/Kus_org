# utils.py
"""Utility functions for the Kusmus Data Generator."""

import uuid
from datetime import datetime, timezone

def generate_case_id(prefix="CASE"):
    """Generates a unique-ish case ID."""
    # Ensure prefix is clean if coming from scenario ID
    clean_prefix = "".join(filter(str.isalnum, prefix))[:4].upper()
    return f"{clean_prefix}-{uuid.uuid4().hex[:8].upper()}"

def now_iso():
    """Returns the current timestamp in ISO 8601 format (UTC)."""
    # Use timezone.utc for explicit UTC timestamp
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
