# Medication Tracker Calendar

The Medication Tracker integration now includes a calendar component that creates a calendar entity called `calendar.medication_tracker_dose_taken`.

## Features

### Calendar Entity
- **Entity ID**: `calendar.medication_tracker_dose_taken`
- **Name**: "Medication Tracker Dose Taken"
- **Purpose**: Displays dose history for all medications as calendar events

### Calendar Events
Each dose record (taken or skipped) appears as a calendar event with:

- **Duration**: 5 minutes starting at the time the dose was recorded
- **Summary**:
  - ✅ Taken: [Medication Name] ([Dosage])
  - ❌ Skipped: [Medication Name] ([Dosage])
- **Description**: Detailed information including:
  - Medication name and dosage
  - Status (Taken/Skipped)
  - Time taken/skipped
  - Notes (if any)
  - Frequency information

### Event Details
Example event details:
```
Summary: ✅ Taken: Aspirin (100mg)

Description:
Medication: Aspirin
Dosage: 100mg
Status: Taken
Time: 9:15 AM
Notes: Taken with breakfast
Frequency: daily
```

## Usage

### In Home Assistant Calendar
- View all medication doses in the standard Home Assistant calendar interface
- Filter by date ranges
- See detailed information about each dose
- Track adherence patterns visually

### Integration with Automations
The calendar can be used in automations to:
- Generate adherence reports
- Send notifications about missed doses
- Create statistical dashboards
- Export dose history data

### Calendar Integration
The calendar automatically:
- Updates when new doses are recorded
- Shows historical dose data
- Syncs with the coordinator for real-time updates
- Maintains proper timezone handling

## Technical Implementation

- **Platform**: `calendar.py`
- **Entity Class**: `MedicationTrackerCalendar`
- **Data Source**: Medication coordinator dose history
- **Event Generation**: Dynamic based on dose records within requested date range
- **Unique IDs**: Generated using domain, medication ID, and timestamp

## Benefits

1. **Visual Tracking**: See medication adherence patterns at a glance
2. **Historical Review**: Easy access to past dose records
3. **Integration Ready**: Works with all Home Assistant calendar features
4. **Automated Updates**: Syncs automatically with dose recordings
5. **Detailed Information**: Rich event descriptions with all relevant details

This calendar component provides a comprehensive view of medication adherence history integrated seamlessly into Home Assistant's calendar system.
