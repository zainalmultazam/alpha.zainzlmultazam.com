#!/bin/bash
APP_DIR="/home/pedulyco/public_html/alpha.zainalmultazam.com"
PYTHON_BIN="/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/bin/python"
UVICORN_BIN="/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/bin/uvicorn"
PORT=8089
PID_FILE="$APP_DIR/tmp/uvicorn.pid"

mkdir -p "$APP_DIR/tmp"
cd "$APP_DIR" || exit 1

# Kill old PID if exists
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if [ -n "$OLD_PID" ]; then
        kill -9 "$OLD_PID" 2>/dev/null
    fi
    rm -f "$PID_FILE"
fi

nohup "$UVICORN_BIN" app.main:app --host 127.0.0.1 --port $PORT --workers 1 </dev/null > "$APP_DIR/tmp/uvicorn.log" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
sleep 1
echo "Alpha Server started on port $PORT (PID: $NEW_PID)"
