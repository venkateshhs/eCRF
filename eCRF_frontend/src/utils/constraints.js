/* eslint-disable */

/**
 * Coerce a "defaultValue" into the correct shape for a field type.
 * This keeps the preview value and stored constraints consistent.
 */
export function coerceDefaultForType(fieldType = "text", value) {
  const t = String(fieldType || "text").toLowerCase();

  // Keep undefined as-is so callers can decide whether to write it
  if (value === undefined) return undefined;

  switch (t) {
    case "checkbox":
      return !!value;

    case "number": {
      if (value === "" || value === null) return "";
      const n = Number(value);
      return Number.isFinite(n) ? n : "";
    }

    case "radio":
      // radio can be single (string) OR multi (array of strings).
      if (Array.isArray(value)) return value.map(v => String(v));
      return typeof value === "string" ? value : "";

    case "select":
      // dropdown is single-select only (string)
      return typeof value === "string" ? value : "";

    case "date":
    case "time":
      // treat these as strings (e.g., "2025-08-18", "13:45")
      return typeof value === "string" ? value : "";

    case "textarea":
    case "text":
    default:
      return value == null ? "" : String(value);
  }
}

/**
 * Normalize constraints per field type:
 * - strips unsupported keys
 * - coerces types
 * - enforces invariants
 * - removes nonsensical entries (e.g., placeholder for checkbox)
 * - coerces defaultValue via coerceDefaultForType
 *
 * NOTE: For radio/select, OPTIONS ARE FIELD-LEVEL (not a constraint).
 *       We intentionally ignore `options` here; the dialog/parent will
 *       emit them and set `field.options` directly.
 */
export function normalizeConstraints(fieldType = "text", raw = {}) {
  const c = { ...(raw || {}) };

  // Strip accidental options from normalization; parent handles them
  if (Array.isArray(c.options)) {
    delete c.options;
  }

  // Coerce booleans first
  ["required", "readonly", "allowMultiple", "integerOnly"].forEach((k) => {
    if (k in c) c[k] = !!c[k];
  });

  // Coerce numeric-like fields
  ["min", "max", "step", "maxLength", "minLength", "maxLengthDigits"].forEach((k) => {
    if (k in c && c[k] !== "" && c[k] != null) {
      const n = Number(c[k]);
      c[k] = Number.isFinite(n) ? n : undefined;
    }
  });

  // Default value is coerced type-aware
  if ("defaultValue" in c) {
    c.defaultValue = coerceDefaultForType(fieldType, c.defaultValue);
  }

  // Date normalization
  if (fieldType === "date") {
    ["minDate", "maxDate"].forEach((k) => {
      if (c[k] == null) c[k] = "";
    });
    c.dateFormat = c.dateFormat || "dd.MM.yyyy";
  }

  // Time normalization
  if (fieldType === "time") {
    if ("step" in c && c.step !== "" && c.step != null) {
      const n = Number(c.step);
      c.step = Number.isFinite(n) ? n : undefined;
    }
    ["minTime", "maxTime"].forEach((k) => {
      if (!(k in c)) return;
      if (typeof c[k] !== "string") c[k] = "";
    });
  }

  // Text-like normalization
  if (["text", "textarea"].includes(fieldType)) {
    if ("transform" in c && !["none", "uppercase", "lowercase", "capitalize"].includes(c.transform)) {
      c.transform = "none";
    }
    if (c.pattern && typeof c.pattern !== "string") {
      delete c.pattern;
    }
  }

  // Checkbox: no placeholder
  if (fieldType === "checkbox") {
    delete c.placeholder;
  }

  // Enforce ranges ordering
  if ("min" in c && "max" in c && c.min != null && c.max != null) {
    if (Number.isFinite(c.min) && Number.isFinite(c.max) && c.max < c.min) {
      const t = c.min;
      c.min = c.max;
      c.max = t;
    }
  }
  if (fieldType === "date" && c.minDate && c.maxDate && c.maxDate < c.minDate) {
    const t = c.minDate;
    c.minDate = c.maxDate;
    c.maxDate = t;
  }

  // Allowed keys per type (IMPORTANT: radio can be multi; select is single)
  const COMMON = ["required", "readonly", "helpText", "placeholder", "defaultValue"];
  const TEXTLIKE = ["minLength", "maxLength", "pattern", "transform"];
  const NUMBER = ["min", "max", "step", "integerOnly", "maxLengthDigits"];
  const DATE = ["minDate", "maxDate", "dateFormat", "defaultValue"];
  const TIME = ["minTime", "maxTime", "step"];

  let allowed = [...COMMON];

  switch (String(fieldType).toLowerCase()) {
    case "text":
    case "textarea":
      allowed = [...COMMON, ...TEXTLIKE];
      break;
    case "number":
      allowed = [...COMMON, ...NUMBER];
      break;
    case "date":
      allowed = [...COMMON, ...DATE];
      break;
    case "time":
      allowed = [...COMMON, ...TIME];
      break;
    case "select":
      allowed = [...COMMON]; // single-select only (no allowMultiple)
      delete c.allowMultiple;
      break;
    case "radio":
      allowed = [...COMMON, "allowMultiple"]; // radios can be multi
      break;
    case "checkbox":
      allowed = ["required", "readonly", "helpText", "defaultValue"];
      break;
    default:
      allowed = [...COMMON];
  }

  // Build cleaned object
  const cleaned = {};
  for (const k of allowed) {
    if (k in c && c[k] !== undefined) cleaned[k] = c[k];
  }

  // If number + integerOnly => ensure integer step, and allow digit limit
  if (String(fieldType).toLowerCase() === "number" && cleaned.integerOnly) {
    if ("step" in cleaned && cleaned.step != null && !Number.isInteger(cleaned.step)) {
      delete cleaned.step;
    }
    // Support legacy 'maxLength' as 'maxLengthDigits'
    if (!("maxLengthDigits" in cleaned) && "maxLength" in cleaned) {
      cleaned.maxLengthDigits = cleaned.maxLength;
      delete cleaned.maxLength;
    }
  } else {
    delete cleaned.maxLengthDigits;
  }

  return cleaned;
}
