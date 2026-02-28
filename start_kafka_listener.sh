#!/bin/bash

# virtual environment path
VENV_PATH="ntpc_reporting_engine_venv"
PYTHON_SCRIPT="kafka_listener.py"


# Check if the virtual environment exists
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "Activated virtual environment: $VENV_PATH"
else
    echo "Failed to activate environment: $VENV_PATH not found."
    exit 1
fi

# Function to handle termination signals.
cleanup() {
    local pid=$1
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "Terminating... $pid"
        kill "$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
        echo "Terminated."
    else
        echo "Process $pid is not running."
    fi
}

trap 'cleanup $PYTHON_PID' SIGTERM SIGINT EXIT

# Start Kafka listener in the background
python "$PYTHON_SCRIPT" & #>> "$LOG_FILE" 2>&1 &
PYTHON_PID=$!

# Wait for background process to finish
wait "$PYTHON_PID"
