/* eslint-disable */

const TEXT_LIKE = new Set(["text", "textarea"]);
const CHOICE = new Set(["select", "radio"]);
const TEMPORAL = new Set(["date", "time"]);

export const FIELD_TYPE_OPTIONS = [
  { value: "text", label: "Text" },
  { value: "textarea", label: "Textarea" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "time", label: "Time" },
  { value: "checkbox", label: "Checkbox" },
  { value: "select", label: "Select" },
  { value: "radio", label: "Radio" },
  { value: "slider", label: "Slider / Likert" },
  { value: "file", label: "File" },
  { value: "table", label: "Table" },
];

function toType(type) {
  return String(type || "text").toLowerCase();
}

function isFiniteNumber(v) {
  return Number.isFinite(Number(v));
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeString(v) {
  return v == null ? "" : String(v);
}

function normalizeOptions(options) {
  const arr = Array.isArray(options) ? options : [];
  return Array.from(
    new Set(arr.map((x) => String(x || "").trim()).filter(Boolean))
  );
}

function defaultConstraintsForType(type) {
  const t = toType(type);

  const base = {
    required: false,
    readonly: false,
    helpText: "",
    visibilityLogic: {
      action: "show",
      match: "all",
      rules: [],
    },
  };

  if (TEXT_LIKE.has(t)) {
    return {
      ...base,
      placeholder: "",
      minLength: undefined,
      maxLength: undefined,
      pattern: "",
      transform: "none",
      defaultValue: "",
    };
  }

  if (t === "number") {
    return {
      ...base,
      placeholder: "",
      min: undefined,
      max: undefined,
      step: undefined,
      integerOnly: false,
      minDigits: undefined,
      maxDigits: undefined,
      defaultValue: "",
    };
  }

  if (t === "date") {
    return {
      ...base,
      dateFormat: "dd.MM.yyyy",
      minDate: "",
      maxDate: "",
      defaultValue: "",
    };
  }

  if (t === "time") {
    return {
      ...base,
      placeholder: "",
      hourCycle: "24",
      minTime: "",
      maxTime: "",
      defaultValue: "",
    };
  }

  if (t === "checkbox") {
    return {
      ...base,
      defaultValue: false,
    };
  }

  if (t === "select") {
    return {
      ...base,
      placeholder: "",
      defaultValue: "",
    };
  }

  if (t === "radio") {
    return {
      ...base,
      allowMultiple: false,
      dominantOptions: [],
      defaultValue: "",
    };
  }

  if (t === "slider") {
    return {
      ...base,
      mode: "slider",
      min: 1,
      max: 5,
      step: 1,
      percent: false,
      marks: [],
      leftLabel: "",
      rightLabel: "",
    };
  }

  if (t === "file") {
    return {
      ...base,
      allowedFormats: [],
      maxSizeMB: undefined,
      storagePreference: "local",
      allowMultipleFiles: true,
      modalities: [],
    };
  }

  if (t === "table") {
    return {
      ...base,
    };
  }

  return base;
}

function defaultValueForType(type, nextConstraints = {}) {
  const t = toType(type);

  if (t === "checkbox") return false;
  if (t === "slider") return null;
  if (t === "file") return nextConstraints.allowMultipleFiles ? [] : null;
  if (t === "table") return [];
  if (t === "radio") return nextConstraints.allowMultiple ? [] : "";
  if (t === "select") return nextConstraints.allowMultiple ? [] : "";
  return "";
}

function pickSharedConstraints(source = {}) {
  return {
    required: !!source.required,
    readonly: !!source.readonly,
    helpText: source.helpText || "",
    visibilityLogic: source.visibilityLogic
      ? clone(source.visibilityLogic)
      : {
          action: "show",
          match: "all",
          rules: [],
        },
  };
}

function convertValueBetweenTypes({
  fromType,
  toType,
  value,
  options = [],
  nextConstraints = {},
  warnings = [],
  valueLabel = "Current value",
}) {
  const from = toTypeLower(fromType);
  const to = toTypeLower(toType);

  if (from === to) return value;

  const fallback = defaultValueForType(to, nextConstraints);

  if (value == null || value === "") {
    if (Array.isArray(value) && value.length === 0) return fallback;
    return fallback;
  }

  if (TEXT_LIKE.has(to)) {
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "boolean") return value ? "true" : "";
    if (typeof value === "object") {
      warnings.push(`${valueLabel} was reset because structured data cannot be represented as plain text.`);
      return fallback;
    }
    return String(value);
  }

  if (to === "number") {
    const n = Number(String(value).replace(/,/g, "."));
    if (Number.isFinite(n)) return n;
    warnings.push(`${valueLabel} was reset because it is not numeric.`);
    return fallback;
  }

  if (to === "checkbox") {
    if (typeof value === "boolean") return value;
    const s = String(value).trim().toLowerCase();
    if (["true", "1", "yes", "y", "checked"].includes(s)) return true;
    if (["false", "0", "no", "n", ""].includes(s)) return false;
    warnings.push(`${valueLabel} was reset because it cannot be safely converted to a checkbox.`);
    return fallback;
  }

  if (to === "date" || to === "time") {
    if (typeof value === "string") return value;
    warnings.push(`${valueLabel} was reset because it cannot be safely converted to ${to}.`);
    return fallback;
  }

  if (to === "select") {
    const normalizedOptions = normalizeOptions(options);
    if (Array.isArray(value)) {
      const first = value.find((v) => normalizedOptions.includes(String(v)));
      if (first != null) {
        warnings.push(`${valueLabel} kept only the first matching option because Select is single-choice.`);
        return String(first);
      }
      warnings.push(`${valueLabel} was reset because no matching option remained.`);
      return fallback;
    }
    const s = String(value);
    if (normalizedOptions.includes(s)) return s;
    warnings.push(`${valueLabel} was reset because it does not match the available options.`);
    return fallback;
  }

  if (to === "radio") {
    const normalizedOptions = normalizeOptions(options);

    if (nextConstraints.allowMultiple) {
      if (Array.isArray(value)) {
        return value.map(String).filter((v) => normalizedOptions.includes(v));
      }
      const s = String(value);
      return normalizedOptions.includes(s) ? [s] : [];
    }

    if (Array.isArray(value)) {
      const first = value.map(String).find((v) => normalizedOptions.includes(v));
      if (first != null) {
        warnings.push(`${valueLabel} kept only the first matching option because Radio is single-choice.`);
        return first;
      }
      warnings.push(`${valueLabel} was reset because no matching option remained.`);
      return fallback;
    }

    const s = String(value);
    if (normalizedOptions.includes(s)) return s;
    warnings.push(`${valueLabel} was reset because it does not match the available options.`);
    return fallback;
  }

  if (to === "slider") {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
    warnings.push(`${valueLabel} was reset because it is not numeric.`);
    return fallback;
  }

  if (to === "file") {
    warnings.push(`${valueLabel} was reset because file fields cannot preserve previous values from other types.`);
    return fallback;
  }

  if (to === "table") {
    warnings.push(`${valueLabel} was reset because table fields require structured row data.`);
    return fallback;
  }

  return fallback;
}

