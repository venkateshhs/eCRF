function cloneValue(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function defaultTableCellValue(column) {
  const constraints = column?.constraints || {};
  if (Object.prototype.hasOwnProperty.call(constraints, "defaultValue")) {
    return cloneValue(constraints.defaultValue);
  }

  switch (String(column?.type || "").toLowerCase()) {
    case "number":
      return null;
    case "checkbox":
      return false;
    case "select":
      return constraints.allowMultiple ? [] : "";
    default:
      return "";
  }
}

function remapColumnSourceReferences(value, columnKeyMap) {
  if (Array.isArray(value)) {
    return value.map((item) => remapColumnSourceReferences(item, columnKeyMap));
  }

  if (!value || typeof value !== "object") return value;

  return Object.fromEntries(
    Object.entries(value).map(([key, nestedValue]) => {
      if (key === "sourceFieldKey") {
        const mapped = columnKeyMap.get(String(nestedValue || ""));
        return [key, mapped || nestedValue];
      }
      return [key, remapColumnSourceReferences(nestedValue, columnKeyMap)];
    })
  );
}

export function copyCompleteTableStructure(
  sourceField,
  { fieldId, name, label, createColumnId }
) {
  if (String(sourceField?.type || "").toLowerCase() !== "table") {
    throw new TypeError("Complete table copying requires a table field.");
  }

  const sourceConfig = cloneValue(sourceField.tableConfig || {});
  const sourceColumns = Array.isArray(sourceConfig.columns)
    ? sourceConfig.columns
    : [];
  const columnKeyMap = new Map();

  const columnsWithNewIdentity = sourceColumns.map((column, index) => {
    const newId = String(createColumnId(column, index));
    [column?.id, column?.key]
      .filter((key) => key !== undefined && key !== null && String(key) !== "")
      .forEach((key) => columnKeyMap.set(String(key), newId));

    return {
      ...cloneValue(column),
      id: newId,
      key: newId,
    };
  });

  const columns = columnsWithNewIdentity.map((column) => ({
    ...column,
    constraints: remapColumnSourceReferences(
      cloneValue(column.constraints || {}),
      columnKeyMap
    ),
  }));

  const initialRows = Math.max(1, Number(sourceConfig.initialRows) || 1);
  const rows = Array.from({ length: initialRows }, () => {
    const row = {};
    columns.forEach((column) => {
      row[column.id] = defaultTableCellValue(column);
    });
    return row;
  });

  return {
    ...cloneValue(sourceField),
    _id: fieldId,
    name,
    label,
    value: { rows },
    constraints: cloneValue(sourceField.constraints || {}),
    tableConfig: {
      ...sourceConfig,
      columns,
    },
  };
}

