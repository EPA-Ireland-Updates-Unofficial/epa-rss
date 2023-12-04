import sqlite3
import os

def update_records_in_database():
    # Connect to the SQLite database
    conn = sqlite3.connect('sqlite/epa-rss-snapshot-20230613_new_column.sqlite')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch all records from the table
    cursor.execute('SELECT * FROM allsubmissions')
    records = cursor.fetchall()

    # Update each record
    for record in records:
        # Here, you can modify the record as needed
        record_id = record['id']
        itemurl = record['itemurl']
        items3url = "https://epa-rss.s3.eu-west-1.amazonaws.com/uploads/" + os.path.basename(itemurl)

        # Update the record in the database
        cursor.execute('UPDATE allsubmissions SET items3url=? WHERE id=?', (items3url, record_id))

    # Commit the changes to the database
    conn.commit()

    # Close the database connection
    conn.close()

# Call the function to update records
update_records_in_database()