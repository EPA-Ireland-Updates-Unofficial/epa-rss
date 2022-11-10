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

  const dailycsvurl = "https://github.com/conoro/epa-rss/blob/main/" + "output/csv/daily/" + twodaysago + ".csv";

  let publishDateTime = new Date();

  feed.addItem({
    title: "Latest submissions to EPA Ireland",
    id: dailycsvurl,
    link: dailycsvurl || "",
    description: "All of the submissions from two days ago",
    content: "On GitHub as a CSV file here",
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

async function main() {
 
  await TwitterRSS();

}

main();

