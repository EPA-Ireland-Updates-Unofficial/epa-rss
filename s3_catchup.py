import sqlite3
import os
import boto3
import requests
import time

# Powershell: 
# $env:EPA_RSS_ACCESS_KEY_ID="value"
# $env:EPA_RSS_SECRET_ACCESS_KEY="value"
# $env:EPA_RSS_BUCKET="value"


# Connect to the SQLite database
conn = sqlite3.connect('sqlite/epa-rss.sqlite')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

accessKeyId = os.environ['EPA_RSS_ACCESS_KEY_ID']
secretAccessKey = os.environ['EPA_RSS_SECRET_ACCESS_KEY']
bucketName = os.environ['EPA_RSS_BUCKET']

# Fetch all records from the table where items3url is NULL
cursor.execute('SELECT * FROM allsubmissions WHERE items3url IS NULL')
records = cursor.fetchall()

# Create a S3 client
s3 = boto3.client('s3', region_name='eu-west-1', aws_access_key_id=accessKeyId, aws_secret_access_key=secretAccessKey)

# Create downloads directory if it doesn't exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Iterate over the records
for record in records:
    try:
        # Download the file
        response = requests.get(record['itemurl'], stream=True)
        response.raise_for_status()

        # Save the file to the downloads directory
        print(f"Downloading {record['itemurl']}...")
        filename = os.path.join('downloads', os.path.basename(record['itemurl']))
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Upload the file to the S3 bucket
        print(f"Uploading {filename}...")
        with open(filename, 'rb') as data:
            s3.upload_fileobj(data, bucketName, "uploads/" + os.path.basename(record['itemurl']))

        # Construct the S3 URL
        s3_url = f'https://{bucketName}.s3.eu-west-1.amazonaws.com/uploads/{os.path.basename(record["itemurl"])}'

        # Update the items3url field in the SQLite database
        cursor.execute('UPDATE allsubmissions SET items3url = ? WHERE id = ?', (s3_url, record['id']))
    except Exception as e:
        print(f"EPA file not accessible {e}")
    print("Sleeping for 0.25 seconds...")
    time.sleep(0.25)

# Commit the changes and close the connection
conn.commit()
conn.close()
