<template>
  <div class="conflict-value-display">
    <template v-if="fieldType === 'table-row'">
      <dl class="object-values">
        <template v-for="column in tableColumns" :key="column.key">
          <dt>{{ column.label }}</dt>
          <dd>{{ formatScalar(tableCellValue(value, column), column.type) }}</dd>
        </template>
      </dl>
    </template>

    <template v-else-if="fieldType === 'table'">
      <div v-if="!tableRows.length" class="empty-value">Empty</div>
      <div v-else class="mini-table-wrap">
        <table class="mini-table">
          <thead>
            <tr>
              <th class="row-number">#</th>
              <th v-for="column in tableColumns" :key="column.key">
                {{ column.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in tableRows" :key="rowIndex">
              <td class="row-number">{{ rowIndex + 1 }}</td>
              <td
                v-for="column in tableColumns"
                :key="column.key"
                :class="{ 'changed-cell': tableCellDiffers(rowIndex, column.key) }"
              >
                {{ formatScalar(tableCellValue(row, column), column.type) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template v-else-if="fieldType === 'file'">
      <div v-if="!fileItems.length" class="empty-value">Empty</div>
      <ul v-else class="file-list">
        <li v-for="(item, index) in fileItems" :key="fileKey(item, index)">
          <i class="fas fa-paperclip" aria-hidden="true"></i>
          <span>{{ fileLabel(item) }}</span>
        </li>
      </ul>
    </template>

    <template v-else-if="Array.isArray(value)">
      <span v-if="!value.length" class="empty-value">Empty</span>
      <span v-else class="value-chips">
        <span v-for="(item, index) in value" :key="index" class="value-chip">
          {{ formatScalar(item, fieldType) }}
        </span>
      </span>
    </template>

    <template v-else-if="isPlainObject(value)">
      <dl class="object-values">
        <template v-for="(item, key) in value" :key="key">
          <dt>{{ humanizeKey(key) }}</dt>
          <dd>{{ formatScalar(item) }}</dd>
        </template>
      </dl>
    </template>

    <span v-else :class="{ 'empty-value': isEmpty(value) }">
      {{ formatScalar(value, fieldType) }}
    </span>
  </div>
</template>

<script>
export default {
  name: "ConflictValueDisplay",
  props: {
    value: { default: null },
    otherValue: { default: null },
    field: { type: Object, default: () => ({}) },
  },
  computed: {
    fieldType() {
      return String(this.field?.type || "").toLowerCase();
    },
    tableRows() {
      return Array.isArray(this.value?.rows) ? this.value.rows : [];
    },
    tableColumns() {
      const conflictColumns = Array.isArray(this.field?.conflictColumns)
        ? this.field.conflictColumns
        : [];
      if (conflictColumns.length) {
        return conflictColumns.map((column) => ({
          ...column,
          label: column.displayLabel || column.label,
          dataKeys: [column.key],
        }));
      }

      const configured = Array.isArray(this.field?.tableConfig?.columns)
        ? this.field.tableConfig.columns
        : [];

      if (configured.length) {
        return configured.map((column, index) => ({
          key: this.tableColumnKey(column, index),
          dataKeys: Array.from(new Set([
            column?.id,
            column?.key,
            this.tableColumnKey(column, index),
            column?.label,
          ].filter(Boolean).map(String))),
          label: column?.label || `Column ${index + 1}`,
          type: String(column?.type || "text").toLowerCase(),
        }));
      }

      const keys = new Set();
      this.tableRows.forEach((row) => {
        if (!row || typeof row !== "object") return;
        Object.keys(row).forEach((key) => keys.add(key));
      });
      return Array.from(keys).map((key) => ({
        key,
        label: this.humanizeKey(key),
        type: "text",
      }));
    },
    fileItems() {
      if (Array.isArray(this.value)) return this.value.filter(Boolean);
      return this.value ? [this.value] : [];
    },
  },
  methods: {
    isPlainObject(value) {
      return !!value && typeof value === "object" && !Array.isArray(value);
    },
    isEmpty(value) {
      return value === undefined || value === null || value === "";
    },
    tableColumnKey(column, index) {
      if (column?.id || column?.key) return String(column.id || column.key);
      const base = String(column?.label || `column_${index + 1}`)
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      return base || `column_${index + 1}`;
    },
    tableCellDiffers(rowIndex, columnKey) {
      const otherRows = Array.isArray(this.otherValue?.rows)
        ? this.otherValue.rows
        : [];
      const column = this.tableColumns.find((item) => item.key === columnKey);
      const currentValue = this.tableCellValue(this.tableRows?.[rowIndex], column);
      const otherValue = this.tableCellValue(otherRows?.[rowIndex], column);
      return JSON.stringify(currentValue ?? null) !== JSON.stringify(otherValue ?? null);
    },
    tableCellValue(row, column) {
      if (!row || typeof row !== "object" || !column) return undefined;
      const candidates = Array.isArray(column.dataKeys)
        ? column.dataKeys
        : [column.key];
      for (const key of candidates) {
        if (Object.prototype.hasOwnProperty.call(row, key)) return row[key];
      }
      return undefined;
    },
    humanizeKey(key) {
      const text = String(key || "").replace(/[_-]+/g, " ").trim();
      return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Value";
    },
    formatScalar(value, type = "") {
      if (value === undefined || value === null || value === "") return "—";
      if (type === "checkbox" || typeof value === "boolean") {
        return value === true ? "Yes" : "No";
      }
      if (Array.isArray(value)) {
        return value.length ? value.map((item) => this.formatScalar(item)).join(", ") : "—";
      }
      if (value && typeof value === "object") {
        return value.name || value.file_name || value.label || value.value || "Structured value";
      }

      const constraints = this.field?.constraints || {};
      const suffix =
        type === "number" || type === "slider"
          ? constraints.unit || constraints.suffix || ""
          : "";
      return suffix ? `${String(value)} ${suffix}` : String(value);
    },
    fileLabel(item) {
      if (typeof item === "string") return item;
      return (
        item?.name ||
        item?.file_name ||
        item?.url ||
        item?.file_path ||
        "Attached file"
      );
    },
    fileKey(item, index) {
      return item?.dbId || item?.id || item?.url || item?.name || index;
    },
  },
};
</script>

<style scoped>
.conflict-value-display {
  min-width: 0;
}

.empty-value {
  color: #64748b;
  font-style: italic;
}

.mini-table-wrap {
  max-width: 100%;
  overflow-x: auto;
}

.mini-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
  background: #fff;
}

.mini-table th,
.mini-table td {
  min-width: 110px;
  padding: 7px 9px;
  border: 1px solid #dbe3ee;
  text-align: left;
  vertical-align: top;
  white-space: normal;
  overflow-wrap: anywhere;
}

.mini-table th {
  background: #f8fafc;
  color: #334155;
  font-weight: 700;
}

.mini-table .row-number {
  min-width: 36px;
  width: 36px;
  color: #64748b;
  text-align: center;
}

.mini-table td.changed-cell {
  background: #fff4d6;
  box-shadow: inset 3px 0 0 #e0a11b;
}

.file-list {
  display: grid;
  gap: 5px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.file-list li {
  display: flex;
  align-items: center;
  gap: 7px;
}

.value-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.value-chip {
  padding: 3px 7px;
  border-radius: 999px;
  background: #eaf1fb;
  color: #27476d;
  font-size: 0.82rem;
}

.object-values {
  display: grid;
  grid-template-columns: minmax(90px, auto) 1fr;
  gap: 5px 10px;
  margin: 0;
}

.object-values dt {
  color: #64748b;
  font-weight: 600;
}

.object-values dd {
  margin: 0;
  overflow-wrap: anywhere;
}
</style>
