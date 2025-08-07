"""Configuration for Medication Tracker tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the custom components directory to the Python path
custom_components_path = (
    Path(__file__).parent.parent.parent.parent / "config" / "custom_components"
)
sys.path.insert(0, str(custom_components_path))
