<template>
  <div class="dashboard-layout">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="logo-container">
        <img src="../assets/Logo_CaseE.png" alt="Logo" class="logo" />
      </div>

      <div class="user-actions">
        <div class="user-identity">
          <div class="user-name" :title="userName">{{ userName }}</div>
          <div class="user-role" :title="role || '—'">{{ role || '—' }}</div>
        </div>
        <button @click="logout" class="btn-minimal">Logout</button>
      </div>
    </header>

    <!-- Sidebar -->
    <aside :class="['dashboard-sidebar', { collapsed: sidebarCollapsed }]">
      <button class="hamburger-menu" @click="toggleSidebar">
        <span></span>
        <span></span>
        <span></span>
      </button>
      <nav>
        <ul>
          <!-- Study Management: only Admin, PI or Investigator -->
          <li
            v-if="isAdmin || isPI || isInvestigator"
            @click="setActiveSection('study-management')"
            class="nav-item"
          >
            <i :class="icons.book" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">Study Management</span>
          </li>
          <!-- User Management: visible to all roles -->
          <li
            @click="() => { setActiveSection(''); navigate('/dashboard/user-info') }"
            class="nav-item"
          >
            <i :class="icons.user" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">User Management</span>
          </li>
        </ul>
      </nav>
    </aside>

    <!-- Main Content -->
    <main :class="['dashboard-main', { expanded: sidebarCollapsed }]">
      <div v-if="$route.name === 'Dashboard' && activeSection === 'study-management'">
        <!-- Centered Heading + Subtitle -->
        <div class="study-management-header">
          <h1 class="study-management-title">Study Management</h1>
          <p class="study-management-subtitle">
            Create a new study, import a template, or open an existing one to manage and collect data.
          </p>
        </div>

        <!-- Primary Actions (hidden when showing Existing Studies) -->
        <div v-if="!showStudyOptions">
          <!-- STYLE 1: Large Cards (default) -->
          <div v-if="actionStyle === 'cards'" class="primary-actions-cards">
            <button
              v-if="isAdmin || isPI"
              class="action-card"
              @click="navigate('/dashboard/create-study')"
            >
              <span class="action-card-title">Create Study</span>
              <span class="action-card-desc">Start a new protocol and forms</span>
            </button>

            <button
              v-if="isAdmin || isPI || isInvestigator"
              class="action-card"
              @click="toggleStudyOptions"
            >
              <span class="action-card-title">Open Existing Study</span>
              <span class="action-card-desc">Continue work on an existing study</span>
            </button>

            <button
              v-if="isAdmin || isPI || isInvestigator"
              class="action-card"
              @click="navigate('/dashboard/import-study')"
            >
              <span class="action-card-title">Import Study (Data)</span>
              <span class="action-card-desc">Ingest participant data from CSV/Excel</span>
            </button>

            <!-- NEW: Import Study Template (template only, no data) -->
            <button
              v-if="isAdmin || isPI"
              class="action-card"
              @click="navigate('/dashboard/import-study-template')"
            >
              <span class="action-card-title">Import Study Template</span>
              <span class="action-card-desc">Template only (no data). Use JSON exported from another device.</span>
            </button>
          </div>

          <!-- STYLE 2: Wide Buttons -->
          <div v-else class="button-container">
            <button
              v-if="isAdmin || isPI"
              @click="navigate('/dashboard/create-study')"
              class="btn-primary"
            >
              Create Study
            </button>

            <button
              v-if="isAdmin || isPI || isInvestigator"
              @click="toggleStudyOptions"
              class="btn-primary"
            >
              Open Existing Study
            </button>

            <button
              v-if="isAdmin || isPI || isInvestigator"
              @click="navigate('/dashboard/import-study')"
              class="btn-primary"
            >
              Import Study (Data)
            </button>

            <!-- NEW wide button -->
            <button
              v-if="isAdmin || isPI"
              @click="navigate('/dashboard/import-study-template')"
              class="btn-primary"
            >
              Import Study Template
            </button>
          </div>
        </div>

        <!-- Study Dashboard Table -->
        <div v-if="showStudyOptions" class="study-dashboard">
          <div class="back-header-row">
            <div class="back-button-container">
              <button @click="toggleStudyOptions" class="btn-minimal">Back</button>
            </div>
            <h2 class="existing-studies-title">Existing Studies</h2>
          </div>

          <table class="study-table">
            <thead>
              <tr>
                <th>Study Name</th>
                <th>Description</th>
                <th>Created At</th>
                <th>Updated At</th>
                <th>Actions</th>
                <th class="menu-col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="study in studies" :key="study.id">
                <td>{{ study.study_name }}</td>
                <td>{{ study.study_description }}</td>
                <td>{{ formatDateTime(study.created_at) }}</td>
                <td>{{ formatDateTime(study.updated_at) }}</td>

                <!-- Actions: vertical buttons -->
                <td class="actions-cell">
                  <div class="action-buttons">
                    <button
                      v-if="isAdmin || isPI || isInvestigator"
                      @click="addData(study)"
                      class="btn-minimal btn-equal"
                    >
                      Add Data
                    </button>
                    <button
                      v-if="isAdmin || isPI || isInvestigator"
                      @click="viewStudy(study)"
                      class="btn-minimal btn-equal"
                    >
                      View Study
                    </button>
                  </div>
                </td>
                <td class="menu-cell">
                  <div class="row-menu-wrap">
                    <button
                      class="icon-ellipsis"
                      @click.stop="toggleRowMenu(study.id)"
                      :aria-expanded="openMenuId === study.id ? 'true' : 'false'"
                      aria-haspopup="menu"
                      :aria-label="`More actions for ${study.study_name}`"
                    >
                      <i :class="icons.ellipsis" aria-hidden="true"></i>
                    </button>

                    <div
                      v-if="openMenuId === study.id"
                      class="menu-dropdown"
                      role="menu"
                    >
                      <button class="menu-item" role="menuitem" @click="handleExportStudy(study)">
                        Export Study Template
                      </button>
                      <button class="menu-item" role="menuitem" @click="handleDownloadStudy(study)">
                        Download Study (ZIP)
                      </button>
                      <button class="menu-item" role="menuitem" @click="handleMergeStudy(study)">
                        Merge study
                      </button>
                    </div>
                  </div>
                </td>

              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <router-view/>
    </main>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";
