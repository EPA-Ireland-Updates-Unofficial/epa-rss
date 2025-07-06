import sqlite3
import os
import boto3


# Powershell: 
# $env:EPA_RSS_ACCESS_KEY_ID="value"
# $env:EPA_RSS_SECRET_ACCESS_KEY="value"
# $env:EPA_RSS_BUCKET="value"


# Connect to the SQLite database
conn = sqlite3.connect('sqlite/epa-rss.sqlite')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Fetch all records from the table
cursor.execute('SELECT * FROM allsubmissions')
records = cursor.fetchall()

accessKeyId = os.environ['EPA_RSS_ACCESS_KEY_ID']
secretAccessKey = os.environ['EPA_RSS_SECRET_ACCESS_KEY']
bucketName = os.environ['EPA_RSS_BUCKET']

# Create a S3 client
s3 = boto3.client('s3', region_name='eu-west-1', aws_access_key_id=accessKeyId, aws_secret_access_key=secretAccessKey)

# Iterate over the records
for record in records:
    # Extract the filename from the URL
    filename = os.path.basename(record['itemurl'])

    try:
        # Check if the file exists in the S3 bucket
        s3.head_object(Bucket=bucketName, Key="uploads/"+filename)

        # If the file exists, construct the S3 URL
        s3_url = f'https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/{filename}'

        # Update the record in the SQLite database
        cursor.execute('UPDATE allsubmissions SET items3url = ? WHERE id = ?', (s3_url, record['id']))
    except Exception as e:
        print(f"Error checking file {filename}: {e}")

# Commit the changes and close the connection
conn.commit()
conn.close()