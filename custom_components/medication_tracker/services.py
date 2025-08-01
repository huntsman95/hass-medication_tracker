"""Services for Medication Tracker integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_TAKE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_ADD_MEDICATION,
    SERVICE_REMOVE_MEDICATION,
    SERVICE_UPDATE_MEDICATION,
    ATTR_MEDICATION_ID,
    CONF_MEDICATION_NAME,
    CONF_DOSAGE,
    CONF_FREQUENCY,
    CONF_TIMES,
    CONF_START_DATE,
    CONF_END_DATE,
    CONF_NOTES,
    FREQUENCY_DAILY,
    FREQUENCY_WEEKLY,
    FREQUENCY_MONTHLY,
    FREQUENCY_AS_NEEDED,
)
from .coordinator import MedicationCoordinator
from .models import MedicationData

_LOGGER = logging.getLogger(__name__)

TAKE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

SKIP_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

ADD_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MEDICATION_NAME): cv.string,
        vol.Required(CONF_DOSAGE): cv.string,
        vol.Required(CONF_FREQUENCY): vol.In(
            [
                FREQUENCY_DAILY,
                FREQUENCY_WEEKLY,
                FREQUENCY_MONTHLY,
                FREQUENCY_AS_NEEDED,
            ]
        ),
        vol.Optional(CONF_TIMES, default=[]): [cv.string],
        vol.Optional(CONF_START_DATE): cv.date,
        vol.Optional(CONF_END_DATE): cv.date,
        vol.Optional(CONF_NOTES, default=""): cv.string,
    }
)

REMOVE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

UPDATE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(CONF_MEDICATION_NAME): cv.string,
        vol.Optional(CONF_DOSAGE): cv.string,
        vol.Optional(CONF_FREQUENCY): vol.In(
            [
                FREQUENCY_DAILY,
                FREQUENCY_WEEKLY,
                FREQUENCY_MONTHLY,
                FREQUENCY_AS_NEEDED,
            ]
        ),
        vol.Optional(CONF_TIMES): [cv.string],
        vol.Optional(CONF_START_DATE): cv.date,
        vol.Optional(CONF_END_DATE): cv.date,
        vol.Optional(CONF_NOTES): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Medication Tracker."""

    # Check if services are already registered to avoid duplicates
    if hass.services.has_service(DOMAIN, SERVICE_TAKE_MEDICATION):
        _LOGGER.debug("Services already registered, skipping setup")
        return

    async def handle_take_medication(call: ServiceCall) -> None:
        """Handle take medication service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]

        # Find the coordinator for this medication
        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            await coordinator.async_take_medication(medication_id)
        else:
            _LOGGER.error("Medication %s not found", medication_id)

    async def handle_skip_medication(call: ServiceCall) -> None:
        """Handle skip medication service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]

        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            await coordinator.async_skip_medication(medication_id)
        else:
            _LOGGER.error("Medication %s not found", medication_id)

    async def handle_add_medication(call: ServiceCall) -> None:
        """Handle add medication service call."""
        # For simplicity, add to the first available coordinator
        coordinators = _get_all_coordinators(hass)
        if not coordinators:
            _LOGGER.error("No medication tracker instances found")
            return

        coordinator = coordinators[0]
        medication_data = MedicationData(
            name=call.data[CONF_MEDICATION_NAME],
            dosage=call.data[CONF_DOSAGE],
            frequency=call.data[CONF_FREQUENCY],
            times=call.data.get(CONF_TIMES, []),
            start_date=call.data.get(CONF_START_DATE),
            end_date=call.data.get(CONF_END_DATE),
            notes=call.data.get(CONF_NOTES, ""),
        )

        medication_id = await coordinator.async_add_medication(medication_data)
        _LOGGER.info(
            "Added medication %s with ID %s", medication_data.name, medication_id
        )

    async def handle_remove_medication(call: ServiceCall) -> None:
        """Handle remove medication service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]

        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            success = await coordinator.async_remove_medication(medication_id)
            if success:
                _LOGGER.info("Removed medication %s", medication_id)
            else:
                _LOGGER.error("Failed to remove medication %s", medication_id)
        else:
            _LOGGER.error("Medication %s not found", medication_id)

    async def handle_update_medication(call: ServiceCall) -> None:
        """Handle update medication service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]

        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if not coordinator:
            _LOGGER.error("Medication %s not found", medication_id)
            return

        # Get the current medication data
        current_medication = coordinator.get_medication(medication_id)
        if not current_medication:
            _LOGGER.error("Medication %s not found", medication_id)
            return

        # Create updated medication data, keeping existing values for fields not provided
        updated_data = MedicationData(
            name=call.data.get(CONF_MEDICATION_NAME, current_medication.data.name),
            dosage=call.data.get(CONF_DOSAGE, current_medication.data.dosage),
            frequency=call.data.get(CONF_FREQUENCY, current_medication.data.frequency),
            times=call.data.get(CONF_TIMES, current_medication.data.times),
            start_date=call.data.get(
                CONF_START_DATE, current_medication.data.start_date
            ),
            end_date=call.data.get(CONF_END_DATE, current_medication.data.end_date),
            notes=call.data.get(CONF_NOTES, current_medication.data.notes),
        )

        success = await coordinator.async_update_medication(medication_id, updated_data)
        if success:
            _LOGGER.info("Updated medication %s (%s)", medication_id, updated_data.name)
        else:
            _LOGGER.error("Failed to update medication %s", medication_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_TAKE_MEDICATION,
        handle_take_medication,
        schema=TAKE_MEDICATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SKIP_MEDICATION,
        handle_skip_medication,
        schema=SKIP_MEDICATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_MEDICATION,
        handle_add_medication,
        schema=ADD_MEDICATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_MEDICATION,
        handle_remove_medication,
        schema=REMOVE_MEDICATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_MEDICATION,
        handle_update_medication,
        schema=UPDATE_MEDICATION_SCHEMA,
    )


def _get_coordinator_for_medication(
    hass: HomeAssistant, medication_id: str
) -> MedicationCoordinator | None:
    """Find the coordinator that contains the specified medication."""
    if DOMAIN not in hass.data:
        return None

    for coordinator in hass.data[DOMAIN].values():
        if isinstance(coordinator, MedicationCoordinator):
            if coordinator.get_medication(medication_id):
                return coordinator
    return None


def _get_all_coordinators(hass: HomeAssistant) -> list[MedicationCoordinator]:
    """Get all medication coordinators."""
    if DOMAIN not in hass.data:
        return []

    return [
        coordinator
        for coordinator in hass.data[DOMAIN].values()
        if isinstance(coordinator, MedicationCoordinator)
    ]


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_TAKE_MEDICATION)
    hass.services.async_remove(DOMAIN, SERVICE_SKIP_MEDICATION)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_MEDICATION)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_MEDICATION)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_MEDICATION)
