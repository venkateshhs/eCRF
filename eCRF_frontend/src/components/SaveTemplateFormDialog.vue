<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal save-template-dialog">
      <div class="dialog-header" :class="{ danger: isDeleteMode }">
        <h3>{{ dialogTitle }}</h3>
        <p>{{ dialogSubtitle }}</p>
      </div>

      <div class="dialog-body">
        <!-- MODE OPTIONS -->
        <div class="form-row">
          <label class="field-label">
            {{ isDeleteMode ? "Delete option" : "Save option" }}
          </label>

          <div class="save-type-options">
            <label
              class="save-type-card"
              :class="{ active: formData.type === primaryType, danger: isDeleteMode }"
            >
              <input
                type="radio"
                :value="primaryType"
                v-model="formData.type"
              />

              <span>
                <strong>{{ primaryOptionTitle }}</strong>
                <small>{{ primaryOptionDescription }}</small>
              </span>
            </label>

            <label
              class="save-type-card"
              :class="{ active: formData.type === 'sections', danger: isDeleteMode }"
            >
              <input
                type="radio"
                value="sections"
                v-model="formData.type"
              />

              <span>
                <strong>{{ sectionsOptionTitle }}</strong>
                <small>{{ sectionsOptionDescription }}</small>
              </span>
            </label>
          </div>
        </div>

        <!-- SECTION SELECTION -->
        <div v-if="formData.type === 'sections'" class="form-row">
          <div class="section-select-header">
            <label class="field-label">
              Select sections <span class="required">*</span>
            </label>

            <button
              type="button"
              class="btn-link"
              @click="toggleAllSections"
            >
              {{ allSectionsSelected ? "Deselect all" : "Select all" }}
            </button>
          </div>

          <div v-if="sections.length" class="section-list">
            <label
              v-for="(section, index) in sections"
              :key="section._id || section.title || index"
              class="section-option"
              :class="{ selected: selectedSectionIndexes.has(index), danger: isDeleteMode }"
            >
              <input
                type="checkbox"
                :checked="selectedSectionIndexes.has(index)"
                @change="toggleSection(index)"
              />

              <span>
                <strong>{{ section.title || `Section ${index + 1}` }}</strong>
                <small>
                  {{ getFieldCount(section) }} field{{ getFieldCount(section) === 1 ? "" : "s" }}
                </small>
              </span>
            </label>
          </div>

          <div v-else class="empty-section-state">
            No sections available.
          </div>
        </div>

        <!-- SAVE-ONLY TITLE -->
        <div v-if="!isDeleteMode" class="form-row">
          <label class="field-label">
            Title <span class="required">*</span>
          </label>

          <input
            type="text"
            v-model.trim="formData.title"
            placeholder="Example: Basic Demographics"
          />
        </div>

        <!-- SAVE-ONLY DESCRIPTION -->
        <div v-if="!isDeleteMode" class="form-row">
          <label class="field-label">
            Description <span class="required">*</span>
          </label>

          <textarea
            v-model.trim="formData.description"
            rows="4"
            placeholder="Describe when this reusable template should be used."
          ></textarea>
        </div>

        <!-- DELETE WARNING -->
        <div v-if="isDeleteMode" class="delete-warning">
          <strong>Warning:</strong>
          This action will remove the selected saved template content. This cannot be undone.
        </div>

        <div v-if="error" class="dialog-error">
          {{ error }}
        </div>
      </div>

      <div class="modal-actions save-template-actions">
        <button
          class="btn-primary"
          :class="{ danger: isDeleteMode }"
          :disabled="saving"
          @click="confirm"
        >
          {{ saving ? busyLabel : confirmLabel }}
        </button>

        <button
          class="btn-option"
          :disabled="saving"
          @click="close"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "SaveTemplateFormDialog",

  props: {
    visible: {
      type: Boolean,
      default: false
    },
    mode: {
      type: String,
      default: "save",
      validator: value => ["save", "delete"].includes(value)
    },
    form: {
      type: Object,
      default: () => ({ sections: [] })
    },
    saving: {
      type: Boolean,
      default: false
    }
  },

  emits: ["save", "delete", "close"],

  data() {
    return {
      formData: {
        type: "form",
        title: "",
        description: ""
      },
      selectedSectionIndexes: new Set(),
      error: ""
    };
  },

  computed: {
    isDeleteMode() {
      return this.mode === "delete";
    },

    sections() {
      return Array.isArray(this.form?.sections) ? this.form.sections : [];
    },

    primaryType() {
      return this.isDeleteMode ? "all" : "form";
    },

    dialogTitle() {
      return this.isDeleteMode ? "Delete Saved Template" : "Save Template/Form";
    },

    dialogSubtitle() {
      return this.isDeleteMode
        ? "Delete the whole saved template or only selected sections."
        : "Save the complete form or selected sections as a reusable template.";
    },

    primaryOptionTitle() {
      return this.isDeleteMode ? "Delete everything" : "Save everything";
    },

    primaryOptionDescription() {
      return this.isDeleteMode
        ? "Delete this complete saved template."
        : "Save all sections and fields in this form.";
    },

    sectionsOptionTitle() {
      return this.isDeleteMode ? "Delete selected section(s)" : "Save selected section(s)";
    },

    sectionsOptionDescription() {
      return this.isDeleteMode
        ? "Choose one or more sections to delete."
        : "Choose one or more sections to save.";
    },

    confirmLabel() {
      return this.isDeleteMode ? "Delete" : "Save";
    },

    busyLabel() {
      return this.isDeleteMode ? "Deleting…" : "Saving…";
    },

    allSectionsSelected() {
      return (
        this.sections.length > 0 &&
        this.sections.every((_, index) => this.selectedSectionIndexes.has(index))
      );
    }
  },

  watch: {
    visible(value) {
      if (value) this.resetDialog();
    },

    mode() {
      if (this.visible) this.resetDialog();
    },

    "formData.type"() {
      this.error = "";

      if (
        this.formData.type === "sections" &&
        !this.selectedSectionIndexes.size &&
        this.sections.length
      ) {
        this.selectedSectionIndexes = new Set([0]);
      }
    }
  },

  methods: {
    resetDialog() {
      this.formData = {
        type: this.primaryType,
        title: "",
        description: ""
      };

      this.selectedSectionIndexes = this.sections.length ? new Set([0]) : new Set();
      this.error = "";
    },

    getFieldCount(section) {
      return Array.isArray(section?.fields) ? section.fields.length : 0;
    },

    toggleSection(index) {
      const next = new Set(this.selectedSectionIndexes);

      if (next.has(index)) next.delete(index);
      else next.add(index);

      this.selectedSectionIndexes = next;
      this.error = "";
    },

    toggleAllSections() {
      if (this.allSectionsSelected) {
        this.selectedSectionIndexes = new Set();
      } else {
        this.selectedSectionIndexes = new Set(
          this.sections.map((_, index) => index)
        );
      }

      this.error = "";
    },

    validate() {
      if (!this.sections.length) {
        return this.isDeleteMode
          ? "No sections available to delete."
          : "Cannot save an empty form.";
      }

      if (this.formData.type === "sections" && !this.selectedSectionIndexes.size) {
        return this.isDeleteMode
          ? "Please select at least one section to delete."
          : "Please select at least one section.";
      }

      if (!this.isDeleteMode && !this.formData.title.trim()) {
        return "Title is required.";
      }

      if (!this.isDeleteMode && !this.formData.description.trim()) {
        return "Description is required.";
      }

      return "";
    },

    confirm() {
      const validationError = this.validate();

      if (validationError) {
        this.error = validationError;
        return;
      }

      this.error = "";

      if (this.isDeleteMode) {
        this.$emit("delete", {
          type: this.formData.type,
          sectionIndexes: this.formData.type === "sections"
            ? Array.from(this.selectedSectionIndexes).sort((a, b) => a - b)
            : []
        });
        return;
      }

      this.$emit("save", {
        type: this.formData.type,
        sectionIndexes: this.formData.type === "sections"
          ? Array.from(this.selectedSectionIndexes).sort((a, b) => a - b)
          : [],
        title: this.formData.title.trim(),
        description: this.formData.description.trim()
      });
    },

    close() {
      if (this.saving) return;
      this.$emit("close");
    }
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(17, 24, 39, 0.48);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.modal {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
  color: #111827;
}

.save-template-dialog {
  width: min(680px, calc(100vw - 32px));
  max-height: 88vh;
  overflow: hidden;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  padding: 22px 24px 16px;
  border-bottom: 1px solid #eef2f7;
  background: #ffffff;
}

.dialog-header.danger {
  background: #fff7f7;
  border-bottom-color: #fecaca;
}

.dialog-header h3 {
  margin: 0;
  text-align: center;
  font-size: 21px;
  font-weight: 800;
  color: #111827;
}

.dialog-header.danger h3 {
  color: #991b1b;
}

.dialog-header p {
  margin: 7px auto 0;
  max-width: 460px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.45;
}

.dialog-body {
  padding: 20px 24px;
  overflow: auto;
}

.form-row {
  display: grid;
  gap: 8px;
  margin-bottom: 18px;
}

.field-label {
  font-size: 13px;
  font-weight: 800;
  color: #374151;
}

.form-row input[type="text"],
.form-row textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 11px;
  padding: 11px 12px;
  font-size: 14px;
  color: #111827;
  background: #ffffff;
}

