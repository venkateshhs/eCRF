<template>
  <div :class="['dashboard-layout', { collapsed: sidebarCollapsed, 'import-open': showImportData }]">
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
      <!-- IMPORT STUDY (DATA) embedded in Dashboard -->
      <div v-if="$route.name === 'Dashboard' && showImportData">
        <div :class="['import-overlay', { maximized: importMaximized }]">
          <div class="import-overlay-header">
            <div class="import-overlay-left">
              <button class="btn-minimal" @click="closeImportData">
              <span>Back</span>
            </button>
            </div>

            <div class="import-overlay-center">
              <div class="import-overlay-title">Import Study (Data)</div>
              <div class="import-overlay-subtitle">
                Upload a CSV or Excel file and map columns to create a study and import entries (template first, then data).
              </div>
            </div>

            <div class="import-overlay-right">
              <button
                class="btn-minimal icon-only"
                @click="toggleImportMaximize"
                :title="importMaximized ? 'Exit full screen' : 'Full screen'"
                aria-label="Toggle full screen"
              >
                <i
                  :class="importMaximized ? icons.compress : icons.expand"
                  aria-hidden="true"
                ></i>
              </button>
            </div>
          </div>

          <div class="import-overlay-content">
            <ImportStudy />
          </div>
        </div>
      </div>

      <!-- Dashboard home: Study Management -->
      <div v-else-if="$route.name === 'Dashboard' && activeSection === 'study-management'">
        <div class="study-management-header">
          <h1 class="study-management-title">Study Management</h1>
          <p class="study-management-subtitle">
            Create a new study, import data, or open an existing one to manage and collect data.
          </p>
        </div>

        <!-- Primary Actions -->
        <div v-if="!showStudyOptions">
          <!-- Cards -->
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
              @click="openImportData"
            >
              <span class="action-card-title">Import Study (Data)</span>
              <span class="action-card-desc">Ingest participant data from CSV/Excel</span>
            </button>
          </div>

          <!-- Wide buttons -->
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
              @click="openImportData"
              class="btn-primary"
            >
              Import Study (Data)
            </button>
          </div>
        </div>

        <!-- Existing Studies Table -->
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
import ImportStudy from "@/components/ImportStudy.vue";

