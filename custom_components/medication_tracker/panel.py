"""Custom panel for Medication Tracker integration."""

from __future__ import annotations

import contextlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = f"/api/{DOMAIN}"
PANEL_TITLE = "Medication Tracker"
PANEL_ICON = "mdi:pill"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the Medication Tracker panel."""
    # Register the static files
    panel_dir = Path(__file__).parent / "panel"

    # Serve static files
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"{PANEL_URL}/static",
                str(panel_dir / "static"),
                cache_headers=False,
            )
        ]
    )

    # Register the custom panel using panel_custom
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=DOMAIN,
        webcomponent_name="medication-tracker-panel",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_URL}/static/medication-tracker-panel.js",
        embed_iframe=False,
        trust_external=False,
        require_admin=False,
    )


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Unregister the Medication Tracker panel."""
    with contextlib.suppress(KeyError, ImportError):
        # Remove the panel using panel_custom
        frontend.async_remove_panel(hass, DOMAIN)

        # Note: Static path cleanup is handled automatically by Home Assistant
