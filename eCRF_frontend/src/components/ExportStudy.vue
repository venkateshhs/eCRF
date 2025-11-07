<template>
  <div class="export-container">
    <div class="export-card">
      <!-- Header row -->
      <div class="header-row">
        <button class="btn-minimal" type="button" @click="goBack">Back</button>
        <div class="title-wrap">
          <h1 class="page-title">Export Study</h1>
          <div class="study-subtitle" :title="studyName">{{ studyName || "—" }}</div>
        </div>
      </div>

      <!-- Error / Loading -->
      <div v-if="loading" class="status muted">Loading…</div>
      <div v-else-if="error" class="status err">{{ error }}</div>

      <!-- Selection panel -->
      <div v-else class="panel">
        <div class="grid-2">
          <!-- Subjects -->
          <div class="box">
            <div class="box-header">
              <h3 class="box-title">Subjects</h3>
              <div class="tools">
                <label class="chk">
                  <input type="checkbox" :checked="allSubjectsChecked" @change="toggleAllSubjects" />
                  <span>Select all</span>
                </label>
              </div>
            </div>

            <div class="list">
              <label
                v-for="(s, idx) in subjects"
                :key="sKey(s, idx)"
                class="row"
              >
                <input
                  type="checkbox"
                  :value="subjectId(s, idx)"
                  :checked="selectedSubjectIds.has(subjectId(s, idx))"
                  @change="toggleSubject(s, idx, $event.target.checked)"
                />
                <span class="lbl" :title="subjectId(s, idx)">
                  {{ subjectId(s, idx) }}
                  <span v-if="s.group" class="muted">&nbsp;—&nbsp;{{ s.group }}</span>
                </span>
              </label>
              <div v-if="subjects.length === 0" class="muted">No subjects defined.</div>
            </div>
          </div>

          <!-- Visits -->
          <div class="box">
            <div class="box-header">
              <h3 class="box-title">Visits</h3>
            </div>

            <div class="hint">
              Selecting subjects will auto-select the <em>visits assigned</em> to those subjects (by group & assignments).
            </div>

            <div class="list">
              <label v-for="(v, vidx) in visits" :key="vKey(v, vidx)" class="row">
                <input
                  type="checkbox"
                  :value="visitName(v, vidx)"
                  :checked="selectedVisitNames.has(visitName(v, vidx))"
                  @change="toggleVisit(visitName(v, vidx), $event.target.checked)"
                />
                <span class="lbl" :title="visitName(v, vidx)">{{ visitName(v, vidx) }}</span>
              </label>
              <div v-if="visits.length === 0" class="muted">No visits defined.</div>
            </div>
          </div>
        </div>

        <!-- Auto summary of included sections -->
        <div class="box">
          <div class="box-header">
            <h3 class="box-title">Included Sections (auto)</h3>
          </div>
          <div class="chip-list">
            <span v-for="(t, i) in includedSections" :key="t + i" class="chip" :title="t">{{ t }}</span>
            <span v-if="includedSections.length === 0" class="muted">No sections (select subjects & visits).</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="actions">
          <button type="button" class="btn-minimal" @click="clearSelection">Clear</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="selectedSubjectIds.size === 0 || selectedVisitNames.size === 0"
            @click="downloadExport"
            title="Download selected study template as JSON"
          >
            Download
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "ExportStudy",
  data() {
    return {
      loading: true,
      error: null,
      studyId: null,
      studyName: "",
      sd: {},                 // full study_data from backend
      subjects: [],           // [{id, group}, ...]
      visits: [],             // [{name, ...}, ...]
      groups: [],             // [{name}, ...]
      selectedModels: [],     // [{title, fields}, ...]
      assignments: [],        // [section][visit][group] -> boolean
      // selection
      selectedSubjectIds: new Set(),
      selectedVisitNames: new Set(),
    };
  },
  computed: {
    allSubjectsChecked() {
      return this.subjects.length > 0 && this.selectedSubjectIds.size === this.subjects.length;
    },
    includedSections() {
      // Sections (model titles) that are assigned to ANY selected (subject, visit) combo.
      const titles = new Set();
      const gIdxCache = new Map(); // subjectKey -> gIdx
      for (let sIdx = 0; sIdx < this.subjects.length; sIdx++) {
        const subjId = this.subjectId(this.subjects[sIdx], sIdx);
        if (!this.selectedSubjectIds.has(subjId)) continue;

        // Resolve group index for this subject once
        const cacheKey = subjId;
        let gIdx = gIdxCache.get(cacheKey);
        if (gIdx === undefined) {
          gIdx = this.resolveGroupIndexFromSubject(sIdx);
          gIdxCache.set(cacheKey, gIdx);
        }

        for (let vIdx = 0; vIdx < this.visits.length; vIdx++) {
          const vname = this.visitName(this.visits[vIdx], vIdx);
          if (!this.selectedVisitNames.has(vname)) continue;

          for (let mIdx = 0; mIdx < this.selectedModels.length; mIdx++) {
            if (this.isAssigned(mIdx, vIdx, gIdx)) {
              const title = this.modelTitle(this.selectedModels[mIdx]);
              if (title) titles.add(title);
            }
          }
        }
      }
      return Array.from(titles);
    },
  },
  methods: {
    goBack() {
      this.$router.back();
    },
    // --- Helpers for ids/titles/names ---
    subjectId(s, idx) {
      return String(s?.id || s?.subjectId || s?.label || idx + 1).trim();
    },
    visitName(v, idx) {
      return String(v?.name || v?.label || v?.code || v?.id || `Visit_${idx + 1}`).trim();
    },
    modelTitle(m) {
      return String(m?.title || m?.name || "").trim();
    },
    sKey(s, idx) { return this.subjectId(s, idx) + "_" + idx; },
    vKey(v, idx) { return this.visitName(v, idx) + "_" + idx; },

    // --- Assignments & group mapping ---
    resolveGroupIndexFromSubject(subjectIndex) {
      const subjects = this.subjects || [];
      const groups = this.groups || [];
      if (!(subjectIndex >= 0 && subjectIndex < subjects.length) || groups.length === 0) return null;
      const subjGroup = String(subjects[subjectIndex]?.group || "").trim().toLowerCase();
      if (!subjGroup) return null;
      for (let gi = 0; gi < groups.length; gi++) {
        const name = String(groups[gi]?.name || groups[gi]?.label || "").trim().toLowerCase();
        if (name && name === subjGroup) return gi;
      }
      return null;
    },
    isAssigned(mIdx, vIdx, gIdx) {
      const assigns = this.assignments;
      if (!Array.isArray(assigns) || assigns.length === 0) return true; // treat missing as "all assigned"
      try {
        if (gIdx == null) {
          // any group assigned
          const row = assigns[mIdx]?.[vIdx] || [];
          return Array.isArray(row) ? row.some(Boolean) : Boolean(row);
        }
        return Boolean(assigns[mIdx]?.[vIdx]?.[gIdx]);
      } catch {
        return false;
      }
    },

    // --- Subject/Visit selection logic ---
    toggleAllSubjects(e) {
      const checked = e?.target?.checked;
      this.selectedSubjectIds.clear();
      if (checked) {
        for (let i = 0; i < this.subjects.length; i++) {
          this.selectedSubjectIds.add(this.subjectId(this.subjects[i], i));
        }
      }
      this.recomputeVisitsAuto();
    },
    toggleSubject(s, idx, checked) {
      const id = this.subjectId(s, idx);
      if (checked) this.selectedSubjectIds.add(id);
      else this.selectedSubjectIds.delete(id);
      this.recomputeVisitsAuto();
    },
    toggleVisit(vname, checked) {
      // Allow manual override; auto-selection still recomputes on subject changes
      if (checked) this.selectedVisitNames.add(vname);
      else this.selectedVisitNames.delete(vname);
    },
    recomputeVisitsAuto() {
      // Union of visits that are assigned to any selected subject (by group & assignments).
      const next = new Set();
      if (this.selectedSubjectIds.size === 0) {
        this.selectedVisitNames = next;
        return;
      }
      for (let sIdx = 0; sIdx < this.subjects.length; sIdx++) {
        const subjId = this.subjectId(this.subjects[sIdx], sIdx);
        if (!this.selectedSubjectIds.has(subjId)) continue;

        const gIdx = this.resolveGroupIndexFromSubject(sIdx);

        for (let vIdx = 0; vIdx < this.visits.length; vIdx++) {
          if (this.isAssignedToAnySectionAtVisit(vIdx, gIdx)) {
            next.add(this.visitName(this.visits[vIdx], vIdx));
          }
        }
      }
      this.selectedVisitNames = next;
    },
    isAssignedToAnySectionAtVisit(vIdx, gIdx) {
      if (!Array.isArray(this.selectedModels) || this.selectedModels.length === 0) return true;
      for (let mIdx = 0; mIdx < this.selectedModels.length; mIdx++) {
        if (this.isAssigned(mIdx, vIdx, gIdx)) return true;
      }
      return false;
    },

    clearSelection() {
      this.selectedSubjectIds.clear();
      this.selectedVisitNames.clear();
    },

    // --- Data load ---
    async loadStudy() {
      this.loading = true;
      this.error = null;
      try {
        const id = Number(this.$route.params.id || 0);
        this.studyId = id || null;
        const token = this.$store.state.token;
        const resp = await axios.get(`/forms/studies/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const sd = resp.data?.content?.study_data || {};
        this.sd = sd;
        this.studyName = resp.data?.metadata?.study_name || sd?.study?.title || "";
        this.subjects = Array.isArray(sd.subjects) ? sd.subjects.map(x => ({ id: String(x.id || x.subjectId || x.label || "").trim(), group: String(x.group || "").trim() })) : [];
        this.visits = Array.isArray(sd.visits) ? sd.visits : [];
        this.groups = Array.isArray(sd.groups) ? sd.groups : [];
        this.selectedModels = Array.isArray(sd.selectedModels) ? sd.selectedModels : [];
        // Normalize assignments to m x v x g
        this.assignments = Array.isArray(sd.assignments) ? sd.assignments : [];
      } catch (e) {
        this.error = e?.response?.data?.detail || e?.message || "Failed to load study.";
      } finally {
        this.loading = false;
      }
    },

    // --- Export ---
    buildExportPayload() {
      // Filter subjects
      const selectedSubjects = this.subjects.filter((s, idx) =>
        this.selectedSubjectIds.has(this.subjectId(s, idx))
      );

      // Filter visits (preserve order)
      const selVisitNames = this.visits.map((v, idx) => this.visitName(v, idx))
        .filter(n => this.selectedVisitNames.has(n));
      const visitIndexKeep = new Set(selVisitNames.map(n => n.toLowerCase()));
      const filteredVisits = this.visits.filter((v, idx) =>
        visitIndexKeep.has(this.visitName(v, idx).toLowerCase())
      );

      // Filter assignments to selected visits (keep all groups; sections subset is auto-included, but we leave structure intact)
      let filteredAssignments = this.assignments;
      if (Array.isArray(this.assignments) && this.assignments.length > 0) {
        // Map kept visit indices
        const keepVIdx = [];
        for (let vIdx = 0; vIdx < this.visits.length; vIdx++) {
          const vname = this.visitName(this.visits[vIdx], vIdx).toLowerCase();
          if (visitIndexKeep.has(vname)) keepVIdx.push(vIdx);
        }
        // Slice per section
        filteredAssignments = this.assignments.map(secRow => {
          const out = [];
          keepVIdx.forEach(vIdx => {
            out.push(Array.isArray(secRow?.[vIdx]) ? [...secRow[vIdx]] : secRow?.[vIdx]);
          });
          return out;
        });
      }

      // Keep full selectedModels (forms) & constraints; importer can further restrict by subject/visit
      const payload = {
        meta: {
          exported_at: new Date().toISOString(),
          study_name: this.studyName || "",
          tool: "eCRF Export",
          version: 1,
        },
        study_data: {
          study: { ...(this.sd?.study || {}) },
          groups: this.groups,
          visits: filteredVisits,
          subjects: selectedSubjects,
          selectedModels: this.selectedModels,
          assignments: filteredAssignments,
          // keep helpful BIDS maps if present (downstream merge can reuse)
          bids: this.sd?.bids || {},
        },
      };
      return payload;
    },

    downloadExport() {
      try {
        const payload = this.buildExportPayload();
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
        const safeName = (this.studyName || "study").replace(/[^\w.-]+/g, "_");
        const fname = `${safeName}_export.json`;
        if (window.navigator.msSaveOrOpenBlob) {
          window.navigator.msSaveOrOpenBlob(blob, fname);
        } else {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = fname;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        }
      } catch (e) {
        alert("Failed to prepare export: " + (e?.message || e));
      }
    },
  },
  mounted() {
    this.loadStudy();
  },
};
</script>

<style scoped>
/* Page container */
.export-container {
  padding: 24px;
  display: grid;
  place-items: start center;
}

/* Single big card */
.export-card {
  width: min(1100px, 100%);
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* Header: back + title + study name */
.header-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}
.title-wrap {
  text-align: center;
}
.page-title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  color: #111827;
}
.study-subtitle {
  margin-top: 2px;
  font-size: 0.95rem;
  color: #374151;
  max-width: 80ch;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
}

/* Status */
.status { text-align: center; margin: 8px 0; }
.status.muted { color: #6b7280; }
.status.err { color: #dc2626; }

/* Panel content */
.panel { display: grid; gap: 14px; }

/* Two-column grid */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 16px;
}

/* Box */
.box {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
}
.box-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.box-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 500;
  color: #1f2937;
}

/* Lists */
.list { display: grid; gap: 8px; max-height: 52vh; overflow-y: auto; }
.row { display: flex; align-items: center; gap: 10px; }
.lbl { color: #111827; }

/* Small hint text */
.hint {
  color: #6b7280;
  font-size: 0.9rem;
  margin: 0 0 8px 0;
}

/* Checkboxes */
.chk { display: inline-flex; align-items: center; gap: 8px; user-select: none; }

/* Chips */
.chip-list { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 0.85rem;
  color: #374151;
}

/* Actions */
.actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 6px;
}

/* Buttons (consistent with other screens) */
.btn-minimal {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.btn-minimal:hover {
  background: #e8e8e8;
  color: #000;
  border-color: #d6d6d6;
}
.btn-primary {
  padding: 10px 16px;
  background: #4f46e5;
  color: #fff;
  border: 1px solid #4338ca;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.02s ease, box-shadow 0.2s ease;
}
.btn-primary:hover { background: #4338ca; box-shadow: 0 2px 10px rgba(79,70,229,0.25); }
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

/* Responsive */
@media (max-width: 900px) {
  .grid-2 { grid-template-columns: 1fr; }
  .title-wrap { text-align: left; }
}
</style>
