<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal remap-dialog">
      <div class="remap-header">
        <div>
          <h3>Visibility logic affected</h3>
          <p class="remap-subtitle">
            A removed option was still used in visibility logic.
          </p>
        </div>
      </div>

      <div class="remap-alert">
        <div class="remap-alert-icon">!</div>
        <div class="remap-alert-content">
          The option
          <strong>"{{ oldValue }}"</strong>
          was changed or removed from
          <strong>{{ sourceFieldLabel }}</strong>.
        </div>
      </div>

      <div class="remap-summary">
        <div class="summary-row">
          <span class="summary-label">Dependent field</span>
          <span class="summary-value">{{ dependentFieldLabel }}</span>
        </div>

        <div class="summary-row">
          <span class="summary-label">Rule operator</span>
          <span class="summary-value">{{ operatorLabel }}</span>
        </div>

        <div v-if="isMultiValueRule" class="summary-row">
          <span class="summary-label">Rule type</span>
          <span class="summary-value">Multi-value condition</span>
        </div>
      </div>

      <div class="remap-body">
        <label class="remap-label">Choose action</label>

        <div class="remap-actions-list">
          <label class="remap-radio-row" :class="{ selected: localAction === 'replace' }">
            <input
              type="radio"
              value="replace"
              v-model="localAction"
            />
            <div class="remap-radio-copy">
              <div class="remap-radio-title">Replace with another option</div>
              <div class="remap-radio-desc">
                Keep the visibility rule and point it to a new option value.
              </div>
            </div>
          </label>

          <label class="remap-radio-row" :class="{ selected: localAction === 'remove' }">
            <input
              type="radio"
              value="remove"
              v-model="localAction"
            />
            <div class="remap-radio-copy">
              <div class="remap-radio-title">
                {{ isMultiValueRule ? "Remove this value from the condition" : "Remove this condition" }}
              </div>
              <div class="remap-radio-desc">
                {{
                  isMultiValueRule
                    ? "Only the removed value will be cleared from this rule."
                    : "The affected visibility condition will be removed."
                }}
              </div>
            </div>
          </label>
        </div>

        <div v-if="localAction === 'replace'" class="remap-select-wrap">
          <label class="remap-label">New option</label>
          <select v-model="localReplacement">
            <option disabled value="">Select new option…</option>
            <option v-for="opt in normalizedNextOptions" :key="opt" :value="opt">
              {{ opt }}
            </option>
          </select>
          <div v-if="!normalizedNextOptions.length" class="remap-empty-note">
            No replacement options are currently available.
          </div>
        </div>
      </div>

      <div class="remap-footer">
        <div v-if="queuePositionText" class="remap-footer-note">
          {{ queuePositionText }}
        </div>

        <div class="modal-actions">
          <button class="btn-option" @click="$emit('cancel')">Cancel</button>
          <button
            class="btn-primary"
            @click="submitChoice"
            :disabled="localAction === 'replace' && !normalizedNextOptions.length"
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "FieldOptionRemapDialog",
  props: {
    visible: { type: Boolean, default: false },
    sourceFieldLabel: { type: String, default: "" },
    currentItem: { type: Object, default: null },
    nextOptions: { type: Array, default: () => [] },
    currentIndex: { type: Number, default: 0 },
    queueLength: { type: Number, default: 0 },
  },
  data() {
    return {
      localAction: "replace",
      localReplacement: "",
    };
  },
  computed: {
    normalizedNextOptions() {
      return (Array.isArray(this.nextOptions) ? this.nextOptions : [])
        .map(v => String(v || "").trim())
        .filter(Boolean);
    },
    oldValue() {
      return String(this.currentItem?.oldValue || "");
    },
    dependentFieldLabel() {
      const dep = this.currentItem?.dep;
      const sectionTitle = dep?.section?.title || `Section ${(dep?.sectionIndex ?? 0) + 1}`;
      const fieldTitle =
        dep?.field?.label ||
        dep?.field?.name ||
        `Field ${(dep?.fieldIndex ?? 0) + 1}`;
      return `${sectionTitle} → ${fieldTitle}`;
    },
    currentRule() {
      const dep = this.currentItem?.dep;
      const idx = this.currentItem?.resolvedRuleIndex;
      const rules = dep?.field?.constraints?.visibilityLogic?.rules;
      if (!Array.isArray(rules)) return null;
      if (!Number.isInteger(idx)) return null;
      return rules[idx] || null;
    },
    operatorLabel() {
      return String(this.currentRule?.operator || "eq");
    },
    isMultiValueRule() {
      return !!this.currentItem?.multiple;
    },
    queuePositionText() {
      if (!this.queueLength || this.queueLength <= 1) return "";
      return `Dependency ${this.currentIndex + 1} of ${this.queueLength}`;
    }
  },
  watch: {
    visible: {
      immediate: true,
      handler(v) {
        if (v) {
          this.localAction = "replace";
          this.localReplacement = "";
        }
      }
    },
    currentItem: {
      immediate: true,
      handler() {
        this.localAction = "replace";
        this.localReplacement = "";
      }
    }
  },
  methods: {
    submitChoice() {
      if (this.localAction === "replace" && !this.localReplacement) {
        this.$emit("validation-error", "Please select a replacement option.");
        return;
      }

      this.$emit("confirm", {
        action: this.localAction,
        replacement: this.localAction === "replace" ? this.localReplacement : "",
      });
    }
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1400;
  padding: 20px;
}

