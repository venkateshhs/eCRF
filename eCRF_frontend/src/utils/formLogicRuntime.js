/* eslint-disable */
import { create, all } from "mathjs";

/* ============================================================
   MATHJS RUNTIME
   ============================================================ */

const math = create(all, {});

// Reduce risky parser surface as recommended by mathjs security guidance.
// We only need compile/evaluate support indirectly plus normal math functions.
try {
  math.import({
    import: function () {
      throw new Error("math.import is disabled in calculation expressions.");
    },
    createUnit: function () {
      throw new Error("createUnit is disabled in calculation expressions.");
    },
    reviver: function () {
      throw new Error("reviver is disabled in calculation expressions.");
    },
    simplify: function () {
      throw new Error("simplify is disabled in calculation expressions.");
    },
    derivative: function () {
      throw new Error("derivative is disabled in calculation expressions.");
    },
    resolve: function () {
      throw new Error("resolve is disabled in calculation expressions.");
    }
  }, { override: true });
} catch {}

try {
  math.import({
    ifElse: (cond, a, b) => (cond ? a : b),
    nz: (v, fallback = 0) => (v === null || v === undefined || v === "" ? fallback : v),
    mean: (...args) => {
      const arr = Array.isArray(args[0]) && args.length === 1 ? args[0] : args;
      const nums = arr.map(Number).filter(Number.isFinite);
      if (!nums.length) return 0;
      return nums.reduce((a, b) => a + b, 0) / nums.length;
    }
  }, { override: true });
} catch {}

/* ============================================================
   BASIC HELPERS
   ============================================================ */

function isFiniteNumber(n) {
  return typeof n === "number" && Number.isFinite(n);
}

function toNumber(val) {
  if (val === null || val === undefined || val === "") return null;
  if (typeof val === "number") return Number.isFinite(val) ? val : null;
  const n = Number(val);
  return Number.isFinite(n) ? n : null;
}

function valuesToNumbers(values) {
  return values.map(toNumber).filter((n) => n !== null);
}

function meanLegacy(nums) {
  if (!nums.length) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid];
}

function mode(nums) {
  if (!nums.length) return null;
  const freq = new Map();
  nums.forEach((n) => freq.set(n, (freq.get(n) || 0) + 1));
  let bestVal = null;
  let bestCount = -1;
  for (const [val, count] of freq.entries()) {
    if (count > bestCount) {
      bestVal = val;
      bestCount = count;
    }
  }
  return bestVal;
}

function variancePopulation(nums) {
  if (!nums.length) return null;
  const m = meanLegacy(nums);
  return nums.reduce((acc, n) => acc + Math.pow(n - m, 2), 0) / nums.length;
}

function varianceSample(nums) {
  if (nums.length < 2) return null;
  const m = meanLegacy(nums);
  return nums.reduce((acc, n) => acc + Math.pow(n - m, 2), 0) / (nums.length - 1);
}

function stddevPopulation(nums) {
  const v = variancePopulation(nums);
  return v === null ? null : Math.sqrt(v);
}

function stddevSample(nums) {
  const v = varianceSample(nums);
  return v === null ? null : Math.sqrt(v);
}

function roundToDecimals(val, decimals) {
  if (!isFiniteNumber(val)) return val;
  const d = Number.isFinite(Number(decimals)) ? Number(decimals) : null;
  if (d === null) return val;
  return Number(val.toFixed(d));
}

/* ============================================================
   STUDY / FORM HELPERS
   ============================================================ */

export function getStudyFormsFromStudy(study) {
  const sd = study?.content?.study_data || {};
  if (Array.isArray(sd.forms) && sd.forms.length) return sd.forms;
  return [];
}

export function getPrimaryFormFromStudy(study) {
  const forms = getStudyFormsFromStudy(study);
  return forms[0] || null;
}

export function getCalculationRulesFromStudy(study) {
  const form = getPrimaryFormFromStudy(study);
  const calculations = form?.logic?.calculations;
  return Array.isArray(calculations)
    ? calculations.filter((r) => r && r.enabled !== false && (r.kind === "calc_expr" || r.kind === "calc"))
    : [];
}

