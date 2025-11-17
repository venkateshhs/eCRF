// src/utils/studyDownload.js
import axios from "axios";
import JSZip from "jszip";
import { saveAs } from "file-saver";

/**
 * Small helpers copied / aligned with StudyDataDashboard logic
 */
function normalizeKey(k) {
  return String(k || "").trim().toLowerCase();
}

function sectionDictKey(sectionObj) {
  return sectionObj?.title ?? "";
}

function fieldDictKey(fieldObj, fallbackIndex) {
  return (
    fieldObj?.name ||
    fieldObj?.key ||
    fieldObj?.id ||
    fieldObj?.label ||
    fieldObj?.title ||
    `f${fallbackIndex}`
  );
}

function listKeys(obj) {
  return Object.keys(obj || {});
}

function dictRead(sections, dataDict, sIdx, fIdx, dbg) {
  if (!dataDict || typeof dataDict !== "object" || Array.isArray(dataDict)) {
    return undefined;
  }

  const sec = sections[sIdx];
  const fld = sec?.fields?.[fIdx];

  const sKey = sectionDictKey(sec);
  const fKey = fieldDictKey(fld, fIdx);

  let secObj = dataDict[sKey];

  // Fallback section key (case/trim-insensitive)
  if (!secObj) {
    const wanted = normalizeKey(sKey);
    const hitKey = Object.keys(dataDict).find(
      (k) => normalizeKey(k) === wanted
    );
    if (hitKey) {
      secObj = dataDict[hitKey];
      if (dbg) {
        dbg("Section key fallback used:", {
          expected: sKey,
          matched: hitKey,
        });
      }
    }
  }

  if (!secObj || typeof secObj !== "object") {
    if (dbg) {
      dbg("dictRead: section not found", {
        sIdx,
        sKey,
        available: listKeys(dataDict),
      });
    }
    return undefined;
  }

  if (Object.prototype.hasOwnProperty.call(secObj, fKey)) {
    return secObj[fKey];
  }

  // Fallback field key (case/trim-insensitive)
  const wantedField = normalizeKey(fKey);
  const hitField = Object.keys(secObj).find(
    (k) => normalizeKey(k) === wantedField
  );
  if (hitField) {
    if (dbg) {
      dbg("Field key fallback used:", {
        sKey,
        expectedField: fKey,
        matchedField: hitField,
      });
    }
    return secObj[hitField];
  }

  if (dbg) {
    dbg("dictRead: field not found", {
      sIdx,
      fIdx,
      sKey,
      fKey,
      availableFields: listKeys(secObj),
    });
  }
  return undefined;
}

function resolveGroup(studyData, subjIdx, dbg) {
  const subjects = studyData.subjects || [];
  const groups = studyData.groups || [];
  const subjGroup = (subjects[subjIdx]?.group || "").trim().toLowerCase();
  const idx = groups.findIndex(
    (g) => (g.name || "").trim().toLowerCase() === subjGroup
  );
  if (idx < 0 && dbg) {
    dbg("resolveGroup: subject group not found, defaulting to 0", {
      subjectIndex: subjIdx,
      subjectGroup: subjGroup,
      availableGroups: groups.map((g) => g.name),
    });
  }
  return idx >= 0 ? idx : 0;
}

function isAssigned(studyData, sectionIdx, visitIdx, groupIdx, dbg) {
  const ok = !!studyData.assignments?.[sectionIdx]?.[visitIdx]?.[groupIdx];
  if (!ok && sectionIdx === 0 && visitIdx === 0 && groupIdx === 0 && dbg) {
    dbg("isAssigned=false example", { sectionIdx, visitIdx, groupIdx });
  }
  return ok;
}

function findBestEntry(entries, subjIdx, visitIdx, groupIdx, selectedVersion) {
  const all = (entries || []).filter(
    (e) =>
      e.subject_index === subjIdx &&
      e.visit_index === visitIdx &&
      e.group_index === groupIdx
  );
  if (!all.length) return null;

  const target = Number(selectedVersion);

  // Prefer exact match
  const exact = all.find((e) => Number(e.form_version) === target);
  if (exact) return exact;

  // Else highest version <= target
  const le = all
    .filter((e) => Number(e.form_version) <= target)
    .sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
  if (le) return le;

  // Fallback: highest version available
  return all.sort(
    (a, b) => Number(b.form_version) - Number(a.form_version)
  )[0];
}

