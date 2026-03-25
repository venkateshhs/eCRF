<template>
  <div class="audit-shell">
    <main class="content">
      <div class="content-head">
        <div class="left-cluster">
          <div class="tabs">
            <button class="tab" :class="{ active: activeTab === 'study' }" @click="setTab('study')">
              Study
            </button>
            <button class="tab" :class="{ active: activeTab === 'subjects' }" @click="setTab('subjects')">
              Subjects
            </button>
          </div>

          <div v-if="activeTab === 'subjects'" class="subject-select-wrap">
            <label class="subject-label">
              Subject
              <select v-model="activeSubject" class="subject-select" @change="refreshSubjectEvents">
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

      <div class="title-wrap">
        <h2 class="panel-title" v-if="activeTab === 'study'">
          Study audit (system-level)
        </h2>
        <h2 class="panel-title" v-else>
          Subject audit
          <span v-if="activeSubject !== null"> — {{ displaySubject(activeSubject) }}</span>
        </h2>
      </div>

      <div v-if="loading" class="empty-state">Loading audit…</div>
      <div v-else-if="!visibleRows.length" class="empty-state">No audit entries.</div>

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
            <template v-for="(row, i) in visibleRows" :key="`blk-${row.id || 'noid'}-${i}`">
              <tr>
                <td class="mono">{{ fmtTs(row.timestamp) }}</td>
                <td class="strong">{{ displayAction(row) }}</td>

                <td class="user-cell">
                  <div>{{ getUserDisplayName(row.user_id, row.user) }}</div>
                  <div v-if="activeTab === 'subjects'" class="meta" title="Subject / Visit / Group">
                    Subj: {{ resolvedSubject(row) }} · Visit: {{ resolvedVisit(row) }} · Group: {{ resolvedGroup(row) }}
                  </div>
                </td>

                <td class="wrap">
                  <div class="detail-main">{{ summaryText(row) }}</div>

                  <div v-if="row.details && Object.keys(row.details).length" class="detail-lines">
                    <div
                      v-for="(val, key) in filteredDetails(row.details)"
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

              <tr v-show="row.__showRaw">
                <td :colspan="5" class="raw-wrap">
                  <pre class="mini-json">{{ safeDetail(row.raw || row.details) }}</pre>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

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
            <div v-if="diffError" class="diff-error">{{ diffError }}</div>

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
                    <td class="d-old"><pre class="cell-pre">{{ prettyOne(d?.old) }}</pre></td>
                    <td class="d-new"><pre class="cell-pre">{{ prettyOne(d?.new) }}</pre></td>
                  </tr>
                </tbody>
              </table>
            </div>

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
      activeTab: "study",
      activeSubject: null,
      studyEvents: [],
      subjectEvents: [],
      subjectIds: [],
      subjectCounts: {},
      subjectLabels: {},
      visitLabels: {},
      groupLabels: {},
      nameCache: {},

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
      return this.activeTab === "study" ? this.studyEvents : this.subjectEvents;
    },
  },
  watch: {
    studyId: {
      async handler() {
        await this.refreshAll();
      },
    },
    activeSubject: {
      async handler() {
        if (this.activeTab === "subjects") {
          await this.refreshSubjectEvents();
        }
      },
    },
  },
  methods: {
    async refreshAll() {
      if (!this.token) return;
      this.loading = true;
      try {
        await Promise.all([this.refreshOverview(), this.refreshStudyEvents()]);
        if (this.activeTab === "subjects") {
          if (this.activeSubject === null && this.subjectIds.length) {
            this.activeSubject = this.subjectIds[0];
          } else {
            await this.refreshSubjectEvents();
          }
        }
      } catch (e) {
        console.warn("Audit refresh failed:", e?.response?.data || e.message);
        this.studyEvents = [];
        this.subjectEvents = [];
        this.subjectIds = [];
        this.subjectCounts = {};
        this.subjectLabels = {};
        this.visitLabels = {};
        this.groupLabels = {};
      } finally {
        this.loading = false;
      }
    },

    async refreshOverview() {
      const { data } = await axios.get(`/audit/studies/${this.studyId}/audit-overview`, {
        headers: this.authHeaders,
      });

      const subjects = Array.isArray(data?.subjects) ? data.subjects : [];
      const counts = {};
      const labels = {};
      const visitLabels = {};
      const groupLabels = {};
      const ids = [];

      for (const item of subjects) {
        const sid = item?.subject_index;
        if (!(sid === 0 || sid)) continue;

        const key = String(sid);
        ids.push(key);
        counts[key] = Number(item?.events_count || 0);

        const latest = item?.latest_event || {};
        const subjLabel = latest?.subject_raw || item?.subject_raw || `Subject ${sid}`;
        labels[key] = subjLabel;

        const vi = latest?.visit_index;
        if (vi === 0 || vi) {
          const vKey = String(vi);
          if (!visitLabels[vKey]) visitLabels[vKey] = latest?.visit_raw || `Visit ${vi}`;
        }

        const gi = latest?.group_index;
        if (gi === 0 || gi) {
          const gKey = String(gi);
          if (!groupLabels[gKey]) groupLabels[gKey] = latest?.group_raw || `Group ${gi}`;
        }
      }

      this.subjectIds = Array.from(new Set(ids)).sort((a, b) => Number(a) - Number(b));
      this.subjectCounts = counts;
      this.subjectLabels = labels;
      this.visitLabels = visitLabels;
      this.groupLabels = groupLabels;

      if (this.activeTab === "subjects" && this.subjectIds.length && this.activeSubject === null) {
        this.activeSubject = this.subjectIds[0];
      }
    },

    async refreshStudyEvents() {
      const { data } = await axios.get(`/audit/studies/${this.studyId}/events`, {
        headers: this.authHeaders,
      });
      const rows = Array.isArray(data) ? data : [];
      this.studyEvents = rows.map(this.normalizeRow);
      this.primeUsers(this.studyEvents.map((r) => r.user_id).filter(Boolean));
    },

    async refreshSubjectEvents() {
      if (!(this.activeSubject === 0 || this.activeSubject)) {
        this.subjectEvents = [];
        return;
      }

      const { data } = await axios.get(
        `/audit/studies/${this.studyId}/subjects/${this.activeSubject}/events`,
        { headers: this.authHeaders }
      );
      const rows = Array.isArray(data) ? data : [];
      this.subjectEvents = rows.map(this.normalizeRow);
      this.primeUsers(this.subjectEvents.map((r) => r.user_id).filter(Boolean));
    },

    async setTab(tab) {
      this.activeTab = tab;
      if (tab === "subjects") {
        if (this.activeSubject === null && this.subjectIds.length) {
          this.activeSubject = this.subjectIds[0];
        } else {
          await this.refreshSubjectEvents();
        }
      }
    },

    normalizeRow(r) {
      const details = r.details || r.payload || {};
      const userId = r.user_id ?? null;
      return {
        id: r.id,
        study_id: r.study_id != null ? Number(r.study_id) : null,
        subject_id: r.subject_index != null ? Number(r.subject_index) : null,
        visit_index: r.visit_index != null ? Number(r.visit_index) : null,
        group_index: r.group_index != null ? Number(r.group_index) : null,
        user_id: userId != null ? Number(userId) : null,
        user: r.user || "",
        action: r.action || "",
        details,
        raw: r,
        timestamp: r.timestamp || null,
        diff_path: r.diff_path || null,
        diff_available: !!r.diff_available,
        __showRaw: false,
      };
    },

    filteredDetails(details) {
      const hidden = new Set(["diff_payload", "old_content", "old_template_schema"]);
      const out = {};
      Object.keys(details || {}).forEach((k) => {
        if (!hidden.has(k)) out[k] = details[k];
      });
      return out;
    },

    resolvedSubject(row) {
      const idx = row?.subject_id;
      const raw = row?.details?.subject_raw;
      if (raw) return raw;
      if (idx === 0 || idx) return this.subjectLabels[String(idx)] || `Subject ${idx}`;
      return "—";
    },

    resolvedVisit(row) {
      const idx = row?.visit_index ?? row?.details?.visit_index;
      const raw = row?.details?.visit_raw;
      if (raw) return raw;
      if (idx === 0 || idx) return this.visitLabels[String(idx)] || `Visit ${idx}`;
      return "—";
    },

    resolvedGroup(row) {
      const idx = row?.group_index ?? row?.details?.group_index;
      const raw = row?.details?.group_raw;
      if (raw) return raw;
      if (idx === 0 || idx) return this.groupLabels[String(idx)] || `Group ${idx}`;
      return "—";
    },

    displaySubject(sid) {
      return this.subjectLabels[String(sid)] || `Subject ${sid}`;
    },

    fmtTs(ts) {
      if (!ts) return "—";
      return String(ts);
    },

    displayAction(row) {
      const ui = row?.details?.ui_label;
      if (ui && String(ui).trim()) return String(ui).trim();

      const a = String(row.action || "").toLowerCase();
      const map = {
        study_created: "Study created",
        study_edited: "Study edited",
        study_snapshot_written: "Published snapshot written",
        entry_upserted: "Data saved/edited",
        file_added: "File added",
        share_link_created: "Share link created",
        access_changed: "Access changed",
        access_revoked: "Access revoked",
      };
      return map[a] || row.action || "—";
    },

    summaryText(row) {
      const a = (row.action || "").toLowerCase();
      const d = row.details || {};

      if (a === "study_created") return "Study created";
      if (a === "study_edited") return "Study edited";
      if (a === "study_snapshot_written") {
        return `Published snapshot written${d.version ? ` (v${d.version})` : ""}`;
      }
      if (a === "entry_upserted") {
        return `Data saved/edited (subj ${this.resolvedSubject(row)}, visit ${this.resolvedVisit(row)}, group ${this.resolvedGroup(row)})`;
      }
      if (a === "file_added") {
        const fileName = d.file_name || d.url || "file";
        return `File added: ${fileName}`;
      }
      if (a === "share_link_created") {
        return `Share link created (permission ${d.permission || "—"})`;
      }
      if (a === "access_changed") {
        return `Access changed for ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;
      }
      if (a === "access_revoked") {
        return `Access revoked for ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;
      }
      return row.raw?.summary || "—";
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

    toggleRaw(row) {
      row.__showRaw = !row.__showRaw;
      this.$forceUpdate?.();
    },

    safeDetail(obj) {
      try {
        const s = JSON.stringify(obj || {}, null, 2);
        return s.length > 4000 ? s.slice(0, 3997) + "…" : s;
      } catch {
        return "{}";
      }
    },

    getUserDisplayName(userId, rawUser) {
      if (rawUser && String(rawUser).trim()) return String(rawUser).trim();
      if (!userId) return "—";
      return this.nameCache[userId] || `User#${userId}`;
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

    hasDiff(row) {
      return !!row?.diff_available;
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
        const params = {};
        if (this.activeTab === "subjects" && (row.subject_id === 0 || row.subject_id)) {
          params.subject_index = row.subject_id;
        }

        const { data } = await axios.get(
          `/audit/studies/${this.studyId}/events/${row.id}/diff`,
          {
            headers: this.authHeaders,
            params,
          }
        );

        this.diffData = data?.diff ?? null;
        this.diffPath = data?.diff_path || "";
      } catch (e) {
        const maybeHtml = e?.response?.data;
        if (typeof maybeHtml === "string" && maybeHtml.toLowerCase().includes("<!doctype html>")) {
          this.diffError = "Diff endpoint returned the app HTML page. Check backend route registration or proxy path.";
        } else {
          this.diffError = e?.response?.data?.detail || e?.message || "Failed to load diff";
        }
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
.col-action { width: 220px; }
.col-user { width: 200px; }
.col-details { width: auto; }
.col-raw { width: 130px; text-align: right; }

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
.mini-json {
  font-size: 11px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

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
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
@media (max-width: 720px) {
  .col-user { width: 160px; }
  .col-action { width: 200px; }
  .d-path { width: 220px; }
}
</style>