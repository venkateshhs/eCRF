/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

const sourcePath = path.resolve(
  __dirname,
  "../src/utils/constraintEditState.js"
);
const transformed = babel.transformSync(fs.readFileSync(sourcePath, "utf8"), {
  filename: sourcePath,
  cwd: path.resolve(__dirname, ".."),
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const loaded = { exports: {} };
new Function("module", "exports", transformed)(loaded, loaded.exports);

const { constraintEditSnapshot, constraintsForSave } = loaded.exports;

const initialSnapshot = constraintEditSnapshot({
  required: false,
  visibilityLogic: {
    action: "show",
    match: "all",
    rules: [],
    _sectionKey: "ui-only",
  },
});
const sameSnapshot = constraintEditSnapshot({
  required: false,
  visibilityLogic: {
    action: "show",
    match: "all",
    rules: [],
    _sectionKey: "changed-ui-only",
  },
});

assert.equal(initialSnapshot, sameSnapshot);
assert.deepEqual(
  constraintsForSave({
    generated: {
      required: false,
      visibilityLogic: { action: "show", match: "all", rules: [] },
    },
    original: {},
    initialSnapshot,
    currentSnapshot: sameSnapshot,
    sameType: true,
    choiceMembershipUnchanged: true,
    finalOptions: ["B", "A"],
  }),
  {}
);

assert.deepEqual(
  constraintsForSave({
    generated: { required: true },
    original: {},
    initialSnapshot,
    currentSnapshot: constraintEditSnapshot({ required: true }),
    sameType: true,
  }),
  { required: true }
);

assert.deepEqual(
  constraintsForSave({
    generated: { defaultValue: "", options: ["B", "A"] },
    original: { defaultValue: "", options: ["A", "B"] },
    initialSnapshot,
    currentSnapshot: sameSnapshot,
    sameType: true,
    choiceMembershipUnchanged: true,
    finalOptions: ["B", "A"],
  }),
  { defaultValue: "", options: ["B", "A"] }
);

assert.deepEqual(
  constraintsForSave({
    generated: { defaultValue: "", options: ["A", "C"] },
    original: {},
    initialSnapshot,
    currentSnapshot: sameSnapshot,
    sameType: true,
    choiceMembershipUnchanged: false,
    finalOptions: ["A", "C"],
  }),
  { defaultValue: "", options: ["A", "C"] }
);

console.log("constraintEditState tests passed");
