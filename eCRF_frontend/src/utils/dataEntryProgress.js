function isBlankValue(value, fieldType = "") {
  if (fieldType === "checkbox") return value !== true;
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;

  if (fieldType === "file" && typeof value === "object") {
    if (value.source === "url") return !String(value.url || "").trim();

    const file = value.file && typeof value.file === "object"
      ? value.file
      : value;

    return !String(file?.name || "").trim() && !String(value.url || "").trim();
  }

  return false;
}

function buildColumnKey(column, index) {
  if (column?.id || column?.key) return column.id || column.key;

  const base = String(column?.label || `column_${index + 1}`)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  return base || `column_${index + 1}`;
}

function normalizedRuleValues(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item ?? "").trim()).filter(Boolean);
  }

  return [String(value ?? "").trim()].filter(Boolean);
}

function comparableNumber(value) {
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function comparableDate(value) {
  if (!value) return null;
  const parsed = Date.parse(String(value));
  if (Number.isFinite(parsed)) return parsed;

  const parts = String(value).trim().match(/^(\d{2})[.-](\d{2})[.-](\d{4})$/);
  if (!parts) return null;

  const dayFirst = new Date(+parts[3], +parts[2] - 1, +parts[1]).getTime();
  return Number.isFinite(dayFirst) ? dayFirst : null;
}

function comparableTime(value) {
  const match = String(value || "").trim().match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return null;
  return +match[1] * 3600 + +match[2] * 60 + +(match[3] || 0);
}

function evaluateVisibilityRule(rule, row, columns) {
  const sourceKey = String(rule?.sourceFieldKey || "");
  if (!sourceKey) return false;

  const sourceIndex = columns.findIndex((column, index) => {
    const candidates = [
      column?.id,
      column?.key,
      buildColumnKey(column, index),
      column?.label,
    ]
      .filter(Boolean)
      .map(String);

    return candidates.includes(sourceKey);
  });

  if (sourceIndex < 0) return false;

  const sourceColumn = columns[sourceIndex];
  const sourceValue = row?.[buildColumnKey(sourceColumn, sourceIndex)];
  const leftValues = normalizedRuleValues(sourceValue);
  const rightValues = normalizedRuleValues(
    rule?.value ?? rule?.compareValue ?? rule?.values
  );
  const operator = String(rule?.operator || rule?.op || "eq").toLowerCase();
  const sourceType = String(sourceColumn?.type || "").toLowerCase();

  if (operator === "empty" || operator === "is_empty") {
    return leftValues.length === 0;
  }
  if (operator === "not_empty" || operator === "is_not_empty") {
    return leftValues.length > 0;
  }

  if (sourceType === "checkbox") {
    const left = !!sourceValue;
    const compareValue = rule?.value;
    const right =
      compareValue === true ||
      compareValue === "true" ||
      compareValue === 1 ||
      compareValue === "1";

    if (operator === "eq") return left === right;
    if (operator === "neq") return left !== right;
  }

  if (sourceType === "number") {
    const left = comparableNumber(sourceValue);
    const right = comparableNumber(rule?.value);
    const rightTo = comparableNumber(rule?.valueTo);
    if (left === null) return false;

    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") {
      return right !== null && rightTo !== null && left >= right && left <= rightTo;
    }
  }

  if (sourceType === "date" || sourceType === "time") {
    const converter = sourceType === "date" ? comparableDate : comparableTime;
    const left = converter(sourceValue);
    const right = converter(rule?.value);
    const rightTo = converter(rule?.valueTo);
    if (left === null) return false;

    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") {
      return right !== null && rightTo !== null && left >= right && left <= rightTo;
    }
  }

  if (operator === "neq") {
    return !rightValues.some((value) => leftValues.includes(value));
  }
  if (operator === "contains") {
    return rightValues.some((value) => leftValues.includes(value));
  }
  if (operator === "not_contains") {
    return !rightValues.some((value) => leftValues.includes(value));
  }
  if (operator === "starts_with") {
    return rightValues.some((right) =>
      leftValues.some((left) => left.startsWith(right))
    );
  }
  if (operator === "ends_with") {
    return rightValues.some((right) =>
      leftValues.some((left) => left.endsWith(right))
    );
  }
  if (operator === "regex") {
    try {
      const expression = new RegExp(String(rule?.value ?? ""));
      return leftValues.some((left) => expression.test(left));
    } catch {
      return false;
    }
  }

  return rightValues.some((value) => leftValues.includes(value));
}

function isTableColumnVisible(column, row, columns) {
  const logic = column?.constraints?.visibilityLogic;
  const rules = Array.isArray(logic?.rules) ? logic.rules.filter(Boolean) : [];
  if (!rules.length) return true;

  const matches = rules.map((rule) =>
    evaluateVisibilityRule(rule, row, columns)
  );
  const matched =
    String(logic?.match || "all").toLowerCase() === "any"
      ? matches.some(Boolean)
      : matches.every(Boolean);

  return String(logic?.action || "show").toLowerCase() === "hide"
    ? !matched
    : matched;
}

