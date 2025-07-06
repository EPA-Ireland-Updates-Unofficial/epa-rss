#!/usr/bin/env python3

import json
import signal
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, ContextManager, Optional, Tuple
import requests
import time
from tqdm import tqdm
import pprint
from dateutil import parser
import csv
import os
import logging
from rss_generator import RSSGenerator

# Helper to parse API date strings safely
def parse_api_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        # Assuming API dates are naive, make them timezone-aware UTC
        # Or treat stored dates as UTC. Let's assume API gives UTC equivalent.
        dt_naive = datetime.fromisoformat(date_str)
        # If the datetime object is naive, assume UTC
        if dt_naive.tzinfo is None or dt_naive.tzinfo.utcoffset(dt_naive) is None:
             return dt_naive.replace(tzinfo=timezone.utc)
        return dt_naive # Already timezone-aware
    except ValueError:
        print(f"Warning: Could not parse date string: {date_str}")
        return None

# Helper to parse API date strings safely (copied/adapted from backfill_dates)
def parse_date_string(date_str):
    """Attempts to parse a date string into a datetime object."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        # Use isoparse for standard ISO 8601 formats, fallback to general parse
        dt = parser.isoparse(date_str)
        # Ensure timezone-aware UTC for consistency if naive
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) # Convert to UTC if timezone-aware but different TZ
    except ValueError:
        try:
            # General parser might handle other formats but can be slower/ambiguous
            dt = parser.parse(date_str)
            # Ensure timezone-aware UTC
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                 return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return None # Ignore parsing errors
    except Exception:
        return None # Catch any other unexpected parsing errors

# Helper to find the newest date within a parsed API response dictionary
def find_newest_date_in_api_response(api_data: dict) -> Optional[str]:
    """ Parses an API response dict, including nested 'metadata', for the newest date. """
    if not isinstance(api_data, dict):
        return None

    possible_dates = []

    # --- Process Outer Dictionary ---    
    for key, value in api_data.items():
        # Skip the nested metadata field itself, handle separately
        # Also skip internal tracking fields (though unlikely in raw API response)
        if key.lower() in ['metadata', 'last_checked', 'last_updated']:
             continue
        
        if isinstance(key, str) and 'date' in key.lower():
            dt = parse_date_string(value)
            if dt:
                possible_dates.append(dt)

    # --- Process Inner Dictionary (if exists) ---
    # API might return nested dict directly or as string - handle both
    inner_metadata = api_data.get('metadata')
    inner_dict_to_process = None

    if isinstance(inner_metadata, dict):
        inner_dict_to_process = inner_metadata
    elif isinstance(inner_metadata, str):
        try:
            parsed_inner = json.loads(inner_metadata)
            if isinstance(parsed_inner, dict):
                inner_dict_to_process = parsed_inner
        except json.JSONDecodeError:
            pass # Ignore if inner JSON string is invalid

    if inner_dict_to_process:
        for key, value in inner_dict_to_process.items():
            # Exclude internal fields here too, just in case
            if isinstance(key, str) and 'date' in key.lower() and key.lower() not in ['last_checked', 'last_updated']:
                dt = parse_date_string(value)
                if dt:
                    possible_dates.append(dt)

    # --- Find Newest Date --- 
    if not possible_dates:
        return None

    try:
        # Find the maximum date among all collected dates
        newest_date = max(possible_dates)
        # Return as ISO 8601 string with timezone
        return newest_date.isoformat()
    except ValueError:
        return None

def signal_handler(signum, frame):
    """Handle interrupt signals by raising a custom exception."""
    print("\nReceived interrupt signal. Cleaning up...")
    raise KeyboardInterrupt

@contextmanager
def transaction(conn) -> ContextManager[sqlite3.Cursor]:
    """Context manager for database transactions. Ensures rollback on error."""
    if conn is None:
        print("Error: Database connection is None. Cannot start transaction.")
        # Raise an exception instead of yielding None to make failure explicit.
        raise sqlite3.OperationalError("Database connection is not available.") 

    cursor = None # Initialize
    try:
        cursor = conn.cursor()
        yield cursor # Yield the created cursor
        # If the code inside the 'with' block completes without exception:
        conn.commit()
    except sqlite3.Error as e:
        # An error occurred either creating the cursor or within the 'with' block
        print(f"\nDatabase Error encountered: {e}")
        print("Rolling back transaction...")
        try:
            conn.rollback()
            print("Rollback successful.")
        except sqlite3.Error as rb_e:
            print(f"Error during rollback attempt: {rb_e}")
        # Re-raise the original exception to signal failure
        raise e 
    except Exception as e: # Catch non-SQLite errors too
        print(f"\nNon-Database Error encountered during transaction: {e}")
        print("Rolling back transaction as a precaution...")
        try:
            conn.rollback()
            print("Rollback successful.")
        except sqlite3.Error as rb_e:
             print(f"Error during rollback attempt: {rb_e}")
        # Re-raise the original exception
        raise e
    finally:
        # Cursor closing is typically handled when the connection is closed.
        # Avoid closing here if the connection persists.
        pass

class EPAScraper:
    """EPA Ireland data scraper with database transaction protection."""
    # Map record types to their API endpoints and parameters
    type_to_endpoint = {
        'Site Updates/Notifications': {
            'endpoint': 'LicenseeReturns/byid',
            'param': 'lr_id'
        },
        'Meeting': {
            'endpoint': 'MeetingCorrespondence/meetingbyid',
            'param': 'meeting_id'
        },
        'Incident': {
            'endpoint': 'Incident/byid',
            'param': 'incident_id'
        },
        'EPA Initiated Correspondence': {
            'endpoint': 'MeetingCorrespondence/epainiciatedcorrespondencebyid',
            'param': 'epainitiatedcorrespondence_id'
        },
        'Annual Environmental Report': {
            'endpoint': 'LicenseeReturns/byid',
            'param': 'lr_id'
        },
        'Monitoring Returns': {
            'endpoint': 'LicenseeReturns/byid',
            'param': 'lr_id'
        },
        'Site Visit': {
            'endpoint': 'SiteVisit/byid',
            'param': 'sv_id'
        },
        'Non Compliance': {
            'endpoint': 'NonCompliance/byid',
            'param': 'nc_id'
        },
        'Enforcement Categorisation and Charges': {
            'endpoint': 'LicenseeReturns/byid',
            'param': 'lr_id'
        },
        'Requests for Approval and Site Reports': {
            'endpoint': 'LicenseeReturns/byid',
            'param': 'lr_id'
        },
        'Site Closure and Surrender': {
            'endpoint': 'LicenseeReturns/byid',
            'param': 'lr_id'
        },
        'Third Party Correspondence': {
            'endpoint': 'MeetingCorrespondence/thirdpartycorrespondencebyid',
            'param': 'thirdpartycorrespondence_id'
        },
        'Complaint': {
            'endpoint': 'Complaint/byid',
            'param': 'complaint_id'
        },
        'Compliance Investigation': {
            'endpoint': 'Ci/byid',
            'param': 'ci_id'
        }
    }

    def __init__(self):
        self.base_url = "https://data.epa.ie/leap/api/v1"
        self.db_path = "epa_ireland.db"
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # Store a date stamp for the current run for CSV naming
        self.run_date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Ensure tables exist on initialization
        self._create_tables()
        self.logger = logging.getLogger(__name__)
        self.run_start_time_utc = None # Added for tracking run start time

    # ---- CSV Logging Helper ----
    def _log_to_csv(self, record_type: str, record_data: Dict[str, Any]):
        """Logs a record to a date-stamped CSV file in a 'csv/daily' subdirectory."""
        # Skip logging for compliance documents and records as per requirements
        if record_type in ['compliance_document', 'compliance_record']:
            return
            
        if not record_data:
            return

        # Define the subdirectory and ensure it exists
        output_dir = os.path.join("output", "csv", "daily")
        os.makedirs(output_dir, exist_ok=True)

        filename = os.path.join(output_dir, f"{self.run_date_stamp}_{record_type.replace(' ', '_').lower()}s.csv")
        
        processed_record_data = {}
        for key, value in record_data.items():
            if isinstance(value, (dict, list)):
                processed_record_data[key] = json.dumps(value) # Serialize complex types
            elif isinstance(value, datetime):
                processed_record_data[key] = value.isoformat() # Ensure datetime is ISO format string
            else:
                processed_record_data[key] = value
        
        fieldnames = list(processed_record_data.keys())
        if not fieldnames: # Avoid writing empty headers or rows
            return

        file_exists = os.path.exists(filename)
        
        try:
            with open(filename, 'a+', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore') # extrasaction='ignore' is safer
                if not file_exists or csvfile.tell() == 0:
                    writer.writeheader()
                writer.writerow(processed_record_data)
        except IOError as e:
            print(f"\nError writing to CSV {filename}: {e}")
        except Exception as e:
            print(f"\nUnexpected error during CSV writing for {filename}: {e}")

    def _generate_rss_feeds(self, document_urls: List[str]):
        """Generate RSS feeds using the RSSGenerator class."""
        try:
            with RSSGenerator(self.db_path) as rss_gen:
                # Generate documents RSS
                if document_urls:
                    rss_gen.generate_daily_documents_rss(
                        output_dir="output",
                        days_back=1
                    )
                
                # Generate CSV listing RSS
                rss_gen.generate_csv_listing_rss(
                    csv_dir=os.path.join("output", "csv", "daily"),
                    output_dir="output",
                    days=10
                )
        except Exception as e:
            print(f"Error generating RSS feeds: {e}")

    # ---- End CSV Logging ----


    def _create_tables(self):
        """Create database tables if they don't already exist."""
        with transaction(self.conn) as cursor:
            # Licence Profiles Table
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
                last_updated TEXT,
                last_checked TEXT
            )
            """)

            # Compliance Records Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_records (
                compliancerecord_id TEXT PRIMARY KEY,
                licenceprofileid TEXT,
                type TEXT,
                title TEXT, 
                status TEXT,
                date TEXT,
                last_updated TEXT,
                last_checked TEXT,
                metadata_json TEXT,
                FOREIGN KEY (licenceprofileid) REFERENCES licence_profiles (licenceprofileid)
            )
            """)
            
            # Compliance Documents Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_documents (
                document_date TEXT,
                document_url TEXT PRIMARY KEY,
                compliance_id TEXT,
                document_id TEXT,
                document_type TEXT,
                title TEXT,
                last_updated TEXT,
                last_checked TEXT,
                metadata_json TEXT,
                exported BOOLEAN DEFAULT 0,
                export_date TEXT,
                FOREIGN KEY (compliance_id) REFERENCES compliance_records (compliancerecord_id)
            )
            """)
        print("Database tables ensured.")

    
        

    def fetch_licence_profiles(self) -> List[Dict[str, Any]]:
        """Fetch all licence profiles from the EPA API."""
        url = f"{self.base_url}/LicenceProfile/list/"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict):
                print(f"Warning: Unexpected API response format for {url}")
                return []

            # Print response info
            print(f"\nResponse data type: {type(data)}")
            print(f"Keys in response: {list(data.keys())}")
            print(f"Total profiles: {len(data.get('list', []))}")
            
            if data.get('list'):
                print(f"Sample profile: {json.dumps(data['list'][0], indent=2)}")
                
            # The API seems to return all profiles at once, no need for pagination
            return data.get('list', [])
        except requests.exceptions.Timeout:
            print(f"Timeout error fetching licence profiles from {url}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching licence profiles from {url}: {e}")
            return []

    def fetch_compliance_data(self, licence_profile_id: str, from_date: str = None, to_date: str = None) -> List[Dict[str, Any]]:
        """Fetch compliance data for a specific licence profile, ensuring uniqueness."""
        # Use a dictionary keyed by compliancerecord_id to store unique records
        unique_records = {}
        
        # Construct URL with query parameters
        url = f"{self.base_url}/ComplianceList/compliancelist/"
        params = {
            'licence_profile_id': licence_profile_id,
            'page': 1,
            'per_page': 250
        }
        if from_date:
            params['date_from'] = from_date
        if to_date:
            params['date_to'] = to_date
        
        try:
            while True:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if not isinstance(data, dict):
                    # If response is not a dict, assume error or unexpected format
                    print(f"Warning: Unexpected response format for {licence_profile_id}, page {params['page']}. Stopping.")
                    break
                    
                records = data.get('list', [])
                # Reliably break the loop ONLY if the API returns an empty list for the current page.
                if not records:
                    break
                
                # Validate that records are for the requested profile
                filtered_records = []
                for record in records:
                    if record.get('profile_id') == licence_profile_id:
                        filtered_records.append(record)
                    else:
                        # Keep the warning, as this indicates unexpected API behavior
                        print(f"Warning: Got record {record.get('compliancerecord_id')} for profile {record.get('profile_id')} while requesting {licence_profile_id}")
                        
                # Add filtered records to the dictionary, automatically handling duplicates
                for record in filtered_records:
                    record_id = record.get('compliancerecord_id')
                    if record_id:
                        unique_records[record_id] = record
                
                # No longer need to check total_count or current_page here
                # Remove the old break condition: 
                # total_count = data.get('count', 0)
                # current_page = params['page']
                # if len(all_records) >= total_count:
                #    break
                    
                params['page'] = params['page'] + 1 # Simplified increment
                time.sleep(0.1)  # Be nice to the API
            
        except requests.exceptions.Timeout:
            print(f"Timeout error fetching compliance data for licence {licence_profile_id} from {url}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching compliance data for licence {licence_profile_id} from {url}: {e}")
            return None
        
        # Return the unique records as a list
        return list(unique_records.values())

    def fetch_document_metadata(self, record_id: str, record_type: str) -> List[Dict[str, Any]]:
        """Fetch metadata for a specific record type."""
        documents = []
        
        # If we don't know how to handle this record type, return empty list
        if record_type not in self.type_to_endpoint:
            return documents
        
        endpoint_info = self.type_to_endpoint[record_type]
        endpoint = endpoint_info['endpoint']
        param = endpoint_info['param']
        
        # Fetch document metadata from the API
        url = f"{self.base_url}/{endpoint}?{param}={record_id}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Create document metadata record
            doc = {
                'compliance_id': record_id,
                'document_type': record_type,
                'document_url': url,
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'submission_date': data.get('date', ''),
                'status': data.get('status', ''),
                'metadata': json.dumps(data)  # Store full response as JSON
            }
            documents.append(doc)
                
            time.sleep(0.1)  # Be nice to the API
                
        except requests.exceptions.Timeout:
            print(f"Timeout error fetching {record_type} metadata for compliance ID {record_id} from {url}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {record_type} metadata for compliance ID {record_id} from {url}: {e}")
            return []
        
        return documents

    def store_licence_profile(self, profile: Dict[str, Any]) -> bool:
        """Store a licence profile in the database if it's new or changed."""
        profile_id = profile.get('licenceprofileid')
        if not profile_id:
            print(f"Warning: Profile missing ID: {profile}")
            return False

        now = datetime.now(timezone.utc).isoformat()
        epoch_datetime_iso = datetime.fromtimestamp(0, timezone.utc).isoformat()
            
        try:
            # Check if profile exists and get its current values, including last_checked
            self.cursor.execute("""
                SELECT licenceprofileid, name, profilenumber, activelicencetype, 
                       activelicenceregno, county, town, organisationname, 
                       url, last_updated, last_checked 
                FROM licence_profiles 
                WHERE licenceprofileid = ?
            """, (profile_id,))
            
            result = self.cursor.fetchone()
            
            current_last_checked = epoch_datetime_iso # Default for new profiles
            if result and result['last_checked']:
                current_last_checked = result['last_checked']
            
            # Prepare data tuple according to the fixed schema order
            data_tuple = (
                profile_id,
                profile.get('name'),
                profile.get('profilenumber'),
                profile.get('activelicencetype'),
                profile.get('activelicenceregno'),
                profile.get('county'),
                profile.get('town'),
                profile.get('organisationname'),
                profile.get('url'),
                now, # last_updated (update always on seeing the profile's metadata)
                current_last_checked  # last_checked (preserve existing or use epoch for new)
            )

            # Use INSERT OR REPLACE with fixed columns
            self.cursor.execute("""
                INSERT OR REPLACE INTO licence_profiles (
                    licenceprofileid, name, profilenumber,
                    activelicencetype, activelicenceregno, county,
                    town, organisationname, url, 
                    last_updated, last_checked 
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data_tuple)
            
            inserted_or_replaced = self.cursor.rowcount > 0
            if inserted_or_replaced:
                self._log_to_csv("licence_profile", profile)
            return inserted_or_replaced
            
        except Exception as e:
            print(f"Error storing profile {profile_id}: {str(e)}")
            print(f"Profile data: {profile}")
            return False

    def store_compliance_record(self, licence_profile_id: str, record: Dict[str, Any]) -> bool:
        """Store a compliance record in the database.
        Returns True if a new record was created, False if it already existed."""
        compliance_id = record.get('compliancerecord_id')
        if not compliance_id:
            return False
            
        record_type = record.get('type')
        if record_type not in self.type_to_endpoint:
            print(f"\nWARNING: Unknown record type encountered: {record_type} for {compliance_id}")
            # Decide whether to skip or attempt to store anyway
            # return False # Option: Skip unknown types
            pass # Option: Attempt to store basic info anyway
            
        now = datetime.now(timezone.utc).isoformat() # Use timezone aware now
        
        # Check if record exists
        self.cursor.execute(
            "SELECT 1 FROM compliance_records WHERE compliancerecord_id = ?",
            (compliance_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            # New record: Prepare data tuple for fixed schema
            data_tuple = (
                compliance_id,
                licence_profile_id,
                record.get('type'),
                record.get('title'),
                record.get('status'),
                record.get('date'),
                now, # last_updated
                now, # last_checked
                json.dumps(record) # Store full record as JSON
            )
            
            try:
                self.cursor.execute("""
                    INSERT INTO compliance_records (
                        compliancerecord_id, licenceprofileid, type, title, 
                        status, date, last_updated, last_checked, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data_tuple)
                # Log the new record
                self._log_to_csv("compliance_record", record)
                return True
            except sqlite3.Error as e:
                print(f"\nError inserting compliance record {compliance_id}: {e}")
                print(f"Record data: {record}")
                raise e 
        else:
            # Existing record: Update last_checked
            # Optionally, could update metadata_json if content comparison shows change
            self.cursor.execute(
                "UPDATE compliance_records SET last_checked = ? WHERE compliancerecord_id = ?",
                (now, compliance_id)
            )
            return False

    def process_licence_profiles(self):
        """Phase 1: Process all licence profiles."""
        print("\nPhase 1: Processing licence profiles...")
        profiles = self.fetch_licence_profiles()
        new_profiles = 0
        now = datetime.now(timezone.utc).isoformat()
        batch_size = 100
        current_batch = []

        for profile in tqdm(profiles, desc="Fetching licence profiles"):
            try:
                profile_id = profile.get('licenceprofileid')
                if not profile_id:
                    continue

                # Check if profile exists and needs update
                self.cursor.execute(
                    "SELECT last_updated FROM licence_profiles WHERE licenceprofileid = ?",
                    (profile_id,)
                )
                result = self.cursor.fetchone()
                
                if not result:
                    # New profile
                    profile['last_checked'] = now
                    profile['last_updated'] = now
                    current_batch.append(profile)
                    new_profiles += 1
                else:
                    # Update last_checked in current transaction
                    current_batch.append({
                        'licenceprofileid': profile_id,
                        'last_checked': now,
                        'update_only': True
                    })

                # Process batch with transaction protection
                if len(current_batch) >= batch_size:
                    with transaction(self.conn) as cursor:
                        for item in current_batch:
                            if item.get('update_only'):
                                cursor.execute(
                                    "UPDATE licence_profiles SET last_checked = ? WHERE licenceprofileid = ?",
                                    (item['last_checked'], item['licenceprofileid'])
                                )
                            else:
                                placeholders = ', '.join(['?' for _ in item])
                                columns = ', '.join(item.keys())
                                cursor.execute(
                                    f"INSERT INTO licence_profiles ({columns}) VALUES ({placeholders})",
                                    list(item.values())
                                )
                    current_batch = []

            except Exception as e:
                print(f"Error processing profile {profile.get('profilenumber', '')}: {str(e)}")
                continue

        # Process any remaining items
        if current_batch:
            with transaction(self.conn) as cursor:
                for item in current_batch:
                    if item.get('update_only'):
                        cursor.execute(
                            "UPDATE licence_profiles SET last_checked = ? WHERE licenceprofileid = ?",
                            (item['last_checked'], item['licenceprofileid'])
                        )
                    else:
                        placeholders = ', '.join(['?' for _ in item])
                        columns = ', '.join(item.keys())
                        cursor.execute(
                            f"INSERT INTO licence_profiles ({columns}) VALUES ({placeholders})",
                            list(item.values())
                        )

        return new_profiles

    def fetch_compliance_records_for_profile(self, profile_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch compliance records for a specific licence profile."""
        # This simply wraps the existing fetch_compliance_data for clarity
        return self.fetch_compliance_data(profile_id)

    def process_compliance_records(self) -> set[str]:
        """Fetch compliance records for each profile, store new/recent ones, 
           and return IDs needing document checks."""
        print("\nPhase 2: Processing compliance records...")
        
        profiles_to_check = []
        with transaction(self.conn) as local_cursor_init:
            local_cursor_init.execute("SELECT licenceprofileid, last_checked FROM licence_profiles")
            profiles_to_check = local_cursor_init.fetchall()

        all_record_ids_seen_in_api = set()
        compliance_ids_needing_doc_check = set()
        profiles_with_new_records = set()
        existing_records_to_update_checked = set()
        profiles_successfully_processed_in_phase2 = set()

        existing_record_ids_in_db = set()
        with transaction(self.conn) as local_cursor_init:
            local_cursor_init.execute("SELECT compliancerecord_id FROM compliance_records")
            for row in local_cursor_init.fetchall():
                existing_record_ids_in_db.add(row[0])

        for profile_id, profile_last_checked_str in tqdm(profiles_to_check, desc="Fetching compliance records"):
            profile_last_checked_dt = parse_api_date(profile_last_checked_str)
            if not profile_last_checked_dt:
                profile_last_checked_dt = datetime.fromtimestamp(0, timezone.utc)

            try:
                records_from_api = self.fetch_compliance_records_for_profile(profile_id)
                
                if records_from_api is None:
                    print(f"\nSkipping profile {profile_id} due to fetch error for its records.")
                    # Do not add to profiles_successfully_processed_in_phase2 as we couldn't check its records
                    continue 

                # If records_from_api is an empty list, it's valid (no records for this profile).
                # The profile was still successfully checked.

                for record in records_from_api: # Loop handles empty list correctly
                    record_id = record.get('compliancerecord_id')
                    if not record_id:
                        print(f"\nWarning: Record missing compliancerecord_id for profile {profile_id}")
                        continue
                        
                    all_record_ids_seen_in_api.add(record_id)
                    is_currently_in_db = record_id in existing_record_ids_in_db
                    record_date_dt = parse_api_date(record.get('date'))

                    process_this_record_for_docs = False
                    if not is_currently_in_db:
                        process_this_record_for_docs = True
                    elif record_date_dt and record_date_dt > profile_last_checked_dt:
                         process_this_record_for_docs = True
                         
                    if process_this_record_for_docs:
                        was_newly_inserted = self.store_compliance_record(profile_id, record)
                        if was_newly_inserted:
                            profiles_with_new_records.add(profile_id)
                            existing_record_ids_in_db.add(record_id)
                        compliance_ids_needing_doc_check.add(record_id)
                    elif is_currently_in_db:
                         existing_records_to_update_checked.add(record_id)
                
                # If we reached here, the profile's records (even if none) were processed without API error for this profile
                profiles_successfully_processed_in_phase2.add(profile_id)

            except Exception as e:
                # This catches errors within the processing of a specific profile's records, 
                # or errors from fetch_compliance_records_for_profile if not caught and returned as None.
                print(f"\nError during processing records for profile {profile_id}: {e}")
                # Decide if this profile should still be considered 'checked'. 
                # If the error was critical for this profile, maybe don't add it to profiles_successfully_processed_in_phase2
                # so its last_checked is not updated, forcing a retry next run.
                # For now, we'll assume if an exception occurs here, we don't update its last_checked.
                continue
        
        # --- Post-Loop Updates --- 
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Update last_checked for licence_profiles that were successfully processed in this phase
        if profiles_successfully_processed_in_phase2:
            print(f"\nUpdating last_checked for {len(profiles_successfully_processed_in_phase2)} licence profiles processed in Phase 2...")
            profile_lc_update_tuples = [(now_iso, pid) for pid in profiles_successfully_processed_in_phase2]
            try:
                self.cursor.executemany(
                    "UPDATE licence_profiles SET last_checked = ? WHERE licenceprofileid = ?",
                    profile_lc_update_tuples
                )
            except sqlite3.Error as e:
                print(f"\nError batch updating licence_profiles last_checked: {e}")

        # 2. Batch update last_checked for existing compliance records seen but not needing doc checks
        if existing_records_to_update_checked:
            print(f"\nUpdating last_checked for {len(existing_records_to_update_checked)} existing compliance records seen...")
            record_lc_update_tuples = [(now_iso, rec_id) for rec_id in existing_records_to_update_checked]
            try:
                self.cursor.executemany(
                    "UPDATE compliance_records SET last_checked = ? WHERE compliancerecord_id = ?",
                    record_lc_update_tuples
                )
            except sqlite3.Error as e:
                print(f"\nError batch updating compliance_records last_checked: {e}")

        # 3. Batch update last_updated for profiles that received genuinely new compliance records
        if profiles_with_new_records:
            print(f"\nUpdating last_updated for {len(profiles_with_new_records)} licence profiles due to new compliance records...")
            profile_lu_update_tuples = [(now_iso, pid) for pid in profiles_with_new_records]
            try:
                self.cursor.executemany(
                    "UPDATE licence_profiles SET last_updated = ? WHERE licenceprofileid = ?",
                    profile_lu_update_tuples
                )
            except sqlite3.Error as e:
                print(f"\nError batch updating licence_profiles last_updated: {e}")

        # Summary for Phase 2
        print(f"\nPhase 2 Summary: Saw {len(all_record_ids_seen_in_api)} unique compliance records via API.")
        print(f"Identified {len(compliance_ids_needing_doc_check)} records needing document checks (new or recent).")
        
        return compliance_ids_needing_doc_check

    # --- Phase 3: Compliance Documents --- #

    def process_compliance_documents(self, processed_compliance_record_ids: List[str]):
        """Phase 3: Process compliance documents for all provided compliance records.
           Updates last_checked for existing documents.
           Inserts new documents with last_updated and last_checked.
           Updates last_updated for parent compliance records and licence profiles if new docs are found.
           Returns the count of newly added documents."""
        print("\nPhase 3: Processing compliance documents...")
        
        if not processed_compliance_record_ids:
            print("No compliance records were processed in Phase 2 to check documents for.")
            return 0
            
        new_documents_count = 0
        now = datetime.now(timezone.utc).isoformat()
        docs_to_insert = []
        docs_to_update_checked = set()
        compliance_records_with_new_docs = set()
        licence_profiles_with_new_docs = set()

        # Step 1: Get all existing document URLs from the database
        print("Fetching existing document URLs...")
        self.cursor.execute("SELECT document_url FROM compliance_documents")
        existing_doc_urls = {row[0] for row in self.cursor.fetchall() if row[0]}
        print(f"Found {len(existing_doc_urls)} existing document records.")

        # Step 2: Get details (type, licence_id) for all compliance records processed in Phase 2
        print(f"Fetching details for {len(processed_compliance_record_ids)} processed compliance records...")
        placeholders = ','.join('?' for _ in processed_compliance_record_ids)
        # Fetch licenceprofileid along with type
        sql = f"""SELECT cr.compliancerecord_id, cr.type, cr.licenceprofileid 
                 FROM compliance_records cr 
                 WHERE cr.compliancerecord_id IN ({placeholders})"""
        # Convert Set to tuple for parameter substitution
        self.cursor.execute(sql, tuple(processed_compliance_record_ids))
        # Store mapping: compliance_id -> (record_type, licence_profile_id)
        compliance_record_details = {row[0]: (row[1], row[2]) for row in self.cursor.fetchall()}
        print(f"Found details for {len(compliance_record_details)} records.")

        # Step 3: Iterate through processed compliance records and fetch/process their documents
        for compliance_id in tqdm(processed_compliance_record_ids, desc="Fetching & Processing Documents"):
            if compliance_id not in compliance_record_details:
                print(f"Warning: Compliance ID {compliance_id} processed in Phase 2 but not found in DB for Phase 3? Skipping.")
                continue
                
            record_type, licence_profile_id = compliance_record_details[compliance_id]
            
            try:
                documents_from_api = self.fetch_document_metadata(compliance_id, record_type)
                
                for doc in documents_from_api:
                    doc_url = doc.get('document_url')
                    if not doc_url:
                        continue # Skip documents without a URL
                        
                    if doc_url not in existing_doc_urls:
                        # NEW document
                        doc_data_for_db = {}

                        # --- Populate fields for DB columns --- 
                        doc_data_for_db['document_date'] = find_newest_date_in_api_response(doc) # Use find_newest_date_in_api_response to get the most relevant date from the doc payload
                        doc_data_for_db['document_url'] = doc_url
                        doc_data_for_db['compliance_id'] = compliance_id
                        doc_data_for_db['document_id'] = doc.get('document_id') # From original API doc
                        doc_data_for_db['document_type'] = doc.get('document_type', record_type) # Use from doc if available, else fallback to parent record_type
                        doc_data_for_db['title'] = doc.get('title') # From original API doc
                        
                        doc_data_for_db['last_checked'] = now
                        doc_data_for_db['last_updated'] = now # Set initial last_updated for new doc
                        
                        # Store the *entire original* API 'doc' object as JSON in metadata_json
                        # This ensures all fields, including 'description' or any others, are preserved.
                        doc_data_for_db['metadata_json'] = json.dumps(doc)
                        
                        # Log the structured document data intended for DB
                        self._log_to_csv("compliance_document", doc_data_for_db)
                        
                        docs_to_insert.append(doc_data_for_db) # Add the structured data to insert list
                        
                        # Mark relevant parent records for update
                        compliance_records_with_new_docs.add(compliance_id)
                        if licence_profile_id: # Ensure licence_profile_id is available
                            licence_profiles_with_new_docs.add(licence_profile_id)
                        
                        # Add to existing_urls immediately to prevent duplicates within this batch run
                        existing_doc_urls.add(doc_url)
                    else:
                        # EXISTING document - mark for last_checked update
                        docs_to_update_checked.add(doc_url)

            except requests.exceptions.RequestException as e:
                print(f"\nError fetching document metadata for {compliance_id}: {e}")
            except Exception as outer_e:
                print(f"\nUnexpected error processing documents for {compliance_id}: {outer_e}")

        # Step 4: Batch insert new documents
        if docs_to_insert:
            print(f"\nInserting {len(docs_to_insert)} new documents...")
            
            # Dynamically get columns from the first dict (assuming all dicts have same keys)
            if docs_to_insert:
                ordered_columns = ['document_date', 'document_url', 'compliance_id', 'document_id', 
                                   'document_type', 'title', 'last_updated', 'last_checked', 'metadata_json']
                column_names = ', '.join(ordered_columns)
                placeholders = ', '.join(['?' for _ in ordered_columns])
                insert_sql = f"INSERT INTO compliance_documents ({column_names}) VALUES ({placeholders})"
                
                print(f"DEBUG: Attempting to execute SQL: {insert_sql}") # ADDED FOR DEBUGGING

                try:
                    insert_tuples = []
                    for d_db_data in docs_to_insert: # d_db_data is one of the doc_data_for_db dicts
                        insert_tuples.append(tuple(d_db_data.get(k) for k in ordered_columns))

                    # SQL statement for batch insert with conflict handling
                    # Ensure column names here exactly match the `ordered_columns` order and table schema
                    sql = f"""
                        INSERT INTO compliance_documents (
                            document_date, document_url, compliance_id, document_id, 
                            document_type, title, last_updated, last_checked, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(document_url) DO UPDATE SET
                            last_checked = excluded.last_checked,
                            title = excluded.title, 
                            document_date = excluded.document_date, 
                            document_type = excluded.document_type,
                            metadata_json = excluded.metadata_json,
                            last_updated = CASE
                                WHEN IFNULL(compliance_documents.title, '') != IFNULL(excluded.title, '') OR
                                     IFNULL(compliance_documents.document_date, '') != IFNULL(excluded.document_date, '') OR
                                     IFNULL(compliance_documents.document_type, '') != IFNULL(excluded.document_type, '') OR
                                     IFNULL(compliance_documents.metadata_json, '') != IFNULL(excluded.metadata_json, '')
                                THEN excluded.last_updated
                                ELSE compliance_documents.last_updated
                            END;
                    """
                    print(f"DEBUG: Attempting to execute SQL with ON CONFLICT: {sql}") # CORRECTED DEBUG
                    with transaction(self.conn) as cursor:
                        cursor.executemany(sql, insert_tuples)
                    # new_documents_count is incremented based on how many were ACTUALLY new vs updated due to conflict
                    # For simplicity, we can count based on SELECT changes() after executemany, or estimate based on len(insert_tuples)
                    # The current logic for new_documents_count relies on earlier checks and might need refinement
                    # if precise count of *newly inserted* vs *updated on conflict* is critical here.
                    # For now, let's assume most in docs_to_insert are new if they passed the initial URL check.
                    new_documents_count += len(insert_tuples) # This counts all attempted inserts/updates via this path
                except sqlite3.Error as e:
                    print(f"\nError during batch insert of documents: {e}")
                    # Log problematic tuples or data for debugging
                    if insert_tuples:
                        print(f"Sample data for failed batch: {insert_tuples[0]}")

            # Step 5: Batch update last_checked for existing documents
            # Remove duplicates before updating
            unique_docs_to_update = list(set(docs_to_update_checked))
            if unique_docs_to_update:
                print(f"\nUpdating last_checked for {len(unique_docs_to_update)} existing documents...")
                update_sql = "UPDATE compliance_documents SET last_checked = ? WHERE document_url = ?"
                update_data = [(now, url) for url in unique_docs_to_update]
                with transaction(self.conn) as cursor:
                    try:
                        cursor.executemany(update_sql, update_data)
                    except sqlite3.Error as e:
                        print(f"\nError during batch update of last_checked: {e}")

        # Step 6: Update last_updated on parent records if new documents were added
        if new_documents_count > 0:
            # Update parent compliance records
            if compliance_records_with_new_docs:
                print(f"\nUpdating last_updated for {len(compliance_records_with_new_docs)} compliance records due to new documents...")
                comp_placeholders = ','.join('?' for _ in compliance_records_with_new_docs)
                comp_update_sql = f"UPDATE compliance_records SET last_updated = ? WHERE compliancerecord_id IN ({comp_placeholders})"
                comp_update_params = [now] + list(compliance_records_with_new_docs)
                with transaction(self.conn) as cursor:
                    cursor.execute(comp_update_sql, comp_update_params)
            
            # Update parent licence profiles
            if licence_profiles_with_new_docs:
                print(f"\nUpdating last_updated for {len(licence_profiles_with_new_docs)} licence profiles due to new documents...")
                prof_placeholders = ','.join('?' for _ in licence_profiles_with_new_docs)
                prof_update_sql = f"UPDATE licence_profiles SET last_updated = ? WHERE licenceprofileid IN ({prof_placeholders})"
                prof_update_params = [now] + list(licence_profiles_with_new_docs)
                with transaction(self.conn) as cursor:
                    cursor.execute(prof_update_sql, prof_update_params)

        print(f"\nPhase 3 completed. Added {new_documents_count} new documents.")
        return new_documents_count

    def _get_truly_recent_document_details(self, recency_months: int) -> Tuple[int, List[str]]:
        """Counts documents that were updated in the current run and have a recent document_date.
           Returns the count and a list of their document_urls.
        """
        if not self.run_start_time_utc:
            self.logger.warning("_get_truly_recent_document_details called before run_start_time_utc was set.")
            return 0, []

        start_time_str = self.run_start_time_utc.strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate the earliest acceptable document_date string ('YYYY-MM-DD')
        # SQLite's date functions are robust here.
        # We compare document_date (which should be 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')
        # with date('now', '-X months').

        query = """
            SELECT document_url 
            FROM compliance_documents
            WHERE last_updated >= ? 
            AND document_date IS NOT NULL
            AND date(document_date) >= date('now', '-' || CAST(? AS TEXT) || ' months')
        """ 
        try:
            self.cursor.execute(query, (start_time_str, recency_months))
            result_urls = [row[0] for row in self.cursor.fetchall()] 
            return len(result_urls), result_urls
        except sqlite3.Error as e:
            self.logger.error(f"SQL error in _get_truly_recent_document_details: {e}")
            return 0, []

    def generate_recent_documents_csv(self, document_urls: List[str]):
        """Generates a CSV file for documents deemed truly recent, using their document_urls.
           Saves to csv/daily/YYYY-MM-DD.csv
           Only includes documents that haven't been exported before.
        """
        if not document_urls:
            self.logger.info("No 'truly recent' documents found to generate CSV.")
            return []

        # Create the output directory if it doesn't exist
        output_dir = os.path.join("csv", "daily")
        os.makedirs(output_dir, exist_ok=True)
        
        # Use today's date in YYYY-MM-DD format for the filename
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = os.path.join(output_dir, f"{date_str}.csv")
        
        # Create a string of placeholders for the IN clause
        placeholders = ','.join(['?'] * len(document_urls))
        
        try:
            # Start a transaction
            with transaction(self.conn) as cursor:
                # First, fetch only unexported documents
                cursor.execute(f"""
                    SELECT * FROM compliance_documents 
                    WHERE document_url IN ({placeholders})
                    AND (exported = 0 OR exported IS NULL)
                """, document_urls)
                
                rows = cursor.fetchall()
                if not rows:
                    self.logger.info("No new documents to export.")
                    return []
                
                # Get column headers
                headers = [desc[0] for desc in cursor.description]
                
                # Write to CSV
                file_exists = os.path.exists(filename)
                with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    if not file_exists or os.path.getsize(filename) == 0:
                        csv_writer.writerow(headers)
                    csv_writer.writerows(rows)
                
                # Get the list of exported document URLs
                exported_urls = [row[headers.index('document_url')] for row in rows]
                
                # Mark documents as exported
                if exported_urls:
                    export_placeholders = ','.join(['?'] * len(exported_urls))
                    cursor.execute(f"""
                        UPDATE compliance_documents 
                        SET exported = 1, 
                            export_date = ?
                        WHERE document_url IN ({export_placeholders})
                    """, [date_str] + exported_urls)
                
                self.logger.info(f"Successfully exported {len(exported_urls)} new documents to {filename}")
                return exported_urls
                
        except sqlite3.Error as e:
            self.logger.error(f"SQL error in generate_recent_documents_csv: {e}")
            raise
        except IOError as e:
            self.logger.error(f"IOError writing CSV {filename}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in generate_recent_documents_csv: {e}")
            raise


    def run(self):
        """Main execution method to scrape and store all data in phases."""
        self.run_start_time_utc = datetime.now(timezone.utc) # Set run start time
        self.logger.info(f"Starting EPA Ireland data scraper at {self.run_start_time_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}...")
        # print("Starting EPA Ireland data scraper...") # Old print

        # Phase 1: Process licence profiles
        # new_profiles_count = self.process_licence_profiles()
        # Temporarily disable phase 1 if focusing on document processing logic
        # self.logger.info("Skipping Phase 1: Licence Profiles for focused testing.")
        # new_profiles_count = 0
        # Instead of skipping, let's ensure it runs unless an error stops it.
        try:
            new_profiles_count = self.process_licence_profiles()
        except Exception as e:
            self.logger.critical(f"CRITICAL ERROR in Phase 1 (Licence Profiles), stopping: {e}", exc_info=True)
            return # Stop execution if phase 1 fails critically

        # Phase 2: Process compliance records
        try:
            processed_compliance_record_ids = self.process_compliance_records()
        except Exception as e:
            self.logger.critical(f"CRITICAL ERROR in Phase 2 (Compliance Records), stopping: {e}", exc_info=True)
            return # Stop execution if phase 2 fails critically

        # Phase 3: Process compliance documents
        try:
            # This count is total documents inserted/updated in the phase, not 'truly recent'.
            _ = self.process_compliance_documents(processed_compliance_record_ids)
        except Exception as e:
            self.logger.critical(f"CRITICAL ERROR in Phase 3 (Compliance Documents), stopping: {e}", exc_info=True)
            return # Stop execution if phase 3 fails critically
        
        # Get count and IDs of 'truly recent' documents for summary and CSV
        # Using default 3 months recency. Make this configurable if needed later.
        truly_recent_doc_count, truly_recent_doc_urls = self._get_truly_recent_document_details(recency_months=3)

        self.logger.info("\nScraping complete!")
        if new_profiles_count is not None:
             self.logger.info(f"New licence profiles: {new_profiles_count}")
        if processed_compliance_record_ids is not None:
            self.logger.info(f"Processed compliance records: {len(processed_compliance_record_ids)}") 
        
        # Updated log for 'truly recent' documents
        self.logger.info(f"Truly recent documents (updated this run, doc_date < 3 months): {truly_recent_doc_count}")
        # print(f"New documents: {new_documents_count}") # Old print, replaced by logger

        # Generate CSV and RSS for truly recent documents (only unexported ones)
        if truly_recent_doc_urls:
            exported_count = len(self.generate_recent_documents_csv(truly_recent_doc_urls))
            truly_recent_doc_count = exported_count  # Update count to only include newly exported
        
        # Generate RSS feeds
        self._generate_rss_feeds(truly_recent_doc_urls if 'truly_recent_doc_urls' in locals() else [])
        
        # Simplified logging output
        print("New licence profiles")
        print("Processed compliance records")
        print(f"Truly recent documents: {truly_recent_doc_count}")

    def close(self):
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed.")
            # print("Database connection closed.") # Old print


if __name__ == '__main__':
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                        handlers=[
                            logging.FileHandler("scraper.log"),
                            logging.StreamHandler()
                        ])

    scraper = EPAScraper()
    try:
        scraper.run()
    except Exception as e:
        logging.critical(f"Unhandled exception in scraper: {e}", exc_info=True)
    finally:
        scraper.close()