.modal.remap-dialog {
  width: min(620px, 96vw);
  background: #ffffff;
  border-radius: 14px;
  padding: 22px;
  max-height: 88vh;
  overflow-y: auto;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.18);
  border: 1px solid #e5e7eb;
}

.remap-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.remap-header h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  color: #111827;
}

.remap-subtitle {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.remap-alert {
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: 12px;
  align-items: start;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
}

.remap-alert-icon {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fdba74;
  color: #7c2d12;
  font-weight: 700;
  font-size: 18px;
  line-height: 1;
}

.remap-alert-content {
  color: #7c2d12;
  line-height: 1.55;
  font-size: 14px;
}

.remap-summary {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
  display: grid;
  gap: 10px;
}

.summary-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 12px;
  align-items: start;
}

.summary-label {
  color: #6b7280;
  font-size: 13px;
  font-weight: 600;
}

.summary-value {
  color: #111827;
  font-size: 14px;
  word-break: break-word;
}

.remap-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.remap-label {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.remap-actions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.remap-radio-row {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 12px;
  align-items: start;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.remap-radio-row:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.remap-radio-row.selected {
  border-color: #93c5fd;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.remap-radio-row input {
  margin: 2px 0 0;
  accent-color: #2563eb;
}

.remap-radio-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.remap-radio-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.remap-radio-desc {
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.remap-select-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.remap-select-wrap select {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #fff;
  box-sizing: border-box;
  color: #111827;
  font-size: 14px;
}

.remap-select-wrap select:focus {
  outline: none;
  border-color: #60a5fa;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.remap-empty-note {
  font-size: 12px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 8px 10px;
}

.remap-footer {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.remap-footer-note {
  font-size: 12px;
  color: #6b7280;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-option,
.btn-primary {
  min-width: 110px;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.04s ease, background 0.16s ease, border-color 0.16s ease, opacity 0.16s ease;
}

.btn-option:active,
.btn-primary:active {
  transform: scale(0.98);
}

.btn-option {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  color: #111827;
}

.btn-option:hover {
  background: #e5e7eb;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  border: none;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .modal.remap-dialog {
    padding: 18px;
    border-radius: 12px;
  }

  .summary-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }

  .modal-actions {
    justify-content: stretch;
  }

  .btn-option,
  .btn-primary {
    flex: 1 1 100%;
  }
}
</style>