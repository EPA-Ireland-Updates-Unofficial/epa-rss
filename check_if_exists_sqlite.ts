// EPA Ireland RSS and CSV - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0

import * as sqlite3 from "sqlite3";
import { open } from "sqlite";

let db;


async function main() {
  db = await open({
    filename: "sqlite/epa-rss.sqlite",
    driver: sqlite3.Database,
  });

//  let items3url = "https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/090151b2804eada1.pdf";
  let items3url = "https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/090151b280545ea2.pdf";

  let rows = await db.all("SELECT items3url FROM allsubmissions where items3url=?", items3url);

  if (rows.length > 0){
    console.log(rows);
  } else {
    console.log("Not in database");
  }

  await db.close();
}

main();









