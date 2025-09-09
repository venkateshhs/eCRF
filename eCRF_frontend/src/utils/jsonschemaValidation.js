/* eslint-disable */
import Ajv from "ajv";

// ---------- helpers ----------
const rxTime = /^(\d{2}):(\d{2})(?::(\d{2}))?$/;

const DATE_FORMATS = [
  "dd.MM.yyyy",
  "MM-dd-yyyy",
  "dd-MM-yyyy",
  "yyyy-MM-dd",
  "MM/yyyy",
  "MM-yyyy",
  "yyyy/MM",
  "yyyy-MM",
  "yyyy",
];

const KB = 1024;
const MB = 1024 * KB;

function parseDateByFormat(str, fmt) {
  const s = String(str || "");
  let m;
  switch (fmt) {
    case "dd.MM.yyyy":
      m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s);
      if (!m) return null;
      return new Date(+m[3], +m[2] - 1, +m[1]);
    case "MM-dd-yyyy":
      m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s);
      if (!m) return null;
      return new Date(+m[3], +m[1] - 1, +m[2]);
    case "dd-MM-yyyy":
      m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s);
      if (!m) return null;
      return new Date(+m[3], +m[2] - 1, +m[1]);
    case "yyyy-MM-dd":
      m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
      if (!m) return null;
      return new Date(+m[1], +m[2] - 1, +m[3]);
    case "MM/yyyy":
      m = /^(\d{2})\/(\d{4})$/.exec(s);
      if (!m) return null;
      return new Date(+m[2], +m[1] - 1, 1);
    case "MM-yyyy":
      m = /^(\d{2})-(\d{4})$/.exec(s);
      if (!m) return null;
      return new Date(+m[2], +m[1] - 1, 1);
    case "yyyy/MM":
      m = /^(\d{4})\/(\d{2})$/.exec(s);
      if (!m) return null;
      return new Date(+m[1], +m[2] - 1, 1);
    case "yyyy-MM":
      m = /^(\d{4})-(\d{2})$/.exec(s);
      if (!m) return null;
      return new Date(+m[1], +m[2] - 1, 1);
    case "yyyy":
      m = /^(\d{4})$/.exec(s);
      if (!m) return null;
      return new Date(+m[1], 0, 1);
    default:
      return null;
  }
}

function timeToSeconds(str) {
  const m = rxTime.exec(String(str || ""));
  if (!m) return null;
  const h = +m[1], mi = +m[2], se = m[3] ? +m[3] : 0;
  return h * 3600 + mi * 60 + se;
}

function digitsCountOfNumber(val) {
  if (val === "" || val === null || val === undefined) return 0;
  const s = String(val);
  return s.replace(/[^0-9]/g, "").length;
}

// Match a local file's meta against accepts list
function fileMetaMatchesAccept(meta, accepts) {
  const name = String(meta?.name || meta?.filename || "").toLowerCase();
  const mime = String(meta?.type || meta?.contentType || "").toLowerCase();
  const checks = (accepts || []).map(a => String(a || "").trim().toLowerCase()).filter(Boolean);
  if (!checks.length) return true;
  return checks.some(a => {
    if (a.endsWith("/*")) {
      const base = a.slice(0, -2);
      return mime.startsWith(base + "/");
    }
    if (a.startsWith(".")) {
      return name.endsWith(a);
    }
    if (a.includes("/")) {
      return mime === a;
    }
    return name.endsWith("." + a.replace(/^\./, ""));
  });
}

// Match a URL pathname against accepts list (best-effort by extension)
function urlMatchesAccept(urlStr, accepts) {
  try {
    const u = new URL(String(urlStr));
    const path = (u.pathname || "").toLowerCase();
    const checks = (accepts || []).map(a => String(a || "").trim().toLowerCase()).filter(Boolean);
    if (!checks.length) return true;
    return checks.some(a => {
      if (a.endsWith("/*")) return true;
      if (a.startsWith(".")) return path.endsWith(a);
      if (a.includes("/")) return true;
      return path.endsWith("." + a.replace(/^\./, ""));
    });
  } catch {
    return false;
  }
}