export function buildFieldLookup(selectedModels) {
  const lookup = new Map();

  (selectedModels || []).forEach((section, mIdx) => {
    (section?.fields || []).forEach((field, fIdx) => {
      const keys = [
        field?._id,
        field?.id,
        field?.field_id,
        field?.uid,
        field?.key,
        field?.name,
        field?.label,
        field?.title,
      ].filter(Boolean);

      const meta = {
        mIdx,
        fIdx,
        field,
        section,
      };

      keys.forEach((k) => {
        if (!lookup.has(String(k))) {
          lookup.set(String(k), meta);
        }
      });
    });
  });

  return lookup;
}

export function getCalculatedTargetIdSet(study) {
  const rules = getCalculationRulesFromStudy(study);
  const out = new Set();
  rules.forEach((r) => {
    if (r?.target) out.add(String(r.target));
  });
  return out;
}

export function isCalculatedRuntimeField(study, field) {
  if (!field) return false;
  if (field.computed || field.isCalculatedField) return true;

  const targetIds = getCalculatedTargetIdSet(study);
  const keys = [
    field?._id,
    field?.id,
    field?.field_id,
    field?.uid,
    field?.key,
    field?.name,
  ].filter(Boolean);

  return keys.some((k) => targetIds.has(String(k)));
}

/* ============================================================
   FIELD KEY HELPERS
   ============================================================ */

function getFieldKeys(field) {
  return [
    field?._id,
    field?.id,
    field?.field_id,
    field?.uid,
    field?.key,
    field?.name,
    field?.label,
    field?.title,
  ]
    .filter(Boolean)
    .map(String);
}

function getMetaForFieldId(selectedModels, fieldId) {
  const lookup = buildFieldLookup(selectedModels);
  return lookup.get(String(fieldId)) || null;
}

function getRawFieldValueById(selectedModels, currentCellData, fieldId) {
  const meta = getMetaForFieldId(selectedModels, fieldId);
  if (!meta) return null;
  return currentCellData?.[meta.mIdx]?.[meta.fIdx];
}

function getFieldLabelByIdInternal(selectedModels, fieldId) {
  const lookup = buildFieldLookup(selectedModels);
  const meta = lookup.get(String(fieldId));
  if (!meta?.field) return "Field";
  return meta.field.label || meta.field.name || meta.field.title || "Field";
}

/* ============================================================
   EXPRESSION RULE HELPERS
   ============================================================ */

function resolveMappedChoice(rawValue, mappings) {
  if (rawValue === null || rawValue === undefined || rawValue === "") return null;
  if (!mappings || typeof mappings !== "object") return null;

  const exact = mappings[String(rawValue)];
  const n = Number(exact);
  return Number.isFinite(n) ? n : null;
}

function resolveBooleanScore(rawValue, mappings) {
  const checked = rawValue === true || rawValue === "true" || rawValue === 1 || rawValue === "1";
  const key = checked ? "__checked" : "__unchecked";
  const n = Number(mappings?.[key]);
  return Number.isFinite(n) ? n : null;
}

function resolveSymbolValue(symbolDef, rawValue, blankPolicy = "strict") {
  const valueType = String(symbolDef?.valueType || "number");

  if (valueType === "number") {
    const n = toNumber(rawValue);
    if (n === null && blankPolicy === "zero") return 0;
    return n;
  }

  if (valueType === "mapped_choice") {
    const n = resolveMappedChoice(rawValue, symbolDef.mappings || {});
    if (n === null && blankPolicy === "zero") return 0;
    return n;
  }

  if (valueType === "boolean_score") {
    const n = resolveBooleanScore(rawValue, symbolDef.mappings || {});
    if (n === null && blankPolicy === "zero") return 0;
    return n;
  }

  const fallback = toNumber(rawValue);
  if (fallback === null && blankPolicy === "zero") return 0;
  return fallback;
}

function buildScopeForExpressionRule(rule, selectedModels, currentCellData) {
  const scope = {};
  const symbolMap = rule?.symbolMap || {};
  const blankPolicy = rule?.blankPolicy || "strict";

  for (const [symbol, def] of Object.entries(symbolMap)) {
    const rawValue = getRawFieldValueById(selectedModels, currentCellData, def?.fieldId);
    scope[symbol] = resolveSymbolValue(def, rawValue, blankPolicy);
  }

  return scope;
}

function hasStrictMissingValues(scope) {
  return Object.values(scope).some((v) => v === null || typeof v === "undefined" || Number.isNaN(v));
}

