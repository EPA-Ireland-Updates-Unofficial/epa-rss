<<<<<<< HEAD
"use strict";
// EPA Ireland RSS and CSV - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (_) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
exports.__esModule = true;
var axios_1 = require("axios");
var cheerio_1 = require("cheerio");
var feed_1 = require("feed");
var Parser = require("rss-parser");
var limiter_1 = require("limiter");
var sqlite3 = require("sqlite3");
var sqlite_1 = require("sqlite");
var fs = require("fs");
var csv_stringify_1 = require("csv-stringify");
var db;
// Throttle URL requests to one every 0.25 seconds
var limiter = new limiter_1.RateLimiter({ tokensPerInterval: 1, interval: 250 });
function scrapeNews(urlbase) {
    return __awaiter(this, void 0, void 0, function () {
        var alphabet, chr, url, response, html, $, RSSLinks, i, eachRSSURL, remainingMessages, parser, RSSContent, j, item, isoDate, result, e_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    alphabet = 0;
                    _a.label = 1;
                case 1:
                    if (!(alphabet < 1)) return [3 /*break*/, 14];
                    chr = String.fromCharCode(65 + alphabet);
                    url = urlbase + chr + "*&Submit=Browse";
                    console.log("Page for Letter " + chr + " : " + url);
                    return [4 /*yield*/, axios_1["default"].get(url)];
                case 2:
                    response = _a.sent();
                    html = response.data;
                    $ = cheerio_1["default"].load(html);
                    RSSLinks = $(".licSearchTable").find("a").toArray();
                    i = 0;
                    _a.label = 3;
                case 3:
                    if (!(i < RSSLinks.length)) return [3 /*break*/, 13];
                    eachRSSURL = "https://epawebapp.epa.ie/licences/lic_eDMS/rss/" + $(RSSLinks[i]).text() + ".xml";
                    console.log(eachRSSURL);
                    return [4 /*yield*/, limiter.removeTokens(1)];
                case 4:
                    remainingMessages = _a.sent();
                    parser = new Parser({
                        headers: { 'Accept': 'application/rss+xml, text/xml; q=0.1' }
                    });
                    _a.label = 5;
                case 5:
                    _a.trys.push([5, 11, , 12]);
                    return [4 /*yield*/, parser.parseURL(eachRSSURL)];
                case 6:
                    RSSContent = _a.sent();
                    console.log(RSSContent.title);
                    j = 0;
                    _a.label = 7;
                case 7:
                    if (!(j < RSSContent.items.length)) return [3 /*break*/, 10];
                    item = RSSContent.items[j];
                    isoDate = new Date(item.pubDate);
                    return [4 /*yield*/, db.run('INSERT OR REPLACE INTO allsubmissions (mainpageurl, rsspageurl, rsspagetitle, itemurl, itemtitle, itemdate) VALUES (?, ?, ?, ?, ?, ?)', url, eachRSSURL, RSSContent.title, item.link, item.title, isoDate.toISOString())];
                case 8:
                    result = _a.sent();
                    _a.label = 9;
                case 9:
                    j++;
                    return [3 /*break*/, 7];
                case 10: return [3 /*break*/, 12];
                case 11:
                    e_1 = _a.sent();
                    console.log("Error: " + e_1);
                    return [3 /*break*/, 12];
                case 12:
                    i++;
                    return [3 /*break*/, 3];
                case 13:
                    alphabet++;
                    return [3 /*break*/, 1];
                case 14: return [2 /*return*/];
            }
        });
    });
}
function dailyRSSCSV() {
    return __awaiter(this, void 0, void 0, function () {
        var feed, d, month, day, year, yesterday, result, dailycsv, writableStream, columns, stringifier, i, publishDateTime;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    console.log("Enter");
                    feed = new feed_1.Feed({
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
                    d = new Date();
                    month = ("0" + (d.getMonth() + 1)).slice(-2);
                    day = ("0" + (d.getDate() - 1)).slice(-2);
                    year = d.getFullYear();
                    yesterday = year + "-" + month + "-" + day;
                    return [4 /*yield*/, db.all('select * from allsubmissions where DATE(itemdate) = ?', [yesterday])];
                case 1:
                    result = _a.sent();
                    dailycsv = "output/csv/daily/" + yesterday + ".csv";
                    writableStream = fs.createWriteStream(dailycsv);
                    columns = [
                        "Item Date",
                        "Submitter",
                        "Item",
                        "Item URL",
                        "Submitter URL",
                        "Main Page URL",
                    ];
                    stringifier = (0, csv_stringify_1.stringify)({ header: true, columns: columns });
                    for (i = 0; i < result.length; i++) {
                        stringifier.write([result[i].itemdate, result[i].rsspagetitle, result[i].itemtitle, result[i].itemurl, result[i].rsspageurl, result[i].mainpageurl]);
                        publishDateTime = new Date(result[i].itemdate);
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
                    fs.writeFileSync('./output/daily.xml', feed.rss2());
                    console.log("wrote output/daily.xml");
                    // Save the CSV file
                    stringifier.pipe(writableStream);
                    console.log("wrote " + dailycsv);
                    // Debug
                    //console.log("Current Path: " + process.cwd());
                    // console.log("Current LS: ");
                    //fs.readdirSync("./").forEach(file => {
                    //   console.log(file);
                    // });
                    // fs.readdirSync("./output/").forEach(file => {
                    //   console.log(file);
                    //  });
                    //  fs.readdirSync("./output/csv/").forEach(file => {
                    //     console.log(file);
                    //  });
                    // console.log(feed.rss2());
                    console.log("leave");
                    return [2 /*return*/];
            }
        });
    });
}
function main() {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, sqlite_1.open)({
                        filename: 'epa-rss.sqlite',
                        driver: sqlite3.cached.Database
                    })
                    // Scrape all the RSS feeds on the EPA site and update SQLite
                ];
                case 1:
                    // Debug
                    //console.log("Current Path: " + process.cwd());
                    //console.log("Current LS: ");
                    //fs.readdirSync("./").forEach(file => {
                    //  console.log(file);
                    //});
                    db = _a.sent();
                    // Scrape all the RSS feeds on the EPA site and update SQLite
                    return [4 /*yield*/, scrapeNews("https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=")];
                case 2:
                    // Scrape all the RSS feeds on the EPA site and update SQLite
                    _a.sent();
                    console.log("Hello");
                    // Generate daily RSS and CSV for yesterday's updates
                    return [4 /*yield*/, dailyRSSCSV()];
                case 3:
                    // Generate daily RSS and CSV for yesterday's updates
                    _a.sent();
                    return [4 /*yield*/, db.close()];
                case 4:
                    _a.sent();
                    console.log("Goodbye");
                    return [2 /*return*/];
            }
        });
    });
}
main();
=======
"use strict";
// EPA Ireland RSS and CSV - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (_) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
exports.__esModule = true;
exports.EPAScraper = void 0;
var axios_1 = require("axios");
var cheerio_1 = require("cheerio");
var feed_1 = require("feed");
var Parser = require("rss-parser");
var limiter_1 = require("limiter");
var sqlite3 = require("sqlite3");
var sqlite_1 = require("sqlite");
var fs = require("fs");
var csv_stringify_1 = require("csv-stringify");
// Throttle URL requests to one every 0.25 seconds
var limiter = new limiter_1.RateLimiter({ tokensPerInterval: 1, interval: 250 });
var EPAScraper = /** @class */ (function () {
    function EPAScraper() {
    }
    EPAScraper.prototype.scrapeNews = function (urlbase) {
        return __awaiter(this, void 0, void 0, function () {
            var db, alphabet, chr, url, response, html, $, RSSLinks, i, eachRSSURL, remainingMessages, parser, RSSContent, j, item, isoDate, result, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, (0, sqlite_1.open)({
                            filename: 'epa-rss.sqlite',
                            driver: sqlite3.cached.Database
                        })];
                    case 1:
                        db = _a.sent();
                        alphabet = 0;
                        _a.label = 2;
                    case 2:
                        if (!(alphabet < 26)) return [3 /*break*/, 15];
                        chr = String.fromCharCode(65 + alphabet);
                        url = urlbase + chr + "*&Submit=Browse";
                        console.log("Page for Letter " + chr + " : " + url);
                        return [4 /*yield*/, axios_1["default"].get(url)];
                    case 3:
                        response = _a.sent();
                        html = response.data;
                        $ = cheerio_1["default"].load(html);
                        RSSLinks = $(".licSearchTable").find("a").toArray();
                        i = 0;
                        _a.label = 4;
                    case 4:
                        if (!(i < RSSLinks.length)) return [3 /*break*/, 14];
                        eachRSSURL = "https://epawebapp.epa.ie/licences/lic_eDMS/rss/" + $(RSSLinks[i]).text() + ".xml";
                        console.log(eachRSSURL);
                        return [4 /*yield*/, limiter.removeTokens(1)];
                    case 5:
                        remainingMessages = _a.sent();
                        parser = new Parser({
                            headers: { 'Accept': 'application/rss+xml, text/xml; q=0.1' }
                        });
                        _a.label = 6;
                    case 6:
                        _a.trys.push([6, 12, , 13]);
                        return [4 /*yield*/, parser.parseURL(eachRSSURL)];
                    case 7:
                        RSSContent = _a.sent();
                        console.log(RSSContent.title);
                        j = 0;
                        _a.label = 8;
                    case 8:
                        if (!(j < RSSContent.items.length)) return [3 /*break*/, 11];
                        item = RSSContent.items[j];
                        isoDate = new Date(item.pubDate);
                        return [4 /*yield*/, db.run('INSERT OR REPLACE INTO allsubmissions (mainpageurl, rsspageurl, rsspagetitle, itemurl, itemtitle, itemdate) VALUES (?, ?, ?, ?, ?, ?)', url, eachRSSURL, RSSContent.title, item.link, item.title, isoDate.toISOString())];
                    case 9:
                        result = _a.sent();
                        _a.label = 10;
                    case 10:
                        j++;
                        return [3 /*break*/, 8];
                    case 11: return [3 /*break*/, 13];
                    case 12:
                        e_1 = _a.sent();
                        console.log("Error: " + e_1);
                        return [3 /*break*/, 13];
                    case 13:
                        i++;
                        return [3 /*break*/, 4];
                    case 14:
                        alphabet++;
                        return [3 /*break*/, 2];
                    case 15: return [4 /*yield*/, db.close()];
                    case 16:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    return EPAScraper;
}());
exports.EPAScraper = EPAScraper;
function dailyRSSCSV() {
    return __awaiter(this, void 0, void 0, function () {
        var db, feed, d, month, day, year, yesterday, result, dailycsv, writableStream, columns, stringifier, i, publishDateTime;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, sqlite_1.open)({
                        filename: 'epa-rss.sqlite',
                        driver: sqlite3.cached.Database
                    })
                    // Update Daily RSS
                ];
                case 1:
                    db = _a.sent();
                    feed = new feed_1.Feed({
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
                    d = new Date();
                    month = ("0" + (d.getMonth() + 1)).slice(-2);
                    day = ("0" + (d.getDate() - 1)).slice(-2);
                    year = d.getFullYear();
                    yesterday = year + "-" + month + "-" + day;
                    return [4 /*yield*/, db.all('select * from allsubmissions where DATE(itemdate) = ?', [yesterday])];
                case 2:
                    result = _a.sent();
                    dailycsv = "output/csv/daily/" + yesterday + ".csv";
                    writableStream = fs.createWriteStream(dailycsv);
                    columns = [
                        "Item Date",
                        "Submitter",
                        "Item",
                        "Item URL",
                        "Submitter URL",
                        "Main Page URL",
                    ];
                    stringifier = (0, csv_stringify_1.stringify)({ header: true, columns: columns });
                    for (i = 0; i < result.length; i++) {
                        stringifier.write([result[i].itemdate, result[i].rsspagetitle, result[i].itemtitle, result[i].itemurl, result[i].rsspageurl, result[i].mainpageurl]);
                        publishDateTime = new Date(result[i].itemdate);
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
                    fs.writeFileSync('./output/daily.xml', feed.rss2());
                    console.log("wrote output/daily.xml");
                    // Save the CSV file
                    stringifier.pipe(writableStream);
                    console.log("wrote " + dailycsv);
                    // Debug
                    console.log("Current Path: " + process.cwd());
                    console.log("Current LS: ");
                    fs.readdirSync("./").forEach(function (file) {
                        console.log(file);
                    });
                    fs.readdirSync("./output/").forEach(function (file) {
                        console.log(file);
                    });
                    fs.readdirSync("./output/csv/").forEach(function (file) {
                        console.log(file);
                    });
                    return [2 /*return*/];
            }
        });
    });
}
function main() {
    return __awaiter(this, void 0, void 0, function () {
        var scraper;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    // Debug
                    console.log("Current Path: " + process.cwd());
                    console.log("Current LS: ");
                    fs.readdirSync("./").forEach(function (file) {
                        console.log(file);
                    });
                    scraper = new EPAScraper();
                    return [4 /*yield*/, scraper.scrapeNews("https://epawebapp.epa.ie/terminalfour/ippc/ippc-search.jsp?name=")];
                case 1:
                    _a.sent();
                    // Generate daily RSS and CSV for yesterday's updates
                    return [4 /*yield*/, dailyRSSCSV()];
                case 2:
                    // Generate daily RSS and CSV for yesterday's updates
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
main();
>>>>>>> 47ca707f4070bb800a50231f438ea797f74daf2b
