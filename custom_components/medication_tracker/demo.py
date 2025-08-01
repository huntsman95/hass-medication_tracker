"""Demo script showing how to use the Medication Tracker integration services."""

# Example service calls for testing the medication tracker

# 1. Add a new medication
# This should automatically create entities without needing to reload the integration
ADD_MEDICATION_SERVICE_CALL = {
    "service": "medication_tracker.add_medication",
    "data": {
        "name": "Vitamin D",
        "dosage": "1000 IU",
        "frequency": "daily",
        "times": ["09:00"],
        "notes": "Take with breakfast for better absorption",
    },
}

# 2. Add another medication with multiple daily doses
ADD_MEDICATION_TWICE_DAILY = {
    "service": "medication_tracker.add_medication",
    "data": {
        "name": "Blood Pressure Medication",
        "dosage": "5mg",
        "frequency": "daily",
        "times": ["08:00", "20:00"],
        "notes": "Take with food",
    },
}

# 3. Take a medication (after you know the medication_id)
TAKE_MEDICATION_SERVICE_CALL = {
    "service": "medication_tracker.take_medication",
    "data": {
        "medication_id": "med_1"  # Replace with actual ID
    },
}

# 4. Skip a medication
SKIP_MEDICATION_SERVICE_CALL = {
    "service": "medication_tracker.skip_medication",
    "data": {
        "medication_id": "med_1"  # Replace with actual ID
    },
}

# 5. Remove a medication (this should also remove all its entities)
REMOVE_MEDICATION_SERVICE_CALL = {
    "service": "medication_tracker.remove_medication",
    "data": {
        "medication_id": "med_1"  # Replace with actual ID
    },
}

# Expected entities that should be created for each medication:
# - sensor.{medication_name}_status
# - sensor.{medication_name}_adherence
# - binary_sensor.{medication_name}_due
# - button.take_{medication_name}
# - button.skip_{medication_name}

# Example automation that uses the entities:
MEDICATION_REMINDER_AUTOMATION = """
automation:
  - id: medication_due_reminder
    alias: "Medication Due Reminder"
    description: "Send notification when any medication is due"
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.vitamin_d_due
          - binary_sensor.blood_pressure_medication_due
        to: "on"
    action:
      - service: notify.persistent_notification
        data:
          title: "💊 Medication Reminder"
          message: >
            Time to take your {{ trigger.to_state.attributes.medication_name }}!
            Dosage: {{ trigger.to_state.attributes.dosage }}
          data:
            actions:
              - action: "TAKE_MED_{{ trigger.entity_id.split('_')[:-1] | join('_') }}"
                title: "✅ Mark as Taken"
              - action: "SKIP_MED_{{ trigger.entity_id.split('_')[:-1] | join('_') }}"
                title: "⏭️ Skip Dose"

  - id: medication_adherence_tracking
    alias: "Low Medication Adherence Alert"
    description: "Alert when medication adherence drops below 80%"
    trigger:
      - platform: numeric_state
        entity_id:
          - sensor.vitamin_d_adherence
          - sensor.blood_pressure_medication_adherence
        below: 80
    action:
      - service: notify.persistent_notification
        data:
          title: "⚠️ Low Medication Adherence"
          message: >
            Your adherence for {{ trigger.to_state.attributes.medication_name }}
            is {{ trigger.to_state.state }}%. Consider setting up more reminders.
"""

# Testing Steps:
# 1. Install the integration through Home Assistant UI
# 2. Call the add_medication service to create medications
# 3. Verify that entities are created immediately (no restart needed)
# 4. Test taking/skipping medications
# 5. Test removing medications and verify entities are cleaned up
# 6. Check that the coordinator properly saves/loads data across restarts

print("Medication Tracker Demo - Service calls ready for testing!")
print("Copy the service calls above to test the dynamic entity creation.")
