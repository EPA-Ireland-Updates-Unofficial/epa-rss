// EPA Ireland RSS and CSV - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0

import axios from "axios";
import cheerio from "cheerio";
import { Feed } from "feed";
import * as Parser from "rss-parser";
import { RateLimiter } from "limiter";
import * as sqlite3 from "sqlite3";
import { open } from "sqlite";
import * as AWS from "aws-sdk";
import * as fs from "fs";
import { stringify } from "csv-stringify";
import { URL } from "url";
import * as path from "path";

// Retrieve AWS credentials from environment variables
const accessKeyId = process.env.EPA_RSS_ACCESS_KEY_ID;
const secretAccessKey = process.env.EPA_RSS_SECRET_ACCESS_KEY;

// Set the S3 bucket details
const bucketName = process.env.EPA_RSS_BUCKET;

let db;

// Throttle URL requests to one every 0.25 seconds
const limiter = new RateLimiter({ tokensPerInterval: 1, interval: 250 });

const s3 = new AWS.S3({
  accessKeyId,
  secretAccessKey,
});

async function downloadPDF(url: string): Promise<Buffer> {
  const response = await axios.get(url, {
    responseType: "arraybuffer",
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

async function scrapeNews(urlbase: string) {
  for (let alphabet = 0; alphabet < 26; alphabet++) {
    //for (let alphabet = 0; alphabet < 1; alphabet++) {

    // Do every letter in alphabet. This is a *lot* of requests overall. 26 * number of companies per letter
    var chr = String.fromCharCode(65 + alphabet);
    // https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse

    let url = urlbase + chr + "*&Submit=Browse";
    console.log("Page for Letter " + chr + " : " + url);
    const response = await axios.get(url);
    const html = response.data;

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
        const xmlUtf16le = await axios.get(eachRSSURL, {
          responseEncoding: "utf16le",
        });

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
            isoDate = new Date("Mon, 03 Jan 2050 11:00:00 GMT");
          }

          const filename = path.basename(item.link);
          const items3url = "https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/" + filename;
          const key = "uploads/" + filename;

          // Check if file already in S3. If it isn't, upload it
          let rows = await db.all("SELECT items3url FROM allsubmissions where items3url=?", items3url);
          if (rows.length == 0){
            try {
              const buffer = await downloadPDF(item.link);
              await uploadToS3(buffer, key);
             //console.log("Simulating download/upload")
            } catch (error) {
              console.error("An S3 upload error occurred:", error);
            }
          }
        
          // Add entry to SQLite
          const result = await db.run(
            "INSERT OR REPLACE INTO allsubmissions (mainpageurl, rsspageurl, rsspagetitle, itemurl, itemtitle, itemdate, items3url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            url,
            eachRSSURL,
            RSSContent.title,
            item.link,
            item.title,
            isoDate.toISOString(),
            items3url
          );
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
  const result = await db.all(
    "select * from allsubmissions where DATE(itemdate) = ?",
    [twodaysago]
  );

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
  db = await open({
    filename: "sqlite/epa-rss.sqlite",
    driver: sqlite3.Database,
  });

  // Scrape all the RSS feeds on the EPA site and update SQLite
  await scrapeNews(
    "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name="
  );

  // Generate daily RSS and CSV for two day ago's updates
  await dailyRSSCSV();

  await TwitterRSS();

  await db.close();
}

main();
