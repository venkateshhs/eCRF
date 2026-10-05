export const STUDY_BEFORE_IDLE_EVENT = "casee:study-before-idle";

export function normalizedStudyStatus(value, fallback = "DRAFT") {
  const status = String(value || "").trim().toUpperCase();
  return status || fallback;
}

export function isDraftStudyStatus(value) {
  return normalizedStudyStatus(value) === "DRAFT";
}
