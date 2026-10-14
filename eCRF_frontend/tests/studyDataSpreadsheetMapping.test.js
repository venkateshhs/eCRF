/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function load(relative) {
  const filename = path.resolve(__dirname, "../src", relative);
  let source = fs.readFileSync(filename, "utf8");
  if (filename.endsWith(".vue")) source = source.match(/<script>([\s\S]*?)<\/script>/)[1];
  const code = babel.transformSync(source, { filename, babelrc: false, configFile: false, plugins: ["@babel/plugin-transform-modules-commonjs"] }).code;
  const module = { exports: {} };
  new Function("module", "exports", "require", code)(module, module.exports, name => name.startsWith("@/") ? load(`${name.slice(2)}.js`) : require(name));
  return module.exports;
}

function instance(component) {
  const vm = {};
  Object.entries(component.methods).forEach(([key, method]) => { vm[key] = method.bind(vm); });
  Object.assign(vm, component.data.call(vm));
  Object.entries(component.computed).forEach(([key, getter]) => Object.defineProperty(vm, key, { get: getter.bind(vm) }));
  vm.availableFields = [];
  vm.subjects = [];
  vm.previewRows = [];
  return vm;
}

const component = load("components/dataentry/StudyDataImportDialog.vue").default;
const vm = instance(component);
vm.rawAoA = [
  ["Subject ID", "1. Angry…", "Same label. (1)", "Other (1)", "2. Afraid…", "Same label. (2)", "Other (2)"],
  ["S01", "", "1", "2", "", "3", "4"],
  ["S02", "", "2", "3", "", "4", "5"],
];
vm.availableFields = [
  { key: "0-0", sectionTitle: "1. Angry…", fieldLabel: "Same label.", fieldName: "1_angry_same_label", stableFieldKey: "1_angry_same_label", importAliases: ["Same label. (1)"] },
  { key: "0-1", sectionTitle: "1. Angry…", fieldLabel: "Other", fieldName: "1_angry_other", stableFieldKey: "1_angry_other", importAliases: ["Other (1)"] },
  { key: "1-0", sectionTitle: "2. Afraid…", fieldLabel: "Same label.", fieldName: "2_afraid_same_label", stableFieldKey: "2_afraid_same_label", importAliases: ["Same label. (2)"] },
  { key: "1-1", sectionTitle: "2. Afraid…", fieldLabel: "Other", fieldName: "2_afraid_other", stableFieldKey: "2_afraid_other", importAliases: ["Other (2)"] },
];
vm.buildColumnsAndRows();
assert.equal(vm.detectedLayout, "legacy-sections");
assert.equal(vm.columns.length, 5, "section marker columns must not become data columns");
assert.equal(vm.metadataMapping.subject, "0");
assert.equal(vm.visitSource, "fixed", "files without a visit column must fall back to a selected visit");
assert.equal(vm.groupSource, "subject", "files without a group column must use the subject's assigned group");
assert.equal(vm.mappings[2], "0-0");
assert.equal(vm.mappings[5], "1-0", "same label in another section must map independently");
assert.equal(vm.mappingCollisions.length, 0);
vm.mappings[3] = "0-0";
assert.equal(vm.mappingCollisions.length, 1, "many source columns may not overwrite one target field");

console.log("Study data spreadsheet mapping tests passed");
