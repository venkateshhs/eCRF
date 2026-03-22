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
              Study
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
          <div v-if="activeTab === 'subjects'" class="subject-select-wrap">
            <label class="subject-label">
              Subject
              <select v-model="activeSubject" class="subject-select">
                <option v-for="sid in subjectIds" :key="`sel-${sid}`" :value="sid">
                  {{ displaySubject(sid) }} ({{ subjectCounts[String(sid)] || 0 }})
                </option>
              </select>
            </label>
          </div>
        </div>

        <div class="tools">
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
          <span v-if="activeSubject !== null && String(activeSubject) in subjectLabels">
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
            <!-- ✅ IMPORTANT:
                 When using <template v-for>, the ONLY key is on the <template>.
                 Do NOT put :key on child <tr> nodes (VueCompilerError). -->
            <template v-for="(row, i) in visibleRows" :key="`blk-${row.id || 'noid'}-${i}`">
              <tr>
                <td class="mono">{{ fmtTs(row.timestamp) }}</td>
                <td class="strong">{{ displayAction(row) }}</td>

                <td class="user-cell">
                  <div>{{ getUserDisplayName(row.user_id) }}</div>
                  <div
                    v-if="activeTab === 'subjects'"
                    class="meta"
                    title="Subject / Visit"
                  >
                    Subj: {{ resolvedSubject(row) }} · Visit: {{ resolvedVisit(row) }}
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
                      <span class="detail-value">{{ formatDetailValue(val) }}</span>
                    </div>
                  </div>
                </td>

                <td class="actions-cell">
                  <button
                    v-if="hasDiff(row)"
                    class="link-btn"
                    @click="openDiff(row)"
                    :disabled="diffLoading && diffEventId === row.id"
                    title="Show diff"
                  >
                    {{ diffLoading && diffEventId === row.id ? "loading…" : "diff" }}
                  </button>

                  <button class="link-btn" @click="toggleRaw(row)">
                    {{ row.__showRaw ? "hide" : "view raw" }}
                  </button>
                </td>
              </tr>

              <!-- ✅ no :key here (key is on <template>) -->
              <tr v-show="row.__showRaw">
                <td :colspan="5" class="raw-wrap">
                  <pre class="mini-json">{{ safeDetail(row.details) }}</pre>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Diff modal -->
      <div v-if="diffOpen" class="modal-backdrop" @click.self="closeDiff">
        <div class="modal">
          <div class="modal-head">
            <div class="modal-title">
              Diff
              <span v-if="diffPath" class="diff-path">— {{ diffPath }}</span>
            </div>
            <button class="btn-close" @click="closeDiff">✕</button>
          </div>

          <div class="modal-body">
            <div v-if="diffError" class="diff-error">
              {{ diffError }}
            </div>

            <!-- Render diff as a table when it's an array -->
            <div v-else-if="Array.isArray(diffData) && diffData.length" class="diff-table-wrap">
              <table class="diff-table" aria-label="Diff table">
                <thead>
                  <tr>
                    <th class="d-op">Op</th>
                    <th class="d-path">Path</th>
                    <th class="d-old">Old</th>
                    <th class="d-new">New</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(d, idx) in diffData" :key="`d-${idx}`">
                    <td class="d-op mono">{{ d?.op || "—" }}</td>
                    <td class="d-path mono">{{ d?.path || "—" }}</td>
                    <td class="d-old">
                      <pre class="cell-pre">{{ prettyOne(d?.old) }}</pre>
                    </td>
                    <td class="d-new">
                      <pre class="cell-pre">{{ prettyOne(d?.new) }}</pre>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- fallback -->
            <pre v-else class="diff-json">{{ pretty(diffData) }}</pre>
          </div>

          <div class="modal-foot">
            <button class="btn-minimal" @click="closeDiff">Close</button>
          </div>
        </div>
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
      all: [],

      activeTab: "study",
      activeSubject: null,

      subjectIds: [],
      subjectCounts: {},
      subjectLabels: {},
      visitLabels: {},

      nameCache: {},
      timerId: null,

      // diff modal state
      diffOpen: false,
      diffLoading: false,
      diffEventId: null,
      diffData: null,
      diffError: "",
      diffPath: "",
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
    authHeaders() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {};
    },
    visibleRows() {
      return this.activeTab === "study" ? this.studyRows() : this.subjectRows();
    },
  },
  methods: {
    // ====== fetch ======
    async refreshAll() {
      if (!this.token) return;
      this.loading = true;
      try {
        const { data } = await axios.get(`/audit/studies/${this.studyId}/events`, {
          headers: this.authHeaders,
        });
        const rows = Array.isArray(data) ? data : data?.items || [];
        this.all = rows.map(this.normalizeRow);

        // Resolve user names (best-effort)
        this.primeUsers(this.all.map((r) => r.user_id).filter(Boolean));

        // Build subject list, counts, labels
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
            if (label && !labels[key]) labels[key] = label;
          }

          const vi = this.getVisitIndexFromRow(r);
          if (vi === 0 || vi) {
            const vKey = String(vi);
            const vLabel = this.extractVisitLabel(r, vi);
            if (vLabel && !visitLabels[vKey]) visitLabels[vKey] = vLabel;
          }
        }

        this.subjectIds = Array.from(set).sort((a, b) => Number(a) - Number(b));
        this.subjectCounts = counts;
        this.subjectLabels = labels;
        this.visitLabels = visitLabels;

        if (this.activeTab === "subjects" && this.subjectIds.length && this.activeSubject === null) {
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

    // ====== tabs ======
    activateSubjectsTab() {
      this.activeTab = "subjects";
      if (this.subjectIds.length && this.activeSubject === null) {
        this.activeSubject = this.subjectIds[0];
      }
    },

    // ====== partitions ======
    studyRows() {
      return this.all.filter((r) => {
        const sid = this.getSubjectIdFromRow(r);
        return !(sid === 0 || sid);
      });
    },
    subjectRows() {
      const withSubject = this.all.filter((r) => {
        const sid = this.getSubjectIdFromRow(r);
        return sid === 0 || sid;
      });
      if (this.activeSubject === null) return withSubject;
      return withSubject.filter((r) => String(this.getSubjectIdFromRow(r)) === String(this.activeSubject));
    },

    // ====== normalize ======
    normalizeRow(r) {
      const userId = r.user?.id ?? r.user_id ?? null;
      return {
        id: r.id,
        study_id: r.study_id != null ? Number(r.study_id) : null,
        subject_id: r.subject_id != null ? Number(r.subject_id) : null,
        user_id: userId != null ? Number(userId) : null,
        action: r.action || "",
        details: r.details || {},
        timestamp: r.timestamp || r.ts || null,
        diff_path: r.diff_path || null, // optional
        __showRaw: false,
      };
    },

    // ====== subject/visit resolvers ======
    getSubjectIdFromRow(row) {
      if (row.subject_id === 0 || row.subject_id) return row.subject_id;
      const idx = row?.details?.subject_index;
      if (idx === 0 || idx) return Number(idx);
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
      const fromDetails = d.subject_id || d.subject_label || d.subject_code || null;
      if (fromDetails) return fromDetails;

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
      return d.visit_label || d.visit_name || d.visit_code || (vi === 0 || vi ? `Visit ${vi}` : null);
    },
    resolvedSubject(row) {
      const sid = this.getSubjectIdFromRow(row);
      if (!(sid === 0 || sid)) return "—";
      const key = String(sid);
      if (this.subjectLabels[key]) return this.subjectLabels[key];
      return this.extractSubjectLabel(row, sid) || String(sid);
    },
    resolvedVisit(row) {
      const vi = this.getVisitIndexFromRow(row);
      if (!(vi === 0 || vi)) return "—";
      const key = String(vi);
      if (this.visitLabels[key]) return this.visitLabels[key];
      return this.extractVisitLabel(row, vi) || String(vi);
    },
    displaySubject(sid) {
      const key = String(sid);
      return this.subjectLabels[key] || String(sid);
    },

    // ====== formatters ======
    fmtTs(ts) {
      if (!ts) return "—";
      return String(ts);
    },

    //  Action column: show audit UI label if present; fallback to action
    displayAction(row) {
      const ui = row?.details?.ui_label;
      if (ui && String(ui).trim()) return String(ui).trim();
      return row.action || "—";
    },

    summaryText(row) {
      const a = (row.action || "").toLowerCase();
      const d = row.details || {};

      if (a === "study_created") return "Study created";
      if (a === "study_edited") return "Study edited";

      if (a === "file_added" || a === "share_file_added") {
        const name = d.file_name || "file";
        const mods = Array.isArray(d.modalities) && d.modalities.length ? ` · ${d.modalities.join(", ")}` : "";
        const vi = this.resolvedVisit(row);
        const part = a === "share_file_added" ? "via share link" : "added";
        const subj = this.resolvedSubject(row);
        const loc = subj !== "—" || vi !== "—" ? ` (subj ${subj}, visit ${vi})` : "";
        return `File ${part}: ${name}${mods}${loc}`;
      }

      // backend now emits entry_upsert
      if (a === "entry_upsert" || a === "entry_upserted") {
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
        const exp = d.expires_in_days === 0 || d.expires_in_days ? `${d.expires_in_days}d` : "—";
        return `Share link created (permission ${p}, expires ${exp})`;
      }

      if (a === "access_granted")
        return `Access granted to ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;
      if (a === "access_updated")
        return `Access updated for ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;
      if (a === "access_revoked")
        return `Access revoked for ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;

      const keys = Object.keys(d || {});
      if (!keys.length) return "—";
      const parts = [];
      for (const k of keys.slice(0, 3)) {
        const val = d[k];
        if (["string", "number", "boolean"].includes(typeof val)) parts.push(`${k}: ${String(val)}`);
      }
      return parts.join(" · ");
    },

    formatDetailValue(val) {
      if (val === null || val === undefined) return "—";
      if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") return String(val);
      try {
        const s = JSON.stringify(val);
        return s.length > 120 ? s.slice(0, 117) + "…" : s;
      } catch {
        return String(val);
      }
    },

    // ====== raw ======
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

    // ====== user names ( regression-proof) ======
    userName(userId) {
      return this.getUserDisplayName(userId);
    },
    getUserDisplayName(userId) {
      if (!userId) return "—";
      const cached = this.nameCache[userId];
      return cached ? cached : `User#${userId}`;
    },
    async primeUsers(userIds) {
      const unique = Array.from(new Set(userIds)).filter(Boolean);
      const missing = unique.filter((id) => !this.nameCache[id]);

      for (const id of missing.slice(0, 25)) {
        try {
          const { data } = await axios.get(`/users/${id}`, { headers: this.authHeaders });
          const u = data || {};
          const firstLast = [u?.profile?.first_name, u?.profile?.last_name].filter(Boolean).join(" ").trim();
          const label = u.name || u.full_name || firstLast || u.username || u.email || `User#${id}`;
          if (this.$set) this.$set(this.nameCache, id, label);
          else this.nameCache[id] = label;
        } catch {
          if (this.$set) this.$set(this.nameCache, id, `User#${id}`);
          else this.nameCache[id] = `User#${id}`;
        }
      }
    },

    // ====== diff ======
    hasDiff(row) {
      const dp = row?.diff_path || row?.details?.diff_path || row?.details?.diffPath || row?.details?.diff_file || null;
      return !!(dp && String(dp).trim());
    },
    async openDiff(row) {
      if (!row?.id) return;

      this.diffOpen = true;
      this.diffLoading = true;
      this.diffEventId = row.id;
      this.diffData = null;
      this.diffError = "";
      this.diffPath = "";

      try {
        const { data } = await axios.get(`/audit/events/${row.id}/diff`, {
          headers: this.authHeaders,
        });
        this.diffData = data?.diff ?? data ?? null;
        this.diffPath = data?.diff_path || row?.details?.diff_path || row?.diff_path || "";
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || "Failed to load diff";
        this.diffError = String(msg);
      } finally {
        this.diffLoading = false;
      }
    },
    closeDiff() {
      this.diffOpen = false;
      this.diffLoading = false;
      this.diffEventId = null;
      this.diffData = null;
      this.diffError = "";
      this.diffPath = "";
    },
    pretty(obj) {
      try {
        return JSON.stringify(obj ?? {}, null, 2);
      } catch {
        return String(obj);
      }
    },
    prettyOne(val) {
      try {
        if (val === undefined) return "—";
        if (val === null) return "null";
        if (typeof val === "string") return val;
        return JSON.stringify(val, null, 2);
      } catch {
        return String(val);
      }
    },
  },
  async mounted() {
    await this.refreshAll();
  },
};
</script>

