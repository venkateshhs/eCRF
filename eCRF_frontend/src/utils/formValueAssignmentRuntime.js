import { parseDateByConfiguredFormat } from "@/utils/dateFormatParsing";

function getPrimaryForm(study) {
  const forms = study?.content?.study_data?.forms;
  return Array.isArray(forms) ? forms[0] || null : null;
}

export function getValueAssignmentRulesFromStudy(study) {
  const rules = getPrimaryForm(study)?.logic?.valueAssignments;
  return Array.isArray(rules)
    ? rules.filter((rule) => rule && rule.enabled !== false && rule.targetFieldKey)
    : [];
}

function fieldKeys(field) {
  return [
    field?._id,
    field?.id,
    field?.field_id,
    field?.uid,
    field?.key,
    field?.name,
  ]
    .filter(Boolean)
    .map(String);
}

export function buildValueAssignmentFieldLookup(selectedModels) {
  const lookup = new Map();

  (selectedModels || []).forEach((section, sectionIndex) => {
    (section?.fields || []).forEach((field, fieldIndex) => {
      const meta = { sectionIndex, fieldIndex, field, section };
      fieldKeys(field).forEach((key) => {
        if (!lookup.has(key)) lookup.set(key, meta);
      });
    });
  });

  return lookup;
}

export function getValueAssignmentTargetIdSet(study) {
  return new Set(
    getValueAssignmentRulesFromStudy(study).map((rule) =>
      String(rule.targetFieldKey)
    )
  );
}

export function isValueAssignmentTargetField(study, field) {
  if (!field) return false;
  const targetIds = getValueAssignmentTargetIdSet(study);
  return fieldKeys(field).some((key) => targetIds.has(key));
}

