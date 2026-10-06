function normalized(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function resolveImportVisit({
  mode,
  visitSource,
  singleVisitIndex,
  bulkVisitIndex,
  visitValue,
  visits = [],
}) {
  if (mode === "single" || visitSource === "fixed") {
    const requestedIndex = Number(mode === "single" ? singleVisitIndex : bulkVisitIndex);
    if (Number.isInteger(requestedIndex) && visits[requestedIndex]) {
      return { index: requestedIndex, issue: "" };
    }
    return { index: null, issue: "The selected visit is no longer available in this study." };
  }

  const requestedName = normalized(visitValue);
  const index = visits.findIndex((visit) => normalized(visit?.name) === requestedName);
  if (index >= 0) return { index, issue: "" };
  return { index: null, issue: `Visit "${String(visitValue || "blank")}" was not found in this study.` };
}

export function validateImportGroup({
  mode,
  groupSource,
  bulkGroupIndex,
  groupValue,
  targetGroupIndex,
  groups = [],
}) {
  if (mode !== "all" || groupSource === "subject" || targetGroupIndex == null || targetGroupIndex < 0) {
    return "";
  }

  const expectedName = String(groups[targetGroupIndex]?.name || "");
  if (groupSource === "fixed") {
    const requestedIndex = Number(bulkGroupIndex);
    if (!Number.isInteger(requestedIndex) || !groups[requestedIndex]) {
      return "The selected group is no longer available in this study.";
    }
    if (requestedIndex !== targetGroupIndex) {
      return `Selected group "${String(groups[requestedIndex]?.name || "")}" does not match the subject group "${expectedName}".`;
    }
    return "";
  }

  if (!normalized(groupValue)) return "Group value is missing in the spreadsheet row.";
  if (normalized(groupValue) !== normalized(expectedName)) {
    return `Group "${String(groupValue)}" does not match the subject group "${expectedName}".`;
  }
  return "";
}
