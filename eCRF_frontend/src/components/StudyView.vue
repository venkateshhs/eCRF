<template>
  <div class="study-view-layout">
    <header class="sv-header">
      <button class="btn-minimal back-btn" @click="goBackToDashboard" aria-label="Back to Dashboard">Back</button>
      <div class="title-wrap">
        <h1 class="sv-title">{{ studyMeta.study_name || 'Study' }}</h1>
        <p class="sv-subtitle" v-if="studyMeta.study_description">{{ studyMeta.study_description }}</p>
      </div>
      <div class="header-spacer" aria-hidden="true"></div>
    </header>

    <div class="sv-content card">
      <!-- Vertical Tabs -->
      <aside class="v-tabs" role="tablist" aria-orientation="vertical">
        <button
          v-for="t in tabs"
          :key="t.key"
          :class="['v-tab', { active: activeTab === t.key }]"
          @click="activeTab = t.key"
          role="tab"
          :aria-selected="activeTab === t.key"
        >
          {{ t.label }}
        </button>
      </aside>

      <!-- Panels -->
      <section class="v-panel">
        <!-- META-DATA -->
        <div v-if="activeTab === 'meta'">
          <h2 class="panel-title">Meta-data</h2>

          <!-- Core meta (only show fields that have values) -->
          <div class="meta-grid">
            <div class="meta-item" v-if="hasValue(studyMeta.id)">
              <div class="meta-label">Study ID</div>
              <div class="meta-value monospace">{{ studyMeta.id }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.study_name)">
              <div class="meta-label">Name</div>
              <div class="meta-value">{{ studyMeta.study_name }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.study_description)">
              <div class="meta-label">Description</div>
              <div class="meta-value">{{ studyMeta.study_description }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.created_by)">
              <div class="meta-label">Created By</div>
              <div class="meta-value">{{ studyMeta.created_by }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.created_at)">
              <div class="meta-label">Created At</div>
              <div class="meta-value">{{ formatDateTime(studyMeta.created_at) }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.updated_at)">
              <div class="meta-label">Updated At</div>
              <div class="meta-value">{{ formatDateTime(studyMeta.updated_at) }}</div>
            </div>
          </div>

          <!-- Study Data -->
          <div class="subsection">
            <h3 class="sub-title">Study Data</h3>
            <div v-if="studyKVEntries.length" class="kv-grid">
              <div class="kv-row" v-for="entry in studyKVEntries" :key="entry[0]">
                <div class="kv-key">{{ prettyLabel(entry[0]) }}</div>
                <div class="kv-val">{{ formatAny(entry[1]) }}</div>
              </div>
            </div>
            <div v-else class="empty-state">No additional study data.</div>
          </div>

          <!-- Groups -->
          <div class="subsection">
            <h3 class="sub-title">Groups</h3>
            <div v-if="groups && groups.length" class="list-grid">
              <div class="list-card" v-for="(g, i) in groups" :key="i">
                <div class="kv-row" v-for="entry in objectEntriesFiltered(g)" :key="entry[0]">
                  <div class="kv-key">{{ prettyLabel(entry[0]) }}</div>
                  <div class="kv-val">{{ formatAny(entry[1]) }}</div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">No groups defined.</div>
          </div>

          <!-- Visits -->
          <div class="subsection">
            <h3 class="sub-title">Visits</h3>
            <div v-if="visits && visits.length" class="list-grid">
              <div class="list-card" v-for="(v, i) in visits" :key="i">
                <div class="kv-row" v-for="entry in objectEntriesFiltered(v)" :key="entry[0]">
                  <div class="kv-key">{{ prettyLabel(entry[0]) }}</div>
                  <div class="kv-val">{{ formatAny(entry[1]) }}</div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">No visits defined.</div>
          </div>

          <!-- Subject Assignment -->
          <div class="subsection">
            <h3 class="sub-title">Subject Assignment</h3>
            <div class="kv-grid">
              <div class="kv-row" v-if="hasValue(studyData.assignmentMethod)">
                <div class="kv-key">Assignment Method</div>
                <div class="kv-val">{{ studyData.assignmentMethod }}</div>
              </div>
              <div class="kv-row" v-if="hasValue(studyData.subjectCount)">
                <div class="kv-key">Subjects Planned</div>
                <div class="kv-val">{{ studyData.subjectCount }}</div>
              </div>
              <div class="kv-row" v-if="Array.isArray(subjects)">
                <div class="kv-key">Subjects Enrolled</div>
                <div class="kv-val">{{ subjects.length }}</div>
              </div>
              <div class="kv-row" v-if="assignmentSize">
                <div class="kv-key">Assignment Matrix</div>
                <div class="kv-val">
                  {{ assignmentSize.m }} × {{ assignmentSize.v }} × {{ assignmentSize.g }}
                  <span class="muted">(models × visits × groups)</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Edit Study -->
          <div class="edit-row">
            <button class="btn-primary" @click="editStudy">Edit Study</button>
          </div>
        </div>

        <!-- DOCUMENTS -->
        <div v-else-if="activeTab === 'docs'">
          <h2 class="panel-title">Documents</h2>
          <div v-if="documents && documents.length" class="doc-list">
            <div v-for="(doc, i) in documents" :key="i" class="doc-item">
              <div class="doc-name">{{ doc.name || doc.title || 'Document' }}</div>
              <div class="doc-meta muted">
                {{ doc.type || doc.mime || 'file' }} •
                {{ doc.size ? prettyBytes(doc.size) : (doc.bytes ? prettyBytes(doc.bytes) : 'unknown size') }}
              </div>
            </div>
          </div>
          <div v-else class="empty-state">No documents available for this study.</div>
        </div>

        <!-- STUDY TEAM -->
        <div v-else-if="activeTab === 'team'">
          <h2 class="panel-title">Study Team</h2>
          <div v-if="team && team.length" class="team-list">
            <div v-for="(m, i) in team" :key="i" class="team-card">
              <div class="team-name">{{ m.name || m.displayName || m.email || 'Team Member' }}</div>
              <div class="team-role muted">{{ m.role || '—' }}</div>
              <div class="team-contact">
                <div v-if="m.email" class="contact-row">
                  <span class="label">Email:</span>
                  <a :href="'mailto:' + m.email">{{ m.email }}</a>
                </div>
                <div v-if="m.phone || m.phoneNumber" class="contact-row">
                  <span class="label">Phone:</span>
                  <a :href="'tel:' + (m.phone || m.phoneNumber)">{{ m.phone || m.phoneNumber }}</a>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">No team members defined for this study.</div>
        </div>

        <!-- VIEW DATA: Auto-redirect -->
        <div v-else-if="activeTab === 'viewdata'">
          <h2 class="panel-title">View Data</h2>
          <p class="muted">Redirecting to the data dashboard…</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyView",
  data() {
    return {
      studyId: this.$route.params.id,
      studyMeta: {},
      studyData: {},
      documents: [],
      team: [],
      me: null, // /me response
      activeTab: "meta",
      tabs: [
        { key: "meta", label: "Meta-data" },
        { key: "docs", label: "Documents" },
        { key: "team", label: "Study Team" },
        { key: "viewdata", label: "View Data" },
      ],
    };
  },
  computed: {
    groups() {
      return Array.isArray(this.studyData.groups) ? this.studyData.groups : [];
    },
    visits() {
      return Array.isArray(this.studyData.visits) ? this.studyData.visits : [];
    },
    subjects() {
      return Array.isArray(this.studyData.subjects) ? this.studyData.subjects : [];
    },
    assignmentSize() {
      const a = this.studyData.assignments;
      if (!Array.isArray(a) || !a.length) return null;
      const m = a.length;
      const v = Array.isArray(a[0]) ? a[0].length : 0;
      const g = v && Array.isArray(a[0][0]) ? a[0][0].length : 0;
      return { m, v, g };
    },
    studyKVEntries() {
      return this.objectEntriesFiltered(this.studyData.study);
    },
  },
  watch: {
    activeTab(val) {
      if (val === "viewdata") this.goViewData();
    },
  },
  methods: {
     async fetchUserNameById(userId) {
      const token = this.$store.state.token;
      if (!token || userId == null) return null;
      try {
        const { data } = await axios.get(`http://127.0.0.1:8000/users/${userId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const u = data || {};
        const firstLast = [u?.profile?.first_name, u?.profile?.last_name].filter(Boolean).join(" ").trim();
        return u.name || u.full_name || firstLast || u.username || u.email || null;
      } catch (e) {
        console.warn("fetchUserNameById failed:", e?.response?.data || e.message);
        return null;
      }
    },
    scrollToTop() {
      try {
        window.scrollTo({ top: 0, left: 0, behavior: "auto" });
        if (this.$el && typeof this.$el.scrollTop === "number") this.$el.scrollTop = 0;
      } catch (err) {console.warn("StudyView scrollToTop failed:", err);}
    },
    goBackToDashboard() {
      this.$router.push({ name: "Dashboard", query: { openStudies: "true" } });
    },
    formatDateTime(d) {
      if (!d) return "";
      return new Date(d).toLocaleString("en-GB", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
    },
    prettyBytes(n) {
      if (!n && n !== 0) return "";
      const units = ["B","KB","MB","GB","TB"];
      const i = n === 0 ? 0 : Math.floor(Math.log(n)/Math.log(1024));
      return `${(n/Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
    },
    prettyLabel(key) {
      if (!key) return "";
      return String(key)
        .replace(/[-_]+/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/\s+/g, " ")
        .replace(/^./, s => s.toUpperCase());
    },
    formatAny(val) {
      if (val == null) return "—";
      if (typeof val === "boolean") return val ? "Yes" : "No";
      if (Array.isArray(val)) return val.length ? JSON.stringify(val) : "—";
      if (typeof val === "object") return Object.keys(val).length ? JSON.stringify(val) : "—";
      const s = String(val);
      return s.trim().length ? s : "—";
    },
    hasValue(val) {
      if (val === null || val === undefined) return false;
      if (typeof val === "string") return val.trim().length > 0;
      if (Array.isArray(val)) return val.length > 0;
      if (typeof val === "object") return Object.keys(val).length > 0;
      // numbers/booleans count as values (0 and false are valid)
      return true;
    },
    objectEntriesFiltered(obj) {
      return Object.entries(obj || {}).filter(([, v]) => this.hasValue(v));
    },
    displayNameFromUser(u) {
      if (!u) return "";
      const firstLast = [u.first_name, u.last_name].filter(Boolean).join(" ").trim();
      return u.name || u.full_name || firstLast || u.username || u.email || "";
    },
    resolveCreator(meta) {
      const explicit =
        meta.created_by_name ||
        meta.created_by_full_name ||
        meta.created_by_display ||
        meta.created_by_username ||
        meta.created_by_email;
      if (explicit) return explicit;
      // try matching /me if ids/usernames/emails align
      if (this.me) {
        const meName = this.displayNameFromUser(this.me);
        const createdBy = meta.created_by != null ? String(meta.created_by) : "";
        const meId = this.me.id != null ? String(this.me.id) : "";
        if (createdBy && (createdBy === meId || createdBy === this.me.username || createdBy === this.me.email)) {
          return meName || createdBy;
        }
      }
      return meta.created_by || "-";
    },
    async fetchMe() {
      const token = this.$store.state.token;
      if (!token) return;
      try {
        const { data } = await axios.get("http://127.0.0.1:8000/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        this.me = data || null;
        console.log("Venkatesh", data)
      } catch (e) {
        console.warn("Failed to fetch /me:", e?.response?.data || e.message);
      }
    },
    async fetchStudy() {
      const token = this.$store.state.token;
      if (!token) {
        this.$router.push("/login");
        return;
      }
      try {
        const resp = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${this.studyId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const sd = resp.data?.content?.study_data || {};
        const meta = resp.data?.metadata || {};
        let createdByDisplay =
          meta.created_by_name ||
          meta.created_by_full_name ||
          meta.created_by_display ||
          meta.created_by_username ||
          meta.created_by_email ||
          null;

        if (!createdByDisplay && meta.created_by != null) {
          // created_by is an ID; resolve it via /users/{id}
          const resolved = await this.fetchUserNameById(meta.created_by);
          createdByDisplay = resolved || String(meta.created_by);
        }
        this.studyMeta = {
          id: meta.id,
          study_name: meta.study_name,
          study_description: meta.study_description,
          created_at: meta.created_at,
          updated_at: meta.updated_at,
          created_by: createdByDisplay || "-",
        };
        this.studyData = sd || {};
        this.documents = Array.isArray(sd.documents) ? sd.documents : [];
        const maybeTeam = sd.team || sd.studyTeam || sd.collaborators || [];
        this.team = Array.isArray(maybeTeam) ? maybeTeam : [];
      } catch (e) {
        console.error("Failed to fetch study view:", e);
      }
    },
    goViewData() {
      this.$router.push({ name: "StudyDataDashboard", params: { id: this.studyId } });
    },
    async editStudy() {
      localStorage.removeItem("setStudyDetails");
      localStorage.removeItem("scratchForms");
      const token = this.$store.state.token;
      if (!token) {
        this.$router.push("/login");
        return;
      }
      try {
        const resp = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${this.studyId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const sd = resp.data.content?.study_data;
        const meta = resp.data.metadata || {};
        if (!sd) {
          console.error("Study content is empty");
          return;
        }
        let assignments = Array.isArray(sd.assignments) ? sd.assignments : [];
        if (!assignments.length && sd.selectedModels?.length) {
          const m = sd.selectedModels.length;
          const v = sd.visits?.length || 0;
          const g = sd.groups?.length || 0;
          assignments = Array.from({ length: m }, () =>
            Array.from({ length: v }, () =>
              Array.from({ length: g }, () => false)
            )
          );
        }
        const studyInfo = {
          id: meta.id,
          name: meta.study_name,
          description: meta.study_description,
          created_at: meta.created_at,
          updated_at: meta.updated_at,
          created_by: meta.created_by
        };
        this.$store.commit("setStudyDetails", {
          study_metadata: studyInfo,
          study: { id: meta.id, ...sd.study },
          groups: sd.groups || [],
          visits: sd.visits || [],
          subjectCount: sd.subjectCount || 0,
          assignmentMethod: sd.assignmentMethod || "random",
          subjects: sd.subjects || [],
          assignments: assignments,
          forms: sd.selectedModels ? [{
            sections: sd.selectedModels.map(model => ({
              title: model.title,
              fields: model.fields,
              source: "template"
            }))
          }] : []
        });
        if (sd.selectedModels) {
          const scratchForms = [{
            sections: sd.selectedModels.map(model => ({
              title: model.title,
              fields: model.fields,
              source: "template"
            }))
          }];
          localStorage.setItem("scratchForms", JSON.stringify(scratchForms));
        }
        this.$router.push({ name: "CreateStudy", params: { id: this.studyId } });
      } catch (e) {
        console.error("Failed to load study details for edit:", e);
      }
    },
  },
  mounted() {
    this.scrollToTop();
    this.fetchMe().finally(() => this.fetchStudy());
  },
  beforeRouteEnter(to, from, next) {
    next(vm => vm.scrollToTop());
  },
  beforeRouteUpdate(to, from, next) {
    this.studyId = to.params.id;
    this.scrollToTop();
    this.fetchStudy();
    next();
  },
};
</script>

<style scoped>
/* Typography base for consistency */
:host, * {
  font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif;
  letter-spacing: 0.1px;
}

.study-view-layout {
  display: flex; flex-direction: column; gap: 16px;
  padding: 24px; background: #f9fafb; min-height: 100%;
}

/* Header */
.sv-header {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
}
.back-btn {
  position: absolute;
  left: 0; top: 50%; transform: translateY(-50%);
}
.title-wrap {
  grid-column: 2 / 3;
  min-width: 0;
  text-align: center;
}
.sv-title { margin: 0; font-size: 22px; font-weight: 800; color: #111827; }
.sv-subtitle { margin: 6px 0 0; color: #6b7280; }
.header-spacer { width: 56px; height: 1px; }

/* Card layout */
.card {
  display: grid; grid-template-columns: 240px 1fr;
  background: #fff; border: 1px solid #ececec; border-radius: 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.04); overflow: hidden;
}

/* Vertical tabs */
.v-tabs {
  background: #fcfcff; border-right: 1px solid #f0f0f6; padding: 10px;
  display: flex; flex-direction: column; gap: 8px; min-height: 360px;
}
.v-tab {
  text-align: left; background: #fff; border: 1px solid #ececec; border-radius: 10px;
  padding: 10px 12px; font-size: 14px; color: #374151; cursor: pointer;
  transition: background .2s, color .2s, box-shadow .2s, border .2s;
}
.v-tab:hover { background: #f8fafc; }
.v-tab.active { background: #eef2ff; color: #3538cd; border-color: #e0e7ff; box-shadow: 0 3px 10px rgba(53,56,205,0.08); }

/* Panel */
.v-panel { padding: 18px 20px; }

/* Panel title */
.panel-title { margin: 4px 0 12px; font-size: 16px; font-weight: 700; }

/* Subsections */
.subsection { margin-top: 18px; }
.sub-title { margin: 0 0 8px; font-size: 14px; font-weight: 700; color: #111827; }

/* Meta grid */
.meta-grid { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 12px; }
.meta-item { border: 1px solid #f1f1f1; border-radius: 10px; padding: 10px 12px; background: #fff; }
.meta-label {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: #6b7280; margin-bottom: 6px;
}
.meta-value { font-size: 14px; color: #111827; word-break: break-word; }
.monospace { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }

/* Key-value grids */
.kv-grid { display: grid; grid-template-columns: 1fr; gap: 8px; }
.kv-row { display: grid; grid-template-columns: 200px 1fr; gap: 8px; padding: 8px 10px; border: 1px solid #f5f5f5; border-radius: 8px; }
.kv-key { color: #6b7280; font-size: 13px; }
.kv-val { color: #111827; font-size: 14px; white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word; }

/* Lists for groups/visits */
.list-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 10px; }
.list-card { border: 1px solid #f1f1f1; border-radius: 12px; padding: 10px; background: #fff; }
.list-card .kv-row {
  display: grid;
  grid-template-columns: minmax(120px, 220px) 1fr; /* let label shrink/grow */
  gap: 8px;
  align-items: start;
}

/* Docs */
.doc-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.doc-item { border: 1px solid #f1f1f1; border-radius: 12px; padding: 12px; background: #fff; }
.doc-name { font-weight: 600; }
.doc-meta { font-size: 12px; margin: 6px 0 10px; }

/* Team */
.team-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.team-card { border: 1px solid #f1f1f1; border-radius: 12px; padding: 12px; background: #fff; }
.team-name { font-weight: 700; }
.team-role { margin-top: 2px; color: #6b7280; }
.team-contact { margin-top: 8px; }
.contact-row { display: flex; gap: 6px; font-size: 14px; }
.contact-row .label { color: #6b7280; }

/* Buttons */
.btn-primary {
  border-radius: 10px; padding: 10px 12px; font-size: 14px; cursor: pointer;
  transition: transform .05s, box-shadow .2s, background .2s, color .2s, border .2s;
  border: 1px solid transparent; background: #111827; color: #fff;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(0,0,0,.1); }
.btn-minimal {
  background: none; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 8px 12px; font-size: 14px; color: #555; cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}
.btn-minimal:hover { background: #e8e8e8; color: #000; border-color: #d6d6d6; }
.edit-row { margin-top: 16px; }

/* Empty */
.empty-state { color: #6b7280; }

@media (max-width: 520px) {
  .list-card .kv-row {
    grid-template-columns: 1fr;
  }
  .list-card .kv-key {
    margin-bottom: 4px;
  }
}

/* Responsive */
@media (max-width: 980px) {
  .card { grid-template-columns: 200px 1fr; }
}
@media (max-width: 760px) {
  .card { grid-template-columns: 1fr; }
  .v-tabs { flex-direction: row; border-right: 0; border-bottom: 1px solid #f0f0f6; }
  .v-tab { flex: 1; text-align: center; }
  .meta-grid { grid-template-columns: 1fr; }
  .kv-row { grid-template-columns: 140px 1fr; }
}
</style>
