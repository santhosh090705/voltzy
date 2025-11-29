# TODO: Add Charging Mode Functionality

## Completed Tasks
- [x] Add simulated latitude and longitude to device_simulator.py
- [x] Include lat/lng in API payload
- [x] Add Google Maps button to dashboard header
- [x] Style the maps button with CSS
- [x] Implement JavaScript to enable button always (not dependent on location data)
- [x] Add click handler to open Google Maps with EV stations search (location-specific if available, general search otherwise)
- [x] Modify device_simulator.py to handle keyboard input and mode switching
- [x] Add /api/mode endpoint in app.py for dashboard toggle
- [x] Add charging toggle button to dashboard.html
- [x] Update simulator logic for charging mode (negative current, SoC increase)

## Pending Tasks
- [x] Test the functionality

## Summary
Added a "Find EV Stations" button to the dashboard that opens Google Maps with a search for nearby EV charging stations. The button is enabled immediately and uses the current vehicle location if available, otherwise performs a general search.
