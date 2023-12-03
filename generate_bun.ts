// EPA Ireland RSS and CSV - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0
// 2023-09-24 Giving up on S3 upload for the moment, as getting crazy bursts of files from EPA site
// 2023-09-24 Using Bun instead of Node.js as an experiment

//import axios from "axios";
import cheerio from "cheerio";
import { Feed } from "feed";
import Parser from 'rss-parser';
import { RateLimiter } from "limiter";

import * as AWS from "aws-sdk";
import * as fs from "fs";
import { stringify } from "csv-stringify";
import * as path from "path";

import { Database } from "bun:sqlite";

// Retrieve AWS credentials from environment variables
const accessKeyId = process.env.EPA_RSS_ACCESS_KEY_ID;
const secretAccessKey = process.env.EPA_RSS_SECRET_ACCESS_KEY;

// Set the S3 bucket details
const bucketName = process.env.EPA_RSS_BUCKET;

const db = new Database("sqlite/epa-rss.sqlite");

// Throttle URL requests to one every 0.25 seconds
const limiter = new RateLimiter({ tokensPerInterval: 1, interval: 250 });

const s3 = new AWS.S3({
  accessKeyId,
  secretAccessKey,
});

async function downloadPDF(url: string): Promise<Buffer> {
  const response = await fetch(url);
  const buffer = await response.arrayBuffer();
  return Buffer.from(buffer);
}

// 2023-09-24 Giving up on S3 upload for the moment, as getting crazy bursts of files from EPA site
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

async function scrapeNewsAndUploadS3(urlbase: string) {
  for (let alphabet = 0; alphabet < 26; alphabet++) {
    //for (let alphabet = 0; alphabet < 1; alphabet++) {

    // Do every letter in alphabet. This is a *lot* of requests overall. 26 * number of companies per letter
    var chr = String.fromCharCode(65 + alphabet);
    // https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse

    let url = urlbase + chr + "*&Submit=Browse";
    console.log("Page for Letter " + chr + " : " + url);
    const response = await fetch(url);
    const html = await response.text();

    const $ = cheerio.load(html);
    const RSSLinks = $(".licSearchTable").find("a").toArray();
    for (let i = 0; i < RSSLinks.length; i++) {
      // HREF of each page is like: ippc-view.jsp?regno=P1115-01
      // URL of each page is like:  https://epawebapp.epa.ie/terminalfour/ippc/ippc-view.jsp?regno=P1115-01
      // Giving an RSS URL like:    https://epawebapp.epa.ie/licences/lic_eDMS/rss/P1115-01.xml

      //console.log($(link).text(), $(link).attr('href'));
      let eachRSSURL =
        "https://epawebapp.epa.ie/licences/lic_eDMS/rss/" +
        $(RSSLinks[i]).text() +
        ".xml";
      //console.log(eachRSSURL);

      // Rate Limit
      const remainingMessages = await limiter.removeTokens(1);

      let parser = new Parser({
        headers: { Accept: "application/rss+xml, text/xml; q=0.1" },
      });

      try {
        // Deal with encoding BOM at start of XML
        //console.log("Fetching: " + eachRSSURL);
        const response = await fetch(eachRSSURL);
        const buffer = await response.arrayBuffer();
        const decoder = new TextDecoder("utf-16le");
        const xmlUtf16le = decoder.decode(buffer);


        
        // Idiots now generating invalid XML
        let santizedXML = xmlUtf16le.data.replace(/&/g, "&amp;amp;");

        let RSSContent = await parser.parseString(santizedXML);

        // console.log(RSSContent.title);
        for (let j = 0; j < RSSContent.items.length; j++) {
          let item = RSSContent.items[j];
          let isoDate;
          if (item.pubDate) {
            isoDate = new Date(item.pubDate!);
          } else {
            //            isoDate = new Date("Mon, 03 Jan 2050 11:00:00 GMT");
            isoDate = new Date();
          }

          const filename = path.basename(item.link);
          const items3url = "https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/" + filename;
          const key = "uploads/" + filename;

          // Check if file already in S3. If it isn't, upload it
          const s3Query = db.query(`SELECT items3url FROM allsubmissions where items3url=$urlreq;`);
          let s3Rows = s3Query.all({ $urlreq: items3url });

          if (s3Rows.length == 0) {
            try {
              const buffer = await downloadPDF(item.link);
              await uploadToS3(buffer, key);
              //console.log("Simulating download/upload")
            } catch (error) {
              console.error("An S3 upload error occurred:", error);
            }
          }

          // Check if file already in SQlite. If it isn't add it
          // We have to add this because the geniuses are now including files in the RSS feed with no upload date
          // So we need to use a pseudo-date of the first time we see the file instead of the 2050 trick I used before
          // There was also a one-off setting of all dates to 2023-09-23 that were previously Mon, 03 Jan 2050 11:00:00 GMT 
          const query = db.query(`SELECT itemurl FROM allsubmissions where itemurl=$suburl;`);
          let rows = query.all({ $suburl: item.link });

          if (rows.length == 0) {
            try {
              const insertQuery = db.query(`INSERT OR REPLACE INTO allsubmissions (mainpageurl, rsspageurl, rsspagetitle, itemurl, itemtitle, itemdate, items3url) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)`);
              let insertResult = insertQuery.all(url, eachRSSURL, RSSContent.title, item.link, item.title, isoDate.toISOString(), items3url);
              console.log("Added new entry to SQLite: " + item.link)
            } catch (error) {
              console.error("Error adding: " + item.link);
            }
          }
        }
      } catch (e) {
        console.log("Error: " + e);
      }
    }
  }
}

