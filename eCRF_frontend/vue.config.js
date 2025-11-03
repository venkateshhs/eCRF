const { defineConfig } = require('@vue/cli-service');

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