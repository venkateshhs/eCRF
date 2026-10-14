function asStrings(values) {
  return (Array.isArray(values) ? values : [])
    .map((value) => (value == null ? "" : String(value)))
    .filter(Boolean);
}

export function haveSameChoiceOptions(left, right) {
  const normalizedLeft = asStrings(left)
    .map((value) => value.trim())
    .filter(Boolean)
    .sort();
  const normalizedRight = asStrings(right)
    .map((value) => value.trim())
    .filter(Boolean)
    .sort();

  return (
    normalizedLeft.length === normalizedRight.length &&
    normalizedLeft.every((value, index) => value === normalizedRight[index])
  );
}

export function normalizeDominantOptions(dominantOptions, options = []) {
  const valid = new Set(asStrings(options));
  return Array.from(
    new Set(asStrings(dominantOptions).filter((value) => valid.has(value)))
  );
}

export function normalizeMultiChoiceValue(
  value,
  options = [],
  dominantOptions = [],
  allowOther = false
) {
  const valid = new Set(asStrings(options));
  const dominant = new Set(normalizeDominantOptions(dominantOptions, options));
  const raw = asStrings(value);
  const selected = Array.from(new Set(raw.filter((item) => valid.has(item))));
  if (allowOther) {
    const custom = raw.find((item) => !valid.has(item));
    if (custom && !selected.includes(custom)) selected.push(custom);
  }
  const selectedDominant = selected.find((item) => dominant.has(item));

  return selectedDominant ? [selectedDominant] : selected;
}

export function toggleMultiChoiceValue({
  value,
  option,
  checked,
  options = [],
  dominantOptions = [],
  allowOther = false,
}) {
  const normalizedOption = option == null ? "" : String(option);
  const dominant = new Set(normalizeDominantOptions(dominantOptions, options));
  const selected = new Set(
    normalizeMultiChoiceValue(value, options, dominantOptions, allowOther)
  );

  if (!checked) {
    selected.delete(normalizedOption);
  } else if (dominant.has(normalizedOption)) {
    return [normalizedOption];
  } else {
    for (const dominantOption of dominant) selected.delete(dominantOption);
    selected.add(normalizedOption);
  }

  return Array.from(selected);
}
