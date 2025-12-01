<template>
  <div class="audit-shell">
    <!-- MAIN CONTENT AREA -->
    <main class="content">
      <!-- Toolbar -->
      <div class="content-head">
        <div class="left-cluster">
          <!-- Horizontal tabs -->
          <div class="tabs">
            <button
              class="tab"
              :class="{ active: activeTab === 'study' }"
              @click="activeTab = 'study'"
            >
              Study (System)
            </button>
            <button
              class="tab"
              :class="{ active: activeTab === 'subjects' }"
              @click="activateSubjectsTab()"
            >
              Subjects
            </button>
          </div>

          <!-- Subject selector when in Subjects tab -->
          <div
            v-if="activeTab === 'subjects'"
            class="subject-select-wrap"
          >
            <label class="subject-label">
              Subject
              <select
                v-model="activeSubject"
                class="subject-select"
              >
                <option
                  v-for="sid in subjectIds"
                  :key="`sel-${sid}`"
                  :value="sid"
                >
                  {{ displaySubject(sid) }} ({{ subjectCounts[String(sid)] || 0 }})
                </option>
              </select>
            </label>
          </div>
        </div>

        <div class="tools">
          <input
            class="input search"
            v-model="search"
            placeholder="Search action / user / details…"
            @input="debouncedFilter"
          />
          <button class="btn-minimal" @click="refreshAll" :disabled="loading">
            Refresh
          </button>
        </div>
      </div>

      <!-- Heading under toolbar -->
      <div class="title-wrap">
        <h2 class="panel-title" v-if="activeTab === 'study'">
          Study audit (system-level)
        </h2>
        <h2 class="panel-title" v-else>
          Subject audit
          <span
            v-if="activeSubject !== null && String(activeSubject) in subjectLabels"
          >
            — {{ displaySubject(activeSubject) }}
          </span>
          <span v-else-if="activeSubject !== null">
            — Subject {{ displaySubject(activeSubject) }}
          </span>
        </h2>
      </div>

      <!-- Loading / empty states -->
      <div v-if="loading" class="empty-state">Loading audit…</div>
      <div v-else-if="!visibleRows.length" class="empty-state">
        No audit entries.
      </div>

      <!-- Tables -->
      <div v-else class="table-wrap">
        <table class="audit-table" aria-label="Audit">
          <thead>
            <tr>
              <th class="col-ts">Timestamp</th>
              <th class="col-action">Action</th>
              <th class="col-user">User</th>
              <th class="col-details">Details</th>
              <th class="col-raw"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in visibleRows"
              :key="`row-${i}-${row.id || ''}`"
            >
              <td class="mono">{{ fmtTs(row.timestamp) }}</td>
              <td class="strong">{{ row.action || "—" }}</td>
              <td class="user-cell">
                <div>{{ userName(row.user_id) }}</div>
                <div
                  v-if="activeTab === 'subjects'"
                  class="meta"
                  title="Subject / Visit"
                >
                  Subj: {{ resolvedSubject(row) }} · Visit:
                  {{ resolvedVisit(row) }}
                </div>
              </td>
              <td class="wrap">
                <div class="detail-main">
                  {{ summaryText(row) }}
                </div>
                <div
                  v-if="row.details && Object.keys(row.details).length"
                  class="detail-lines"
                >
                  <div
                    v-for="(val, key) in row.details"
                    :key="`detail-${row.id || i}-${key}`"
                    class="detail-line"
                  >
                    <span class="detail-key">{{ key }}:</span>
                    <span class="detail-value">
                      {{ formatDetailValue(val) }}
                    </span>
                  </div>
                </div>
              </td>
              <td>
                <button class="link-btn" @click="toggleRaw(row)">
                  {{ row.__showRaw ? "hide" : "view raw" }}
                </button>
              </td>
            </tr>
            <tr
              v-for="(row, i) in visibleRows"
              :key="`raw-${i}-${row.id || ''}`"
              v-show="row.__showRaw"
            >
              <td :colspan="5" class="raw-wrap">
                <pre class="mini-json">{{ safeDetail(row.details) }}</pre>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyAuditLogs",
  props: {
    studyId: { type: [String, Number], required: true },
  },
  data() {
    return {
      loading: false,
      all: [], // all events (for this study) from API
      search: "",
      activeTab: "study", // 'study' | 'subjects'
      activeSubject: null, // subject id string/number or null
      subjectIds: [], // list of subject indexes as strings
      subjectCounts: {}, // sid -> count (by index)
      subjectLabels: {}, // sid (index) -> human subject id/label
      visitLabels: {}, // visit index -> human visit label
      nameCache: {}, // user id -> display name
      timerId: null,
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
    authHeaders() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {};
    },
    // rows filtered by current tab & selection
    visibleRows() {
      const base =
        this.activeTab === "study" ? this.studyRows() : this.subjectRows();
      return this.applySearch(base, this.search);
    },
  },
  methods: {
    // ====== fetch ======
    async refreshAll() {
      if (!this.token) return;
      this.loading = true;
      try {
        const { data } = await axios.get(
          `/audit/studies/${this.studyId}/events`,
          {
            headers: this.authHeaders,
          }
        );
        const rows = Array.isArray(data) ? data : data?.items || [];
        this.all = rows.map(this.normalizeRow);

        // Resolve user names (best-effort)
        this.primeUsers(this.all.map((r) => r.user_id).filter(Boolean));

        // Build subject list, counts, and labels from resolved subject ids
        const counts = {};
        const labels = {};
        const visitLabels = {};
        const set = new Set();

        for (const r of this.all) {
          const sid = this.getSubjectIdFromRow(r);
          if (sid === 0 || sid) {
            const key = String(sid);
            set.add(key);
            counts[key] = (counts[key] || 0) + 1;

            const label = this.extractSubjectLabel(r, sid);
            if (label && !labels[key]) {
              labels[key] = label;
            }
          }

          const vi = this.getVisitIndexFromRow(r);
          if (vi === 0 || vi) {
            const vKey = String(vi);
            const vLabel = this.extractVisitLabel(r, vi);
            if (vLabel && !visitLabels[vKey]) {
              visitLabels[vKey] = vLabel;
            }
          }
        }

        this.subjectIds = Array.from(set).sort(
          (a, b) => Number(a) - Number(b)
        );
        this.subjectCounts = counts;
        this.subjectLabels = labels;
        this.visitLabels = visitLabels;

        // If subjects tab is active but activeSubject is not set, pick the first
        if (
          this.activeTab === "subjects" &&
          this.subjectIds.length &&
          this.activeSubject === null
        ) {
          this.activeSubject = this.subjectIds[0];
        }
      } catch (e) {
        console.warn("Audit fetch failed:", e?.response?.data || e.message);
        this.all = [];
        this.subjectIds = [];
        this.subjectCounts = {};
        this.subjectLabels = {};
        this.visitLabels = {};
      } finally {
        this.loading = false;
      }
    },

    // ====== tabs / subject selection ======
    activateSubjectsTab() {
      this.activeTab = "subjects";
      if (this.subjectIds.length && this.activeSubject === null) {
        this.activeSubject = this.subjectIds[0];
      }
    },
    selectSubject(sid) {
      this.activeSubject = sid;
    },

    // ====== partition helpers ======
    studyRows() {
      // study/system-level = those without a resolvable subject id
      return this.all.filter((r) => {
        const sid = this.getSubjectIdFromRow(r);
        return !(sid === 0 || sid);
      });
    },
    subjectRows() {
      // subject-level = those with a resolvable subject id (and matches activeSubject)
      const withSubject = this.all.filter((r) => {
        const sid = this.getSubjectIdFromRow(r);
        return sid === 0 || sid;
      });
      if (this.activeSubject === null) return withSubject;
      return withSubject.filter(
        (r) =>
          String(this.getSubjectIdFromRow(r)) === String(this.activeSubject)
      );
    },

    // ====== normalizers / resolvers ======
    normalizeRow(r) {
      // API guarantees this endpoint is already scoped by studyId; we still normalize fields we use.
      const userId = r.user?.id ?? r.user_id ?? null;
      return {
        id: r.id,
        study_id: r.study_id != null ? Number(r.study_id) : null,
        subject_id: r.subject_id != null ? Number(r.subject_id) : null,
        user_id: userId != null ? Number(userId) : null,
        action: r.action || "",
        details: r.details || {},
        timestamp: r.timestamp || r.ts || null,
        __showRaw: false,
      };
    },
    getSubjectIdFromRow(row) {
      // prefer explicit subject_id (index)
      if (row.subject_id === 0 || row.subject_id) return row.subject_id;
      // fallback: details.subject_index
      const idx = row?.details?.subject_index;
      if (idx === 0 || idx) return Number(idx);
      // do NOT infer from participant_id anymore
      return null;
    },
    getVisitIndexFromRow(row) {
      const vi = row?.details?.visit_index;
      if (vi === 0 || vi) return Number(vi);
      const vid = row?.details?.visit_id;
      if (vid === 0 || vid) return Number(vid);
      return null;
    },
    extractSubjectLabel(row, sid) {
      const d = row.details || {};
      // Always prefer subject id / subject-specific labels; do not use participant_id
      const fromDetails =
        d.subject_id || d.subject_label || d.subject_code || null;
      if (fromDetails) return fromDetails;

      // Fallback: look up in global studyDetails.subjects using subject index (sid)
      const sd = (this.$store && this.$store.state && this.$store.state.studyDetails) || {};
      const subjects = Array.isArray(sd.subjects) ? sd.subjects : [];
      const subjectEntry = subjects[sid];
      if (subjectEntry) {
        return (
          subjectEntry.subject_id ||
          subjectEntry.id ||
          subjectEntry.code ||
          subjectEntry.label ||
          subjectEntry.name ||
          null
        );
      }

      return sid === 0 || sid ? `Subject ${sid}` : null;
    },
    extractVisitLabel(row, vi) {
      const d = row.details || {};
      return (
        d.visit_label ||
        d.visit_name ||
        d.visit_code ||
        (vi === 0 || vi ? `Visit ${vi}` : null)
      );
    },
    resolvedSubject(row) {
      const sid = this.getSubjectIdFromRow(row);
      if (!(sid === 0 || sid)) return "—";
      const key = String(sid);
      if (this.subjectLabels[key]) return this.subjectLabels[key];
      const rowLabel = this.extractSubjectLabel(row, sid);
      return rowLabel || String(sid);
    },
    resolvedVisit(row) {
      const vi = this.getVisitIndexFromRow(row);
      if (!(vi === 0 || vi)) return "—";
      const key = String(vi);
      if (this.visitLabels[key]) return this.visitLabels[key];
      const rowLabel = this.extractVisitLabel(row, vi);
      return rowLabel || String(vi);
    },
    fmtTs(ts) {
      // Do NOT convert; just show raw value from backend
      if (!ts) return "—";
      return String(ts);
    },
    displaySubject(sid) {
      const key = String(sid);
      return this.subjectLabels[key] || String(sid);
    },

    // ====== compact summary (only key fields) ======
    summaryText(row) {
      const a = (row.action || "").toLowerCase();
      const d = row.details || {};

      // Keep aligned with the *trimmed backend* actions
      if (a === "study_created") return `Study created`;
      if (a === "study_edited") return `Study edited`;

      if (a === "file_added" || a === "share_file_added") {
        const name = d.file_name || "file";
        const mods =
          Array.isArray(d.modalities) && d.modalities.length
            ? ` · ${d.modalities.join(", ")}`
            : "";
        const vi = this.resolvedVisit(row);
        const part = a === "share_file_added" ? "via share link" : "added";
        const subj = this.resolvedSubject(row);
        const loc =
          subj !== "—" || vi !== "—" ? ` (subj ${subj}, visit ${vi})` : "";
        return `File ${part}: ${name}${mods}${loc}`;
      }

      if (a === "entry_upserted") {
        const subj = this.resolvedSubject(row);
        const vi = this.resolvedVisit(row);
        return `Data saved/edited (subj ${subj}, visit ${vi})`;
      }
      if (a === "share_entry_upserted") {
        const subj = this.resolvedSubject(row);
        const vi = this.resolvedVisit(row);
        return `Data submitted via share link (subj ${subj}, visit ${vi})`;
      }

      if (a === "share_link_created") {
        const p = d.permission || "?";
        const exp =
          d.expires_in_days === 0 || d.expires_in_days
            ? `${d.expires_in_days}d`
            : "—";
        return `Share link created (permission ${p}, expires ${exp})`;
      }

      if (a === "access_granted")
        return `Access granted to ${
          d.target_user_display ||
          d.target_user_email ||
          `User#${d.target_user_id}`
        }`;
      if (a === "access_updated")
        return `Access updated for ${
          d.target_user_display ||
          d.target_user_email ||
          `User#${d.target_user_id}`
        }`;
      if (a === "access_revoked")
        return `Access revoked for ${
          d.target_user_display ||
          d.target_user_email ||
          `User#${d.target_user_id}`
        }`;

      // Fallback: tiny slice of details
      const keys = Object.keys(d || {});
      if (!keys.length) return "—";
      const parts = [];
      for (const k of keys.slice(0, 3)) {
        const val = d[k];
        if (["string", "number", "boolean"].includes(typeof val)) {
          parts.push(`${k}: ${String(val)}`);
        }
      }
      return parts.join(" · ");
    },

    formatDetailValue(val) {
      if (val === null || val === undefined) return "—";
      if (
        typeof val === "string" ||
        typeof val === "number" ||
        typeof val === "boolean"
      ) {
        return String(val);
      }
      try {
        const s = JSON.stringify(val);
        return s.length > 120 ? s.slice(0, 117) + "…" : s;
      } catch {
        return String(val);
      }
    },

    // ====== raw toggle & utils ======
    toggleRaw(row) {
      row.__showRaw = !row.__showRaw;
      this.$forceUpdate?.();
    },
    safeDetail(obj) {
      try {
        const s = JSON.stringify(obj || {}, null, 2);
        return s.length > 2000 ? s.slice(0, 1997) + "…" : s;
      } catch {
        return "{}";
      }
    },

    // ====== search ======
    debouncedFilter() {
      clearTimeout(this.timerId);
      this.timerId = setTimeout(() => this.$forceUpdate(), 150);
    },
    applySearch(rows, qRaw) {
      const q = (qRaw || "").toLowerCase();
      if (!q) return rows;
      return rows.filter((r) => {
        const parts = [
          this.fmtTs(r.timestamp),
          r.action || "",
          this.userName(r.user_id),
          this.summaryText(r),
          this.resolvedSubject(r),
          this.resolvedVisit(r),
        ].map((s) => (s || "").toString().toLowerCase());
        return parts.some((s) => s.includes(q));
      });
    },

    // ====== user names ======
    userName(userId) {
      if (!userId) return "—";
      const cached = this.nameCache[userId];
      return cached ? cached : `User#${userId}`;
    },
    async primeUsers(userIds) {
      const unique = Array.from(new Set(userIds)).filter(Boolean);
      const missing = unique.filter((id) => !this.nameCache[id]);
      for (const id of missing.slice(0, 25)) {
        try {
          const { data } = await axios.get(`/users/${id}`, {
            headers: this.authHeaders,
          });
          const u = data || {};
          const firstLast = [u?.profile?.first_name, u?.profile?.last_name]
            .filter(Boolean)
            .join(" ")
            .trim();
          const label =
            u.name ||
            u.full_name ||
            firstLast ||
            u.username ||
            u.email ||
            `User#${id}`;
          if (this.$set) this.$set(this.nameCache, id, label);
          else this.nameCache[id] = label;
        } catch {
          if (this.$set) this.$set(this.nameCache, id, `User#${id}`);
          else this.nameCache[id] = `User#${id}`;
        }
      }
    },
  },
  async mounted() {
    await this.refreshAll();
  },
};
</script>

