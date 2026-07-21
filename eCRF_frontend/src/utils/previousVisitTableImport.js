function cloneValue(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function columnKey(column, index) {
  if (column?.id || column?.key) return String(column.id || column.key);
  const base = String(column?.label || `column_${index + 1}`)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return base || `column_${index + 1}`;
}

export function buildPreviousVisitTableColumns(field, value) {
  const configured = Array.isArray(field?.tableConfig?.columns)
    ? field.tableConfig.columns
    : [];
  const columns = configured.map((column, index) => ({
    key: columnKey(column, index),
    label: column?.label || `Column ${index + 1}`,
    type: String(column?.type || "text").toLowerCase(),
    columnIndex: index,
  }));
  const known = new Set(columns.map((column) => column.key));

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
      });
    });
  });

  const labelCounts = columns.reduce((counts, column) => {
    counts[column.label] = (counts[column.label] || 0) + 1;
    return counts;
  }, {});

  return columns.map((column) => ({
    ...column,
    label:
      labelCounts[column.label] > 1
        ? `${column.label} (Column ${column.columnIndex + 1})`
        : column.label,
  }));
}

function cellHasEnteredValue(value, type = "") {
  if (value === undefined || value === null) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) {
    return value.some((item) => cellHasEnteredValue(item));
  }
  if (String(type).toLowerCase() === "checkbox" && value === false) {
    return false;
  }
  if (value && typeof value === "object") {
    return Object.values(value).some((item) => cellHasEnteredValue(item));
  }
  return true;
}

export function previousVisitTableRowHasData(row, columns) {
  if (!row || typeof row !== "object") return false;
  return (columns || []).some((column) =>
    cellHasEnteredValue(row[column.key], column.type)
  );
}

export function hasPreviousVisitTableData(field, value) {
  const rows = Array.isArray(value?.rows) ? value.rows : [];
  if (!rows.length) return false;
  const columns = buildPreviousVisitTableColumns(field, value);
  return rows.some((row) => previousVisitTableRowHasData(row, columns));
}

export function buildPreviousVisitTableRows(value, columns) {
  const rows = Array.isArray(value?.rows) ? value.rows : [];
  return rows
    .map((row, rowIndex) => ({ row, rowIndex }))
    .filter(({ row }) => previousVisitTableRowHasData(row, columns))
    .map(({ row, rowIndex }) => ({
      rowIndex,
      cells: (columns || []).map((column) => ({
        key: column.key,
        type: column.type,
        value:
          row && Object.prototype.hasOwnProperty.call(row, column.key)
            ? cloneValue(row[column.key])
            : undefined,
      })),
    }));
}

export function selectPreviousVisitTableRows(value, selectedRowIndexes) {
  const sourceRows = Array.isArray(value?.rows) ? value.rows : [];
  const selected = new Set(
    (selectedRowIndexes || [])
      .map((index) => Number(index))
      .filter((index) => Number.isInteger(index) && index >= 0)
  );
  const result = cloneValue(value) || {};
  result.rows = sourceRows
    .filter((_, rowIndex) => selected.has(rowIndex))
    .map((row) => cloneValue(row));
  return result;
}
