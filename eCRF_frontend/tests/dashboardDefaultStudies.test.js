/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { parse } = require("@vue/compiler-sfc");

const componentPath = path.resolve(__dirname, "../src/components/DashboardComponent.vue");
const source = fs.readFileSync(componentPath, "utf8");
const { descriptor, errors } = parse(source, { filename: componentPath });

assert.deepEqual(errors, []);
assert.ok(descriptor.template);
assert.match(source, /<h1 class="study-management-title">Studies<\/h1>/);
assert.match(source, /<div class="study-dashboard">/);
assert.match(source, /Create study/);
assert.match(source, /Set up or import a new study/);
assert.match(source, /v-if="!authReady \|\| studiesLoading"/);
assert.match(source, /No studies yet/);
assert.match(source, /Create your first study/);
assert.match(source, /No studies assigned/);
assert.match(source, /Unable to load studies/);
assert.match(source, />Retry<\/button>/);
assert.match(source, /No studies found for/);
assert.match(source, /Clear search/);
assert.doesNotMatch(source, /Open Existing Study/);
assert.doesNotMatch(source, /toggleStudyOptions/);
assert.doesNotMatch(source, /showStudyOptions/);
assert.doesNotMatch(source, /query\.openStudies/);
assert.match(source, /this\.loadStudies\(\);/);
assert.match(source, /class="account-menu-toggle"/);
assert.match(source, />Profile<\/span>/);
assert.match(source, />Change password<\/span>/);
assert.match(source, />Logout<\/span>/);
assert.match(source, /openUserSection\(tab\)/);
assert.match(source, /query: \{ tab \}/);
assert.match(source, /isUserManagementRoute\(\)/);

const userInfoPath = path.resolve(__dirname, "../src/components/UserInfoComponent.vue");
const userInfoSource = fs.readFileSync(userInfoPath, "utf8");
const userInfoParseResult = parse(userInfoSource, { filename: userInfoPath });
const studyViewPath = path.resolve(__dirname, "../src/components/StudyView.vue");
const studyViewSource = fs.readFileSync(studyViewPath, "utf8");
const studyViewParseResult = parse(studyViewSource, { filename: studyViewPath });

assert.deepEqual(userInfoParseResult.errors, []);
assert.match(userInfoSource, /const requested = String\(this\.\$route\?\.query\?\.tab \|\| ""\)/);
assert.match(userInfoSource, /const allowedTabs = \["profile", "password"\]/);
assert.doesNotMatch(userInfoSource, /StudySettings/);
assert.doesNotMatch(userInfoSource, /currentTab === 'settings'/);
assert.match(userInfoSource, /const accountTabs = \[/);
assert.match(userInfoSource, /key: "profile", label: "Profile"/);
assert.match(userInfoSource, /key: "password", label: "Change Password"/);
assert.match(userInfoSource, /key: "management", label: "User Management"/);
assert.match(userInfoSource, /key: "studyAccess", label: "Study Access"/);
assert.match(userInfoSource, /accountTabs\.some\(\(tab\) => tab\.key === requested\)/);

assert.deepEqual(studyViewParseResult.errors, []);
assert.match(source, /Show only archived studies/);
assert.match(source, /Show active studies/);
assert.match(source, /class="studies-title-row"/);
assert.match(source, /'archive-filter-toggle'/);
assert.match(source, /type="checkbox"/);
assert.doesNotMatch(source, /archived-studies-toggle/);
assert.match(source, /status: "ARCHIVED"/);
assert.match(source, /\/unarchive`/);
assert.match(studyViewSource, /\/archive`/);
assert.match(studyViewSource, /\/unarchive`/);
assert.match(studyViewSource, /const archivedTabs = new Set\(\["meta", "compliance", "viewdata", "bids"\]\)/);
assert.match(studyViewSource, /Archived studies are read-only/);
assert.match(studyViewSource, /id="archive-study-dialog-title"/);
assert.match(studyViewSource, /Archive this study\?/);
assert.match(studyViewSource, /It will become read-only until it is unarchived/);
assert.match(studyViewSource, /@click="openArchiveStudyDialog"/);
assert.doesNotMatch(studyViewSource, /window\.confirm/);
assert.doesNotMatch(studyViewSource, /archivedTabs\.add\("docs"\)/);
assert.doesNotMatch(studyViewSource, /archivedTabs\.add\("team"\)/);

console.log("Dashboard default studies tests passed");
