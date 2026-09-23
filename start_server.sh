#!/bin/bash
APP_DIR="/home/pedulyco/public_html/alpha.zainalmultazam.com"
PYTHON_BIN="/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/bin/python"
UVICORN_BIN="/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/bin/uvicorn"
PORT=8089
PID_FILE="$APP_DIR/tmp/uvicorn.pid"

mkdir -p "$APP_DIR/tmp"
cd "$APP_DIR" || exit 1

FORCE_RESTART=0
if [ "$1" == "--restart" ] || [ "$1" == "-r" ] || [ "$1" == "force" ]; then
    FORCE_RESTART=1
fi

# Check if process is already alive and responding
if [ $FORCE_RESTART -eq 0 ] && [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:$PORT/health" 2>/dev/null)
        if [ "$HTTP_CODE" == "200" ]; then
            # Server is healthy, keep running smoothly
            exit 0
        fi
    fi
fi

# Kill old PID if exists
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
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
