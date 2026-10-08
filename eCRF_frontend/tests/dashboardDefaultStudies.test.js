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
assert.doesNotMatch(source, /class="dashboard-sidebar"/);
assert.doesNotMatch(source, /sidebar-hidden/);
assert.match(source, /class="account-menu-toggle"/);
assert.match(source, />User management<\/span>/);
assert.match(source, />Logout<\/span>/);
assert.match(source, /query: \{ tab: this\.isAdmin \? "management" : "profile" \}/);

console.log("Dashboard default studies tests passed");