export default {
  name: "DashboardComponent",
  components: { ImportStudy },
  data() {
    return {
      sidebarCollapsed: false,
      activeSection: "study-management",
      showStudyOptions: false,
      studies: [],
      icons,
      actionStyle: "cards",
      openMenuId: null,

      showImportData: false,
      importMaximized: false,
    };
  },
  watch: {
    "$route.query.openStudies"(val) {
      if (this.showImportData) return;

      if (val === "true") {
        this.activeSection = "study-management";
        this.showStudyOptions = true;
        this.loadStudies();
      } else {
        this.activeSection = "study-management";
        this.showStudyOptions = false;
      }
    },
    "$route.name"() {
      this.syncFromRoute();
    },
    "$route.query.view"() {
      this.syncFromRoute();
    },
    // keep: optional global lock, but now we also fix the real cause (grid shrink)
    showImportData(val) {
      this.setPageNoXScroll(!!val);
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
    isInvestigator() {
      return this.role === "Investigator";
    },
  },
  methods: {
    setPageNoXScroll(on) {
      document.documentElement.classList.toggle("no-x-scroll", on);
      document.body.classList.toggle("no-x-scroll", on);
    },

    syncFromRoute() {
      if (this.$route.name !== "Dashboard") return;

      const view = String(this.$route.query.view || "");
      if (view === "import-data") {
        this.showImportData = true;
        this.showStudyOptions = false;
        this.activeSection = "study-management";
        return;
      }

      this.showImportData = false;
      this.importMaximized = false;
      this.activeSection = "study-management";

      const openStudies = String(this.$route.query.openStudies || "false");
      if (openStudies === "true") {
        this.showStudyOptions = true;
        this.loadStudies();
      } else {
        this.showStudyOptions = false;
      }
    },

    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
    },

    async setActiveSection(section) {
      await this.$router.push({ name: "Dashboard" });
      this.activeSection = section;
      this.showStudyOptions = false;
      this.showImportData = false;
      this.importMaximized = false;
    },

    toggleStudyOptions() {
      this.showStudyOptions = !this.showStudyOptions;
      this.showImportData = false;
      this.importMaximized = false;

      if (this.showStudyOptions) {
        this.$router.push({ name: "Dashboard", query: { openStudies: "true" } });
        this.loadStudies();
      } else {
        this.$router.push({ name: "Dashboard", query: { openStudies: "false" } });
      }
    },

    openImportData() {
      this.openMenuId = null;
      this.showStudyOptions = false;
      this.showImportData = true;
      this.importMaximized = false;
      this.$router.push({ name: "Dashboard", query: { view: "import-data" } });
    },

    closeImportData() {
      this.showImportData = false;
      this.importMaximized = false;
      this.$router.push({ name: "Dashboard", query: { openStudies: "false" } });
    },

    toggleImportMaximize() {
      this.importMaximized = !this.importMaximized;
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
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    },

    addData(study) {
      this.$router.push({ name: "StudyDetail", params: { id: study.id } });
    },
    viewStudy(study) {
      this.$router.push({ name: "StudyView", params: { id: study.id } });
    },

    navigate(to) {
      this.activeSection = "";
      this.showImportData = false;
      this.importMaximized = false;
      this.$router.push(to);
    },

    logout() {
      this.$store.commit("setUser", null);
      this.$store.commit("setToken", null);
      this.$router.push("/login");
    },

    toggleRowMenu(id) {
      this.openMenuId = this.openMenuId === id ? null : id;
    },
    handleDocClick(e) {
      if (!this.$el.contains(e.target)) {
        this.openMenuId = null;
      } else {
        const btn = e.target.closest(".icon-ellipsis");
        const dd = e.target.closest(".menu-dropdown");
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
    document.addEventListener("click", this.handleDocClick, true);
    this.syncFromRoute();
    this.setPageNoXScroll(!!this.showImportData);

    if (this.$route.path === "/dashboard" && this.$route.name === "Dashboard") {
      this.activeSection = "study-management";
    }
  },
  beforeUnmount() {
    document.removeEventListener("click", this.handleDocClick, true);
    this.setPageNoXScroll(false);
  },
};
</script>

<style scoped>
/* page-level horizontal scroll lock when import overlay open */
:global(html.no-x-scroll),
:global(body.no-x-scroll) {
  overflow-x: hidden !important;
}

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

.logo-container img {
  width: 110px;
}

/* User area */
.user-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-identity {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.2;
}
.user-name {
  font-weight: 600;
  font-size: 14px;
  color: #222;
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-role {
  font-size: 12px;
  color: #666;
}

/* Sidebar */
.dashboard-sidebar {
  grid-area: sidebar;
  background: #f9f9f9;
  padding: 20px;
  border-right: 1px solid #e0e0e0;
  transition: width 0.3s ease, padding 0.3s ease;
}
.dashboard-sidebar.collapsed {
  width: 70px;
  padding: 10px;
}

.hamburger-menu {
  background: none;
  border: none;
  padding: 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.hamburger-menu span {
  display: block;
  width: 20px;
  height: 2px;
  background: #333;
  transition: all 0.3s ease;
}
.hamburger-menu:hover span {
  background: #000;
}

/* Sidebar Navigation */
.dashboard-sidebar nav ul {
  list-style: none;
  padding: 0;
}
.nav-item {
  padding: 10px;
  font-size: 15px;
  color: #555;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.3s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}
.nav-item:hover {
  background: #e8e8e8;
}

/* Main Content */
.dashboard-main {
  grid-area: main;
  padding: 30px;
  background: #fff;
  transition: margin-left 0.3s ease;

  /* allow grid item to shrink; prevents wide tables from expanding whole page */
  min-width: 0;
}
.dashboard-main.expanded {
  margin-left: -150px;
}

/* Study Management Heading + Subtitle (centered) */
.study-management-header {
  text-align: center;
  margin-bottom: 18px;
}
.study-management-title {
  margin: 0 0 6px 0;
  color: #333;
}
.study-management-subtitle {
  margin: 0 auto;
  color: #666;
  font-size: 14px;
}

/* Primary Actions — Cards (VERTICAL) */
.primary-actions-cards {
  display: grid;
  grid-template-columns: minmax(260px, 520px);
  justify-content: center;
  gap: 18px;
  margin-top: 20px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 18px 20px;
  background: #fafafa;
  border: 1px solid #e3e3e3;
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  transition: transform 0.06s ease, box-shadow 0.2s ease, border-color 0.2s ease,
    background 0.2s ease;
}

/* force desc visible even if some global CSS is hiding it */
.action-card-title {
  display: block !important;
  font-size: 16px;
  font-weight: 600;
  color: #222;
  line-height: 1.3;
}
.action-card-desc {
  display: block !important;
  font-size: 13px;
  color: #666;
  line-height: 1.35;
  white-space: normal !important;
  opacity: 1 !important;
  visibility: visible !important;
}

.action-card:hover {
  background: #f5f5f5;
  border-color: #dcdcdc;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}
.action-card:active {
  transform: translateY(1px);
}

/* Primary Actions — Wide Buttons */
.button-container {
  display: flex;
  gap: 16px;
  margin-top: 20px;
  justify-content: center;
  flex-wrap: wrap;
}
.btn-primary {
  min-width: 260px;
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
  box-shadow: 0 2px 10px rgba(47, 111, 237, 0.25);
}
.btn-primary:active {
  transform: translateY(1px);
}

/* Study Dashboard Styles */
.study-dashboard {
  margin-top: 22px;
}

.back-header-row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
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
  text-align: center;
}

/* Table */
.study-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 15px;
}
.study-table th,
.study-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e8e8e8;
}
.study-table td {
  color: #333;
}
.study-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #555;
}
.study-table tr:hover {
  background-color: #f9f9f9;
}

/* Actions column */
.actions-cell .action-buttons {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  min-width: 180px;
  max-width: 240px;
}
.action-buttons .btn-equal {
  width: 100%;
  justify-content: center;
  text-align: center;
}

/* menu column */
.study-table th.menu-col,
.study-table td.menu-cell {
  width: 56px;
  text-align: right;
}

/* 3-dot icon + dropdown */
.row-menu-wrap {
  position: relative;
  display: inline-block;
}
.icon-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  width: 36px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}
.icon-ellipsis:hover {
  background: #f3f4f6;
  border-color: #d6d6d6;
}
.icon-ellipsis i {
  font-size: 14px;
  color: #555;
}
.menu-dropdown {
  position: absolute;
  right: 0;
  top: 40px;
  min-width: 160px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
  padding: 6px;
  z-index: 5;
}
.menu-item {
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 14px;
  color: #111827;
  cursor: pointer;
}
.menu-item:hover {
  background: #f3f4f6;
}

/* Uniform minimal button */
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
  gap: 8px;
}
.btn-minimal:hover {
  background: #e8e8e8;
  color: #000;
  border-color: #d6d6d6;
}
.btn-minimal.icon-only {
  padding: 8px 10px;
}
.btn-minimal.icon-only i {
  font-size: 14px;
}