function toTypeLower(type) {
  return String(type || "text").toLowerCase();
}

function buildConvertedConstraints({
  fromType,
  toType,
  sourceConstraints = {},
  sourceOptions = [],
  warnings = [],
}) {
  const from = toTypeLower(fromType);
  const to = toTypeLower(toType);

  const shared = pickSharedConstraints(sourceConstraints);
  const defaults = defaultConstraintsForType(to);
  const next = { ...defaults, ...shared };

  if (TEXT_LIKE.has(to)) {
    next.placeholder = sourceConstraints.placeholder || "";
    if (TEXT_LIKE.has(from)) {
      next.minLength = sourceConstraints.minLength;
      next.maxLength = sourceConstraints.maxLength;
      next.pattern = sourceConstraints.pattern || "";
      next.transform = sourceConstraints.transform || "none";
    } else {
      if (from === "number") {
        if (
          sourceConstraints.min != null ||
          sourceConstraints.max != null ||
          sourceConstraints.step != null ||
          sourceConstraints.integerOnly ||
          sourceConstraints.minDigits != null ||
          sourceConstraints.maxDigits != null
        ) {
          warnings.push("Numeric constraints were removed.");
        }
      } else if (CHOICE.has(from)) {
        warnings.push("Choice behavior was removed.");
      } else if (TEMPORAL.has(from)) {
        warnings.push("Date/time formatting constraints were removed.");
      } else if (from === "slider") {
        warnings.push("Slider presentation settings were removed.");
      } else if (from === "file") {
        warnings.push("File upload settings were removed.");
      } else if (from === "table") {
        warnings.push("Table configuration was removed.");
      }
    }
    return next;
  }

  if (to === "number") {
    next.placeholder = sourceConstraints.placeholder || "";
    if (from === "number") {
      next.min = sourceConstraints.min;
      next.max = sourceConstraints.max;
      next.step = sourceConstraints.step;
      next.integerOnly = !!sourceConstraints.integerOnly;
      next.minDigits = sourceConstraints.minDigits;
      next.maxDigits = sourceConstraints.maxDigits;
    } else if (from === "slider") {
      next.min = sourceConstraints.min;
      next.max = sourceConstraints.max;
      next.step = sourceConstraints.step;
      warnings.push("Slider-specific settings were simplified to number constraints.");
    }
    return next;
  }

  if (to === "date") {
    next.dateFormat = sourceConstraints.dateFormat || "dd.MM.yyyy";
    if (from === "date") {
      next.minDate = sourceConstraints.minDate || "";
      next.maxDate = sourceConstraints.maxDate || "";
    } else if (from !== "text" && from !== "textarea") {
      warnings.push("Previous type-specific constraints were removed.");
    }
    return next;
  }

  if (to === "time") {
    next.placeholder = sourceConstraints.placeholder || "";
    next.hourCycle = sourceConstraints.hourCycle || "24";
    if (from === "time") {
      next.minTime = sourceConstraints.minTime || "";
      next.maxTime = sourceConstraints.maxTime || "";
    } else if (from !== "text" && from !== "textarea") {
      warnings.push("Previous type-specific constraints were removed.");
    }
    return next;
  }

  if (to === "checkbox") {
    if (from !== "checkbox") {
      if (
        CHOICE.has(from) ||
        from === "number" ||
        from === "slider" ||
        TEMPORAL.has(from) ||
        from === "file" ||
        from === "table"
      ) {
        warnings.push("Previous field behavior was converted to a simple checkbox.");
      }
    }
    return next;
  }

  if (to === "select") {
    next.placeholder = sourceConstraints.placeholder || "";
    delete next.allowMultiple;
    delete next.dominantOptions;

    if (CHOICE.has(from)) {
      return next;
    }

    if (TEXT_LIKE.has(from) && normalizeOptions(sourceOptions).length) {
      warnings.push("Existing options were reused.");
      return next;
    }

    warnings.push("A default option list was created for the Select field.");
    return next;
  }

  if (to === "radio") {
    next.allowMultiple = !!sourceConstraints.allowMultiple;
    next.dominantOptions = next.allowMultiple
      ? normalizeOptions(sourceConstraints.dominantOptions)
      : [];

    if (CHOICE.has(from)) {
      return next;
    }

    if (TEXT_LIKE.has(from) && normalizeOptions(sourceOptions).length) {
      warnings.push("Existing options were reused.");
      return next;
    }

    warnings.push("A default option list was created for the Radio field.");
    return next;
  }

  if (to === "slider") {
    if (from === "slider") {
      next.mode = sourceConstraints.mode === "linear" ? "linear" : "slider";
      next.min = isFiniteNumber(sourceConstraints.min) ? Number(sourceConstraints.min) : 1;
      next.max = isFiniteNumber(sourceConstraints.max) ? Number(sourceConstraints.max) : 5;
      next.step = isFiniteNumber(sourceConstraints.step) ? Number(sourceConstraints.step) : 1;
      next.percent = !!sourceConstraints.percent;
      next.marks = Array.isArray(sourceConstraints.marks) ? clone(sourceConstraints.marks) : [];
      next.leftLabel = sourceConstraints.leftLabel || "";
      next.rightLabel = sourceConstraints.rightLabel || "";
      return next;
    }

    if (from === "number") {
      next.mode = "slider";
      next.min = isFiniteNumber(sourceConstraints.min) ? Number(sourceConstraints.min) : 1;
      next.max = isFiniteNumber(sourceConstraints.max) ? Number(sourceConstraints.max) : 5;
      next.step = isFiniteNumber(sourceConstraints.step) ? Number(sourceConstraints.step) : 1;
      return next;
    }

    warnings.push("Slider defaults were initialized for the new field type.");
    return next;
  }

  if (to === "file") {
    warnings.push("File-specific settings were initialized. Previous value and non-file constraints were removed.");
    return next;
  }

  if (to === "table") {
    warnings.push("Table settings were initialized. Previous value and non-table constraints were removed.");
    return next;
  }

  return next;
}

