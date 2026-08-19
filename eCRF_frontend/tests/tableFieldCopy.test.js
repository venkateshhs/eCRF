/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function loadModule(relativePath) {
  const sourcePath = path.resolve(__dirname, relativePath);
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

const { copyCompleteTableStructure } = loadModule("../src/utils/tableFieldCopy.js");

const source = {
  _id: "original-table-id",
  name: "vaccinations",
  label: "Vaccinations",
  type: "table",
  value: {
    rows: [{ vaccine: "Comirnaty", confirmed: true }],
  },
  constraints: {
    required: true,
    readonly: false,
    helpText: "Record every vaccination",
    visibilityLogic: {
      action: "show",
      match: "all",
      rules: [{ sourceFieldKey: "external-field", operator: "eq", value: "Yes" }],
    },
  },
  tableConfig: {
    version: 1,
    mode: "2d",
    initialRows: 2,
    allowAddRows: false,
    showRowNumbers: false,
    columns: [
      {
        id: "vaccine",
        key: "old-vaccine-key",
        label: "Vaccine",
        type: "select",
        options: ["Comirnaty", "Spikevax"],
        constraints: { required: true },
      },
      {
        id: "confirmed",
        key: "old-confirmed-key",
        label: "Confirmed",
        type: "checkbox",
        options: [],
        constraints: {
          visibilityLogic: {
            action: "show",
            match: "all",
            rules: [
              { sourceFieldKey: "vaccine", operator: "eq", value: "Comirnaty" },
              { sourceFieldKey: "external-field", operator: "eq", value: "Yes" },
            ],
          },
        },
      },
    ],
  },
};

let nextColumnId = 0;
const clone = copyCompleteTableStructure(source, {
  fieldId: "copied-table-id",
  name: "vaccinations_copy",
  label: "Vaccinations_copy",
  createColumnId: () => `new-column-${++nextColumnId}`,
});

assert.equal(clone._id, "copied-table-id");
assert.equal(clone.name, "vaccinations_copy");
assert.equal(clone.label, "Vaccinations_copy");
assert.equal(clone.tableConfig.allowAddRows, false);
assert.equal(clone.tableConfig.showRowNumbers, false);
assert.deepEqual(clone.tableConfig.columns[0].options, ["Comirnaty", "Spikevax"]);
assert.equal(clone.tableConfig.columns[0].constraints.required, true);
assert.equal(clone.tableConfig.columns[0].id, "new-column-1");
assert.equal(clone.tableConfig.columns[0].key, "new-column-1");
assert.equal(clone.tableConfig.columns[1].id, "new-column-2");

const copiedRules = clone.tableConfig.columns[1].constraints.visibilityLogic.rules;
assert.equal(copiedRules[0].sourceFieldKey, "new-column-1");
assert.equal(copiedRules[1].sourceFieldKey, "external-field");
assert.deepEqual(clone.constraints.visibilityLogic, source.constraints.visibilityLogic);

assert.equal(clone.value.rows.length, 2);
assert.deepEqual(clone.value.rows, [
  { "new-column-1": "", "new-column-2": false },
  { "new-column-1": "", "new-column-2": false },
]);
assert.notDeepEqual(clone.value, source.value, "entered table data must not be copied");

clone.tableConfig.columns[0].options.push("Changed copy");
clone.constraints.visibilityLogic.rules[0].value = "No";
assert.deepEqual(source.tableConfig.columns[0].options, ["Comirnaty", "Spikevax"]);
assert.equal(source.constraints.visibilityLogic.rules[0].value, "Yes");

assert.throws(
  () => copyCompleteTableStructure(
    { type: "text" },
    { fieldId: "x", name: "x", label: "x", createColumnId: () => "x" }
  ),
  /requires a table field/
);