import { downloadStudyBundle } from "@/utils/studyDownload";

export default {
  name: "DashboardComponent",
  data() {
    return {
      sidebarCollapsed: false,
      activeSection: "study-management",
      showStudyOptions: false,
      studies: [],
      icons,
      actionStyle: 'cards',
      openMenuId: null,
    };
  },
  watch: {
    '$route.query.openStudies'(val) {
      if (val === 'true') {
        this.activeSection = 'study-management';
        this.showStudyOptions = true;
        this.loadStudies();
      } else {
        this.activeSection = 'study-management';
        this.showStudyOptions = false;
      }
    }
  },
  computed: {
    currentUser() {
      return this.$store.getters.getUser || {};
    },
    role() {
      return this.currentUser.profile?.role || "";
    },
    // Graceful username fallback chain
    userName() {
      const p = this.currentUser.profile || {};
      const firstLast = [p.first_name, p.last_name].filter(Boolean).join(" ").trim();
      return (
        p.name ||
        p.full_name ||
        firstLast ||
        this.currentUser.username ||
        this.currentUser.email ||
        "User"
      );
    },
    isAdmin() {
      return this.role === "Administrator";
    },
    isPI() {
      return this.role === "Principal Investigator";
    },
    isInvestigator() { return this.role === "Investigator"; },
  },
  methods: {
    toggleSidebar() { this.sidebarCollapsed = !this.sidebarCollapsed; },
    async setActiveSection(section) {
      await this.$router.push({ name: "Dashboard" });
      this.activeSection = section;
      this.showStudyOptions = false;
    },
    toggleStudyOptions() {
      this.showStudyOptions = !this.showStudyOptions;
      if (this.showStudyOptions) {
        this.$router.push({ name: "Dashboard", query: { openStudies: "true" } });
        this.loadStudies();
      } else {
        this.$router.push({ name: "Dashboard", query: { openStudies: "false" } });
      }
    },
    async loadStudies() {
      const token = this.$store.state.token;
      if (!token) {
        alert("Please log in again.");
        return this.$router.push("/login");
      }
      try {
        const { data } = await axios.get("/forms/studies", {
          headers: { Authorization: `Bearer ${token}` },
        });
        this.studies = data;
      } catch (e) {
        console.error('Failed to load studies:', e);
        if (e.response?.status === 401) {
          alert("Session expired.");
          this.$router.push("/login");
        } else {
          alert("Failed to load studies.");
        }
      }
    },
    formatDateTime(d) {
      if (!d) return "";
      return new Date(d).toLocaleString("en-GB", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
    },
    // Keeping editStudy method for compatibility, but no button on dashboard
    async editStudy(study) {
      localStorage.removeItem("setStudyDetails");
      localStorage.removeItem("scratchForms");
      const token = this.$store.state.token;
      if (!token) {
        alert("Please log in again.");
        return;
      }
      try {
        const resp = await axios.get(
          `/forms/studies/${study.id}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const sd = resp.data.content?.study_data;
        const meta = resp.data.metadata || {};
        if (!sd) {
          alert("Study content is empty.");
          return;
        }

        // Initialize assignments
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
          assignmentMethod: sd.assignmentMethod || 'random',
          subjects: sd.subjects || [],
          assignments: assignments,
          forms: sd.selectedModels ? [{
            sections: sd.selectedModels.map(model => ({
              title: model.title,
              fields: model.fields,
              source: 'template'
            }))
          }] : []
        });

        if (sd.selectedModels) {
          const scratchForms = [{
            sections: sd.selectedModels.map(model => ({
              title: model.title,
              fields: model.fields,
              source: 'template'
            }))
          }];
          localStorage.setItem("scratchForms", JSON.stringify(scratchForms));
        }

        this.activeSection = "";
        this.$router.push({ name: "CreateStudy", params: { id: study.id } });
      } catch (e) {
        console.error('Failed to load study details:', e);
        alert("Failed to load study details.");
      }
    },
    addData(study) { this.$router.push({ name: "StudyDetail", params: { id: study.id } }); },
    viewStudy(study) { this.$router.push({ name: "StudyView", params: { id: study.id } }); },
    navigate(to) { this.activeSection = ""; this.$router.push(to); },
    logout() {
      this.$store.commit("setUser", null);
      this.$store.commit("setToken", null);
      this.$router.push("/login");
    },

    // --- 3-dot menu handlers (separate column) ---
    toggleRowMenu(id) { this.openMenuId = this.openMenuId === id ? null : id; },
    handleDocClick(e) {
      if (!this.$el.contains(e.target)) {
        this.openMenuId = null;
      } else {
        const btn = e.target.closest('.icon-ellipsis');
        const dd  = e.target.closest('.menu-dropdown');
        if (!btn && !dd) this.openMenuId = null;
      }
    },
    handleExportStudy(study) {
      this.openMenuId = null;
      this.$router.push(`/dashboard/export-study/${study.id}`);
    },
    handleMergeStudy(study) {
      this.openMenuId = null;
      this.$router.push(`/dashboard/merge-study/${study.id}`);
    },
    async handleDownloadStudy(study) {
      this.openMenuId = null;
      const token = this.$store.state.token;
      if (!token) {
        alert("Please log in again.");
        this.$router.push("/login");
        return;
      }
      try {
        await downloadStudyBundle({ studyId: study.id, token });
      } catch (e) {
        console.error("Failed to download study bundle:", e);
        alert("Failed to download study bundle.");
      }
    },
  },
  mounted() {
    if (this.$route.path === "/dashboard") {
      this.activeSection = "study-management";
      this.showStudyOptions = false;
    }
    if (this.$route.query.openStudies === 'true') {
      this.activeSection = 'study-management';
      this.showStudyOptions = true;
      this.loadStudies();
    }
    document.addEventListener('click', this.handleDocClick, true);
  },
  beforeUnmount() {
    document.removeEventListener('click', this.handleDocClick, true);
  },
};
</script>

<style scoped>
.dashboard-layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main";
  grid-template-rows: 70px 1fr;
  grid-template-columns: 220px 1fr;
  height: 100vh;
  font-family: "Inter", sans-serif;
  transition: grid-template-columns 0.3s ease;
}

.dashboard-header {
  grid-area: header;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.logo-container img { width: 110px; }

/* User area */
.user-actions { display: flex; align-items: center; gap: 12px; }
.user-identity { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.2; }
.user-name { font-weight: 600; font-size: 14px; color: #222; max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { font-size: 12px; color: #666; }
.user-actions .btn-minimal {
  background: none; border: 1px solid #e0e0e0; font-size: 14px; color: #555; cursor: pointer; padding: 8px 12px; border-radius: 6px;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}
.user-actions .btn-minimal:hover { background: #eaeaea; color: #000; border-color: #d6d6d6; }

/* Sidebar */
.dashboard-sidebar { grid-area: sidebar; background: #f9f9f9; padding: 20px; border-right: 1px solid #e0e0e0; transition: width 0.3s ease, padding 0.3s ease; }
.dashboard-sidebar.collapsed { width: 70px; padding: 10px; }

.hamburger-menu { background: none; border: none; padding: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.hamburger-menu span { display: block; width: 20px; height: 2px; background: #333; transition: all 0.3s ease; }
.hamburger-menu:hover span { background: #000; }

/* Sidebar Navigation */
.dashboard-sidebar nav ul { list-style: none; padding: 0; }
.nav-item {
  padding: 10px; font-size: 15px; color: #555; cursor: pointer; border-radius: 6px; transition: background 0.3s ease; display: flex; align-items: center; gap: 10px;
}
.nav-item:hover { background: #e8e8e8; }

/* Main Content */
.dashboard-main { grid-area: main; padding: 30px; background: #fff; transition: margin-left 0.3s ease; }
.dashboard-main.expanded { margin-left: -150px; }

/* Study Management Heading + Subtitle (centered) */
.study-management-header { text-align: center; margin-bottom: 18px; }
.study-management-title { margin: 0 0 6px 0; color: #333; }
.study-management-subtitle { margin: 0 auto; color: #666; font-size: 14px; }

/* Primary Actions — Style 1: Cards */
.primary-actions-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 360px));
  justify-content: center; /* center the grid */
  gap: 18px;
  margin-top: 20px;
}
.action-card {
  display: flex; flex-direction: column; gap: 6px;
  padding: 18px 20px; background: #fafafa; border: 1px solid #e3e3e3; border-radius: 12px; cursor: pointer; text-align: left;
  transition: transform 0.06s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}
.action-card:hover { background: #f5f5f5; border-color: #dcdcdc; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
.action-card:active { transform: translateY(1px); }
.action-card-title { font-size: 16px; font-weight: 600; color: #222; }
.action-card-desc { font-size: 13px; color: #666; }

/* Primary Actions — Style 2: Wide Buttons */
.button-container {
  display: flex;
  gap: 16px;
  margin-top: 20px;
  justify-content: center;   /* centered horizontally */
  flex-wrap: wrap;
}

.btn-primary {
  min-width: 260px;            /* elongated */
  padding: 14px 24px;
  background: #2f6fed;
  border: 1px solid #245fe0;
  border-radius: 10px;
  font-size: 16px;
  color: #fff;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.02s ease, box-shadow 0.2s ease;
}

.btn-primary:hover {
  background: #285fce;
  box-shadow: 0 2px 10px rgba(47,111,237,0.25);
}

.btn-primary:active {
  transform: translateY(1px);
}

/* Study Dashboard Styles */
.study-dashboard { margin-top: 22px; }

/* Back + centered title row */
.back-header-row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center; /* centers the title regardless of back width */
  min-height: 42px;
  margin-bottom: 12px;
}

.back-button-container {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
}

.existing-studies-title {
  margin: 0;
  font-size: 20px;
  color: #333;
  text-align: center; /* ensure centered text */
}

/* Table */
.study-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
.study-table th,
.study-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e8e8e8;
}

/* Uniform text color for all data cells */
.study-table td { color: #333; }
.study-table th { background: #f5f5f5; font-weight: 600; color: #555; }
.study-table tr:hover { background-color: #f9f9f9; }

/* Actions column: vertical buttons */
.actions-cell .action-buttons {
  display: flex; flex-direction: column; align-items: stretch; gap: 8px; min-width: 180px; max-width: 240px;
}
.action-buttons .btn-equal {
  width: 100%;
  justify-content: center;
  text-align: center;
}

/* Unnamed menu column (rightmost) */
.study-table th.menu-col,
.study-table td.menu-cell {
  width: 56px;
  text-align: right;
}

/* 3-dot icon + dropdown */
.row-menu-wrap { position: relative; display: inline-block; }
.icon-ellipsis {
  display: inline-flex; align-items: center; justify-content: center; height: 34px; width: 36px;
  border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; cursor: pointer; transition: background 0.2s ease, border-color 0.2s ease;
}
.icon-ellipsis:hover {
  background: #f3f4f6;
  border-color: #d6d6d6;
}
.icon-ellipsis i { font-size: 14px; color: #555; }
.menu-dropdown {
  position: absolute; right: 0; top: 40px; min-width: 160px; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.08); padding: 6px; z-index: 5;
}
.menu-item {
  width: 100%; text-align: left; background: none; border: none; padding: 8px 10px; border-radius: 6px; font-size: 14px; color: #111827; cursor: pointer;
}
.menu-item:hover { background: #f3f4f6; }

/* Minimalistic Button Style */
.btn-minimal {
  background: none; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px 12px; font-size: 14px; color: #555; cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease; display: inline-flex; align-items: center; gap: 5px;
}
.btn-minimal:hover { background: #e8e8e8; color: #000; border-color: #d6d6d6; }

/* Responsive */
@media (max-width: 900px) { .primary-actions-cards { grid-template-columns: minmax(260px, 1fr); } }
.action-buttons .btn-equal { min-width: 130px; }
@media (max-width: 768px) {
  .dashboard-layout { grid-template-columns: 70px 1fr; }
  .dashboard-sidebar { width: 70px; }
  .dashboard-main { padding: 20px; }
  .user-name { max-width: 160px; }
}
</style>
