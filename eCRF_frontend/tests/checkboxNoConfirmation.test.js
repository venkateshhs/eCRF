/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function loadProgressModule() {
  const sourcePath = path.resolve(__dirname, "../src/utils/dataEntryProgress.js");
  const transformed = babel.transformSync(fs.readFileSync(sourcePath, "utf8"), {
    filename: sourcePath,
    cwd: path.resolve(__dirname, ".."),
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const loaded = { exports: {} };
  new Function("module", "exports", "require", transformed)(
    loaded,
    loaded.exports,
    require
  );
  return loaded.exports;
}

const { calculateDataEntryFieldProgress } = loadProgressModule();
const checkbox = { type: "checkbox", constraints: {} };

assert.deepEqual(
  calculateDataEntryFieldProgress({ field: checkbox, value: false }),
  { total: 1, completed: 0, skipped: 0 }
);

assert.deepEqual(
  calculateDataEntryFieldProgress({
    field: checkbox,
    value: false,
    checkboxFalseIsComplete: true,
  }),
  { total: 1, completed: 1, skipped: 0 }
);

assert.deepEqual(
  calculateDataEntryFieldProgress({
    field: { type: "checkbox", constraints: { readonly: true } },
    value: false,
    checkboxFalseIsComplete: true,
  }),
  { total: 0, completed: 0, skipped: 0 }
);

assert.deepEqual(
  calculateDataEntryFieldProgress({
    field: checkbox,
    value: true,
    checkboxFalseIsComplete: true,
  }),
  { total: 1, completed: 1, skipped: 0 }
);

console.log("Checkbox No-confirmation progress tests passed");
