<template>
  <div v-if="isVisible" class="dialog-overlay">
    <div class="dialog">
      <div class="dialog-content">
        <p>{{ message }}</p>
      </div>
      <div class="dialog-actions">
        <button @click="closeDialog" class="btn-primary">OK</button>
      </div>
    </div>
  </div>
</template>

<script>


export default {
  name: "CustomDialog",
  props: {
    message: {
      type: String,
      required: true,
    },
    isVisible: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["close"],
  setup(props, { emit }) {
    function closeDialog() {
      emit("close");
    }

    return {
      closeDialog,
    };
  },
};
</script>

<style scoped lang="scss">
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.dialog-content {
  margin-bottom: 20px;
  font-size: 16px;
  color: #333;
  text-align: center;
}

.dialog-actions {
  display: flex;
  justify-content: center;
}

.btn-primary {
  background: #007bff;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary:hover {
  background: #0056b3;
}
</style>
