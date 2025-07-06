# Written by ChatGPT 4 on 2023-05-03
# Mind blown- the code worked first time, no changes!
# Code generated in response to the prompt:
# Please write a Python script that:
# - Accepts a list of URLs in a CSV file as input
# - Iterates through that list
# - For each entry in the list it:
#   - Downloads the URL as a file
#   - Uploads the file to a specific S3 bucket, using my AWS credentials
#   - Delay for 1 second
# - Logs progress to the console

# Conor's own notes:
  # First: pip install requests boto3
  # Second: Export SQLite DB as CSV to get all the submission URLs
  # Third: Configure S3 bucket
  # Fourth: Configure AWS Credentials in PowerShell:
    # $env:EPA_RSS_ACCESS_KEY_ID = 'blah'
    # $env:EPA_RSS_SECRET_ACCESS_KEY = 'blah'
    # export EPA_RSS_ACCESS_KEY_ID="blah"
    # export EPA_RSS_SECRET_ACCESS_KEY="blah"

import csv
import os
import sys
import time
import json
import boto3
import requests
from requests.exceptions import HTTPError
from botocore.exceptions import NoCredentialsError

def download_file(url, local_filename):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None

def upload_to_s3(local_filename, s3_bucket, s3_key, aws_access_key_id, aws_secret_access_key):
    try:
        s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        s3.upload_file(local_filename, s3_bucket, s3_key)
        print(f"Uploaded {s3_key} to {s3_bucket}.")
    except NoCredentialsError:
        print("Unable to find AWS credentials. Check your credentials and try again.")
        sys.exit(1)

def process_csv(input_csv, s3_bucket, aws_access_key_id, aws_secret_access_key, log_file):
    try:
        with open(log_file, 'r') as f:
            processed_urls = json.load(f)
    except FileNotFoundError:
        processed_urls = []

    with open(input_csv, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            url = row[0]

            if url in processed_urls:
                print(f"{url} has already been processed. Skipping...")
                continue

            print(f"Downloading {url}...")
            local_filename = url.split('/')[-1]
            downloaded_file = download_file(url, local_filename)

            if downloaded_file is not None:
                s3_key = f"uploads/{local_filename}"

                try: 
                    upload_to_s3(local_filename, s3_bucket, s3_key, aws_access_key_id, aws_secret_access_key)
                except ClientError as e:  # handle aws s3 exceptions
                    msg = e.response.get('Error', {}).get('Message', 'Unknown')
                    code = e.response.get('Error', {}).get('Code', 'Unknown')
                    print('Failed to copy to S3 bucket: {msg} ({code})'.format(msg=msg, code=code))

                os.remove(local_filename)
                print(f"Finished processing {url}.\n")

            else:
                print(f"Skipping {url} due to download error.\n")

            processed_urls.append(url)
            with open(log_file, 'w') as f:
                json.dump(processed_urls, f)

            time.sleep(1)  # Add a 1-second delay

if __name__ == "__main__":
#    input_csv = "epa-rss-submission-urls.csv" # Replace with your input CSV file name
#    input_csv = "epa-rss-submission-urls-01.csv" # Replace with your input CSV file name
    input_csv = "epa-rss-submission-urls-02.csv" # Replace with your input CSV file name
    s3_bucket = "epa-rss" # Replace with your target S3 bucket name
    aws_access_key_id = os.getenv('EPA_RSS_ACCESS_KEY_ID') # Replace with your AWS access key ID
    aws_secret_access_key = os.getenv('EPA_RSS_SECRET_ACCESS_KEY') # Replace with your AWS secret access key
    log_file = "processed_urls.json" # File to store processed URLs

    process_csv(input_csv, s3_bucket, aws_access_key_id, aws_secret_access_key, log_file)
