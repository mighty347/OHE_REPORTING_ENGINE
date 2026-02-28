#!/bin/bash

# virtual environment path
VENV_PATH="ntpc_reporting_engine_venv"

# Check if the virtual environment exists
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "Activated virtual environment: $VENV_PATH"
else
    echo "Failed to activate environment: $VENV_PATH not found."
    exit 1
fi


# Dev celery worker
# celery -A celery_report_gen worker -l info -Q dev_report_task_queue --pool threads --concurrency 1

# Prod celery worker
celery -A celery_report_gen worker -l info -Q prod_report_task_queue --pool threads --concurrency 1

# Deactivate the virtual environment
deactivate