async function TwitterRSS() {
  // RSS Feed for IFTTT to Twitter linking to the most recent CSV file
  const feed = new Feed({
    title: "EPA Ireland RSS Feed",
    description: "RSS feed for EPA website",
    id: "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse",
    link: "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse",
    language: "en",
    image:
      "https://www.epa.ie/media/epa-2020/content-assets/images/EPA_logo_favicon.jpg",
    favicon:
      "https://www.epa.ie/media/epa-2020/content-assets/images/EPA_logo_favicon.jpg",
    copyright: "2022 © EPA. All Rights Reserved.",
    updated: new Date(),
    generator: "GitHub Actions",
    feedLinks: {
      rss: "https://example.com/rss",
    },
    author: {
      name: "EPA",
      email: "info@epa.ie",
      link: "https://www.epa.ie/who-we-are/contact-us/",
    },
  });

  // Link to data from two days ago as the EPA now seems to be delaying by 1 day and we run early in the morning
  let d = new Date();
  d.setDate(d.getDate() - 2);
  let month = ("0" + (d.getMonth() + 1)).slice(-2);
  let day = ("0" + d.getDate()).slice(-2);
  let year = d.getFullYear();
  let twodaysago = year + "-" + month + "-" + day;

  const dailycsvurl =
    "https://github.com/EPA-Ireland-Updates-Unofficial/epa-rss/blob/main/output/csv/daily/" +
    twodaysago +
    ".csv";

  let publishDateTime = new Date();

  feed.addItem({
    title: twodaysago + " summary of all updates to EPA licences: ",
    id: dailycsvurl,
    link: dailycsvurl || "",
    description: "All updates on " + twodaysago,
    content:
      "EPA warning letters, inspectors reports, 3rd party submissions on licenses etc on " +
      twodaysago,
    author: [
      {
        name: "EPA Ireland",
        email: "info@epa.ie",
        link: "https://www.epa.ie/who-we-are/contact-us/",
      },
    ],
    date: publishDateTime,
  });

  // Save this to an XML file
  fs.writeFileSync("./output/rsstwitter.xml", feed.rss2());
  console.log("wrote output/rsstwitter.xml");
}

async function dailyRSSCSV() {
  // Update Daily RSS
  const feed = new Feed({
    title: "EPA Ireland RSS Feed",
    description: "RSS feed for EPA website",
    id: "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse",
    link: "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse",
    language: "en",
    image:
      "https://www.epa.ie/media/epa-2020/content-assets/images/EPA_logo_favicon.jpg",
    favicon:
      "https://www.epa.ie/media/epa-2020/content-assets/images/EPA_logo_favicon.jpg",
    copyright: "2022 © EPA. All Rights Reserved.",
    updated: new Date(),
    generator: "GitHub Actions",
    feedLinks: {
      rss: "https://example.com/rss",
    },
    author: {
      name: "EPA",
      email: "info@epa.ie",
      link: "https://www.epa.ie/who-we-are/contact-us/",
    },
  });

  // Get all the results for two days ago as the EPA now seems to be delaying by 1 day and we run early in the morning
  let d = new Date();
  d.setDate(d.getDate() - 2);
  let month = ("0" + (d.getMonth() + 1)).slice(-2);
  let day = ("0" + d.getDate()).slice(-2);
  let year = d.getFullYear();
  let twodaysago = year + "-" + month + "-" + day;

  const query = db.query(`select * from allsubmissions where DATE(itemdate) = $datereq;`);
  let result = query.all({ $datereq: twodaysago });

  const dailycsv = "output/csv/daily/" + twodaysago + ".csv";
  const writableStream = fs.createWriteStream(dailycsv);
  const columns = [
    "Item Date",
    "Submitter",
    "Item",
    "Item URL",
    "Submitter URL",
    "Main Page URL",
    "S3 URL",
  ];
  const stringifier = stringify({ header: true, columns: columns });

  for (let i = 0; i < result.length; i++) {
    stringifier.write([
      result[i].itemdate,
      result[i].rsspagetitle,
      result[i].itemtitle,
      result[i].itemurl,
      result[i].rsspageurl,
      result[i].mainpageurl,
      result[i].items3url,
    ]);

    //console.log(result[i]);
    let publishDateTime = new Date(result[i].itemdate);
    feed.addItem({
      title: result[i].itemtitle,
      id: result[i].itemurl,
      link: result[i].itemurl || "",
      description: result[i].itemtitle,
      content: result[i].rsspagetitle + ": " + result[i].itemtitle,
      author: [
        {
          name: "EPA Ireland",
          email: "info@epa.ie",
          link: "https://www.epa.ie/who-we-are/contact-us/",
        },
      ],
      date: publishDateTime,
    });
  }

  // Save this to an XML file
  fs.writeFileSync("./output/daily.xml", feed.rss2());
  console.log("wrote output/daily.xml");

  // Save the CSV file
  stringifier.pipe(writableStream);
  console.log("wrote " + dailycsv);
}

async function main() {

  // Scrape all the RSS feeds on the EPA site and update SQLite
  await scrapeNewsAndUploadS3(
    "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name="
  );

  // Generate daily RSS and CSV for two day ago's updates
  await dailyRSSCSV();

  await TwitterRSS();

  await db.close();
}

main();
