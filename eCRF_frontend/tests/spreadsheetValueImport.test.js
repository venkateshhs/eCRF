/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

const filename = path.resolve(__dirname, "../src/utils/spreadsheetValueImport.js");
const code = babel.transformSync(fs.readFileSync(filename, "utf8"), {
  filename,
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const moduleUnderTest = { exports: {} };
new Function("module", "exports", code)(moduleUnderTest, moduleUnderTest.exports);
const { analyzeDelimitedChoices, normalizeImportedBoolean, splitDelimitedChoices } = moduleUnderTest.exports;

assert.deepEqual(splitDelimitedChoices("Deutsch, Tuerkisch; Englisch|Franzoesisch\nArabisch"), [
  "Deutsch", "Tuerkisch", "Englisch", "Franzoesisch", "Arabisch",
]);
assert.deepEqual(splitDelimitedChoices(["Deutsch", "Tuerkisch, Englisch"]), ["Deutsch", "Tuerkisch", "Englisch"]);
assert.deepEqual(analyzeDelimitedChoices(["Deutsch", "Deutsch, Tuerkisch", "Deutsch"]), {
  allowMultiple: true,
  options: ["Deutsch", "Tuerkisch"],
});
assert.equal(normalizeImportedBoolean("Ja"), true);
assert.equal(normalizeImportedBoolean("Wahr"), true);
assert.equal(normalizeImportedBoolean("Nein"), false);
assert.equal(normalizeImportedBoolean("FALSE"), false);
assert.equal(normalizeImportedBoolean(true), true);
assert.equal(normalizeImportedBoolean("Vielleicht"), "Vielleicht");

console.log("Spreadsheet value import tests passed");
