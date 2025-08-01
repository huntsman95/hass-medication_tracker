# Medication Tracker Integration

A comprehensive Home Assistant custom integration for tracking medications, setting reminders, and monitoring adherence with **device-based organization** and a **web-based management panel**.

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository to HACS as a custom repository:
   - Go to HACS > Integrations
   - Click the three dots in the upper right corner
   - Select "Custom repositories"
   - Add the URL of this repository and select "Integration" as the category
3. Click "Install" when the integration appears in HACS
4. Restart Home Assistant
5. Add the integration via the Home Assistant UI (Configuration > Integrations > Add Integration)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=huntsman95&repository=hass-medication_tracker&category=Integration)

### Manual Installation

1. Download the latest release from the GitHub repository
2. Extract the contents to your Home Assistant configuration directory under `custom_components/ha_medication_tracker`
3. Restart Home Assistant
4. Add the integration via the Home Assistant UI (Configuration > Integrations > Add Integration)

## Configuration

The integration is configured through the Home Assistant UI. After installation, go to Configuration > Integrations and add the "Medication Tracker" integration.

## ✨ Key Features

- **Interactive Web Panel**: Dedicated web interface for easy medication management
- **Device-Based Organization**: Each medication creates its own device with all related entities grouped together
- **Dynamic Entity Management**: Entities are created/removed automatically when medications are added/removed - no restart required!
- **Comprehensive Medication Management**: Add, edit, remove, and track multiple medications via services and web UI
- **Real-time Status Monitoring**: Live status updates (due, taken, overdue, not due, skipped) with automatic refresh
- **Timezone-Aware Scheduling**: Proper timezone handling for accurate medication timing
- **Adherence Tracking**: Monitor medication adherence rates and missed doses
- **Flexible Scheduling**: Support for daily, weekly, monthly, and as-needed medications
- **Multiple Daily Doses**: Support for medications taken multiple times per day
- **Complete History**: Track all taken and skipped doses with timestamps
- **Skip Functionality**: Mark medications as skipped with proper status tracking
- **Automation Ready**: Binary sensors for creating automations and alerts
- **Persistent Storage**: Data survives Home Assistant restarts with proper data consistency

## 🌐 Web Management Panel

The integration includes a dedicated web panel accessible at `/medication_tracker` for easy medication management:

### Panel Features:
- **Real-time Updates**: Automatically refreshes every 30 seconds and on entity state changes
- **Manual Refresh**: Click the refresh button for immediate updates
- **Add Medications**: User-friendly form with time pickers and date selection
- **Edit Medications**: Modify existing medications without removing and re-adding
- **Visual Status**: Color-coded medication cards showing current status
- **Take/Skip Actions**: Quick action buttons for each medication
- **Responsive Design**: Works on desktop and mobile devices

### Accessing the Panel:
1. Add "Medication Tracker" to your sidebar via Settings → Dashboards → Add to sidebar
2. Navigate directly to `http://your-home-assistant:8123/medication_tracker`
3. Panel automatically persists after Home Assistant restarts

## 🔧 How Device-Based Organization Works

This integration implements a modern device-based approach:

1. **Adding Medications**: When you call `medication_tracker.add_medication`, a new device is created
2. **Device Contains All Entities**: Each medication device contains:
   - Status sensor
   - Adherence sensor
   - Due alert binary sensor
   - Take medication button
   - Skip medication button
3. **Organized Dashboard**: All entities for a medication are grouped under its device
4. **Easy Management**: Find medications easily in the device registry
5. **Clean Removal**: When removing a medication, the entire device and all entities are cleaned up

## 📅 Date Range Support

The integration supports optional start and end dates for medications:

- **Start Date**: Medication tracking begins on this date. Before the start date, the medication status will be "not due"
- **End Date**: Medication tracking ends on this date. After the end date, the medication status will be "not due"
- **No Dates**: If no dates are specified, the medication is active indefinitely

### Use Cases:
- **Antibiotics**: 7-day course with specific start and end dates
- **Seasonal medications**: Allergy medication during spring months
- **Trial periods**: New medications with planned review dates
- **Post-surgery**: Pain medication with defined duration

