"""Constants for the Medication Tracker integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "medication_tracker"

# Configuration constants
CONF_MEDICATIONS: Final = "medications"
CONF_MEDICATION_NAME: Final = "name"
CONF_DOSAGE: Final = "dosage"
CONF_FREQUENCY: Final = "frequency"
CONF_TIMES: Final = "times"
CONF_START_DATE: Final = "start_date"
CONF_END_DATE: Final = "end_date"
CONF_NOTES: Final = "notes"

# Supply tracking configuration constants
CONF_SUPPLY_TRACKING_ENABLED: Final = "supply_tracking_enabled"
CONF_CURRENT_SUPPLY: Final = "current_supply"
CONF_PILLS_PER_DOSE: Final = "pills_per_dose"
CONF_REFILL_REMINDER_THRESHOLD: Final = "refill_reminder_threshold"
CONF_LAST_REFILL_DATE: Final = "last_refill_date"
CONF_SHOW_REFILL_ON_CALENDAR: Final = "show_refill_on_calendar"

# Frequency options
FREQUENCY_DAILY: Final = "daily"
FREQUENCY_WEEKLY: Final = "weekly"
FREQUENCY_MONTHLY: Final = "monthly"
FREQUENCY_AS_NEEDED: Final = "as_needed"

# Service names
SERVICE_TAKE_MEDICATION: Final = "take_medication"
SERVICE_SKIP_MEDICATION: Final = "skip_medication"
SERVICE_ADD_MEDICATION: Final = "add_medication"
SERVICE_REMOVE_MEDICATION: Final = "remove_medication"
SERVICE_UPDATE_MEDICATION: Final = "update_medication"
SERVICE_REFILL_MEDICATION: Final = "refill_medication"
SERVICE_UPDATE_SUPPLY: Final = "update_supply"

# Attributes
ATTR_MEDICATION_ID: Final = "medication_id"
ATTR_DATETIME: Final = "datetime"
ATTR_DEVICE_ID: Final = "device_id"
ATTR_TAKEN_AT: Final = "taken_at"
ATTR_SKIPPED_AT: Final = "skipped_at"
ATTR_NEXT_DUE: Final = "next_due"
ATTR_LAST_TAKEN: Final = "last_taken"
ATTR_MISSED_DOSES: Final = "missed_doses"
ATTR_ADHERENCE_RATE: Final = "adherence_rate"

# Supply tracking attributes
ATTR_CURRENT_SUPPLY: Final = "current_supply"
ATTR_PILLS_PER_DOSE: Final = "pills_per_dose"
ATTR_REFILL_AMOUNT: Final = "refill_amount"
ATTR_DAYS_REMAINING: Final = "days_remaining"
ATTR_ESTIMATED_REFILL_DATE: Final = "estimated_refill_date"
ATTR_DAILY_CONSUMPTION: Final = "daily_consumption"
ATTR_REFILL_THRESHOLD_DAYS: Final = "refill_threshold_days"

# Device info
DEVICE_MODEL: Final = "Medication Tracker"
DEVICE_MANUFACTURER: Final = "Home Assistant"

# States
STATE_DUE: Final = "due"
STATE_TAKEN: Final = "taken"
STATE_OVERDUE: Final = "overdue"
STATE_NOT_DUE: Final = "not_due"
STATE_SKIPPED: Final = "skipped"

# Events
EVENT_MEDICATION_STATE_CHANGED: Final = "medication_tracker_state_changed"
EVENT_MEDICATION_LOW_SUPPLY: Final = "medication_tracker_low_supply"
