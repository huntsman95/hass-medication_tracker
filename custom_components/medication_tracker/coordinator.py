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

from .const import DEVICE_MANUFACTURER, DEVICE_MODEL, DOMAIN, EVENT_MEDICATION_LOW_SUPPLY
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

    def _fire_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Fire a Home Assistant event."""
        self.hass.bus.async_fire(event_type, event_data)

    async def async_load_medications(self) -> None:
        """Load medications from storage."""
        try:
            data = await self._store.async_load()
            if data is not None:
                for med_id, med_data in data.get("medications", {}).items():
                    medication = MedicationEntry.from_dict(med_data, self._fire_event)
                    self._medications[med_id] = medication
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
        # Auto-populate start_date with today if not specified
        if medication_data.start_date is None:
            # Use the same pattern as services.py - create timezone-aware datetime for start of today
            today = dt_util.now().date()
            medication_data.start_date = dt_util.start_of_local_day(today)

        medication = MedicationEntry(
            id=str(uuid.uuid4()),
            data=medication_data,
            event_callback=self._fire_event,
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

        # Force recalculation of next due time since schedule may have changed
        medication.reset_schedule()
        now = dt_util.now()
        medication.update_status(now)

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

        # Check if supply was low BEFORE taking (for event firing)
        was_low_supply = medication.is_low_supply

        medication.record_dose_taken(taken_at)

        # Auto-decrement supply if supply tracking is enabled
        if medication.data.supply_tracking_enabled:
            medication.decrement_supply()

            # Fire low supply event if supply just became low
            if not was_low_supply and medication.is_low_supply:
                self._fire_low_supply_event(medication)

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

    async def async_refill_medication(
        self,
        medication_id: str,
        refill_amount: float,
        refill_date: datetime | None = None,
    ) -> bool:
        """Refill medication supply."""
        if medication_id not in self._medications:
            return False

        medication = self._medications[medication_id]

        if not medication.data.supply_tracking_enabled:
            _LOGGER.warning(
                "Supply tracking not enabled for medication %s", medication_id
            )
            return False

        # Add to current supply
        current = medication.data.current_supply or 0
        medication.data.current_supply = current + refill_amount

        # Update last refill date
        medication.data.last_refill_date = refill_date or dt_util.now()

        await self.async_save_medications()
        await self.async_request_refresh()

        _LOGGER.info(
            "Refilled medication %s with %d units. New supply: %d",
            medication_id,
            refill_amount,
            medication.data.current_supply,
        )
        return True

    async def async_update_supply(
        self, medication_id: str, new_supply: int
    ) -> bool:
        """Manually update medication supply count."""
        if medication_id not in self._medications:
            return False

        medication = self._medications[medication_id]

        if not medication.data.supply_tracking_enabled:
            _LOGGER.warning(
                "Supply tracking not enabled for medication %s", medication_id
            )
            return False

        # Check if supply was low BEFORE updating (for event firing)
        was_low_supply = medication.is_low_supply

        medication.data.current_supply = new_supply

        # Fire low supply event if supply just became low
        if not was_low_supply and medication.is_low_supply:
            self._fire_low_supply_event(medication)

        await self.async_save_medications()
        await self.async_request_refresh()

        _LOGGER.info(
            "Updated supply for medication %s to %d", medication_id, new_supply
        )
        return True

    def _fire_low_supply_event(self, medication: MedicationEntry) -> None:
        """Fire a Home Assistant event when medication supply becomes low."""
        days_remaining = medication.days_of_supply_remaining
        estimated_refill = medication.estimated_refill_date

        event_data = {
            "medication_id": medication.id,
            "medication_name": medication.data.name,
            "current_supply": medication.data.current_supply,
            "pills_per_dose": medication.data.pills_per_dose,
            "days_remaining": round(days_remaining, 1) if days_remaining else None,
            "refill_threshold_days": medication.data.refill_reminder_threshold,
            "estimated_refill_date": (
                estimated_refill.isoformat() if estimated_refill else None
            ),
        }
        self.hass.bus.async_fire(EVENT_MEDICATION_LOW_SUPPLY, event_data)
        _LOGGER.info(
            "Fired low supply event for medication %s (supply: %d, days remaining: %.1f)",
            medication.data.name,
            medication.data.current_supply or 0,
            days_remaining or 0,
        )
