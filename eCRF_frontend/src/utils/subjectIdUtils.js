export const DEFAULT_SUBJECT_ID_CONFIG = {
  mode: "title_based",
  preset: "subj-prefix-number",
  prefix: "ST",
  pattern: "SUBJ-{PREFIX}-{NUMBER}",
  padding: 3,
  startNumber: 1,
  locked: false,
};

export const SUBJECT_ID_PRESET_DEFINITIONS = [
  {
    key: "subj-prefix-number",
    mode: "title_based",
    pattern: "SUBJ-{PREFIX}-{NUMBER}",
    label: (prefix) => `Title based default: SUBJ-${prefix}-001`,
  },
  {
    key: "prefix-number",
    mode: "custom",
    pattern: "{PREFIX}-{NUMBER}",
    label: (prefix) => `${prefix}-001`,
  },
  {
    key: "study-prefix-number",
    mode: "custom",
    pattern: "STUDY-{PREFIX}-{NUMBER}",
    label: (prefix) => `STUDY-${prefix}-001`,
  },
  {
    key: "s-number",
    mode: "custom",
    pattern: "S{NUMBER}",
    label: () => "S001",
  },
  {
    key: "p-number",
    mode: "custom",
    pattern: "P{NUMBER}",
    label: () => "P001",
  },
  {
    key: "subj-prefix-rand6",
    mode: "random",
    pattern: "SUBJ-{PREFIX}-{RAND6}",
    label: (prefix) => `SUBJ-${prefix}-A8F3K2`,
  },
  {
    key: "subj-prefix-uuid8",
    mode: "uuid",
    pattern: "SUBJ-{PREFIX}-{UUID8}",
    label: (prefix) => `SUBJ-${prefix}-550E8400`,
  },
  {
    key: "uuid",
    mode: "uuid",
    pattern: "{UUID}",
    label: () => "Full UUID",
  },
  {
    key: "custom",
    mode: "custom",
    pattern: "",
    label: () => "Custom pattern",
  },
];

export function deepClone(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return value;
  }
}

export function normalizeSubjectPrefix(value) {
  const cleaned = String(value || "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 12);

  return cleaned || "ST";
}

export function deriveSubjectPrefixFromStudy(studyNode = {}, fallbackName = "Study") {
  const s = studyNode || {};

  const raw =
    s.short_name ||
    s.shortName ||
    s.title ||
    s.study_name ||
    s.name ||
    fallbackName ||
    "Study";

  const words = String(raw)
    .replace(/[^A-Za-z0-9\s]/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  const acronym = words.map((w) => w[0]).join("");

  return normalizeSubjectPrefix(acronym || raw || "ST");
}

export function createDefaultSubjectIdConfig(studyNode = {}, fallbackName = "Study") {
  const prefix = deriveSubjectPrefixFromStudy(studyNode, fallbackName);

  return {
    ...DEFAULT_SUBJECT_ID_CONFIG,
    prefix,
  };
}

export function normalizeSubjectIdPreset(value) {
  const key = String(value || "");

  return SUBJECT_ID_PRESET_DEFINITIONS.some((p) => p.key === key)
    ? key
    : DEFAULT_SUBJECT_ID_CONFIG.preset;
}

export function presetFromSubjectIdConfig(config) {
  const src = config && typeof config === "object" ? config : {};
  const preset = String(src.preset || "");
  const pattern = String(src.pattern || "").trim();

  if (preset === "custom") {
    return (
      SUBJECT_ID_PRESET_DEFINITIONS.find((p) => p.key === "custom") ||
      SUBJECT_ID_PRESET_DEFINITIONS[0]
    );
  }

  const byPattern = SUBJECT_ID_PRESET_DEFINITIONS.find(
    (p) => p.key !== "custom" && p.pattern === pattern
  );

  if (byPattern) return byPattern;

  const byKey = SUBJECT_ID_PRESET_DEFINITIONS.find(
    (p) => p.key === normalizeSubjectIdPreset(preset)
  );

  return byKey || SUBJECT_ID_PRESET_DEFINITIONS[0];
}

export function normalizeSubjectIdConfig(config, studyNode = {}, fallbackName = "Study") {
  const fallback = createDefaultSubjectIdConfig(studyNode, fallbackName);
  const src = config && typeof config === "object" ? config : {};
  const preset = presetFromSubjectIdConfig(src);

  const padding = Number(src.padding || fallback.padding || 3);
  const startNumber = Number(src.startNumber || fallback.startNumber || 1);
  const customPattern = String(src.pattern || "").trim();

  return {
    ...fallback,
    ...deepClone(src),
    preset: preset.key,
    mode: preset.mode,
    pattern:
      preset.key === "custom"
        ? customPattern || fallback.pattern
        : preset.pattern,
    prefix: normalizeSubjectPrefix(src.prefix || fallback.prefix),
    padding: Number.isFinite(padding) ? Math.min(Math.max(padding, 1), 8) : 3,
    startNumber: Number.isFinite(startNumber) ? Math.max(startNumber, 1) : 1,
    locked: !!src.locked,
  };
}

export function makeSubjectUuid() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function makeSubjectRandomToken(length = 6) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let out = "";

  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const arr = new Uint32Array(length);
    crypto.getRandomValues(arr);

    for (let i = 0; i < length; i += 1) {
      out += chars[arr[i] % chars.length];
    }

    return out;
  }

  for (let i = 0; i < length; i += 1) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }

  return out;
}

