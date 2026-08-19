/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function loadModule(relativePath) {
  const sourcePath = path.resolve(__dirname, relativePath);
  const transformed = babel.transformSync(fs.readFileSync(sourcePath, "utf8"), {
    filename: sourcePath,
    cwd: path.resolve(__dirname, ".."),
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const loaded = { exports: {} };
  new Function("module", "exports", "require", transformed)(
    loaded,
    loaded.exports,
    require
  );
  return loaded.exports;
}

const { calculateContainedRevealScrollTop } = loadModule(
  "../src/utils/builderScrollFocus.js"
);

{
  const result = calculateContainedRevealScrollTop({
    scrollTop: 500,
    scrollHeight: 4000,
    clientHeight: 1000,
    containerTop: 100,
    targetTop: 1300,
    targetHeight: 100,
    topClearance: 150,
  });
  assert.equal(result, 1185, "a normal field should be centered in the usable large-screen area");
}

{
  const result = calculateContainedRevealScrollTop({
    scrollTop: 500,
    scrollHeight: 5000,
    clientHeight: 700,
    containerTop: 100,
    targetTop: 1000,
    targetHeight: 900,
    topClearance: 140,
  });
  assert.equal(result, 1260, "a field taller than the viewport should begin below sticky headers");
}

{
  const result = calculateContainedRevealScrollTop({
    scrollTop: 0,
    scrollHeight: 700,
    clientHeight: 1000,
    containerTop: 0,
    targetTop: 400,
    targetHeight: 100,
    topClearance: 120,
  });
  assert.equal(result, 0, "a large viewport with no inner overflow must not move the page");
}

{
  const result = calculateContainedRevealScrollTop({
    scrollTop: 2500,
    scrollHeight: 3000,
    clientHeight: 800,
    containerTop: 50,
    targetTop: 900,
    targetHeight: 120,
    topClearance: 130,
  });
  assert.equal(result, 2200, "the requested position must be clamped to the inner container bottom");
}