function tableHasAnyEnteredValue(field, value) {
  const rows = Array.isArray(value?.rows) ? value.rows : [];
  const columns = Array.isArray(field?.tableConfig?.columns)
    ? field.tableConfig.columns
    : [];

  return rows.some((row) =>
    columns.some((column, index) => {
      if (!isTableColumnVisible(column, row, columns)) return false;

      return !isBlankValue(
        row?.[buildColumnKey(column, index)],
        String(column?.type || "").toLowerCase()
      );
    })
  );
}

function tableProgress(
  field,
  value,
  skipped,
  hasError,
  cellErrors = {},
  tableIsSystemManaged = false
) {
  const rows = Array.isArray(value?.rows) ? value.rows : [];
  const columns = Array.isArray(field?.tableConfig?.columns)
    ? field.tableConfig.columns
    : [];
  const hasSpecificCellErrors = Object.values(cellErrors || {}).some(Boolean);
  let total = 0;
  let completed = 0;

  rows.forEach((row, rowIndex) => {
    columns.forEach((column, columnIndex) => {
      if (!isTableColumnVisible(column, row, columns)) return;

      const cellValue = row?.[buildColumnKey(column, columnIndex)];
      const cellType = String(column?.type || "").toLowerCase();
      const hasValue = !isBlankValue(cellValue, cellType);
      const cellIsSystemManaged =
        tableIsSystemManaged ||
        !!column?.constraints?.readonly;

      // Preserve the form-level rule: an empty value that the user cannot
      // edit does not lower progress, while a populated one is counted.
      if (cellIsSystemManaged && !hasValue) return;

      total += 1;

      const hasCellError = !!cellErrors?.[`${rowIndex}-${columnIndex}`];
      const hasUnscopedTableError = hasError && !hasSpecificCellErrors;

      if (
        !skipped &&
        hasValue &&
        !hasCellError &&
        !hasUnscopedTableError
      ) {
        completed += 1;
      }
    });
  });

  return { total, completed };
}

export function calculateDataEntryProgress({
  sections = [],
  assignedSectionIndexes = [],
  values = [],
  skips = [],
  isFieldVisible = () => true,
  isCalculatedField = () => false,
  hasFieldError = () => false,
  getTableCellErrors = () => ({}),
  checkboxFalseIsComplete = false,
} = {}) {
  let total = 0;
  let completed = 0;
  let skipped = 0;

  assignedSectionIndexes.forEach((sectionIndex) => {
    const section = sections?.[sectionIndex];
    if (!section) return;

    (section.fields || []).forEach((field, fieldIndex) => {
      if (!isFieldVisible(sectionIndex, fieldIndex)) return;

      const contribution = calculateDataEntryFieldProgress({
        field,
        value: values?.[sectionIndex]?.[fieldIndex],
        skipped: !!skips?.[sectionIndex]?.[fieldIndex],
        visible: true,
        calculated: isCalculatedField(sectionIndex, fieldIndex),
        hasError: hasFieldError(sectionIndex, fieldIndex),
        tableCellErrors: getTableCellErrors(sectionIndex, fieldIndex),
        checkboxFalseIsComplete,
      });

      total += contribution.total;
      completed += contribution.completed;
      skipped += contribution.skipped;
    });
  });

  const percentage = total > 0
    ? Math.round((completed / total) * 100)
    : 0;

  return {
    total,
    completed,
    incomplete: Math.max(0, total - completed),
    skipped,
    percentage,
  };
}

export function calculateDataEntryFieldProgress({
  field,
  value,
  skipped = false,
  visible = true,
  calculated = false,
  hasError = false,
  tableCellErrors = {},
  checkboxFalseIsComplete = false,
} = {}) {
  if (!field || !visible) {
    return { total: 0, completed: 0, skipped: 0 };
  }

  const fieldType = String(field?.type || "").toLowerCase();
  const isSystemManaged = !!field?.constraints?.readonly || !!calculated;
  const skippedCount = skipped ? 1 : 0;

  if (fieldType === "table") {
    if (isSystemManaged && !tableHasAnyEnteredValue(field, value)) {
      return { total: 0, completed: 0, skipped: skippedCount };
    }

    const progress = tableProgress(
      field,
      value,
      skipped,
      !!hasError,
      tableCellErrors || {},
      isSystemManaged
    );

    return {
      total: progress.total,
      completed: progress.completed,
      skipped: skippedCount,
    };
  }

  const hasValue = fieldType === "checkbox" && checkboxFalseIsComplete && !isSystemManaged
    ? typeof value === "boolean"
    : !isBlankValue(value, fieldType);

  // Preserve the full-calculation rule exactly: empty read-only/calculated
  // fields do not reduce progress, while populated ones count as data points.
  if (isSystemManaged && !hasValue) {
    return { total: 0, completed: 0, skipped: skippedCount };
  }

  return {
    total: 1,
    completed: !skipped && hasValue && !hasError ? 1 : 0,
    skipped: skippedCount,
  };
}
