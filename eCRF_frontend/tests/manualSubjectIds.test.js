/* eslint-env node */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const babel = require('@babel/core');
const parser = require('@babel/parser');
const XLSX = require('xlsx');

function load(relative) {
  const filename = path.resolve(__dirname, '../src', relative);
  const code = babel.transformSync(fs.readFileSync(filename, 'utf8'), {
    filename, babelrc: false, configFile: false, plugins: ['@babel/plugin-transform-modules-commonjs'],
  }).code;
  const module = { exports: {} };
  new Function('module', 'exports', 'require', code)(module, module.exports, require);
  return module.exports;
}
const ids = load('utils/subjectIdUtils.js');
const manual = load('utils/manualSubjectIds.js');
const { validateManualSubjectIds, parseSubjectIdCsv, reconcileManualSubjects } = manual;
const manualInputSource = fs.readFileSync(
  path.resolve(__dirname, '../src/components/ManualSubjectIdsInput.vue'), 'utf8'
);
assert.match(manualInputSource, /class="btn-option add-id-btn"/);
assert.match(manualInputSource, /class="btn-option remove-id-btn"/);
assert.match(manualInputSource, /class="btn-primary import-btn"/);
assert.match(manualInputSource, /\+ Add another subject/);
const subjectFormSource = fs.readFileSync(
  path.resolve(__dirname, '../src/components/SubjectForm.vue'), 'utf8'
);
assert.match(subjectFormSource, /class="btn-option skip-manual-btn"/);

// Round-trip actual XLS and XLSX bytes through the same reader used by uploads.
for (const bookType of ['biff8', 'xlsx']) {
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([]), 'Empty');
  const sheet = XLSX.utils.aoa_to_sheet([
    ['Subject ID', 'Comment'], ['ARIA08LE', 'not imported'], ['0009', 'text ID'],
    [8, 'formatted number'], ['Ab10', 'case preserved'], ['', 'missing ID'],
  ]);
  sheet.A4.z = '0000';
  XLSX.utils.book_append_sheet(workbook, sheet, 'Subjects');
  const bytes = XLSX.write(workbook, { bookType, type: 'array' });
  const imported = manual.readSubjectIdWorkbook(bytes);
  assert.deepEqual(imported.SheetNames, ['Empty', 'Subjects']);
  assert.throws(() => manual.parseSubjectIdWorksheet(imported, 'Empty'), /header row/);
  const table = manual.parseSubjectIdWorksheet(imported, 'Subjects');
  assert.deepEqual(table.headers, ['Subject ID', 'Comment']);
  assert.deepEqual(table.rows.map(row => row[0]), ['ARIA08LE', '0009', '0008', 'Ab10', '']);
  assert.equal(validateManualSubjectIds(table.rows.slice(0, 4).map(row => row[0])), '');
  assert.match(validateManualSubjectIds(table.rows.map(row => row[0])), /empty/);
  assert.throws(() => manual.parseSubjectIdWorksheet(imported, 'Missing'), /Select a worksheet/);
}

assert.equal(ids.normalizeSubjectIdConfig({}).preset, 'subj-prefix-number');
for (const preset of ids.SUBJECT_ID_PRESET_DEFINITIONS.filter(p => p.key !== 'manual')) {
  const cfg = ids.normalizeSubjectIdConfig({ preset: preset.key, pattern: preset.pattern, prefix: 'RT' });
  assert.notEqual(cfg.mode, 'manual');
  assert.equal(ids.subjectIdPatternValidationMessage(cfg), '');
  assert.ok(ids.buildSubjectIdFromConfig(cfg, 1));
}
const cfg = ids.normalizeSubjectIdConfig({ preset: 'manual', manualIds: ['0008', 'ARIA08LE'] });
assert.equal(cfg.mode, 'manual');
assert.equal(ids.normalizeSubjectIdConfig(JSON.parse(JSON.stringify(cfg))).mode, 'manual');
assert.throws(() => ids.buildUniqueSubjectId(cfg, 1), /Enter a Subject ID/);
assert.equal(ids.subjectIdPatternValidationMessage(cfg), '');
assert.equal(ids.buildPreviewSubjectId(cfg, 1), '');

