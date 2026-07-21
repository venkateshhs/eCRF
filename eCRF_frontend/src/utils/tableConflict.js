import {
  cloneConflictValue,
  conflictValuesEqual,
} from "@/utils/dataEntryConflict";

const hasOwn = (value, key) =>
  value != null &&
  typeof value === "object" &&
  Object.prototype.hasOwnProperty.call(value, key);

function generatedColumnKey(column, index) {
  if (column?.id || column?.key) return String(column.id || column.key);
  const base = String(column?.label || `column_${index + 1}`)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return base || `column_${index + 1}`;
}

export function tableConflictColumns(field, ...values) {
  const configured = Array.isArray(field?.tableConfig?.columns)
    ? field.tableConfig.columns
    : [];
  const columns = configured.map((column, index) => ({
    key: generatedColumnKey(column, index),
    label: column?.label || `Column ${index + 1}`,
    type: String(column?.type || "text").toLowerCase(),
    columnIndex: index,
    definition: column,
  }));
  const known = new Set(columns.map((column) => column.key));

  values.forEach((value) => {
    const rows = Array.isArray(value?.rows) ? value.rows : [];
    rows.forEach((row) => {
      if (!row || typeof row !== "object") return;
      Object.keys(row).forEach((key) => {
        if (known.has(key)) return;
        known.add(key);
        columns.push({
          key,
          label: key,
          type: "text",
          columnIndex: columns.length,
          definition: { key, label: key, type: "text" },
        });
      });
    });
  });

  const labelCounts = columns.reduce((counts, column) => {
    const label = String(column.label || "");
    counts[label] = (counts[label] || 0) + 1;
    return counts;
  }, {});

  return columns.map((column) => ({
    ...column,
    displayLabel:
      labelCounts[String(column.label || "")] > 1
        ? `${column.label} (Column ${column.columnIndex + 1})`
        : column.label,
  }));
}

/**
 * Three-way merge a table by row index and column key.
 * Non-overlapping cell edits merge automatically. Only cells changed
 * differently by both users become conflict rows.
 */
export function mergeTableFieldConflict({
  parentKey,
  sectionKey,
  fieldKey,
  field,
  baseValue,
  localValue,
  latestValue,
}) {
  const baseRows = Array.isArray(baseValue?.rows) ? baseValue.rows : [];
  const localRows = Array.isArray(localValue?.rows) ? localValue.rows : [];
  const latestRows = Array.isArray(latestValue?.rows) ? latestValue.rows : [];
  const merged = cloneConflictValue(latestValue) || { rows: [] };
  if (!Array.isArray(merged.rows)) merged.rows = [];

  const columns = tableConflictColumns(field, baseValue, localValue, latestValue);
  const conflicts = [];
  const rowCount = Math.max(baseRows.length, localRows.length, latestRows.length);

  for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
    const baseRowPresent = rowIndex < baseRows.length;
    const localRowPresent = rowIndex < localRows.length;
    const latestRowPresent = rowIndex < latestRows.length;
    const baseRow = baseRows[rowIndex] || {};
    const localRow = localRows[rowIndex] || {};
    const latestRow = latestRows[rowIndex] || {};

    // Without stable row IDs, two users adding different rows at the same
    // position must be treated as competing complete rows. Resolving their
    // cells independently could create a clinical record that neither user
    // entered, so offer a row-level "keep both" decision instead.
    if (
      !baseRowPresent &&
      localRowPresent &&
      latestRowPresent &&
      !conflictValuesEqual(localRow, latestRow)
    ) {
      conflicts.push({
        key: `${parentKey}|table-row|${rowIndex}`,
        parentKey,
        sectionKey,
        fieldKey,
        originalValue: undefined,
        localValue: cloneConflictValue(localRow),
        latestValue: cloneConflictValue(latestRow),
        localPresent: true,
        valuePath: ["rows", rowIndex],
        tableRowIndex: rowIndex,
        tableColumns: columns,
        conflictKind: "concurrent-table-row-addition",
        allowKeepBoth: true,
      });
      continue;
    }

    if (!merged.rows[rowIndex]) merged.rows[rowIndex] = {};

    columns.forEach((column) => {
      const baseCell = hasOwn(baseRow, column.key) ? baseRow[column.key] : undefined;
      const localCell = hasOwn(localRow, column.key) ? localRow[column.key] : undefined;
      const latestCell = hasOwn(latestRow, column.key) ? latestRow[column.key] : undefined;
      const localChanged = !conflictValuesEqual(localCell, baseCell);
      const latestChanged = !conflictValuesEqual(latestCell, baseCell);

      if (
        localChanged &&
        latestChanged &&
        !conflictValuesEqual(localCell, latestCell)
      ) {
        conflicts.push({
          key: `${parentKey}|table|${rowIndex}|${encodeURIComponent(column.key)}`,
          parentKey,
          sectionKey,
          fieldKey,
          originalValue: cloneConflictValue(baseCell),
          localValue: cloneConflictValue(localCell),
          latestValue: cloneConflictValue(latestCell),
          localPresent: hasOwn(localRow, column.key),
          valuePath: ["rows", rowIndex, column.key],
          tableRowIndex: rowIndex,
          tableColumnKey: column.key,
          tableColumnLabel: column.displayLabel,
          tableColumnType: column.type,
          tableColumn: column.definition || {},
        });
        return;
      }

      if (!localChanged) return;
      if (hasOwn(localRow, column.key)) {
        merged.rows[rowIndex][column.key] = cloneConflictValue(localCell);
      } else {
        delete merged.rows[rowIndex][column.key];
      }
    });
  }

  return { mergedValue: merged, conflicts };
}
