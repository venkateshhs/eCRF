/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function loadUtility(relativePath) {
  const filename = path.resolve(__dirname, "../src", relativePath);
  const exported = [];
  const code = fs.readFileSync(filename, "utf8")
    .replace(/export const (\w+)/g, (_, name) => {
      exported.push(name);
      return `const ${name}`;
    })
    .replace(/export function (\w+)/g, (_, name) => {
      exported.push(name);
      return `function ${name}`;
    }) + `\nmodule.exports = { ${exported.join(", ")} };`;
  const module = { exports: {} };
  new Function("module", "exports", code)(module, module.exports);
  return module.exports;
}

const {
  collectStudyMeasurements,
  normalizeStudySettings,
  studyNumberExamples,
} = loadUtility("utils/studySettings.js");

const defaults = normalizeStudySettings();
assert.equal(defaults.numberFormat.preset, "international");
assert.equal(defaults.numberFormat.decimalSeparator, ".");
assert.equal(defaults.numberFormat.groupingSeparator, ",");

const german = normalizeStudySettings({
  numberFormat: { preset: "german", unexpectedInputPolicy: "reject" },
});
assert.equal(german.numberFormat.decimalSeparator, ",");
assert.equal(german.numberFormat.groupingSeparator, ".");
assert.equal(german.numberFormat.unexpectedInputPolicy, "reject");
assert.equal(studyNumberExamples(german).exampleLarge, "100.000,25");

const summary = collectStudyMeasurements([
  {
    sections: [
      {
        title: "Vitals",
        fields: [
          { name: "score", label: "Clinical score", type: "number", constraints: {} },
          {
            name: "mass",
            label: "Patient mass",
            type: "number",
            constraints: { measurement: { concept: "body_weight", unitSource: "study_default" } },
          },
          { name: "comment", label: "Comment", type: "text", constraints: {} },
        ],
      },
    ],
  },
]);

assert.equal(summary.unclassified.length, 1);
assert.equal(summary.unclassified[0].label, "Clinical score");
assert.equal(summary.classified.length, 1);
assert.equal(summary.classified[0].concept, "body_weight");
assert.equal(summary.classified[0].fields[0].label, "Patient mass");

const { normalizeConstraints } = loadUtility("utils/constraints.js");
assert.deepEqual(
  normalizeConstraints("number", {
    min: 0,
    measurement: { concept: "body_weight", unitSource: "study_default" },
  }).measurement,
  { concept: "body_weight", unitSource: "study_default" }
);

console.log("studySettings tests passed");
