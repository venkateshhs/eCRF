<template>
  <div v-if="visible" class="share-dialog-overlay" @click.self="handleClose">
    <div class="share-dialog">
      <div class="dialog-header">
        <div>
          <h3>Create Shareable Link</h3>
          <p class="dialog-subtitle">
            Choose permission, expiry and which sections should be visible in the shared link.
          </p>
        </div>

        <button
          type="button"
          class="icon-close"
          @click="handleClose"
          aria-label="Close share dialog"
        >
          ×
        </button>
      </div>

      <div class="share-info-card">
        <div class="info-row">
          <span class="info-label">Subject</span>
          <span class="info-value">{{ subjectLabel }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Visit</span>
          <span class="info-value">{{ visitLabel }}</span>
        </div>
      </div>

      <div class="form-grid">
        <div class="form-row">
          <label for="share-permission">Permission</label>
          <select id="share-permission" v-model="localPermission">
            <option value="view">View</option>
            <option value="add">Add Data</option>
          </select>
        </div>

        <div class="form-row">
          <label for="share-max-uses">Max Uses</label>
          <input
            id="share-max-uses"
            type="number"
            min="1"
            v-model.number="localMaxUses"
          />
        </div>

        <div class="form-row">
          <label for="share-expires-days">Expires (days)</label>
          <input
            id="share-expires-days"
            type="number"
            min="1"
            v-model.number="localExpiresInDays"
          />
        </div>
      </div>

      <div class="form-row">
        <div class="sections-header">
          <label>Allowed Sections</label>

          <div class="sections-actions">
            <button type="button" class="btn-link" @click="selectAllSections">
              Select All
            </button>
            <button type="button" class="btn-link" @click="clearAllSections">
              Clear All
            </button>
          </div>
        </div>

        <div class="share-sections-box">
          <div
            v-if="normalizedSections.length"
            class="share-sections-list"
          >
            <label
              v-for="sec in normalizedSections"
              :key="sec.id"
              class="share-section-row"
            >
              <input
                type="checkbox"
                :value="sec.id"
                v-model="selectedSectionIds"
              />
              <span class="section-title">{{ sec.title }}</span>
            </label>
          </div>

          <div v-else class="share-sections-empty">
            No sections available.
          </div>
        </div>

        <div class="selection-hint">
          {{ selectedSectionIds.length }} section(s) selected
        </div>
      </div>

      <div v-if="generatedLink" class="generated-link-card">
        <label class="generated-label">Generated Link</label>

        <div class="generated-link-row">
          <input
            class="generated-link-input"
            type="text"
            :value="generatedLink"
            readonly
          />
          <button type="button" class="btn-copy" @click="$emit('copy')">
            Copy
          </button>
        </div>

        <div v-if="copyStatus" class="copy-status">
          {{ copyStatus }}
        </div>
      </div>

      <div class="dialog-actions">
        <button type="button" class="btn-secondary" @click="handleClose">
          Cancel
        </button>

        <button
          v-if="!generatedLink"
          type="button"
          class="btn-primary"
          @click="onGenerate"
        >
          Generate Link
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "StudyShareDialog",

  props: {
    visible: { type: Boolean, default: false },
    subjectLabel: { type: String, default: "N/A" },
    visitLabel: { type: String, default: "N/A" },

    permission: { type: String, default: "view" },
    maxUses: { type: Number, default: 1 },
    expiresInDays: { type: Number, default: 7 },

    availableSections: {
      type: Array,
      default: () => [],
    },

    generatedLink: { type: String, default: "" },
    copyStatus: { type: String, default: "" },
  },

  emits: ["close", "generate", "copy"],

  data() {
    return {
      localPermission: "view",
      localMaxUses: 1,
      localExpiresInDays: 7,
      selectedSectionIds: [],
    };
  },

  computed: {
    normalizedSections() {
      return (this.availableSections || [])
        .map((s, idx) => ({
          id: String(s?.id || `section-${idx}`).trim(),
          title: s?.title || s?.label || `Section ${idx + 1}`,
        }))
        .filter((s) => s.id);
    },
  },

  watch: {
    visible: {
      immediate: true,
      handler(val) {
        if (val) {
          this.localPermission = this.permission || "view";
          this.localMaxUses = Number(this.maxUses) || 1;
          this.localExpiresInDays = Number(this.expiresInDays) || 7;
          this.selectedSectionIds = this.normalizedSections.map((s) => s.id);
        }
      },
    },

    availableSections: {
      immediate: true,
      deep: true,
      handler() {
        const validIds = this.normalizedSections.map((s) => s.id);

        if (!this.selectedSectionIds.length) {
          this.selectedSectionIds = [...validIds];
          return;
        }

        this.selectedSectionIds = this.selectedSectionIds.filter((id) =>
          validIds.includes(id)
        );
      },
    },
  },

  methods: {
    handleClose() {
      this.$emit("close");
    },

    selectAllSections() {
      this.selectedSectionIds = this.normalizedSections.map((s) => s.id);
    },

    clearAllSections() {
      this.selectedSectionIds = [];
    },

    onGenerate() {
      this.$emit("generate", {
        permission: this.localPermission,
        maxUses: Math.max(1, Number(this.localMaxUses) || 1),
        expiresInDays: Math.max(1, Number(this.localExpiresInDays) || 7),
        allowed_section_ids: [...this.selectedSectionIds],
      });
    },
  },
};
</script>