.form-row input[type="text"]:focus,
.form-row textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
}

.form-row textarea {
  resize: vertical;
  min-height: 96px;
}

.save-type-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.save-type-card {
  display: flex;
  gap: 11px;
  align-items: flex-start;
  border: 1px solid #d1d5db;
  border-radius: 14px;
  padding: 14px;
  background: #f9fafb;
  cursor: pointer;
}

.save-type-card:hover {
  background: #f3f4f6;
}

.save-type-card.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.save-type-card.danger.active {
  border-color: #dc2626;
  background: #fef2f2;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.12);
}

.save-type-card input {
  margin-top: 3px;
  flex: 0 0 auto;
}

.save-type-card span {
  display: grid;
  gap: 4px;
}

.save-type-card strong {
  color: #111827;
  font-size: 14px;
  font-weight: 800;
}

.save-type-card small {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
}

.section-select-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.btn-link {
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  padding: 4px 0;
}

.btn-link:hover {
  text-decoration: underline;
}

.section-list {
  display: grid;
  gap: 8px;
  max-height: 230px;
  overflow: auto;
  padding: 2px 3px 2px 0;
}

.section-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 11px 12px;
  background: #ffffff;
  cursor: pointer;
}

.section-option:hover {
  background: #f9fafb;
}

.section-option.selected {
  border-color: #2563eb;
  background: #eff6ff;
}

