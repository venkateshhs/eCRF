/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

const sourcePath = path.resolve(__dirname, "../src/utils/dominantChoice.js");
const transformed = babel.transformSync(fs.readFileSync(sourcePath, "utf8"), {
  filename: sourcePath,
  cwd: path.resolve(__dirname, ".."),
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const loaded = { exports: {} };
new Function("module", "exports", transformed)(loaded, loaded.exports);

const {
  normalizeDominantOptions,
  normalizeMultiChoiceValue,
  toggleMultiChoiceValue,
} = loaded.exports;

const options = ["Scar", "Burn", "Amputation", "No injuries"];
const dominantOptions = ["No injuries"];

assert.deepEqual(
  normalizeDominantOptions(["No injuries", "Missing"], options),
  ["No injuries"]
);
assert.deepEqual(
  normalizeMultiChoiceValue(["Scar", "Burn"], options, dominantOptions),
  ["Scar", "Burn"]
);
assert.deepEqual(
  normalizeMultiChoiceValue(
    ["Scar", "No injuries", "Burn"],
    options,
    dominantOptions
  ),
  ["No injuries"]
);
assert.deepEqual(
  toggleMultiChoiceValue({
    value: ["Scar", "Burn"],
    option: "No injuries",
    checked: true,
    options,
    dominantOptions,
  }),
  ["No injuries"]
);
assert.deepEqual(
  toggleMultiChoiceValue({
    value: ["No injuries"],
    option: "Scar",
    checked: true,
    options,
    dominantOptions,
  }),
  ["Scar"]
);

console.log("dominantChoice tests passed");