function compileRuleExpression(rule) {
  const expr = String(rule?.expression || "").trim();
  if (!expr) throw new Error("Expression is empty.");
  return math.compile(expr);
}

export function computeExpressionCalculation(rule, selectedModels, currentCellData) {
  try {
    const scope = buildScopeForExpressionRule(rule, selectedModels, currentCellData);

    if ((rule?.blankPolicy || "strict") === "strict" && hasStrictMissingValues(scope)) {
      return {
        ok: false,
        value: null,
        warning: "One or more inputs are missing or unmapped."
      };
    }

    const compiled = compileRuleExpression(rule);
    const result = compiled.evaluate(scope);
    const numeric = Number(result);

    if (!Number.isFinite(numeric)) {
      return {
        ok: false,
        value: null,
        warning: "Expression result is not a finite number."
      };
    }

    return {
      ok: true,
      value: roundToDecimals(numeric, rule?.decimals),
      warning: ""
    };
  } catch (err) {
    return {
      ok: false,
      value: null,
      warning: err?.message || "Failed to evaluate expression."
    };
  }
}

/* ============================================================
   LEGACY RULE SUPPORT
   ============================================================ */

export function computeLegacyCalculation(rule, sourceValues) {
  const op = String(rule?.op || "").toLowerCase();
  const nums = valuesToNumbers(sourceValues);
  const rawCount = Array.isArray(sourceValues) ? sourceValues.length : 0;
  const nonEmptyCount = (sourceValues || []).filter(
    (v) => !(v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0))
  ).length;

  if (!Array.isArray(sourceValues) || sourceValues.length < 2) {
    return {
      ok: false,
      value: null,
      warning: "At least 2 source fields are required.",
    };
  }

  if (
    ["sum", "subtract", "multiply", "divide", "mean", "median", "mode", "min", "max", "range", "stddev_pop", "stddev_samp", "variance_pop", "variance_samp"].includes(op)
  ) {
    if (!nums.length) {
      return {
        ok: false,
        value: null,
        warning: "No numeric source values available.",
      };
    }
  }

  switch (op) {
    case "sum":
      return { ok: true, value: nums.reduce((a, b) => a + b, 0), warning: "" };

    case "subtract": {
      if (!nums.length) return { ok: false, value: null, warning: "No numeric source values available." };
      let result = nums[0];
      for (let i = 1; i < nums.length; i++) result -= nums[i];
      return { ok: true, value: result, warning: "" };
    }

    case "multiply":
      return { ok: true, value: nums.reduce((a, b) => a * b, 1), warning: "" };

    case "divide": {
      if (!nums.length) return { ok: false, value: null, warning: "No numeric source values available." };
      let result = nums[0];
      for (let i = 1; i < nums.length; i++) {
        if (nums[i] === 0) {
          return {
            ok: false,
            value: null,
            warning: "Division by zero is not allowed.",
          };
        }
        result /= nums[i];
      }
      return { ok: true, value: result, warning: "" };
    }

    case "mean":
      return { ok: true, value: meanLegacy(nums), warning: "" };

    case "median":
      return { ok: true, value: median(nums), warning: "" };

    case "mode":
      return { ok: true, value: mode(nums), warning: "" };

    case "min":
      return { ok: true, value: Math.min(...nums), warning: "" };

    case "max":
      return { ok: true, value: Math.max(...nums), warning: "" };

    case "range":
      return { ok: true, value: Math.max(...nums) - Math.min(...nums), warning: "" };

    case "count":
      return { ok: true, value: nonEmptyCount, warning: "" };

    case "count_all":
      return { ok: true, value: rawCount, warning: "" };

    case "stddev_pop":
      return { ok: true, value: stddevPopulation(nums), warning: nums.length ? "" : "No numeric source values available." };

    case "stddev_samp": {
      if (nums.length < 2) {
        return {
          ok: false,
          value: null,
          warning: "Sample standard deviation needs at least 2 numeric values.",
        };
      }
      return { ok: true, value: stddevSample(nums), warning: "" };
    }

    case "variance_pop":
      return { ok: true, value: variancePopulation(nums), warning: nums.length ? "" : "No numeric source values available." };

    case "variance_samp": {
      if (nums.length < 2) {
        return {
          ok: false,
          value: null,
          warning: "Sample variance needs at least 2 numeric values.",
        };
      }
      return { ok: true, value: varianceSample(nums), warning: "" };
    }

    default:
      return {
        ok: false,
        value: null,
        warning: `Unsupported calculation operation "${op}".`,
      };
  }
}

