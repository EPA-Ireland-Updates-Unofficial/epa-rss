#!/usr/bin/env python3
"""
Export compliance records to daily CSV files for a given date range, including associated licence profile info.
Usage:
    python export_compliance_csv.py --start YYYY-MM-DD --end YYYY-MM-DD [--db epa_ireland.db]
"""
import argparse
import sqlite3
import csv
from datetime import datetime, timedelta
import os

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)

def main():
    parser = argparse.ArgumentParser(description="Export daily compliance records to CSV.")
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--db', default='epa_ireland.db', help='Path to SQLite DB')
    parser.add_argument('--outdir', default='.', help='Directory to save CSV files')
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    for day in daterange(start_date, end_date):
        day_str = day.strftime("%Y-%m-%d")
        print(f"Exporting records for {day_str}...")
        
        # Query compliance records with this date
        cursor.execute('''
            SELECT cr.*, lp.*
            FROM compliance_records cr
            LEFT JOIN licence_profiles lp ON cr.profile_id = lp.licenceprofileid
            WHERE cr.date = ?
        ''', (day_str,))
        rows = cursor.fetchall()
        if not rows:
            print(f"  No records found for {day_str}.")
            continue

        # Prepare output CSV
        out_path = os.path.join(args.outdir, f"compliance_records_{day_str}.csv")
        with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Dynamically get all column names from both tables, excluding duplicate id columns
            fieldnames = [col for col in rows[0].keys() if col != 'id']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                # Convert sqlite3.Row to dict
                writer.writerow({k: row[k] for k in fieldnames})
        print(f"  Wrote {len(rows)} records to {out_path}")

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
