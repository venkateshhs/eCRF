const { defineConfig } = require('@vue/cli-service')
module.exports = {
  devServer: {
    proxy: {
      "/users": {
        target: "http://127.0.0.1:8000", // Backend URL
        changeOrigin: true, // Handle cross-origin
        secure: false,     // Allow insecure backend
      },
    },
  },
};