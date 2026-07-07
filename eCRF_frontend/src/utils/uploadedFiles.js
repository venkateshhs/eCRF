function baseName(path) {
  if (!path) return "";
  const parts = String(path).split(/[\\/]/);
  return parts[parts.length - 1] || "";
}

export function uploadedFileName(file) {
  if (!file) return "";
  if (typeof file === "string") return baseName(file);
  return (
    file.file_name ||
    file.name ||
    baseName(file.url) ||
    baseName(file.file_path) ||
    "Uploaded file"
  );
}

export function uploadedFileId(file) {
  if (!file || typeof file !== "object") return null;
  return file.dbId || file.id || file.file_id || null;
}

export function canDownloadUploadedFile(file) {
  if (!file) return false;
  if (typeof file === "object" && file.source === "url" && file.url) return true;
  if (typeof file === "object" && String(file.storage_option || "").toLowerCase() === "url" && file.file_path) return true;
  return !!uploadedFileId(file);
}

export function normalizeUploadedFiles(value) {
  const values = Array.isArray(value) ? value : value ? [value] : [];
  return values
    .filter((item) => item && typeof item === "object")
    .filter((item) => canDownloadUploadedFile(item) || uploadedFileName(item))
    .map((item) => ({
      ...item,
      displayName: uploadedFileName(item),
      downloadable: canDownloadUploadedFile(item),
    }));
}

function uniqueKeys(values) {
  return values
    .filter((value) => value !== null && typeof value !== "undefined" && String(value) !== "")
    .map((value) => String(value));
}

function normalizeKey(value) {
  return String(value || "").trim().toLowerCase();
}

function sectionKeys(section, index) {
  return uniqueKeys([
    section?._id,
    section?.id,
    section?.section_id,
    section?.uid,
    section?.key,
    section?.title,
    section?.name,
    index,
  ]);
}

function fieldKeys(field, index) {
  return uniqueKeys([
    field?._id,
    field?.id,
    field?.field_id,
    field?.uid,
    field?.key,
    field?.name,
    field?.label,
    field?.title,
    index,
  ]);
}

function readByCandidateKeys(object, candidates) {
  if (!object || typeof object !== "object") return undefined;

  for (const key of candidates) {
    if (Object.prototype.hasOwnProperty.call(object, key)) {
      return object[key];
    }
  }

  const normalizedCandidates = candidates.map(normalizeKey);
  const matchedKey = Object.keys(object).find((key) =>
    normalizedCandidates.includes(normalizeKey(key))
  );

  return matchedKey ? object[matchedKey] : undefined;
}

function valueFromData(data, section, sectionIndex, field, fieldIndex) {
  if (Array.isArray(data)) {
    return data?.[sectionIndex]?.[fieldIndex];
  }

  if (!data || typeof data !== "object") return undefined;

  const secObj = readByCandidateKeys(data, sectionKeys(section, sectionIndex));
  if (!secObj || typeof secObj !== "object") return undefined;

  return readByCandidateKeys(secObj, fieldKeys(field, fieldIndex));
}

export function collectUploadedFilesForSlot({ sections = [], data = [] } = {}) {
  const files = [];

  (sections || []).forEach((section, sectionIndex) => {
    (section?.fields || []).forEach((field, fieldIndex) => {
      if (String(field?.type || "").toLowerCase() !== "file") return;

      const value = valueFromData(data, section, sectionIndex, field, fieldIndex);
      normalizeUploadedFiles(value).forEach((file, fileIndex) => {
        files.push({
          ...file,
          fileIndex,
          sectionIndex,
          fieldIndex,
          sectionTitle: section?.title || section?.name || `Section ${sectionIndex + 1}`,
          fieldLabel: field?.label || field?.name || field?.title || `Field ${fieldIndex + 1}`,
        });
      });
    });
  });

  return files;
}

export function inferUploadedFileFieldContext(file, sections = []) {
  const labels = [
    file?.description,
    ...(Array.isArray(file?.modalities) ? file.modalities : []),
  ]
    .filter(Boolean)
    .map(normalizeKey);

  if (!labels.length) return null;

  for (let sectionIndex = 0; sectionIndex < (sections || []).length; sectionIndex++) {
    const section = sections[sectionIndex] || {};
    const fields = section.fields || [];

    for (let fieldIndex = 0; fieldIndex < fields.length; fieldIndex++) {
      const field = fields[fieldIndex] || {};
      if (String(field.type || "").toLowerCase() !== "file") continue;

      const fieldLabels = [
        field.label,
        field.name,
        field.title,
        ...(Array.isArray(field?.constraints?.modalities) ? field.constraints.modalities : []),
      ]
        .filter(Boolean)
        .map(normalizeKey);

      if (fieldLabels.some((label) => labels.includes(label))) {
        return {
          sectionIndex,
          fieldIndex,
          sectionTitle: section.title || section.name || `Section ${sectionIndex + 1}`,
          fieldLabel: field.label || field.name || field.title || `Field ${fieldIndex + 1}`,
        };
      }
    }
  }

  return null;
}
