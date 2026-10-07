/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function load(relative) {
  const filename = path.resolve(__dirname, "../src", relative);
  const code = babel.transformSync(fs.readFileSync(filename, "utf8"), {
    filename, babelrc: false, configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const module = { exports: {} };
  new Function("module", "exports", "require", code)(module, module.exports, name => {
    if (name.startsWith("@/")) return load(`${name.slice(2)}.js`);
    return require(name);
  });
  return module.exports;
}

const structure = load("utils/spreadsheetStructure.js");

const legacy = [
  ["Subject ID", "1. Angry…", "Same label. (1)", "Other (1)", "2. Afraid…", "Same label. (2)", "Other (2)"],
  ["S01", "", "1", "2", "", "3", "4"],
  ["S02", "", "2", "3", "", "4", "5"],
];
assert.equal(structure.detectSpreadsheetLayout(legacy), "legacy-sections");
const parsedLegacy = structure.parseSpreadsheetStructure(legacy, { layout: "auto" });
assert.deepEqual(parsedLegacy.markerIndexes, [1, 4]);
assert.equal(parsedLegacy.columns.length, 5);
assert.equal(parsedLegacy.columns[1].sectionName, "1. Angry…");
assert.equal(parsedLegacy.columns[1].fieldName, "Same label.");
assert.equal(parsedLegacy.columns[3].sectionName, "2. Afraid…");
assert.notEqual(parsedLegacy.columns[1].stableKey, parsedLegacy.columns[3].stableKey);
assert.equal(parsedLegacy.dataRows.length, 2);

const canonical = [
  ["Metadata", "Angry", "Angry", "Afraid", "Afraid"],
  ["Subject ID", "Same label", "Other", "Same label", "Other"],
  ["subject_id", "angry_same", "angry_other", "afraid_same", "afraid_other"],
  ["S01", 1, 2, 3, 4],
];
assert.equal(structure.detectSpreadsheetLayout(canonical), "three-row");
const parsedCanonical = structure.parseSpreadsheetStructure(canonical, { layout: "three-row" });
assert.equal(parsedCanonical.dataStartIndex, 3);
assert.equal(parsedCanonical.columns[2].sectionName, "Angry");
assert.equal(parsedCanonical.columns[3].stableKey, "afraid_same");
assert.equal(parsedCanonical.dataRows[0][0], "S01");

const sentence = structure.parseSpreadsheetStructure([["Question with a period. (1)"], ["yes"]], { layout: "single" });
assert.equal(sentence.columns[0].sectionName, "");
assert.equal(sentence.columns[0].fieldName, "Question with a period. (1)");
assert.deepEqual(structure.splitExplicitHeader("Section :: Field"), { sectionName: "Section", fieldName: "Field" });

console.log("Spreadsheet structure tests passed");
