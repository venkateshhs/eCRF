/* eslint-disable */

/**
 * Coerce a "defaultValue" into the correct shape for a field type.
 * This keeps the preview value and stored constraints consistent.
 */
export function coerceDefaultForType(fieldType = "text", value) {
  const t = String(fieldType || "text").toLowerCase();

  if (value === undefined) return undefined;

  switch (t) {
    case "slider":
      // No default for slider or linear scale (both are type "slider")
      return undefined;

    case "file":
      // No default for file/link fields
      return undefined;

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
      return typeof value === "string" ? value : ""

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

  ["required", "readonly", "allowMultiple","allowMultipleFiles", "integerOnly", "percent", "showTicks"].forEach((k) => {
    if (k in c) c[k] = !!c[k];
  });

  [
    "min", "max", "step",
    "maxLength", "minLength",
    "maxLengthDigits",
    "minDigits", "maxDigits"
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

  // Enforce numeric range order for generic numeric
  if ("min" in c && "max" in c && c.min != null && c.max != null) {
    if (Number.isFinite(c.min) && Number.isFinite(c.max) && c.max < c.min) {
      const t = c.min; c.min = c.max; c.max = t;
    }
  }
  if (fieldType === "date" && c.minDate && c.maxDate && c.maxDate < c.minDate) {
    const t = c.minDate; c.minDate = c.maxDate; c.maxDate = t;
  }

  if (String(fieldType).toLowerCase() === "slider") {
    const mode = (String(c.mode || "slider").toLowerCase() === "linear") ? "linear" : "slider";
    c.mode = mode;

    const snap = (v, base, step) => {
      if (!Number.isFinite(v)) return null;
      if (!Number.isFinite(step) || step <= 0) return v;
      const r = Math.round((v - base) / step);
      return Number((base + r * step).toFixed(6));
    };
    const normalizeMarks = (marks, min, max, step) => {
      let arr = [];
      if (Array.isArray(marks)) arr = marks;
      else if (marks && typeof marks === "object") {
        arr = Object.keys(marks).map(k => ({ value: Number(k), label: String(marks[k]) }));
      }
      arr = arr
        .map(m => ({ value: Number(m?.value), label: String(m?.label || "").trim() }))
        .filter(m => Number.isFinite(m.value) && !!m.label)
        .map(m => {
          let v = snap(m.value, min, step);
          if (!Number.isFinite(v)) v = m.value;
          if (v < min) v = min;
          if (v > max) v = max;
          return { value: v, label: m.label };
        });

      const byVal = new Map();
      arr.forEach(m => { if (!byVal.has(m.value)) byVal.set(m.value, m.label); });
      return [...byVal.entries()]
        .map(([value, label]) => ({ value, label }))
        .sort((a, b) => a.value - b.value);
    };

    if (mode === "slider") {
      if (c.percent) {
        c.min = 1;
        c.max = 100;
        c.step = Math.max(1, Number.isFinite(c.step) && c.step > 0 ? Math.round(c.step) : 1);
      } else {
        c.min = Number.isFinite(c.min) ? c.min : 1;
        c.max = Number.isFinite(c.max) ? c.max : 5;
        if (c.max <= c.min) c.max = c.min + 1;
        c.step = Number.isFinite(c.step) && c.step > 0 ? c.step : 1;
      }

      if ("marks" in c) {
        c.marks = normalizeMarks(c.marks, c.min, c.max, c.step);
      }

      delete c.placeholder;
      delete c.defaultValue;
    } else {
      c.min = Number.isFinite(c.min) ? Math.round(c.min) : 1;
      c.max = Number.isFinite(c.max) ? Math.round(c.max) : 5;
      if (c.max <= c.min) c.max = c.min + 1;

      delete c.percent;
      delete c.step;
      delete c.marks;
      delete c.placeholder;
      delete c.defaultValue;
    }

    const COMMON_SLIDER = ["required", "readonly", "helpText"];
    const allowed = mode === "slider"
      ? [...COMMON_SLIDER, "mode", "percent", "min", "max", "step", "marks", "showTicks"]
      : [...COMMON_SLIDER, "mode", "min", "max", "leftLabel", "rightLabel"];

    const cleanedSlider = {};
    for (const k of allowed) {
      if (k in c && c[k] !== undefined) cleanedSlider[k] = c[k];
    }
    return cleanedSlider;
  }

  if (String(fieldType).toLowerCase() === "file") {
    const sp = String(c.storagePreference || "local").toLowerCase();
    c.storagePreference = (sp === "url") ? "url" : "local";

    if ("maxSizeMB" in c && c.maxSizeMB !== "" && c.maxSizeMB != null) {
      const n = Number(c.maxSizeMB);
      c.maxSizeMB = Number.isFinite(n) && n > 0 ? n : 100;
    } else {
      c.maxSizeMB = 100;
    }

    let formats = Array.isArray(c.allowedFormats) ? c.allowedFormats : [];
    formats = formats
      .map(x => String(x || "").trim().toLowerCase())
      .filter(Boolean);
    c.allowedFormats = Array.from(new Set(formats));

    let mods = Array.isArray(c.modalities) ? c.modalities : [];
    mods = mods.map(x => String(x || "").trim()).filter(Boolean);
    c.modalities = Array.from(new Set(mods));

    const allowed = [
      "required", "readonly", "helpText", "placeholder",
      "storagePreference", "allowedFormats", "maxSizeMB", "modalities", "allowMultipleFiles"
    ];

    const cleanedFile = {};
    for (const k of allowed) {
      if (k in c && c[k] !== undefined) cleanedFile[k] = c[k];
    }
    return cleanedFile;
  }

  const COMMON = ["required", "readonly", "helpText", "placeholder", "defaultValue"];
  const TEXTLIKE = ["minLength", "maxLength", "pattern", "transform"];
  const NUMBER = ["min", "max", "step", "integerOnly", "minDigits", "maxDigits"];
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
      allowed = [...COMMON];
      delete c.allowMultiple;
      break;
    case "radio":
      allowed = [...COMMON, "allowMultiple"];
      break;
    case "checkbox":
      allowed = ["required", "readonly", "helpText", "defaultValue"];
      break;
    default:
      allowed = [...COMMON];
  }

  const cleaned = {};
  for (const k of allowed) {
    if (k in c && c[k] !== undefined) cleaned[k] = c[k];
  }

  if (String(fieldType).toLowerCase() === "number") {
    if (Number.isFinite(cleaned.minDigits) && cleaned.minDigits < 0) cleaned.minDigits = 0;
    if (Number.isFinite(cleaned.maxDigits) && cleaned.maxDigits < 0) cleaned.maxDigits = 0;
    if (Number.isFinite(cleaned.minDigits) && Number.isFinite(cleaned.maxDigits) && cleaned.maxDigits < cleaned.minDigits) {
      const t = cleaned.minDigits; cleaned.minDigits = cleaned.maxDigits; cleaned.maxDigits = t;
    }
    if (cleaned.integerOnly && "step" in cleaned && cleaned.step != null && !Number.isInteger(cleaned.step)) {
      delete cleaned.step;
    }
  }

  return cleaned;
}
