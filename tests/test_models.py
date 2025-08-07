"""Tests for the Medication Tracker models."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from homeassistant.util import dt as dt_util

# Add the custom components directory to the Python path
custom_components_path = (
    Path(__file__).parent.parent.parent.parent / "config" / "custom_components"
)
sys.path.insert(0, str(custom_components_path))

# Import the medication tracker models
from medication_tracker.const import (
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
from medication_tracker.models import (
    DoseRecord,
    MedicationData,
    MedicationEntry,
)


class TestMedicationStatusCalculation:
    """Test medication status calculation across day boundaries."""

    def create_daily_medication(
        self, times: list[str] | None = None
    ) -> MedicationEntry:
        """Create a daily medication for testing."""
        times = times or ["09:00"]
        med_data = MedicationData(
            name="Test Medication",
            dosage="1 pill",
            frequency=FREQUENCY_DAILY,
            times=times,
        )
        return MedicationEntry("test_med", med_data)

    def test_medication_taken_yesterday_not_due_today_early(self) -> None:
        """Test that medication taken yesterday shows as not_due early today.

        This is the main bug fix test: A medication taken yesterday should
        show as "not_due" before the next scheduled time today, not "taken".
        """
        medication = self.create_daily_medication(["09:00"])

        # Take medication yesterday at 09:30 (timezone-aware)
        yesterday_taken = dt_util.as_local(datetime(2025, 8, 6, 9, 30))
        medication.record_dose_taken(yesterday_taken)

        # Check status today at 08:00 (before scheduled time) (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 8, 0))
        medication.update_status(current_time)

        # Should be not_due, not taken
        assert medication.current_status == STATE_NOT_DUE
        assert medication.last_taken == yesterday_taken
        # Expected next due time (timezone-aware)
        expected_next_due = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        assert medication.next_due == expected_next_due

    def test_medication_taken_yesterday_due_today_at_scheduled_time(self) -> None:
        """Test that medication shows as due at scheduled time even if taken yesterday."""
        medication = self.create_daily_medication(["09:00"])

        # Take medication yesterday (timezone-aware)
        yesterday_taken = dt_util.as_local(datetime(2025, 8, 6, 9, 30))
        medication.record_dose_taken(yesterday_taken)

        # Check status today at scheduled time (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        medication.update_status(current_time)

        # Should be due now
        assert medication.current_status == STATE_DUE

    def test_medication_taken_late_yesterday_not_due_early_today(self) -> None:
        """Test medication taken very late yesterday (23:30) is not_due early today (01:00)."""
        medication = self.create_daily_medication(["09:00"])

        # Take medication yesterday at 23:30 (very late) (timezone-aware)
        yesterday_late = dt_util.as_local(datetime(2025, 8, 6, 23, 30))
        medication.record_dose_taken(yesterday_late)

        # Check status today at 01:00 (early morning) (timezone-aware)
        today_early = dt_util.as_local(datetime(2025, 8, 7, 1, 0))
        medication.update_status(today_early)

        # Should be not_due, not taken
        assert medication.current_status == STATE_NOT_DUE
        assert medication.last_taken == yesterday_late
        expected_next_due = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        assert medication.next_due == expected_next_due

    def test_medication_taken_today_shows_as_taken(self) -> None:
        """Test that medication taken today shows as taken (before next scheduled time)."""
        medication = self.create_daily_medication(["09:00", "21:00"])

        # Take morning dose today (timezone-aware)
        morning_dose = dt_util.as_local(datetime(2025, 8, 7, 9, 15))
        medication.record_dose_taken(morning_dose)

        # Check status in the afternoon (before evening dose) (timezone-aware)
        afternoon_check = dt_util.as_local(datetime(2025, 8, 7, 15, 0))
        medication.update_status(afternoon_check)

        # Should be taken (morning dose taken, evening not due yet)
        assert medication.current_status == STATE_TAKEN
        assert medication.last_taken == morning_dose

    def test_multiple_doses_per_day_calculation(self) -> None:
        """Test status calculation with multiple scheduled times per day."""
        medication = self.create_daily_medication(["08:00", "12:00", "20:00"])

        # Take first dose (timezone-aware)
        first_dose = dt_util.as_local(datetime(2025, 8, 7, 8, 15))
        medication.record_dose_taken(first_dose)

        # Check at 10:00 - should be taken (first dose taken, next at 12:00) (timezone-aware)
        check_time = dt_util.as_local(datetime(2025, 8, 7, 10, 0))
        medication.update_status(check_time)
        assert medication.current_status == STATE_TAKEN

        # Check at 12:00 - should be due (second dose time) (timezone-aware)
        check_time = dt_util.as_local(datetime(2025, 8, 7, 12, 0))
        medication.update_status(check_time)
        assert medication.current_status == STATE_DUE

    def test_medication_overdue_calculation(self) -> None:
        """Test that medication shows as overdue after 2+ hours past due time."""
        medication = self.create_daily_medication(["09:00"])

        # Check status at 11:30 (2.5 hours after due time) (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 11, 30))
        medication.update_status(current_time)

        # Should be overdue
        assert medication.current_status == STATE_OVERDUE
        expected_next_due = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        assert medication.next_due == expected_next_due

    def test_medication_just_due_not_overdue(self) -> None:
        """Test that medication shows as due (not overdue) within 2 hours of due time."""
        medication = self.create_daily_medication(["09:00"])

        # Check status at 10:30 (1.5 hours after due time) (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 10, 30))
        medication.update_status(current_time)

        # Should be due, not overdue
        assert medication.current_status == STATE_DUE

    def test_midnight_boundary_edge_cases(self) -> None:
        """Test various edge cases around midnight boundary."""
        medication = self.create_daily_medication(["09:00"])

        # Take dose just before midnight (timezone-aware)
        late_dose = dt_util.as_local(datetime(2025, 8, 6, 23, 59))
        medication.record_dose_taken(late_dose)

        # Check just after midnight (timezone-aware)
        after_midnight = dt_util.as_local(datetime(2025, 8, 7, 0, 1))
        medication.update_status(after_midnight)

        # Should be not_due (new day, not yet time for next dose)
        assert medication.current_status == STATE_NOT_DUE

    def test_skipped_dose_priority_over_taken(self) -> None:
        """Test that recently skipped doses take priority over taken status."""
        medication = self.create_daily_medication(["09:00"])

        # Take dose yesterday (timezone-aware)
        yesterday = dt_util.as_local(datetime(2025, 8, 6, 9, 15))
        medication.record_dose_taken(yesterday)

        # Skip dose today (timezone-aware)
        today_skip = dt_util.as_local(datetime(2025, 8, 7, 9, 30))
        medication.record_dose_skipped(today_skip)

        # Check current status (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 10, 0))
        medication.update_status(current_time)

        # Should show as skipped (most recent action today)
        assert medication.current_status == STATE_SKIPPED

        # Verify next_due is set correctly after skipping - should be tomorrow at scheduled time
        expected_next_due = dt_util.as_local(datetime(2025, 8, 8, 9, 0))
        assert medication.next_due == expected_next_due

    def test_daily_medication_next_due_after_skip(self) -> None:
        """Test that next_due is correctly calculated after skipping daily medication doses."""
        medication = self.create_daily_medication(
            ["09:00", "21:00"]
        )  # Morning and evening doses

        # Test 1: Skip morning dose - next_due should be evening dose same day
        morning_skip = dt_util.as_local(datetime(2025, 8, 7, 9, 30))
        medication.record_dose_skipped(morning_skip)

        # Check status and next_due after skipping morning dose
        after_morning_skip = dt_util.as_local(datetime(2025, 8, 7, 10, 0))
        medication.update_status(after_morning_skip)
        assert medication.current_status == STATE_SKIPPED

        # Next due should be evening dose today
        expected_evening_due = dt_util.as_local(datetime(2025, 8, 7, 21, 0))
        assert medication.next_due == expected_evening_due

        # Test 2: Take evening dose - next_due should move to tomorrow morning
        evening_taken = dt_util.as_local(datetime(2025, 8, 7, 21, 15))
        medication.record_dose_taken(evening_taken)

        after_evening_taken = dt_util.as_local(datetime(2025, 8, 7, 22, 0))
        medication.update_status(after_evening_taken)
        assert medication.current_status == STATE_TAKEN

        # Next due should be tomorrow morning
        expected_tomorrow_morning = dt_util.as_local(datetime(2025, 8, 8, 9, 0))
        assert medication.next_due == expected_tomorrow_morning

        # Test 3: Skip both doses in one day - next_due should advance to next day
        medication_single = self.create_daily_medication(["09:00"])

        today_skip = dt_util.as_local(datetime(2025, 8, 7, 9, 30))
        medication_single.record_dose_skipped(today_skip)

        after_skip = dt_util.as_local(datetime(2025, 8, 7, 12, 0))
        medication_single.update_status(after_skip)
        assert medication_single.current_status == STATE_SKIPPED

        # Next due should be tomorrow at scheduled time
        expected_next_day = dt_util.as_local(datetime(2025, 8, 8, 9, 0))
        assert medication_single.next_due == expected_next_day

    def test_timezone_aware_calculation(self) -> None:
        """Test that timezone-aware datetimes are handled correctly."""
        medication = self.create_daily_medication(["09:00"])

        # Create timezone-aware datetimes
        yesterday_aware = dt_util.as_local(datetime(2025, 8, 6, 9, 30))
        today_aware = dt_util.as_local(datetime(2025, 8, 7, 8, 0))

        medication.record_dose_taken(yesterday_aware)
        medication.update_status(today_aware)

        # Should be not_due despite being timezone-aware
        assert medication.current_status == STATE_NOT_DUE


class TestNonDailyMedicationStatusCalculation:
    """Test medication status calculation for non-daily frequencies."""

    def test_weekly_medication_taken_status(self) -> None:
        """Test weekly medication status calculation."""
        med_data = MedicationData(
            name="Weekly Med",
            dosage="1 pill",
            frequency=FREQUENCY_WEEKLY,
            times=["09:00"],
        )
        medication = MedicationEntry("weekly_med", med_data)

        # Take dose (timezone-aware)
        taken_time = dt_util.as_local(datetime(2025, 8, 1, 9, 15))
        medication.record_dose_taken(taken_time)

        # Check 3 days later (still within week) (timezone-aware)
        check_time = dt_util.as_local(datetime(2025, 8, 4, 10, 0))
        medication.update_status(check_time)

        # Should still be taken (within weekly interval)
        assert medication.current_status == STATE_TAKEN

        # Check after a week (timezone-aware)
        check_time = dt_util.as_local(datetime(2025, 8, 8, 10, 0))
        medication.update_status(check_time)

        # Should be due again
        assert medication.current_status == STATE_DUE

    def test_monthly_medication_taken_status(self) -> None:
        """Test monthly medication status calculation."""
        med_data = MedicationData(
            name="Monthly Med",
            dosage="1 pill",
            frequency=FREQUENCY_MONTHLY,
            times=["09:00"],
        )
        medication = MedicationEntry("monthly_med", med_data)

        # Take dose (timezone-aware)
        taken_time = dt_util.as_local(datetime(2025, 8, 1, 9, 15))
        medication.record_dose_taken(taken_time)

        # Check 2 weeks later (still within month) (timezone-aware)
        check_time = dt_util.as_local(datetime(2025, 8, 15, 10, 0))
        medication.update_status(check_time)

        # Should still be taken (within monthly interval)
        assert medication.current_status == STATE_TAKEN

    def test_monthly_medication_next_due_after_skip(self) -> None:
        """Test that next_due is correctly calculated after skipping monthly medication doses."""
        med_data = MedicationData(
            name="Monthly Med",
            dosage="1 pill",
            frequency=FREQUENCY_MONTHLY,
            times=["09:00"],
        )
        medication = MedicationEntry("monthly_med", med_data)

        # Take first dose on August 1st
        first_dose = dt_util.as_local(datetime(2025, 8, 1, 9, 15))
        medication.record_dose_taken(first_dose)

        # Status should be taken initially
        check_after_first = dt_util.as_local(datetime(2025, 8, 15, 10, 0))
        medication.update_status(check_after_first)
        assert medication.current_status == STATE_TAKEN

        # Skip the next monthly dose (September 1st) - using scheduled time for skip
        skip_time = dt_util.as_local(
            datetime(2025, 9, 1, 9, 15)
        )  # Same time as taken dose
        medication.record_dose_skipped(skip_time)

        # Check status after skipping
        after_skip = dt_util.as_local(datetime(2025, 9, 1, 12, 0))
        medication.update_status(after_skip)
        assert medication.current_status == STATE_SKIPPED

        # Verify next_due is set to next month (October) at a reasonable time
        # The exact calculation may vary, but it should be in October
        assert medication.next_due is not None
        next_due_date = dt_util.as_local(medication.next_due).date()
        assert next_due_date.year == 2025
        assert next_due_date.month == 10  # Should advance to October

    def test_as_needed_medication_always_not_due(self) -> None:
        """Test as-needed medication always shows as not_due."""
        med_data = MedicationData(
            name="As Needed Med",
            dosage="1 pill",
            frequency=FREQUENCY_AS_NEEDED,
            times=[],
        )
        medication = MedicationEntry("as_needed_med", med_data)

        # Check status without any doses (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 10, 0))
        medication.update_status(current_time)

        assert medication.current_status == STATE_NOT_DUE

        # Take a dose
        medication.record_dose_taken(current_time)

        # Should still be not_due
        medication.update_status(current_time)
        assert medication.current_status == STATE_NOT_DUE

    def test_weekly_medication_with_start_date_scheduling(self) -> None:
        """Test weekly medication scheduling with start_date.

        The next due should initially be the first dose time on the start_date.
        When the med is skipped or taken, the next_due should be the next closest
        due date in the future at the dose time.
        """
        # Create weekly medication starting on Monday (Aug 4, 2025) at 10:00 AM
        start_date = dt_util.as_local(datetime(2025, 8, 4))  # Monday
        med_data = MedicationData(
            name="Weekly Vitamin",
            dosage="1 tablet",
            frequency=FREQUENCY_WEEKLY,
            times=["10:00"],
            start_date=start_date,
        )
        medication = MedicationEntry("weekly_vitamin", med_data)

        # Test 1: Before start date - should be not_due
        before_start = dt_util.as_local(datetime(2025, 8, 3, 15, 0))  # Sunday before
        medication.update_status(before_start)
        assert medication.current_status == STATE_NOT_DUE
        assert medication.next_due is None

        # Test 2: On start date before dose time - should be not_due with next_due set
        start_day_early = dt_util.as_local(datetime(2025, 8, 4, 8, 0))  # Monday 8:00 AM
        medication.update_status(start_day_early)
        assert medication.current_status == STATE_NOT_DUE
        expected_first_due = dt_util.as_local(datetime(2025, 8, 4, 10, 0))
        assert medication.next_due == expected_first_due

        # Test 3: At dose time on start date - should be due
        first_dose_time = dt_util.as_local(
            datetime(2025, 8, 4, 10, 0)
        )  # Monday 10:00 AM
        medication.update_status(first_dose_time)
        assert medication.current_status == STATE_DUE

        # Test 4: Take the first dose
        dose_taken_time = dt_util.as_local(
            datetime(2025, 8, 4, 10, 30)
        )  # Monday 10:30 AM
        medication.record_dose_taken(dose_taken_time)
        medication.update_status(dose_taken_time)
        assert medication.current_status == STATE_TAKEN
        assert medication.last_taken == dose_taken_time

        # Test 5: Check next_due is set to next week (7 days later)
        expected_next_due = dt_util.as_local(
            datetime(2025, 8, 11, 10, 0)
        )  # Next Monday 10:00 AM
        assert medication.next_due == expected_next_due

        # Test 6: Check status during the week - should remain taken
        mid_week = dt_util.as_local(datetime(2025, 8, 7, 15, 0))  # Thursday
        medication.update_status(mid_week)
        assert medication.current_status == STATE_TAKEN

        # Test 7: At next dose time (second week) - should be due again
        second_dose_time = dt_util.as_local(
            datetime(2025, 8, 11, 10, 0)
        )  # Next Monday 10:00 AM
        medication.update_status(second_dose_time)
        assert medication.current_status == STATE_DUE

        # Test 8: Skip the second dose
        skip_time = dt_util.as_local(datetime(2025, 8, 11, 11, 0))  # Monday 11:00 AM
        medication.record_dose_skipped(skip_time)
        medication.update_status(skip_time)
        assert medication.current_status == STATE_SKIPPED

        # Test 9: Check next_due is set to third week after skipping
        expected_third_due = dt_util.as_local(
            datetime(2025, 8, 18, 10, 0)
        )  # Third Monday 10:00 AM
        assert medication.next_due == expected_third_due

        # Test 10: Check status between skip and next due - should remain skipped
        between_skip_and_next = dt_util.as_local(datetime(2025, 8, 15, 12, 0))  # Friday
        medication.update_status(between_skip_and_next)
        assert medication.current_status == STATE_SKIPPED

        # Test 11: At third dose time - should be due (skipped status should not persist to next dose)
        third_dose_time = dt_util.as_local(
            datetime(2025, 8, 18, 10, 0)
        )  # Third Monday 10:00 AM
        medication.update_status(third_dose_time)
        assert medication.current_status == STATE_DUE

        # Test 12: Take third dose late
        late_third_dose = dt_util.as_local(
            datetime(2025, 8, 18, 14, 30)
        )  # Monday 2:30 PM
        medication.record_dose_taken(late_third_dose)
        medication.update_status(late_third_dose)
        assert medication.current_status == STATE_TAKEN

        # Test 13: Verify next_due is correctly set to fourth week
        expected_fourth_due = dt_util.as_local(
            datetime(2025, 8, 25, 10, 0)
        )  # Fourth Monday 10:00 AM
        assert medication.next_due == expected_fourth_due

        # Test 14: Verify dose history contains all actions
        assert len(medication.dose_history) == 3  # taken, skipped, taken
        assert medication.dose_history[0].taken is True  # First dose taken
        assert medication.dose_history[1].taken is False  # Second dose skipped
        assert medication.dose_history[2].taken is True  # Third dose taken


class TestMedicationDataSerialization:
    """Test medication data serialization and deserialization."""

    def test_medication_data_to_dict(self) -> None:
        """Test MedicationData serialization to dictionary."""
        med_data = MedicationData(
            name="Test Med",
            dosage="1 pill",
            frequency=FREQUENCY_DAILY,
            times=["09:00", "21:00"],
            start_date=dt_util.as_local(datetime(2025, 8, 1)),
            end_date=dt_util.as_local(datetime(2025, 8, 31)),
            notes="Test notes",
        )

        result = med_data.to_dict()

        assert result["name"] == "Test Med"
        assert result["dosage"] == "1 pill"
        assert result["frequency"] == FREQUENCY_DAILY
        assert result["times"] == ["09:00", "21:00"]
        # The exact string format depends on timezone but should contain the date
        assert "2025-08-01" in result["start_date"]
        assert "2025-08-31" in result["end_date"]
        assert result["notes"] == "Test notes"

    def test_medication_data_from_dict(self) -> None:
        """Test MedicationData deserialization from dictionary."""
        data = {
            "name": "Test Med",
            "dosage": "1 pill",
            "frequency": FREQUENCY_DAILY,
            "times": ["09:00", "21:00"],
            "start_date": "2025-08-01T00:00:00",
            "end_date": "2025-08-31T00:00:00",
            "notes": "Test notes",
        }

        med_data = MedicationData.from_dict(data)

        assert med_data.name == "Test Med"
        assert med_data.dosage == "1 pill"
        assert med_data.frequency == FREQUENCY_DAILY
        assert med_data.times == ["09:00", "21:00"]
        assert isinstance(med_data.start_date, datetime)
        assert isinstance(med_data.end_date, datetime)
        # Should be timezone-aware after deserialization
        assert med_data.start_date.tzinfo is not None
        assert med_data.end_date.tzinfo is not None
        assert med_data.notes == "Test notes"

    def test_dose_record_serialization(self) -> None:
        """Test DoseRecord serialization and deserialization."""
        timestamp = dt_util.as_local(datetime(2025, 8, 7, 9, 15))
        record = DoseRecord(timestamp=timestamp, taken=True, notes="Test notes")

        # Test to_dict
        result = record.to_dict()
        # The timestamp should be serialized as ISO string
        assert "2025-08-07T09:15:00" in result["timestamp"]
        assert result["taken"] is True
        assert result["notes"] == "Test notes"

        # Test from_dict
        restored = DoseRecord.from_dict(result)
        # Both should be timezone-aware and represent the same moment
        assert restored.timestamp.tzinfo is not None
        assert timestamp.tzinfo is not None
        # Compare as UTC to avoid timezone display differences
        assert restored.timestamp.astimezone(dt_util.UTC) == timestamp.astimezone(
            dt_util.UTC
        )
        assert restored.taken is True
        assert restored.notes == "Test notes"

    def test_medication_entry_serialization(self) -> None:
        """Test MedicationEntry serialization and deserialization."""
        med_data = MedicationData(
            name="Test Med",
            dosage="1 pill",
            frequency=FREQUENCY_DAILY,
            times=["09:00"],
        )

        medication = MedicationEntry("test_id", med_data)

        # Add some dose history (timezone-aware)
        dose_time = dt_util.as_local(datetime(2025, 8, 7, 9, 15))
        medication.record_dose_taken(dose_time)

        # Test to_dict
        result = medication.to_dict()
        assert result["id"] == "test_id"
        assert result["device_id"] == "medication_test_id"
        assert result["data"]["name"] == "Test Med"
        assert len(result["dose_history"]) == 1

        # Test from_dict
        restored = MedicationEntry.from_dict(result)
        assert restored.id == "test_id"
        assert restored.device_id == "medication_test_id"
        assert restored.data.name == "Test Med"
        assert len(restored.dose_history) == 1
        assert restored.dose_history[0].taken is True


class TestMedicationDateRanges:
    """Test medication active date range handling."""

    def test_medication_before_start_date(self) -> None:
        """Test medication shows not_due before start date."""
        med_data = MedicationData(
            name="Future Med",
            dosage="1 pill",
            frequency=FREQUENCY_DAILY,
            times=["09:00"],
            start_date=dt_util.as_local(datetime(2025, 8, 10)),  # Future start date
        )
        medication = MedicationEntry("future_med", med_data)

        # Check before start date (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 5, 10, 0))
        medication.update_status(current_time)

        assert medication.current_status == STATE_NOT_DUE

    def test_medication_after_end_date(self) -> None:
        """Test medication shows not_due after end date."""
        med_data = MedicationData(
            name="Expired Med",
            dosage="1 pill",
            frequency=FREQUENCY_DAILY,
            times=["09:00"],
            end_date=dt_util.as_local(datetime(2025, 8, 5)),  # Past end date
        )
        medication = MedicationEntry("expired_med", med_data)

        # Check after end date (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 10, 10, 0))
        medication.update_status(current_time)

        assert medication.current_status == STATE_NOT_DUE

    def test_medication_within_date_range(self) -> None:
        """Test medication functions normally within date range."""
        med_data = MedicationData(
            name="Active Med",
            dosage="1 pill",
            frequency=FREQUENCY_DAILY,
            times=["09:00"],
            start_date=dt_util.as_local(datetime(2025, 8, 1)),
            end_date=dt_util.as_local(datetime(2025, 8, 31)),
        )
        medication = MedicationEntry("active_med", med_data)

        # Check within date range at due time (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        medication.update_status(current_time)

        assert medication.current_status == STATE_DUE


class TestMedicationHelperMethods:
    """Test medication helper methods."""

    def test_was_taken_today_method(self) -> None:
        """Test the _was_taken_today helper method."""
        medication = MedicationEntry(
            "test",
            MedicationData(
                name="Test", dosage="1", frequency=FREQUENCY_DAILY, times=["09:00"]
            ),
        )

        # Test same day (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 15, 0))
        taken_time = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        assert medication._was_taken_today(current_time, taken_time) is True

        # Test different day (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 15, 0))
        taken_time = dt_util.as_local(datetime(2025, 8, 6, 9, 0))
        assert medication._was_taken_today(current_time, taken_time) is False

        # Test edge case: just after midnight (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 0, 1))
        taken_time = dt_util.as_local(datetime(2025, 8, 6, 23, 59))
        assert medication._was_taken_today(current_time, taken_time) is False

    def test_adherence_rate_calculation(self) -> None:
        """Test adherence rate calculation."""
        medication = MedicationEntry(
            "test",
            MedicationData(
                name="Test", dosage="1", frequency=FREQUENCY_DAILY, times=["09:00"]
            ),
        )

        # No doses - should be 0%
        assert medication.adherence_rate == 0.0

        # Add some doses (timezone-aware)
        medication.record_dose_taken(dt_util.as_local(datetime(2025, 8, 1, 9, 0)))
        medication.record_dose_taken(dt_util.as_local(datetime(2025, 8, 2, 9, 0)))
        medication.record_dose_skipped(dt_util.as_local(datetime(2025, 8, 3, 9, 0)))

        # 2 out of 3 taken = 66.67%
        assert abs(medication.adherence_rate - 66.66666666666667) < 0.01

    def test_missed_doses_count(self) -> None:
        """Test missed doses count."""
        medication = MedicationEntry(
            "test",
            MedicationData(
                name="Test", dosage="1", frequency=FREQUENCY_DAILY, times=["09:00"]
            ),
        )

        # No doses - should be 0
        assert medication.missed_doses == 0

        # Add doses (timezone-aware)
        medication.record_dose_taken(dt_util.as_local(datetime(2025, 8, 1, 9, 0)))
        medication.record_dose_skipped(dt_util.as_local(datetime(2025, 8, 2, 9, 0)))
        medication.record_dose_skipped(dt_util.as_local(datetime(2025, 8, 3, 9, 0)))

        # 2 missed doses
        assert medication.missed_doses == 2


class TestEventCallbacks:
    """Test medication event callbacks."""

    def test_state_change_event_fired(self) -> None:
        """Test that state change events are fired correctly."""
        callback_mock = Mock()
        medication = MedicationEntry(
            "test",
            MedicationData(
                name="Test", dosage="1", frequency=FREQUENCY_DAILY, times=["09:00"]
            ),
            event_callback=callback_mock,
        )

        # Change status should fire event (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 9, 0))
        medication.update_status(current_time)

        # Should have fired event for status change
        assert callback_mock.called

        # Check event data
        call_args = callback_mock.call_args
        event_type, event_data = call_args[0]

        assert "medication_id" in event_data
        assert "old_status" in event_data
        assert "new_status" in event_data
        assert event_data["medication_id"] == "test"

    def test_no_event_when_status_unchanged(self) -> None:
        """Test that no event is fired when status doesn't change."""
        callback_mock = Mock()
        medication = MedicationEntry(
            "test",
            MedicationData(
                name="Test", dosage="1", frequency=FREQUENCY_DAILY, times=["09:00"]
            ),
            event_callback=callback_mock,
        )

        # Set initial status (timezone-aware)
        current_time = dt_util.as_local(datetime(2025, 8, 7, 8, 0))  # Before due time
        medication.update_status(current_time)

        # Reset mock
        callback_mock.reset_mock()

        # Update with same status
        medication.update_status(current_time)

        # Should not fire event for unchanged status
        assert not callback_mock.called
