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