/* =========================
   IMPORT OVERLAY (scroll + full screen)
   ========================= */
.import-overlay {
  display: flex;
  flex-direction: column;

  height: calc(100vh - 70px - 60px);
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 25px rgba(16, 24, 40, 0.06);
  overflow: hidden;

  max-width: 100%;
  min-width: 0;
  width: 100%;
}

.import-overlay.maximized {
  position: fixed;
  inset: 0;
  z-index: 9999;
  height: 100vh;
  border-radius: 0;
  border: none;
  box-shadow: none;
}

.import-overlay-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: grid;

  /* prevents center content from expanding the whole header width */
  grid-template-columns: minmax(0, 1fr) minmax(0, 720px) minmax(0, 1fr);

  align-items: center;
  padding: 10px 12px;
}

.import-overlay-left {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
}

/* two-line title/subtitle */
.import-overlay-center {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-width: 0;
  text-align: center;
  gap: 2px;
}

.import-overlay-right {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  min-width: 0;
}

.import-overlay-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.import-overlay-subtitle {
  display: block;
  font-size: 12px;
  color: #6b7280;
  max-width: 720px;
  line-height: 1.3;
  padding: 0 8px;
  white-space: normal; /* allow wrap */
}

.import-overlay-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px;

  max-width: 100%;
  min-width: 0;
}

/* Ensure embedded ImportStudy respects container width */
.import-overlay-content :deep(.import-study) {
  max-width: none;
  width: 100%;
  margin: 0;
  min-width: 0;
}

/* Defensive */
.import-overlay-content :deep(table) {
  max-width: 100%;
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-layout {
    grid-template-columns: 70px 1fr;
  }
  .dashboard-sidebar {
    width: 70px;
  }
  .dashboard-main {
    padding: 20px;
  }
  .user-name {
    max-width: 160px;
  }
  .import-overlay {
    height: calc(100vh - 70px - 40px);
  }
}
</style>
