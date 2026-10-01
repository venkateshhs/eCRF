/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { markRaw, reactive } = require("vue");

const componentPath = path.resolve(
  __dirname,
  "../src/components/StudyDataEntryComponent.vue"
);
const source = fs.readFileSync(componentPath, "utf8");

assert.match(source, /import \{ markRaw \} from "vue";/);
assert.match(source, /runtimeCommitHandles:\s*markRaw\(new Map\(\)\)/);
assert.match(
  source,
  /this\.runtimeCommitHandles\.get\(key\) !== handle/
);

const unprotectedState = reactive({ handles: new Map() });
const unprotectedHandle = { frameId: null, timerId: null };
unprotectedState.handles.set("field", unprotectedHandle);
assert.notEqual(
  unprotectedState.handles.get("field"),
  unprotectedHandle,
  "Vue proxies objects read from a reactive Map"
);

const protectedState = reactive({ handles: markRaw(new Map()) });
const protectedHandle = { frameId: null, timerId: null };
protectedState.handles.set("field", protectedHandle);
assert.equal(
  protectedState.handles.get("field"),
  protectedHandle,
  "the raw timer registry must preserve identity for the stale-callback guard"
);

console.log("Data-entry runtime commit regression tests passed");
