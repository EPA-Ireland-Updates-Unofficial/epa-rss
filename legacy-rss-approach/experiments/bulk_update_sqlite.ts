import * as sqlite3 from 'sqlite3';
import { URL } from "url";
import * as path from 'path';

// Open the SQLite database
const db = new sqlite3.Database('sqlite/epa-rss-snapshot-20230613_new_column.sqlite');

// Function to read and update records
async function readAndUpdateRecords() {
  return new Promise<void>((resolve, reject) => {
    // Query to select all records from the table
    const selectQuery = 'SELECT * FROM allsubmissions';

    // Execute the select query
    db.all(selectQuery, (err, rows) => {
      if (err) {
        reject(err);
      } else {
        // Loop through each row and update the data
        for (const row of rows) {
          // Perform your desired update operation here
          // For example, updating the 'name' column

          const leapURL = new URL(row.itemurl);
          const filename = path.basename(leapURL.pathname);
         

          const items3url = "https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/" + filename;

          // Query to update the record
          const updateQuery = `UPDATE allsubmissions SET items3url = '${items3url}' WHERE id = ${row.id}`;

          // Execute the update query
          db.run(updateQuery, (error) => {
            if (error) {
              reject(error);
            }
          });
        }
        resolve();
      }
    });
  });
}

// Close the database connection
function closeDatabase() {
  db.close((err) => {
    if (err) {
      console.error(err.message);
    } else {
      console.log('Database connection closed.');
    }
  });
}

// Call the readAndUpdateRecords function and handle any errors
readAndUpdateRecords()
  .then(() => {
    console.log('Records updated successfully.');
    closeDatabase();
  })
  .catch((error) => {
    console.error('Error updating records:', error);
    closeDatabase();
  });
