"""Calendar platform for Medication Tracker integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MedicationCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform for Medication Tracker."""
    coordinator: MedicationCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create a single calendar entity that shows all dose history
    async_add_entities([MedicationTrackerCalendar(coordinator)])


class MedicationTrackerCalendar(CalendarEntity):
    """Calendar entity for medication dose history."""

    def __init__(self, coordinator: MedicationCoordinator) -> None:
        """Initialize the calendar entity."""
        super().__init__()
        self._coordinator = coordinator
        self._attr_name = "Medication Tracker Dose Taken"
        self._attr_unique_id = f"{DOMAIN}_dose_taken"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "dose_calendar")},
            "name": "Medication Tracker Calendar",
            "manufacturer": "Home Assistant",
            "model": "Dose History Calendar",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next event."""
        # For calendar entities, this typically returns the next upcoming event
        # Since this is a historical dose calendar, we return None
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = []

        medications = self._coordinator.data.get("medications", {})

        for medication_id, medication in medications.items():
            # Get dose history for this medication
            for dose_record in medication.dose_history:
                dose_time = dose_record.timestamp

                # Compare using dates to avoid timezone issues
                if start_date.date() <= dose_time.date() <= end_date.date():
                    event_summary = self._create_event_summary(medication, dose_record)
                    event_description = self._create_event_description(
                        medication, dose_record
                    )

                    event = CalendarEvent(
                        start=dose_time,
                        end=dose_time + timedelta(minutes=5),
                        summary=event_summary,
                        description=event_description,
                        uid=f"{DOMAIN}_{medication_id}_{dose_time.isoformat()}",
                    )
                    events.append(event)

            # Add estimated refill date event if enabled
            if (
                medication.data.supply_tracking_enabled
                and medication.data.show_refill_on_calendar
            ):
                refill_date = medication.estimated_refill_date
                if refill_date and start_date.date() <= refill_date <= end_date.date():
                    refill_datetime = datetime.combine(
                        refill_date, datetime.min.time().replace(hour=9, minute=0),
                        tzinfo=start_date.tzinfo
                    )
                    event = CalendarEvent(
                        start=refill_datetime,
                        end=refill_datetime + timedelta(hours=1),
                        summary=f"💊 Refill Needed: {medication.data.name}",
                        description=self._create_refill_event_description(medication),
                        uid=f"{DOMAIN}_{medication_id}_refill_{refill_date.isoformat()}",
                    )
                    events.append(event)

        events.sort(key=lambda x: x.start)
        return events

    def _create_event_summary(self, medication, dose_record) -> str:
        """Create a summary for the calendar event."""
        status = "✅ Taken" if dose_record.taken else "❌ Skipped"
        return f"{status}: {medication.data.name} ({medication.data.dosage})"

    def _create_event_description(self, medication, dose_record) -> str:
        """Create a description for the calendar event."""
        status = "taken" if dose_record.taken else "skipped"
        description_parts = [
            f"Medication: {medication.data.name}",
            f"Dosage: {medication.data.dosage}",
            f"Status: {status.title()}",
            f"Time: {dose_record.timestamp.strftime('%I:%M %p')}",
        ]

        if dose_record.notes:
            description_parts.append(f"Notes: {dose_record.notes}")

        if medication.data.frequency:
            description_parts.append(f"Frequency: {medication.data.frequency}")

        return "\n".join(description_parts)

    def _create_refill_event_description(self, medication) -> str:
        """Create a description for the refill calendar event."""
        description_parts = [
            f"Medication: {medication.data.name}",
            f"Current Supply: {medication.data.current_supply} units",
        ]

        daily_consumption = medication.daily_consumption
        if daily_consumption:
            description_parts.append(
                f"Daily Consumption: {daily_consumption:.1f} units/day"
            )

        days_remaining = medication.days_of_supply_remaining
        if days_remaining is not None:
            description_parts.append(f"Days Remaining: {days_remaining:.1f}")

        if medication.data.last_refill_date:
            description_parts.append(
                f"Last Refill: {medication.data.last_refill_date.isoformat()}"
            )

        return "\n".join(description_parts)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    async def async_update(self) -> None:
        """Update the entity."""
        # The calendar data is provided by the coordinator
        # No additional update logic needed

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        # Listen for coordinator updates
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
