#!/usr/bin/env python3
"""
Database migration and initialization script for EPA Ireland scraper.
Run this to initialize or migrate your database schema.
"""
import sqlite3
import sys
import os

def check_and_add_columns(conn):
    """Check for and add any missing columns to existing tables."""
    cursor = conn.cursor()
    
    # Check for and add exported tracking columns to compliance_documents
    cursor.execute("""
        SELECT name FROM pragma_table_info('compliance_documents')
        WHERE name IN ('exported', 'export_date')
    """)
    existing_columns = {row[0] for row in cursor.fetchall()}
    
    if 'exported' not in existing_columns:
        print("Adding 'exported' column to compliance_documents table...")
        cursor.execute("""
            ALTER TABLE compliance_documents
            ADD COLUMN exported BOOLEAN DEFAULT 0
        """)
        print("✓ Added 'exported' column")
    
    if 'export_date' not in existing_columns:
        print("Adding 'export_date' column to compliance_documents table...")
        cursor.execute("""
            ALTER TABLE compliance_documents
            ADD COLUMN export_date TEXT
        """)
        print("✓ Added 'export_date' column")
    
    conn.commit()

def create_tables(conn):
    cursor = conn.cursor()
    # Compliance records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compliancerecord_id TEXT UNIQUE,
            type TEXT,
            reference TEXT,
            subject TEXT,
            status TEXT,
            date TEXT,
            licence_id TEXT,
            profile_id TEXT,
            related_compliance_recordid TEXT,
            licenceregno TEXT,
            profilenumber TEXT,
            last_checked TEXT,
            last_updated TEXT,
            FOREIGN KEY (profile_id) REFERENCES licence_profiles (licenceprofileid)
        )
    """)
    # Compliance documents table with export tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compliance_id TEXT,
            document_type TEXT,
            document_url TEXT UNIQUE,
            title TEXT,
            description TEXT,
            submission_date TEXT,
            status TEXT,
            metadata JSON,
            last_checked TEXT,
            last_updated TEXT,
            exported BOOLEAN DEFAULT 0,
            export_date TEXT,
            FOREIGN KEY (compliance_id) REFERENCES compliance_records (compliancerecord_id)
        )
    """)
    # Licence profiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licence_profiles (
            licenceprofileid TEXT PRIMARY KEY,
            name TEXT,
            profilenumber TEXT,
            activelicencetype TEXT,
            activelicenceregno TEXT,
            county TEXT,
            town TEXT,
            organisationname TEXT,
            url TEXT,
            last_checked TIMESTAMP,
            last_updated TIMESTAMP
        )
    """)
    # Add any missing columns to existing tables
    check_and_add_columns(conn)
    
    conn.commit()
    print("✓ All tables created or verified.")
    print("✓ Database schema is up to date.")

def main():
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    else:
        db_file = "epa_ireland.db"
    
    if not os.path.exists(db_file):
        print(f"Creating new database: {db_file}")
    else:
        print(f"Updating existing database: {db_file}")
    
    try:
        conn = sqlite3.connect(db_file)
        create_tables(conn)
        print(f"✓ Database '{db_file}' is ready.")
        return True
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
