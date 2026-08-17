#!/bin/bash
APP_DIR="/home/pedulyco/public_html/alpha.zainalmultazam.com"
PYTHON_BIN="/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/bin/python"
UVICORN_BIN="/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/bin/uvicorn"
PORT=8089

cd "$APP_DIR" || exit 1

# Check if already running on port
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -z "$PID" ]; then
    nohup "$UVICORN_BIN" app.main:app --host 127.0.0.1 --port $PORT --workers 1 </dev/null > "$APP_DIR/tmp/uvicorn.log" 2>&1 &
    sleep 1
    echo "Alpha Server started on port $PORT"
else
    echo "Alpha Server already running (PID: $PID)"
fi
