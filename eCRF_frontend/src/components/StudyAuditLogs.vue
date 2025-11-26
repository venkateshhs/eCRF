<template>
  <div class="audit-shell">
    <!-- LEFT RAIL: vertical tabs -->
    <aside class="rail">
      <div class="rail-group">
        <div class="rail-title">Audit Views</div>
        <button
          class="rail-item"
          :class="{ active: activeTab === 'study' }"
          @click="activeTab = 'study'"
        >
          Study (System)
        </button>
        <button
          class="rail-item"
          :class="{ active: activeTab === 'subjects' }"
          @click="activateSubjectsTab()"
        >
          Subjects
        </button>
      </div>

      <!-- Subjects list only when Subjects tab is active -->
      <div v-if="activeTab === 'subjects'" class="rail-group subjects">
        <div class="rail-title small">Subjects</div>
        <div v-if="!subjectIds.length" class="rail-empty">No subjects found yet.</div>
        <button
          v-for="sid in subjectIds"
          :key="`sid-${sid}`"
          class="rail-item"
          :class="{ active: String(activeSubject) === String(sid) }"
          @click="selectSubject(sid)"
        >
          Subject {{ displaySubject(sid) }}
          <span class="count-badge">{{ subjectCounts[String(sid)] || 0 }}</span>
        </button>
      </div>
    </aside>

    <!-- RIGHT CONTENT AREA -->
    <main class="content">
      <!-- Toolbar -->
      <div class="content-head">
        <div class="title-wrap">
          <h2 class="panel-title" v-if="activeTab === 'study'">Study audit (system-level)</h2>
          <h2 class="panel-title" v-else>
            Subject audit<span v-if="activeSubject !== null"> — Subject {{ displaySubject(activeSubject) }}</span>
          </h2>
        </div>
        <div class="tools">
          <input
            class="input search"
            v-model="search"
            placeholder="Search action / user / details…"
            @input="debouncedFilter"
          />
          <button class="btn-minimal" @click="refreshAll" :disabled="loading">Refresh</button>
        </div>
      </div>

      <!-- Loading / empty states -->
      <div v-if="loading" class="empty-state">Loading audit…</div>
      <div v-else-if="!visibleRows.length" class="empty-state">No audit entries.</div>

      <!-- Tables -->
      <div v-else class="table-wrap">
        <table class="audit-table" aria-label="Audit">
          <thead>
            <tr>
              <th style="width: 180px">Timestamp</th>
              <th>Action</th>
              <th style="width: 220px">User</th>
              <th>Details</th>
              <th style="width: 80px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in visibleRows" :key="`row-${i}-${row.id || ''}`">
              <td class="mono">{{ fmtTs(row.timestamp) }}</td>
              <td class="strong">{{ row.action || '—' }}</td>
              <td class="user-cell">
                <div>{{ userName(row.user_id) }}</div>
                <div v-if="activeTab === 'subjects'" class="meta" title="Subject / Visit">
                  Subj: {{ resolvedSubject(row) }} · Visit: {{ resolvedVisit(row) }}
                </div>
              </td>
              <td class="wrap">{{ summaryText(row) }}</td>
              <td>
                <button class="link-btn" @click="toggleRaw(row)">{{ row.__showRaw ? 'hide' : 'view raw' }}</button>
              </td>
            </tr>
            <tr v-for="(row, i) in visibleRows" :key="`raw-${i}-${row.id || ''}`" v-show="row.__showRaw">
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
      all: [],                // all events (for this study) from API
      search: "",
      activeTab: "study",     // 'study' | 'subjects'
      activeSubject: null,    // subject id string/number or null
      subjectIds: [],         // list of subject ids as strings
      subjectCounts: {},      // sid -> count
      nameCache: {},          // user id -> display name
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
      const base = this.activeTab === "study" ? this.studyRows() : this.subjectRows();
      return this.applySearch(base, this.search);
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
        const rows = Array.isArray(data) ? data : (data?.items || []);
        this.all = rows.map(this.normalizeRow);

        // Resolve user names (best-effort)
        this.primeUsers(this.all.map(r => r.user_id).filter(Boolean));

        // Build subject list and counts from resolved subject ids
        const counts = {};
        const set = new Set();
        for (const r of this.all) {
          const sid = this.getSubjectIdFromRow(r);
          if (sid === 0 || sid) {
            const key = String(sid);
            set.add(key);
            counts[key] = (counts[key] || 0) + 1;
          }
        }
        this.subjectIds = Array.from(set).sort((a, b) => Number(a) - Number(b));
        this.subjectCounts = counts;

        // If subjects tab is active but activeSubject is not set, pick the first
        if (this.activeTab === "subjects" && this.subjectIds.length && (this.activeSubject === null)) {
          this.activeSubject = this.subjectIds[0];
        }
      } catch (e) {
        console.warn("Audit fetch failed:", e?.response?.data || e.message);
        this.all = [];
        this.subjectIds = [];
        this.subjectCounts = {};
      } finally {
        this.loading = false;
      }
    },

    // ====== tabs / subject selection ======
    activateSubjectsTab() {
      this.activeTab = "subjects";
      if (this.subjectIds.length && (this.activeSubject === null)) {
        this.activeSubject = this.subjectIds[0];
      }
    },
    selectSubject(sid) {
      this.activeSubject = sid;
    },

    // ====== partition helpers ======
    studyRows() {
      // study/system-level = those without a resolvable subject id
      return this.all.filter(r => {
        const sid = this.getSubjectIdFromRow(r);
        return !(sid === 0 || sid);
      });
    },
    subjectRows() {
      // subject-level = those with a resolvable subject id (and matches activeSubject)
      const withSubject = this.all.filter(r => {
        const sid = this.getSubjectIdFromRow(r);
        return (sid === 0 || sid);
      });
      if (this.activeSubject === null) return withSubject;
      return withSubject.filter(r => String(this.getSubjectIdFromRow(r)) === String(this.activeSubject));
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
      // prefer explicit subject_id
      if (row.subject_id === 0 || row.subject_id) return row.subject_id;
      // fallback: details.subject_index
      const idx = row?.details?.subject_index;
      if (idx === 0 || idx) return Number(idx);
      // fallback: details.participant_id like sub-001
      const pid = row?.details?.participant_id || "";
      const m = /^sub-(\d+)/i.exec(pid);
      if (m) return Number(m[1]);
      return null;
    },
    resolvedSubject(row) {
      const sid = this.getSubjectIdFromRow(row);
      return (sid === 0 || sid) ? String(sid) : "—";
    },
    resolvedVisit(row) {
      const vi = row?.details?.visit_index;
      if (vi === 0 || vi) return String(vi);
      const vn = row?.details?.visit_name;
      return vn ? String(vn) : "—";
    },
    fmtTs(ts) {
      if (!ts) return "—";
      try {
        const d = new Date(ts);
        // display as UTC-ish (strip ms)
        return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
          .toISOString()
          .replace(/\.\d{3}Z$/, "Z");
      } catch {
        return String(ts);
      }
    },
    displaySubject(sid) {
      // If your app uses zero-padded display, uncomment next line
      // return String(sid).padStart(3, "0");
      return String(sid);
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
        const mods = Array.isArray(d.modalities) && d.modalities.length ? ` · ${d.modalities.join(", ")}` : "";
        const vi = this.resolvedVisit(row);
        const part = (a === "share_file_added") ? "via share link" : "added";
        const subj = this.resolvedSubject(row);
        const loc = (subj !== "—" || vi !== "—") ? ` (subj ${subj}, visit ${vi})` : "";
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
        const exp = (d.expires_in_days === 0 || d.expires_in_days) ? `${d.expires_in_days}d` : "—";
        return `Share link created (permission ${p}, expires ${exp})`;
      }

      if (a === "access_granted") return `Access granted to ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;
      if (a === "access_updated") return `Access updated for ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;
      if (a === "access_revoked") return `Access revoked for ${d.target_user_display || d.target_user_email || `User#${d.target_user_id}`}`;

      // Fallback: tiny slice of details
      const keys = Object.keys(d || {});
      if (!keys.length) return "—";
      const parts = [];
      for (const k of keys.slice(0, 3)) {
        const val = d[k];
        if (["string","number","boolean"].includes(typeof val)) parts.push(`${k}: ${String(val)}`);
      }
      return parts.join(" · ");
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
      return rows.filter(r => {
        const parts = [
          this.fmtTs(r.timestamp),
          r.action || "",
          this.userName(r.user_id),
          this.summaryText(r),
          this.resolvedSubject(r),
          this.resolvedVisit(r),
        ].map(s => (s || "").toString().toLowerCase());
        return parts.some(s => s.includes(q));
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
      const missing = unique.filter(id => !this.nameCache[id]);
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
  },
  async mounted() {
    await this.refreshAll();
  },
};
</script>

