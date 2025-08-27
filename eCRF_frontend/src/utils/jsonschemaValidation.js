// src/utils/jsonschemaValidation.js
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

// ---------- AJV factory (v6 signature for addKeyword) ----------
export function createAjv() {
  const ajv = new Ajv({
    allErrors: true,
    // Ajv v6 ignores "strict" option; safe to leave out or keep.
  });

  // Built-in formats we need
  ajv.addFormat("time", rxTime);

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

  // ----- Custom keywords (v6: addKeyword(name, def)) -----

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

    const validate = ajv.compile(schema);
    const ok = validate(value);
    if (ok) return { valid: true };

    const err = Array.isArray(validate.errors) ? validate.errors[0] : null;
    if (!err) return { valid: false, message: "Invalid value." };

    switch (err.keyword) {
      case "maxDigits":
      case "minDigits":
      case "minTime":
      case "maxTime":
      case "timeStep":
      case "minDateByFormat":
      case "maxDateByFormat":
        return { valid: false, message: err.message || "Invalid value." };
      case "format":
        if (t === "time") return { valid: false, message: "Use HH:mm or HH:mm:ss" };
        if (t === "date") return { valid: false, message: `Use format ${fieldDef?.constraints?.dateFormat || "dd.MM.yyyy"}` };
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
      default:
        return { valid: false, message: err.message || "Invalid value." };
    }
  } catch (e) {
    return { valid: false, message: "Validation error." };
  }
}

export { DATE_FORMATS };
