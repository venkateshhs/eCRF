<template>
  <teleport to="body">
    <div v-if="visible" class="previous-visit-overlay" @click.self="$emit('close')">
      <div class="previous-visit-modal">
        <h3>Import from Previous Visits</h3>
        <p class="subtext">
          Field: <strong>{{ fieldLabel || "Field" }}</strong>
        </p>

        <div v-if="!options.length" class="empty-state">
          No previous recorded values were found for this field.
        </div>

        <div v-else class="import-options-list">
          <button
            v-for="opt in options"
            :key="opt.key"
            type="button"
            class="import-option-card"
            @click="$emit('select', opt)"
          >
            <div class="import-option-top">
              <strong>{{ opt.visitLabel }}</strong>
              <span v-if="opt.createdAtLabel" class="meta">{{ opt.createdAtLabel }}</span>
            </div>

            <div class="import-option-value">
              {{ formatValue(opt.displayValue) }}
            </div>

            <div class="import-option-meta">
              <span v-if="opt.versionLabel">{{ opt.versionLabel }}</span>
            </div>
          </button>
        </div>

        <div class="modal-actions">
          <button class="btn-option" @click="$emit('close')">Cancel</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script>
/* eslint-disable */
export default {
  name: "PreviousVisitImportDialog",
  props: {
    visible: { type: Boolean, default: false },
    fieldLabel: { type: String, default: "" },
    options: { type: Array, default: () => [] },
  },
  methods: {
    formatValue(value) {
      if (Array.isArray(value)) {
        return value.length ? value.join(", ") : "(empty)";
      }
      if (typeof value === "boolean") {
        return value ? "Checked" : "Unchecked";
      }
      if (value == null) return "(empty)";
      if (typeof value === "object") {
        try {
          return JSON.stringify(value);
        } catch {
          return "(complex value)";
        }
      }
      const text = String(value).trim();
      return text || "(empty)";
    },
  },
};
</script>

<style scoped>
.previous-visit-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.previous-visit-modal {
  width: min(720px, 96vw);
  max-height: 85vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
}

.subtext {
  margin: 6px 0 14px;
  color: #6b7280;
  font-size: 14px;
}

.empty-state {
  padding: 14px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  background: #f9fafb;
}

.import-options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.import-option-card {
  width: 100%;
  text-align: left;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  cursor: pointer;
}

.import-option-card:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.import-option-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.import-option-value {
  font-size: 14px;
  color: #111827;
  word-break: break-word;
}

.import-option-meta,
.meta {
  font-size: 12px;
  color: #6b7280;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.btn-option {
  background: #e5e7eb;
  color: #111827;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
}
</style>