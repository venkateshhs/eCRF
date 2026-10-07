/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function transform(source, filename) {
  return babel.transformSync(source, {
    filename,
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
}

function loadWorkflow() {
  const filename = path.resolve(__dirname, "../src/utils/studySaveWorkflow.js");
  const module = { exports: {} };
  new Function("module", "exports", "require", transform(fs.readFileSync(filename, "utf8"), filename))(
    module,
    module.exports,
    require
  );
  return module.exports;
}

const workflow = loadWorkflow();
assert.equal(workflow.normalizedStudyStatus(" published "), "PUBLISHED");
assert.equal(workflow.normalizedStudyStatus(null), "DRAFT");
assert.equal(workflow.isDraftStudyStatus("DRAFT"), true);
assert.equal(workflow.isDraftStudyStatus("PUBLISHED"), false);

const statusFilename = path.resolve(__dirname, "../src/components/StudySaveStatus.vue");
const statusSource = fs.readFileSync(statusFilename, "utf8");
const statusScript = statusSource.match(/<script>([\s\S]*?)<\/script>/)[1];
const statusModule = { exports: {} };
new Function("module", "exports", "require", transform(statusScript, statusFilename))(
  statusModule,
  statusModule.exports,
  name => {
    if (name === "@/utils/studySaveWorkflow") return workflow;
    return require(name);
  }
);
const statusComponent = statusModule.exports.default;

function statusInstance(overrides = {}) {
  const emitted = [];
  const vm = {
    dirty: true,
    saving: false,
    status: "DRAFT",
    canAutoSave: true,
    reminderVisible: false,
    remindAfter: null,
    remindLaterMs: 10,
    $emit: event => emitted.push(event),
    ...overrides,
  };
  for (const [name, method] of Object.entries(statusComponent.methods)) vm[name] = method.bind(vm);
  return { vm, emitted };
}

{
  const { vm, emitted } = statusInstance({ status: "DRAFT" });
  Object.defineProperty(vm, "published", { get: () => false });
  vm.onBeforeIdle();
  assert.deepEqual(emitted, ["idle-save"], "dirty drafts should save before inactivity logout");
}

{
  const { vm, emitted } = statusInstance({ status: "PUBLISHED" });
  Object.defineProperty(vm, "published", { get: () => true });
  vm.onBeforeIdle();
  assert.deepEqual(emitted, [], "published studies must never be saved by the inactivity event");
  assert.equal(vm.reminderVisible, true, "published changes should remain visibly unsaved");
}

const activitySource = fs.readFileSync(path.resolve(__dirname, "../src/utils/activityTracker.js"), "utf8");
assert.match(activitySource, /beforeIdleMs:\s*2\s*\*\s*60\s*\*\s*1000/);
assert.match(activitySource, /idleFor\s*>=\s*beforeIdleAt/);
assert.match(activitySource, /state\.beforeIdleTriggered\s*=\s*true/);

for (const componentName of ["StudyCreationComponent.vue", "ScratchFormComponent.vue", "ProtocolMatrix.vue"]) {
  const source = fs.readFileSync(path.resolve(__dirname, `../src/components/${componentName}`), "utf8");
  assert.match(source, /__skipActivityTracker:\s*automatic/);
}

for (const componentName of ["StudyCreationComponent.vue", "ProtocolMatrix.vue"]) {
  const source = fs.readFileSync(path.resolve(__dirname, `../src/components/${componentName}`), "utf8");
  assert.match(source, /addEventListener\(STUDY_BEFORE_IDLE_EVENT, saveDraftBeforeIdle\)/);
  assert.match(source, /removeEventListener\(STUDY_BEFORE_IDLE_EVENT, saveDraftBeforeIdle\)/);
}

const creationSource = fs.readFileSync(path.resolve(__dirname, "../src/components/StudyCreationComponent.vue"), "utf8");
assert.doesNotMatch(creationSource, /<StudySaveStatus/);
assert.equal((creationSource.match(/"Save and Continue"/g) || []).length >= 5, true);

const scratchSource = fs.readFileSync(path.resolve(__dirname, "../src/components/ScratchFormComponent.vue"), "utf8");
assert.match(scratchSource, /<StudySaveStatus/);
assert.match(scratchSource, /:show-action="false"/);
assert.match(scratchSource, /\scompact\s/);

const matrixSource = fs.readFileSync(path.resolve(__dirname, "../src/components/ProtocolMatrix.vue"), "utf8");
assert.doesNotMatch(matrixSource, /<StudySaveStatus/);
assert.match(matrixSource, /studyStatus\.value\s*!==\s*"DRAFT"/);
assert.match(matrixSource, /studyStatus\.value\s*===\s*"PUBLISHED"\s*\?\s*"publish"\s*:\s*"draft"/);

console.log("Study save workflow tests passed");