function buildConvertedOptions({
  fromType,
  toType,
  sourceOptions = [],
  warnings = [],
}) {
  const from = toTypeLower(fromType);
  const to = toTypeLower(toType);

  if (!CHOICE.has(to)) return [];

  const normalized = normalizeOptions(sourceOptions);
  if (normalized.length) return normalized;

  if (CHOICE.has(from)) return ["Option 1"];
  warnings.push("Options were initialized with a default entry.");
  return ["Option 1"];
}

function buildConvertedRows({ fromType, toType, sourceRows }) {
  const to = toTypeLower(toType);
  if (to !== "textarea") return undefined;
  return Number.isFinite(Number(sourceRows)) ? Number(sourceRows) : 4;
}

function buildConvertedPlaceholder({ fromType, toType, sourcePlaceholder = "" }) {
  const to = toTypeLower(toType);

  if (to === "checkbox") return "";
  if (to === "file") return "";
  if (to === "table") return "";
  if (to === "slider") return "";
  if (to === "date") return "";
  return sourcePlaceholder || "";
}

function isLossyConversion(fromType, toType) {
  const from = toTypeLower(fromType);
  const to = toTypeLower(toType);

  if (from === to) return false;
  if (TEXT_LIKE.has(from) && TEXT_LIKE.has(to)) return false;
  if (from === "select" && to === "radio") return false;
  if (from === "radio" && to === "select") return false;
  if (from === "number" && to === "slider") return false;
  if (from === "slider" && to === "number") return false;
  if (TEMPORAL.has(from) && TEXT_LIKE.has(to)) return false;
  if (TEXT_LIKE.has(from) && TEMPORAL.has(to)) return false;

  return true;
}

