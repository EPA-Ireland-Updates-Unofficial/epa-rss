#!/bin/bash

# Change to the project directory (CRITICAL for relative paths)
cd /home/conor/gitwork/epa_ireland_scraper

# Absolute path to the virtual environment
VENV_PATH="/home/conor/gitwork/epa_ireland_scraper/venv"

# Absolute path to the Python script
SCRIPT_PATH="/home/conor/gitwork/epa_ireland_scraper/scraper.py"

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

# Run the Python script
python "$SCRIPT_PATH"

# Run the export script for today's date
TODAY=$(date +%Y-%m-%d)
python export_to_csv.py "$TODAY"

# Optional: deactivate venv (not required in cron, but for clarity)
deactivate


