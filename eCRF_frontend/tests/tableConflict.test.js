/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function loadModule(relativePath, requireOverride = require) {
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
    requireOverride
  );
  return loaded.exports;
}

const dataConflict = loadModule("../src/utils/dataEntryConflict.js");
const tableConflict = loadModule(
  "../src/utils/tableConflict.js",
  (request) => {
    if (request === "@/utils/dataEntryConflict") return dataConflict;
    return require(request);
  }
);

const { applyConflictDecisions } = dataConflict;
const { mergeTableFieldConflict, tableConflictColumns } = tableConflict;

const field = {
  type: "table",
  label: "Impfungen",
  tableConfig: {
    columns: [
      { id: "date", label: "Impfdatum", type: "date" },
      { id: "vaccine", label: "Impfstoff", type: "select" },
      { id: "note", label: "Hinweis", type: "text" },
    ],
  },
};

{
  const result = mergeTableFieldConflict({
    parentKey: "vaccinations",
    sectionKey: "Demographische Daten",
    fieldKey: "vaccinations",
    field,
    baseValue: {
      rows: [{ date: "30.06.2026", vaccine: "Unknown", note: "" }],
    },
    localValue: {
      rows: [{ date: "02.07.2026", vaccine: "Moderna (Spikevax)", note: "" }],
    },
    latestValue: {
      rows: [{ date: "01.07.2026", vaccine: "Pfizer/BioNTech (Comirnaty)", note: "" }],
    },
  });

  assert.equal(result.conflicts.length, 2);
  assert.deepEqual(
    result.conflicts.map((conflict) => conflict.tableColumnLabel),
    ["Impfdatum", "Impfstoff"]
  );

  const wrapped = {
    "Demographische Daten": {
      vaccinations: result.mergedValue,
    },
  };
  const resolved = applyConflictDecisions(wrapped, result.conflicts, {
    [result.conflicts[0].key]: "local",
    [result.conflicts[1].key]: "latest",
  });
  assert.deepEqual(resolved["Demographische Daten"].vaccinations.rows[0], {
    date: "02.07.2026",
    vaccine: "Pfizer/BioNTech (Comirnaty)",
    note: "",
  });
}

{
  const result = mergeTableFieldConflict({
    parentKey: "disjoint",
    sectionKey: "Section",
    fieldKey: "table",
    field,
    baseValue: { rows: [{ date: "", vaccine: "", note: "" }] },
    localValue: { rows: [{ date: "02.07.2026", vaccine: "", note: "" }] },
    latestValue: { rows: [{ date: "", vaccine: "Moderna", note: "" }] },
  });

  assert.equal(result.conflicts.length, 0);
  assert.deepEqual(result.mergedValue.rows[0], {
    date: "02.07.2026",
    vaccine: "Moderna",
    note: "",
  });
}

{
  const duplicateField = {
    type: "table",
    tableConfig: {
      columns: [
        { id: "first", label: "Value", type: "text" },
        { id: "second", label: "Value", type: "text" },
      ],
    },
  };
  const columns = tableConflictColumns(duplicateField, {
    rows: [{ first: "A", second: "B" }, { first: "C", second: "D" }],
  });
  assert.deepEqual(
    columns.map((column) => column.displayLabel),
    ["Value (Column 1)", "Value (Column 2)"]
  );
}

{
  const result = mergeTableFieldConflict({
    parentKey: "new-row",
    sectionKey: "Demographische Daten",
    fieldKey: "vaccinations",
    field,
    baseValue: { rows: [] },
    localValue: {
      rows: [{ date: "02.07.2026", vaccine: "Moderna", note: "Local" }],
    },
    latestValue: {
      rows: [{ date: "01.07.2026", vaccine: "Pfizer", note: "Latest" }],
    },
  });

  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].allowKeepBoth, true);
  assert.equal(result.conflicts[0].conflictKind, "concurrent-table-row-addition");

  const wrapped = {
    "Demographische Daten": { vaccinations: result.mergedValue },
  };
  const resolved = applyConflictDecisions(wrapped, result.conflicts, {
    [result.conflicts[0].key]: "both",
  });
  assert.deepEqual(resolved["Demographische Daten"].vaccinations.rows, [
    { date: "01.07.2026", vaccine: "Pfizer", note: "Latest" },
    { date: "02.07.2026", vaccine: "Moderna", note: "Local" },
  ]);

  const useMine = applyConflictDecisions(wrapped, result.conflicts, {
    [result.conflicts[0].key]: "local",
  });
  assert.deepEqual(useMine["Demographische Daten"].vaccinations.rows, [
    { date: "02.07.2026", vaccine: "Moderna", note: "Local" },
  ]);

  const useOther = applyConflictDecisions(wrapped, result.conflicts, {
    [result.conflicts[0].key]: "latest",
  });
  assert.deepEqual(useOther["Demographische Daten"].vaccinations.rows, [
    { date: "01.07.2026", vaccine: "Pfizer", note: "Latest" },
  ]);
}

{
  const result = mergeTableFieldConflict({
    parentKey: "one-new-row",
    sectionKey: "Section",
    fieldKey: "table",
    field,
    baseValue: { rows: [] },
    localValue: { rows: [] },
    latestValue: { rows: [{ date: "01.07.2026", vaccine: "Pfizer" }] },
  });

  assert.equal(result.conflicts.length, 0);
  assert.deepEqual(result.mergedValue.rows, [
    { date: "01.07.2026", vaccine: "Pfizer" },
  ]);
}

console.log("table conflict tests passed");
