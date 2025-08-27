/* eslint-disable */

/**
 * Coerce a "defaultValue" into the correct shape for a field type.
 * This keeps the preview value and stored constraints consistent.
 */
export function coerceDefaultForType(fieldType = "text", value) {
  const t = String(fieldType || "text").toLowerCase();

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
      if (Array.isArray(value)) return value.map(v => String(v));
      return typeof value === "string" ? value : "";

    case "select":
      return typeof value === "string" ? value : "";

    case "date":
    case "time":
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
 */
export function normalizeConstraints(fieldType = "text", raw = {}) {
  const c = { ...(raw || {}) };

  // Options belong to the field, not constraints.
  if (Array.isArray(c.options)) delete c.options;

  // Boolean coercions
  ["required", "readonly", "allowMultiple", "integerOnly"].forEach((k) => {
    if (k in c) c[k] = !!c[k];
  });

  // Numeric coercions
  [
    "min", "max", "step",
    "maxLength", "minLength",
    "maxLengthDigits", // legacy
    "minDigits", "maxDigits" // new
  ].forEach((k) => {
    if (k in c && c[k] !== "" && c[k] != null) {
      const n = Number(c[k]);
      c[k] = Number.isFinite(n) ? n : undefined;
    }
  });

  // Migrate legacy maxLengthDigits -> maxDigits (if present)
  if ("maxLengthDigits" in c && c.maxLengthDigits != null) {
    if (!("maxDigits" in c)) c.maxDigits = c.maxLengthDigits;
    delete c.maxLengthDigits;
  }

  // Default value: type-aware
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

  // Enforce numeric range order
  if ("min" in c && "max" in c && c.min != null && c.max != null) {
    if (Number.isFinite(c.min) && Number.isFinite(c.max) && c.max < c.min) {
      const t = c.min; c.min = c.max; c.max = t;
    }
  }
  if (fieldType === "date" && c.minDate && c.maxDate && c.maxDate < c.minDate) {
    const t = c.minDate; c.minDate = c.maxDate; c.maxDate = t;
  }

  // Allowed keys per type
  const COMMON = ["required", "readonly", "helpText", "placeholder", "defaultValue"];
  const TEXTLIKE = ["minLength", "maxLength", "pattern", "transform"];
  const NUMBER = ["min", "max", "step", "integerOnly", "minDigits", "maxDigits"]; // ← digits here
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
      allowed = [...COMMON]; // single-select only
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

  // Extra numeric invariants for digits
  if (String(fieldType).toLowerCase() === "number") {
    if (Number.isFinite(cleaned.minDigits) && cleaned.minDigits < 0) cleaned.minDigits = 0;
    if (Number.isFinite(cleaned.maxDigits) && cleaned.maxDigits < 0) cleaned.maxDigits = 0;
    if (Number.isFinite(cleaned.minDigits) && Number.isFinite(cleaned.maxDigits) && cleaned.maxDigits < cleaned.minDigits) {
      const t = cleaned.minDigits; cleaned.minDigits = cleaned.maxDigits; cleaned.maxDigits = t;
    }
    // If integerOnly + non-integer step, drop it
    if (cleaned.integerOnly && "step" in cleaned && cleaned.step != null && !Number.isInteger(cleaned.step)) {
      delete cleaned.step;
    }
  }

  return cleaned;
}
