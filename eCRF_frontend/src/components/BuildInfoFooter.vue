<template>
  <footer class="build-info" aria-label="Application version">
    Case-E · Version {{ version }} · Build
    <a
      v-if="commitUrl"
      :href="commitUrl"
      target="_blank"
      rel="noopener noreferrer"
      :aria-label="`Open build ${buildId} on GitHub`"
    >{{ buildId }}</a>
    <span v-else>{{ buildId }}</span>
    · Updated {{ buildDate }}
  </footer>
</template>

<script>
export default {
  name: "BuildInfoFooter",
  data() {
    return {
      version: process.env.VUE_APP_CASEE_VERSION || "development",
      buildId: process.env.VUE_APP_CASEE_BUILD_ID || "local",
      commitUrl: process.env.VUE_APP_CASEE_COMMIT_URL || "",
    };
  },
  computed: {
    buildDate() {
      const value = process.env.VUE_APP_CASEE_BUILD_DATE;
      const date = value ? new Date(value) : null;

      if (!date || Number.isNaN(date.getTime())) return "unknown";

      return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    },
  },
};
</script>

<style scoped>
.build-info {
  padding: 16px 12px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
  text-align: center;
}

.build-info a {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.build-info a:hover {
  color: #374151;
}
</style>
