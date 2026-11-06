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
  vm.$emit = (event, payload) => { if (event === "import-fields") vm.emitted = payload; };
  return vm;
}

const component = load("components/ImportCsvTemplateDialog.vue").default;
const vm = instance(component);
vm.loadWorkbookData({ Legacy: [
  ["Subject ID", "Angry", "Same label (1)", "Afraid", "Same label (2)"],
  ["S01", "", "1", "", "2"],
  ["S02", "", "2", "", "3"],
] });
assert.equal(vm.orientation, "legacy-sections");
vm.candidates.find(item => item.columnIndex === 0).selected = false;
vm.goToReview();
assert.equal(vm.importRows.length, 2);
assert.deepEqual(vm.importRows.map(row => row.sectionTitle), ["Angry", "Afraid"]);
vm.importRows[0].type = "radio";
vm.applyTypeToSection(vm.importRows[0]);
vm.confirmImport();
assert.equal(vm.emitted.sections.length, 2);
assert.equal(vm.emitted.sections[0].fields[0].constraints.importAliases[0], "Same label (1)");
assert.notEqual(vm.emitted.sections[0].fields[0].name, vm.emitted.sections[1].fields[0].name);

const multiVm = instance(component);
multiVm.loadWorkbookData({ Responses: [
  ["ID", "Muttersprache"],
  ["1", "Deutsch"],
  ["2", "Deutsch, Tuerkisch"],
  ["3", "Deutsch"],
  ["4", "Deutsch, Englisch"],
] });
multiVm.orientation = "columns";
multiVm.prepareCandidates();
multiVm.candidates.find(item => item.label === "ID").selected = false;
const multiCandidate = multiVm.candidates.find(item => item.label === "Muttersprache");
assert.equal(multiCandidate.inferredAllowMultiple, true);
assert.match(multiVm.candidateSubtitle(multiCandidate), /multiple choices detected/);
multiVm.goToReview();
assert.equal(multiVm.importRows[0].type, "radio");
assert.equal(multiVm.importRows[0].allowMultiple, true);
assert.equal(multiVm.importRows[0].optionsRaw, "Deutsch | Tuerkisch | Englisch");
multiVm.confirmImport();
const multiField = multiVm.emitted[0];
assert.equal(multiField.type, "radio");
assert.equal(multiField.constraints.allowMultiple, true);
assert.deepEqual(multiField.options, ["Deutsch", "Tuerkisch", "Englisch"]);

console.log("Structured template import tests passed");
