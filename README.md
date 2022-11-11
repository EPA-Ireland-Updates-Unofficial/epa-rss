# Introduction
This code scrapes all of the RSS feeds for submissions on the [EPA Ireland website](https://www.epa.ie/) once a day. It then generates a single small RSS feed with all of the previous day's updates. Finally it generates daily CSV files with the same data.

It all runs under GitHub Actions around 01:30AM UTC every day and takes about 20 minutes to complete due to the number of RSS feeds that need to be downloaded and parsed.

## Subscribing to the RSS Feed
Use this URL in [Feedly](https://feedly.com) or similar: https://raw.githubusercontent.com/EPA-Ireland-Updates-Unofficial/epa-rss/main/output/daily.xml

## Viewing the daily CSV files.
They are all here in the repo starting on Sep 22nd 2022: https://github.com/EPA-Ireland-Updates-Unofficial/epa-rss/tree/main/output/csv/daily

## Getting notified by email (experimental)
If you'd like to receive email with a link to the latest CSV each day:

* Create a GitHub Account
* Click the drop-down menu beside "Watch" in the top right of this project's page. 
* Select "Custom" and tick the box beside "Issues". Then click Apply. 
* You should start receiving the emails beginning tomorrow.
  
## SQLite Database
The latest full set of scraped data is available as a SQLite DB that you can [download here](https://epa-rss.s3.eu-west-1.amazonaws.com/latest/epa-rss.sqlite). Use something like [SQLiteStudio](https://sqlitestudio.pl/) to browse and query it.

## Examining the data in the SQLite Database using Datasette Lite
Alternatively you can use a very cool project by Simon Willison called [Datasette Lite](https://github.com/simonw/datasette-lite) to browse and query all the latest data in your browser [by going here](https://lite.datasette.io/?url=https%3A%2F%2Fepa-rss.s3.eu-west-1.amazonaws.com%2Flatest%2Fepa-rss.sqlite#/epa-rss/allsubmissions). 


LICENSE Apache-2.0

Copyright Conor O'Neill 2022, conor@conoroneill.com
