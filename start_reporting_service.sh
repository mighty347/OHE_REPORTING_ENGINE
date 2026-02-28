#!/bin/bash

set -e  # Exit on error

# Get the present working directory
SCRIPT_DIR="$(pwd)"
LOGS_DIR="$SCRIPT_DIR/proc_logs"
PID_FILE="$LOGS_DIR/pids.txt"
MAX_LOG_SIZE=10485760  # 10MB max size for each log file


# Check if LOGS_DIR exists, if not, create it
if [ ! -d "$LOGS_DIR" ]; then
    mkdir -p "$LOGS_DIR"
    echo "Created directory: $LOGS_DIR"
fi


# Clear the PID file before starting
> "$PID_FILE"

# List to store PIDs
PIDS=()

# Function to truncate log file if it exceeds max size
truncate_log() {
    local log_file=$1
    if [[ -f "$log_file" && $(stat --format=%s "$log_file") -gt $MAX_LOG_SIZE ]]; then
        echo "Truncating $log_file..." > "$log_file"
    fi
}

cleanup() {
    local triggered_by=$1
    echo -e "\nTerminating all background processes..."
    echo -e "\tTriggered by : $triggered_by"
    echo -e "\tKilling pids : ${PIDS[@]}"

    for pid in "${PIDS[@]}"; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "\tTerminating... $pid"
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
            echo -e "\tTerminated : $pid"
        else
            echo -e "\tProcess $pid is not running."
        fi
    done
}

# Trap process teminating signals and call cleanup
trap 'cleanup "SIGTERM"' SIGTERM
trap 'cleanup "SIGINT"' SIGINT
trap 'cleanup "EXIT"' EXIT


echo "Starting all scripts in parallel from $SCRIPT_DIR..."

# Run scripts in the background, log output, and store PIDs
for script in start_redis_server.sh start_celery_worker.sh start_kafka_listener.sh; do
    LOG_FILE="$LOGS_DIR/${script%.sh}.log"
    
    # Ensure log file exists
    touch "$LOG_FILE"
    
    "$SCRIPT_DIR/$script" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo "$script -> $PID" >> "$PID_FILE"
    
    # Monitor log file size in the background
    while kill -0 $PID 2>/dev/null; do
        truncate_log "$LOG_FILE"
        sleep 60  # Check every 60 seconds
    done &
    PIDS+=("$PID")
done
echo "Started : ${PIDS[@]}"
# Wait for all scripts to complete
wait

echo "All scripts completed."
