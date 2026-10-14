/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

const filename = path.resolve(__dirname, "../src/utils/studyDataImportTarget.js");
const source = fs.readFileSync(filename, "utf8");
const code = babel.transformSync(source, {
  filename,
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const moduleUnderTest = { exports: {} };
new Function("module", "exports", code)(moduleUnderTest, moduleUnderTest.exports);
const { resolveImportVisit, validateImportGroup } = moduleUnderTest.exports;

const visits = [{ name: "Baseline" }, { name: "Week 6" }];
const groups = [{ name: "Control" }, { name: "Treatment" }];

assert.deepEqual(
  resolveImportVisit({ mode: "all", visitSource: "fixed", bulkVisitIndex: 1, visits }),
  { index: 1, issue: "" },
  "bulk imports must support a selected visit when no visit column exists"
);
assert.equal(
  resolveImportVisit({ mode: "all", visitSource: "column", visitValue: "baseline", visits }).index,
  0,
  "visit-column matching must remain case insensitive"
);
assert.equal(
  resolveImportVisit({ mode: "single", singleVisitIndex: 0, visits }).index,
  0,
  "individual imports must use the visit selected in the dialog"
);
assert.equal(
  validateImportGroup({ mode: "all", groupSource: "subject", targetGroupIndex: 1, groups }),
  "",
  "the subject's assigned group must work without a group column"
);
assert.match(
  validateImportGroup({ mode: "all", groupSource: "fixed", bulkGroupIndex: 0, targetGroupIndex: 1, groups }),
  /does not match/,
  "a fixed group mismatch must be reported rather than changing the subject's group"
);
assert.match(
  validateImportGroup({ mode: "all", groupSource: "column", groupValue: "", targetGroupIndex: 1, groups }),
  /missing/,
  "a selected group column must reject blank values"
);

console.log("Study data import target tests passed");
