"""Button platform for Medication Tracker."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MedicationCoordinator
from .models import MedicationEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: MedicationCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create entities for existing medications
    entities = []
    if coordinator.data:
        medications = coordinator.data.get("medications", {})
        for medication_id, medication in medications.items():
            entities.extend(
                [
                    TakeMedicationButton(coordinator, medication_id, medication),
                    SkipMedicationButton(coordinator, medication_id, medication),
                ]
            )

    async_add_entities(entities)

    # Register callback for dynamic entity creation
    async def create_entities_for_medication(
        medication_id: str, medication: MedicationEntry
    ) -> None:
        """Create entities for a new medication."""
        new_entities = [
            TakeMedicationButton(coordinator, medication_id, medication),
            SkipMedicationButton(coordinator, medication_id, medication),
        ]
        async_add_entities(new_entities)

    coordinator.register_entity_creation_callback(
        "button", create_entities_for_medication
    )


class TakeMedicationButton(CoordinatorEntity, ButtonEntity):
    """Button to mark medication as taken."""

    def __init__(
        self,
        coordinator: MedicationCoordinator,
        medication_id: str,
        medication: MedicationEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._medication_id = medication_id
        self._medication = medication
        self._attr_unique_id = f"{DOMAIN}_{medication_id}_take"
        self._attr_name = f"Take {medication.data.name}"
        self._attr_icon = "mdi:check-circle"
        self.coordinator: MedicationCoordinator = coordinator
        # Associate with the medication device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, medication.device_id)},
            "name": f"{medication.data.name} Medication",
            "manufacturer": "Home Assistant",
            "model": "Medication Tracker",
            "suggested_area": "Medicine Cabinet",
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_take_medication(self._medication_id)


class SkipMedicationButton(CoordinatorEntity, ButtonEntity):
    """Button to mark medication as skipped."""

    def __init__(
        self,
        coordinator: MedicationCoordinator,
        medication_id: str,
        medication: MedicationEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._medication_id = medication_id
        self._medication = medication
        self._attr_unique_id = f"{DOMAIN}_{medication_id}_skip"
        self._attr_name = f"Skip {medication.data.name}"
        self._attr_icon = "mdi:close-circle"
        self.coordinator: MedicationCoordinator = coordinator
        # Associate with the medication device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, medication.device_id)},
            "name": f"{medication.data.name} Medication",
            "manufacturer": "Home Assistant",
            "model": "Medication Tracker",
            "suggested_area": "Medicine Cabinet",
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_skip_medication(self._medication_id)
