<template>
  <div class="field-table-root">
    <!-- =========================
         CONFIGURE MODE
         ========================= -->
    <div v-if="mode === 'configure'" class="table-configurator">
      <div class="tc-header">
        <h3 class="tc-title">Configure Table Field</h3>
        <p class="tc-subtitle">
          Define the table structure and configure each column using the same field constraints dialog
          used elsewhere in the builder.
        </p>
      </div>

      <div class="tc-grid">
        <div class="tc-group">
          <label>Field label</label>
          <input
            v-model.trim="localConfig.label"
            type="text"
            placeholder="e.g. Lab Results Table"
          />
        </div>

        <div class="tc-group">
          <label>Initial rows</label>
          <input
            v-model.number="localConfig.initialRows"
            type="number"
            min="1"
            max="500"
          />
        </div>
      </div>

      <div class="tc-toggles">
        <label class="tc-checkbox">
          <input type="checkbox" v-model="localConfig.allowAddRows" />
          Allow adding rows during data entry
        </label>

        <label class="tc-checkbox">
          <input type="checkbox" v-model="localConfig.showRowNumbers" />
          Show row numbers
        </label>
      </div>

      <div class="tc-section">
        <div class="tc-section-header">
          <h4>Columns</h4>
          <button class="btn-option" type="button" @click="addColumn">
            + Add Column
          </button>
        </div>

        <div
          v-for="(col, idx) in localConfig.columns"
          :key="col.id"
          class="tc-column-card"
        >
          <div class="tc-column-top">
            <strong>Column {{ idx + 1 }}</strong>

            <div class="tc-column-actions">
              <button
                type="button"
                class="icon-btn"
                :disabled="idx === 0"
                title="Move up"
                @click="moveColumn(idx, -1)"
              >
                ↑
              </button>

              <button
                type="button"
                class="icon-btn"
                :disabled="idx === localConfig.columns.length - 1"
                title="Move down"
                @click="moveColumn(idx, 1)"
              >
                ↓
              </button>

              <button
                type="button"
                class="icon-btn"
                title="Column settings"
                @click="openColumnSettings(idx)"
              >
                <i :class="icons.cog"></i>
              </button>

              <button
                type="button"
                class="icon-btn danger"
                :disabled="localConfig.columns.length === 1"
                title="Delete column"
                @click="removeColumn(idx)"
              >
                Delete
              </button>
            </div>
          </div>

          <div class="tc-column-grid">
            <div class="tc-group">
              <label>Column label</label>
              <input
                v-model.trim="col.label"
                type="text"
                :placeholder="`Column ${idx + 1}`"
              />
            </div>

            <div class="tc-group">
              <label>Column type</label>
              <select v-model="col.type" @change="onTypeChanged(col)">
                <option v-for="t in columnTypeOptions" :key="t.value" :value="t.value">
                  {{ t.label }}
                </option>
              </select>
            </div>
          </div>

          <div class="tc-column-summary">
            <span class="tc-chip">{{ prettyType(col.type) }}</span>

            <span v-if="columnSummary(col)" class="tc-summary-text">
              {{ columnSummary(col) }}
            </span>
            <span v-else class="tc-summary-text muted">
              No extra constraints configured
            </span>
          </div>
        </div>
      </div>

      <div class="tc-section">
        <h4>Preview</h4>

        <div class="table-runtime-wrap preview-wrap">
          <table class="table-runtime">
            <thead>
              <tr>
                <th v-if="localConfig.showRowNumbers" class="rowno-col">#</th>
                <th
                  v-for="(col, colIdx) in localConfig.columns"
                  :key="col.id || colIdx"
                >
                  <div class="table-head-title">{{ col.label || 'Untitled column' }}</div>
                  <div class="table-head-type">{{ prettyType(col.type) }}</div>
                </th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="(row, rowIndex) in previewRows" :key="`preview-row-${rowIndex}`">
                <td v-if="localConfig.showRowNumbers" class="rowno-col">{{ rowIndex + 1 }}</td>

                <td
                  v-for="(col, colIdx) in localConfig.columns"
                  :key="`${rowIndex}-${col.id || colIdx}`"
                >
                  <div class="table-cell-box">
                    <div class="table-cell-control">
                      <input
                        v-if="col.type === 'text'"
                        type="text"
                        :value="row[getPreviewColKey(col, colIdx)]"
                        :placeholder="col.constraints?.placeholder || ''"
                        readonly
                      />

                      <textarea
                        v-else-if="col.type === 'textarea'"
                        :value="row[getPreviewColKey(col, colIdx)]"
                        :placeholder="col.constraints?.placeholder || ''"
                        rows="3"
                        readonly
                      ></textarea>

                      <input
                        v-else-if="col.type === 'number'"
                        type="number"
                        :value="row[getPreviewColKey(col, colIdx)]"
                        :min="col.constraints?.min"
                        :max="col.constraints?.max"
                        :step="col.constraints?.step"
                        readonly
                      />

                      <DateFormatPicker
                        v-else-if="col.type === 'date'"
                        :modelValue="row[getPreviewColKey(col, colIdx)]"
                        :format="col.constraints?.dateFormat || 'dd.MM.yyyy'"
                        :placeholder="col.constraints?.placeholder || ''"
                        :min-date="col.constraints?.minDate || null"
                        :max-date="col.constraints?.maxDate || null"
                      />

                      <FieldTime
                        v-else-if="col.type === 'time'"
                        :modelValue="row[getPreviewColKey(col, colIdx)]"
                        v-bind="col.constraints || {}"
                        :hourCycle="col.constraints?.hourCycle || '24'"
                        :placeholder="col.constraints?.placeholder || ''"
                      />

                      <select
                        v-else-if="col.type === 'select'"
                        :value="row[getPreviewColKey(col, colIdx)] || '__preview_empty__'"
                        disabled
                      >
                        <option value="__preview_empty__">Select…</option>
                        <option v-for="opt in (col.options || [])" :key="opt" :value="opt">{{ opt }}</option>
                      </select>

                      <FieldRadioGroup
                        v-else-if="col.type === 'radio'"
                        :name="`preview_radio_${rowIndex}_${col.id || colIdx}`"
                        :options="col.options || []"
                        :modelValue="row[getPreviewColKey(col, colIdx)]"
                      />

                      <FieldCheckbox
                        v-else-if="col.type === 'checkbox'"
                        :modelValue="row[getPreviewColKey(col, colIdx)]"
                      />

                      <input
                        v-else
                        type="text"
                        :value="row[getPreviewColKey(col, colIdx)]"
                        readonly
                      />
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="tc-preview-footer">
          <span>Initial rows: {{ localConfig.initialRows }}</span>
          <span>Columns: {{ localConfig.columns.length }}</span>
          <span>{{ localConfig.allowAddRows ? "Rows can be expanded later" : "Rows fixed initially" }}</span>
        </div>
      </div>

      <div class="modal-actions">
        <button class="btn-primary" type="button" @click="saveConfig">Save Table</button>
        <button class="btn-option" type="button" @click="$emit('cancel')">Cancel</button>
      </div>

      <div v-if="showColumnConstraintsDialog" class="modal-overlay nested-modal-overlay">
        <div class="modal nested-modal">
          <FieldConstraintsDialog
            :currentFieldType="currentColumnFieldType"
            :constraintsForm="columnConstraintsForm"
            :form="mockForm"
            :currentFieldKey="currentColumnKey"
            :currentFieldLabel="currentColumnLabel"
            @updateConstraints="confirmColumnConstraintsDialog"
            @closeConstraintsDialog="cancelColumnConstraintsDialog"
            @showGenericDialog="forwardGenericDialog"
          />
        </div>
      </div>
    </div>

    <!-- =========================
         RENDER MODE
         ========================= -->
    <div v-else class="table-runtime-shell">
      <div class="table-runtime-wrap">
        <table class="table-runtime">
          <thead>
            <tr>
              <th v-if="resolvedTableConfig.showRowNumbers" class="rowno-col">#</th>
              <th v-for="(col, colIdx) in resolvedColumns" :key="col.id || colIdx">
                <div class="table-head-title">{{ col.label }}</div>
                <div class="table-head-type">{{ prettyType(col.type) }}</div>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(row, rowIndex) in internalRows" :key="`row-${rowIndex}`">
              <td v-if="resolvedTableConfig.showRowNumbers" class="rowno-col">{{ rowIndex + 1 }}</td>

              <td v-for="(col, colIdx) in resolvedColumns" :key="`${rowIndex}-${col.id || colIdx}`">
                <div class="table-cell-box">
                  <div class="table-cell-control">
                    <input
                      v-if="col.type === 'text'"
                      type="text"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      :placeholder="col.constraints?.placeholder || ''"
                      :readonly="readonly || !!col.constraints?.readonly"
                      @blur="validateCellAt(rowIndex, colIdx)"
                    />

                    <textarea
                      v-else-if="col.type === 'textarea'"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      :placeholder="col.constraints?.placeholder || ''"
                      rows="3"
                      :readonly="readonly || !!col.constraints?.readonly"
                      @blur="validateCellAt(rowIndex, colIdx)"
                    ></textarea>

                    <input
                      v-else-if="col.type === 'number'"
                      type="number"
                      v-model.number="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      :min="col.constraints?.min"
                      :max="col.constraints?.max"
                      :step="col.constraints?.step"
                      :readonly="readonly || !!col.constraints?.readonly"
                      @blur="validateCellAt(rowIndex, colIdx)"
                    />

                    <DateFormatPicker
                      v-else-if="col.type === 'date'"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      :format="col.constraints?.dateFormat || 'dd.MM.yyyy'"
                      :placeholder="col.constraints?.placeholder || ''"
                      :min-date="col.constraints?.minDate || null"
                      :max-date="col.constraints?.maxDate || null"
                      @change="validateCellAt(rowIndex, colIdx)"
                      @blur="validateCellAt(rowIndex, colIdx)"
                    />

                    <FieldTime
                      v-else-if="col.type === 'time'"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      v-bind="col.constraints || {}"
                      :hourCycle="col.constraints?.hourCycle || '24'"
                      :placeholder="col.constraints?.placeholder || ''"
                      @change="validateCellAt(rowIndex, colIdx)"
                      @blur="validateCellAt(rowIndex, colIdx)"
                    />

                    <select
                      v-else-if="col.type === 'select'"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      :disabled="readonly || !!col.constraints?.readonly"
                      @change="validateCellAt(rowIndex, colIdx)"
                    >
                      <option value="" disabled>Select…</option>
                      <option v-for="opt in (col.options || [])" :key="opt" :value="opt">{{ opt }}</option>
                    </select>

                    <FieldRadioGroup
                      v-else-if="col.type === 'radio'"
                      :name="`table_radio_${rowIndex}_${col.id || colIdx}`"
                      :options="col.options || []"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      @update:modelValue="validateCellAt(rowIndex, colIdx)"
                    />

                    <FieldCheckbox
                      v-else-if="col.type === 'checkbox'"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      @update:modelValue="validateCellAt(rowIndex, colIdx)"
                    />

                    <input
                      v-else
                      type="text"
                      v-model="internalRows[rowIndex][getRuntimeColKey(col, colIdx)]"
                      :readonly="readonly"
                      @blur="validateCellAt(rowIndex, colIdx)"
                    />
                  </div>

                  <div v-if="getCellError(rowIndex, colIdx)" class="table-cell-error">
                    {{ getCellError(rowIndex, colIdx) }}
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="resolvedTableConfig.allowAddRows && !readonly" class="table-actions">
        <button type="button" class="btn-option" @click="addRuntimeRow">
          + Add Row
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import icons from "@/assets/styles/icons";
import FieldConstraintsDialog from "@/components/FieldConstraintsDialog.vue";
import DateFormatPicker from "@/components/DateFormatPicker.vue";
import FieldCheckbox from "@/components/fields/FieldCheckbox.vue";
import FieldRadioGroup from "@/components/fields/FieldRadioGroup.vue";
import FieldTime from "@/components/fields/FieldTime.vue";
import { normalizeConstraints } from "@/utils/constraints";
import { createAjv, validateFieldValue } from "@/utils/jsonschemaValidation";