assert.deepEqual(parseSubjectIdCsv('\uFEFFID,comment\r\n0008,"with, comma"\r\nARIA08LE,test\r\n').rows.map(row => row[0]), ['0008', 'ARIA08LE']);
assert.deepEqual(parseSubjectIdCsv('name;ID\nrecord;Ab08\n').rows[0], ['record', 'Ab08']);
assert.deepEqual(parseSubjectIdCsv('ID\n0008\nARIA08LE\n').rows, [['0008'], ['ARIA08LE']]);
assert.throws(() => parseSubjectIdCsv('ID\n'), /at least one/);
assert.throws(() => parseSubjectIdCsv('ID,other\nA,B,C\n'), /same number/);
assert.equal(validateManualSubjectIds(['0008', 'ARIA08LE']), '');
assert.match(validateManualSubjectIds(['A', 'a']), /duplicated/);
assert.match(validateManualSubjectIds(['a'], ['A']), /already exist/);
assert.deepEqual(
  manual.duplicateSubjectIds(['Existing', 'DUP', 'dup', 'Second', 'SECOND'], ['existing']),
  ['Existing', 'dup', 'SECOND']
);
assert.match(
  validateManualSubjectIds(['Existing', 'DUP', 'dup', 'Second', 'SECOND'], ['existing']),
  /"Existing", "dup", "SECOND"/
);
for (const value of ['', '../path', 'a/b', 'a b', 'x'.repeat(129)]) {
  assert.ok(validateManualSubjectIds([value]));
}

// Duplicate file imports must show every conflict and must not emit/replace IDs.
const inputScript = manualInputSource.match(/<script>([\s\S]*?)<\/script>/)[1];
const inputCode = babel.transformSync(inputScript, {
  filename: 'ManualSubjectIdsInput.vue', babelrc: false, configFile: false,
  plugins: ['@babel/plugin-transform-modules-commonjs'],
}).code;
const inputModule = { exports: {} };
new Function('module', 'exports', 'require', inputCode)(inputModule, inputModule.exports, name => {
  if (name === 'vue') return { markRaw: value => value };
  if (name === '@/utils/manualSubjectIds') return manual;
  return require(name);
});
const inputComponent = inputModule.exports.default;
const emitted = [];
const inputVm = {
  ...inputComponent.methods,
  selectedRows: [0, 1, 2, 3], column: 0,
  csv: { rows: [['EXISTING'], ['DUP'], ['dup'], ['OK']] },
  modelValue: ['CURRENT'], existingIds: ['existing'], lockedCount: 0,
  error: '', workbook: null, sheetName: '', disabled: false,
  $emit: (...args) => emitted.push(args),
};
inputVm.importIds();
assert.match(inputVm.error, /"EXISTING", "dup"/);
assert.match(inputVm.error, /No subject IDs were changed/);
assert.deepEqual(emitted, []);
assert.deepEqual(inputVm.modelValue, ['CURRENT']);
const persisted = [{ id: '0008', group: 'Control', status: 'DROPPED_DATA_RETAINED' }];
const next = reconcileManualSubjects(['0008', 'ARIA08LE'], persisted, persisted, ['Control'], true);
assert.deepEqual(next[0], persisted[0]);
assert.equal(next[1].id, 'ARIA08LE');
assert.deepEqual(reconcileManualSubjects(['0008', 'ARIA08LE'], next, persisted, ['Control'], true), next);
assert.throws(() => reconcileManualSubjects(['ARIA08LE', '0008'], next, persisted), /positions/);

