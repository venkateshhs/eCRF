const TYPE_ALIASES = {
  text: "text",
  string: "text",
  shorttext: "text",
  "short text": "text",
  textarea: "textarea",
  longtext: "textarea",
  "long text": "textarea",
  multiline: "textarea",
  number: "number",
  numeric: "number",
  integer: "number",
  int: "number",
  decimal: "number",
  float: "number",
  date: "date",
  datum: "date",
  time: "time",
  zeit: "time",
  select: "select",
  dropdown: "select",
  choice: "select",
  radio: "radio",
  "radio group": "radio",
  slider: "slider",
  likert: "slider",
  linear: "slider",
  linearscale: "slider",
  "linear scale": "slider",
  checkbox: "checkbox",
  boolean: "checkbox",
  bool: "checkbox",
  file: "file",
  upload: "file",
};

const LABEL_HEADERS = [
  "field", "field label", "label", "display", "question", "question text",
  "column", "column name", "variable", "variable label", "feld", "feldname",
  "bezeichnung", "frage",
];
const NAME_HEADERS = ["name", "field name", "variable name", "key", "code", "id"];
const TYPE_HEADERS = ["type", "field type", "data type", "datatype", "typ", "feldtyp"];

export function normalizeHeader(value) {
  return String(value ?? "").trim().toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
}

export function isBlank(value) {
  return value == null || String(value).trim() === "";
}

export function makeColumns(headerRow = []) {
  const occurrences = new Map();
  return headerRow.map((value, index) => {
    const label = String(value ?? "").trim() || `Column ${index + 1}`;
    const count = (occurrences.get(label) || 0) + 1;
    occurrences.set(label, count);
    return {
      index,
      id: `column_${index}`,
      label,
      displayLabel: count === 1 ? label : `${label} (${count})`,
    };
  });
}

export function findColumnIndex(columns, aliases) {
  const normalizedAliases = aliases.map(normalizeHeader);
  const exact = columns.find(column => normalizedAliases.includes(normalizeHeader(column.label)));
  if (exact) return exact.index;
  const partial = columns.find(column => normalizedAliases.some(alias => normalizeHeader(column.label).includes(alias)));
  return partial?.index ?? -1;
}

export function suggestDefinitionMappings(columns) {
  return {
    labelIndex: findColumnIndex(columns, LABEL_HEADERS),
    nameIndex: findColumnIndex(columns, NAME_HEADERS),
    typeIndex: findColumnIndex(columns, TYPE_HEADERS),
  };
}

export function detectOrientation(rows = [], headerRowIndex = 0) {
  const columns = makeColumns(rows[headerRowIndex] || []);
  const mappings = suggestDefinitionMappings(columns);
  const body = rows.slice(headerRowIndex + 1).filter(row => Array.isArray(row) && row.some(value => !isBlank(value)));
  const typeValues = mappings.typeIndex >= 0
    ? body.slice(0, 25).map(row => normalizeType(row[mappings.typeIndex], "")).filter(Boolean)
    : [];
  const definitionScore =
    (mappings.labelIndex >= 0 ? 2 : 0) +
    (mappings.typeIndex >= 0 ? 3 : 0) +
    (typeValues.length ? 2 : 0) +
    (columns.length <= 8 && body.length > columns.length ? 1 : 0);
  return definitionScore >= 4 ? "rows" : "columns";
}

export function normalizeType(value, fallback = "text") {
  const key = normalizeHeader(value);
  return TYPE_ALIASES[key] || fallback;
}

function looksBoolean(values) {
  if (!values.length) return false;
  const allowed = new Set(["true", "false", "yes", "no", "y", "n", "ja", "nein", "0", "1"]);
  return values.every(value => allowed.has(normalizeHeader(value)));
}

function looksNumeric(values) {
  if (!values.length) return false;
  return values.every(value => {
    if (typeof value === "number") return Number.isFinite(value);
    const text = String(value).trim().replace(",", ".");
    return text !== "" && /^[-+]?\d+(?:\.\d+)?$/.test(text);
  });
}

function looksTime(values) {
  return values.length > 0 && values.every(value => /^([01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$/.test(String(value).trim()));
}

function looksDate(values) {
  return values.length > 0 && values.every(value => {
    if (value instanceof Date && !Number.isNaN(value.getTime())) return true;
    const text = String(value).trim();
    return /^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T].*)?$/.test(text) ||
      /^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}(?:[ T].*)?$/.test(text);
  });
}

export function distinctValues(values = [], limit = 50) {
  const seen = new Set();
  const result = [];
  for (const value of values) {
    if (isBlank(value)) continue;
    const text = String(value).trim();
    if (seen.has(text)) continue;
    seen.add(text);
    result.push(text);
    if (result.length >= limit) break;
  }
  return result;
}

export function inferFieldType(values = [], label = "") {
  const nonBlank = values.filter(value => !isBlank(value));
  const hint = normalizeHeader(label);
  if (!nonBlank.length) return "text";
  if (/\b(time|uhrzeit|zeit)\b/.test(hint) && looksTime(nonBlank)) return "time";
  if (/\b(date|datum|birth|geburt|gestartet|beendet)\b/.test(hint) && looksDate(nonBlank)) return "date";
  if (looksBoolean(nonBlank)) return "checkbox";
  if (looksTime(nonBlank)) return "time";
  if (looksDate(nonBlank)) return "date";
  if (looksNumeric(nonBlank)) return "number";

  const unique = distinctValues(nonBlank, 13);
  if (unique.length >= 2 && unique.length <= 12 && unique.length < nonBlank.length) return "select";
  if (nonBlank.some(value => String(value).length > 180 || String(value).includes("\n"))) return "textarea";
  return "text";
}

export function analyzeColumnFields(rows = [], headerRowIndex = 0) {
  const columns = makeColumns(rows[headerRowIndex] || []);
  const body = rows.slice(headerRowIndex + 1).filter(row => Array.isArray(row) && row.some(value => !isBlank(value)));
  return columns.map(column => {
    const values = body.map(row => row[column.index]).filter(value => !isBlank(value));
    const inferredType = inferFieldType(values, column.label);
    return {
      ...column,
      selected: true,
      nonBlankCount: values.length,
      samples: distinctValues(values, 3),
      distinct: distinctValues(values),
      inferredType,
    };
  });
}

export function analyzeDefinitionRows(rows = [], headerRowIndex = 0, labelIndex = -1, typeIndex = -1, nameIndex = -1) {
  return rows.slice(headerRowIndex + 1).map((row, offset) => ({
    id: `row_${headerRowIndex + 1 + offset}`,
    rowIndex: headerRowIndex + 1 + offset,
    selected: Array.isArray(row) && row.some(value => !isBlank(value)),
    label: labelIndex >= 0 ? String(row?.[labelIndex] ?? "").trim() : "",
    name: nameIndex >= 0 ? String(row?.[nameIndex] ?? "").trim() : "",
    rawType: typeIndex >= 0 ? String(row?.[typeIndex] ?? "").trim() : "",
    values: row || [],
  })).filter(item => item.values.some(value => !isBlank(value)));
}

export function slugifyFieldName(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "field";
}

export function uniqueFieldNames(items = []) {
  const used = new Set();
  return items.map((item, index) => {
    const base = slugifyFieldName(item.name || item.label || `field_${index + 1}`);
    let candidate = base;
    let suffix = 2;
    while (used.has(candidate)) candidate = `${base}_${suffix++}`;
    used.add(candidate);
    return candidate;
  });
}

export const definitionHeaderAliases = {
  label: LABEL_HEADERS,
  name: NAME_HEADERS,
  type: TYPE_HEADERS,
};
