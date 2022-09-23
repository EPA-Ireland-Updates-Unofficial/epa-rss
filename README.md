# Introduction
This code scrapes all of the RSS feeds for submissions on the EPA Ireland website. It does this once per day and saves all of the new submissions to a SQLite DB. It then generates a single small RSS feed with all of the previous days updates. Finally it generates daily CSV files with the same data.

It all runs under GitHub Actions at 1.15AM UTC every day and takes about 15 minutes to complete due to the number of RSS feeds that need to be downloaded and parsed.

## Subscribing to the RSS Feed


## Getting the latest updates via EMail


## Examining the data in the SQLite Database using Datasette Lite
