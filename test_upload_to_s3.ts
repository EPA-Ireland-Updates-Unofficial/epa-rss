import axios from 'axios';
import * as AWS from 'aws-sdk';
import * as fs from 'fs';

// Retrieve AWS credentials from environment variables
const accessKeyId = process.env.EPA_RSS_ACCESS_KEY_ID;
const secretAccessKey = process.env.EPA_RSS_SECRET_ACCESS_KEY;

// Set the S3 bucket details
const bucketName = 'epa-rss';

const s3 = new AWS.S3({
    accessKeyId,
    secretAccessKey,
  });

async function downloadPDF(url: string): Promise<Buffer> {
  const response = await axios.get(url, {
    responseType: 'arraybuffer',
  });

  return response.data;
}

async function uploadToS3(buffer: Buffer, key: string): Promise<void> {
  await s3
    .upload({
      Bucket: bucketName,
      Key: key,
      Body: buffer,
    })
    .promise();

  console.log(`PDF uploaded successfully to S3: ${key}`);
}

async function main() {
  try {
    const url = 'https://epawebapp.epa.ie/licences/lic_eDMS/090151b28087909f.pdf'; // Replace with the actual PDF URL
    const key = 'test_090151b28087909f.pdf'; // Replace with the desired S3 key

    console.log('Downloading PDF...');
    const buffer = await downloadPDF(url);

    console.log('Uploading PDF to S3...');
    await uploadToS3(buffer, key);
  } catch (error) {
    console.error('An error occurred:', error);
  }
}

main();
