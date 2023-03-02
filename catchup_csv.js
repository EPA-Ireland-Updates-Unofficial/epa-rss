"use strict";
// Use this when the EPA site was down or generate.ts didn't run for a given day for some reason
// Provide the number of days in the past you want to generate CSV for
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
var sqlite3 = require("sqlite3");
var sqlite_1 = require("sqlite");
var fs = require("fs");
var csv_stringify_1 = require("csv-stringify");
function dailyCSV(days) {
    return __awaiter(this, void 0, void 0, function () {
        var db, eachday, d, month, day, year, somedaysago, result, dailycsv, writableStream, columns, stringifier, i;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, sqlite_1.open)({
                        filename: "sqlite/epa-rss.sqlite",
                        driver: sqlite3.Database
                    })];
                case 1:
                    db = _a.sent();
                    eachday = 1;
                    _a.label = 2;
                case 2:
                    if (!(eachday <= days)) return [3 /*break*/, 5];
                    d = new Date();
                    d.setDate(d.getDate() - eachday);
                    month = ("0" + (d.getMonth() + 1)).slice(-2);
                    day = ("0" + d.getDate()).slice(-2);
                    year = d.getFullYear();
                    somedaysago = year + "-" + month + "-" + day;
                    return [4 /*yield*/, db.all("select * from allsubmissions where DATE(itemdate) = ?", [somedaysago])];
                case 3:
                    result = _a.sent();
                    dailycsv = "output/csv/daily/" + somedaysago + ".csv";
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
                        stringifier.write([
                            result[i].itemdate,
                            result[i].rsspagetitle,
                            result[i].itemtitle,
                            result[i].itemurl,
                            result[i].rsspageurl,
                            result[i].mainpageurl,
                        ]);
                    }
                    // Save the CSV file
                    stringifier.pipe(writableStream);
                    console.log("wrote " + dailycsv);
                    _a.label = 4;
                case 4:
                    eachday++;
                    return [3 /*break*/, 2];
                case 5: return [4 /*yield*/, db.close()];
                case 6:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
function main() {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: 
                // Generate daily RSS and CSV for two day ago's updates
                return [4 /*yield*/, dailyCSV(parseInt(process.argv[2]))];
                case 1:
                    // Generate daily RSS and CSV for two day ago's updates
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
main();
