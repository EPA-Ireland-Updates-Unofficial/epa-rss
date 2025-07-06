# EPA Ireland Data Scraper

This tool scrapes data from the EPA Ireland API and stores it in a SQLite database. It captures:
1. Licence holder profiles
2. Compliance data for each licence holder

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scraper.py
```

The script will create a SQLite database named `epa_ireland.db` with all the scraped data.