export default {
  name: "FieldTable",
  components: {
    FieldConstraintsDialog,
    DateFormatPicker,
    FieldCheckbox,
    FieldRadioGroup,
    FieldTime
  },
  props: {
    mode: {
      type: String,
      default: "render"
    },
    value: {
      type: Object,
      default: () => ({})
    },
    modelValue: {
      type: Object,
      default: () => ({ rows: [] })
    },
    field: {
      type: Object,
      default: () => ({})
    },
    readonly: {
      type: Boolean,
      default: false
    }
  },
  emits: ["save", "cancel", "showGenericDialog", "update:modelValue", "validation-state"],
  data() {
    return {
      icons,
      ajv: createAjv(),
      cellErrors: {},
      columnTypeOptions: [
        { label: "Text", value: "text" },
        { label: "Textarea", value: "textarea" },
        { label: "Number", value: "number" },
        { label: "Date", value: "date" },
        { label: "Time", value: "time" },
        { label: "Select", value: "select" },
        { label: "Radio", value: "radio" },
        { label: "Checkbox", value: "checkbox" }
      ],
      localConfig: this.buildInitialConfig(this.value),
      previewData: [],
      showColumnConstraintsDialog: false,
      editingColumnIndex: null,
      currentColumnFieldType: "",
      columnConstraintsForm: {},
      internalRows: [],
      syncingFromParent: false,
      lastEmittedRowsJson: ""
    };
  },
  computed: {
    previewRows() {
      return this.previewData;
    },

    currentColumn() {
      if (!Number.isInteger(this.editingColumnIndex)) return null;
      return this.localConfig.columns[this.editingColumnIndex] || null;
    },

    currentColumnLabel() {
      return this.currentColumn?.label || "";
    },

    currentColumnKey() {
      return this.currentColumn?.id || "";
    },

    mockForm() {
      return {
        sections: [
          {
            title: "Table",
            fields: this.localConfig.columns.map(col => ({
              _id: col.id,
              label: col.label,
              name: col.id,
              type: col.type,
              options: Array.isArray(col.options) ? col.options : [],
              constraints: col.constraints || {}
            }))
          }
        ]
      };
    },

    resolvedTableConfig() {
      return {
        version: 1,
        mode: "2d",
        initialRows: Number(this.field?.tableConfig?.initialRows) || 1,
        allowAddRows: this.field?.tableConfig?.allowAddRows !== false,
        showRowNumbers: this.field?.tableConfig?.showRowNumbers !== false
      };
    },

    resolvedColumns() {
      return Array.isArray(this.field?.tableConfig?.columns)
        ? this.field.tableConfig.columns
        : [];
    }
  },
  watch: {
    value: {
      deep: true,
      handler(next) {
        if (this.mode !== "configure") return;
        this.localConfig = this.buildInitialConfig(next);
        this.ensurePreviewData();
      }
    },

    localConfig: {
      deep: true,
      handler() {
        if (this.mode !== "configure") return;
        this.ensurePreviewData();
      }
    },

    modelValue: {
      deep: true,
      immediate: true,
      handler(next) {
        if (this.mode !== "render") return;

        const normalized = this.normalizeRows(
          next?.rows,
          this.resolvedColumns,
          this.resolvedTableConfig.initialRows
        );

        const nextJson = JSON.stringify(normalized);
        const currentJson = JSON.stringify(this.internalRows);

        if (nextJson === currentJson) return;

        this.syncingFromParent = true;
        this.internalRows = normalized;
        this.lastEmittedRowsJson = nextJson;

        this.$nextTick(() => {
          this.syncingFromParent = false;
          this.validateAllCells();
        });
      }
    },

    field: {
      deep: true,
      immediate: true,
      handler() {
        if (this.mode !== "render") return;

        const normalized = this.normalizeRows(
          this.modelValue?.rows,
          this.resolvedColumns,
          this.resolvedTableConfig.initialRows
        );

        const nextJson = JSON.stringify(normalized);
        const currentJson = JSON.stringify(this.internalRows);

        if (nextJson === currentJson) return;

        this.syncingFromParent = true;
        this.internalRows = normalized;
        this.lastEmittedRowsJson = nextJson;

        this.$nextTick(() => {
          this.syncingFromParent = false;
          this.validateAllCells();
        });
      }
    },

    internalRows: {
      deep: true,
      handler(rows) {
        if (this.mode !== "render") return;
        if (this.syncingFromParent) return;

        const payload = { rows: JSON.parse(JSON.stringify(rows)) };
        const nextJson = JSON.stringify(payload.rows);

        if (nextJson === this.lastEmittedRowsJson) return;

        this.lastEmittedRowsJson = nextJson;
        this.$emit("update:modelValue", payload);

        this.$nextTick(() => {
          this.validateAllCells();
        });
      }
    }
  },
  mounted() {
    if (this.mode === "configure") {
      this.ensurePreviewData();
    }

    if (this.mode === "render") {
      const normalized = this.normalizeRows(
        this.modelValue?.rows,
        this.resolvedColumns,
        this.resolvedTableConfig.initialRows
      );
      this.internalRows = normalized;
      this.lastEmittedRowsJson = JSON.stringify(normalized);

      this.$nextTick(() => {
        this.validateAllCells();
      });
    }
  },
  methods: {
    buildInitialConfig(src) {
      const initialColumns =
        Array.isArray(src?.tableConfig?.columns) && src.tableConfig.columns.length
          ? src.tableConfig.columns.map((c, idx) => this.makeColumn(idx, c))
          : [this.makeColumn(0, { label: "Column 1", type: "text" })];

      return {
        label: src?.label || "Table",
        initialRows: Number(src?.tableConfig?.initialRows) > 0 ? Number(src.tableConfig.initialRows) : 1,
        allowAddRows: src?.tableConfig?.allowAddRows !== false,
        showRowNumbers: src?.tableConfig?.showRowNumbers !== false,
        columns: initialColumns
      };
    },

    makeColumn(idx, c = {}) {
      const type = this.normalizeAllowedType(c.type);

      let options = Array.isArray(c.options) ? [...c.options] : [];
      options = options.map(o => String(o || "").trim()).filter(Boolean);

      if ((type === "select" || type === "radio") && !options.length) {
        options = ["Option 1"];
      }

      return {
        id: c.id || `table_col_${Date.now()}_${idx}_${Math.random().toString(16).slice(2, 8)}`,
        key: c.key || this.buildColumnKey(c.label || `Column ${idx + 1}`, idx),
        label: c.label || `Column ${idx + 1}`,
        type,
        options,
        constraints: {
          ...(c.constraints || {})
        }
      };
    },

    normalizeAllowedType(type) {
      const allowed = ["text", "textarea", "number", "date", "time", "select", "radio", "checkbox"];
      return allowed.includes(type) ? type : "text";
    },

    prettyType(type) {
      const map = {
        text: "Text",
        textarea: "Textarea",
        number: "Number",
        date: "Date",
        time: "Time",
        select: "Select",
        radio: "Radio",
        checkbox: "Checkbox"
      };
      return map[type] || "Text";
    },

    buildColumnKey(label, idx) {
      const base = String(label || `column_${idx + 1}`)
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      return base || `column_${idx + 1}`;
    },

    getPreviewColKey(col, idx) {
      return col.key || this.buildColumnKey(col.label, idx);
    },

    getRuntimeColKey(col, idx) {
      return col.key || this.buildColumnKey(col.label, idx);
    },

    defaultValueForType(type) {
      switch (type) {
        case "number":
          return null;
        case "checkbox":
          return false;
        default:
          return "";
      }
    },

    ensurePreviewData() {
      const columns = this.localConfig.columns.map((col, idx) => ({
        ...col,
        key: this.buildColumnKey(col.label, idx)
      }));

      const row = {};
      columns.forEach((col) => {
        row[col.key] = this.defaultValueForType(col.type);
      });

      this.previewData = [row];
    },

    normalizeRows(rows, columns, initialRows = 1) {
      const safeColumns = Array.isArray(columns) ? columns : [];
      const incoming = Array.isArray(rows) ? JSON.parse(JSON.stringify(rows)) : [];
      const result = [];

      if (!incoming.length) {
        const count = Math.max(1, Number(initialRows) || 1);
        for (let i = 0; i < count; i += 1) {
          result.push(this.createEmptyRow(safeColumns));
        }
        return result;
      }

      incoming.forEach((row) => {
        const normalized = {};
        safeColumns.forEach((col, idx) => {
          const key = col.key || this.buildColumnKey(col.label, idx);
          normalized[key] =
            row?.[key] !== undefined
              ? row[key]
              : this.defaultValueForType(col.type);
        });
        result.push(normalized);
      });

      return result;
    },

    createEmptyRow(columns) {
      const row = {};
      (columns || []).forEach((col, idx) => {
        const key = col.key || this.buildColumnKey(col.label, idx);
        row[key] = this.defaultValueForType(col.type);
      });
      return row;
    },

    cellErrorKey(rowIndex, colIndex) {
      return `${rowIndex}-${colIndex}`;
    },

    getCellError(rowIndex, colIndex) {
      return this.cellErrors[this.cellErrorKey(rowIndex, colIndex)] || "";
    },

    setCellError(rowIndex, colIndex, message) {
      const key = this.cellErrorKey(rowIndex, colIndex);
      const next = { ...this.cellErrors };
      if (message) next[key] = message;
      else delete next[key];
      this.cellErrors = next;
    },

    clearCellError(rowIndex, colIndex) {
      this.setCellError(rowIndex, colIndex, "");
    },

    isCellEmpty(col, value) {
      if (col.type === "checkbox") return value !== true;
      if (Array.isArray(value)) return value.length === 0;
      return value == null || (typeof value === "string" && value.trim() === "");
    },

    validateDateBounds(value, constraints, label) {
      if (!value) return "";

      const parse = (s, fmt) => {
        const str = String(s || "");
        let m;

        switch (fmt) {
          case "dd.MM.yyyy":
            m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(str);
            return m ? new Date(+m[3], +m[2] - 1, +m[1]) : null;
          case "MM-dd-yyyy":
            m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(str);
            return m ? new Date(+m[3], +m[1] - 1, +m[2]) : null;
          case "dd-MM-yyyy":
            m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(str);
            return m ? new Date(+m[3], +m[2] - 1, +m[1]) : null;
          case "yyyy-MM-dd":
            m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str);
            return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
          case "MM/yyyy":
            m = /^(\d{2})\/(\d{4})$/.exec(str);
            return m ? new Date(+m[2], +m[1] - 1, 1) : null;
          case "MM-yyyy":
            m = /^(\d{2})-(\d{4})$/.exec(str);
            return m ? new Date(+m[2], +m[1] - 1, 1) : null;
          case "yyyy/MM":
            m = /^(\d{4})\/(\d{2})$/.exec(str);
            return m ? new Date(+m[1], +m[2] - 1, 1) : null;
          case "yyyy-MM":
            m = /^(\d{4})-(\d{2})$/.exec(str);
            return m ? new Date(+m[1], +m[2] - 1, 1) : null;
          case "yyyy":
            m = /^(\d{4})$/.exec(str);
            return m ? new Date(+m[1], 0, 1) : null;
          default:
            return null;
        }
      };

      const fmt = constraints?.dateFormat || "dd.MM.yyyy";
      const current = parse(value, fmt);
      if (!current) return "";

      if (constraints?.minDate) {
        const minD = parse(constraints.minDate, fmt);
        if (minD && current < minD) {
          return `${label} must be ≥ ${constraints.minDate}.`;
        }
      }

      if (constraints?.maxDate) {
        const maxD = parse(constraints.maxDate, fmt);
        if (maxD && current > maxD) {
          return `${label} must be ≤ ${constraints.maxDate}.`;
        }
      }

      return "";
    },

    validateTimeBounds(value, constraints, label) {
      if (!value) return "";

      const toSec = (s) => {
        const m = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(String(s || ""));
        if (!m) return null;
        return (+m[1] * 3600) + (+m[2] * 60) + (m[3] ? +m[3] : 0);
      };

      const cur = toSec(value);
      if (cur == null) return "";

      if (constraints?.minTime) {
        const minT = toSec(constraints.minTime);
        if (minT != null && cur < minT) {
          return `${label} must be ≥ ${constraints.minTime}.`;
        }
      }

      if (constraints?.maxTime) {
        const maxT = toSec(constraints.maxTime);
        if (maxT != null && cur > maxT) {
          return `${label} must be ≤ ${constraints.maxTime}.`;
        }
      }

      return "";
    },

    validateSingleCell(rowIndex, colIndex) {
      const col = this.resolvedColumns[colIndex];
      if (!col) return true;

      const key = this.getRuntimeColKey(col, colIndex);
      const row = this.internalRows[rowIndex] || {};
      const value = row[key];
      const label = col.label || `Column ${colIndex + 1}`;
      const constraints = col.constraints || {};

      this.clearCellError(rowIndex, colIndex);

      if (constraints.readonly) return true;

      if (constraints.required && this.isCellEmpty(col, value)) {
        this.setCellError(rowIndex, colIndex, `${label} is required.`);
        return false;
      }

      const pseudoField = {
        type: col.type,
        label,
        name: key,
        options: Array.isArray(col.options) ? col.options : [],
        constraints
      };

      if (col.type !== "checkbox") {
        const { valid, message } = validateFieldValue(this.ajv, pseudoField, value);
        if (!valid) {
          this.setCellError(rowIndex, colIndex, message || `${label} is invalid.`);
          return false;
        }
      }

      if (col.type === "number" && value !== "" && value != null) {
        const num = Number(value);
        if (!Number.isFinite(num)) {
          this.setCellError(rowIndex, colIndex, `${label} must be a number.`);
          return false;
        }

        if (constraints.integerOnly && !Number.isInteger(num)) {
          this.setCellError(rowIndex, colIndex, `${label} must be an integer.`);
          return false;
        }

        const digits = String(Math.abs(num)).replace(".", "").replace("-", "").length;

        if (Number.isFinite(Number(constraints.minDigits)) && digits < Number(constraints.minDigits)) {
          this.setCellError(rowIndex, colIndex, `${label} must have at least ${constraints.minDigits} digits.`);
          return false;
        }

        if (Number.isFinite(Number(constraints.maxDigits)) && digits > Number(constraints.maxDigits)) {
          this.setCellError(rowIndex, colIndex, `${label} must have at most ${constraints.maxDigits} digits.`);
          return false;
        }
      }

      if (col.type === "date") {
        const msg = this.validateDateBounds(value, constraints, label);
        if (msg) {
          this.setCellError(rowIndex, colIndex, msg);
          return false;
        }
      }

      if (col.type === "time") {
        const msg = this.validateTimeBounds(value, constraints, label);
        if (msg) {
          this.setCellError(rowIndex, colIndex, msg);
          return false;
        }
      }

      if ((col.type === "select" || col.type === "radio") && value) {
        const opts = Array.isArray(col.options) ? col.options.map(String) : [];
        if (!opts.includes(String(value))) {
          this.setCellError(rowIndex, colIndex, `${label} has an invalid option.`);
          return false;
        }
      }

      return true;
    },

    validateCellAt(rowIndex, colIndex) {
      const ok = this.validateSingleCell(rowIndex, colIndex);
      this.emitValidationState();
      return ok;
    },

    validateAllCells() {
      let ok = true;

      for (let r = 0; r < this.internalRows.length; r += 1) {
        for (let c = 0; c < this.resolvedColumns.length; c += 1) {
          const valid = this.validateSingleCell(r, c);
          if (!valid) ok = false;
        }
      }

      this.emitValidationState();
      return ok;
    },

    emitValidationState() {
      const messages = Object.values(this.cellErrors || {}).filter(Boolean);
      this.$emit("validation-state", {
        valid: messages.length === 0,
        message: messages[0] || "",
        cellErrors: { ...this.cellErrors }
      });
    },

    addColumn() {
      this.localConfig.columns.push(
        this.makeColumn(this.localConfig.columns.length, {
          label: `Column ${this.localConfig.columns.length + 1}`,
          type: "text"
        })
      );
    },

    removeColumn(idx) {
      if (this.localConfig.columns.length <= 1) return;
      this.localConfig.columns.splice(idx, 1);
    },

    moveColumn(idx, dir) {
      const next = idx + dir;
      if (next < 0 || next >= this.localConfig.columns.length) return;
      const moved = this.localConfig.columns.splice(idx, 1)[0];
      this.localConfig.columns.splice(next, 0, moved);
    },

    onTypeChanged(col) {
      col.type = this.normalizeAllowedType(col.type);

      if (col.type !== "select" && col.type !== "radio") {
        col.options = [];
      } else {
        const cleaned = Array.isArray(col.options)
          ? col.options.map(o => String(o || "").trim()).filter(Boolean)
          : [];

        col.options = cleaned.length ? cleaned : ["Option 1"];
      }

      col.constraints = this.rebuildColumnConstraintsForType(col);
    },

    rebuildColumnConstraintsForType(col) {
      const prev = JSON.parse(JSON.stringify(col.constraints || {}));
      const type = col.type;

      if (type === "checkbox") {
        return {
          helpText: prev.helpText || "",
          required: !!prev.required,
          readonly: !!prev.readonly,
          visibilityLogic: prev.visibilityLogic || {
            enabled: false,
            match: "all",
            action: "show",
            targetFieldKeys: [],
            rules: []
          }
        };
      }

      if (type === "select" || type === "radio") {
        return {
          helpText: prev.helpText || "",
          required: !!prev.required,
          readonly: !!prev.readonly,
          visibilityLogic: prev.visibilityLogic || {
            enabled: false,
            match: "all",
            action: "show",
            targetFieldKeys: [],
            rules: []
          }
        };
      }

      if (type === "date") {
        return {
          helpText: prev.helpText || "",
          required: !!prev.required,
          readonly: !!prev.readonly,
          dateFormat: prev.dateFormat || "dd.MM.yyyy",
          minDate: prev.minDate || null,
          maxDate: prev.maxDate || null,
          visibilityLogic: prev.visibilityLogic || {
            enabled: false,
            match: "all",
            action: "show",
            targetFieldKeys: [],
            rules: []
          }
        };
      }

      if (type === "time") {
        return {
          helpText: prev.helpText || "",
          required: !!prev.required,
          readonly: !!prev.readonly,
          hourCycle: prev.hourCycle || "24",
          visibilityLogic: prev.visibilityLogic || {
            enabled: false,
            match: "all",
            action: "show",
            targetFieldKeys: [],
            rules: []
          }
        };
      }

      if (type === "number") {
        return {
          helpText: prev.helpText || "",
          required: !!prev.required,
          readonly: !!prev.readonly,
          min: prev.min,
          max: prev.max,
          step: prev.step,
          integerOnly: !!prev.integerOnly,
          minDigits: prev.minDigits,
          maxDigits: prev.maxDigits,
          visibilityLogic: prev.visibilityLogic || {
            enabled: false,
            match: "all",
            action: "show",
            targetFieldKeys: [],
            rules: []
          }
        };
      }

      return {
        helpText: prev.helpText || "",
        required: !!prev.required,
        readonly: !!prev.readonly,
        placeholder: prev.placeholder || "",
        visibilityLogic: prev.visibilityLogic || {
          enabled: false,
          match: "all",
          action: "show",
          targetFieldKeys: [],
          rules: []
        }
      };
    },

    buildConstraintsFormForColumn(col) {
      const existing = JSON.parse(JSON.stringify(col.constraints || {}));

      return {
        ...existing,
        type: col.type,
        options: (col.type === "select" || col.type === "radio")
          ? (Array.isArray(col.options) ? [...col.options] : [])
          : existing.options,
        dateFormat: col.type === "date"
          ? (existing.dateFormat || "dd.MM.yyyy")
          : existing.dateFormat
      };
    },

    openColumnSettings(idx) {
      const col = this.localConfig.columns[idx];
      if (!col) return;

      this.editingColumnIndex = idx;
      this.currentColumnFieldType = col.type;
      this.columnConstraintsForm = this.buildConstraintsFormForColumn(col);
      this.showColumnConstraintsDialog = true;
    },

    confirmColumnConstraintsDialog(c) {
      const col = this.currentColumn;
      if (!col) {
        this.showColumnConstraintsDialog = false;
        return;
      }

      const prevConstraints = JSON.parse(JSON.stringify(col.constraints || {}));
      const type = col.type;
      const norm = normalizeConstraints(type, c);

      if ((type === "select" || type === "radio") && Array.isArray(c.options)) {
        const cleanedOptions = c.options.map(o => String(o || "").trim()).filter(Boolean);
        col.options = cleanedOptions.length ? cleanedOptions : ["Option 1"];
      }

      if (type === "date" && (c.dateFormat || norm.dateFormat)) {
        norm.dateFormat = c.dateFormat || norm.dateFormat;
      }

      col.constraints = {
        ...prevConstraints,
        ...norm,
        visibilityLogic: c.visibilityLogic || prevConstraints.visibilityLogic || {
          enabled: false,
          match: "all",
          action: "show",
          targetFieldKeys: [],
          rules: []
        }
      };

      this.showColumnConstraintsDialog = false;
      this.editingColumnIndex = null;
    },

    cancelColumnConstraintsDialog() {
      this.showColumnConstraintsDialog = false;
      this.editingColumnIndex = null;
    },

    forwardGenericDialog(msg) {
      this.$emit("showGenericDialog", msg);
    },

    columnSummary(col) {
      const c = col.constraints || {};
      const parts = [];

      if (c.required) parts.push("Required");
      if (c.readonly) parts.push("Read only");

      if ((col.type === "text" || col.type === "textarea") && c.placeholder) {
        parts.push("Placeholder set");
      }

      if (col.type === "number") {
        if (c.min !== undefined && c.min !== null) parts.push(`Min ${c.min}`);
        if (c.max !== undefined && c.max !== null) parts.push(`Max ${c.max}`);
        if (c.step !== undefined && c.step !== null) parts.push(`Step ${c.step}`);
        if (c.integerOnly) parts.push("Integer only");
      }

      if (col.type === "date" && c.dateFormat) {
        parts.push(`Format ${c.dateFormat}`);
      }

      if (col.type === "time" && c.hourCycle) {
        parts.push(`${c.hourCycle}-hour`);
      }

      if ((col.type === "select" || col.type === "radio") && Array.isArray(col.options) && col.options.length) {
        parts.push(`${col.options.length} option${col.options.length === 1 ? "" : "s"}`);
      }

      if (c.helpText) parts.push("Help text set");

      return parts.join(" • ");
    },

    validateConfig() {
      if (!this.localConfig.label) {
        return "Please enter a table field label.";
      }

      if (!Number.isFinite(this.localConfig.initialRows) || this.localConfig.initialRows < 1) {
        return "Initial rows must be at least 1.";
      }

      if (!Array.isArray(this.localConfig.columns) || !this.localConfig.columns.length) {
        return "Please add at least one column.";
      }

      const seenLabels = new Set();

      for (let i = 0; i < this.localConfig.columns.length; i += 1) {
        const col = this.localConfig.columns[i];

        if (!col.label || !String(col.label).trim()) {
          return `Column ${i + 1} needs a label.`;
        }

        const key = String(col.label).trim().toLowerCase();
        if (seenLabels.has(key)) {
          return `Duplicate column label "${col.label}" found.`;
        }
        seenLabels.add(key);

        if (
          (col.type === "select" || col.type === "radio") &&
          (!Array.isArray(col.options) || !col.options.length)
        ) {
          return `Column "${col.label}" needs at least one option. Open its settings and add options.`;
        }
      }

      return "";
    },

    saveConfig() {
      const err = this.validateConfig();
      if (err) {
        this.$emit("showGenericDialog", err);
        return;
      }

      const columns = this.localConfig.columns.map((col, idx) => ({
        id: col.id,
        key: this.buildColumnKey(col.label, idx),
        label: col.label,
        type: col.type,
        options: Array.isArray(col.options) ? [...col.options] : [],
        constraints: JSON.parse(JSON.stringify(col.constraints || {}))
      }));

      const rows = [];
      const rowCount = Math.max(1, Number(this.localConfig.initialRows) || 1);

      for (let r = 0; r < rowCount; r += 1) {
        const row = {};
        columns.forEach((col) => {
          row[col.key] = this.defaultValueForType(col.type);
        });
        rows.push(row);
      }

      const payload = {
        _id: this.value?._id,
        label: this.localConfig.label,
        name: this.value?.name || `table_${Date.now()}`,
        type: "table",
        value: { rows },
        constraints: {
          helpText: this.value?.constraints?.helpText || "",
          required: !!this.value?.constraints?.required,
          readonly: !!this.value?.constraints?.readonly,
          visibilityLogic: this.value?.constraints?.visibilityLogic || {
            action: "show",
            match: "all",
            rules: []
          }
        },
        tableConfig: {
          version: 1,
          mode: "2d",
          initialRows: Number(this.localConfig.initialRows),
          allowAddRows: !!this.localConfig.allowAddRows,
          showRowNumbers: !!this.localConfig.showRowNumbers,
          columns
        }
      };

      this.$emit("save", { ok: true, payload });
    },

    addRuntimeRow() {
      this.internalRows.push(this.createEmptyRow(this.resolvedColumns));
      this.$nextTick(() => {
        this.validateAllCells();
      });
    }
  }
};
</script>

