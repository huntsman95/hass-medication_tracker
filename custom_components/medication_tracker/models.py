"""Data models for Medication Tracker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    EVENT_MEDICATION_STATE_CHANGED,
    FREQUENCY_AS_NEEDED,
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_WEEKLY,
    STATE_DUE,
    STATE_NOT_DUE,
    STATE_OVERDUE,
    STATE_SKIPPED,
    STATE_TAKEN,
)


@dataclass
class MedicationData:
    """Medication configuration data."""

    name: str
    dosage: str
    frequency: str
    times: list[str] = field(default_factory=list)
    start_date: date | datetime | None = None
    end_date: date | datetime | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "times": self.times,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MedicationData:
        """Create from dictionary."""
        # Handle start_date parsing
        start_date = None
        if data.get("start_date"):
            start_date_str = data["start_date"]
            if "T" in start_date_str:
                start_date = dt_util.as_local(datetime.fromisoformat(start_date_str))
            else:
                start_date = datetime.fromisoformat(start_date_str).date()

        # Handle end_date parsing
        end_date = None
        if data.get("end_date"):
            end_date_str = data["end_date"]
            if "T" in end_date_str:
                end_date = dt_util.as_local(datetime.fromisoformat(end_date_str))
            else:
                end_date = datetime.fromisoformat(end_date_str).date()

        return cls(
            name=data["name"],
            dosage=data["dosage"],
            frequency=data["frequency"],
            times=data.get("times", []),
            start_date=start_date,
            end_date=end_date,
            notes=data.get("notes", ""),
        )


@dataclass
class DoseRecord:
    """Record of a medication dose."""

    timestamp: datetime
    taken: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "taken": self.taken,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoseRecord:
        """Create from dictionary."""
        timestamp_str = data["timestamp"]
        # Parse the timestamp and ensure it's timezone-aware
        timestamp = datetime.fromisoformat(timestamp_str)
        if timestamp.tzinfo is None:
            # If the timestamp is naive, assume it's in the system timezone
            timestamp = dt_util.as_local(timestamp)
        return cls(
            timestamp=timestamp,
            taken=data["taken"],
            notes=data.get("notes", ""),
        )


class MedicationEntry:
    """Medication entry with tracking data."""

    def __init__(
        self, id: str, data: MedicationData, event_callback: Callable | None = None
    ) -> None:
        """Initialize medication entry."""
        self.id = id
        self.data = data
        self.dose_history: list[DoseRecord] = []
        self._current_status = STATE_NOT_DUE
        self._next_due: datetime | None = None
        self._last_taken: datetime | None = None
        # Device identifier for Home Assistant device registry
        self.device_id = f"medication_{id}"
        # Callback to fire events when state changes
        self._event_callback = event_callback

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "data": self.data.to_dict(),
            "dose_history": [record.to_dict() for record in self.dose_history],
            # Don't cache calculated values - always compute fresh from data
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], event_callback: Callable | None = None
    ) -> MedicationEntry:
        """Create from dictionary."""
        entry = cls(
            id=data["id"],
            data=MedicationData.from_dict(data["data"]),
            event_callback=event_callback,
        )
        # Handle legacy data that might not have device_id
        if "device_id" in data:
            entry.device_id = data["device_id"]
        entry.dose_history = [
            DoseRecord.from_dict(record) for record in data.get("dose_history", [])
        ]

        # Don't load cached calculated values - always compute fresh
        # These will be calculated when update_status() is called
        entry._current_status = STATE_NOT_DUE
        entry._next_due = None
        entry._last_taken = None

        return entry

    def record_dose_taken(self, timestamp: datetime, notes: str = "") -> None:
        """Record that a dose was taken."""
        record = DoseRecord(timestamp=timestamp, taken=True, notes=notes)
        self.dose_history.append(record)
        # Don't cache _last_taken - calculate it dynamically from dose_history
        self._update_next_due(timestamp)
        # Update status after recording dose
        self.update_status(timestamp)

    def record_dose_skipped(self, timestamp: datetime, notes: str = "") -> None:
        """Record that a dose was skipped."""
        record = DoseRecord(timestamp=timestamp, taken=False, notes=notes)
        self.dose_history.append(record)
        # When skipping, use the current next_due time (scheduled time) to calculate next due
        scheduled_time = self.next_due if self.next_due else timestamp
        self._update_next_due(scheduled_time)
        # Update status after recording dose
        self.update_status(timestamp)

    def reset_schedule(self) -> None:
        """Reset schedule calculations to force recalculation."""
        self._next_due = None

    def _fire_state_change_event(self, old_status: str, new_status: str) -> None:
        """Fire an event when medication state changes."""
        if self._event_callback and old_status != new_status:
            event_data = {
                "medication_id": self.id,
                "device_id": self.device_id,
                "name": self.data.name,
                "dosage": self.data.dosage,
                "frequency": self.data.frequency,
                "notes": self.data.notes,
                "old_status": old_status,
                "new_status": new_status,
                "next_due": self._next_due.isoformat() if self._next_due else None,
                "last_taken": self.last_taken.isoformat() if self.last_taken else None,
                "missed_doses": self.missed_doses,
                "adherence_rate": self.adherence_rate,
            }
            self._event_callback(EVENT_MEDICATION_STATE_CHANGED, event_data)

    def update_status(self, current_time: datetime) -> None:
        """Update the current status of the medication."""
        # Store the old status to detect changes
        old_status = self._current_status

        # Check if medication is outside its active date range
        current_local = dt_util.as_local(current_time)

        if self.data.start_date:
            if isinstance(self.data.start_date, datetime):
                # start_date is a timezone-aware datetime (start of day in local time)
                if current_local < self.data.start_date:
                    self._current_status = STATE_NOT_DUE
                    self._fire_state_change_event(old_status, self._current_status)
                    return
            elif current_local.date() < self.data.start_date:
                # start_date is a date object, compare dates
                self._current_status = STATE_NOT_DUE
                self._fire_state_change_event(old_status, self._current_status)
                return

        if self.data.end_date:
            if isinstance(self.data.end_date, datetime):
                # end_date is a timezone-aware datetime (end of day in local time)
                if current_local > self.data.end_date:
                    self._current_status = STATE_NOT_DUE
                    self._fire_state_change_event(old_status, self._current_status)
                    return
            elif current_local.date() > self.data.end_date:
                # end_date is a date object, compare dates
                self._current_status = STATE_NOT_DUE
                self._fire_state_change_event(old_status, self._current_status)
                return

        if self.data.frequency == FREQUENCY_AS_NEEDED:
            self._current_status = STATE_NOT_DUE
            self._fire_state_change_event(old_status, self._current_status)
            return

        if self._next_due is None:
            self._calculate_next_due(current_time)

        # Ensure _next_due is timezone-aware for comparison
        next_due = self._next_due
        last_taken = self.last_taken  # Use dynamic property instead of cached variable

        if next_due and next_due.tzinfo is None and current_time.tzinfo is not None:
            next_due = next_due.replace(tzinfo=current_time.tzinfo)
            self._next_due = next_due

        # Ensure last_taken is timezone-aware if it exists
        if last_taken and last_taken.tzinfo is None and current_time.tzinfo is not None:
            last_taken = last_taken.replace(tzinfo=current_time.tzinfo)

        if next_due is None:
            self._current_status = STATE_NOT_DUE
        else:
            # Check for recently skipped doses first (priority over all other statuses)
            recently_skipped = self._check_recently_skipped(current_local)
            if recently_skipped:
                self._current_status = STATE_SKIPPED
                self._fire_state_change_event(old_status, self._current_status)
                return

            # Check if medication is due or overdue
            if current_local >= next_due:
                # Check if it's significantly overdue (more than 2 hours)
                if current_local > next_due + timedelta(hours=2):
                    self._current_status = STATE_OVERDUE
                else:
                    self._current_status = STATE_DUE
            else:
                # Not yet due based on next_due time, but check other conditions

                # For daily medications, check if taken today (same calendar day)
                if (
                    last_taken
                    and self.data.frequency == FREQUENCY_DAILY
                    and self._was_taken_today(current_local, last_taken)
                ):
                    self._current_status = STATE_TAKEN
                    self._fire_state_change_event(old_status, self._current_status)
                    return

                # For non-daily medications, check if recently taken
                if (
                    last_taken
                    and self.data.frequency != FREQUENCY_DAILY
                    and current_local - last_taken < self._get_dose_interval()
                ):
                    self._current_status = STATE_TAKEN
                    self._fire_state_change_event(old_status, self._current_status)
                    return

                self._current_status = STATE_NOT_DUE

        # Fire event for any status change
        self._fire_state_change_event(old_status, self._current_status)

    def _calculate_next_due(self, current_time: datetime) -> None:
        """Calculate the next due time."""
        if self.data.frequency == FREQUENCY_AS_NEEDED:
            return

        if not self.data.times:
            # Default to once daily at 9 AM if no times specified
            self.data.times = ["09:00"]

        if self.data.frequency == FREQUENCY_DAILY:
            self._calculate_daily_next_due(current_time)
        elif self.data.frequency == FREQUENCY_WEEKLY:
            self._calculate_weekly_next_due(current_time)
        elif self.data.frequency == FREQUENCY_MONTHLY:
            self._calculate_monthly_next_due(current_time)

    def _calculate_daily_next_due(self, current_time: datetime) -> None:
        """Calculate next due time for daily medication."""
        # Use dt_util.as_local to properly interpret medication times as local times
        current_local = dt_util.as_local(current_time)
        today = current_local.date()
        next_due = None

        # First, check if there are any remaining times today that are still future
        for time_str in self.data.times:
            hour, minute = map(int, time_str.split(":"))

            # Create a naive datetime for the medication time
            naive_due_time = datetime.combine(
                today, datetime.min.time().replace(hour=hour, minute=minute)
            )

            # Use dt_util.as_local to interpret this as a local time
            due_time = dt_util.as_local(naive_due_time)

            if due_time > current_local:
                if next_due is None or due_time < next_due:
                    next_due = due_time

        # If no future times today, check if any of today's times are still pending
        if next_due is None:
            # Check if any of today's scheduled times haven't been handled yet
            any_today_unhandled = False
            earliest_today_time = None

            for time_str in self.data.times:
                hour, minute = map(int, time_str.split(":"))
                naive_due_time = datetime.combine(
                    today, datetime.min.time().replace(hour=hour, minute=minute)
                )
                due_time = dt_util.as_local(naive_due_time)

                # Track the earliest time today for reference
                if earliest_today_time is None or due_time < earliest_today_time:
                    earliest_today_time = due_time

                # Check if this specific time was handled (taken or skipped)
                if not self._was_dose_handled_for_time(due_time):
                    any_today_unhandled = True
                    # Keep the earliest unhandled time as next_due so it shows as overdue
                    if next_due is None or due_time < next_due:
                        next_due = due_time

            # Only move to tomorrow if all of today's doses were handled (taken or skipped)
            if not any_today_unhandled:
                # All times for today have been handled, get tomorrow's first time
                tomorrow = today + timedelta(days=1)
                hour, minute = map(int, self.data.times[0].split(":"))

                naive_next_due = datetime.combine(
                    tomorrow, datetime.min.time().replace(hour=hour, minute=minute)
                )

                # Use dt_util.as_local to interpret this as a local time
                next_due = dt_util.as_local(naive_next_due)

        self._next_due = next_due

    def _was_dose_taken_for_time(self, scheduled_time: datetime) -> bool:
        """Check if a dose was taken for a specific scheduled time."""
        if not self.dose_history:
            return False

        # For daily medications, check if any dose was taken on the same day
        # as the scheduled time (between 00:00 and 23:59 local time)
        scheduled_date = dt_util.as_local(scheduled_time).date()

        for dose in self.dose_history:
            if dose.taken:
                dose_date = dt_util.as_local(dose.timestamp).date()
                if dose_date == scheduled_date:
                    return True

        return False

    def _was_dose_handled_for_time(self, scheduled_time: datetime) -> bool:
        """Check if a dose was either taken OR skipped for a specific scheduled time."""
        if not self.dose_history:
            return False

        # For daily medications, check if any dose was taken or skipped on the same day
        # as the scheduled time (between 00:00 and 23:59 local time)
        scheduled_date = dt_util.as_local(scheduled_time).date()

        for dose in self.dose_history:
            dose_date = dt_util.as_local(dose.timestamp).date()
            if dose_date == scheduled_date:
                return True  # Either taken or skipped

        return False

    def _was_taken_today(self, current_time: datetime, last_taken: datetime) -> bool:
        """Check if medication was taken today (same calendar day as current_time)."""
        current_date = dt_util.as_local(current_time).date()
        taken_date = dt_util.as_local(last_taken).date()
        return current_date == taken_date

    def _calculate_weekly_next_due(self, current_time: datetime) -> None:
        """Calculate next due time for weekly medication."""
        current_local = dt_util.as_local(current_time)
        last_taken = self.last_taken  # This calculates from dose_history

        if not self.data.times:
            # Default to once weekly at 9 AM if no times specified
            self.data.times = ["09:00"]

        # Get the first (and typically only) scheduled time for weekly meds
        time_str = self.data.times[0]
        hour, minute = map(int, time_str.split(":"))

        # For weekly medications, we need to be smart about calculating from skipped doses
        # Check if the current_time represents a scheduled dose time that's being skipped
        current_date = current_local.date()
        scheduled_time_today = datetime.combine(
            current_date, datetime.min.time().replace(hour=hour, minute=minute)
        )
        scheduled_time_today_aware = dt_util.as_local(scheduled_time_today)

        # If current_time matches a scheduled time (within reasonable window),
        # and there's a recent skip, calculate from this scheduled time
        if (
            abs((current_local - scheduled_time_today_aware).total_seconds())
            < 3600  # within 1 hour
            and self.dose_history
            and not self.dose_history[-1].taken
        ):  # last record is a skip
            # Calculate next dose: 7 days from the scheduled time being skipped
            next_dose_date = current_date + timedelta(weeks=1)
            naive_next_due = datetime.combine(
                next_dose_date, datetime.min.time().replace(hour=hour, minute=minute)
            )
            self._next_due = dt_util.as_local(naive_next_due)
        elif last_taken:
            # Calculate next dose: 7 days from the date the last dose was taken,
            # but at the scheduled time (not the time it was actually taken)
            last_taken_local = dt_util.as_local(last_taken)
            next_dose_date = last_taken_local.date() + timedelta(weeks=1)

            # Create next due time at the scheduled hour/minute (not actual taken time)
            naive_next_due = datetime.combine(
                next_dose_date, datetime.min.time().replace(hour=hour, minute=minute)
            )
            self._next_due = dt_util.as_local(naive_next_due)
        else:
            # First dose - find the next occurrence of the scheduled time
            # If we have a start_date, use it; otherwise use today
            if self.data.start_date:
                if isinstance(self.data.start_date, datetime):
                    start_date = dt_util.as_local(self.data.start_date).date()
                else:
                    start_date = self.data.start_date
            else:
                start_date = current_local.date()

            # Create the scheduled time for the start date
            naive_due_time = datetime.combine(
                start_date, datetime.min.time().replace(hour=hour, minute=minute)
            )
            due_time = dt_util.as_local(naive_due_time)

            # If this time has already passed, move to next week
            if due_time <= current_local:
                next_week_date = start_date + timedelta(weeks=1)
                naive_due_time = datetime.combine(
                    next_week_date,
                    datetime.min.time().replace(hour=hour, minute=minute),
                )
                due_time = dt_util.as_local(naive_due_time)

            self._next_due = due_time

    def _calculate_monthly_next_due(self, current_time: datetime) -> None:
        """Calculate next due time for monthly medication."""
        current_local = dt_util.as_local(current_time)
        last_taken = self.last_taken  # This calculates from dose_history

        # For monthly medications, check if we're calculating from a skipped dose
        # Similar logic to weekly medications
        if (
            self.dose_history
            and not self.dose_history[-1].taken  # Most recent was skipped
            and last_taken
        ):  # But we have a previous taken dose
            # Calculate next dose from the skip time (current_time represents the skip)
            # Move to next month from the current time
            current_date = current_local.date()
            try:
                if current_date.month == 12:
                    next_month_date = current_date.replace(
                        year=current_date.year + 1, month=1
                    )
                else:
                    next_month_date = current_date.replace(month=current_date.month + 1)

                # Use the same time from the last taken dose for consistency
                last_taken_local = dt_util.as_local(last_taken)
                self._next_due = dt_util.as_local(
                    datetime.combine(next_month_date, last_taken_local.time())
                )
            except ValueError:
                # Handle day-of-month edge cases (e.g., Jan 31 -> Feb 28/29)
                if current_date.month == 12:
                    next_month_date = current_date.replace(
                        year=current_date.year + 1, month=1, day=1
                    )
                else:
                    next_month_date = current_date.replace(
                        month=current_date.month + 1, day=1
                    )

                # Use 9 AM as default time
                self._next_due = dt_util.as_local(
                    datetime.combine(
                        next_month_date, datetime.min.time().replace(hour=9, minute=0)
                    )
                )

        elif last_taken:
            # Normal case - calculate from last taken dose
            # Try to maintain the same day of month
            try:
                if last_taken.month == 12:
                    next_month = last_taken.replace(year=last_taken.year + 1, month=1)
                else:
                    next_month = last_taken.replace(month=last_taken.month + 1)
                self._next_due = next_month
            except ValueError:
                # Handle day-of-month edge cases (e.g., Jan 31 -> Feb 28/29)
                if last_taken.month == 12:
                    next_month = last_taken.replace(
                        year=last_taken.year + 1, month=1, day=1
                    )
                else:
                    next_month = last_taken.replace(month=last_taken.month + 1, day=1)
                self._next_due = next_month
        else:
            # First dose - use current time
            self._next_due = current_time

    def _update_next_due(self, taken_time: datetime) -> None:
        """Update next due time after a dose is taken."""
        if self.data.frequency == FREQUENCY_DAILY:
            self._calculate_daily_next_due(taken_time)
        elif self.data.frequency == FREQUENCY_WEEKLY:
            self._calculate_weekly_next_due(taken_time)
        elif self.data.frequency == FREQUENCY_MONTHLY:
            self._calculate_monthly_next_due(taken_time)

    def _get_dose_interval(self) -> timedelta:
        """Get the interval between doses."""
        if self.data.frequency == FREQUENCY_DAILY:
            return timedelta(days=1)
        if self.data.frequency == FREQUENCY_WEEKLY:
            return timedelta(weeks=1)
        if self.data.frequency == FREQUENCY_MONTHLY:
            return timedelta(days=30)
        return timedelta(days=1)

    def _check_recently_skipped(self, current_time: datetime) -> bool:
        """Check if a dose was recently skipped."""
        if not self.dose_history:
            return False

        current_local = dt_util.as_local(current_time)

        if self.data.frequency == FREQUENCY_DAILY:
            # For daily meds, check for skips today only
            today = current_local.date()

            # Get the most recent dose record for today
            most_recent_today = None
            for record in reversed(self.dose_history):
                record_local = dt_util.as_local(record.timestamp)
                record_date = record_local.date()

                if record_date == today:
                    most_recent_today = record
                    break
                if record_date < today:
                    # Stop looking at older records
                    break

            # If the most recent dose record for today was skipped, return True
            if most_recent_today is not None and not most_recent_today.taken:
                return True
        elif (
            self.dose_history
            and not self.dose_history[-1].taken  # Most recent was skipped
            and self.next_due
            and current_local < self.next_due
        ):  # Still before next due
            # For weekly/monthly meds, check if the most recent dose was skipped
            # and it's still before the next scheduled dose
            return True

        return False

    def _get_next_scheduled_time_today(
        self, current_time: datetime, skipped_time: str
    ) -> datetime | None:
        """Get the next scheduled time after the skipped time for today."""
        current_local = dt_util.as_local(current_time)
        today = current_local.date()

        skipped_hour, skipped_minute = map(int, skipped_time.split(":"))

        for time_str in self.data.times:
            hour, minute = map(int, time_str.split(":"))
            scheduled_time = datetime.combine(
                today, datetime.min.time().replace(hour=hour, minute=minute)
            )
            scheduled_time_aware = dt_util.as_local(scheduled_time)

            # Find the next time after the skipped time
            if hour > skipped_hour or (
                hour == skipped_hour and minute > skipped_minute
            ):
                return scheduled_time_aware

        return None  # No more scheduled times today

    @property
    def current_status(self) -> str:
        """Get current status."""
        return self._current_status

    @property
    def next_due(self) -> datetime | None:
        """Get next due time."""
        return self._next_due

    @property
    def last_taken(self) -> datetime | None:
        """Get last taken time calculated from dose history."""
        # Find the most recent dose that was actually taken
        for record in reversed(self.dose_history):
            if record.taken:
                return record.timestamp
        return None

    @property
    def missed_doses(self) -> int:
        """Get count of missed doses."""
        return sum(1 for record in self.dose_history if not record.taken)

    @property
    def adherence_rate(self) -> float:
        """Get adherence rate as percentage."""
        if not self.dose_history:
            return 0.0
        taken_count = sum(1 for record in self.dose_history if record.taken)
        return (taken_count / len(self.dose_history)) * 100