.section-option.danger.selected {
  border-color: #dc2626;
  background: #fef2f2;
}

.section-option input {
  margin-top: 3px;
  flex: 0 0 auto;
}

.section-option span {
  display: grid;
  gap: 3px;
}

.section-option strong {
  color: #111827;
  font-size: 13px;
  font-weight: 800;
}

.section-option small {
  color: #6b7280;
  font-size: 12px;
}

.empty-section-state {
  padding: 14px;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
  background: #f9fafb;
  color: #6b7280;
  text-align: center;
  font-size: 13px;
}

.delete-warning {
  margin-top: 4px;
  padding: 12px 14px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fef2f2;
  color: #991b1b;
  font-size: 13px;
  line-height: 1.45;
}

.required {
  color: #dc2626;
}

.dialog-error {
  margin-top: 4px;
  padding: 11px 13px;
  border: 1px solid #fecaca;
  border-radius: 11px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 600;
}

.save-template-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 22px;
  border-top: 1px solid #eef2f7;
  background: #f9fafb;
}

.save-template-actions button {
  min-width: 104px;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 800;
}

.btn-primary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #ffffff;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary.danger {
  border-color: #dc2626;
  background: #dc2626;
}

.btn-primary.danger:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-option {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  cursor: pointer;
}

.btn-option:hover:not(:disabled) {
  background: #f3f4f6;
}

.btn-primary:disabled,
.btn-option:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .modal-overlay {
    padding: 14px;
  }

  .save-template-dialog {
    width: 100%;
    max-height: 92vh;
  }

  .save-type-options {
    grid-template-columns: 1fr;
  }

  .dialog-header,
  .dialog-body,
  .save-template-actions {
    padding-left: 16px;
    padding-right: 16px;
  }

  .save-template-actions {
    flex-direction: column;
  }

  .save-template-actions button {
    width: 100%;
  }
}
</style>