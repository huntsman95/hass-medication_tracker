"""Binary sensor platform for Medication Tracker."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATE_DUE, STATE_OVERDUE, STATE_SKIPPED
from .coordinator import MedicationCoordinator
from .models import MedicationEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: MedicationCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create entities for existing medications
    entities = []
    if coordinator.data:
        medications = coordinator.data.get("medications", {})
        for medication_id, medication in medications.items():
            entities.append(MedicationDueSensor(coordinator, medication_id, medication))

    async_add_entities(entities)

    # Register callback for dynamic entity creation
    async def create_entities_for_medication(
        medication_id: str, medication: MedicationEntry
    ) -> None:
        """Create entities for a new medication."""
        new_entities = [MedicationDueSensor(coordinator, medication_id, medication)]
        async_add_entities(new_entities)

    coordinator.register_entity_creation_callback(
        "binary_sensor", create_entities_for_medication
    )


class MedicationDueSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for medication due status."""

    def __init__(
        self,
        coordinator: MedicationCoordinator,
        medication_id: str,
        medication: MedicationEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._medication_id = medication_id
        self._medication = medication
        self._attr_unique_id = f"{DOMAIN}_{medication_id}_due"
        self._attr_name = f"{medication.data.name} Due"
        self._attr_icon = "mdi:alarm"
        # Change type to None instead of problem by commenting out the line below
        # self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        # Associate with the medication device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, medication.device_id)},
            "name": f"{medication.data.name} Medication",
            "manufacturer": "Home Assistant",
            "model": "Medication Tracker",
            "suggested_area": "Medicine Cabinet",
        }

    @property
    def is_on(self) -> bool:
        """Return true if medication is due or overdue."""
        if self.coordinator.data:
            medications = self.coordinator.data.get("medications", {})
            if self._medication_id in medications:
                medication = medications[self._medication_id]
                return medication.current_status in (STATE_DUE, STATE_OVERDUE)
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        medications = self.coordinator.data.get("medications", {})
        if self._medication_id not in medications:
            return {}

        medication = medications[self._medication_id]
        attributes = {
            "medication_name": medication.data.name,
            "status": medication.current_status,
            "dosage": medication.data.dosage,
        }

        if medication.next_due:
            attributes["next_due"] = medication.next_due.isoformat()

        if medication.data.start_date:
            attributes["start_date"] = medication.data.start_date.isoformat()

        if medication.data.end_date:
            attributes["end_date"] = medication.data.end_date.isoformat()

        return attributes
