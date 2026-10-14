/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { parse } = require("@vue/compiler-sfc");

function readVue(relativePath) {
  const componentPath = path.resolve(__dirname, relativePath);
  const source = fs.readFileSync(componentPath, "utf8");
  const { errors } = parse(source, { filename: componentPath });
  assert.deepEqual(errors, []);
  return source;
}

const creationSource = readVue("../src/components/StudyCreationComponent.vue");
const matrixSource = readVue("../src/components/ProtocolMatrix.vue");
const dashboardSource = readVue("../src/components/DashboardComponent.vue");

// The generator must distinguish persisted studies from the original create
// flow and retain the subject currently occupying each persisted position.
assert.match(creationSource, /if \(isEditing\.value\) \{/);
assert.match(creationSource, /const nextSubjects = existingSubjects\.slice\(0, N\);/);
assert.match(creationSource, /for \(let idx = currentCount; idx < N; idx \+= 1\)/);
assert.match(creationSource, /getNextSubjectSequenceNumber\(/);

// The exact ID configuration must survive draft creation, dashboard reload,
// edit hydration, and protocol-matrix publication.
assert.match(creationSource, /subjectIdConfig: _deepClone\(subjectIdConfig\.value \|\| null\)/);
assert.match(creationSource, /subjectIdConfig: _deepClone\(sd\.subjectIdConfig \|\| null\)/);
assert.match(dashboardSource, /subjectIdConfig: sd\.subjectIdConfig \|\| null/);
assert.match(matrixSource, /subjectIdConfig: studyDetails\.subjectIdConfig \|\| null/);

// Protocol Matrix should surface the backend validation detail instead of
// replacing it with a generic HTTP 400 message.
assert.match(matrixSource, /error\?\.response\?\.data\?\.detail/);

console.log("Draft subject identity regression tests passed");
