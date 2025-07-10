#!/usr/bin/env python3
"""Fix titles for Complaint documents in the local EPA Ireland SQLite DB.

For each entry in the `compliance_documents` table with:
  • document_type = 'Complaint'
  • (title IS NULL OR title = '')
this script parses the `metadata_json` column and attempts to extract the
`subject` string (nested inside the `metadata` field for modern rows or at the
root level for some older rows). If found, it writes the subject back into the
`title` column.

Usage:
    python3 update_complaint_titles.py [--db epa_ireland.db]

You may wish to run `VACUUM` afterwards to compact the DB.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).with_name("epa_ireland.db")

def extract_subject(meta_raw: str) -> Optional[str]:
    """Attempt to extract the subject string from the `metadata_json` blob."""
    if not meta_raw:
        return None
    try:
        outer = json.loads(meta_raw)
    except json.JSONDecodeError:
        return None

    subject: Optional[str] = None

    if isinstance(outer, dict):
        # Current schema: nested JSON string under `metadata`
        inner_raw = outer.get("metadata")
        if inner_raw:
            try:
                inner = json.loads(inner_raw)
                if isinstance(inner, dict):
                    subject = inner.get("subject")
            except json.JSONDecodeError:
                pass
        # Fallback to top-level subject if present
        subject = subject or outer.get("subject")
    return subject.strip() if subject else None

def main(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Select rows to fix
    cur.execute(
        """
        SELECT document_url, title, metadata_json
        FROM compliance_documents
        WHERE document_type = 'Complaint'
          AND (title IS NULL OR title = '')
        """
    )
    rows = cur.fetchall()
    print(f"Found {len(rows)} complaint documents with blank titles.")

    updated = 0
    for row in rows:
        subject = extract_subject(row["metadata_json"])
        if subject:
            cur.execute(
                """
                UPDATE compliance_documents
                SET title = ?
                WHERE document_url = ?
                """,
                (subject, row["document_url"],),
            )
            updated += 1

    conn.commit()
    conn.close()

    print(f"Updated {updated} rows with extracted subjects.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate title from metadata subject for Complaint documents.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to epa_ireland SQLite database file.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        parser.error(f"Database not found at {db_path}")

    main(db_path)
