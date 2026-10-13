const TRUE_BOOLEAN_VALUES = new Set([
  "true", "yes", "y", "1", "checked", "ja", "j", "wahr",
]);

const FALSE_BOOLEAN_VALUES = new Set([
  "false", "no", "n", "0", "unchecked", "nein", "falsch",
]);

export function splitDelimitedChoices(value) {
  const source = Array.isArray(value) ? value : [value];
  return source
    .flatMap((item) => String(item ?? "").split(/[,;|\n]+/))
    .map((item) => item.trim())
    .filter(Boolean);
}

export function analyzeDelimitedChoices(values = []) {
  const rows = values
    .filter((value) => value != null && String(value).trim() !== "")
    .map((value) => splitDelimitedChoices(value));
  const options = [];
  const seen = new Set();
  rows.flat().forEach((option) => {
    if (seen.has(option)) return;
    seen.add(option);
    options.push(option);
  });
  return {
    allowMultiple: rows.some((row) => row.length > 1),
    options,
  };
}

export function normalizeImportedBoolean(value) {
  if (typeof value === "boolean") return value;
  const normalized = String(value ?? "").trim().toLowerCase();
  if (TRUE_BOOLEAN_VALUES.has(normalized)) return true;
  if (FALSE_BOOLEAN_VALUES.has(normalized)) return false;
  // Keep unrecognised values intact so schema validation can reject them.
  // Treating them as false would silently change imported clinical data.
  return value;
}
