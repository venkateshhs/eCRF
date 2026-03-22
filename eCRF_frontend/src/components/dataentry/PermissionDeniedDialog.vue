<template>
  <div v-if="visible" class="dialog-overlay">
    <div class="dialog">
      <h3>Permission Denied</h3>
      <p>You do not have permission to create a share link. Please contact your administrator.</p>
      <div class="dialog-actions">
        <button @click="$emit('close')">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "PermissionDeniedDialog",
  props: {
    visible: { type: Boolean, default: false },
  },
  emits: ["close"],
};
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.dialog {
  background: #ffffff;
  padding: 1.5rem;
  border-radius: 8px;
  width: 320px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.dialog h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
.dialog-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  background: #e5e7eb;
  color: #1f2937;
}
</style>