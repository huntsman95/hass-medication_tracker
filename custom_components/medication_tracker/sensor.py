"""Sensor platform for Medication Tracker."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_LAST_TAKEN,
    ATTR_NEXT_DUE,
    ATTR_MISSED_DOSES,
)
from .coordinator import MedicationCoordinator
from .models import MedicationEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: MedicationCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create entities for existing medications
    entities = []
    if coordinator.data:
        medications = coordinator.data.get("medications", {})
        for medication_id, medication in medications.items():
            entities.extend(
                [
                    MedicationStatusSensor(coordinator, medication_id, medication),
                    MedicationAdherenceSensor(coordinator, medication_id, medication),
                    MedicationIdSensor(coordinator, medication_id, medication),
                ]
            )

    async_add_entities(entities)

    # Register callback for dynamic entity creation
    async def create_entities_for_medication(
        medication_id: str, medication: MedicationEntry
    ) -> None:
        """Create entities for a new medication."""
        new_entities = [
            MedicationStatusSensor(coordinator, medication_id, medication),
            MedicationAdherenceSensor(coordinator, medication_id, medication),
            MedicationIdSensor(coordinator, medication_id, medication),
        ]
        async_add_entities(new_entities)

    coordinator.register_entity_creation_callback(
        "sensor", create_entities_for_medication
    )


class MedicationStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for medication status."""

    def __init__(
        self,
        coordinator: MedicationCoordinator,
        medication_id: str,
        medication: MedicationEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._medication_id = medication_id
        self._medication = medication
        self._attr_unique_id = f"{DOMAIN}_{medication_id}_status"
        self._attr_name = f"{medication.data.name} Status"
        self._attr_icon = "mdi:pill"
        # Associate with the medication device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, medication.device_id)},
            "name": f"{medication.data.name} Medication",
            "manufacturer": "Home Assistant",
            "model": "Medication Tracker",
            "suggested_area": "Medicine Cabinet",
        }

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator.data:
            medications = self.coordinator.data.get("medications", {})
            if self._medication_id in medications:
                medication = medications[self._medication_id]
                return medication.current_status
        return "unknown"

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
            "medication_id": self._medication_id,  # Include the actual UUID for JavaScript fallback
            "dosage": medication.data.dosage,
            "frequency": medication.data.frequency,
            "times": medication.data.times,
            ATTR_MISSED_DOSES: medication.missed_doses,
        }

        if medication.last_taken:
            attributes[ATTR_LAST_TAKEN] = medication.last_taken.isoformat()

        if medication.next_due:
            attributes[ATTR_NEXT_DUE] = medication.next_due.isoformat()

        if medication.data.start_date:
            attributes["start_date"] = medication.data.start_date.isoformat()

        if medication.data.end_date:
            attributes["end_date"] = medication.data.end_date.isoformat()

        if medication.data.notes:
            attributes["notes"] = medication.data.notes

        return attributes


class MedicationAdherenceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for medication adherence rate."""

    def __init__(
        self,
        coordinator: MedicationCoordinator,
        medication_id: str,
        medication: MedicationEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._medication_id = medication_id
        self._medication = medication
        self._attr_unique_id = f"{DOMAIN}_{medication_id}_adherence"
        self._attr_name = f"{medication.data.name} Adherence"
        self._attr_icon = "mdi:chart-line"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Associate with the medication device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, medication.device_id)},
            "name": f"{medication.data.name} Medication",
            "manufacturer": "Home Assistant",
            "model": "Medication Tracker",
            "suggested_area": "Medicine Cabinet",
        }

    @property
    def native_value(self) -> float:
        """Return the adherence rate."""
        if self.coordinator.data:
            medications = self.coordinator.data.get("medications", {})
            if self._medication_id in medications:
                medication = medications[self._medication_id]
                return round(medication.adherence_rate, 1)
        return 0.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        medications = self.coordinator.data.get("medications", {})
        if self._medication_id not in medications:
            return {}

        medication = medications[self._medication_id]
        total_doses = len(medication.dose_history)
        taken_doses = sum(1 for record in medication.dose_history if record.taken)

        return {
            "medication_name": medication.data.name,
            "total_doses": total_doses,
            "taken_doses": taken_doses,
            ATTR_MISSED_DOSES: medication.missed_doses,
        }


class MedicationIdSensor(CoordinatorEntity, SensorEntity):
    """Sensor for medication ID."""

    def __init__(
        self,
        coordinator: MedicationCoordinator,
        medication_id: str,
        medication: MedicationEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._medication_id = medication_id
        self._medication = medication
        self._attr_unique_id = f"{DOMAIN}_{medication_id}_id"
        self._attr_name = f"{medication.data.name} ID"
        self._attr_icon = "mdi:identifier"
        # Associate with the medication device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, medication.device_id)},
            "name": f"{medication.data.name} Medication",
            "manufacturer": "Home Assistant",
            "model": "Medication Tracker",
            "suggested_area": "Medicine Cabinet",
        }

    @property
    def native_value(self) -> str:
        """Return the medication ID."""
        return self._medication_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        medications = self.coordinator.data.get("medications", {})
        if self._medication_id not in medications:
            return {}

        medication = medications[self._medication_id]
        return {
            "medication_name": medication.data.name,
            "device_id": medication.device_id,
            "medication_id": self._medication_id,
        }
