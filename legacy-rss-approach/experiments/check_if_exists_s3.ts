import * as AWS from "aws-sdk";


// Retrieve AWS credentials from environment variables
const accessKeyId = process.env.EPA_RSS_ACCESS_KEY_ID;
const secretAccessKey = process.env.EPA_RSS_SECRET_ACCESS_KEY;

// Set the S3 bucket details
const bucketName = "epa-rss";


const s3 = new AWS.S3({
    accessKeyId,
    secretAccessKey,
  });

async function checkFileExists(bucketName: string, fileName: string): Promise<boolean> {
  try {
    await s3.headObject({ Bucket: bucketName, Key: fileName }).promise();
    return true; // File exists
  } catch (err) {
    if (err.code === 'NotFound') {
      return false; // File doesn't exist
    }
    throw err; // Other error occurred
  }
}

// Usage
const fileName = 'uploads/090151b2804eada1.pdf';

checkFileExists(bucketName, fileName)
  .then((exists) => {
    console.log(`File "${fileName}" exists in S3: ${exists}`);
  })
  .catch((err) => {
    console.error('Error occurred:', err);
  });
