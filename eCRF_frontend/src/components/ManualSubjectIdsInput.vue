<template>
  <div class="manual-ids">
    <div class="manual-ids-header">
      <div>
        <h4>{{ csvOnly ? "Import subject IDs" : "Add subject IDs" }}</h4>
        <p>
          {{ csvOnly
            ? "Import assigned IDs from CSV or Excel (.xls, .xlsx)."
            : "Enter one or more assigned IDs, or import them from CSV or Excel." }}
          Letter case and leading zeros are preserved.
        </p>
      </div>
      <span class="subject-count-pill">{{ modelValue.length }} {{ modelValue.length === 1 ? "ID" : "IDs" }}</span>
    </div>

    <div v-if="!csvOnly" class="manual-entry-panel">
      <div v-if="!modelValue.length" class="empty-state">
        No subject IDs added yet.
      </div>
      <div v-for="(id, index) in modelValue" :key="index" class="id-row">
        <span class="id-number">{{ index + 1 }}</span>
        <label class="id-field" :for="`manual-subject-${index}`">
          <span>Subject ID</span>
          <input
            :id="`manual-subject-${index}`"
            ref="subjectInputs"
            :value="id"
            :disabled="disabled || index < lockedCount"
            :class="{ invalid: !!rowError(index) }"
            maxlength="128"
            placeholder="e.g. ARIA08LE"
            autocomplete="off"
            @input="updateId(index, $event.target.value)"
          />
          <small v-if="rowError(index)" class="row-error">{{ rowError(index) }}</small>
        </label>
        <button
          v-if="index >= lockedCount"
          type="button"
          class="btn-option remove-id-btn"
          :disabled="disabled"
          :aria-label="`Remove Subject ID ${index + 1}`"
          @click="removeId(index)"
        >Remove</button>
        <span v-else class="saved-pill">Saved</span>
      </div>

      <button type="button" class="btn-option add-id-btn" :disabled="disabled" @click="addId">
        + Add another subject
      </button>
    </div>

    <div v-if="!csvOnly" class="choice-divider"><span>or</span></div>

    <div class="import-panel">
      <div class="import-copy">
        <strong>Import from a file</strong>
        <span>CSV, XLS or XLSX · maximum 5 MB</span>
      </div>
      <label class="btn-option file-picker" :class="{ disabled }">
        Choose file
        <input
          type="file"
          accept=".csv,.xls,.xlsx,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          :disabled="disabled"
          @change="readFile"
        />
      </label>
    </div>

    <label v-if="workbook" class="select-field">
      <span>Select worksheet</span>
      <select v-model="sheetName" :disabled="disabled" @change="selectSheet">
        <option v-for="name in workbook.SheetNames" :key="name" :value="name">{{ name }}</option>
      </select>
    </label>
    <div v-if="csv" class="csv-preview">
      <label class="select-field">
        <span>Select the Subject ID column</span>
        <select v-model.number="column" @change="selectedRows = []">
          <option :value="-1" disabled>Select column…</option>
          <option v-for="(header, index) in csv.headers" :key="index" :value="index">{{ header }} ({{ index + 1 }})</option>
        </select>
      </label>
      <template v-if="column >= 0">
        <div class="selection-toolbar">
          <label class="check-label">
            <input type="checkbox" :checked="allRowsSelected" @change="selectAll($event.target.checked)" />
            Select all IDs
          </label>
          <span>{{ selectedRows.length }} of {{ csv.rows.length }} selected</span>
        </div>
        <div class="csv-rows">
          <label v-for="(row, index) in csv.rows" :key="index" class="csv-row">
            <input v-model="selectedRows" type="checkbox" :value="index" />
            <span class="csv-row-number">Row {{ index + 2 }}</span>
            <span class="csv-id-value">{{ row[column] || "(empty)" }}</span>
          </label>
        </div>
        <button class="btn-primary import-btn" type="button" :disabled="disabled || !selectedRows.length" @click="importIds">
          Import {{ selectedRows.length }} selected {{ selectedRows.length === 1 ? "ID" : "IDs" }}
        </button>
      </template>
    </div>
    <p v-if="error" role="alert" class="error-message">{{ error }}</p>
    <p v-else-if="validationError" role="alert" class="error-message">{{ validationError }}</p>
    <p class="privacy-note">Only the selected ID column is imported. Other columns and worksheets are not saved.</p>
  </div>