<style scoped>
/* Layout */
.audit-shell {
  display: flex;
  flex-direction: column;
  min-height: 420px;
}

.content {
  background: #fff;
  border: 1px solid #f1f1f1;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

/* Header / toolbar */
.content-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.left-cluster {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* Tabs */
.tabs {
  display: inline-flex;
  background: #eef2ff;
  border-radius: 999px;
  padding: 2px;
}

.tab {
  border: none;
  background: transparent;
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 999px;
  cursor: pointer;
  color: #4b5563;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.tab.active {
  background: #dbeafe; /* lighter blue background */
  color: #1d4ed8;
  box-shadow: 0 1px 4px rgba(147, 197, 253, 0.8);
}

/* Subject dropdown */
.subject-select-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.subject-label {
  font-size: 13px;
  color: #374151;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.subject-select {
  height: 32px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  font-size: 13px;
  background: #fff;
}

/* Title below toolbar */
.title-wrap {
  margin-bottom: 6px;
}

.panel-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

/* Tools */
.tools {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input {
  height: 34px;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
}

.search {
  width: 260px;
}

.btn-minimal {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}
.btn-minimal:hover {
  background: #e8e8e8;
  color: #000;
  border-color: #d6d6d6;
}

/* Table */
.table-wrap {
  overflow: auto;
  border: 1px solid #f5f5f5;
  border-radius: 10px;
  margin-top: 4px;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.audit-table thead th,
.audit-table tbody td {
  padding: 8px 10px;
  border-bottom: 1px solid #f6f6f6;
  text-align: left;
  vertical-align: top;
}

.audit-table thead th {
  background: #f9fafb;
  color: #374151;
  font-weight: 600;
}

/* Column sizing */
.col-ts {
  width: 180px;
}
.col-action {
  width: 140px;
}
.col-user {
  width: 200px;
}
.col-details {
  width: auto;
}
.col-raw {
  width: 80px;
  text-align: right;
}

.audit-table tr:last-child td {
  border-bottom: none;
}

/* Cells */
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.strong {
  font-weight: 600;
}
.wrap {
  white-space: normal;
  word-break: break-word;
}
.user-cell .meta {
  color: #6b7280;
  font-size: 12px;
  margin-top: 2px;
}

/* Details formatting */
.detail-main {
  margin-bottom: 4px;
  font-weight: 500;
  color: #111827;
}

.detail-lines {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #4b5563;
}

.detail-line {
  display: flex;
  flex-wrap: wrap;
}

.detail-key {
  font-weight: 600;
  margin-right: 4px;
}

.detail-value {
  white-space: pre-wrap;
  word-break: break-word;
}

.raw-wrap {
  background: #fafafa;
  border-top: 1px dashed #eee;
}

.link-btn {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
  font-size: 12px;
}
.link-btn:hover {
  text-decoration: underline;
}

/* States */
.empty-state {
  color: #6b7280;
  padding: 8px 0;
}

/* Misc */
.mini-json {
  font-size: 11px;
  margin: 0;
}

/* Responsive */
@media (max-width: 720px) {
  .search {
    width: 180px;
  }
  .col-user {
    width: 160px;
  }
}
</style>
