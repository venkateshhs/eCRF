/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function load(relative) {
  const filename = path.resolve(__dirname, "../src", relative);
  const code = babel.transformSync(fs.readFileSync(filename, "utf8"), {
    filename,
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const module = { exports: {} };
  new Function("module", "exports", "require", code)(module, module.exports, require);
  return module.exports;
}

const importer = load("utils/templateFieldImport.js");

const responseExport = [
  ["ID", "Age", "Gender", "Visit date", "Notes"],
  ["P001", 42, "Female", "2026-04-01", "Short"],
  ["P002", 57, "Male", "2026-04-02", "A much longer note"],
  ["P003", 39, "Female", "2026-04-03", "Short"],
];
assert.equal(importer.detectOrientation(responseExport, 0), "columns");
const columns = importer.analyzeColumnFields(responseExport, 0);
assert.equal(columns[1].inferredType, "number");
assert.equal(columns[2].inferredType, "select");
assert.equal(columns[3].inferredType, "date");
assert.deepEqual(columns[2].distinct, ["Female", "Male"]);

const definitions = [
  ["Field name", "Type"],
  ["Subject ID", "text"],
  ["Birth date", "date"],
  ["Consent", "boolean"],
];
assert.equal(importer.detectOrientation(definitions, 0), "rows");
const definitionColumns = importer.makeColumns(definitions[0]);
const mappings = importer.suggestDefinitionMappings(definitionColumns);
assert.equal(mappings.labelIndex, 0);
assert.equal(mappings.typeIndex, 1);
const definitionRows = importer.analyzeDefinitionRows(definitions, 0, mappings.labelIndex, mappings.typeIndex, -1);
assert.equal(definitionRows.length, 3);
assert.equal(importer.normalizeType(definitionRows[2].rawType), "checkbox");

const duplicateHeaders = importer.makeColumns(["Result", "Result", ""]);
assert.deepEqual(duplicateHeaders.map(column => column.displayLabel), ["Result", "Result (2)", "Column 3"]);
assert.deepEqual(importer.uniqueFieldNames([{ label: "Age" }, { label: "Age" }, { label: "Äge" }]), ["age", "age_2", "age_3"]);

console.log("Template field import tests passed");