function formatFileCell(val) {
  const baseName = (p) => {
    if (!p) return "";
    const s = String(p);
    const parts = s.split(/[\\/]/);
    return parts[parts.length - 1];
  };
  const fromObj = (o) =>
    o.file_name || o.name || baseName(o.url) || baseName(o.file_path) || "";

  if (Array.isArray(val)) {
    const names = val
      .map((v) => {
        if (v && typeof v === "object") return fromObj(v);
        if (typeof v === "string") return baseName(v);
        return "";
      })
      .filter(Boolean);
    return names.join(", ");
  }
  if (val && typeof val === "object") {
    return fromObj(val);
  }
  if (typeof val === "string") {
    return baseName(val);
  }
  return "";
}

/**
 * Build flat rows (same layout as StudyDataDashboard CSV export) for a given
 * studyData + entries + template schema.
 */
function buildRowsForLatestVersion(studyData, entries, selectedVersion, dbg) {
  const subjects = studyData.subjects || [];
  const visits = studyData.visits || [];
  const sections = studyData.selectedModels || [];
  const fieldsPerSection = sections.map((sec) => sec.fields?.length || 0);

  const rows = [];

  subjects.forEach((subject, subjIdx) => {
    const groupIdx = resolveGroup(studyData, subjIdx, dbg);
    visits.forEach((visit, vIdx) => {
      const row = {
        subjectId: subject.id,
        visit: visit.name,
      };

      sections.forEach((section, sIdx) => {
        const assigned = isAssigned(studyData, sIdx, vIdx, groupIdx, dbg);
        const fields = section.fields || [];

        fields.forEach((field, fIdx) => {
          let value = "";
          if (assigned) {
            const entry = findBestEntry(
              entries,
              subjIdx,
              vIdx,
              groupIdx,
              selectedVersion
            );
            if (entry && entry.data) {
              const d = entry.data;
              let raw;
              if (!Array.isArray(d)) {
                raw = dictRead(sections, d, sIdx, fIdx, dbg);
                if (raw == null) raw = "";
              } else {
                const secArr = d[sIdx] || [];
                raw =
                  secArr[fIdx] !== undefined && secArr[fIdx] !== null
                    ? secArr[fIdx]
                    : "";
              }

              const type = (field.type || "").toLowerCase();
              if (type === "checkbox") {
                value = raw === true ? "Yes" : raw === false ? "No" : "";
              } else if (type === "file") {
                value = formatFileCell(raw);
              } else {
                value = raw == null || raw === "" ? "" : raw;
              }
            }
          }
          row[`s${sIdx}_f${fIdx}`] = value;
        });
      });

      rows.push(row);
    });
  });

  return { rows, sections, fieldsPerSection };
}

function sanitizeName(name, fallback) {
  const base = (name || fallback || "study")
    .toString()
    .trim()
    .replace(/[^\w-]+/g, "_");
  return base || "study";
}

function buildCsvFromRows(rows, sections, fieldsPerSection) {
  const quote = (v) => `"${String(v).replace(/"/g, '""')}"`;

  const hdr1 = [
    "Subject ID",
    "Visit",
    ...sections.flatMap((s, i) =>
      Array(fieldsPerSection[i]).fill(s.title || s.name || `Section ${i + 1}`)
    ),
  ];
  const hdr2 = [
    "",
    "",
    ...sections.flatMap((sec) =>
      (sec.fields || []).map(
        (f, idx) => f.label || f.name || f.title || `Field ${idx + 1}`
      )
    ),
  ];

  const lines = [];
  lines.push(hdr1.map(quote).join(","));
  lines.push(hdr2.map(quote).join(","));

  rows.forEach((row) => {
    const cells = [row.subjectId, row.visit];
    sections.forEach((section, sIdx) => {
      const fields = section.fields || [];
      fields.forEach((_, fIdx) => {
        cells.push(row[`s${sIdx}_f${fIdx}`]);
      });
    });
    lines.push(cells.map(quote).join(","));
  });

  return lines.join("\r\n");
}