## Entities Created Per Medication Device

For each medication, a device is created containing:

### Sensors
- **Status Sensor**: Shows current medication status (due, taken, overdue, not_due, skipped)
- **Adherence Sensor**: Shows adherence percentage
- **ID Sensor**: Displays the medication's unique ID for service calls

### Binary Sensors
- **Due Alert**: Triggers when medication is due or overdue (excludes skipped medications)

### Buttons
- **Take Medication**: Mark medication as taken
- **Skip Medication**: Mark medication as skipped

## 🕒 Timezone Handling

The integration properly handles timezones for accurate medication scheduling:
- **Timezone-Aware**: All medication times are interpreted in your Home Assistant timezone
- **DST Support**: Automatically adjusts for daylight saving time changes
- **Consistent Timing**: Medications scheduled for 8:00 AM will always trigger at 8:00 AM local time
- **No UTC Confusion**: Times are never interpreted as UTC, preventing incorrect scheduling

## Services

### `medication_tracker.take_medication`
Mark a medication as taken.

**Parameters:**
- `medication_id`: ID of the medication

### `medication_tracker.skip_medication`
Mark a medication as skipped.

**Parameters:**
- `medication_id`: ID of the medication

### `medication_tracker.add_medication`
Add a new medication to track.

**Parameters:**
- `name`: Medication name
- `dosage`: Dosage information (e.g., "10mg", "2 tablets")
- `frequency`: How often to take (daily, weekly, monthly, as_needed)
- `times`: List of times to take medication (e.g., ["09:00", "21:00"])
- `start_date`: Optional start date (when to begin taking the medication)
- `end_date`: Optional end date (when to stop taking the medication)
- `notes`: Optional notes

### `medication_tracker.update_medication`
Update an existing medication's details.

**Parameters:**
- `medication_id`: ID of the medication to update
- `name`: Updated medication name (optional)
- `dosage`: Updated dosage information (optional)
- `frequency`: Updated frequency (optional)
- `times`: Updated list of times (optional)
- `start_date`: Updated start date (optional)
- `end_date`: Updated end date (optional)
- `notes`: Updated notes (optional)

### `medication_tracker.remove_medication`
Remove a medication from tracking.

**Parameters:**
- `medication_id`: ID of the medication to remove

## Installation

1. Copy the `medication_tracker` folder to your `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Medication Tracker" and add it
5. Access the web panel at `/medication-tracker-panel` or add it to your sidebar

## Configuration

The integration is configured through the UI. No YAML configuration is required.
- **Initial Setup**: Add the integration via Settings → Devices & Services
- **Web Panel**: Automatically available after integration setup
- **Sidebar Access**: Optionally add to sidebar via Settings → Dashboards

## Usage Examples

### Using the Web Panel (Recommended):
1. Navigate to the Medication Tracker panel in your sidebar
2. Click "Add Medication" to add new medications using the friendly form interface
3. Use the edit button on medication cards to modify existing medications
4. Take or skip medications directly from the panel
5. Panel automatically refreshes to show current status

### Add a medication via service call:
```yaml
service: medication_tracker.add_medication
data:
  name: "Vitamin D"
  dosage: "1000 IU"
  frequency: "daily"
  times: ["09:00"]
  start_date: "2025-08-01"  # Optional: start taking on this date
  end_date: "2025-12-31"    # Optional: stop taking on this date
  notes: "Take with breakfast"
```
This creates a "Vitamin D Medication" device with all related entities.

### Update medication details:
```yaml
service: medication_tracker.update_medication
data:
  medication_id: "med_1"
  dosage: "2000 IU"  # Increase dosage
  times: ["09:00", "21:00"]  # Add evening dose
  notes: "Take with breakfast and dinner"
```

### Find your medication ID:
After adding a medication, check the Home Assistant logs for a message like:
```
Added medication Vitamin D with ID med_1
```

### Create automation for medication reminders:
```yaml
automation:
  - id: medication_reminder
    alias: "Medication Reminder"
    trigger:
      - platform: state
        entity_id: binary_sensor.vitamin_d_due
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Time to take your Vitamin D!"
          title: "Medication Reminder"
