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
assert.match(source, /Actual enrollment over time/);
assert.match(source, /rolling 90-day average/);
assert.match(source, /Group proportions over time/);
assert.match(source, /v-if="usesStackedEnrollmentAreas"/);
assert.match(source, /v-else-if="hasGroupProportionLineHistory"/);
assert.match(source, /enrollmentTotalLinePoints/);
assert.match(source, /enrollmentGroupSeries/);
assert.match(source, /enrollmentProportionSeries/);
assert.match(source, /Equal share/);
assert.match(source, /Current group allocation/);
assert.match(source, /A time trend will appear after subjects are enrolled on another date/);
assert.match(source, /v-else-if="singleEnrollmentGroup"/);
assert.match(source, /All enrolled subjects are in the same group/);
assert.match(source, /Optional planned enrollment/);
assert.match(source, /Total subjects over a period/);
assert.match(source, /Monthly recruitment numbers/);
assert.match(source, /\/enrollment-plan/);
assert.match(source, /summary\.can_edit_enrollment_plan/);
assert.match(source, /enrollmentPlan\.enabled/);
assert.match(source, /enrollment-planned-line/);

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

const oneGroupContext = {
  enrollmentGroups: [{ group_index: 0, group_name: "Patients", count: 40, proportion_percent: 100 }],
};
assert.equal(component.computed.hasMultipleEnrollmentGroups.call(oneGroupContext), false);
assert.equal(component.computed.usesStackedEnrollmentAreas.call({
  ...oneGroupContext,
  hasMultipleEnrollmentGroups: false,
  enrollment: { enrolled_subjects: 40 },
  enrollmentTimeline: Array.from({ length: 4 }, (_, index) => ({ date: `2026-10-${20 + index}` })),
}), false);
assert.deepEqual(component.computed.singleEnrollmentGroup.call(oneGroupContext), oneGroupContext.enrollmentGroups[0]);

const multipleGroupContext = {
  enrollmentGroups: [
    { group_index: 0, group_name: "Treatment", count: 20, proportion_percent: 50 },
    { group_index: 1, group_name: "Control", count: 20, proportion_percent: 50 },
  ],
};
assert.equal(component.computed.hasMultipleEnrollmentGroups.call(multipleGroupContext), true);
assert.equal(component.computed.singleEnrollmentGroup.call(multipleGroupContext), null);
assert.equal(component.computed.usesStackedEnrollmentAreas.call({
  ...multipleGroupContext,
  hasMultipleEnrollmentGroups: true,
  enrollment: { enrolled_subjects: 40 },
  enrollmentTimeline: [{ date: "2026-10-23" }],
}), false);
assert.equal(component.computed.usesStackedEnrollmentAreas.call({
  ...multipleGroupContext,
  hasMultipleEnrollmentGroups: true,
  enrollment: { enrolled_subjects: 3 },
  enrollmentTimeline: Array.from({ length: 4 }, (_, index) => ({ date: `2026-10-${20 + index}` })),
}), false);
assert.equal(component.computed.usesStackedEnrollmentAreas.call({
  ...multipleGroupContext,
  hasMultipleEnrollmentGroups: true,
  enrollment: { enrolled_subjects: 30 },
  enrollmentTimeline: Array.from({ length: 4 }, (_, index) => ({ date: `2026-10-${20 + index}` })),
}), false);
const fiveGroupContext = {
  enrollmentGroups: Array.from({ length: 5 }, (_, group_index) => ({ group_index, group_name: `g${group_index + 1}` })),
  hasMultipleEnrollmentGroups: true,
  enrollment: { enrolled_subjects: 30 },
  enrollmentTimeline: Array.from({ length: 4 }, (_, index) => ({ date: `2026-10-${20 + index}` })),
};
assert.equal(component.computed.usesStackedEnrollmentAreas.call(fiveGroupContext), true);
assert.equal(component.computed.hasGroupProportionLineHistory.call({
  hasMultipleEnrollmentGroups: true,
  usesStackedEnrollmentAreas: false,
  enrollmentTimeline: [{ date: "2026-10-22" }, { date: "2026-10-23" }],
}), true);

const stepPoints = component.methods.buildStepLinePoints([
  { x: 62, y: 170 },
  { x: 445, y: 95 },
  { x: 828, y: 20 },
]);
assert.equal(stepPoints, "62,170 445,170 445,95 828,95 828,20");

const sparseTimeline = [
  {
    date: "2026-10-08",
    total: 1,
    groups: [
      { group_index: 0, count: 0 },
      { group_index: 1, count: 0 },
      { group_index: 2, count: 1 },
    ],
  },
  {
    date: "2026-10-22",
    total: 2,
    groups: [
      { group_index: 0, count: 0 },
      { group_index: 1, count: 1 },
      { group_index: 2, count: 1 },
    ],
  },
  {
    date: "2026-10-23",
    total: 3,
    groups: [
      { group_index: 0, count: 1 },
      { group_index: 1, count: 1 },
      { group_index: 2, count: 1 },
    ],
  },
];
const sparseGroups = [
  { group_index: 0, group_name: "g1" },
  { group_index: 1, group_name: "g2" },
  { group_index: 2, group_name: "g3" },
];
const chartContext = {
  enrollmentTimeline: sparseTimeline,
  enrollmentGroups: sparseGroups,
  enrollmentChartX: (date) => ({ "2026-10-08": 62, "2026-10-22": 445, "2026-10-23": 828 })[date],
  enrollmentChartY: (value) => 245 - Number(value) * 50,
  enrollmentProportionX: (date) => ({ "2026-10-08": 62, "2026-10-22": 445, "2026-10-23": 828 })[date],
  enrollmentProportionY: component.methods.enrollmentProportionY,
};
const groupSeries = component.computed.enrollmentGroupSeries.call(chartContext);
assert.deepEqual(groupSeries.map((series) => series.chartPoints.map((point) => point.count)), [
  [0, 0, 1],
  [0, 1, 1],
  [1, 1, 1],
]);
const proportionSeries = component.computed.enrollmentProportionSeries.call(chartContext);
assert.equal(proportionSeries.length, 3);
assert.deepEqual(proportionSeries[0].chartPoints.map((point) => point.share_label), ["0%", "0%", "33.3%"]);
assert.deepEqual(proportionSeries[2].chartPoints.map((point) => point.share_label), ["100%", "50%", "33.3%"]);

const areaContext = {};
const areaPoints = component.methods.buildStepAreaPoints.call(
  areaContext,
  [{ date: "a" }, { date: "b" }, { date: "c" }],
  [0, 1, 2],
  [1, 2, 3],
  (date) => ({ a: 0, b: 10, c: 20 })[date],
  (value) => value
);
assert.equal(areaPoints, "0,1 10,1 10,2 20,2 20,3 20,2 20,1 10,1 10,0 0,0");

const studyViewSource = fs.readFileSync(
  path.resolve(__dirname, "../src/components/StudyView.vue"),
  "utf8"
);
assert.match(studyViewSource, /key: "compliance", label: "Compliance view"/);
assert.match(studyViewSource, /<StudyComplianceView/);

console.log("Compliance view tests passed");
