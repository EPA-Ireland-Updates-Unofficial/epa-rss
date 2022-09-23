# Introduction
This code scrapes all of the RSS feeds for submissions on the EPA Ireland website once a day. It then generates a single small RSS feed with all of the previous day's updates. Finally it generates daily CSV files with the same data.

It all runs under GitHub Actions at 1.15AM UTC every day and takes about 15 minutes to complete due to the number of RSS feeds that need to be downloaded and parsed.

## Subscribing to the RSS Feed
Use this URL in [Feedly](https://feedly.com) or similar:

## Viewing the daily CSV files.
They are all here in the repo: https://github.com/conoro/epa-rss/tree/main/output/csv/daily

## Getting the latest updates via Email
Coming at some point.

## Examining the data in the SQLite Database using Datasette Lite
A very cool project by [Simon Willison](https://github.com/simonw/datasette-lite). You can browse and query all the data up to Sep 22nd 2022 here:

