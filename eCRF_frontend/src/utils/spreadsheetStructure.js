import { inferFieldType, distinctValues, slugifyFieldName } from "@/utils/templateFieldImport";

export function cellText(value) {
  return String(value == null ? "" : value).trim();
}

export function normalizeImportText(value) {
  return cellText(value)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[._/\\|:()-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function stripLegacyColumnSuffix(value) {
  return cellText(value).replace(/\s*\(\d+\)\s*$/, "").trim();
}

export function splitExplicitHeader(value) {
  const header = cellText(value);
  for (const separator of ["::", "->", "|"]) {
    const index = header.indexOf(separator);
    if (index > 0) {
      return {
        sectionName: header.slice(0, index).trim(),
        fieldName: header.slice(index + separator.length).trim(),
      };
    }
  }
  return { sectionName: "", fieldName: header };
}

export function detectLegacySectionMarkers(rows = [], headerRowIndex = 0) {
  const header = rows[headerRowIndex] || [];
  const body = rows.slice(headerRowIndex + 1);
  return header.reduce((markers, value, columnIndex) => {
    if (!cellText(value)) return markers;
    const hasData = body.some(row => cellText(row?.[columnIndex]));
    if (!hasData) markers.push(columnIndex);
    return markers;
  }, []);
}

function looksLikeDataRow(row = []) {
  const values = row.filter(value => cellText(value));
  if (!values.length) return false;
  const dataLike = values.filter(value => {
    const text = cellText(value);
    return /^[-+]?\d+(?:[.,]\d+)?$/.test(text) || /^\d{4}-\d{1,2}-\d{1,2}/.test(text);
  });
  return dataLike.length >= Math.max(2, Math.ceil(values.length * 0.35));
}

export function detectSpreadsheetLayout(rows = [], headerRowIndex = 0) {
  const markers = detectLegacySectionMarkers(rows, headerRowIndex);
  if (markers.length >= 2) return "legacy-sections";

  const first = rows[headerRowIndex] || [];
  const second = rows[headerRowIndex + 1] || [];
  const third = rows[headerRowIndex + 2] || [];
  const firstValues = first.map(cellText).filter(Boolean);
  const secondValues = second.map(cellText).filter(Boolean);
  const repeatedSections = firstValues.length - new Set(firstValues.map(normalizeImportText)).size;
  if (secondValues.length && !looksLikeDataRow(second) && third.some(value => cellText(value)) && !looksLikeDataRow(third)) {
    return "three-row";
  }
  if (secondValues.length && !looksLikeDataRow(second) && repeatedSections > 0) return "two-row";
  return "single";
}

function uniqueStableKeys(columns) {
  const used = new Set();
  return columns.map((column, index) => {
    const supplied = slugifyFieldName(column.suppliedStableKey || "");
    const base = supplied !== "field"
      ? supplied
      : slugifyFieldName([column.sectionName, column.fieldName].filter(Boolean).join(" ") || `field_${index + 1}`);
    let stableKey = base;
    let suffix = 2;
    while (used.has(stableKey)) stableKey = `${base}_${suffix++}`;
    used.add(stableKey);
    return { ...column, stableKey };
  });
}

function enrichColumns(columns, dataRows) {
  return uniqueStableKeys(columns).map(column => {
    const values = dataRows.map(row => row?.[column.columnIndex]).filter(value => cellText(value));
    const distinct = distinctValues(values);
    return {
      ...column,
      id: `column_${column.columnIndex}`,
      displayName: [column.sectionName, column.fieldName].filter(Boolean).join(" / ") || `Column ${column.columnIndex + 1}`,
      values,
      samples: distinct.slice(0, 3),
      distinct,
      nonBlankCount: values.length,
      inferredType: inferFieldType(values, column.fieldName),
      selected: true,
    };
  });
}

function parseSingle(rows, headerRowIndex) {
  const header = rows[headerRowIndex] || [];
  const dataRows = rows.slice(headerRowIndex + 1);
  const columns = header.map((value, columnIndex) => {
    const rawHeader = cellText(value) || `Column ${columnIndex + 1}`;
    const split = splitExplicitHeader(rawHeader);
    return {
      columnIndex,
      sectionName: split.sectionName,
      fieldName: split.fieldName || rawHeader,
      rawHeader,
      sourceAlias: rawHeader,
      suppliedStableKey: "",
      isSectionMarker: false,
    };
  });
  return { columns: enrichColumns(columns, dataRows), dataRows, dataStartIndex: headerRowIndex + 1, markerIndexes: [] };
}

function parseLegacy(rows, headerRowIndex) {
  const header = rows[headerRowIndex] || [];
  const dataRows = rows.slice(headerRowIndex + 1);
  const markerIndexes = detectLegacySectionMarkers(rows, headerRowIndex);
  const markerSet = new Set(markerIndexes);
  let sectionName = "";
  const columns = [];
  header.forEach((value, columnIndex) => {
    const rawHeader = cellText(value) || `Column ${columnIndex + 1}`;
    if (markerSet.has(columnIndex)) {
      sectionName = rawHeader;
      return;
    }
    columns.push({
      columnIndex,
      sectionName,
      fieldName: stripLegacyColumnSuffix(rawHeader),
      rawHeader,
      sourceAlias: rawHeader,
      suppliedStableKey: "",
      isSectionMarker: false,
    });
  });
  return { columns: enrichColumns(columns, dataRows), dataRows, dataStartIndex: headerRowIndex + 1, markerIndexes };
}

function parseMultiRow(rows, headerRowIndex, depth) {
  const sectionRow = rows[headerRowIndex] || [];
  const labelRow = rows[headerRowIndex + 1] || [];
  const keyRow = depth === 3 ? rows[headerRowIndex + 2] || [] : [];
  const width = Math.max(sectionRow.length, labelRow.length, keyRow.length);
  const dataStartIndex = headerRowIndex + depth;
  const dataRows = rows.slice(dataStartIndex);
  let currentSection = "";
  const columns = [];
  for (let columnIndex = 0; columnIndex < width; columnIndex++) {
    const explicitSection = cellText(sectionRow[columnIndex]);
    if (explicitSection) currentSection = explicitSection;
    const fieldName = cellText(labelRow[columnIndex]) || `Column ${columnIndex + 1}`;
    const suppliedStableKey = cellText(keyRow[columnIndex]);
    columns.push({
      columnIndex,
      sectionName: currentSection,
      fieldName,
      rawHeader: fieldName,
      sourceAlias: fieldName,
      suppliedStableKey,
      isSectionMarker: false,
    });
  }
  return { columns: enrichColumns(columns, dataRows), dataRows, dataStartIndex, markerIndexes: [] };
}

export function parseSpreadsheetStructure(rows = [], options = {}) {
  const headerRowIndex = Number.isInteger(options.headerRowIndex) ? options.headerRowIndex : 0;
  const requested = options.layout || "auto";
  const layout = requested === "auto" ? detectSpreadsheetLayout(rows, headerRowIndex) : requested;
  let parsed;
  if (layout === "legacy-sections") parsed = parseLegacy(rows, headerRowIndex);
  else if (layout === "two-row") parsed = parseMultiRow(rows, headerRowIndex, 2);
  else if (layout === "three-row") parsed = parseMultiRow(rows, headerRowIndex, 3);
  else parsed = parseSingle(rows, headerRowIndex);
  return { ...parsed, layout, headerRowIndex };
}

export function compositeImportKey(sectionName, fieldName) {
  return `${normalizeImportText(sectionName)}::${normalizeImportText(stripLegacyColumnSuffix(fieldName))}`;
}
