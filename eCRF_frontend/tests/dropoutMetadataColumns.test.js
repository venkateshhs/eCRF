/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");
const { parse } = require("@vue/compiler-sfc");

const componentPath = path.resolve(__dirname, "../src/components/StudyDataDashboard.vue");
const source = fs.readFileSync(componentPath, "utf8");
const { descriptor } = parse(source, { filename: componentPath });
const transformed = babel.transformSync(descriptor.script.content, {
  filename: componentPath,
  cwd: path.resolve(__dirname, ".."),
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const loaded = { exports: {} };
new Function("require", "module", "exports", transformed)(
  (request) => {
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
  },
  loaded,
  loaded.exports
);
const methods = loaded.exports.default.methods;

const versionedStudy = {
  metadata: {},
  content: {
    study_data: {
      subjects: [{ id: "SUB-002", group: "Historical group" }],
      visits: [],
      groups: [],
      selectedModels: [],
      assignments: [],
    },
  },
};
const versionContext = {
  study: versionedStudy,
  authoritativeSubjects: [{
    id: "SUB-002",
    group: "Current group",
    status: "DROPPED_DATA_RETAINED",
    dropout_date: "2026-11-05",
    dropout_reason: "Other",
    dropout_other_reason: "Moved away",
  }],
  mergeSubjectsWithCurrentStatus: methods.mergeSubjectsWithCurrentStatus,
};
methods.applyTemplateSchema.call(versionContext, {
  subjects: [{ id: "SUB-002", group: "Historical group" }],
  visits: [],
  groups: [],
  selectedModels: [],
  assignments: [],
});
assert.deepEqual(versionContext.study.content.study_data.subjects[0], {
  id: "SUB-002",
  group: "Historical group",
  status: "DROPPED_DATA_RETAINED",
  dropout_date: "2026-11-05",
  dropout_reason: "Other",
  dropout_other_reason: "Moved away",
});

const columns = methods.buildDashboardColumns.call({ sections: [] });
assert.deepEqual(columns.map((column) => ({
  kind: column.kind,
  key: column.key,
  label: column.label,
  sectionTitle: column.sectionTitle,
})), [
  { kind: "subjectMetadata", key: "__dropoutDate", label: "Dropout Date", sectionTitle: "Subject Status" },
  { kind: "subjectMetadata", key: "__dropoutReason", label: "Dropout Reason", sectionTitle: "Subject Status" },
]);

const subjects = [
  { id: "SUB-001", group: "A" },
  {
    id: "SUB-002",
    group: "A",
    status: "DROPPED_DATA_RETAINED",
    dropout_date: "2026-11-05",
    dropout_reason: "Other",
    dropout_other_reason: "Moved away",
  },
];
const context = {
  subjects,
  visits: [{ name: "Baseline" }],
  currentWindowIndexSets: () => ({
    subjectIdxPageSet: new Set([0, 1]),
    visitIdxPageSet: new Set([0]),
  }),
  isPairInWindow: () => true,
  resolveGroup: () => 0,
  resolveGroupName: () => "A",
  findBestEntryFromEntries: () => null,
  uploadedFilesForRow: () => [],
  formatSubjectDropoutReason: methods.formatSubjectDropoutReason,
  applyDashboardFilters: (rows) => rows,
  applyDashboardSort: (rows) => rows,
  isAssigned: () => {
    throw new Error("Subject metadata columns must not depend on template assignments");
  },
};
const rows = methods.buildDashboardRows.call(context, {
  entries: [],
  columns,
  forceAllPairs: true,
  applyFilters: false,
  applySort: false,
});

assert.equal(rows[0].__dropoutDate, "");
assert.equal(rows[0].__dropoutReason, "");
assert.equal(rows[1].__dropoutDate, "2026-11-05");
assert.equal(rows[1].__dropoutReason, "Other — Moved away");
assert.match(source, /kind: "subjectMetadata"/);
assert.match(source, /Dropout Date/);
assert.match(source, /Dropout Reason/);

console.log("Dropout metadata column tests passed");
