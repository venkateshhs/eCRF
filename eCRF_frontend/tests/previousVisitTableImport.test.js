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

const {
  buildPreviousVisitTableColumns,
  buildPreviousVisitTableRows,
  hasPreviousVisitTableData,
  selectPreviousVisitTableRows,
} = loadModule("../src/utils/previousVisitTableImport.js");

const field = {
  type: "table",
  tableConfig: {
    columns: [
      { id: "date", label: "Date", type: "date" },
      { id: "result", label: "Result", type: "text" },
    ],
  },
};
const source = {
  rows: [
    { date: "01.07.2026", result: "A" },
    { date: "02.07.2026", result: "B" },
    { date: "03.07.2026", result: "C" },
  ],
};

{
  const columns = buildPreviousVisitTableColumns(field, source);
  const rows = buildPreviousVisitTableRows(source, columns);
  assert.deepEqual(columns.map((column) => column.label), ["Date", "Result"]);
  assert.equal(rows.length, 3);
  assert.deepEqual(rows[1].cells.map((cell) => cell.value), ["02.07.2026", "B"]);
}

{
  const blank = {
    rows: [
      { date: "", result: "" },
      { date: null, result: "   " },
    ],
  };
  const columns = buildPreviousVisitTableColumns(field, blank);
  assert.equal(hasPreviousVisitTableData(field, blank), false);
  assert.deepEqual(buildPreviousVisitTableRows(blank, columns), []);
}

{
  const checkboxField = {
    type: "table",
    tableConfig: {
      columns: [{ id: "confirmed", label: "Confirmed", type: "checkbox" }],
    },
  };
  assert.equal(
    hasPreviousVisitTableData(checkboxField, { rows: [{ confirmed: false }] }),
    false
  );
  assert.equal(
    hasPreviousVisitTableData(checkboxField, { rows: [{ confirmed: true }] }),
    true
  );
}

{
  const numericField = {
    type: "table",
    tableConfig: {
      columns: [{ id: "score", label: "Score", type: "number" }],
    },
  };
  assert.equal(
    hasPreviousVisitTableData(numericField, { rows: [{ score: 0 }] }),
    true,
    "numeric zero is entered clinical data"
  );
}

{
  const mixed = {
    rows: [
      { date: "", result: "" },
      { date: "02.07.2026", result: "Recorded" },
      { date: "", result: null },
    ],
  };
  const columns = buildPreviousVisitTableColumns(field, mixed);
  const rows = buildPreviousVisitTableRows(mixed, columns);
  assert.equal(hasPreviousVisitTableData(field, mixed), true);
  assert.deepEqual(rows.map((row) => row.rowIndex), [1]);
}

{
  const selected = selectPreviousVisitTableRows(source, [0, 2]);
  assert.deepEqual(selected.rows, [source.rows[0], source.rows[2]]);
  selected.rows[0].result = "Changed after copy";
  assert.equal(source.rows[0].result, "A", "copied rows must not share references");
}

{
  const selected = selectPreviousVisitTableRows(source, [2, 99, -1, "invalid"]);
  assert.deepEqual(selected.rows, [source.rows[2]]);
}

{
  const duplicateLabels = buildPreviousVisitTableColumns(
    {
      type: "table",
      tableConfig: {
        columns: [
          { id: "first", label: "Value", type: "text" },
          { id: "second", label: "Value", type: "text" },
        ],
      },
    },
    { rows: [{ first: "A", second: "B" }] }
  );
  assert.deepEqual(
    duplicateLabels.map((column) => column.label),
    ["Value (Column 1)", "Value (Column 2)"]
  );
}

console.log("previous visit table import tests passed");
