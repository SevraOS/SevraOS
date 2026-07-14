#!/bin/bash
xset s off -dpms
xset s noblank

# Wait a couple seconds for the backend service to fully bind to the port
sleep 2

# Launch the browser directly to the dashboard
exec chromium --kiosk --no-sandbox --disable-infobars --no-first-run --window-position=0,0 http://127.0.0.1:8000/
