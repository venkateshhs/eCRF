<template>
  <div id="app">
    <MaintenanceBanner />
    <router-view />
  </div>
</template>

<script>
import MaintenanceBanner from "./components/MaintenanceBanner.vue";

export default {
  name: "App",
  components: {
    MaintenanceBanner,
  },
};
</script>
