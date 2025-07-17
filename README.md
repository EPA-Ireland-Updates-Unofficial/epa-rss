# EPA Ireland Data Scraper

An automated system that monitors and archives regulatory compliance data from the Irish Environmental Protection Agency (EPA). This tool provides daily updates on environmental licence compliance, monitoring reports, incidents, and regulatory activities across Ireland.

## 🎯 What This Does

This system automatically:
- **Scrapes** licence profile data from the EPA Ireland LEAP API
- **Tracks** compliance records, monitoring returns, site visits, and incidents
- **Generates** daily CSV files with new compliance documents
- **Creates** RSS feeds for easy monitoring and integration
- **Archives** historical data in a SQLite database
- **Provides** structured access to EPA regulatory information

## 📊 Data Sources

The system monitors the [EPA Ireland LEAP portal](https://leap.epa.ie/) which contains:
- **Environmental Licences**: Industrial emissions, waste, water discharge permits
- **Compliance Records**: Monitoring reports, audit results, enforcement actions
- **Documents**: Annual reports, site visit reports, incident notifications, complaints
- **Licence Holders**: Companies and organizations with EPA permits

## 🗂️ Output Structure

### Daily CSV Files
```
output/csv/daily/YYYY/MM/YYYY-MM-DD.csv
```
Each CSV contains new compliance documents with columns:
- `licence_profile_name` - Company/facility name
- `document_type` - Type of compliance document
- `title` - Document title (sanitized for CSV)
- `leap_url` - Direct link to EPA portal
- `document_date` - When the document was created
- `compliance_status` - Current status (Open/Closed)
- `document_url` - API endpoint for document data

### RSS Feeds
- **`output/rsstwitter.xml`** - Recent CSV files (last 30 days)
- **`output/daily.xml`** - Recent compliance documents

### Database
- **`epa_ireland.db`** - SQLite database with complete historical data

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager
- Git (for automated updates)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/EPA-Ireland-Updates-Unofficial/epa_ireland_scraper.git
   cd epa_ireland_scraper
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage

### Manual Execution

**Full scrape and update:**
```bash
python scraper.py
```

**Generate CSV for specific date:**
```bash
python export_to_csv.py 2025-01-15
```

**Generate RSS feeds:**
```bash
python rss_generator.py --csv-days 30
```

**Regenerate historical CSV files:**
```bash
python regenerate_csvs.py
```

### Automated Execution

The system includes a cron script (`cron_scraper.sh`) that:
1. Runs the scraper to update the database
2. Exports today's CSV file
3. Updates RSS feeds
4. Commits changes to Git
5. Pushes updates to GitHub

**Set up daily automation:**
```bash
# Edit crontab
crontab -e

# Add line to run daily at 4:30 AM
30 4 * * * /path/to/epa_ireland_scraper/cron_scraper.sh
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `scraper.py` | Main scraper that fetches data from EPA API |
| `export_to_csv.py` | Generates daily CSV files with deduplication |
| `rss_generator.py` | Creates RSS feeds from CSV files and database |
| `cron_scraper.sh` | Automated daily execution script |
| `regenerate_csvs.py` | One-off script to rebuild historical CSVs |
| `requirements.txt` | Python package dependencies |

## 🔧 Configuration

### Database
- Default: `epa_ireland.db` (SQLite)
- Automatically created on first run
- Contains three main tables: `licence_profiles`, `compliance_records`, `compliance_documents`

### CSV Export
- **Default lookback**: 4 days for new documents
- **Deduplication**: Avoids re-exporting previously exported documents
- **Text sanitization**: Removes line breaks and formatting issues

### RSS Feeds
- **CSV feed**: Last 30 days of CSV files
- **Document feed**: Most recent compliance documents
- **Update frequency**: After each scraper run

## 📈 Monitoring

### RSS Feeds
Subscribe to the RSS feeds to monitor updates:
- **For developers**: Use `rsstwitter.xml` to track when new CSV files are available
- **For end users**: Use `daily.xml` to see latest compliance documents

### GitHub Integration
- New CSV files and RSS updates are automatically committed to GitHub
- Watch this repository for notifications when new data is available
- View historical data through GitHub's file browser

## 🛠️ Development

### Adding New Features
The system is modular:
- Modify `scraper.py` to change data collection
- Update `export_to_csv.py` to change CSV format
- Extend `rss_generator.py` for new RSS formats

### Database Schema
```sql
-- Licence profiles (companies/facilities)
licence_profiles: licenceprofileid, profilenumber, name, status, etc.

-- Compliance records (regulatory activities)  
compliance_records: compliancerecord_id, licenceprofileid, type, status, date

-- Documents (reports, monitoring data, incidents)
compliance_documents: document_id, compliance_id, title, document_type, document_date, document_url
```

## 📝 License
Apache 2.0

This project is unofficial and for educational/research purposes. All EPA data remains subject to EPA terms of use.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## ⚠️ Disclaimer

This is an unofficial tool for accessing publicly available EPA Ireland data. Users should:
- Respect EPA's terms of service
- Use data responsibly and ethically  
- Verify important information with official EPA sources
- Be mindful of API rate limits

## 📞 Support

For issues, questions, or feature requests:
- Open a GitHub issue
- Check existing issues for similar problems
- Provide detailed information about your setup and the issue

---

**Last updated**: Daily via automated scraper
**Data source**: [EPA Ireland LEAP Portal](https://leap.epa.ie/)
**Maintained by**: Conor O'Neill