```

### Create automation for skipped medications:
```yaml
automation:
  - id: medication_skipped_alert
    alias: "Medication Skipped Alert"
    trigger:
      - platform: state
        entity_id: sensor.vitamin_d_status
        to: "skipped"
    action:
      - service: persistent_notification.create
        data:
          message: "Vitamin D was skipped. Consider taking it later if possible."
          title: "Medication Skipped"
```

### Device-based Lovelace card:
```yaml
type: entities
title: Vitamin D Medication
show_header_toggle: false
entities:
  - entity: sensor.vitamin_d_status
  - entity: sensor.vitamin_d_adherence
  - entity: sensor.vitamin_d_id  # Shows the medication ID
  - entity: binary_sensor.vitamin_d_due
  - entity: button.take_vitamin_d
  - entity: button.skip_vitamin_d
```

### Mark medication as taken:
```yaml
service: medication_tracker.take_medication
data:
  medication_id: "med_1"  # Use the ID from the logs
```

### Mark medication as skipped:
```yaml
service: medication_tracker.skip_medication
data:
  medication_id: "med_1"
```

## 🔄 Data Consistency & Updates

The integration implements robust data consistency:
- **No Cached Values**: Status, due times, and last taken are calculated fresh from dose history
- **Real-time Updates**: Coordinator updates every minute for responsive status changes
- **Automatic Refresh**: Web panel refreshes every 30 seconds and on entity state changes
- **Timezone Accuracy**: All times properly handle DST and timezone changes
- **Data Integrity**: Storage only contains persistent data, calculated values are never cached

## Finding Medication IDs

Each medication gets a unique ID like `med_1`, `med_2`, etc. To find the ID:

1. **ID Sensor**: Each medication now has an ID sensor that displays the medication ID directly
2. **Check Home Assistant logs** after adding a medication
3. **Look at entity unique_ids** in Developer Tools > States
4. **Device names** in Settings > Devices & Services show the medication name

## Data Storage

The integration stores medication data in Home Assistant's storage system with proper data separation:

### Persistent Data (Stored):
- Medication details (name, dosage, frequency, times, dates, notes)
- Complete dose history with timestamps and actions (taken/skipped)
- Medication unique IDs and device associations

### Calculated Data (Not Stored):
- Current status (due, taken, overdue, not_due, skipped)
- Next due time
- Last taken time
- Adherence percentages

This separation ensures data consistency - status information is always calculated fresh from the actual dose history, preventing discrepancies between cached and actual data.

## 🛠️ Troubleshooting

### Common Issues:

**Medications showing wrong time:**
- Ensure your Home Assistant timezone is set correctly
- Check that medication times are in 24-hour format (e.g., "09:00", not "9:00 AM")

**Panel not loading:**
- Clear browser cache and refresh
- Check Home Assistant logs for JavaScript errors
- Ensure the integration is properly installed and loaded

**Status not updating:**
- Check coordinator logs for any errors
- Verify entities are being created correctly in Developer Tools → States
- Use the manual refresh button in the panel

**Binary sensor not triggering:**
- Verify the medication is currently due (not skipped, taken, or outside date range)
- Check automation triggers are using the correct entity IDs

### Debug Information:

Enable debug logging by adding to your `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.medication_tracker: debug
```

## 📋 Complete Feature List

### Web Interface:
- ✅ Dedicated management panel
- ✅ Real-time auto-refresh (30s intervals)
- ✅ Manual refresh button with animation
- ✅ Add medication form with validation
- ✅ Edit medication dialog
- ✅ Visual status indicators
- ✅ Quick take/skip actions
- ✅ Responsive mobile design

### Backend Features:
- ✅ Device-based organization
- ✅ Timezone-aware scheduling
- ✅ Multiple dose frequencies
- ✅ Date range support
- ✅ Complete CRUD operations
- ✅ Skip functionality
- ✅ Adherence tracking
- ✅ Real-time status updates
- ✅ Data consistency guarantees
- ✅ Persistent storage
- ✅ Binary sensor automation support
