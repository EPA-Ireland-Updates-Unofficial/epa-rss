#!/usr/bin/env python3
"""One-off utility to populate the `leap_url` column for existing rows
in the `compliance_documents` table.

Run this once after upgrading the database schema.  It is idempotent –
rows that already possess a non-blank `leap_url` are skipped.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import Dict
from urllib.parse import urlparse, parse_qs

from tqdm import tqdm

DB_PATH = "epa_ireland.db"

# Mapping from document_type to URL segment for constructing LEAP URLs
TYPE_SEGMENT_MAP: Dict[str, str] = {
    "Monitoring Returns": "return",
    "Annual Environmental Report": "return",
    "Requests for Approval and Site Reports": "return",
    "Site Updates/Notifications": "return",
    "Site Closure and Surrender": "return",
    "Site Visit": "sitevisit",
    "Non Compliance": "non-compliance",
    "Incident": "incident",
    "Complaint": "complaint",
    "Compliance Investigation": "investigation",
    "EPA Initiated Correspondence": "epa-correspondence",
}


def extract_guid(document_url: str) -> str | None:
    """Return LEAP GUID/id from an existing document_url."""
    if not document_url:
        return None
    parsed = urlparse(document_url.rstrip("/"))
    if parsed.query:
        qs = parse_qs(parsed.query)
        # take first query parameter value (lr_id, incident_id, etc.)
        val_list = next(iter(qs.values()), [""])
        return val_list[0] if val_list else None
    # Otherwise use last path segment
    return parsed.path.rstrip("/").split("/")[-1] if parsed.path else None


def compute_leap_url(profilenumber: str | None, document_type: str | None, document_url: str) -> str | None:
    if not profilenumber:
        return None
    seg = TYPE_SEGMENT_MAP.get(document_type or "", "return")
    guid = extract_guid(document_url)
    if guid:
        return f"https://leap.epa.ie/licence-profile/{profilenumber}/compliance/{seg}/{guid}"
    return None


def ensure_leap_column(conn: sqlite3.Connection) -> None:
    """Add leap_url column to compliance_documents if it is missing (older DBs)."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(compliance_documents)")
    cols = {row[1] for row in cur.fetchall()}
    if "leap_url" not in cols:
        print("Adding missing leap_url column to compliance_documents …")
        cur.execute("ALTER TABLE compliance_documents ADD COLUMN leap_url TEXT")
        conn.commit()


def backfill(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Back-fill missing leap_url values.

    Returns number of rows updated.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT d.document_url,
               d.document_type,
               d.rowid,  -- internal rowid for fast updates
               lp.profilenumber
        FROM compliance_documents d
        JOIN compliance_records cr ON d.compliance_id = cr.compliancerecord_id
        LEFT JOIN licence_profiles lp ON cr.licenceprofileid = lp.licenceprofileid
        WHERE (d.leap_url IS NULL OR d.leap_url = '')
        """
    )
    rows = cur.fetchall()
    updates = []
    for row in tqdm(rows, desc="Computing leap_url"):
        doc_url, doc_type, rowid, profilenumber = row
        leap = compute_leap_url(profilenumber, doc_type, doc_url)
        if leap:
            updates.append((leap, rowid))
    if not updates:
        print("All rows already have leap_url populated.")
        return 0

    print(f"Updating {len(updates)} rows…")
    if dry_run:
        print("Dry-run mode active – no database changes made.")
        return len(updates)

    cur.executemany("UPDATE compliance_documents SET leap_url = ? WHERE rowid = ?", updates)
    conn.commit()
    return len(updates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate missing leap_url values in compliance_documents table.")
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite database (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes, just report how many rows would be updated")
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(args.db)
    except sqlite3.Error as e:
        print(f"Cannot open database {args.db}: {e}")
        sys.exit(1)

    try:
        ensure_leap_column(conn)
        updated = backfill(conn, dry_run=args.dry_run)
        print(f"Back-fill complete. Rows updated: {updated}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
