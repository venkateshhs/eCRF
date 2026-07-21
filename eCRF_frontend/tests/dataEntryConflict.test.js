/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

const sourcePath = path.resolve(__dirname, "../src/utils/dataEntryConflict.js");
const source = fs.readFileSync(sourcePath, "utf8");
const transformed = babel.transformSync(source, {
  filename: sourcePath,
  cwd: path.resolve(__dirname, ".."),
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const moduleUnderTest = { exports: {} };
new Function("module", "exports", "require", transformed)(
  moduleUnderTest,
  moduleUnderTest.exports,
  require
);

const {
  applyConflictDecisions,
  mergeDataEntryFields,
} = moduleUnderTest.exports;

function field(value) {
  return { "Clinical assessment": { temperature: value } };
}

{
  const result = mergeDataEntryFields(
    { A: { one: "", two: "" } },
    { A: { one: "local", two: "" } },
    { A: { one: "", two: "remote" } }
  );
  assert.deepEqual(result.merged, { A: { one: "local", two: "remote" } });
  assert.equal(result.conflicts.length, 0);
}

{
  const result = mergeDataEntryFields(field("36.5"), field("37.0"), field("38.0"));
  assert.equal(result.conflicts.length, 1);
  assert.deepEqual(result.merged, field("38.0"));

  const keepMine = applyConflictDecisions(result.merged, result.conflicts, {
    [result.conflicts[0].key]: "local",
  });
  assert.deepEqual(keepMine, field("37.0"));
}

{
  const result = mergeDataEntryFields(field("36.5"), field("37.0"), field("37.0"));
  assert.deepEqual(result.merged, field("37.0"));
  assert.equal(result.conflicts.length, 0);
}

{
  const result = mergeDataEntryFields(field("36.5"), field(""), field("36.5"));
  assert.deepEqual(result.merged, field(""));
  assert.equal(result.conflicts.length, 0);
}

{
  const firstMerge = mergeDataEntryFields(
    { A: { one: "", two: "", three: "" } },
    { A: { one: "user-2", two: "", three: "" } },
    { A: { one: "", two: "user-1", three: "" } }
  );
  assert.equal(firstMerge.conflicts.length, 0);

  const secondMerge = mergeDataEntryFields(
    firstMerge.merged,
    { A: { ...firstMerge.merged.A, three: "user-3" } },
    { A: { ...firstMerge.merged.A, two: "user-4" } }
  );
  assert.deepEqual(secondMerge.merged, {
    A: { one: "user-2", two: "user-4", three: "user-3" },
  });
  assert.equal(secondMerge.conflicts.length, 0);
}

console.log("dataEntryConflict tests passed");
