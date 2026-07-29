function clone(value) {
  return JSON.parse(JSON.stringify(value ?? {}));
}

function withoutUiState(value) {
  if (Array.isArray(value)) return value.map(withoutUiState);
  if (!value || typeof value !== "object") return value;

  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !key.startsWith("_"))
      .map(([key, nested]) => [key, withoutUiState(nested)])
  );
}

export function constraintEditSnapshot(local, allowedFormatsText = "") {
  return JSON.stringify({
    local: withoutUiState(local || {}),
    allowedFormatsText: String(allowedFormatsText || "").trim(),
  });
}

export function constraintsForSave({
  generated,
  original,
  initialSnapshot,
  currentSnapshot,
  sameType,
  choiceMembershipUnchanged = true,
  finalOptions = null,
}) {
  if (
    !sameType ||
    !initialSnapshot ||
    initialSnapshot !== currentSnapshot ||
    !choiceMembershipUnchanged
  ) {
    return generated;
  }

  const preserved = clone(original);
  if (
    Array.isArray(finalOptions) &&
    Object.prototype.hasOwnProperty.call(preserved, "options")
  ) {
    preserved.options = [...finalOptions];
  }
  return preserved;
}
