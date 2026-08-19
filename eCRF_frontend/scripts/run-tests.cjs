const { readdirSync } = require("node:fs");
const { join } = require("node:path");
const { spawnSync } = require("node:child_process");

const testsDirectory = join(__dirname, "..", "tests");
const testFiles = readdirSync(testsDirectory)
  .filter((file) => file.endsWith(".test.js"))
  .sort()
  .map((file) => join(testsDirectory, file));

if (testFiles.length === 0) {
  console.error("No frontend test files were found.");
  process.exit(1);
}

const result = spawnSync(process.execPath, ["--test", ...testFiles], {
  stdio: "inherit",
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