// Exercise the actual setup step, including repeated navigation and skipping.
const filename = path.resolve(__dirname, '../src/components/StudyCreationComponent.vue');
const script = fs.readFileSync(filename, 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const ast = parser.parse(script, { sourceType: 'module' });
const functions = {};
function visit(node) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'FunctionDeclaration') functions[node.id.name] = script.slice(node.start, node.end);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach(visit);
    else if (value && typeof value === 'object') visit(value);
  }
}
visit(ast);
const ref = value => ({ value });
const scope = {
  ...ids, ...manual, _deepClone: value => JSON.parse(JSON.stringify(value)),
  subjectIdConfig: ref(cfg), subjectData: ref([]), persistedSubjects: ref([]),
  skipSubjectCreationNow: ref(false), subjectCount: ref(0), assignmentMethod: ref('Random'),
  groupData: ref([{ name: 'Control' }]), studyData: ref({}), assignments: ref([]),
  stepErrors: ref({}), step: ref(3), showDialog: ref(false), dialogMode: ref(''), dialogMessage: ref(''),
  commitStudyDetailsPreservingForms: () => {},
};
scope.checkSubjectsSetup = new Function('scope', `with (scope) { return (${functions.checkSubjectsSetup}); }`)(scope);
const skip = new Function('scope', `with (scope) { return (${functions.skipManualEnrollment}); }`)(scope);
assert.equal(scope.checkSubjectsSetup(), true);
assert.deepEqual(scope.subjectData.value.map(subject => subject.id), ['0008', 'ARIA08LE']);
const first = JSON.stringify(scope.subjectData.value);
assert.equal(scope.checkSubjectsSetup(), true);
assert.equal(JSON.stringify(scope.subjectData.value), first);
scope.persistedSubjects.value = JSON.parse(first);
scope.subjectIdConfig.value.manualIds.push('NEXT01');
assert.equal(scope.checkSubjectsSetup(), true);
assert.deepEqual(scope.subjectData.value.slice(0, 2), JSON.parse(first));
scope.subjectIdConfig.value.manualIds = ['changed', 'ARIA08LE'];
assert.equal(scope.checkSubjectsSetup(), false);
assert.match(scope.dialogMessage.value, /positions/);
skip();
assert.deepEqual(scope.subjectData.value, JSON.parse(first));
assert.equal(scope.step.value, 5);
scope.persistedSubjects.value = [];
skip();
assert.deepEqual(scope.subjectData.value, []);
assert.equal(scope.subjectCount.value, 0);

// Data entry must honor the saved manual mode rather than infer a generated
// pattern from the imported IDs; editing a pending ID must retain its group.
const entryScript = fs.readFileSync(path.resolve(__dirname, '../src/components/StudyDataEntryComponent.vue'), 'utf8')
  .match(/<script>([\s\S]*?)<\/script>/)[1];
const entryAst = parser.parse(entryScript, { sourceType: 'module' });
const methods = {};
function findMethods(node) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'ObjectMethod' && ['openSubjectDialog', 'generateSubjectDrafts', 'defaultGroupForIndex'].includes(node.key.name)) {
    methods[node.key.name] = new Function(...Object.keys(ids), `return function ${entryScript.slice(node.start, node.end)}`)(...Object.values(ids));
  }
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach(findMethods);
    else if (value && typeof value === 'object') findMethods(value);
  }
}
findMethods(entryAst);
const entry = {
  ...methods, isShared: false, sd: { subjectIdConfig: cfg, subjects: [{ id: 'ARIA08LE', group: 'Control' }] },
  study: { metadata: { study_name: 'Trial' } }, groupList: [{ name: 'Control' }], subjectDrafts: [],
};
entry.openSubjectDialog();
assert.equal(entry.subjectIdConfigDraft.mode, 'manual');
assert.equal(entry.subjectDrafts[0].id, '');
entry.subjectIdConfigDraft.manualIds = ['NEW08'];
entry.generateSubjectDrafts();
assert.equal(entry.subjectDrafts[0].id, 'NEW08');
entry.subjectDrafts[0].group = 'Assigned group';
entry.subjectIdConfigDraft.manualIds = ['NEW09', 'NEXT10', 'THIRD11'];
entry.generateSubjectDrafts();
assert.equal(entry.subjectDrafts[0].group, 'Assigned group');
assert.deepEqual(entry.subjectDrafts.map(subject => subject.id), ['NEW09', 'NEXT10', 'THIRD11']);
assert.equal(validateManualSubjectIds(entry.subjectDrafts.map(subject => subject.id), ['ARIA08LE']), '');
entry.subjectIdConfigDraft.manualIds.push('next10');
entry.generateSubjectDrafts();
assert.match(validateManualSubjectIds(entry.subjectDrafts.map(subject => subject.id), ['ARIA08LE']), /duplicated/);
assert.deepEqual(entry.sd.subjects, [{ id: 'ARIA08LE', group: 'Control' }]);
console.log('Manual subject ID workflow tests passed');
