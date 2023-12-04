CREATE TABLE allsubmissions (
    [index]      INTEGER  PRIMARY KEY AUTOINCREMENT,
    mainpageurl  STRING   NOT NULL,
    rsspageurl   STRING   NOT NULL,
    rsspagetitle STRING   NOT NULL,
    itemurl      STRING   NOT NULL
                          UNIQUE,
    itemtitle    STRING   NOT NULL,
    itemdate     DATETIME NOT NULL
);