<style scoped>
.share-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.share-dialog {
  width: min(640px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
  padding: 22px;
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.dialog-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.dialog-subtitle {
  margin: 6px 0 0 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.45;
}

.icon-close {
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
}

.icon-close:hover {
  background: #f3f4f6;
  color: #111827;
}

.share-info-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}

.info-row + .info-row {
  margin-top: 8px;
}

.info-label {
  color: #6b7280;
  font-weight: 600;
}

.info-value {
  color: #111827;
  font-weight: 500;
  text-align: right;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.form-row {
  margin-bottom: 14px;
}

.form-row label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.form-row input,
.form-row select {
  width: 100%;
  min-height: 40px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  color: #111827;
  background: #ffffff;
  box-sizing: border-box;
}

.form-row input:focus,
.form-row select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.sections-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.sections-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-link {
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.btn-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.share-sections-box {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
  padding: 10px;
}

.share-sections-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}

.share-section-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
}

.share-section-row:hover {
  background: #f3f4f6;
}

.share-section-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin: 0;
  flex: 0 0 auto;
}

.section-title {
  font-size: 14px;
  color: #111827;
}

.share-sections-empty {
  padding: 12px;
  font-size: 13px;
  color: #6b7280;
  text-align: center;
}

.selection-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.generated-link-card {
  margin-top: 10px;
  margin-bottom: 8px;
  padding: 12px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 10px;
}

.generated-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1e3a8a;
}

.generated-link-row {
  display: flex;
  gap: 10px;
}

.generated-link-input {
  flex: 1;
  min-width: 0;
  min-height: 40px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
  color: #111827;
}

.copy-status {
  margin-top: 8px;
  font-size: 12px;
  color: #15803d;
  font-weight: 600;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-primary,
.btn-secondary,
.btn-copy {
  min-height: 40px;
  border-radius: 8px;
  padding: 0 14px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: none;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-secondary {
  background: #f3f4f6;
  color: #111827;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-copy {
  background: #111827;
  color: #ffffff;
  border: none;
  white-space: nowrap;
}

.btn-copy:hover {
  background: #1f2937;
}

@media (max-width: 640px) {
  .share-dialog {
    padding: 16px;
    border-radius: 12px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .generated-link-row {
    flex-direction: column;
  }

  .dialog-actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary,
  .btn-copy {
    width: 100%;
  }
}
</style>