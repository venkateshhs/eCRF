<template>
  <div
    :class="[
      'dashboard-layout',
      {
        collapsed: sidebarCollapsed && !hideSidebar,
        'import-open': showImportData,
        'sidebar-hidden': hideSidebar
      }
    ]"
  >
    <!-- Header -->
    <header class="dashboard-header">
      <div class="logo-container">
        <!-- Make logo clickable and route to /dashboard -->
        <img
          src="../assets/Logo_CaseE.png"
          alt="Logo"
          class="logo"
          role="button"
          tabindex="0"
          @click="goToDashboardHome"
          @keydown.enter.prevent="goToDashboardHome"
          @keydown.space.prevent="goToDashboardHome"
        />
      </div>

      <div class="user-actions">
        <div class="user-identity">
          <div class="user-name" :title="userName">{{ userName }}</div>
          <div class="user-role" :title="role || '—'">{{ role || '—' }}</div>
        </div>
        <button type="button" @click="logout" class="btn-minimal">Logout</button>
      </div>
    </header>

    <!-- Sidebar (HIDDEN for View Study + Add Data + Scratch Form) -->
    <aside v-if="!hideSidebar" :class="['dashboard-sidebar', { collapsed: sidebarCollapsed }]">
      <button type="button" class="hamburger-menu" @click="toggleSidebar" aria-label="Toggle sidebar">
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
            tabindex="0"
            @keydown.enter="setActiveSection('study-management')"
            @keydown.space.prevent="setActiveSection('study-management')"
          >
            <i :class="icons.book || 'fas fa-book'" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">Study Management</span>
          </li>

          <!-- User Management: visible to all roles -->
          <li
            @click="() => { setActiveSection(''); navigate({ name: 'UserInfo' }) }"
            class="nav-item"
            tabindex="0"
            @keydown.enter="() => { setActiveSection(''); navigate({ name: 'UserInfo' }) }"
            @keydown.space.prevent="() => { setActiveSection(''); navigate({ name: 'UserInfo' }) }"
          >
            <i :class="icons.user || 'fas fa-user'" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">User Management</span>
          </li>
        </ul>
      </nav>
    </aside>

    <!-- Main Content -->
    <main :class="['dashboard-main', { expanded: sidebarCollapsed && !hideSidebar }]">
      <!-- Only show Dashboard home content when you're actually ON Dashboard route -->
      <template v-if="$route.name === 'Dashboard'">
        <!-- IMPORT STUDY (DATA) embedded in Dashboard -->
        <div v-if="showImportData">
          <div :class="['import-overlay', { maximized: importMaximized }]">
            <div class="import-overlay-header">
              <div class="import-overlay-left">
                <button type="button" class="btn-minimal" @click="closeImportData">
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
                  type="button"
                  class="btn-minimal icon-only"
                  @click="toggleImportMaximize"
                  :title="importMaximized ? 'Exit full screen' : 'Full screen'"
                  aria-label="Toggle full screen"
                >
                  <i
                    :class="importMaximized ? (icons.compress || 'fas fa-compress') : (icons.expand || 'fas fa-expand')"
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
        <div v-else-if="activeSection === 'study-management'">
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
                type="button"
                class="action-card"
                @click="navigate({ name: 'CreateStudy' })"
              >
                <span class="action-card-title">Create Study</span>
                <span class="action-card-desc">Start a new protocol and forms</span>
              </button>

              <button
                v-if="isAdmin || isPI || isInvestigator"
                type="button"
                class="action-card"
                @click="toggleStudyOptions"
              >
                <span class="action-card-title">Open Existing Study</span>
                <span class="action-card-desc">Continue work on an existing study</span>
              </button>

              <button
                v-if="isAdmin || isPI || isInvestigator"
                type="button"
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
                type="button"
                @click="navigate({ name: 'CreateStudy' })"
                class="btn-primary"
              >
                Create Study
              </button>

              <button
                v-if="isAdmin || isPI || isInvestigator"
                type="button"
                @click="toggleStudyOptions"
                class="btn-primary"
              >
                Open Existing Study
              </button>

              <button
                v-if="isAdmin || isPI || isInvestigator"
                type="button"
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
                <button type="button" @click="toggleStudyOptions" class="btn-minimal">Back</button>
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
                </tr>
              </thead>
              <tbody>
                <tr v-for="study in studies" :key="study.id">
                  <td>
                    <span class="study-name-cell">
                      <span>{{ study.study_name }}</span>
                      <span v-if="isDraftStudy(study)" class="status-tag status-tag--draft">DRAFT</span>
                    </span>
                  </td>
                  <td>{{ study.study_description }}</td>
                  <td>{{ formatDateTime(study.created_at) }}</td>
                  <td>{{ formatDateTime(study.updated_at) }}</td>

                  <td class="actions-cell">
                    <div class="action-buttons">
                      <button
                          v-if="canAddData(study)"
                          type="button"
                          @click="handleAddDataClick(study)"
                          class="btn-minimal btn-equal"
                        >
                          Add Data
                        </button>
                        <button
                          v-if="canViewStudy(study)"
                          type="button"
                          @click="handleViewStudyClick(study)"
                          class="btn-minimal btn-equal"
                        >
                          View Study
                        </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <router-view v-else />

      <!-- Draft blocker / discard confirm dialog (custom) -->
      <div
        v-if="draftDialog.open"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        @click.self="closeDraftDialog"
      >
        <div class="modal">
          <div class="modal-header">
            <div class="modal-title">
              <template v-if="draftDialog.step === 'block'">
                {{ draftDialog.mode === 'add-data' ? 'Study setup is not finished' : 'Study is still a draft' }}
              </template>
              <template v-else>Discard draft study?</template>
            </div>
            <button class="modal-close" type="button" @click="closeDraftDialog" aria-label="Close dialog">×</button>
          </div>

          <div class="modal-body">
            <template v-if="draftDialog.step === 'block'">
              <p class="modal-lead">
                <strong>{{ draftDialog.study?.study_name || 'This study' }}</strong>
                hasn’t been finalized yet.
              </p>

              <p class="modal-text" v-if="draftDialog.mode === 'add-data'">
                You can’t add participant data until the study setup is completed (protocol, forms, and required
                settings). Finish the setup first, then come back to add data.
              </p>

              <p class="modal-text" v-else>
                This study is not finalized yet. You can finish the setup now, or open the study view anyway if you
                understand it may be incomplete.
              </p>

              <div class="modal-warning">
                <div class="modal-warning-title">Choose an option</div>
                <ul class="modal-warning-list">
                  <li><strong>Continue setup</strong> to complete the study creation.</li>
                  <li><strong>Discard draft</strong> to permanently delete this draft template.</li>
                  <li v-if="draftDialog.mode === 'view-study'">
                    <strong>View anyway</strong> to open the study view even if incomplete.
                  </li>
                </ul>
              </div>
            </template>

            <template v-else>
              <p class="modal-lead">
                You’re about to discard <strong>{{ draftDialog.study?.study_name || 'this draft study' }}</strong
                >.
              </p>
              <p class="modal-text">
                This will permanently delete the draft template and any configuration saved under it. This action cannot
                be undone.
              </p>
              <div class="modal-warning modal-warning--danger">
                <div class="modal-warning-title">Permanent action</div>
                <div class="modal-text" style="margin: 0">
                  If you still want to keep this study, click <strong>Go back</strong> and choose
                  <strong>Continue setup</strong>.
                </div>
              </div>
            </template>
          </div>

          <div class="modal-footer">
            <template v-if="draftDialog.step === 'block'">
              <button type="button" class="btn-minimal" @click="closeDraftDialog" :disabled="draftDialog.busy">
                Cancel
              </button>

              <button
                type="button"
                class="btn-minimal btn-danger"
                @click="goToDiscardConfirm"
                :disabled="draftDialog.busy"
              >
                Discard draft
              </button>

              <button type="button" class="btn-primary-solid" @click="continueStudyCreation" :disabled="draftDialog.busy">
                Continue setup
              </button>

              <button
                v-if="draftDialog.mode === 'view-study'"
                type="button"
                class="btn-primary-outline"
                @click="viewStudyAnyway"
                :disabled="draftDialog.busy"
              >
                View anyway
              </button>
            </template>

            <template v-else>
              <button type="button" class="btn-minimal" @click="draftDialog.step = 'block'" :disabled="draftDialog.busy">
                Go back
              </button>

              <button type="button" class="btn-minimal" @click="closeDraftDialog" :disabled="draftDialog.busy">
                Cancel
              </button>

              <button
                type="button"
                class="btn-primary-solid btn-danger-solid"
                @click="discardDraftStudy"
                :disabled="draftDialog.busy"
              >
                {{ draftDialog.busy ? 'Discarding…' : 'Yes, discard draft' }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";
import ImportStudy from "@/components/ImportStudy.vue";
import activityTracker from "@/utils/activityTracker";

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

      showImportData: false,
      importMaximized: false,

      // Draft-blocker dialog state
      draftDialog: {
        open: false,
        mode: "", // 'add-data' | 'view-study'
        step: "block", // 'block' | 'confirm-discard'
        study: null,
        busy: false,
      },
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
    showImportData(val) {
      this.setPageNoXScroll(!!val);
    },
  },
  computed: {
    // Hide dashboard sidebar on View Study + Add Data + Scratch Form
    hideSidebar() {
      return (
        this.$route.name === "StudyView" ||
        this.$route.name === "DashboardAddData" ||
        this.$route.name === "CreateFormScratch"
      );
    },

    currentUser() {
      return this.$store.getters.getUser || {};
    },
    role() {
      return this.currentUser.profile?.role || "";
    },
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
    // ---- Per-study permission helpers (uses backend `study.permissions`) ----
    studyPerms(study) {
      const p = study?.permissions;
      return p && typeof p === "object" ? p : null;
    },

    isStudyOwner(study) {
      // backend uses numeric created_by in StudyMetadataOut
      const createdBy = study?.created_by ?? null;
      const meId = this.currentUser?.id ?? this.currentUser?.user_id ?? null;
      if (createdBy == null || meId == null) return false;
      return String(createdBy) === String(meId);
    },

    canAddData(study) {
      // Owner/Admin: always show
      if (this.isAdmin || this.isStudyOwner(study)) return true;

      // Otherwise: only if permission says add_data
      const perms = this.studyPerms(study);
      return perms ? perms.add_data === true : false;
    },

    canViewStudy(study) {
      // Owner/Admin: always show
      if (this.isAdmin || this.isStudyOwner(study)) return true;

      // Otherwise: only if permission says view OR add_data (add implies view)
      const perms = this.studyPerms(study);
      return perms ? (perms.view === true || perms.add_data === true) : false;
    },

    setPageNoXScroll(on) {
      document.documentElement.classList.toggle("no-x-scroll", on);
      document.body.classList.toggle("no-x-scroll", on);
    },

    isDraftStudy(study) {
      if (!study) return false;

      // common flags first
      if (study.is_draft === true) return true;

      // status strings (case-insensitive)
      const status = String(study.status || "").trim().toUpperCase();
      return status === "DRAFT";
    },

    // Draft dialog control
    openDraftDialog(mode, study) {
      this.draftDialog.open = true;
      this.draftDialog.mode = mode;
      this.draftDialog.step = "block";
      this.draftDialog.study = study || null;
      this.draftDialog.busy = false;
    },
    closeDraftDialog() {
      // prevent closing during destructive delete
      if (this.draftDialog.busy) return;

      this.draftDialog.open = false;
      this.draftDialog.mode = "";
      this.draftDialog.step = "block";
      this.draftDialog.study = null;
      this.draftDialog.busy = false;
    },
    goToDiscardConfirm() {
      if (this.draftDialog.busy) return;
      this.draftDialog.step = "confirm-discard";
    },

    // Load study into store (same approach as your StudyView edit launcher)
    async loadStudyIntoStoreForEdit(studyId) {
      localStorage.removeItem("setStudyDetails");
      localStorage.removeItem("scratchForms");

      const token = this.$store.state.token;
      if (!token) {
        alert("Please log in again.");
        this.$router.push("/login");
        return false;
      }

      try {
        const resp = await axios.get(`/forms/studies/${studyId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        const sd = resp.data?.content?.study_data;
        const meta = resp.data?.metadata || {};

        if (!sd) {
          alert("Study content is empty.");
          return false;
        }

        let assignments = Array.isArray(sd.assignments) ? sd.assignments : [];
        if (!assignments.length && Array.isArray(sd.selectedModels) && sd.selectedModels.length) {
          const m = sd.selectedModels.length;
          const v = sd.visits?.length || 0;
          const g = sd.groups?.length || 0;
          assignments = Array.from({ length: m }, () =>
            Array.from({ length: v }, () => Array.from({ length: g }, () => false))
          );
        }

        const studyInfo = {
          id: meta.id,
          name: meta.study_name,
          description: meta.study_description,
          created_at: meta.created_at,
          updated_at: meta.updated_at,
          created_by: meta.created_by,
        };

        this.$store.commit("setStudyDetails", {
          study_metadata: studyInfo,
          study: { id: meta.id, ...(sd.study || {}) },
          groups: sd.groups || [],
          visits: sd.visits || [],
          subjectCount: sd.subjectCount || 0,
          assignmentMethod: sd.assignmentMethod || "random",
          subjects: sd.subjects || [],
          assignments: assignments,
          forms: Array.isArray(sd.selectedModels)
            ? [
                {
                  sections: sd.selectedModels.map((model) => ({
                    title: model.title,
                    fields: model.fields,
                    source: "template",
                  })),
                },
              ]
            : [],
        });

        if (Array.isArray(sd.selectedModels)) {
          const scratchForms = [
            {
              sections: sd.selectedModels.map((model) => ({
                title: model.title,
                fields: model.fields,
                source: "template",
              })),
            },
          ];
          localStorage.setItem("scratchForms", JSON.stringify(scratchForms));
        }

        return true;
      } catch (e) {
        console.error("Failed to load study details:", e);
        alert("Failed to load study details.");
        return false;
      }
    },

    // FIX: allow dialog to close after successful "Continue setup"
    async continueStudyCreation() {
      const s = this.draftDialog.study;
      if (!s?.id) return;

      this.draftDialog.busy = true;

      const ok = await this.loadStudyIntoStoreForEdit(s.id);
      if (!ok) {
        this.draftDialog.busy = false;
        return;
      }

      //  IMPORTANT FIX:
      // closeDraftDialog() blocks closing while busy, so drop busy first, then close.
      this.draftDialog.busy = false;
      this.closeDraftDialog();

      this.$router
        .push({
          name: "CreateStudy",
          params: { id: s.id },
          query: {
            mode: "edit",
            returnTo: "Dashboard",
            returnOpenStudies: "true",
          },
        })
        .catch(() => null);
    },

    viewStudyAnyway() {
      const s = this.draftDialog.study;
      this.closeDraftDialog();
      if (!s?.id) return;
      this.$router.push({ name: "StudyView", params: { id: s.id } }).catch(() => null);
    },

    async discardDraftStudy() {
      const s = this.draftDialog.study;
      if (!s?.id) return;

      const token = this.$store.state.token;
      if (!token) {
        alert("Please log in again.");
        this.closeDraftDialog();
        return this.$router.push("/login");
      }

      this.draftDialog.busy = true;

      try {
        // If your backend uses a different delete path, change ONLY this line.
        await axios.delete(`/forms/studies/${s.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        // Hard reset dialog so it never gets stuck
        this.draftDialog.open = false;
        this.draftDialog.mode = "";
        this.draftDialog.step = "block";
        this.draftDialog.study = null;
        this.draftDialog.busy = false;

        // Keep user in Existing Studies list
        await this.$router.push({ name: "Dashboard", query: { openStudies: "true" } }).catch(() => null);

        this.activeSection = "study-management";
        this.showImportData = false;
        this.importMaximized = false;
        this.showStudyOptions = true;

        await this.loadStudies();
      } catch (e) {
        console.error("Failed to discard draft study:", e);
        const msg =
          e?.response?.data?.detail || e?.response?.data?.message || "Failed to discard the draft. Please try again.";
        alert(msg);
        this.draftDialog.busy = false;
      }
    },

    handleAddDataClick(study) {
      if (this.isDraftStudy(study)) {
        this.openDraftDialog("add-data", study);
        return;
      }
      this.addData(study);
    },

    handleViewStudyClick(study) {
      if (this.isDraftStudy(study)) {
        this.openDraftDialog("view-study", study);
        return;
      }
      this.viewStudy(study);
    },

    // Logo click should always take user to /dashboard
    goToDashboardHome() {
      // no reload; just route to dashboard
      this.$router.push({ path: "/dashboard" }).catch(() => null);
    },

    syncFromRoute() {
      // Only apply dashboard home state sync when route is Dashboard itself
      if (this.$route.name !== "Dashboard") {
        // ensure overlay scroll lock never leaks into child routes
        this.showImportData = false;
        this.importMaximized = false;
        this.setPageNoXScroll(false);
        return;
      }

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
        console.error("Failed to load studies:", e);
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

    //  Add Data inside dashboard layout
    addData(study) {
      this.$router.push({ name: "DashboardAddData", params: { id: study.id } });
    },

    // View Study inside dashboard layout (already)
    viewStudy(study) {
      this.$router.push({ name: "StudyView", params: { id: study.id } });
    },

    // accepts either string path or route object
    navigate(to) {
      this.activeSection = "";
      this.showImportData = false;
      this.importMaximized = false;
      this.$router.push(to);
    },

    async logout(message) {
      console.log("[Dashboard] logout()", message || "");

      // stop tracker first to prevent any late pings racing with logout
      activityTracker.stop();

      const token =
        this.$store.state.token || localStorage.getItem("access_token");

      // Best-effort server revoke (do NOT block logout if this fails)
      try {
        if (token) {
          console.log("[Dashboard] calling POST /users/logout");
          await axios.post("/users/logout", null, {
            headers: { Authorization: `Bearer ${token}` },
          });
          console.log("[Dashboard] server session revoked");
        }
      } catch (e) {
        console.warn(
          "[Dashboard] /users/logout failed (ignoring):",
          e?.response?.status,
          e?.message
        );
      }

      if (message) alert(message);

      // clear local auth
      this.$store.commit("setUser", null);
      this.$store.commit("setToken", null);
      localStorage.removeItem("access_token");

      this.$router.push("/login");
    },

  },
  mounted() {
    this.syncFromRoute();
    this.setPageNoXScroll(!!this.showImportData);

    if (this.$route.path === "/dashboard" && this.$route.name === "Dashboard") {
      this.activeSection = "study-management";
    }

    console.log("[Dashboard] starting ActivityTracker (DOM sampled + API activity)");

    activityTracker.start({
      getToken: () => this.$store.state.token,
      onLogout: (msg) => this.logout(msg),

      // only called every 5 min if there was activity in that window
      pingFn: (token) => {
        console.log("[Dashboard] ActivityTracker pingFn() called");
        return axios.post("/users/ping", null, {
          headers: { Authorization: `Bearer ${token}` },
        });
      },

      config: {
        debug: true,

        // server policy
        pingIntervalMs: 5 * 60 * 1000,
        inactivityMs: 30 * 60 * 1000,
        idleCheckMs: 30 * 1000,
        eventCooldownMs: 5 * 60 * 1000,
        detachListenersDuringCooldown: true,
      },
    });
  },
  beforeUnmount() {
    this.setPageNoXScroll(false);
    console.log("[Dashboard] stopping ActivityTracker (unmount)");
    activityTracker.stop();
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
  transition: grid-template-columns 0.3s ease;
}

/* When sidebar should be hidden entirely (View Study / Add Data / Scratch Form) */
.dashboard-layout.sidebar-hidden {
  grid-template-areas:
    "header header"
    "main main";
  grid-template-columns: 0 1fr;
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

/*  make it feel clickable without changing layout */
.logo-container .logo {
  cursor: pointer;
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
  padding: 20px;
  background: #fff;
  transition: margin-left 0.3s ease;
  min-width: 0;
}
.dashboard-main.expanded {
  margin-left: -150px;
}

/*  If sidebar hidden, ensure no funky shift */
.dashboard-layout.sidebar-hidden .dashboard-main {
  margin-left: 0 !important;
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

/* draft tag */
.status-tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.3px;
  line-height: 1;
  border: 1px solid transparent;
  user-select: none;
}
.status-tag--draft {
  background: #fff7ed;
  border-color: #fdba74;
  color: #9a3412;
}
.study-name-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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

/* solid/outline buttons for dialog */
.btn-primary-solid {
  border: 1px solid #245fe0;
  background: #2f6fed;
  color: #fff;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 14px;
  cursor: pointer;
}
.btn-primary-solid:hover {
  background: #285fce;
}
.btn-primary-outline {
  border: 1px solid #245fe0;
  background: transparent;
  color: #245fe0;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 14px;
  cursor: pointer;
}
.btn-primary-outline:hover {
  background: rgba(47, 111, 237, 0.08);
}
.btn-danger {
  border-color: #fecaca !important;
  background: #fff1f2 !important;
  color: #9f1239 !important;
}
.btn-danger:hover {
  background: #ffe4e6 !important;
}
.btn-danger-solid {
  border-color: #9f1239 !important;
  background: #9f1239 !important;
  color: #fff !important;
}
.btn-danger-solid:hover {
  background: #881337 !important;
  border-color: #881337 !important;
}

/* modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}
.modal {
  width: 100%;
  max-width: 560px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.25);
  border: 1px solid #e5e7eb;
  overflow: hidden;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.modal-title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
}
.modal-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
  color: #6b7280;
}
.modal-close:hover {
  color: #111827;
}
.modal-body {
  padding: 14px 16px 6px 16px;
}
.modal-lead {
  margin: 0 0 10px 0;
  color: #111827;
}
.modal-text {
  margin: 0 0 12px 0;
  color: #374151;
  line-height: 1.45;
}
.modal-warning {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 12px;
  margin-top: 10px;
}
.modal-warning--danger {
  background: #fff1f2;
  border-color: #fecaca;
}
.modal-warning-title {
  font-weight: 700;
  color: #111827;
  margin-bottom: 6px;
}
.modal-warning-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
}
.modal-warning-list li {
  margin: 6px 0;
}
.modal-footer {
  padding: 12px 16px 16px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

/* IMPORT OVERLAY */
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
  white-space: normal;
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
.import-overlay-content :deep(.import-study) {
  max-width: none;
  width: 100%;
  margin: 0;
  min-width: 0;
}
.import-overlay-content :deep(table) {
  max-width: 100%;
}


@media (min-width: 1700px) {

  /* ---- Typography scale up ---- */
  .dashboard-layout {
    font-size: 16px;
  }

  .user-role {
    font-size: 14px;
  }

  .action-card-desc {
    font-size: 14px;
  }

  .btn-minimal {
    font-size: 15px;
  }

  /* ---- CENTER CONTENT AREA WIDTH ---- */
  .dashboard-main {
    max-width: 1600px;
    margin: 0 auto;
  }

  /* ---- ACTION CARDS -> HORIZONTAL GRID ---- */
  .primary-actions-cards {
    grid-template-columns: repeat(3, minmax(320px, 1fr));
    justify-content: center;
    gap: 28px;
    margin-top: 32px;
  }

  /* cards become slightly larger */
  .action-card {
    padding: 24px 26px;
    border-radius: 14px;
  }

  .action-card-title {
    font-size: 18px;
  }

  .action-card-desc {
    font-size: 15px;
  }

  /* optional: nicer hover presence on large screens */
  .action-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  }


  .study-table th,
  .study-table td {
    padding: 16px;
    font-size: 15px;
  }

}
</style>