<style scoped>
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

.tabs {
  display: inline-flex;
  background: #eef2ff;
  border-radius: 999px;
  padding: 2px;

  /*  spacing between Study and Subjects */
  gap: 6px;
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
  background: #dbeafe;
  color: #1d4ed8;
  box-shadow: 0 1px 4px rgba(147, 197, 253, 0.8);
}

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

.title-wrap {
  margin-bottom: 6px;
}
.panel-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.tools {
  display: flex;
  gap: 8px;
  align-items: center;
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

.col-ts { width: 180px; }
.col-action { width: 220px; } /* a bit wider for audit labels */
.col-user { width: 200px; }
.col-details { width: auto; }
.col-raw { width: 130px; text-align: right; }

.audit-table tr:last-child td {
  border-bottom: none;
}

.strong { font-weight: 600; }
.wrap { white-space: normal; word-break: break-word; }
.user-cell .meta {
  color: #6b7280;
  font-size: 12px;
  margin-top: 2px;
}

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
.detail-line { display: flex; flex-wrap: wrap; }
.detail-key { font-weight: 600; margin-right: 4px; }
.detail-value { white-space: pre-wrap; word-break: break-word; }

.raw-wrap {
  background: #fafafa;
  border-top: 1px dashed #eee;
}

.actions-cell {
  text-align: right;
  white-space: nowrap;
}

.link-btn {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
  font-size: 12px;
  margin-left: 10px;
}
.link-btn:hover { text-decoration: underline; }

.empty-state {
  color: #6b7280;
  padding: 8px 0;
}
.mini-json { font-size: 11px; margin: 0; }

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 9999;
}
.modal {
  width: min(1100px, 96vw);
  max-height: 86vh;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #eee;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
}
.modal-title {
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.diff-path {
  font-weight: 500;
  color: #6b7280;
  font-size: 12px;
}
.btn-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}
.modal-body {
  padding: 12px;
  overflow: auto;
}
.diff-json {
  margin: 0;
  font-size: 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  padding: 10px;
}
.diff-error {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 10px;
  padding: 10px;
  font-size: 13px;
}
.modal-foot {
  padding: 10px 12px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
}

/*  Diff table (scrollable + sticky header) */
.diff-table-wrap {
  overflow: auto;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  background: #fff;
}
.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.diff-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f9fafb;
  border-bottom: 1px solid #eee;
  padding: 8px 10px;
  text-align: left;
  font-weight: 700;
  color: #374151;
}
.diff-table tbody td {
  border-bottom: 1px solid #f6f6f6;
  padding: 8px 10px;
  vertical-align: top;
}
.diff-table tbody tr:hover td {
  background: #fcfcfd;
}

.d-op { width: 90px; }
.d-path { width: 260px; }
.d-old, .d-new { width: 340px; }

.cell-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 8px;
  max-height: 200px;
  overflow: auto;
}

.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }

@media (max-width: 720px) {
  .col-user { width: 160px; }
  .col-action { width: 200px; }
  .d-path { width: 220px; }
}
</style>