function isBlank(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

function toNumber(value) {
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function toDate(value, format = "dd.MM.yyyy") {
  const parsed = parseDateByConfiguredFormat(value, format);
  return parsed ? parsed.getTime() : null;
}

function toTime(value) {
  const match = String(value || "").match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return null;
  return +match[1] * 3600 + +match[2] * 60 + +(match[3] || 0);
}

function choiceValues(value) {
  return Array.isArray(value)
    ? value.map((item) => String(item ?? ""))
    : [String(value ?? "")];
}

function evaluateCondition(condition, sourceField, sourceValue) {
  const operator = String(condition?.operator || "eq").toLowerCase();
  const type = String(sourceField?.type || "").toLowerCase();
  const compareValue = condition?.value;
  const compareValueTo = condition?.valueTo;

  if (operator === "empty" || operator === "is_empty") return isBlank(sourceValue);
  if (operator === "not_empty" || operator === "is_not_empty") return !isBlank(sourceValue);

  if (type === "select" || type === "radio") {
    const left = choiceValues(sourceValue);
    const right = choiceValues(compareValue);
    if (operator === "eq") return right.some((value) => left.includes(value));
    if (operator === "neq") return !isBlank(sourceValue) && !right.some((value) => left.includes(value));
    if (operator === "contains") return right.some((value) => left.includes(value));
    if (operator === "not_contains") return !right.some((value) => left.includes(value));
  }

  if (type === "checkbox") {
    const left = !!sourceValue;
    const right =
      compareValue === true ||
      compareValue === "true" ||
      compareValue === 1 ||
      compareValue === "1";
    if (operator === "eq") return left === right;
    if (operator === "neq") return left !== right;
  }

  if (type === "number" || type === "slider") {
    const left = toNumber(sourceValue);
    const right = toNumber(compareValue);
    const rightTo = toNumber(compareValueTo);
    if (left === null) return false;
    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") return right !== null && rightTo !== null && left >= right && left <= rightTo;
  }

  if (type === "date" || type === "time") {
    const dateFormat = sourceField?.constraints?.dateFormat || "dd.MM.yyyy";
    const converter = type === "date"
      ? (value) => toDate(value, dateFormat)
      : toTime;
    const left = converter(sourceValue);
    const right = converter(compareValue);
    const rightTo = converter(compareValueTo);
    if (left === null) return false;
    if (operator === "eq") return right !== null && left === right;
    if (operator === "neq") return right !== null && left !== right;
    if (operator === "lt") return right !== null && left < right;
    if (operator === "lte") return right !== null && left <= right;
    if (operator === "gt") return right !== null && left > right;
    if (operator === "gte") return right !== null && left >= right;
    if (operator === "between") return right !== null && rightTo !== null && left >= right && left <= rightTo;
  }

  const left = String(sourceValue ?? "");
  const right = String(compareValue ?? "");
  const rightTo = String(compareValueTo ?? "");
  if (operator === "eq") return left === right;
  if (operator === "neq") return !isBlank(sourceValue) && left !== right;
  if (operator === "contains") return left.includes(right);
  if (operator === "not_contains") return !left.includes(right);
  if (operator === "starts_with") return left.startsWith(right);
  if (operator === "ends_with") return left.endsWith(right);
  if (operator === "between") return left >= right && left <= rightTo;
  if (operator === "regex") {
    try {
      return new RegExp(right).test(left);
    } catch {
      return false;
    }
  }
  return false;
}

function ruleMatches(rule, lookup, cellData) {
  const conditions = Array.isArray(rule?.conditions)
    ? rule.conditions.filter((condition) => condition?.sourceFieldKey)
    : [];
  if (!conditions.length) return false;

  const results = conditions.map((condition) => {
    const source = lookup.get(String(condition.sourceFieldKey));
    if (!source) return false;
    const value = cellData?.[source.sectionIndex]?.[source.fieldIndex];
    return evaluateCondition(condition, source.field, value);
  });

  return String(rule?.match || "all").toLowerCase() === "any"
    ? results.some(Boolean)
    : results.every(Boolean);
}

function fieldOptions(field) {
  const options = field?.options || field?.constraints?.options || [];
  return Array.isArray(options)
    ? options.map((option) =>
        typeof option === "object"
          ? String(option?.value ?? option?.label ?? option?.name ?? "")
          : String(option)
      )
    : [];
}

function coerceOutputValue(field, value) {
  const type = String(field?.type || "").toLowerCase();
  if (type === "checkbox") {
    return {
      ok: true,
      value:
        value === true ||
        value === "true" ||
        value === 1 ||
        value === "1",
    };
  }

  if (type === "number" || type === "slider") {
    const number = toNumber(value);
    return number === null
      ? { ok: false, value: null, warning: "Output is not a valid number." }
      : { ok: true, value: number };
  }

  if (type === "select" || type === "radio") {
    const options = fieldOptions(field);
    const candidate = String(value ?? "");
    const allowMultiple = type === "radio" && !!field?.constraints?.allowMultiple;
    return options.includes(candidate)
      ? { ok: true, value: allowMultiple ? [candidate] : candidate }
      : { ok: false, value: null, warning: `Output "${candidate}" is not a valid target option.` };
  }

  if (["text", "textarea", "date", "time"].includes(type)) {
    return { ok: true, value: String(value ?? "") };
  }

  return {
    ok: false,
    value: null,
    warning: `Target field type "${type || "unknown"}" is not supported.`,
  };
}

function emptyValueForField(field) {
  const type = String(field?.type || "").toLowerCase();
  if (type === "checkbox") return false;
  if (type === "radio" && field?.constraints?.allowMultiple) return [];
  if (type === "number" || type === "slider") return null;
  return "";
}

function valuesEqual(left, right) {
  if (Array.isArray(left) || Array.isArray(right)) {
    return JSON.stringify(left) === JSON.stringify(right);
  }
  return left === right;
}

export function evaluateValueAssignments(
  study,
  selectedModels,
  currentCellData,
  fieldLookup = null
) {
  const rules = getValueAssignmentRulesFromStudy(study);
  if (!rules.length) return { updates: [], warnings: [] };

  const lookup = fieldLookup || buildValueAssignmentFieldLookup(selectedModels);
  const working = (currentCellData || []).map((section) =>
    Array.isArray(section) ? [...section] : []
  );
  const warnings = [];
  const updatesByTarget = new Map();
  const grouped = new Map();

  rules.forEach((rule, index) => {
    const target = String(rule.targetFieldKey || "");
    if (!grouped.has(target)) grouped.set(target, []);
    grouped.get(target).push({ ...rule, _order: Number(rule.priority ?? index) });
  });

  grouped.forEach((targetRules) => {
    targetRules.sort((a, b) => a._order - b._order);
  });

  const maxPasses = Math.max(2, rules.length + 1);
  let changedOnLastPass = false;

  for (let pass = 0; pass < maxPasses; pass += 1) {
    let changed = false;

    grouped.forEach((targetRules, targetKey) => {
      const target = lookup.get(targetKey);
      if (!target) {
        warnings.push(`Assignment target "${targetKey}" was not found.`);
        return;
      }

      const current = working?.[target.sectionIndex]?.[target.fieldIndex];
      const matched = targetRules.find((rule) => ruleMatches(rule, lookup, working));

      if (!matched) {
        const shouldClear = targetRules.some(
          (rule) => !!rule.overwriteManualInputs && rule.clearWhenNoMatch !== false
        );
        const emptyValue = emptyValueForField(target.field);
        if (shouldClear && !valuesEqual(current, emptyValue)) {
          working[target.sectionIndex][target.fieldIndex] = emptyValue;
          updatesByTarget.set(targetKey, {
            targetFieldKey: targetKey,
            sectionIndex: target.sectionIndex,
            fieldIndex: target.fieldIndex,
            value: emptyValue,
            ruleId: null,
          });
          changed = true;
        }
        return;
      }

      if (!matched.overwriteManualInputs && !isBlank(current)) return;

      const coerced = coerceOutputValue(target.field, matched.outputValue);
      if (!coerced.ok) {
        warnings.push(coerced.warning);
        return;
      }

      if (!valuesEqual(current, coerced.value)) {
        working[target.sectionIndex][target.fieldIndex] = coerced.value;
        updatesByTarget.set(targetKey, {
          targetFieldKey: targetKey,
          sectionIndex: target.sectionIndex,
          fieldIndex: target.fieldIndex,
          value: coerced.value,
          ruleId: matched.id || null,
        });
        changed = true;
      }
    });

    changedOnLastPass = changed;
    if (!changed) break;
  }

  if (changedOnLastPass) {
    warnings.push("Value-assignment rules may contain a circular dependency.");
  }

  return {
    updates: Array.from(updatesByTarget.values()),
    warnings: Array.from(new Set(warnings)),
  };
}
