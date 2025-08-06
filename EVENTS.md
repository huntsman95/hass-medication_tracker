# Medication Tracker Events

The Medication Tracker integration fires events when medication states change. This allows you to create automations that respond to medication status changes.

## Event: medication_tracker_state_changed

This event is fired whenever a medication's status changes (e.g., from "not_due" to "due", or from "due" to "taken").

### Event Data

The event includes the following data:

- `medication_id`: Unique identifier for the medication
- `device_id`: Device identifier for Home Assistant device registry
- `name`: Name of the medication
- `dosage`: Dosage information
- `frequency`: Frequency (daily, weekly, monthly, as_needed)
- `notes`: Any notes associated with the medication
- `old_status`: Previous status
- `new_status`: New status
- `next_due`: ISO formatted datetime of next due time (or null)
- `last_taken`: ISO formatted datetime of last taken time (or null)
- `missed_doses`: Number of missed doses
- `adherence_rate`: Adherence rate as a percentage

### Status Values

- `not_due`: Medication is not currently due
- `due`: Medication is currently due
- `overdue`: Medication is overdue (more than 2 hours past due time)
- `taken`: Medication has been recently taken
- `skipped`: Medication was skipped

## Example Automation

Here's an example automation that sends a notification when a medication becomes due:

```yaml
automation:
  - alias: "Medication Due Notification"
    trigger:
      - platform: event
        event_type: medication_tracker_state_changed
        event_data:
          new_status: "due"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Medication Due"
          message: "{{ trigger.event.data.name }} ({{ trigger.event.data.dosage }}) is now due"
          data:
            tag: "medication_{{ trigger.event.data.medication_id }}"
```

Another example that tracks when medications are taken:

```yaml
automation:
  - alias: "Medication Taken Tracker"
    trigger:
      - platform: event
        event_type: medication_tracker_state_changed
        event_data:
          new_status: "taken"
    action:
      - service: logbook.log
        data:
          name: "Medication Tracker"
          message: "{{ trigger.event.data.name }} was taken"
          entity_id: "sensor.medication_{{ trigger.event.data.medication_id }}_status"
```

## Developer Usage

If you're developing custom components or scripts that need to listen for medication events, you can listen for the `medication_tracker_state_changed` event:

```python
@callback
def handle_medication_state_change(event):
    """Handle medication state change event."""
    data = event.data
    medication_name = data.get("name")
    old_status = data.get("old_status")
    new_status = data.get("new_status")
    
    _LOGGER.info(
        "Medication %s changed from %s to %s",
        medication_name,
        old_status,
        new_status
    )

hass.bus.async_listen("medication_tracker_state_changed", handle_medication_state_change)
```