</template>
<script>
import { markRaw } from "vue";
import {
  duplicateSubjectIds,
  parseSubjectIdCsv,
  readSubjectIdWorkbook,
  parseSubjectIdWorksheet,
  validateManualSubjectIds,
} from "@/utils/manualSubjectIds";
export default {
  name: "ManualSubjectIdsInput",
  props: {
    modelValue: { type: Array, default: () => [] },
    existingIds: { type: Array, default: () => [] },
    lockedCount: { type: Number, default: 0 },
    disabled: { type: Boolean, default: false },
    csvOnly: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  data: () => ({ csv: null, workbook: null, sheetName: "", column: -1, selectedRows: [], error: "", readVersion: 0 }),
  computed: {
    validationError() { return this.modelValue.length ? validateManualSubjectIds(this.modelValue, this.existingIds) : ""; },
    allRowsSelected() {
      return !!this.csv?.rows?.length && this.selectedRows.length === this.csv.rows.length;
    },
  },
  methods: {
    emitIds(ids) { if (!this.disabled) { this.error = ""; this.$emit("update:modelValue", ids); } },
    addId() {
      if (this.disabled) return;
      this.emitIds([...this.modelValue, ""]);
      this.$nextTick(() => {
        const inputs = this.$refs.subjectInputs;
        const input = Array.isArray(inputs) ? inputs[inputs.length - 1] : inputs;
        input?.focus();
      });
    },
    rowError(index) {
      const value = String(this.modelValue[index] ?? "").trim();
      if (!value) return "Subject ID is required.";
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(value)) {
        return "Use letters, numbers, hyphens or underscores.";
      }
      const normalized = value.toLowerCase();
      if (this.existingIds.some(id => String(id).trim().toLowerCase() === normalized)) {
        return "This Subject ID already exists.";
      }
      if (this.modelValue.some((id, candidateIndex) =>
        candidateIndex !== index && String(id).trim().toLowerCase() === normalized
      )) return "Subject IDs must be unique.";
      return "";
    },
    updateId(index, value) { const ids = [...this.modelValue]; ids[index] = value; this.emitIds(ids); },
    removeId(index) { this.emitIds(this.modelValue.filter((_, i) => i !== index)); },
    async readFile(event) {
      const file = event.target.files?.[0];
      const version = ++this.readVersion;
      this.csv = null; this.workbook = null; this.sheetName = "";
      this.column = -1; this.selectedRows = []; this.error = "";
      if (!file) return;
      try {
        if (file.size > 5 * 1024 * 1024) throw new Error("Please use a file smaller than 5 MB.");
        const extension = file.name.split(".").pop().toLowerCase();
        if (extension === "csv") {
          const parsed = parseSubjectIdCsv(await file.text());
          if (version === this.readVersion) this.csv = parsed;
        } else if (["xls", "xlsx"].includes(extension)) {
          const workbook = readSubjectIdWorkbook(await file.arrayBuffer());
          if (version !== this.readVersion) return;
          this.workbook = markRaw(workbook);
          this.sheetName = workbook.SheetNames[0];
          this.selectSheet();
        } else {
          throw new Error("Choose a .csv, .xls or .xlsx file.");
        }
      } catch (error) { if (version === this.readVersion) this.error = error.message; }
      event.target.value = "";
    },
    selectSheet() {
      this.csv = null; this.column = -1; this.selectedRows = []; this.error = "";
      try { this.csv = parseSubjectIdWorksheet(this.workbook, this.sheetName); }
      catch (error) { this.error = error.message; }
    },
    selectAll(checked) { this.selectedRows = checked ? this.csv.rows.map((_, index) => index) : []; },
    importIds() {
      const incoming = [...this.selectedRows].sort((a, b) => a - b).map(index => String(this.csv.rows[index][this.column] ?? "").trim());
      // An untouched blank input is not an enrolled subject.
      const current = this.modelValue.filter((id, index) => index < this.lockedCount || String(id).trim());
      const combined = [...current, ...incoming];
      const duplicates = duplicateSubjectIds(combined, this.existingIds);
      if (duplicates.length) {
        this.error = `Import stopped. Duplicate Subject IDs: ${duplicates.map(id => `"${id}"`).join(", ")}. Remove or deselect the duplicates and try again. No subject IDs were changed.`;
        return;
      }
      this.error = validateManualSubjectIds(combined, this.existingIds);
      if (this.error) return;
      this.emitIds(combined); this.csv = null; this.workbook = null; this.sheetName = ""; this.selectedRows = [];
    },
  },
};
</script>
<style scoped>
.manual-ids {
  margin-top: 12px;
  padding: 16px;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #f8fafc;
  color: #334155;
}
.manual-ids-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.manual-ids-header h4 { margin: 0; color: #111827; font-size: 15px; }
.manual-ids-header p { margin: 5px 0 0; color: #64748b; font-size: 13px; line-height: 1.45; }
.subject-count-pill, .saved-pill {
  flex: 0 0 auto; padding: 4px 9px; border-radius: 999px; background: #e0e7ff;
  color: #3730a3; font-size: 12px; font-weight: 700;
}
.manual-entry-panel { display: grid; gap: 10px; margin-top: 16px; }
.empty-state { padding: 14px; border: 1px dashed #cbd5e1; border-radius: 8px; color: #64748b; text-align: center; }
.id-row {
  display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 10px;
  align-items: start; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff;
}
.id-number {
  display: grid; place-items: center; width: 26px; height: 26px; margin-top: 20px;
  border-radius: 50%; background: #eef2ff; color: #4338ca; font-size: 12px; font-weight: 700;
}
.id-field, .select-field { display: grid; gap: 6px; font-size: 13px; font-weight: 700; color: #374151; }
.id-field input, .select-field select {
  width: 100%; min-height: 40px; box-sizing: border-box; padding: 8px 10px;
  border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; color: #111827; font: inherit;
}
.id-field input:focus, .select-field select:focus { outline: 2px solid rgba(37, 99, 235, .16); border-color: #2563eb; }
.id-field input.invalid { border-color: #dc2626; }
.row-error { color: #b91c1c; font-size: 12px; font-weight: 600; }
.remove-id-btn { align-self: center; margin-top: 18px; color: #b91c1c; }
.add-id-btn { justify-self: start; }
.choice-divider { display: flex; align-items: center; gap: 10px; margin: 15px 0; color: #94a3b8; font-size: 12px; }
.choice-divider::before, .choice-divider::after { content: ""; height: 1px; flex: 1; background: #dbe3ef; }
.import-panel {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 13px; border: 1px solid #dbe3ef; border-radius: 8px; background: #fff;
}
.import-copy { display: grid; gap: 3px; }
.import-copy strong { color: #1f2937; font-size: 14px; }
.import-copy span { color: #64748b; font-size: 12px; }
.file-picker { display: inline-flex; align-items: center; white-space: nowrap; }
.file-picker input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.file-picker.disabled { opacity: .55; cursor: not-allowed; }
.select-field { margin-top: 12px; }
.csv-preview { display: grid; gap: 12px; margin-top: 12px; padding: 13px; border: 1px solid #dbe3ef; border-radius: 8px; background: #fff; }
.selection-toolbar { display: flex; justify-content: space-between; gap: 10px; color: #64748b; font-size: 12px; }
.check-label, .csv-row { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.csv-rows { display: grid; gap: 3px; max-height: 220px; overflow: auto; border: 1px solid #e2e8f0; border-radius: 7px; }
.csv-row { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; }
.csv-row:last-child { border-bottom: 0; }
.csv-row:hover { background: #f8fafc; }
.csv-row-number { width: 58px; color: #64748b; font-size: 12px; }
.csv-id-value { color: #111827; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.import-btn { justify-self: end; }
.error-message { margin: 10px 0 0; padding: 9px 11px; border-radius: 7px; background: #fef2f2; color: #b91c1c; font-size: 13px; }
.privacy-note { margin: 10px 0 0; color: #64748b; font-size: 12px; }
button:disabled { opacity: .55; cursor: not-allowed; }
@media (max-width: 640px) {
  .manual-ids-header, .import-panel, .selection-toolbar { flex-direction: column; align-items: stretch; }
  .id-row { grid-template-columns: 26px minmax(0, 1fr); }
  .remove-id-btn, .saved-pill { grid-column: 2; justify-self: start; margin-top: 0; }
}
</style>
