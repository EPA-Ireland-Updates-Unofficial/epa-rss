#!/usr/bin/env python3
"""
Standalone CSV generator for EPA Ireland data.
Exports documents created in the past N days to a single CSV file.
Only includes documents not already present in previous CSVs.
"""
import sqlite3
import csv
import os
import sys
from datetime import datetime, timezone, timedelta

# Configuration
DB_PATH = 'epa_ireland.db'
OUTPUT_DIR = os.path.join('output', 'csv', 'daily')
DEFAULT_DAYS_BACK = 4

# Mapping from document_type to URL segment for constructing LEAP URLs
TYPE_SEGMENT_MAP = {
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


def get_previously_exported_documents(days_back):
    """Get a set of document URLs that have been exported in recent CSVs.
    
    Args:
        days_back: Number of days to look back for existing CSVs
        
    Returns:
        set: Set of document URLs that have already been exported
    """
    exported_docs = set()
    today = datetime.now(timezone.utc).date()
    
    # Calculate date range to check (go back extra day to be safe)
    start_date = today - timedelta(days=days_back + 1)
    
    # Walk through relevant date directories only
    current_date = start_date
    while current_date <= today:
        year = current_date.strftime("%Y")
        month = current_date.strftime("%m")
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Build the expected CSV path
        csv_path = os.path.join(OUTPUT_DIR, year, month, f"{date_str}.csv")
        
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    csv_reader = csv.reader(f)
                    # Read header to find document_url column index
                    header = next(csv_reader, None)
                    if header and 'document_url' in header:
                        doc_url_index = header.index('document_url')
                        # Read document URLs from the correct column
                        for row in csv_reader:
                            if len(row) > doc_url_index:
                                doc_url = row[doc_url_index].strip()
                                if doc_url:
                                    exported_docs.add(doc_url)
            except Exception as e:
                print(f"Warning: Could not read {csv_path}: {e}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    return exported_docs

def generate_recent_documents_csv(target_date, days_back=DEFAULT_DAYS_BACK):
    """Generate a CSV file containing documents from the past N days.
    
    Args:
        target_date: Date string in YYYY-MM-DD format for the output filename
        days_back: Number of days to look back for documents
        
    Returns:
        str: Path to the generated CSV file, or None if no documents found
    """
    try:
        # Parse the target date for the output filename
        date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        
        # Create output directory structure
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        output_dir = os.path.join(OUTPUT_DIR, year, month)
        os.makedirs(output_dir, exist_ok=True)
        
        # Output filename
        filename = os.path.join(output_dir, f"{target_date}.csv")
        
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get documents that were already exported in recent CSVs
        exported_docs = get_previously_exported_documents(days_back)
        
        # Calculate date range for the query
        end_date = date_obj + timedelta(days=1)  # Include the target date
        start_date = end_date - timedelta(days=days_back)
        
        # Get documents created in the date range that haven't been exported
        cursor.execute("""
            SELECT 
                lp.name as licence_profile_name,
                d.document_type,
                d.title,
                d.leap_url,
                d.document_date,
                cr.status as compliance_status,
                cr.date as compliance_date,
                d.document_url,
                d.metadata_json,
                lp.profilenumber,
                cr.licenceprofileid
            FROM compliance_documents d
            JOIN compliance_records cr ON d.compliance_id = cr.compliancerecord_id
            LEFT JOIN licence_profiles lp ON cr.licenceprofileid = lp.licenceprofileid
            WHERE d.document_date >= ? 
              AND d.document_date < ?
              AND d.document_url NOT IN (""" + 
              ",".join(["?"] * len(exported_docs)) + """)
            ORDER BY d.document_date DESC, d.document_url
        """, [str(start_date), str(end_date)] + list(exported_docs))
        
        documents = [dict(row) for row in cursor.fetchall()]

        # Function to sanitize text fields for CSV output
        def sanitize_csv_text(text):
            """Remove line breaks, carriage returns, and other problematic characters from text."""
            if not text:
                return text
            
            # Convert to string and strip whitespace
            text = str(text).strip()
            
            # Replace line breaks and carriage returns with spaces
            text = text.replace('\n', ' ').replace('\r', ' ')
            
            # Replace multiple consecutive spaces with single space
            import re
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()

        # Fix blank titles for Complaint and Incident documents using subject from metadata_json
        import json
        for doc in documents:
            if (
                doc.get("document_type") in ("Complaint", "Incident") and
                (doc.get("title") is None or str(doc.get("title")).strip() == "")
            ):
                meta_raw = doc.get("metadata_json")
                subject = None
                if meta_raw:
                    try:
                        outer = json.loads(meta_raw)
                        # The LEAP API stores another JSON string in the "metadata" field for Complaints
                        if isinstance(outer, dict):
                            inner_raw = outer.get("metadata")
                            if inner_raw:
                                try:
                                    inner = json.loads(inner_raw)
                                    subject = inner.get("subject")
                                except json.JSONDecodeError:
                                    # If inner is not valid JSON, treat it as plain string
                                    subject = None
                            # Fallback – some older records may store subject at top level
                            subject = subject or outer.get("subject")
                    except json.JSONDecodeError:
                        pass
                if subject:
                    doc["title"] = sanitize_csv_text(subject)

        # Remove metadata_json from output.  Ensure leap_url present; compute only if still missing.
        from urllib.parse import urlparse, parse_qs
        for doc in documents:
            doc.pop("metadata_json", None)
            if doc.get("leap_url"):
                continue  # already populated by DB
            # Fallback computation for legacy rows (should not normally occur)
            seg = TYPE_SEGMENT_MAP.get(doc.get("document_type"), "return")
            raw_url = (doc.get("document_url") or "").rstrip("/")
            parsed = urlparse(raw_url)
            if parsed.query:
                qs = parse_qs(parsed.query)
                guid = next(iter(qs.values()), [""])[0]
            else:
                guid = parsed.path.rstrip("/").split("/")[-1] if parsed.path else ""
            profilenumber = doc.get("profilenumber") or ""
            if guid and profilenumber:
                doc["leap_url"] = f"https://leap.epa.ie/licence-profile/{profilenumber}/compliance/{seg}/{guid}"
        
        # Sanitize all text fields that might contain line breaks or other problematic characters
        for doc in documents:
            # Sanitize title (most important for CSV integrity)
            if doc.get("title"):
                doc["title"] = sanitize_csv_text(doc["title"])
            
            # Sanitize licence_profile_name in case it has line breaks
            if doc.get("licence_profile_name"):
                doc["licence_profile_name"] = sanitize_csv_text(doc["licence_profile_name"])
        
        if not documents:
            print(f"No new documents found from the past {days_back} days.")
            return None
            
        # Build column headers with leap_url after title and document_url last
        all_keys = list(documents[0].keys())
        desired_order = [
            "licence_profile_name",
            "document_type",
            "title",
            "leap_url",
            "document_date",
            "compliance_status",
            "compliance_date",
            "profilenumber",
            "licenceprofileid",
            "document_url",
        ]
        headers = [k for k in desired_order if k in all_keys] + [k for k in all_keys if k not in desired_order]
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            writer.writerows([[doc[col] for col in headers] for doc in documents])
        
        print(f"Exported {len(documents)} new documents to {filename}")
        return filename
        
    except ValueError as e:
        print(f"Invalid date format. Please use YYYY-MM-DD format: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Export EPA documents from the past N days to a CSV file.')
    parser.add_argument('date', help='Target date for the output file (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS_BACK,
                      help=f'Number of days to look back for documents (default: {DEFAULT_DAYS_BACK})')
    
    args = parser.parse_args()
    
    result = generate_recent_documents_csv(args.date, args.days)
    if not result:
        sys.exit(1)
