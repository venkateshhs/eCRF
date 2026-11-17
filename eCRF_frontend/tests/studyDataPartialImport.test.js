/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const parser = require("@babel/parser");
const babel = require("@babel/core");

const filename = path.resolve(__dirname, "../src/components/StudyDataEntryComponent.vue");
const source = fs.readFileSync(filename, "utf8");
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
const ast = parser.parse(script, { sourceType: "module" });
let methodSource = "";

function visit(node) {
  if (!node || typeof node !== "object") return;
  if (node.type === "ObjectMethod" && node.key?.name === "hydrateImportTargetFromSlot") {
    methodSource = script.slice(node.start, node.end);
  }
  Object.values(node).forEach((value) => {
    if (Array.isArray(value)) value.forEach(visit);
    else if (value && typeof value === "object") visit(value);
  });
}
visit(ast);
assert.ok(methodSource, "bulk import must expose authoritative slot hydration");

const hydrateImportTargetFromSlot = new Function(
  `return function ${methodSource}`
)();
const vm = {
  entryData: [],
  skipFlags: [],
  entryIds: [],
  ensureSlot(s, v, g) {
    this.entryData[s] = this.entryData[s] || [];
    this.entryData[s][v] = this.entryData[s][v] || [];
    this.entryData[s][v][g] = [];
    this.skipFlags[s] = this.skipFlags[s] || [];
    this.skipFlags[s][v] = this.skipFlags[s][v] || [];
    this.skipFlags[s][v][g] = [];
    this.entryIds[s] = this.entryIds[s] || [];
    this.entryIds[s][v] = this.entryIds[s][v] || [];
  },
  dictToArray(data) {
    return [[data.Demographics.name, data.Laboratory.result]];
  },
  makeSectionFieldSkeleton() {
    return [["", ""]];
  },
  mergeStudyFileRecordsIntoSlotData(_s, _v, data) {
    return data;
  },
  normalizeSkipFlagsShape(flags) {
    return flags;
  },
};

hydrateImportTargetFromSlot.call(vm, 0, 0, 0, {
  entry_id: 42,
  data: {
    Demographics: { name: "Previously imported" },
    Laboratory: { result: "Existing result" },
  },
  skipped_required_flags: [[true, false]],
});

assert.deepEqual(
  vm.entryData[0][0][0],
  [["Previously imported", "Existing result"]],
  "a later CSV import must begin with all saved fields from the slot"
);
assert.deepEqual(vm.skipFlags[0][0][0], [[true, false]]);
assert.equal(vm.entryIds[0][0][0], 42);
assert.ok(
  source.indexOf("this.hydrateImportTargetFromSlot(s, v, g, slot)") <
    source.indexOf("row.importedFields.forEach((item) =>"),
  "saved slot data must be hydrated before current CSV fields are applied"
);

const importTargetFilename = path.resolve(
  __dirname,
  "../src/utils/studyDataImportTarget.js"
);
const importTargetSource = fs.readFileSync(importTargetFilename, "utf8");
const importTargetCode = babel.transformSync(importTargetSource, {
  filename: importTargetFilename,
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const importTargetModule = { exports: {} };
new Function("module", "exports", importTargetCode)(
  importTargetModule,
  importTargetModule.exports
);
const { isCommittableImportRow } = importTargetModule.exports;

assert.equal(isCommittableImportRow({ status: "Ready" }), true);
assert.equal(
  isCommittableImportRow({ status: "Warning" }),
  true,
  "non-blocking validation warnings must not silently skip an otherwise matched subject row"
);
assert.equal(isCommittableImportRow({ status: "Error" }), false);

console.log("Partial study-data import regression tests passed");