export function buildSubjectIdFromConfig(config, sequenceNumber, studyNode = {}, fallbackName = "Study") {
  const cfg = normalizeSubjectIdConfig(config, studyNode, fallbackName);
  const number = Number(sequenceNumber || cfg.startNumber || 1);
  const padded = String(number).padStart(cfg.padding, "0");
  const uuid = makeSubjectUuid();
  const uuidCompact = uuid.replaceAll("-", "").toUpperCase();

  let id = String(cfg.pattern || DEFAULT_SUBJECT_ID_CONFIG.pattern)
    .replaceAll("{PREFIX}", cfg.prefix)
    .replaceAll("{NUMBER}", padded)
    .replaceAll("{UUID}", uuid)
    .replaceAll("{UUID8}", uuidCompact.slice(0, 8))
    .replaceAll("{RAND6}", makeSubjectRandomToken(6))
    .replace(/\s+/g, "")
    .toUpperCase();

  if (!id) id = `SUBJ-${cfg.prefix}-${padded}`;

  return id;
}

export function buildUniqueSubjectId(
  config,
  sequenceNumber,
  existingIds = new Set(),
  studyNode = {},
  fallbackName = "Study"
) {
  let id = "";
  let attempts = 0;

  do {
    id = buildSubjectIdFromConfig(
      config,
      Number(sequenceNumber || 1) + attempts,
      studyNode,
      fallbackName
    );
    attempts += 1;
  } while (existingIds.has(id) && attempts < 50);

  return id;
}

export function buildPreviewSubjectId(config, sequenceNumber, previewIndex = 0) {
  const cfg = normalizeSubjectIdConfig(config);
  const padded = String(sequenceNumber || cfg.startNumber || 1).padStart(cfg.padding, "0");

  const fakeUuids = [
    "550e8400-e29b-41d4-a716-446655440000",
    "7b9f2c10-a3d4-4e8b-9f21-19c8b6a7d302",
    "c41a92de-6f73-48a1-b9d5-82f3e1a0c764",
  ];

  const fakeRandTokens = ["A8F3K2", "B7M9Q4", "C2L8X5"];

  const uuid = fakeUuids[previewIndex % fakeUuids.length];
  const uuidCompact = uuid.replaceAll("-", "").toUpperCase();

  let id = String(cfg.pattern || DEFAULT_SUBJECT_ID_CONFIG.pattern)
    .replaceAll("{PREFIX}", cfg.prefix)
    .replaceAll("{NUMBER}", padded)
    .replaceAll("{UUID}", uuid)
    .replaceAll("{UUID8}", uuidCompact.slice(0, 8))
    .replaceAll("{RAND6}", fakeRandTokens[previewIndex % fakeRandTokens.length])
    .replace(/\s+/g, "")
    .toUpperCase();

  if (!id) id = `SUBJ-${cfg.prefix}-${padded}`;

  return id;
}

