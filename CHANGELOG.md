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