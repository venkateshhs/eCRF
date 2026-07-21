const hasOwn = (value, key) =>
  value != null &&
  typeof value === "object" &&
  Object.prototype.hasOwnProperty.call(value, key);

export function cloneConflictValue(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function isSemanticallyEmpty(value) {
  return (
    value === undefined ||
    value === null ||
    value === "" ||
    (Array.isArray(value) && value.length === 0)
  );
}

function normalizeForComparison(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeForComparison);
  }

  if (value && typeof value === "object") {
    return Object.keys(value)
      .sort()
      .reduce((out, key) => {
        out[key] = normalizeForComparison(value[key]);
        return out;
      }, {});
  }

  return value;
}

export function conflictValuesEqual(left, right) {
  // Different field widgets and older saved forms can represent the same
  // untouched blank as missing, null, "", or []. These must not become a
  // clinical-data conflict. Boolean false and numeric zero remain real values.
  if (isSemanticallyEmpty(left) && isSemanticallyEmpty(right)) return true;
  if (left === undefined || right === undefined) return left === right;
  return (
    JSON.stringify(normalizeForComparison(left)) ===
    JSON.stringify(normalizeForComparison(right))
  );
}

function setFieldValue(target, sectionKey, fieldKey, source, value) {
  if (!hasOwn(target, sectionKey) || !target[sectionKey] || typeof target[sectionKey] !== "object") {
    target[sectionKey] = {};
  }

  if (hasOwn(source, fieldKey)) {
    target[sectionKey][fieldKey] = cloneConflictValue(value);
  } else {
    delete target[sectionKey][fieldKey];
  }
}

/**
 * Merge one eCRF slot using the snapshot that the user opened as the base.
 *
 * A field conflicts only when both the local user and the backend changed it
 * from the same base value and the two resulting values differ. Complex field
 * values (tables, files, multi-selects) are intentionally atomic at field level.
 */
export function mergeDataEntryFields(baseData, localData, latestData) {
  const base = baseData && typeof baseData === "object" ? baseData : {};
  const local = localData && typeof localData === "object" ? localData : {};
  const latest = latestData && typeof latestData === "object" ? latestData : {};
  const merged = cloneConflictValue(latest) || {};
  const conflicts = [];

  const sectionKeys = new Set([
    ...Object.keys(base),
    ...Object.keys(local),
    ...Object.keys(latest),
  ]);

  sectionKeys.forEach((sectionKey) => {
    const baseSection =
      base[sectionKey] && typeof base[sectionKey] === "object" ? base[sectionKey] : {};
    const localSection =
      local[sectionKey] && typeof local[sectionKey] === "object" ? local[sectionKey] : {};
    const latestSection =
      latest[sectionKey] && typeof latest[sectionKey] === "object" ? latest[sectionKey] : {};

    const fieldKeys = new Set([
      ...Object.keys(baseSection),
      ...Object.keys(localSection),
      ...Object.keys(latestSection),
    ]);

    fieldKeys.forEach((fieldKey) => {
      const baseValue = hasOwn(baseSection, fieldKey) ? baseSection[fieldKey] : undefined;
      const localValue = hasOwn(localSection, fieldKey) ? localSection[fieldKey] : undefined;
      const latestValue = hasOwn(latestSection, fieldKey) ? latestSection[fieldKey] : undefined;
      const localChanged = !conflictValuesEqual(localValue, baseValue);
      const latestChanged = !conflictValuesEqual(latestValue, baseValue);

      if (
        localChanged &&
        latestChanged &&
        !conflictValuesEqual(localValue, latestValue)
      ) {
        const key = JSON.stringify([sectionKey, fieldKey]);
        conflicts.push({
          key,
          sectionKey,
          fieldKey,
          localPresent: hasOwn(localSection, fieldKey),
          originalValue: cloneConflictValue(baseValue),
          localValue: cloneConflictValue(localValue),
          latestValue: cloneConflictValue(latestValue),
        });
        return;
      }

      if (localChanged) {
        setFieldValue(merged, sectionKey, fieldKey, localSection, localValue);
      }
    });
  });

  return { merged, conflicts };
}

export function applyConflictDecisions(mergedData, conflicts, decisions) {
  const resolved = cloneConflictValue(mergedData) || {};
  const rowConflicts = [];

  (conflicts || []).forEach((conflict) => {
    const decision = decisions?.[conflict.key];
    if (conflict.conflictKind === "concurrent-table-row-addition") {
      rowConflicts.push({ conflict, decision });
      return;
    }
    if (decision !== "local") return;

    if (Array.isArray(conflict.valuePath) && conflict.valuePath.length) {
      if (!resolved[conflict.sectionKey] || typeof resolved[conflict.sectionKey] !== "object") {
        resolved[conflict.sectionKey] = {};
      }
      if (!resolved[conflict.sectionKey][conflict.fieldKey]) {
        resolved[conflict.sectionKey][conflict.fieldKey] = {};
      }

      let target = resolved[conflict.sectionKey][conflict.fieldKey];
      const path = conflict.valuePath;
      for (let index = 0; index < path.length - 1; index += 1) {
        const part = path[index];
        const nextPart = path[index + 1];
        if (target[part] == null) {
          target[part] = typeof nextPart === "number" ? [] : {};
        }
        target = target[part];
      }

      const leaf = path[path.length - 1];
      if (conflict.localPresent) {
        target[leaf] = cloneConflictValue(conflict.localValue);
      } else {
        delete target[leaf];
      }
      return;
    }

    const localSection = conflict.localPresent
      ? { [conflict.fieldKey]: conflict.localValue }
      : {};
    setFieldValue(
      resolved,
      conflict.sectionKey,
      conflict.fieldKey,
      localSection,
      conflict.localValue
    );
  });

  // Work from the last row backwards so inserting a second row cannot shift
  // the indexes of any remaining row-level decisions.
  rowConflicts
    .sort((left, right) => right.conflict.tableRowIndex - left.conflict.tableRowIndex)
    .forEach(({ conflict, decision }) => {
      if (decision !== "local" && decision !== "both") return;
      if (!resolved[conflict.sectionKey] || typeof resolved[conflict.sectionKey] !== "object") {
        resolved[conflict.sectionKey] = {};
      }
      if (!resolved[conflict.sectionKey][conflict.fieldKey]) {
        resolved[conflict.sectionKey][conflict.fieldKey] = { rows: [] };
      }
      const table = resolved[conflict.sectionKey][conflict.fieldKey];
      if (!Array.isArray(table.rows)) table.rows = [];

      if (decision === "local") {
        table.rows[conflict.tableRowIndex] = cloneConflictValue(conflict.localValue);
      } else {
        table.rows.splice(
          conflict.tableRowIndex + 1,
          0,
          cloneConflictValue(conflict.localValue)
        );
      }
    });

  return resolved;
}
