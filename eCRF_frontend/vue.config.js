const { defineConfig } = require('@vue/cli-service');
const { execFileSync } = require('child_process');
const packageJson = require('./package.json');

function gitValue(args) {
  try {
    return execFileSync('git', args, {
      cwd: __dirname,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return '';
  }
}

const commit = process.env.GITHUB_SHA || gitValue(['rev-parse', 'HEAD']);
const origin = gitValue(['remote', 'get-url', 'origin']);
const githubRepositoryUrl =
  process.env.CASEE_REPOSITORY_URL ||
  (process.env.GITHUB_SERVER_URL && process.env.GITHUB_REPOSITORY
    ? `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}`
    : origin
        .replace(/^git@github\.com:/, 'https://github.com/')
        .replace(/^ssh:\/\/git@github\.com\//, 'https://github.com/')
        .replace(/\.git$/, ''));
const releaseTag =
  process.env.CASEE_VERSION ||
  (process.env.GITHUB_REF_TYPE === 'tag' ? process.env.GITHUB_REF_NAME : '') ||
  gitValue(['describe', '--tags', '--exact-match']);

process.env.VUE_APP_CASEE_VERSION = releaseTag || packageJson.version;
process.env.VUE_APP_CASEE_BUILD_ID =
  process.env.CASEE_BUILD_ID ||
  [process.env.GITHUB_RUN_NUMBER, commit.slice(0, 7)].filter(Boolean).join('-') ||
  'local';
process.env.VUE_APP_CASEE_BUILD_DATE =
  process.env.CASEE_BUILD_DATE || new Date().toISOString();
process.env.VUE_APP_CASEE_COMMIT_URL =
  process.env.CASEE_COMMIT_URL ||
  (commit && githubRepositoryUrl.startsWith('https://github.com/')
    ? `${githubRepositoryUrl}/commit/${commit}`
    : '');

module.exports = defineConfig({
  transpileDependencies: ['shacl-tulip'],

  devServer: {
    proxy: {
      // hit your FastAPI backend for all API paths you actually use
      "/": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