<style scoped>
/* Layout */
.audit-shell { display: grid; grid-template-columns: 260px 1fr; gap: 16px; min-height: 420px; }
.rail { background:#fff; border:1px solid #f1f1f1; border-radius:12px; padding:10px; display:flex; flex-direction:column; gap:14px; }
.content { background:#fff; border:1px solid #f1f1f1; border-radius:12px; padding:12px; display:flex; flex-direction:column; }

.content-head { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-bottom:8px; }
.panel-title { margin:0; font-size:16px; font-weight:700; }
.tools { display:flex; gap:8px; align-items:center; }

/* Rail */
.rail-group { display:flex; flex-direction:column; gap:6px; }
.rail-title { font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#6b7280; padding:4px 6px; }
.rail-title.small { font-size:11px; }
.rail-item {
  text-align:left; padding:8px 10px; border-radius:8px; border:1px solid #e5e7eb; background:#fff; cursor:pointer;
  font-size:14px; color:#374151; display:flex; align-items:center; justify-content:space-between; gap:8px;
}
.rail-item:hover { background:#f9fafb; }
.rail-item.active { background:#eef2ff; border-color:#c7d2fe; color:#1f2937; }
.rail-empty { color:#6b7280; font-size:13px; padding:8px 6px; }
.count-badge { font-size:12px; background:#f3f4f6; padding:0 6px; border-radius:999px; border:1px solid #e5e7eb; }

/* Inputs / buttons */
.input { height:36px; padding:6px 10px; border:1px solid #d1d5db; border-radius:8px; font-size:14px; background:#fff; }
.search { width:260px; }
.btn-minimal {
  background:none; border:1px solid #e0e0e0; border-radius:8px; padding:8px 12px; font-size:14px; color:#555; cursor:pointer;
}
.btn-minimal:hover { background:#e8e8e8; color:#000; border-color:#d6d6d6; }
.link-btn { background:none; border:none; color:#2563eb; cursor:pointer; padding:0; font-size:12px; }
.link-btn:hover { text-decoration: underline; }

/* Table */
.table-wrap { overflow:auto; border:1px solid #f5f5f5; border-radius:10px; }
.audit-table { width:100%; border-collapse:collapse; font-size:13px; }
.audit-table th, .audit-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f6f6f6;
  text-align: left;
  vertical-align: top;
}
.audit-table thead th { background:#fafafe; color:#374151; font-weight:600; }
.audit-table tr:last-child td { border-bottom:none; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.strong { font-weight:600; }
.wrap { white-space: normal; word-break: break-word; }
.user-cell .meta { color:#6b7280; font-size:12px; margin-top:2px; }
.raw-wrap { background:#fafafa; border-top:1px dashed #eee; }

/* States */
.empty-state { color:#6b7280; padding:8px 0; }
</style>
