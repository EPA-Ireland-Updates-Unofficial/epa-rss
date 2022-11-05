// EPA Ireland RSS - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0

import axios from 'axios';
import cheerio from 'cheerio';
import { Feed } from 'feed';
import * as Parser from 'rss-parser';
import { RateLimiter } from 'limiter';
import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite'
import * as fs from 'fs';
import { stringify } from 'csv-stringify';

async function dailyRSSCSV() {

  const db = await open({
    filename: 'epa-rss-test.sqlite',
    driver: sqlite3.Database
  })

  // Update Daily RSS
  const feed = new Feed({
    title: "EPA Ireland RSS Feed",
    description: "RSS feed for EPA website",
    id: "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse",
    link: "https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=B*&Submit=Browse",
    language: "en",
    image: "https://www.epa.ie/media/epa-2020/content-assets/images/EPA_logo_favicon.jpg",
    favicon: "https://www.epa.ie/media/epa-2020/content-assets/images/EPA_logo_favicon.jpg",
    copyright: "2022 © EPA. All Rights Reserved.",
    updated: new Date(),
    generator: "AWS Lambda",
    feedLinks: {
      rss: "https://example.com/rss"
    },
    author: {
      name: "EPA",
      email: "info@epa.ie",
      link: "https://www.epa.ie/who-we-are/contact-us/"
    }
  });

  // Get all the results for two-days-ago
  let d = new Date();
  d.setDate(d.getDate() - 2);
  let month = ("0" + (d.getMonth() + 1)).slice(-2);
  let day = ("0" + d.getDate()).slice(-2);
  let year = d.getFullYear();
  let twodaysago = year+"-"+month+"-"+day;
  console.log("two days ago was " + twodaysago);
  const result = await db.all('select * from allsubmissions where DATE(itemdate) = ?', [twodaysago]);

  const dailycsv = "output/csv/daily/"+twodaysago+".csv";
  const writableStream = fs.createWriteStream(dailycsv);
  const columns = [
    "Item Date",
    "Submitter",
    "Item",
    "Item URL",
    "Submitter URL",
    "Main Page URL",
  ];
  const stringifier = stringify({ header: true, columns: columns });

  for (let i = 0; i < result.length; i++){
  
  stringifier.write([result[i].itemdate, result[i].rsspagetitle, result[i].itemtitle, result[i].itemurl, result[i].rsspageurl, result[i].mainpageurl]);

  //console.log(result[i]);
  let publishDateTime = new Date(result[i].itemdate);
  console.log(publishDateTime);
  console.log(result[i].itemtitle);
  console.log(result[i].itemurl);
  console.log(result[i].rsspagetitle + ": " + result[i].itemtitle);

    feed.addItem({
      title: result[i].itemtitle,
      id: result[i].itemurl,
      link: result[i].itemurl || '',
      description: result[i].itemtitle,
      content: result[i].rsspagetitle + ": " + result[i].itemtitle,
      author: [
        {
          name: "EPA Ireland",
          email: "info@epa.ie",
          link: "https://www.epa.ie/who-we-are/contact-us/"
        }
      ],
      date: publishDateTime
    });

}

  // Save this to an XML file
  fs.writeFileSync('output/daily.xml', feed.rss2());

  // Save the CSV file
  stringifier.pipe(writableStream);

 // console.log(feed.rss2());
}

async function main() {
 
  await dailyRSSCSV();

  // Generate a GitHub Release with today's updates as the contents

}

main();