export function getFieldTypeConversionReport({
  field,
  fromType,
  toType,
}) {
  const from = toTypeLower(fromType || field?.type);
  const to = toTypeLower(toType);

  const warnings = [];

  const nextConstraints = buildConvertedConstraints({
    fromType: from,
    toType: to,
    sourceConstraints: field?.constraints || {},
    sourceOptions: field?.options || [],
    warnings,
  });

  const nextOptions = buildConvertedOptions({
    fromType: from,
    toType: to,
    sourceOptions: field?.options || [],
    warnings,
  });

  const nextValue = convertValueBetweenTypes({
    fromType: from,
    toType: to,
    value: field?.value,
    options: nextOptions,
    nextConstraints,
    warnings,
    valueLabel: "Current value",
  });

  const nextDefaultValue = convertValueBetweenTypes({
    fromType: from,
    toType: to,
    value: field?.constraints?.defaultValue,
    options: nextOptions,
    nextConstraints,
    warnings,
    valueLabel: "Default value",
  });

  nextConstraints.defaultValue = nextDefaultValue;

  return {
    fromType: from,
    toType: to,
    lossy: isLossyConversion(from, to) || warnings.length > 0,
    warnings: Array.from(new Set(warnings)),
    nextType: to,
    nextConstraints,
    nextOptions,
    nextValue,
    nextPlaceholder: buildConvertedPlaceholder({
      fromType: from,
      toType: to,
      sourcePlaceholder: field?.placeholder || field?.constraints?.placeholder || "",
    }),
    nextRows: buildConvertedRows({
      fromType: from,
      toType: to,
      sourceRows: field?.rows,
    }),
  };
}

export function buildConvertedField({
  field,
  fromType,
  toType,
}) {
  const report = getFieldTypeConversionReport({
    field,
    fromType,
    toType,
  });

  const nextField = {
    ...clone(field || {}),
    type: report.nextType,
    constraints: report.nextConstraints,
    value: report.nextValue,
    placeholder: report.nextPlaceholder,
  };

  if (CHOICE.has(report.nextType)) {
    nextField.options = report.nextOptions;
  } else {
    nextField.options = [];
  }

  if (report.nextType === "textarea") {
    nextField.rows = report.nextRows || 4;
  } else {
    delete nextField.rows;
  }

  if (report.nextType !== "table") {
    delete nextField.tableConfig;
  }

  if (report.nextType === "checkbox" && typeof nextField.value !== "boolean") {
    nextField.value = false;
  }

  if (report.nextType === "file" && !("constraints" in nextField)) {
    nextField.constraints = defaultConstraintsForType("file");
  }

  return {
    report,
    field: nextField,
  };
}
