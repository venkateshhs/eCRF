<template>
  <Teleport to="body">
    <div v-if="isVisible" class="dialog-overlay">
      <div class="dialog" role="dialog" aria-modal="true">
        <div class="dialog-content">
          <p class="dialog-message">{{ message }}</p>
        </div>
        <div class="dialog-actions">
          <button
            v-if="showCancel"
            @click="cancelDialog"
            class="btn-secondary"
            type="button"
          >
            {{ cancelLabel }}
          </button>
          <button @click="confirmDialog" class="btn-primary" type="button">
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
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
    showCancel: {
      type: Boolean,
      default: false,
    },
    confirmLabel: {
      type: String,
      default: "OK",
    },
    cancelLabel: {
      type: String,
      default: "Cancel",
    },
  },
  emits: ["close", "confirm", "cancel"],
  setup(props, { emit }) {
    function confirmDialog() {
      emit("confirm");
      emit("close");
    }

    function cancelDialog() {
      emit("cancel");
      emit("close");
    }

    return {
      confirmDialog,
      cancelDialog,
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
  gap: 10px;
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
.btn-secondary {
  background: #e5e7eb;
  color: #111827;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.btn-secondary:hover {
  background: #d1d5db;
}
.dialog-message {
  white-space: pre-line;
}
</style>
