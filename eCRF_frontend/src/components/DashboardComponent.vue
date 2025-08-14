<template>
  <div class="dashboard-layout">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="logo-container">
        <img src="../assets/logo.png" alt="Logo" class="logo" />
      </div>
      <div class="user-actions">
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
          <li @click="() => { setActiveSection(''); navigate('/dashboard/user-info') }" class="nav-item">
            <i :class="icons.user" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">User Management</span>
          </li>
        </ul>
      </nav>
    </aside>

    <!-- Main Content -->
    <main :class="['dashboard-main', { expanded: sidebarCollapsed }]">
      <div v-if="$route.name === 'Dashboard' && activeSection === 'study-management'">
        <h1 class="study-management-title">Study Management</h1>
        <div class="button-container" v-if="!showStudyOptions">
          <!-- Create Study: only Admin or PI -->
          <button
            v-if="isAdmin || isPI"
            @click="navigate('/dashboard/create-study')"
            class="btn-option"
          >
            Create Study
          </button>
          <!-- Open Study: Admin, PI, Investigator -->
          <button
            v-if="isAdmin || isPI || isInvestigator"
            @click="toggleStudyOptions"
            class="btn-option"
          >
            Open Existing Study
          </button>
        </div>

        <!-- Study Dashboard Table -->
        <div v-if="showStudyOptions" class="study-dashboard">
          <div class="back-button-container">
            <button @click="toggleStudyOptions" class="btn-minimal">
              Back
            </button>
          </div>
          <h2>Existing Studies</h2>
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
                <td>{{ study.study_name }}</td>
                <td>{{ study.study_description }}</td>
                <td>{{ formatDateTime(study.created_at) }}</td>
                <td>{{ formatDateTime(study.updated_at) }}</td>
                <td>
                  <div class="action-buttons">
                    <!-- Edit Study: only Admin or PI -->
                    <button
                      v-if="isAdmin || isPI"
                      @click="editStudy(study)"
                      class="btn-minimal"
                    >
                      Edit Study
                    </button>
                    <!-- Add Data: Admin, PI, Investigator -->
                    <button
                      v-if="isAdmin || isPI || isInvestigator"
                      @click="addData(study)"
                      class="btn-minimal"
                    >
                      Add Data
                    </button>
                      <button
                        v-if="isAdmin || isPI || isInvestigator"
                        @click="viewData(study)"
                        class="btn-minimal"
                      >View Data
                      </button>
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

export default {
  name: "DashboardComponent",
  data() {
    return {
      sidebarCollapsed: false,
      activeSection: "study-management",
      showStudyOptions: false,
      studies: [],
      icons,
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
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
    },
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
        const { data } = await axios.get("http://127.0.0.1:8000/forms/studies", {
          headers: { Authorization: `Bearer ${token}` },
        });
        console.log('Fetched studies:', JSON.stringify(data, null, 2));
        this.studies = data;
      } catch (e) {
        console.error('Failed to load studies:', e);
        console.log('Error details:', e.response?.data || e.message);
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
          `http://127.0.0.1:8000/forms/studies/${study.id}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        console.log('Fetched study details:', JSON.stringify(resp.data, null, 2));
        const sd = resp.data.content?.study_data;
        const meta = resp.data.metadata || {};
        if (!sd) {
          console.error('Study content is empty');
          alert("Study content is empty.");
          return;
        }

        // Initialize assignments
        let assignments = Array.isArray(sd.assignments) ? sd.assignments : [];
        if (!assignments.length && sd.selectedModels?.length) {
          console.warn('Assignments missing in backend response, initializing empty assignments');
          const m = sd.selectedModels.length;
          const v = sd.visits?.length || 0;
          const g = sd.groups?.length || 0;
          assignments = Array.from({ length: m }, () =>
            Array.from({ length: v }, () =>
              Array.from({ length: g }, () => false)
            )
          );
        }
        console.log('Loaded assignments from backend:', JSON.stringify(assignments, null, 2));

        // Prepare study metadata
        const studyInfo = {
          id: meta.id,
          name: meta.study_name,
          description: meta.study_description,
          created_at: meta.created_at,
          updated_at: meta.updated_at,
          created_by: meta.created_by
        };

        // Commit to Vuex store
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
        console.log('Committed studyDetails to Vuex:', JSON.stringify(this.$store.state.studyDetails, null, 2));

        // Store scratchForms in localStorage
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
        console.error('Failed to fetch study details:', e);
        console.log('Error details:', e.response?.data || e.message);
        alert("Failed to load study details.");
      }
    },
    addData(study) {
      this.$router.push({ name: "StudyDetail", params: { id: study.id } });
    },
    viewData(study) {
    this.$router.push({ name: "StudyDataDashboard", params: { id: study.id } });
    },
    navigate(to) {
      this.activeSection = "";
      this.$router.push(to);
    },
    logout() {
      this.$store.commit("setUser", null);
      this.$store.commit("setToken", null);
      this.$router.push("/login");
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

.logo-container img {
  width: 110px;
}

.user-actions .btn-minimal {
  background: none;
  border: none;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  padding: 8px 12px;
  transition: color 0.3s ease;
}

.user-actions .btn-minimal:hover {
  color: #000;
}

/* Sidebar */
.dashboard-sidebar {
  grid-area: sidebar;
  background: #f9f9f9;
  padding: 20px;
  border-right: 1px solid #e0e0e0;
  transition: width 0.3s ease;
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
  border-radius: 4px;
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
}

.dashboard-main.expanded {
  margin-left: -150px;
}

/* Study Management Title */
.study-management-title {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

/* Study Dashboard Styles */
.study-dashboard {
  margin-top: 20px;
}

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

.study-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #444;
}

.study-table tr:hover {
  background-color: #f9f9f9;
}

/* Action Buttons Container */
.action-buttons {
  display: flex;
  gap: 10px;
}

/* Back Button Container */
.back-button-container {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 15px;
}

/* Minimalistic Button Style */
.btn-minimal {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease;
  display: flex;
  align-items: center;
  gap: 5px;
}

.btn-minimal:hover {
  background: #e8e8e8;
  color: #000;
}

/* Option Button Style for Create/Open Study */
.btn-option {
  flex: 1;
  padding: 12px;
  background: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-size: 16px;
  color: #333;
  cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease;
  text-align: center;
}

.btn-option:hover {
  background: #e0e0e0;
  color: #000;
}

/* Button Container */
.button-container {
  display: flex;
  gap: 15px;
  margin-top: 20px;
}

/* Responsive Design */
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
}
</style>