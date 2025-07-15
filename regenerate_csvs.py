#!/usr/bin/env python3
"""
One-off script to regenerate all CSV files from April 1st, 2025 onwards.
This will delete existing CSV files and regenerate them with the fixed deduplication logic.
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta

def regenerate_all_csvs():
    """Regenerate all CSV files from April 1st, 2025 to today."""
    
    # Define the start date
    start_date = datetime(2025, 4, 1).date()
    
    # Get today's date
    today = datetime.now().date()
    
    # Output directory structure
    output_dir = os.path.join('output', 'csv', 'daily')
    
    print(f"Regenerating CSV files from {start_date} to {today}")
    print(f"Output directory: {output_dir}")
    
    # Counter for tracking progress
    total_days = (today - start_date).days + 1
    current_day = 0
    
    # Iterate through each date
    current_date = start_date
    while current_date <= today:
        current_day += 1
        date_str = current_date.strftime("%Y-%m-%d")
        year = current_date.strftime("%Y")
        month = current_date.strftime("%m")
        
        # Build the CSV file path
        csv_path = os.path.join(output_dir, year, month, f"{date_str}.csv")
        
        print(f"\n[{current_day}/{total_days}] Processing {date_str}...")
        
        # Delete existing CSV file if it exists
        if os.path.exists(csv_path):
            try:
                os.remove(csv_path)
                print(f"  Deleted existing file: {csv_path}")
            except Exception as e:
                print(f"  Warning: Could not delete {csv_path}: {e}")
        
        # Run the export_to_csv.py script for this date
        try:
            result = subprocess.run([
                sys.executable, 'export_to_csv.py', date_str
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                print(f"  ✓ Successfully generated CSV for {date_str}")
                if result.stdout.strip():
                    print(f"    {result.stdout.strip()}")
            else:
                print(f"  ✗ Failed to generate CSV for {date_str}")
                if result.stderr.strip():
                    print(f"    Error: {result.stderr.strip()}")
                if result.stdout.strip():
                    print(f"    Output: {result.stdout.strip()}")
        
        except Exception as e:
            print(f"  ✗ Exception while processing {date_str}: {e}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    print(f"\nCompleted processing {total_days} days from {start_date} to {today}")
    print("All CSV files have been regenerated with the fixed deduplication logic.")

if __name__ == '__main__':
    # Confirm before running
    print("This script will:")
    print("1. Delete all existing CSV files from April 1st, 2025 onwards")
    print("2. Regenerate them using the fixed export_to_csv.py script")
    print("3. This may take several minutes depending on the date range")
    
    response = input("\nDo you want to proceed? (y/N): ").strip().lower()
    if response == 'y' or response == 'yes':
        regenerate_all_csvs()
    else:
        print("Operation cancelled.") 