#!/usr/bin/env python3

import os
import sqlite3
import csv
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
import argparse
from urllib.parse import urlparse, parse_qs

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

class RSSGenerator:
    def __init__(self, db_path: str = "epa_ireland.db"):
        """Initialize the RSS generator with a database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """Close the database connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def generate_rss_feed(self, items: List[Dict[str, str]], output_path: str, 
                         title: str, description: str, link: str = "") -> None:
        """Generate an RSS feed from a list of items.
        
        Args:
            items: List of dictionaries containing feed items
            output_path: Path to save the RSS feed
            title: Feed title
            description: Feed description
            link: Feed link (URL)
        """
        if not link:
            link = "https://github.com/EPA-Ireland-Updates-Unofficial/epa_ireland_scraper"
            
        rss = f'''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>{title}</title>
    <link>{link}</link>
    <description>{description}</description>
    <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
    <pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
'''
        for item in items:
            rss += f'''    <item>
        <title>{item.get('title', 'Untitled').replace('&', '&amp;')}</title>
        <link>{item.get('link', '').replace('&', '&amp;')}</link>
        <description>{item.get('description', '').replace('&', '&amp;')}</description>
        <pubDate>{item.get('pubDate', '')}</pubDate>
        <guid isPermaLink="false">{item.get('guid', item.get('link', '')).replace('&', '&amp;')}</guid>
    </item>
'''
        rss += '''</channel>
</rss>'''
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rss)
        print(f"Generated RSS feed: {output_path}")
    
    def _get_most_recent_csv(self, csv_dir: str) -> Optional[str]:
        """Find the most recent CSV file in the directory."""
        if not os.path.exists(csv_dir):
            return None
            
        csv_files = [
            os.path.join(csv_dir, f) 
            for f in os.listdir(csv_dir) 
            if f.endswith('.csv')
        ]
        
        if not csv_files:
            return None
            
        # Sort by modification time (newest first)
        csv_files.sort(key=os.path.getmtime, reverse=True)
        return csv_files[0]

    def generate_daily_documents_rss(self, output_dir: str = "output", 
                                   days_back: int = 1) -> str:
        """Generate RSS feed from the most recent CSV file.
        
        Args:
            output_dir: Directory to save the RSS feed
            days_back: Unused, kept for backward compatibility
            
        Returns:
            Path to the generated RSS file
        """
        csv_dir = os.path.join("output", "csv", "daily")
        latest_csv = self._get_most_recent_csv(csv_dir)
        
        if not latest_csv:
            print("No CSV files found in", csv_dir)
            return ""
            
        items = []
        try:
            with open(latest_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Try to get the most relevant fields from the CSV
                    doc_type = row.get('document_type', '')
                    title = row.get('title', row.get('document_id', 'Untitled'))
                    raw_url = (row.get('document_url') or '').rstrip('/')

                    # Use leap_url from CSV if present, else compute it on the fly
                    leap_url = row.get('leap_url')
                    if not leap_url:
                        seg = TYPE_SEGMENT_MAP.get(doc_type, 'return')
                        parsed = urlparse(raw_url)
                        if parsed.query:
                            qs = parse_qs(parsed.query)
                            guid_vals = next(iter(qs.values()), [''])
                            guid = guid_vals[0]
                        else:
                            guid = parsed.path.rstrip('/').split('/')[-1] if parsed.path else ''
                        profilenumber = row.get('profilenumber') or ''
                        if guid and profilenumber:
                            leap_url = f"https://leap.epa.ie/licence-profile/{profilenumber}/compliance/{seg}/{guid}"

                    url = leap_url or raw_url
                    doc_date = row.get('document_date', '')
                    
                    try:
                        pub_date = datetime.fromisoformat(doc_date).strftime('%a, %d %b %Y %H:%M:%S +0000')
                    except (ValueError, TypeError):
                        pub_date = ''
                    
                    items.append({
                        'title': f"{doc_type}: {title}" if doc_type else title,
                        'link': url,
                        'description': f"Type: {doc_type}<br>Date: {doc_date}" if doc_date else f"Type: {doc_type}",
                        'pubDate': pub_date,
                        'guid': url or str(hash(str(row)))
                    })
        except Exception as e:
            print(f"Error reading CSV file {latest_csv}: {e}")
            return ""
        
        output_path = os.path.join(output_dir, "daily.xml")
        self.generate_rss_feed(
            items=items,
            output_path=output_path,
            title="EPA Ireland - Recent Documents",
            description=f"Recent documents from EPA Ireland (from {os.path.basename(latest_csv)})"
        )
        return output_path
    
    def generate_csv_listing_rss(self, csv_dir: str = "output/csv/daily", 
                               output_dir: str = "output", 
                               days: int = 10) -> str:
        """Generate RSS feed listing recent CSV files from the last N calendar days.
        
        Args:
            csv_dir: Base directory containing YYYY/MM/ subdirectories with CSV files
            output_dir: Directory to save the RSS feed
            days: Number of calendar days of CSV files to include
            
        Returns:
            Path to the generated RSS file
        """
        if not os.path.exists(csv_dir):
            print(f"CSV directory not found: {csv_dir}")
            return ""
            
        # Get all CSV files
        csv_files = []
        try:
            # Get list of dates for the last 'days' calendar days
            today = datetime.now(timezone.utc).date()
            date_objects = [(today - timedelta(days=i)) for i in range(days)]
            
            # Check which of these dates have corresponding CSV files
            for date_obj in date_objects:
                year = date_obj.strftime('%Y')
                month = date_obj.strftime('%m')
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # Build the expected file path
                file_name = f"{date_str}.csv"
                file_path = os.path.join(csv_dir, year, month, file_name)
                
                if os.path.exists(file_path):
                    mtime = os.path.getmtime(file_path)
                    # Store both the full path and the display path (relative to the repo root)
                    display_path = os.path.join("output", "csv", "daily", year, month, file_name)
                    csv_files.append((file_path, mtime, file_name, display_path, date_str))
            
            # Sort by date (newest first)
            csv_files.sort(key=lambda x: x[4], reverse=True)
            
            items = []
            for file_path, mtime, file_name, display_path, date_str in csv_files:
                file_date = datetime.fromtimestamp(mtime, timezone.utc)
                pub_date = file_date.strftime('%a, %d %b %Y %H:%M:%S +0000')
                
                # Create a GitHub URL
                github_url = f"https://github.com/EPA-Ireland-Updates-Unofficial/epa_ireland_scraper/blob/main/{display_path}"
                
                items.append({
                    'title': f"CSV: {file_name}",
                    'link': github_url,
                    'description': f"CSV file for {date_str}",
                    'pubDate': pub_date,
                    'guid': display_path
                })
            
            output_path = os.path.join(output_dir, "rsstwitter.xml")
            self.generate_rss_feed(
                items=items,
                output_path=output_path,
                title="EPA Ireland - Recent CSV Files",
                description=f"CSV files from the last {days} calendar days"
            )
            return output_path
                
        except Exception as e:
            print(f"Error generating CSV listing RSS: {e}")
            return ""

def main():
    """Command-line interface for RSS generation."""
    parser = argparse.ArgumentParser(description='Generate RSS feeds for EPA Ireland data')
    parser.add_argument('--db', default='epa_ireland.db', help='Path to SQLite database')
    parser.add_argument('--output-dir', default='output', help='Output directory for RSS feeds')
    parser.add_argument('--days', type=int, default=1, help='Number of days of documents to include in daily feed')
    parser.add_argument('--csv-dir', default='output/csv/daily', help='Directory containing CSV files')
    parser.add_argument('--csv-days', type=int, default=10, help='Number of days of CSV files to include')
    
    args = parser.parse_args()
    
    with RSSGenerator(args.db) as rss_gen:
        # Generate documents RSS
        docs_path = rss_gen.generate_daily_documents_rss(
            output_dir=args.output_dir,
            days_back=args.days
        )
        
        # Generate CSV listing RSS
        csv_path = rss_gen.generate_csv_listing_rss(
            csv_dir=args.csv_dir,
            output_dir=args.output_dir,
            days=args.csv_days
        )
        
        if docs_path or csv_path:
            print("RSS generation complete!")
        else:
            print("No RSS feeds were generated.")

if __name__ == '__main__':
    main()