export function computeCalculation(rule, selectedModels, currentCellData, sourceValues = null) {
  if (String(rule?.kind || "") === "calc_expr") {
    return computeExpressionCalculation(rule, selectedModels, currentCellData);
  }

  if (Array.isArray(sourceValues)) {
    return computeLegacyCalculation(rule, sourceValues);
  }

  const values = (rule?.sources || []).map((srcId) =>
    getRawFieldValueById(selectedModels, currentCellData, srcId)
  );
  return computeLegacyCalculation(rule, values);
}

/* ============================================================
   RULE LOOKUP + FORMULA LABELS
   ============================================================ */

export function findCalculationRuleForField(study, field) {
  if (!field) return null;

  const rules = getCalculationRulesFromStudy(study);
  if (!rules.length) return null;

  const keys = getFieldKeys(field);
  return rules.find((r) => keys.includes(String(r?.target || ""))) || null;
}

export function getFieldLabelById(selectedModels, fieldId) {
  return getFieldLabelByIdInternal(selectedModels, fieldId);
}

function replaceSymbolsWithLabels(expression, rule, selectedModels) {
  let out = String(expression || "");
  const entries = Object.entries(rule?.symbolMap || {}).sort((a, b) => b[0].length - a[0].length);

  entries.forEach(([symbol, def]) => {
    const label =
      def?.fieldLabel ||
      getFieldLabelByIdInternal(selectedModels, def?.fieldId) ||
      symbol;

    const rx = new RegExp(`\\b${symbol.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g");
    out = out.replace(rx, label);
  });

  return out;
}

export function buildCalculationFormula(rule, selectedModels, targetField = null) {
  if (!rule) return "";

  const targetLabel =
    targetField?.label ||
    targetField?.name ||
    targetField?.title ||
    getFieldLabelByIdInternal(selectedModels, rule.target) ||
    "Result";

  if (rule.kind === "calc_expr") {
    return `${targetLabel} = ${replaceSymbolsWithLabels(rule.expression, rule, selectedModels)}`;
  }

  const sourceLabels = (rule.sources || []).map((srcId) =>
    getFieldLabelByIdInternal(selectedModels, srcId)
  );

  const A = sourceLabels[0];
  const rest = sourceLabels.slice(1);
  const op = String(rule?.op || "").toLowerCase();

  if (op === "sum") return `${targetLabel} = ${sourceLabels.join(" + ")}`;
  if (op === "subtract") return `${targetLabel} = ${A}${rest.length ? " - " + rest.join(" - ") : ""}`;
  if (op === "multiply") return `${targetLabel} = ${sourceLabels.join(" × ")}`;
  if (op === "divide") return `${targetLabel} = ${A}${rest.length ? " ÷ " + rest.join(" ÷ ") : ""}`;
  if (op === "mean") return `${targetLabel} = MEAN(${sourceLabels.join(", ")})`;
  if (op === "median") return `${targetLabel} = MEDIAN(${sourceLabels.join(", ")})`;
  if (op === "mode") return `${targetLabel} = MODE(${sourceLabels.join(", ")})`;
  if (op === "min") return `${targetLabel} = MIN(${sourceLabels.join(", ")})`;
  if (op === "max") return `${targetLabel} = MAX(${sourceLabels.join(", ")})`;
  if (op === "range") return `${targetLabel} = RANGE(${sourceLabels.join(", ")})`;
  if (op === "count") return `${targetLabel} = COUNT_NON_EMPTY(${sourceLabels.join(", ")})`;
  if (op === "count_all") return `${targetLabel} = COUNT_ALL(${sourceLabels.join(", ")})`;
  if (op === "stddev_pop") return `${targetLabel} = STDDEV_POP(${sourceLabels.join(", ")})`;
  if (op === "stddev_samp") return `${targetLabel} = STDDEV_SAMP(${sourceLabels.join(", ")})`;
  if (op === "variance_pop") return `${targetLabel} = VAR_POP(${sourceLabels.join(", ")})`;
  if (op === "variance_samp") return `${targetLabel} = VAR_SAMP(${sourceLabels.join(", ")})`;

  return `${targetLabel} = ${String(rule.op || "CALC").toUpperCase()}(${sourceLabels.join(", ")})`;
}

export function getCalculationFormulaForField(study, selectedModels, field) {
  const rule = findCalculationRuleForField(study, field);
  if (!rule) return "";
  return buildCalculationFormula(rule, selectedModels, field);
}

/* ============================================================
   VISIBILITY LOGIC RUNTIME
   ============================================================ */

function isBlankValue(val) {
  if (val === null || val === undefined) return true;
  if (typeof val === "string") return val.trim() === "";
  if (Array.isArray(val)) return val.length === 0;
  return false;
}

function toComparableNumber(val) {
  if (val === null || val === undefined || val === "") return null;
  const n = Number(val);
  return Number.isFinite(n) ? n : null;
}

function compareArraysHasAny(leftArr, rightArr) {
  if (!Array.isArray(leftArr) || !Array.isArray(rightArr)) return false;
  return rightArr.some((v) => leftArr.includes(v));
}

function parseDateLike(value, format = "dd.MM.yyyy") {
  if (!value) return null;
  const s = String(value).trim();

  const map = {
    "dd.MM.yyyy": /^(\d{2})\.(\d{2})\.(\d{4})$/,
    "MM-dd-yyyy": /^(\d{2})-(\d{2})-(\d{4})$/,
    "dd-MM-yyyy": /^(\d{2})-(\d{2})-(\d{4})$/,
    "yyyy-MM-dd": /^(\d{4})-(\d{2})-(\d{2})$/,
    "MM/yyyy": /^(\d{2})\/(\d{4})$/,
    "MM-yyyy": /^(\d{2})-(\d{4})$/,
    "yyyy/MM": /^(\d{4})\/(\d{2})$/,
    "yyyy-MM": /^(\d{4})-(\d{2})$/,
    "yyyy": /^(\d{4})$/,
  };

  const rx = map[format];
  if (!rx) return null;

  const m = rx.exec(s);
  if (!m) return null;

  let y, M, d;

  if (format === "dd.MM.yyyy") {
    d = +m[1]; M = +m[2]; y = +m[3];
  } else if (format === "MM-dd-yyyy") {
    M = +m[1]; d = +m[2]; y = +m[3];
  } else if (format === "dd-MM-yyyy") {
    d = +m[1]; M = +m[2]; y = +m[3];
  } else if (format === "yyyy-MM-dd") {
    y = +m[1]; M = +m[2]; d = +m[3];
  } else if (format === "MM/yyyy" || format === "MM-yyyy") {
    M = +m[1]; y = +m[2]; d = 1;
  } else if (format === "yyyy/MM" || format === "yyyy-MM") {
    y = +m[1]; M = +m[2]; d = 1;
  } else if (format === "yyyy") {
    y = +m[1]; M = 1; d = 1;
  }

  const dt = new Date(y, M - 1, d);
  return Number.isNaN(dt.getTime()) ? null : dt.getTime();
}

function parseTimeLike(value) {
  if (!value) return null;
  const s = String(value).trim();
  const mm = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(s);
  if (!mm) return null;

  const h = +mm[1];
  const m = +mm[2];
  const sec = mm[3] ? +mm[3] : 0;

  return h * 3600 + m * 60 + sec;
}

function evaluateSingleVisibilityRule(rule, sourceValue, sourceField) {
  const operator = String(rule?.operator || "eq").toLowerCase();
  const sourceType = String(sourceField?.type || "").toLowerCase();
  const constraints = sourceField?.constraints || {};
  const compareValue = rule?.value;
  const compareValueTo = rule?.valueTo;

  if (operator === "empty") return isBlankValue(sourceValue);
  if (operator === "not_empty" || operator === "is_not_empty") return !isBlankValue(sourceValue);

 if (sourceType === "select" || sourceType === "radio") {
  if (Array.isArray(sourceValue)) {
    if (operator === "eq") {
      if (Array.isArray(compareValue)) return compareArraysHasAny(sourceValue, compareValue);
      return sourceValue.includes(compareValue);
    }

    if (operator === "neq") {
      // Blank / no selection should NOT satisfy "not equal"
      if (sourceValue.length === 0) return false;

      if (Array.isArray(compareValue)) return !compareArraysHasAny(sourceValue, compareValue);
      return !sourceValue.includes(compareValue);
    }
  } else {
    if (operator === "eq") {
      if (Array.isArray(compareValue)) {
        return compareValue.map(String).includes(String(sourceValue ?? ""));
      }

      return String(sourceValue ?? "") === String(compareValue ?? "");
    }

    if (operator === "neq") {
      // Blank / no selection should NOT satisfy "not equal"
      if (isBlankValue(sourceValue)) return false;

      if (Array.isArray(compareValue)) {
        return !compareValue.map(String).includes(String(sourceValue ?? ""));
      }

      return String(sourceValue ?? "") !== String(compareValue ?? "");
    }
  }
}

  if (sourceType === "checkbox") {
    const left = !!sourceValue;
    const right = compareValue === true || compareValue === "true" || compareValue === 1 || compareValue === "1";
    if (operator === "eq") return left === right;
    if (operator === "neq") return left !== right;
  }

  if (sourceType === "number" || sourceType === "slider") {
    const left = toComparableNumber(sourceValue);
    const right = toComparableNumber(compareValue);
    const rightTo = toComparableNumber(compareValueTo);

    if (left === null) return false;

    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") return right !== null && rightTo !== null && left >= right && left <= rightTo;
  }

  if (sourceType === "date") {
    const fmt = constraints.dateFormat || "dd.MM.yyyy";
    const left = parseDateLike(sourceValue, fmt);
    const right = parseDateLike(compareValue, fmt);
    const rightTo = parseDateLike(compareValueTo, fmt);

    if (left === null) return false;

    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") return right !== null && rightTo !== null && left >= right && left <= rightTo;
  }

  if (sourceType === "time") {
    const left = parseTimeLike(sourceValue);
    const right = parseTimeLike(compareValue);
    const rightTo = parseTimeLike(compareValueTo);

    if (left === null) return false;

    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") return right !== null && rightTo !== null && left >= right && left <= rightTo;
  }

  const leftText = String(sourceValue ?? "");
  const rightText = String(compareValue ?? "");
  const rightToText = String(compareValueTo ?? "");

  if (operator === "eq") return leftText === rightText;
  if (operator === "neq") return leftText !== rightText;
  if (operator === "contains") return leftText.includes(rightText);
  if (operator === "starts_with") return leftText.startsWith(rightText);
  if (operator === "ends_with") return leftText.endsWith(rightText);
  if (operator === "regex") {
    try {
      return new RegExp(rightText).test(leftText);
    } catch {
      return false;
    }
  }
  if (operator === "between") return leftText >= rightText && leftText <= rightToText;

  return false;
}

/* ============================================================
   POPUP / INLINE REMINDER RUNTIME
   ============================================================ */

function normalizePopupLogic(raw) {
  const src = raw && typeof raw === "object" ? raw : {};

  return {
    enabled: src.enabled === true,
    operator: String(src.operator || "eq").toLowerCase(),
    message: String(src.message || "").trim(),
    value: src.value,
    valueTo: src.valueTo,

    // Optional future support:
    // If this exists, the same reminder can also be shown under the target field.
    targetFieldKey: String(
      src.targetFieldKey ||
      src.targetFieldId ||
      src.target ||
      ""
    ).trim(),
  };
}

function fieldHasKey(field, key) {
  const needle = String(key || "").trim();
  if (!needle) return false;

  return [
    field?._id,
    field?.id,
    field?.field_id,
    field?.uid,
    field?.key,
    field?.name,
    field?.label,
    field?.title,
  ]
    .filter(Boolean)
    .map(String)
    .includes(needle);
}

export function evaluatePopupLogic(
  study,
  selectedModels,
  currentCellData,
  sourceMIdx,
  sourceFIdx
) {
  const sourceField = selectedModels?.[sourceMIdx]?.fields?.[sourceFIdx];
  if (!sourceField) return false;

  const popupLogic = normalizePopupLogic(sourceField?.constraints?.popupLogic);

  if (!popupLogic.enabled) return false;
  if (!popupLogic.message) return false;

  // If the source field itself is hidden, do not show reminders for it.
  const sourceVisible = evaluateFieldVisibility(
    study,
    selectedModels,
    currentCellData,
    sourceMIdx,
    sourceFIdx
  );

  if (!sourceVisible) return false;

  const sourceValue = currentCellData?.[sourceMIdx]?.[sourceFIdx];

  return evaluateSingleVisibilityRule(
    {
      operator: popupLogic.operator,
      value: popupLogic.value,
      valueTo: popupLogic.valueTo,
    },
    sourceValue,
    sourceField
  );
}

export function getPopupReminderMessage(selectedModels, sourceMIdx, sourceFIdx) {
  const sourceField = selectedModels?.[sourceMIdx]?.fields?.[sourceFIdx];
  const popupLogic = normalizePopupLogic(sourceField?.constraints?.popupLogic);

  return popupLogic.enabled ? popupLogic.message : "";
}

export function getPopupReminderMessagesForField(
  study,
  selectedModels,
  currentCellData,
  displayMIdx,
  displayFIdx
) {
  const displayField = selectedModels?.[displayMIdx]?.fields?.[displayFIdx];
  if (!displayField) return [];

  const messages = [];

  (selectedModels || []).forEach((section, sourceMIdx) => {
    (section?.fields || []).forEach((sourceField, sourceFIdx) => {
      const popupLogic = normalizePopupLogic(sourceField?.constraints?.popupLogic);

      if (!popupLogic.enabled || !popupLogic.message) return;

      const shouldShowSourceMessage =
        sourceMIdx === displayMIdx && sourceFIdx === displayFIdx;

      const shouldShowTargetMessage =
        !!popupLogic.targetFieldKey &&
        fieldHasKey(displayField, popupLogic.targetFieldKey);

      if (!shouldShowSourceMessage && !shouldShowTargetMessage) return;

      const matched = evaluatePopupLogic(
        study,
        selectedModels,
        currentCellData,
        sourceMIdx,
        sourceFIdx
      );

      if (!matched) return;

      if (!messages.includes(popupLogic.message)) {
        messages.push(popupLogic.message);
      }
    });
  });

  return messages;
}

export function evaluateFieldVisibility(
  study,
  selectedModels,
  currentCellData,
  targetMIdx,
  targetFIdx,
  visiting = new Set()
) {
  const targetField = selectedModels?.[targetMIdx]?.fields?.[targetFIdx];
  if (!targetField) return true;

  const logic = targetField?.constraints?.visibilityLogic;
  if (!logic || !Array.isArray(logic.rules) || !logic.rules.length) return true;

  const targetKey = `${targetMIdx}:${targetFIdx}`;
  if (visiting.has(targetKey)) {
    // Prevent infinite recursion if someone creates circular visibility rules.
    return false;
  }

  const nextVisiting = new Set(visiting);
  nextVisiting.add(targetKey);

  const lookup = buildFieldLookup(selectedModels);

  const results = logic.rules.map((rule) => {
    const srcKey = String(rule?.sourceFieldKey || "");
    if (!srcKey) return false;

    const meta = lookup.get(srcKey);
    if (!meta) return false;

    // IMPORTANT:
    // If the source field itself is hidden, this rule must be false.
    // Example: C depends on B != Tablet, but B is hidden because A = No.
    const sourceVisible = evaluateFieldVisibility(
      study,
      selectedModels,
      currentCellData,
      meta.mIdx,
      meta.fIdx,
      nextVisiting
    );

    if (!sourceVisible) return false;

    const sourceField = meta.field;
    const sourceValue = currentCellData?.[meta.mIdx]?.[meta.fIdx];

    return evaluateSingleVisibilityRule(rule, sourceValue, sourceField);
  });

  const matchMode = String(logic.match || "all").toLowerCase();
  const matched = matchMode === "any"
    ? results.some(Boolean)
    : results.every(Boolean);

  const action = String(logic.action || "show").toLowerCase();

  if (action === "hide") {
    return !matched;
  }

  return matched;
}

export function sectionHasVisibleFields(study, selectedModels, currentCellData, mIdx) {
  const fields = selectedModels?.[mIdx]?.fields || [];
  if (!fields.length) return false;

  return fields.some((_, fIdx) =>
    evaluateFieldVisibility(study, selectedModels, currentCellData, mIdx, fIdx)
  );
}