// ---------- AJV factory (v6 signature for addKeyword) ----------
export function createAjv() {
  const ajv = new Ajv({
    allErrors: true,
  });

  // Built-in formats we need
  ajv.addFormat("time", rxTime);

  // Allow only http(s) for link-upload
  ajv.addFormat("http-url", /^(https?:\/\/).+/i);

  // Custom date formats: "date:<fmt>"
  DATE_FORMATS.forEach((fmt) => {
    const name = `date:${fmt}`;
    let rx;
    switch (fmt) {
      case "dd.MM.yyyy":
        rx = /^\d{2}\.\d{2}\.\d{4}$/; break;
      case "MM-dd-yyyy":
      case "dd-MM-yyyy":
        rx = /^\d{2}-\d{2}-\d{4}$/; break;
      case "yyyy-MM-dd":
        rx = /^\d{4}-\d{2}-\d{2}$/; break;
      case "MM/yyyy":
        rx = /^\d{2}\/\d{4}$/; break;
      case "MM-yyyy":
        rx = /^\d{2}-\d{4}$/; break;
      case "yyyy/MM":
        rx = /^\d{4}\/\d{2}$/; break;
      case "yyyy-MM":
        rx = /^\d{4}-\d{2}$/; break;
      case "yyyy":
        rx = /^\d{4}$/; break;
      default:
        rx = /.+/;
    }
    ajv.addFormat(name, rx);
  });

  // ----- Custom keywords -----

  // maxDigits
  const maxDigitsValidate = function (max, data) {
    const digits = digitsCountOfNumber(data);
    const ok = digits <= max;
    if (!ok) {
      maxDigitsValidate.errors = [
        { keyword: "maxDigits", params: { limit: max }, message: `should have ≤ ${max} digits` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("maxDigits", {
    type: "number",
    errors: true,
    metaSchema: { type: "number", minimum: 1 },
    validate: maxDigitsValidate,
  });

  // minDigits
  const minDigitsValidate = function (min, data) {
    const digits = digitsCountOfNumber(data);
    const ok = digits >= min;
    if (!ok) {
      minDigitsValidate.errors = [
        { keyword: "minDigits", params: { limit: min }, message: `should have ≥ ${min} digits` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("minDigits", {
    type: "number",
    errors: true,
    metaSchema: { type: "number", minimum: 0 },
    validate: minDigitsValidate,
  });

  // minTime
  const minTimeValidate = function (minTime, data) {
    if (!data) return true;
    const v = timeToSeconds(data);
    const m = timeToSeconds(minTime);
    const ok = v != null && m != null ? v >= m : true;
    if (!ok) {
      minTimeValidate.errors = [
        { keyword: "minTime", params: { limit: minTime }, message: `should be ≥ ${minTime}` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("minTime", {
    type: "string",
    errors: true,
    metaSchema: { type: "string", pattern: rxTime.source },
    validate: minTimeValidate,
  });

  // maxTime
  const maxTimeValidate = function (maxTime, data) {
    if (!data) return true;
    const v = timeToSeconds(data);
    const x = timeToSeconds(maxTime);
    const ok = v != null && x != null ? v <= x : true;
    if (!ok) {
      maxTimeValidate.errors = [
        { keyword: "maxTime", params: { limit: maxTime }, message: `should be ≤ ${maxTime}` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("maxTime", {
    type: "string",
    errors: true,
    metaSchema: { type: "string", pattern: rxTime.source },
    validate: maxTimeValidate,
  });

  // timeStep (step in seconds)
  const timeStepValidate = function (stepSeconds, data) {
    if (!data || !stepSeconds) return true;
    const v = timeToSeconds(data);
    const ok = v != null ? v % stepSeconds === 0 : true;
    if (!ok) {
      timeStepValidate.errors = [
        { keyword: "timeStep", params: { step: stepSeconds }, message: `should align to ${stepSeconds}s steps` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("timeStep", {
    type: "string",
    errors: true,
    metaSchema: { type: "number", minimum: 1 },
    validate: timeStepValidate,
  });

  // minDateByFormat / maxDateByFormat
  const minDateByFormatValidate = function (schemaObj, data) {
    const { minDate, format } = schemaObj || {};
    if (!data || !minDate || !format) return true;
    const d = parseDateByFormat(data, format);
    const m = parseDateByFormat(minDate, format);
    const ok = d && m ? d >= m : true;
    if (!ok) {
      minDateByFormatValidate.errors = [
        { keyword: "minDateByFormat", params: { limit: minDate }, message: `should be ≥ ${minDate}` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("minDateByFormat", {
    type: "string",
    errors: true,
    metaSchema: {
      type: "object",
      properties: { minDate: { type: "string" }, format: { type: "string" } },
      required: ["minDate", "format"],
      additionalProperties: false,
    },
    validate: minDateByFormatValidate,
  });

  const maxDateByFormatValidate = function (schemaObj, data) {
    const { maxDate, format } = schemaObj || {};
    if (!data || !maxDate || !format) return true;
    const d = parseDateByFormat(data, format);
    const x = parseDateByFormat(maxDate, format);
    const ok = d && x ? d <= x : true;
    if (!ok) {
      maxDateByFormatValidate.errors = [
        { keyword: "maxDateByFormat", params: { limit: maxDate }, message: `should be ≤ ${maxDate}` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("maxDateByFormat", {
    type: "string",
    errors: true,
    metaSchema: {
      type: "object",
      properties: { maxDate: { type: "string" }, format: { type: "string" } },
      required: ["maxDate", "format"],
      additionalProperties: false,
    },
    validate: maxDateByFormatValidate,
  });

  // stepAlign (numeric step with floating-point tolerance)
  const stepAlignValidate = function (schemaObj, data) {
    if (data == null || data === "") return true;
    const base = Number(schemaObj?.base);
    const step = Number(schemaObj?.step);
    if (!Number.isFinite(step) || step <= 0) return true;
    const r = (Number(data) - (Number.isFinite(base) ? base : 0)) / step;
    const diff = Math.abs(r - Math.round(r));
    const EPS = 1e-9;
    const ok = diff <= EPS;
    if (!ok) {
      stepAlignValidate.errors = [
        {
          keyword: "stepAlign",
          params: { base, step },
          message: `should align to step ${step}${Number.isFinite(base) ? ` starting at ${base}` : ""}`
        }
      ];
    }
    return ok;
  };
  ajv.addKeyword("stepAlign", {
    type: "number",
    errors: true,
    metaSchema: {
      type: "object",
      properties: {
        base: { type: ["number", "null"] },
        step: { type: "number", minimum: 0 }
      },
      required: ["step"],
      additionalProperties: false
    },
    validate: stepAlignValidate,
  });

  // fileMatchesAccept (local file meta)
  const fileMatchesAcceptValidate = function (accepts, data) {
    if (!data || typeof data !== "object") return true;
    if (!Array.isArray(accepts)) return true;
    const meta = data.file && typeof data.file === "object" ? data.file : data;
    const ok = fileMetaMatchesAccept(meta, accepts);
    if (!ok) {
      fileMatchesAcceptValidate.errors = [
        { keyword: "fileMatchesAccept", params: {}, message: "type not allowed" },
      ];
    }
    return ok;
  };
  ajv.addKeyword("fileMatchesAccept", {
    type: "object",
    errors: true,
    metaSchema: { type: "array", items: { type: "string" } },
    validate: fileMatchesAcceptValidate,
  });

  // urlMatchesAccept (best-effort by extension)
  const urlMatchesAcceptValidate = function (accepts, data) {
    if (!data || typeof data !== "string") return true;
    if (!Array.isArray(accepts)) return true;
    const ok = urlMatchesAccept(data, accepts);
    if (!ok) {
      urlMatchesAcceptValidate.errors = [
        { keyword: "urlMatchesAccept", params: {}, message: "URL not in allowed formats" },
      ];
    }
    return ok;
  };
  ajv.addKeyword("urlMatchesAccept", {
    type: "string",
    errors: true,
    metaSchema: { type: "array", items: { type: "string" } },
    validate: urlMatchesAcceptValidate,
  });

  // maxFileBytes (local meta.size limit)
  const maxFileBytesValidate = function (limit, data) {
    if (!data || typeof data !== "object") return true;
    const meta = data.file && typeof data.file === "object" ? data.file : data;
    const sz = (typeof meta?.size === "number") ? meta.size : Number(meta?.size);
    if (!Number.isFinite(sz)) return true;
    const ok = sz <= limit;
    if (!ok) {
      maxFileBytesValidate.errors = [
        { keyword: "maxFileBytes", params: { limit }, message: `exceeds max size (${Math.round(limit / MB)} MB)` },
      ];
    }
    return ok;
  };
  ajv.addKeyword("maxFileBytes", {
    type: "object",
    errors: true,
    metaSchema: { type: "number", minimum: 1 },
    validate: maxFileBytesValidate,
  });

  return ajv;
}

// ---------- schema builder ----------
function buildSchemaForField(fieldDef) {
  const type = String(fieldDef?.type || "text").toLowerCase();
  const c = fieldDef?.constraints || {};
  const title = fieldDef?.label || "Field";

  const opts = Array.isArray(fieldDef?.options) && fieldDef.options.length
    ? fieldDef.options.map(String)
    : [""];
  let schema = { title };

  if (type === "text" || type === "textarea") {
    schema = {
      type: "string",
      minLength: isFinite(c.minLength) ? c.minLength : undefined,
      maxLength: isFinite(c.maxLength) ? c.maxLength : undefined,
      pattern: c.pattern || undefined,
    };
  } else if (type === "number") {
    schema = {
      type: c.integerOnly ? "integer" : "number",
      minimum: Number.isFinite(c.min) ? c.min : undefined,
      maximum: Number.isFinite(c.max) ? c.max : undefined,
      maxDigits:
        Number.isFinite(c.maxDigits) ? c.maxDigits :
        (Number.isFinite(c.maxLengthDigits) ? c.maxLengthDigits : undefined),
      minDigits: Number.isFinite(c.minDigits) ? c.minDigits : undefined,
    };
  } else if (type === "checkbox") {
    schema = { type: "boolean" };
  } else if (type === "radio" || type === "select") {
    if (c.allowMultiple) {
      schema = {
        type: "array",
        items: { type: "string", enum: opts },
        uniqueItems: true,
      };
    } else {
      schema = {
        type: "string",
        enum: opts,
      };
    }
  } else if (type === "date") {
    const fmt = c.dateFormat || "dd.MM.yyyy";
    schema = {
      type: "string",
      format: `date:${fmt}`,
      minDateByFormat: c.minDate ? { minDate: c.minDate, format: fmt } : undefined,
      maxDateByFormat: c.maxDate ? { maxDate: c.maxDate, format: fmt } : undefined,
    };
  } else if (type === "time") {
    schema = {
      type: "string",
      format: "time",
      minTime: c.minTime || undefined,
      maxTime: c.maxTime || undefined,
      timeStep: Number.isFinite(c.step) ? c.step : undefined,
    };
  } else if (type === "slider") {
    const mode = String(c.mode || "slider").toLowerCase() === "linear" ? "linear" : "slider";
    if (mode === "slider") {
      const min = c.percent ? 1 : (Number.isFinite(c.min) ? c.min : 1);
      const max = c.percent ? 100 : (Number.isFinite(c.max) ? c.max : 5);
      const step = Number.isFinite(c.step) && c.step > 0 ? c.step : 1;
      schema = {
        type: "number",
        minimum: min,
        maximum: max,
        stepAlign: { base: min, step }
      };
    } else {
      const min = Number.isFinite(c.min) ? Math.round(c.min) : 1;
      const max = Number.isFinite(c.max) ? Math.round(c.max) : Math.max(min + 1, 5);
      schema = {
        type: "integer",
        minimum: min,
        maximum: max
      };
    }
  } else if (type === "file") {
    const accepts = Array.isArray(c.allowedFormats) ? c.allowedFormats : [];
    const maxBytes = (Number.isFinite(c.maxSizeMB) && c.maxSizeMB > 0 ? c.maxSizeMB : 100) * MB;

    const urlSchema = {
      type: "object",
      required: ["source", "url"],
      properties: {
        source: { const: "url" },
        url: { type: "string", format: "http-url", urlMatchesAccept: accepts },
        filename: { type: "string" },
        contentType: { type: "string" }
      },
      additionalProperties: true
    };

    // accept both number and numeric-string for size; allow nested file meta too
    const localBaseProps = {
      source: { const: "local" },
      name: { type: "string" },
      size: { anyOf: [{ type: "number", minimum: 0 }, { type: "string", pattern: "^[0-9]+$" }] },
      type: { type: "string" },
      lastModified: { anyOf: [{ type: "number" }, { type: "string", pattern: "^[0-9]+$" }] }
    };

    const localSchemaFlat = {
      type: "object",
      required: ["source", "name", "size"],
      properties: localBaseProps,
      additionalProperties: true,
      fileMatchesAccept: accepts,
      maxFileBytes: maxBytes
    };

    const localSchemaNested = {
      type: "object",
      required: ["source", "file"],
      properties: {
        source: { const: "local" },
        file: {
          type: "object",
          required: ["name", "size"],
          properties: localBaseProps,
          additionalProperties: true
        }
      },
      additionalProperties: true,
      fileMatchesAccept: accepts,
      maxFileBytes: maxBytes
    };

    const pref = String(c.storagePreference || "local").toLowerCase();
    if (pref === "url") {
      schema = urlSchema;
    } else if (pref === "local") {
      schema = { oneOf: [localSchemaFlat, localSchemaNested] };
    } else {
      schema = { oneOf: [urlSchema, localSchemaFlat, localSchemaNested] };
    }
  } else {
    schema = { type: "string" };
  }


  Object.keys(schema).forEach((k) => schema[k] === undefined && delete schema[k]);
  return schema;
}

// ---------- single-field validator ----------
export function validateFieldValue(ajv, fieldDef, value) {
  try {
    const schema = buildSchemaForField(fieldDef);

    const t = String(fieldDef?.type || "text").toLowerCase();
    if ((value === "" || value == null) && !fieldDef?.constraints?.required) {
      return { valid: true };
    }
    if (t === "number" && (value === "" || value == null)) {
      return { valid: !fieldDef?.constraints?.required };
    }
    if (t === "slider" && (value === "" || value == null)) {
      return { valid: !fieldDef?.constraints?.required };
    }
    if (t === "file" && (value === "" || value == null)) {
      return { valid: !fieldDef?.constraints?.required };
    }

    const validate = ajv.compile(schema);
    const ok = validate(value);
    if (ok) return { valid: true };

    const err = Array.isArray(validate.errors) ? validate.errors[0] : null;
    if (!err) return { valid: false, message: "Invalid value." };

    switch (err.keyword) {
      case "stepAlign":
      case "maxDigits":
      case "minDigits":
      case "minTime":
      case "maxTime":
      case "timeStep":
      case "minDateByFormat":
      case "maxDateByFormat":
      case "fileMatchesAccept":
      case "urlMatchesAccept":
      case "maxFileBytes":
        return { valid: false, message: err.message || "Invalid value." };
      case "format":
        if (t === "time") return { valid: false, message: "Use HH:mm or HH:mm:ss" };
        if (t === "date") return { valid: false, message: `Use format ${fieldDef?.constraints?.dateFormat || "dd.MM.yyyy"}` };
        if (t === "file") return { valid: false, message: "Use a valid http(s) URL." };
        return { valid: false, message: "Bad format." };
      case "enum":
        return { valid: false, message: "Choose a valid option." };
      case "type":
        return { valid: false, message: `Expected ${schema.type}.` };
      case "minimum":
        return { valid: false, message: `Must be ≥ ${schema.minimum}.` };
      case "maximum":
        return { valid: false, message: `Must be ≤ ${schema.maximum}.` };
      case "minLength":
        return { valid: false, message: `Needs ≥ ${schema.minLength} characters.` };
      case "maxLength":
        return { valid: false, message: `Allows ≤ ${schema.maxLength} characters.` };
      case "pattern":
        return { valid: false, message: "Does not match required pattern." };
      case "required":
        return { valid: false, message: "This field is required." };
      default:
        return { valid: false, message: err.message || "Invalid value." };
    }
  } catch (e) {
    return { valid: false, message: "Validation error." };
  }
}

export { DATE_FORMATS };
