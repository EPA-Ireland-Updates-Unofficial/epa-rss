// This is a test using Bun locally instead of Node.js. No transpiling necessary. Different SQLite3 driver. All good. WSL or OSX only. Not Windows yet.

// Use this utility when the EPA site was down or generate.ts didn't run for a given number of days for some reason
// Make sure you have first downloaded the latest epa-rss.sqlite from  https://epa-rss.s3.eu-west-1.amazonaws.com/latest/epa-rss.sqlite and put it in the sqlite dub-directory
// Provide the number of days you want to generate CSV for as a parameter

const { Database } = require("bun:sqlite");
import * as fs from "fs";
import { stringify } from "csv-stringify";
import { argv } from "process";

async function dailyCSV(days: number) {

  const db =  new Database("sqlite/epa-rss.sqlite");

  for (let eachday = 1; eachday <= days; eachday++) {
    let d = new Date();
    d.setDate(d.getDate() - eachday);
    let month = ("0" + (d.getMonth() + 1)).slice(-2);
    let day = ("0" + d.getDate()).slice(-2);
    let year = d.getFullYear();
    let somedaysago = year + "-" + month + "-" + day;

    const query = db.query(`select * from allsubmissions where DATE(itemdate) = $datereq;`);
    let result = query.all({ $datereq: somedaysago });
 
    let dailycsv = "output/csv/daily/" + somedaysago + ".csv";
    let writableStream = fs.createWriteStream(dailycsv);
    let columns = [
      "Item Date",
      "Submitter",
      "Item",
      "Item URL",
      "Submitter URL",
      "Main Page URL",
      "S3 URL",
    ];
    let stringifier = stringify({ header: true, columns: columns });

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
    }
    // Save the CSV file
    stringifier.pipe(writableStream);
    console.log("wrote " + dailycsv);
  }
  db.close();
}

async function main() {

  // Generate daily CSV for specified number of past days
  await dailyCSV(parseInt(process.argv[2]));

}

main();
