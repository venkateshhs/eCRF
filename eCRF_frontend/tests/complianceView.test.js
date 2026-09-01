/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");
const { parse } = require("@vue/compiler-sfc");

const componentPath = path.resolve(__dirname, "../src/components/StudyComplianceView.vue");
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
  (request) => request === "axios" ? {} : require(request),
  loaded,
  loaded.exports
);
const component = loaded.exports.default;

assert.match(source, /Subjects enrolled with data/);
assert.match(source, /At least one visit started/);
assert.match(source, /Overall data compliance/);
assert.match(source, /Visit completion/);
assert.match(source, /width: `\$\{visit\.data_compliance_percent\}%`/);
assert.doesNotMatch(source, /width: `\$\{visit\.subject_completion_percent\}%`/);
assert.match(source, /Data compliance by group/);
assert.match(source, /Dropped subjects whose data was deleted are excluded/);
assert.doesNotMatch(source, /<th>Skipped fields<\/th>/);
assert.match(source, /Subject completeness distribution/);
assert.match(source, /Subjects appear after they have entered data for at least one visit/);
assert.doesNotMatch(source, /Subjects by 10% band/);
assert.match(source, /Completeness threshold curve/);
assert.match(source, /At least \{\{ marker\.threshold \}\}% complete/);
assert.doesNotMatch(source, /Visits at ≥80%/);
assert.match(source, /Needs attention/);
assert.match(source, /Partially completed subject-visits/);
assert.match(source, /Current compliance scope/);
assert.match(source, /Subjects with no started visits and future visits with no entered data are excluded/);
assert.match(source, /dropout percentage is the share of this enrolled-with-data cohort/);
assert.match(source, /expected visit not yet started by that subject is 0%/);

const context = {
  summary: {
    recruitment: {
      recruited_subjects: 10,
      active_subjects: 7,
      dropped_data_retained: 2,
      dropped_data_deleted: 1,
    },
    compliance: { data_compliance_percent: 65 },
    subject_visit_status: { complete: 6, partial: 3, not_started: 1 },
    completeness_histogram: [
      { range_start: 0, range_end: 10, subject_count: 1 },
      { range_start: 90, range_end: 100, subject_count: 3 },
    ],
    completeness_threshold_curve: Array.from({ length: 101 }, (_, threshold) => ({
      threshold,
      subject_count: threshold <= 65 ? 4 : 2,
    })),
    visit_stats: [],
    group_stats: [],
  },
};
context.recruitment = component.computed.recruitment.call(context);
context.compliance = component.computed.compliance.call(context);
context.distribution = component.computed.distribution.call(context);
context.distributionTotal = component.computed.distributionTotal.call(context);
context.histogramBars = component.computed.histogramBars.call(context);

assert.equal(context.recruitment.recruited_subjects, 10);
assert.equal(context.compliance.data_compliance_percent, 65);
assert.equal(component.methods.distributionWidth.call(context, "complete"), "60%");
assert.equal(component.computed.subjectVisitsNeedingAttention.call(context), 3);
assert.equal(context.histogramBars[0].label, "0–9%");
assert.equal(context.histogramBars[1].label, "90–100%");
assert.equal(component.computed.histogramSubjectTotal.call(context), 4);
assert.match(component.computed.complianceRadialStyle.call(context).background, /65%/);
assert.match(component.computed.recruitmentDonutStyle.call(context).background, /conic-gradient/);
assert.equal(component.methods.percentClass({ data_compliance_percent: 90, skipped_fields: 1 }), "skipped");

const studyViewSource = fs.readFileSync(
  path.resolve(__dirname, "../src/components/StudyView.vue"),
  "utf8"
);
assert.match(studyViewSource, /key: "compliance", label: "Compliance view"/);
assert.match(studyViewSource, /<StudyComplianceView/);

console.log("Compliance view tests passed");