export function inferSubjectIdConfigFromExistingSubjects(
  subjects,
  studyNode = {},
  fallbackName = "Study",
  options = {}
) {
  const list = Array.isArray(subjects) ? subjects : [];

  const ids = list
    .map((s) => String(s?.id || s?.subject_id || "").trim())
    .filter(Boolean);

  const useLast = options.useLast !== false;
  const selectedId = useLast ? ids[ids.length - 1] || "" : ids[0] || "";
  const fallbackStart = ids.length + 1;

  if (!selectedId) {
    return {
      ...createDefaultSubjectIdConfig(studyNode, fallbackName),
      startNumber: 1,
      locked: false,
    };
  }

  let match = selectedId.match(/^SUBJ-([A-Z0-9]+)-(\d+)$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "subj-prefix-number",
        prefix: match[1],
        pattern: "SUBJ-{PREFIX}-{NUMBER}",
        padding: match[2].length,
        startNumber: Number(match[2]) + 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  match = selectedId.match(/^STUDY-([A-Z0-9]+)-(\d+)$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "study-prefix-number",
        prefix: match[1],
        pattern: "STUDY-{PREFIX}-{NUMBER}",
        padding: match[2].length,
        startNumber: Number(match[2]) + 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  match = selectedId.match(/^([A-Z0-9]+)-(\d+)$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "prefix-number",
        prefix: match[1],
        pattern: "{PREFIX}-{NUMBER}",
        padding: match[2].length,
        startNumber: Number(match[2]) + 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  match = selectedId.match(/^S(\d+)$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "s-number",
        prefix: deriveSubjectPrefixFromStudy(studyNode, fallbackName),
        pattern: "S{NUMBER}",
        padding: match[1].length,
        startNumber: Number(match[1]) + 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  match = selectedId.match(/^P(\d+)$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "p-number",
        prefix: deriveSubjectPrefixFromStudy(studyNode, fallbackName),
        pattern: "P{NUMBER}",
        padding: match[1].length,
        startNumber: Number(match[1]) + 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  if (/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(selectedId)) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "uuid",
        prefix: deriveSubjectPrefixFromStudy(studyNode, fallbackName),
        pattern: "{UUID}",
        padding: 3,
        startNumber: 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  match = selectedId.match(/^SUBJ-([A-Z0-9]+)-([A-Z0-9]{8})$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "subj-prefix-uuid8",
        prefix: match[1],
        pattern: "SUBJ-{PREFIX}-{UUID8}",
        padding: 3,
        startNumber: 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  match = selectedId.match(/^SUBJ-([A-Z0-9]+)-([A-Z0-9]{6})$/i);
  if (match) {
    return normalizeSubjectIdConfig(
      {
        mode: "inferred",
        preset: "subj-prefix-rand6",
        prefix: match[1],
        pattern: "SUBJ-{PREFIX}-{RAND6}",
        padding: 3,
        startNumber: 1,
        locked: false,
      },
      studyNode,
      fallbackName
    );
  }

  return normalizeSubjectIdConfig(
    {
      mode: "inferred_custom",
      preset: "custom",
      prefix: deriveSubjectPrefixFromStudy(studyNode, fallbackName),
      pattern: "SUBJ-{PREFIX}-{NUMBER}",
      padding: 3,
      startNumber: fallbackStart,
      locked: false,
    },
    studyNode,
    fallbackName
  );
}

export function getNextSubjectSequenceNumber(subjects, config = null) {
  const cfg = normalizeSubjectIdConfig(config);

  const ids = (Array.isArray(subjects) ? subjects : [])
    .map((s) => String(s?.id || s?.subject_id || "").trim())
    .filter(Boolean);

  const numericValues = ids
    .map((id) => {
      const match = id.match(/(\d+)$/);
      return match ? Number(match[1]) : null;
    })
    .filter((n) => Number.isFinite(n));

  if (numericValues.length) {
    return Math.max(...numericValues) + 1;
  }

  return Number(cfg.startNumber || 1);
}

export function subjectIdPatternValidationMessage(config) {
  const cfg = normalizeSubjectIdConfig(config);
  const pattern = String(cfg.pattern || "");

  const hasAnyValidToken =
    pattern.includes("{NUMBER}") ||
    pattern.includes("{UUID}") ||
    pattern.includes("{UUID8}") ||
    pattern.includes("{RAND6}");

  if (!hasAnyValidToken) {
    return "Pattern must contain at least one of {NUMBER}, {UUID}, {UUID8}, or {RAND6}.";
  }

  if (pattern.includes("{PREFIX}") && !cfg.prefix) {
    return "Prefix is required when pattern contains {PREFIX}.";
  }

  return "";
}