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

# Optional: deactivate venv (not required in cron, but for clarity)
deactivate


