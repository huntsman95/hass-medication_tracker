v1.4.2
- BUGFIX: Fixed incorrect "taken" status for not_due medications (regression of bug fixed in 1.3.0)
- BUGFIX: Implemented correct logic for weekly and monthly medications. Before they were basically unusable as I battled bugs with daily meds like crazy.
- NOTE: Unit tests on model.py are now being used to validate changes to the codebase before pushing a release so we should see less regressions.

v1.4.1
- BUGFIX: Fixed bug introduced in v1.3.1 where dose taken in overdue state was not triggering status sensor to change to "taken" status

v1.4.0
- FEATURE: Added dose history calendar to track taken and skipped doses (does not record "missed" doses)

v1.3.1
- BUGFIX: Fixed incorrect next_due calculation for missed medications (due/overdue) when reloading integration or modifying medication

v1.3.0
- FEATURE: Now emits events. See EVENTS.md
- BUGFIX: Resolved medications showing as "Taken" even though they aren't yet due for the day.
- BUGFIX: Resolved an issue where modifying the dose time of a medication would not trigger a recalculation of next_due which resulted in inconsistent sensor states.
- BUGFIX: Weekly/Monthly Next Due Calculation: Updated the _calculate_weekly_next_due and _calculate_monthly_next_due methods in models.py to use the dynamic self.last_taken property instead of the cached self._last_taken value, ensuring correct calculations after Home Assistant reloads.
- BUGFIX: Panel Date Field Population: Added the _formatDateForInput helper method in the JavaScript panel to properly convert date/datetime values from the backend into the YYYY-MM-DD format expected by HTML date input fields.
- Coordinator.py Lint Fixes
  - Import compliance: Changed device registry import from direct function import to namespace import
    - from homeassistant.helpers.device_registry import async_get as async_get_device_registry → from homeassistant.helpers import device_registry as dr
    - Updated function calls from async_get_device_registry(self.hass) to dr.async_get(self.hass)
    - Resolves Pylint W7425 (hass-helper-namespace-import)
  - Type annotations: Added proper type specifications to Callable types
  - Callable → Callable[..., Any] for _entity_creation_callbacks and register_entity_creation_callback
  - Code structure: Removed unnecessary else clause after raise statement in _async_update_data

  - Eliminates unreachable code after exception handling
  - Performance optimization: Changed list to set for membership testing
    - ["sensor", "binary_sensor", "button"] → {"sensor", "binary_sensor", "button"}
    - Improves lookup performance from O(n) to O(1)
  - Code formatting: Removed trailing whitespace from blank lines
    - Complies with PEP 8 formatting standards

v1.2.4
- Fixed bug introduced with v1.2.3 which marked all taken medication as overdue.

v1.2.3
- Fixed "skipped" state not properly taking effect immediately
- Fixed UI panel delays. Now responds to HASS Websocket updates instead of polling.

v1.2.2
- Fixed timezone handling with `Start Date` and `End Date`

v1.2.1
- Added optional datetime parameter to take/skip service calls to accurately record dose time if recording happens in the future after taking a medication.

- Known Bugs:
    - "Taking" or "Skipping" a medication in the past - prior to your most recent dose - will set your most recent dose to that past time due to the ordering in local storage. This will be addressed in a future release by sorting JSON objects first before processing.

v1.2.0
- Use UUID's as medication ID's to avoid sensor re-use on delete/add of new medications

v1.1.0
- Fixed a bug where reloading the integration would not reregister services effectively breaking it until a HASS restart
- Fixed a bug where removing and re-adding the integration would not reregister the UI panel
- Fixed a bug which would allow multiple instances of this integration to be configured
- Some UI changes in the panel to fix hover colors

v1.0.0
- Initial release