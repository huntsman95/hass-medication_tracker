"""Services for Medication Tracker integration."""

from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CURRENT_SUPPLY,
    ATTR_DATETIME,
    ATTR_MEDICATION_ID,
    ATTR_REFILL_AMOUNT,
    CONF_CURRENT_SUPPLY,
    CONF_DOSAGE,
    CONF_END_DATE,
    CONF_FREQUENCY,
    CONF_MEDICATION_NAME,
    CONF_NOTES,
    CONF_PILLS_PER_DOSE,
    CONF_REFILL_REMINDER_THRESHOLD,
    CONF_SHOW_REFILL_ON_CALENDAR,
    CONF_START_DATE,
    CONF_SUPPLY_TRACKING_ENABLED,
    CONF_TIMES,
    DOMAIN,
    FREQUENCY_AS_NEEDED,
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_WEEKLY,
    SERVICE_ADD_MEDICATION,
    SERVICE_REFILL_MEDICATION,
    SERVICE_REMOVE_MEDICATION,
    SERVICE_SKIP_MEDICATION,
    SERVICE_TAKE_MEDICATION,
    SERVICE_UPDATE_MEDICATION,
    SERVICE_UPDATE_SUPPLY,
)
from .coordinator import MedicationCoordinator
from .models import MedicationData

_LOGGER = logging.getLogger(__name__)

TAKE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_DATETIME): cv.datetime,
    }
)

SKIP_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_DATETIME): cv.datetime,
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
        # Supply tracking fields
        vol.Optional(CONF_SUPPLY_TRACKING_ENABLED, default=False): cv.boolean,
        vol.Optional(CONF_CURRENT_SUPPLY): vol.Coerce(float),
        vol.Optional(CONF_PILLS_PER_DOSE, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_REFILL_REMINDER_THRESHOLD, default=7): cv.positive_int,
        vol.Optional(CONF_SHOW_REFILL_ON_CALENDAR, default=False): cv.boolean,
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
        # Supply tracking fields
        vol.Optional(CONF_SUPPLY_TRACKING_ENABLED): cv.boolean,
        vol.Optional(CONF_CURRENT_SUPPLY): vol.Coerce(float),
        vol.Optional(CONF_PILLS_PER_DOSE): vol.Coerce(float),
        vol.Optional(CONF_REFILL_REMINDER_THRESHOLD): cv.positive_int,
        vol.Optional(CONF_SHOW_REFILL_ON_CALENDAR): cv.boolean,
    }
)

REFILL_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Required(ATTR_REFILL_AMOUNT): vol.Coerce(float),
        vol.Optional(ATTR_DATETIME): cv.datetime,
    }
)