<style scoped lang="scss">
.field-table-root {
  width: 100%;
}

/* =========================
   CONFIGURE MODE
   ========================= */
.table-configurator {
  width: min(92vw, 980px);
  max-width: 980px;
  min-width: 0;
  margin: 0 auto;
}

.tc-header {
  margin-bottom: 18px;
}

.tc-title {
  text-align: center;
  margin: 0;
}

.tc-subtitle {
  margin: 8px auto 0;
  color: #6b7280;
  font-size: 13px;
  text-align: center;
  max-width: 760px;
  line-height: 1.45;
}

.tc-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.tc-column-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 12px;
}

.tc-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.tc-group label {
  font-weight: 600;
  font-size: 13px;
  color: #111827;
}

.tc-group input,
.tc-group select {
  width: 100%;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  box-sizing: border-box;
  font-size: 14px;
  line-height: 1.2;
  margin: 0;
}

.tc-group input:focus,
.tc-group select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.tc-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
}

.tc-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #111827;
}

.tc-checkbox input[type="checkbox"] {
  width: auto;
  margin: 0;
  padding: 0;
}

.tc-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.tc-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.tc-section-header h4 {
  margin: 0;
}

.tc-column-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 14px;
  background: #f9fafb;
}

.tc-column-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.tc-column-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.icon-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  min-height: 36px;
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-btn.danger {
  color: #b91c1c;
}

