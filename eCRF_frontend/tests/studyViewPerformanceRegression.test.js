/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");
const { parse } = require("@vue/compiler-sfc");

function loadVueComponent(relativePath) {
  const sourcePath = path.resolve(__dirname, relativePath);
  const source = fs.readFileSync(sourcePath, "utf8");
  const { descriptor } = parse(source, { filename: sourcePath });
  const transformed = babel.transformSync(descriptor.script.content, {
    filename: sourcePath,
    cwd: path.resolve(__dirname, ".."),
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const loaded = { exports: {} };
  const requireMock = (request) => {
    if (request === "axios") return {};
    if (request.includes("uploadedFiles")) {
      return {
        collectUploadedFilesForSlot: () => [],
        inferUploadedFileFieldContext: () => null,
        normalizeUploadedFiles: () => [],
        uploadedFileId: () => null,
        uploadedFileName: () => "",
      };
    }
    return {};
  };
  new Function("require", "module", "exports", transformed)(requireMock, loaded, loaded.exports);
  return { component: loaded.exports.default, source };
}

const loadedDashboard = loadVueComponent("../src/components/StudyDataDashboard.vue");
const dashboard = loadedDashboard.component;
assert.match(loadedDashboard.source, /v-if="isBootstrapping \|\| isLoadingEntries"/);
assert.match(loadedDashboard.source, /class="dashboard-loading-spinner"/);
const methods = dashboard.methods;
const proxiedStudy = new Proxy({ metadata: { id: 12 }, content: { study_data: { subjects: [] } } }, {});
const clonedStudy = methods.cloneStudyPayload(proxiedStudy);
assert.deepEqual(clonedStudy, proxiedStudy);
assert.notEqual(clonedStudy, proxiedStudy);

const entries = [
  { id: 1, subject_index: 0, visit_index: 0, group_index: 0, form_version: 1, data: [["v1"]] },
  { id: 2, subject_index: 0, visit_index: 0, group_index: 0, form_version: 2, data: [["v2"]] },
  { id: 3, subject_index: 0, visit_index: 0, group_index: 0, form_version: 3, data: [["v3"]] },
  { id: 4, subject_index: 1, visit_index: 0, group_index: 0, form_version: 1, data: [["other"]] },
];
const dashboardContext = {
  entries,
  selectedVersion: 2,
  entryIndexCache: new WeakMap(),
  entrySlotKey: methods.entrySlotKey,
  buildEntrySlotIndex: methods.buildEntrySlotIndex,
  entrySlotIndexFor: methods.entrySlotIndexFor,
};
Object.defineProperty(dashboardContext, "currentEntrySlotIndex", {
  get() {
    return methods.buildEntrySlotIndex.call(dashboardContext, entries);
  },
});

assert.equal(methods.findBestEntryFromEntries.call(dashboardContext, entries, 0, 0, 0).id, 2);
dashboardContext.selectedVersion = 4;
assert.equal(methods.findBestEntryFromEntries.call(dashboardContext, entries, 0, 0, 0).id, 3);
dashboardContext.selectedVersion = 0;
assert.equal(methods.findBestEntryFromEntries.call(dashboardContext, entries, 0, 0, 0).id, 3);
assert.equal(methods.findBestEntryFromEntries.call(dashboardContext, entries, 1, 0, 0).id, 4);
assert.equal(methods.findBestEntryFromEntries.call(dashboardContext, entries, "0", 0, 0), null);

function legacyFindBest(slotEntries, targetVersion) {
  const exact = slotEntries.find((entry) => Number(entry.form_version) === Number(targetVersion));
  if (exact) return exact;
  const atOrBefore = slotEntries
    .filter((entry) => Number(entry.form_version) <= Number(targetVersion))
    .sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
  if (atOrBefore) return atOrBefore;
  return [...slotEntries].sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
}

const primarySlotEntries = entries.filter(
  (entry) => entry.subject_index === 0 && entry.visit_index === 0 && entry.group_index === 0
);
[-1, 0, 1, 2, 3, 4, 99].forEach((targetVersion) => {
  dashboardContext.selectedVersion = targetVersion;
  const indexed = methods.findBestEntryFromEntries.call(dashboardContext, entries, 0, 0, 0);
  const legacy = legacyFindBest(primarySlotEntries, targetVersion);
  assert.equal(indexed.id, legacy.id);
});

const studyView = loadVueComponent("../src/components/StudyView.vue").component;
let nextCalls = 0;
const routeContext = {
  activeTab: "meta",
  tabs: [{ key: "meta" }, { key: "viewdata" }],
};
studyView.beforeRouteUpdate.call(
  routeContext,
  { params: { id: "12" }, query: { tab: "viewdata" } },
  { params: { id: "12" }, query: { tab: "meta" } },
  () => { nextCalls += 1; }
);
assert.equal(routeContext.activeTab, "viewdata");
assert.equal(nextCalls, 1);

console.log("Study View performance regression tests passed");
