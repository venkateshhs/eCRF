/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

const sourcePath = path.resolve(
  __dirname,
  "../src/components/fields/FieldFileUpload.vue"
);
const vueSource = fs.readFileSync(sourcePath, "utf8");
assert.equal(vueSource.includes("window.confirm"), false);
assert.match(vueSource, /<CustomDialog[\s\S]*:showCancel="true"/);
const scriptSource = vueSource
  .match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace('import icons from "@/assets/styles/icons";', "const icons = {};")
  .replace(
    'import CustomDialog from "@/components/CustomDialog.vue";',
    "const CustomDialog = {};"
  );
const transformed = babel.transformSync(scriptSource, {
  filename: sourcePath,
  cwd: path.resolve(__dirname, ".."),
  babelrc: false,
  configFile: false,
  plugins: ["@babel/plugin-transform-modules-commonjs"],
}).code;
const loaded = { exports: {} };
new Function("module", "exports", transformed)(loaded, loaded.exports);
const component = loaded.exports.default;

function makeInstance({ value, isMultiple }) {
  const emitted = [];
  const instance = {
    ...component.methods,
    value,
    isMultiple,
    readonly: false,
    error: "old error",
    localUrl: "https://example.org/file",
    deleteConfirmationVisible: false,
    pendingRemoval: null,
    $emit: (...args) => emitted.push(args),
  };
  return { instance, emitted };
}

const savedFile = {
  source: "local",
  name: "scan.nii.gz",
  size: 42,
  dbId: 17,
};

{
  const { instance, emitted } = makeInstance({
    value: savedFile,
    isMultiple: false,
  });
  instance.clearValue();
  assert.equal(instance.deleteConfirmationVisible, true);
  assert.deepEqual(emitted, []);
  instance.cancelPendingRemoval();
  assert.equal(instance.localUrl, "https://example.org/file");
  assert.equal(instance.deleteConfirmationVisible, false);
}

{
  const { instance, emitted } = makeInstance({
    value: savedFile,
    isMultiple: false,
  });
  instance.clearValue();
  assert.deepEqual(emitted, []);
  instance.confirmPendingRemoval();
  assert.deepEqual(emitted, [
    ["file-removed", savedFile],
    ["input", null],
  ]);
}

{
  const secondFile = {
    source: "local",
    name: "other.nii.gz",
    size: 99,
    dbId: 18,
  };
  const { instance, emitted } = makeInstance({
    value: [savedFile, secondFile],
    isMultiple: true,
  });
  instance.removeLocalAt(0);
  assert.deepEqual(emitted, []);
  instance.confirmPendingRemoval();
  assert.deepEqual(emitted, [
    ["file-removed", savedFile],
    ["input", [secondFile]],
  ]);
}

console.log("FieldFileUpload delete confirmation tests passed");
