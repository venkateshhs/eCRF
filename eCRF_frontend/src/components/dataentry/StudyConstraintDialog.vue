<template>
  <div v-if="visible" class="mini-overlay" @click.self="$emit('close')">
    <div class="mini-dialog" role="dialog" aria-modal="true">
      <div class="mini-head">
        <h4 class="mini-title">{{ title }}</h4>
        <button class="mini-close" @click="$emit('close')" aria-label="Close">✕</button>
      </div>
      <ul class="mini-list">
        <li v-for="(line, idx) in items" :key="idx">{{ line }}</li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: "StudyConstraintDialog",
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: "" },
    items: { type: Array, default: () => [] },
  },
  emits: ["close"],
};
</script>

<style scoped>
.mini-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.mini-dialog {
  width: 360px;
  max-width: 92%;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  padding: 12px 12px 10px;
}
.mini-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.mini-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}
.mini-close {
  background: transparent;
  border: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}
.mini-close:hover {
  color: #111827;
}
.mini-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 14px;
}
.mini-list li {
  margin: 4px 0;
}
</style>