.tc-column-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
}

.tc-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef2ff;
  font-size: 12px;
  color: #374151;
}

.tc-summary-text {
  font-size: 12px;
  color: #374151;
  line-height: 1.4;
}

.tc-summary-text.muted {
  color: #6b7280;
}

.tc-preview-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 10px;
  font-size: 12px;
  color: #6b7280;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-option {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
}

/* =========================
   NESTED CONSTRAINTS MODAL
   ========================= */
.nested-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 4000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.nested-modal {
  width: min(92vw, 980px);
  max-width: 980px;
  max-height: 90vh;
  overflow-y: auto;
  margin: 0 auto;
  box-sizing: border-box;
  padding: 20px 22px;
  border-radius: 14px;
}

.nested-modal :deep(.modal),
.nested-modal :deep(.constraints-edit-modal),
.nested-modal :deep(.constraints-dialog),
.nested-modal :deep(.field-constraints-dialog) {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.nested-modal :deep(.row),
.nested-modal :deep(.row.two) {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.nested-modal :deep(input),
.nested-modal :deep(select),
.nested-modal :deep(textarea) {
  box-sizing: border-box;
  max-width: 100%;
}

/* =========================
   TABLE RUNTIME / PREVIEW
   ========================= */
.table-runtime-shell {
  width: 100%;
}

.table-runtime-wrap {
  overflow-x: auto;
  overflow-y: visible;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #fff;
}

.preview-wrap {
  margin-top: 10px;
}

.table-runtime {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
}

.table-runtime th,
.table-runtime td {
  border: 1px solid #e5e7eb;
  padding: 10px;
  vertical-align: top;
  text-align: left;
}

.table-head-title {
  font-weight: 600;
  color: #111827;
}

.table-head-type {
  margin-top: 2px;
  font-size: 11px;
  color: #6b7280;
  text-transform: capitalize;
}

.rowno-col {
  width: 56px;
  text-align: center;
}

.table-cell-box {
  min-width: 220px;
  overflow: visible;
}

.table-cell-control {
  min-width: 220px;
  display: flex;
  align-items: stretch;
  overflow: visible;
}

.table-cell-control :deep(input[type="text"]),
.table-cell-control :deep(input[type="number"]),
.table-cell-control :deep(textarea),
.table-cell-control :deep(select) {
  width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  margin: 0;
  background: #fff;
  box-sizing: border-box;
  min-height: 42px;
  color: #111827;
}

.table-cell-control :deep(textarea) {
  min-height: 88px;
  resize: vertical;
}

.table-cell-control :deep(select) {
  appearance: auto;
}

.table-cell-control :deep(.field-radio-group),
.table-cell-control :deep(.radio-group),
.table-cell-control :deep(.radio-options) {
  width: 100%;
}

.table-cell-control :deep(label) {
  white-space: normal;
}

.table-cell-control :deep(.date-format-picker),
.table-cell-control :deep(.field-time),
.table-cell-control :deep(.time-field),
.table-cell-control :deep(.date-picker-wrapper) {
  width: 100%;
  min-width: 200px;
  overflow: visible;
}

.table-cell-control :deep(input[type="date"]),
.table-cell-control :deep(input[type="time"]) {
  width: 100%;
  min-width: 200px;
}

.table-cell-error {
  margin-top: 6px;
  color: #dc2626;
  font-size: 12px;
  line-height: 1.35;
}

.table-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-start;
}

/* =========================
   RESPONSIVE
   ========================= */
@media (max-width: 900px) {
  .tc-grid,
  .tc-column-grid {
    grid-template-columns: 1fr;
  }

  .tc-column-top {
    align-items: flex-start;
    flex-direction: column;
  }

  .nested-modal {
    width: min(96vw, 980px);
    padding: 16px;
  }
}
</style>