UPDATE_SUPPLY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Required(ATTR_CURRENT_SUPPLY): vol.Coerce(float),
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
        taken_at = call.data.get(ATTR_DATETIME)

        # Convert naive datetime to timezone-aware datetime if needed
        if taken_at is not None and taken_at.tzinfo is None:
            taken_at = dt_util.as_local(taken_at)

        # Find the coordinator for this medication
        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            await coordinator.async_take_medication(medication_id, taken_at)
        else:
            _LOGGER.error("Medication %s not found", medication_id)

    async def handle_skip_medication(call: ServiceCall) -> None:
        """Handle skip medication service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]
        skipped_at = call.data.get(ATTR_DATETIME)

        # Convert naive datetime to timezone-aware datetime if needed
        if skipped_at is not None and skipped_at.tzinfo is None:
            skipped_at = dt_util.as_local(skipped_at)

        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            await coordinator.async_skip_medication(medication_id, skipped_at)
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

        # Convert date objects to local timezone datetime objects
        start_date = call.data.get(CONF_START_DATE)
        if start_date is not None:
            # Convert date to start of day in local timezone (00:00:00)
            start_date = dt_util.start_of_local_day(start_date)

        end_date = call.data.get(CONF_END_DATE)
        if end_date is not None:
            # Convert date to end of day in local timezone (23:59:59.999999)
            end_date = (
                dt_util.start_of_local_day(end_date)
                + timedelta(days=1)
                - timedelta(microseconds=1)
            )
        medication_data = MedicationData(
            name=call.data[CONF_MEDICATION_NAME],
            dosage=call.data[CONF_DOSAGE],
            frequency=call.data[CONF_FREQUENCY],
            times=call.data.get(CONF_TIMES, []),
            start_date=start_date,
            end_date=end_date,
            notes=call.data.get(CONF_NOTES, ""),
            # Supply tracking fields
            supply_tracking_enabled=call.data.get(CONF_SUPPLY_TRACKING_ENABLED, False),
            current_supply=call.data.get(CONF_CURRENT_SUPPLY),
            pills_per_dose=call.data.get(CONF_PILLS_PER_DOSE, 1),
            refill_reminder_threshold=call.data.get(CONF_REFILL_REMINDER_THRESHOLD, 7),
            show_refill_on_calendar=call.data.get(CONF_SHOW_REFILL_ON_CALENDAR, False),
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

        # Handle date conversions
        start_date = call.data.get(CONF_START_DATE, current_medication.data.start_date)
        if start_date is not None and not isinstance(start_date, (type(None), str)):
            # If it's a date object (not None or string), convert to local timezone datetime
            start_date = dt_util.start_of_local_day(start_date)

        end_date = call.data.get(CONF_END_DATE, current_medication.data.end_date)
        if end_date is not None and not isinstance(end_date, (type(None), str)):
            # If it's a date object (not None or string), convert to end of day in local timezone
            end_date = (
                dt_util.start_of_local_day(end_date)
                + timedelta(days=1)
                - timedelta(microseconds=1)
            )

        # Create updated medication data, keeping existing values for fields not provided
        updated_data = MedicationData(
            name=call.data.get(CONF_MEDICATION_NAME, current_medication.data.name),
            dosage=call.data.get(CONF_DOSAGE, current_medication.data.dosage),
            frequency=call.data.get(CONF_FREQUENCY, current_medication.data.frequency),
            times=call.data.get(CONF_TIMES, current_medication.data.times),
            start_date=start_date,
            end_date=end_date,
            notes=call.data.get(CONF_NOTES, current_medication.data.notes),
            # Supply tracking fields
            supply_tracking_enabled=call.data.get(
                CONF_SUPPLY_TRACKING_ENABLED,
                current_medication.data.supply_tracking_enabled,
            ),
            current_supply=call.data.get(
                CONF_CURRENT_SUPPLY, current_medication.data.current_supply
            ),
            pills_per_dose=call.data.get(
                CONF_PILLS_PER_DOSE, current_medication.data.pills_per_dose
            ),
            refill_reminder_threshold=call.data.get(
                CONF_REFILL_REMINDER_THRESHOLD,
                current_medication.data.refill_reminder_threshold,
            ),
            last_refill_date=current_medication.data.last_refill_date,
            show_refill_on_calendar=call.data.get(
                CONF_SHOW_REFILL_ON_CALENDAR,
                current_medication.data.show_refill_on_calendar,
            ),
        )

        success = await coordinator.async_update_medication(medication_id, updated_data)
        if success:
            _LOGGER.info("Updated medication %s (%s)", medication_id, updated_data.name)
        else:
            _LOGGER.error("Failed to update medication %s", medication_id)

    async def handle_refill_medication(call: ServiceCall) -> None:
        """Handle refill medication service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]
        refill_amount = call.data[ATTR_REFILL_AMOUNT]
        refill_date = call.data.get(ATTR_DATETIME)

        # Convert naive datetime to timezone-aware datetime if needed
        if refill_date is not None and refill_date.tzinfo is None:
            refill_date = dt_util.as_local(refill_date)

        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            success = await coordinator.async_refill_medication(
                medication_id, refill_amount, refill_date
            )
            if success:
                _LOGGER.info(
                    "Refilled medication %s with %d units", medication_id, refill_amount
                )
            else:
                _LOGGER.error("Failed to refill medication %s", medication_id)
        else:
            _LOGGER.error("Medication %s not found", medication_id)

    async def handle_update_supply(call: ServiceCall) -> None:
        """Handle update supply service call."""
        medication_id = call.data[ATTR_MEDICATION_ID]
        new_supply = call.data[ATTR_CURRENT_SUPPLY]

        coordinator = _get_coordinator_for_medication(hass, medication_id)
        if coordinator:
            success = await coordinator.async_update_supply(medication_id, new_supply)
            if success:
                _LOGGER.info(
                    "Updated supply for medication %s to %d", medication_id, new_supply
                )
            else:
                _LOGGER.error("Failed to update supply for medication %s", medication_id)
        else:
            _LOGGER.error("Medication %s not found", medication_id)

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

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFILL_MEDICATION,
        handle_refill_medication,
        schema=REFILL_MEDICATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SUPPLY,
        handle_update_supply,
        schema=UPDATE_SUPPLY_SCHEMA,
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
    hass.services.async_remove(DOMAIN, SERVICE_REFILL_MEDICATION)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_SUPPLY)
