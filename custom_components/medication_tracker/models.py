"""Data models for Medication Tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
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
                start_date = datetime.fromisoformat(start_date_str)
            else:
                start_date = datetime.fromisoformat(start_date_str).date()

        # Handle end_date parsing
        end_date = None
        if data.get("end_date"):
            end_date_str = data["end_date"]
            if "T" in end_date_str:
                end_date = datetime.fromisoformat(end_date_str)
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

    def __init__(self, id: str, data: MedicationData) -> None:
        """Initialize medication entry."""
        self.id = id
        self.data = data
        self.dose_history: list[DoseRecord] = []
        self._current_status = STATE_NOT_DUE
        self._next_due: datetime | None = None
        self._last_taken: datetime | None = None
        # Device identifier for Home Assistant device registry
        self.device_id = f"medication_{id}"

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
    def from_dict(cls, data: dict[str, Any]) -> MedicationEntry:
        """Create from dictionary."""
        entry = cls(
            id=data["id"],
            data=MedicationData.from_dict(data["data"]),
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

    def record_dose_skipped(self, timestamp: datetime, notes: str = "") -> None:
        """Record that a dose was skipped."""
        record = DoseRecord(timestamp=timestamp, taken=False, notes=notes)
        self.dose_history.append(record)
        self._update_next_due(timestamp)

    def update_status(self, current_time: datetime) -> None:
        """Update the current status of the medication."""
        # Check if medication is outside its active date range
        current_local = dt_util.as_local(current_time)

        if self.data.start_date:
            if isinstance(self.data.start_date, datetime):
                # start_date is a timezone-aware datetime (start of day in local time)
                if current_local < self.data.start_date:
                    self._current_status = STATE_NOT_DUE
                    return
            elif current_local.date() < self.data.start_date:
                # start_date is a date object, compare dates
                self._current_status = STATE_NOT_DUE
                return

        if self.data.end_date:
            if isinstance(self.data.end_date, datetime):
                # end_date is a timezone-aware datetime (end of day in local time)
                if current_local > self.data.end_date:
                    self._current_status = STATE_NOT_DUE
                    return
            elif current_local.date() > self.data.end_date:
                # end_date is a date object, compare dates
                self._current_status = STATE_NOT_DUE
                return

        if self.data.frequency == FREQUENCY_AS_NEEDED:
            self._current_status = STATE_NOT_DUE
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
        elif current_time >= next_due:
            # Check if it's significantly overdue (more than 2 hours)
            if current_time > next_due + timedelta(hours=2):
                self._current_status = STATE_OVERDUE
            else:
                self._current_status = STATE_DUE
        else:
            # Check for recently skipped doses first (priority over taken status)
            recently_skipped = self._check_recently_skipped(current_time)
            if recently_skipped:
                self._current_status = STATE_SKIPPED
                return

            if last_taken and current_time - last_taken < self._get_dose_interval():
                # Check if dose was recently taken
                self._current_status = STATE_TAKEN
                return

            # Check if any of today's scheduled times are overdue
            current_local = dt_util.as_local(current_time)
            today = current_local.date()

            for time_str in self.data.times:
                hour, minute = map(int, time_str.split(":"))
                naive_due_time = datetime.combine(
                    today, datetime.min.time().replace(hour=hour, minute=minute)
                )
                due_time = dt_util.as_local(naive_due_time)

                # If current time is past this scheduled time today, medication is due/overdue
                if current_time >= due_time:
                    if current_time > due_time + timedelta(hours=2):
                        self._current_status = STATE_OVERDUE
                    else:
                        self._current_status = STATE_DUE
                    return

            self._current_status = STATE_NOT_DUE

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

        for time_str in self.data.times:
            hour, minute = map(int, time_str.split(":"))

            # Create a naive datetime for the medication time
            naive_due_time = datetime.combine(
                today, datetime.min.time().replace(hour=hour, minute=minute)
            )

            # Use dt_util.as_local to interpret this as a local time
            due_time = dt_util.as_local(naive_due_time)

            if due_time > current_time:
                if next_due is None or due_time < next_due:
                    next_due = due_time

        if next_due is None:
            # All times for today have passed, get tomorrow's first time
            tomorrow = today + timedelta(days=1)
            hour, minute = map(int, self.data.times[0].split(":"))

            naive_next_due = datetime.combine(
                tomorrow, datetime.min.time().replace(hour=hour, minute=minute)
            )

            # Use dt_util.as_local to interpret this as a local time
            next_due = dt_util.as_local(naive_next_due)

        self._next_due = next_due

    def _calculate_weekly_next_due(self, current_time: datetime) -> None:
        """Calculate next due time for weekly medication."""
        # Use the dynamic property instead of cached _last_taken
        last_taken = self.last_taken  # This calculates from dose_history
        if last_taken:
            self._next_due = last_taken + timedelta(weeks=1)
        else:
            # First dose - use current time
            self._next_due = current_time

    def _calculate_monthly_next_due(self, current_time: datetime) -> None:
        """Calculate next due time for monthly medication."""
        # Use the dynamic property instead of cached _last_taken
        last_taken = self.last_taken  # This calculates from dose_history
        if last_taken:
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
        if self.data.frequency == FREQUENCY_WEEKLY:
            self._next_due = taken_time + timedelta(weeks=1)
        if self.data.frequency == FREQUENCY_MONTHLY:
            try:
                next_month = taken_time.replace(month=taken_time.month + 1)
                self._next_due = next_month
            except ValueError:
                # Handle December -> January
                next_year = taken_time.replace(year=taken_time.year + 1, month=1)
                self._next_due = next_year

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
        """Check if a dose was recently skipped for today's scheduled times."""
        if not self.dose_history:
            return False

        current_local = dt_util.as_local(current_time)
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
