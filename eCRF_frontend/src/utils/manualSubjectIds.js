import Papa from "papaparse";
import { read, utils } from "xlsx";

export function duplicateSubjectIds(ids, existingIds = []) {
  const seen = new Set(
    existingIds
      .map(id => String(id ?? "").trim().toLowerCase())
      .filter(Boolean)
  );
  const duplicates = new Map();

  for (const rawId of Array.isArray(ids) ? ids : []) {
    const id = String(rawId ?? "").trim();
    if (!id) continue;
    const normalized = id.toLowerCase();
    if (seen.has(normalized) && !duplicates.has(normalized)) {
      duplicates.set(normalized, id);
    }
    seen.add(normalized);
  }

  return [...duplicates.values()];
}

export function validateManualSubjectIds(ids, existingIds = []) {
  if (!Array.isArray(ids) || !ids.length) return "Enter at least one Subject ID, import a CSV or Excel file, or skip enrollment for now.";
  for (let index = 0; index < ids.length; index += 1) {
    const id = String(ids[index] ?? "").trim();
    if (!id) return `Subject ID ${index + 1} is empty.`;
    if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(id)) {
      return `Subject ID ${index + 1}: use 1–128 letters, numbers, hyphens or underscores, starting with a letter or number.`;
    }
  }
  const duplicates = duplicateSubjectIds(ids, existingIds);
  if (duplicates.length) {
    return `The following Subject IDs are duplicated or already exist: ${duplicates.map(id => `"${id}"`).join(", ")}. IDs must be unique, including letter case differences.`;
  }
  return "";
}

// Parse as strings: leading zeros and letter case are part of the ID.
export function parseSubjectIdCsv(text) {
  const parsed = Papa.parse(String(text).replace(/^\uFEFF/, ""), { skipEmptyLines: "greedy", dynamicTyping: false });
  // A single-column ID file has no delimiter; Papa's comma fallback is correct.
  if (parsed.errors.some(error => error.code !== "UndetectableDelimiter")) throw new Error("Could not read CSV. Check its delimiters and quotation marks.");
  const [headers, ...rows] = parsed.data;
  if (!headers?.length || !rows.length) throw new Error("CSV must contain a header row and at least one ID row.");
  if (rows.some(row => row.length !== headers.length)) throw new Error("CSV rows must have the same number of columns as the header.");
  return { headers: headers.map((header, index) => String(header).trim() || `Column ${index + 1}`), rows };
}

export function readSubjectIdWorkbook(buffer) {
  try {
    const workbook = read(buffer, { type: "array", cellText: true });
    if (!workbook.SheetNames.length) throw new Error("No worksheets");
    return workbook;
  } catch {
    throw new Error("Could not read Excel file. Use a valid, unencrypted .xls or .xlsx workbook.");
  }
}

export function parseSubjectIdWorksheet(workbook, sheetName) {
  const sheet = workbook.Sheets[sheetName];
  if (!sheet) throw new Error("Select a worksheet.");
  // Use displayed text so numeric cells formatted as 0000 retain leading zeros.
  // Text IDs are preserved verbatim; formulas are not executed.
  const [headers, ...rows] = utils.sheet_to_json(sheet, {
    header: 1, raw: false, defval: "", blankrows: false,
  });
  if (!headers?.length || !rows.length) throw new Error("Worksheet must contain a header row and at least one ID row.");
  return {
    headers: headers.map((header, index) => String(header).trim() || `Column ${index + 1}`),
    rows: rows.map(row => headers.map((_, index) => String(row[index] ?? ""))),
  };
}

export function reconcileManualSubjects(ids, current = [], persisted = [], groupNames = [], random = false) {
  const cleaned = ids.map(id => String(id ?? "").trim());
  const error = validateManualSubjectIds(cleaned);
  if (error) throw new Error(error);
  if (persisted.some((subject, index) => cleaned[index] !== String(subject.id || subject.subject_id || "").trim())) {
    throw new Error("Existing subject IDs and positions cannot be changed.");
  }
  const byId = new Map(current.map(subject => [String(subject.id || subject.subject_id), subject]));
  return cleaned.map((id, index) => {
    if (index < persisted.length) return { ...persisted[index], ...current[index], id };
    const previous = byId.get(id);
    return {
      ...previous, id,
      group: previous?.group || (random && groupNames.length ? groupNames[Math.floor(Math.random() * groupNames.length)] : ""),
    };
  });
}
