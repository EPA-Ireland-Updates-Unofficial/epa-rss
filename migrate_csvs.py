#!/usr/bin/env python3

import os
import shutil
from datetime import datetime

def migrate_csvs():
    """Migrate CSV files from the old flat structure to the new YYYY/MM structure."""
    source_dir = os.path.join("output", "csv", "daily")
    
    # Check if source directory exists
    if not os.path.exists(source_dir):
        print(f"Source directory not found: {source_dir}")
        return
    
    # Get all CSV files in the source directory
    csv_files = [f for f in os.listdir(source_dir) if f.endswith('.csv') and f[0].isdigit()]
    
    if not csv_files:
        print("No CSV files found to migrate.")
        return
    
    migrated_count = 0
    
    for filename in csv_files:
        try:
            # Extract date from filename (format: YYYY-MM-DD.csv)
            date_str = filename.split('.')[0]
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Create target directory structure: output/csv/daily/YYYY/MM
            year = date_obj.strftime('%Y')
            month = date_obj.strftime('%m')
            target_dir = os.path.join(source_dir, year, month)
            os.makedirs(target_dir, exist_ok=True)
            
            # Define source and target paths
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(target_dir, filename)
            
            # Move the file
            if os.path.exists(target_path):
                print(f"Skipping {filename} - already exists in target location")
            else:
                shutil.move(source_path, target_path)
                print(f"Moved {filename} to {target_dir}/")
                migrated_count += 1
                
        except (ValueError, IndexError) as e:
            print(f"Skipping {filename} - invalid date format")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"\nMigration complete. Moved {migrated_count} files.")

if __name__ == "__main__":
    migrate_csvs()
