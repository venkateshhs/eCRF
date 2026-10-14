/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");
const XLSX = require("xlsx");

const filename = path.resolve(__dirname, "../src/utils/dateFormatParsing.js");
const source = fs.readFileSync(filename, "utf8");
const code = babel.transformSync(source, {
  filename,
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const moduleUnderTest = { exports: {} };
new Function("module", "exports", "require", code)(moduleUnderTest, moduleUnderTest.exports, require);
const { normalizeImportedDateForFormat } = moduleUnderTest.exports;

const workbook = XLSX.utils.book_new();
const worksheet = XLSX.utils.aoa_to_sheet([["Start"], [new Date(2026, 3, 6, 19, 58)]]);
worksheet.A2.z = "m/d/yy h:mm";
XLSX.utils.book_append_sheet(workbook, worksheet, "Data");
const reopened = XLSX.read(XLSX.write(workbook, { type: "buffer", bookType: "xlsx" }), { type: "buffer", cellDates: true });
const reopenedRows = XLSX.utils.sheet_to_json(reopened.Sheets.Data, { header: 1, raw: true, defval: "" });
assert.ok(reopenedRows[1][0] instanceof Date, "the import reader must retain native Excel dates alongside formatted display values");

assert.equal(
  normalizeImportedDateForFormat(new Date(2026, 3, 6, 19, 58), "dd.MM.yyyy"),
  "06.04.2026",
  "native Excel date cells must be formatted for the target field"
);
assert.equal(
  normalizeImportedDateForFormat("06.04.2026 19:58", "dd.MM.yyyy"),
  "06.04.2026",
  "a timestamp using the configured date format must be accepted for a date-only field"
);
assert.equal(
  normalizeImportedDateForFormat("2026-04-06 19:58", "dd.MM.yyyy"),
  "06.04.2026",
  "ISO-like CSV timestamps must be normalized to the configured format"
);
assert.equal(
  normalizeImportedDateForFormat("4/6/26 19:58", "dd.MM.yyyy"),
  "06.04.2026",
  "Excel-style formatted timestamps copied into CSV must also be normalized"
);
assert.equal(
  normalizeImportedDateForFormat("06/04/2026", "dd.MM.yyyy"),
  "06.04.2026",
  "four-digit slash dates must follow the target field's day-first convention"
);
assert.equal(
  normalizeImportedDateForFormat("not a date", "dd.MM.yyyy"),
  "not a date",
  "invalid values must remain visible to the normal validation pipeline"
);

console.log("Spreadsheet date import tests passed");
