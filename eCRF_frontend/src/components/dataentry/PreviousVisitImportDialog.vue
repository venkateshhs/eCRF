<template>
  <teleport to="body">
    <div v-if="visible" class="previous-visit-overlay" @click.self="$emit('close')">
      <div class="previous-visit-modal">
        <h3>Import from Previous Visits</h3>
        <p class="subtext">
          Field: <strong>{{ fieldLabel || "Field" }}</strong>
        </p>

        <div v-if="!options.length" class="empty-state">
          No value was entered for this field in previous visits.
        </div>

        <div v-else class="import-options-list">
          <template v-for="opt in options" :key="opt.key">
          <button
            v-if="!opt.isTable"
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

          <section v-else class="table-import-card">
            <div class="import-option-top">
              <div>
                <strong>{{ opt.visitLabel }}</strong>
                <div v-if="opt.versionLabel" class="import-option-meta">
                  {{ opt.versionLabel }}
                </div>
              </div>
              <span v-if="opt.createdAtLabel" class="meta">{{ opt.createdAtLabel }}</span>
            </div>

            <div v-if="!opt.tableRows.length" class="empty-state">
              No value was entered for this table.
            </div>

            <template v-else>
            <div class="table-selection-actions">
              <label>
                <input
                  type="checkbox"
                  :checked="allRowsSelected(opt)"
                  @change="toggleAllRows(opt, $event.target.checked)"
                />
                Select all rows
              </label>
              <span>{{ selectedRowIndexes(opt).length }} of {{ opt.tableRows.length }} selected</span>
            </div>

            <div class="previous-table-wrap">
              <table class="previous-table">
                <thead>
                  <tr>
                    <th class="select-column">Copy</th>
                    <th class="row-column">Row</th>
                    <th v-for="column in opt.tableColumns" :key="column.key">
                      {{ column.label }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in opt.tableRows" :key="row.rowIndex">
                    <td class="select-column">
                      <input
                        type="checkbox"
                        :aria-label="`Copy row ${row.rowIndex + 1} from ${opt.visitLabel}`"
                        :checked="isRowSelected(opt, row.rowIndex)"
                        @change="toggleRow(opt, row.rowIndex, $event.target.checked)"
                      />
                    </td>
                    <td class="row-column">{{ row.rowIndex + 1 }}</td>
                    <td v-for="cell in row.cells" :key="cell.key">
                      {{ formatCellValue(cell.value, cell.type) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="table-import-footer">
              <button
                type="button"
                class="copy-selected-btn"
                :disabled="!selectedRowIndexes(opt).length"
                @click="copySelectedRows(opt)"
              >
                Copy selected rows
              </button>
            </div>
            </template>
          </section>
          </template>
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
  data() {
    return {
      tableSelections: {},
    };
  },
  watch: {
    visible(next) {
      if (next) this.initializeTableSelections();
    },
    options: {
      deep: true,
      handler() {
        if (this.visible) this.initializeTableSelections();
      },
    },
  },
  methods: {
    initializeTableSelections() {
      const selections = {};
      this.options.forEach((option) => {
        if (!option.isTable) return;
        selections[option.key] = (option.tableRows || []).map(
          (row) => row.rowIndex
        );
      });
      this.tableSelections = selections;
    },
    selectedRowIndexes(option) {
      return this.tableSelections[option.key] || [];
    },
    isRowSelected(option, rowIndex) {
      return this.selectedRowIndexes(option).includes(rowIndex);
    },
    toggleRow(option, rowIndex, checked) {
      const selected = new Set(this.selectedRowIndexes(option));
      if (checked) selected.add(rowIndex);
      else selected.delete(rowIndex);
      this.tableSelections = {
        ...this.tableSelections,
        [option.key]: Array.from(selected).sort((a, b) => a - b),
      };
    },
    toggleAllRows(option, checked) {
      this.tableSelections = {
        ...this.tableSelections,
        [option.key]: checked
          ? (option.tableRows || []).map((row) => row.rowIndex)
          : [],
      };
    },
    allRowsSelected(option) {
      const rows = option.tableRows || [];
      return (
        rows.length > 0 && this.selectedRowIndexes(option).length === rows.length
      );
    },
    copySelectedRows(option) {
      const selectedRowIndexes = this.selectedRowIndexes(option);
      if (!selectedRowIndexes.length) return;
      this.$emit("select", { ...option, selectedRowIndexes });
    },
    formatCellValue(value, type) {
      if (value === undefined || value === null || value === "") return "—";
      if (type === "checkbox" || typeof value === "boolean") {
        return value ? "Checked" : "Unchecked";
      }
      if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
      if (value && typeof value === "object") return this.formatValue(value);
      return String(value);
    },
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
  width: min(980px, 96vw);
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

.table-import-card {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.table-selection-actions,
.table-import-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.table-selection-actions {
  margin-bottom: 10px;
  color: #4b5563;
  font-size: 13px;
}

.table-selection-actions label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
}

.previous-table-wrap {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
}

.previous-table {
  width: 100%;
  min-width: 640px;
  border-collapse: collapse;
  font-size: 13px;
}

.previous-table th,
.previous-table td {
  padding: 9px 10px;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}

.previous-table th:last-child,
.previous-table td:last-child {
  border-right: 0;
}

.previous-table tbody tr:last-child td {
  border-bottom: 0;
}

.previous-table th {
  background: #f9fafb;
  color: #374151;
}

.previous-table .select-column,
.previous-table .row-column {
  width: 58px;
  text-align: center;
}

.table-import-footer {
  justify-content: flex-end;
  margin-top: 10px;
}

.copy-selected-btn {
  border: 0;
  border-radius: 6px;
  padding: 8px 13px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}

.copy-selected-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