/**
 * Public API: downloadStudyBundle
 * - Fetches latest template + data entries for latest version
 * - Builds a ZIP containing:
 *    /<study-name>/
 *       template_vX.json
 *       data_vX.csv
 */
export async function downloadStudyBundle({ studyId, token }) {
  if (!studyId || !token) {
    throw new Error("studyId and token are required for downloadStudyBundle");
  }

  const headers = { Authorization: `Bearer ${token}` };

  // 1. Load study (for name + fallback data)
  const studyResp = await axios.get(`/forms/studies/${studyId}`, { headers });
  const study = studyResp.data || {};
  const metadata = study.metadata || {};
  const currentData = study.content?.study_data || {};

  // 2. Load versions to determine latest
  let latestVersion = 1;
  try {
    const verResp = await axios.get(`/forms/studies/${studyId}/versions`, {
      headers,
    });
    const arr = Array.isArray(verResp.data) ? verResp.data : [];
    if (arr.length) {
      arr.sort((a, b) => a.version - b.version);
      latestVersion = arr[arr.length - 1].version;
    }
  } catch (e) {
    // Fallback: keep latestVersion = 1
  }

  // 3. Load template for latestVersion
  let schema = {};
  try {
    const tmplResp = await axios.get(`/forms/studies/${studyId}/template`, {
      headers,
      params: { version: latestVersion },
    });
    schema = tmplResp?.data?.schema || {};
  } catch (e) {
    schema = {};
  }

  // 4. Normalize studyData similarly to StudyDataDashboard.applyTemplateSchema
  const studyData = {
    study: schema.study ?? currentData.study ?? {},
    subjects:
      Array.isArray(schema.subjects) && schema.subjects.length
        ? schema.subjects
        : currentData.subjects || [],
    subjectCount: Number.isFinite(schema.subjectCount)
      ? schema.subjectCount
      : currentData.subjectCount ??
        (currentData.subjects?.length || 0),
    visits:
      Array.isArray(schema.visits) && schema.visits.length
        ? schema.visits
        : currentData.visits || [],
    groups:
      Array.isArray(schema.groups) && schema.groups.length
        ? schema.groups
        : currentData.groups || [],
    selectedModels: Array.isArray(schema.selectedModels)
      ? schema.selectedModels
      : currentData.selectedModels || [],
    assignments: Array.isArray(schema.assignments)
      ? schema.assignments
      : currentData.assignments || [],
  };

  // 5. Load all data entries for latestVersion
  let entries = [];
  try {
    const params = new URLSearchParams();
    params.append("all", "true");
    params.append("version", String(latestVersion));

    const url = `/forms/studies/${studyId}/data_entries?${params.toString()}`;
    const entriesResp = await axios.get(url, { headers });
    const payload = Array.isArray(entriesResp.data)
      ? { entries: entriesResp.data }
      : entriesResp.data || {};
    entries = payload.entries || [];
  } catch (e) {
    entries = [];
  }

  // 6. Build rows + CSV (same structure as StudyDataDashboard.exportCSV)
  const dbg = () => {
    // Optional: uncomment for debug logging
    // console.log("[StudyDownload]", ...arguments);
  };

  const { rows, sections, fieldsPerSection } = buildRowsForLatestVersion(
    studyData,
    entries,
    latestVersion,
    dbg
  );

  const csvContent = buildCsvFromRows(rows, sections, fieldsPerSection);

  // 7. Build template JSON (use raw schema from /template)
  const templateJson = JSON.stringify(schema || {}, null, 2);

  // 8. Build ZIP folder
  const studyNameSafe = sanitizeName(
    metadata.study_name,
    `study_${studyId}`
  );
  const zip = new JSZip();
  const folder = zip.folder(studyNameSafe);

  folder.file(`template_v${latestVersion}.json`, templateJson);
  folder.file(`data_v${latestVersion}.csv`, csvContent);

  const blob = await zip.generateAsync({ type: "blob" });
  const zipName = `${studyNameSafe}_v${latestVersion}_bundle.zip`;
  saveAs(blob, zipName);
}
