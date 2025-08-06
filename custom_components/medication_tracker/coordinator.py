"""Data update coordinator for Medication Tracker."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DEVICE_MANUFACTURER, DEVICE_MODEL, DOMAIN
from .models import MedicationData, MedicationEntry

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_medications"
UPDATE_INTERVAL = timedelta(minutes=1)


class MedicationCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Medication data update coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=config_entry,
        )
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._medications: dict[str, MedicationEntry] = {}
        self._entity_creation_callbacks: dict[str, Callable[..., Any]] = {}
        self._config_entry_id: str = config_entry.entry_id

    async def async_load_medications(self) -> None:
        """Load medications from storage."""
        try:
            data = await self._store.async_load()
            if data is not None:
                for med_id, med_data in data.get("medications", {}).items():
                    self._medications[med_id] = MedicationEntry.from_dict(med_data)
        except (OSError, ValueError) as err:
            _LOGGER.error("Error loading medications: %s", err)

    async def async_save_medications(self) -> None:
        """Save medications to storage."""
        try:
            data = {
                "medications": {
                    med_id: med.to_dict() for med_id, med in self._medications.items()
                }
            }
            await self._store.async_save(data)
        except (OSError, ValueError) as err:
            _LOGGER.error("Error saving medications: %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update medication data."""
        try:
            # Load medications if not already loaded
            if not self._medications:
                await self.async_load_medications()

            # Update medication statuses
            now = dt_util.now()
            for medication in self._medications.values():
                medication.update_status(now)

        except (OSError, ValueError) as err:
            _LOGGER.error("Error updating medication data: %s", err)
            raise UpdateFailed(f"Error updating medication data: {err}") from err

        return {
            "medications": self._medications,
            "last_updated": now,
        }

    async def async_add_medication(self, medication_data: MedicationData) -> str:
        """Add a new medication."""
        medication = MedicationEntry(
            id=str(uuid.uuid4()),
            data=medication_data,
        )
        self._medications[medication.id] = medication
        await self.async_save_medications()

        # Create device for the medication
        await self._async_create_device_for_medication(medication)

        # Notify platforms to create entities for the new medication
        await self._async_create_entities_for_medication(medication.id, medication)

        await self.async_request_refresh()
        return medication.id

    async def async_remove_medication(self, medication_id: str) -> bool:
        """Remove a medication."""
        if medication_id in self._medications:
            # Notify platforms to remove entities for this medication
            await self._async_remove_entities_for_medication(medication_id)

            # Remove device for the medication
            await self._async_remove_device_for_medication(medication_id)

            del self._medications[medication_id]
            await self.async_save_medications()
            await self.async_request_refresh()
            return True
        return False

    async def async_update_medication(
        self, medication_id: str, medication_data: MedicationData
    ) -> bool:
        """Update an existing medication."""
        if medication_id not in self._medications:
            return False

        # Update the medication data
        medication = self._medications[medication_id]
        medication.data = medication_data

        # Save the changes
        await self.async_save_medications()
        await self.async_request_refresh()

        _LOGGER.info("Updated medication %s (%s)", medication_id, medication_data.name)
        return True

    def register_entity_creation_callback(
        self, platform: str, callback: Callable[..., Any]
    ) -> None:
        """Register a callback for creating entities when medications are added."""
        self._entity_creation_callbacks[platform] = callback

    async def async_setup_platform_entities(self) -> None:
        """Set up entities for existing medications when a platform is loaded."""
        if not self.data:
            return

        medications = self.data.get("medications", {})
        for medication_id, medication in medications.items():
            await self._async_create_entities_for_medication(medication_id, medication)

    async def _async_create_entities_for_medication(
        self, medication_id: str, medication: MedicationEntry
    ) -> None:
        """Create entities for a new medication across all platforms."""
        for platform, callback in self._entity_creation_callbacks.items():
            try:
                await callback(medication_id, medication)
            except (ValueError, TypeError, AttributeError) as err:
                _LOGGER.error(
                    "Error creating entities for medication %s on platform %s: %s",
                    medication_id,
                    platform,
                    err,
                )

    async def _async_remove_entities_for_medication(self, medication_id: str) -> None:
        """Remove entities for a medication across all platforms."""
        # Get the entity registry to remove entities
        entity_registry = er.async_get(self.hass)

        # Find and remove all entities for this medication
        entries_to_remove = [
            entry.entity_id
            for entry in entity_registry.entities.values()
            if (
                entry.domain in {"sensor", "binary_sensor", "button"}
                and entry.platform == DOMAIN
                and medication_id in entry.unique_id
            )
        ]

        for entity_id in entries_to_remove:
            entity_registry.async_remove(entity_id)

    async def async_take_medication(
        self, medication_id: str, taken_at: datetime | None = None
    ) -> bool:
        """Mark a medication as taken."""
        if medication_id not in self._medications:
            return False

        medication = self._medications[medication_id]
        if taken_at is None:
            taken_at = dt_util.now()

        medication.record_dose_taken(taken_at)
        await self.async_save_medications()
        await self.async_refresh()
        return True

    async def async_skip_medication(
        self, medication_id: str, skipped_at: datetime | None = None
    ) -> bool:
        """Mark a medication as skipped."""
        if medication_id not in self._medications:
            return False

        medication = self._medications[medication_id]
        if skipped_at is None:
            skipped_at = dt_util.now()

        medication.record_dose_skipped(skipped_at)
        await self.async_save_medications()
        await self.async_refresh()
        return True

    async def _async_create_device_for_medication(
        self, medication: MedicationEntry
    ) -> None:
        """Create a device for a medication."""
        device_registry = dr.async_get(self.hass)

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry_id,
            identifiers={(DOMAIN, medication.device_id)},
            name=f"{medication.data.name} Medication",
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            suggested_area="Medicine Cabinet",
        )

    async def _async_remove_device_for_medication(self, medication_id: str) -> None:
        """Remove a device for a medication."""
        device_registry = dr.async_get(self.hass)
        medication = self._medications.get(medication_id)

        if medication:
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, medication.device_id)}
            )
            if device:
                device_registry.async_remove_device(device.id)

    def get_medication(self, medication_id: str) -> MedicationEntry | None:
        """Get a medication by ID."""
        return self._medications.get(medication_id)

    def get_all_medications(self) -> dict[str, MedicationEntry]:
        """Get all medications."""
        return self._medications.copy()
