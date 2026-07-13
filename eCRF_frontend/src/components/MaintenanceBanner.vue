<template>
  <div
    v-if="enabled"
    class="maintenance-banner"
    role="status"
    aria-live="polite"
  >
    <div class="maintenance-banner__content">
      <i class="fas fa-tools"></i>

      <div>
        <strong>Scheduled maintenance</strong>

        <div class="maintenance-banner__text">
          The Case-E website will be temporarily unavailable due to
          scheduled maintenance.

          <br />

          <strong>
            Tuesday, 14 July 2026 · 10:00-12:00 CEST
          </strong>

          <br />

          Thank you for your understanding.
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "MaintenanceBanner",

  data() {
    return {
      enabled: false,
    };
  },

  async mounted() {
    await this.checkMaintenance();
  },

  methods: {
    async checkMaintenance() {
      try {
        const response = await fetch(
          `/maintenance.enabled?t=${Date.now()}`,
          {
            cache: "no-store",
          }
        );

        const contentType = response.headers.get("content-type") || "";
        this.enabled = response.ok && !contentType.includes("text/html");
      } catch (e) {
        this.enabled = false;
      }
    },
  },
};
</script>

<style scoped>
.maintenance-banner {
  background: #fff3cd;
  color: #664d03;
  border-bottom: 1px solid #ffecb5;
  padding: 14px 20px;
  font-size: 15px;
}

.maintenance-banner__content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 1200px;
  margin: 0 auto;
}

.maintenance-banner__content i {
  margin-top: 2px;
  font-size: 20px;
}

.maintenance-banner__text {
  margin-top: 4px;
  line-height: 1.5;
}
</style>
