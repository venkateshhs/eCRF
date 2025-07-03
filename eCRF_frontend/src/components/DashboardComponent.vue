<template>
  <div class="dashboard-layout">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="logo-container">
        <img src="../assets/logo.png" alt="Logo" class="logo" />
      </div>
      <div class="user-actions">
        <button @click="logout" class="btn-logout">Logout</button>
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
          <!-- Study Management: hidden from Patients -->
          <li
            v-if="role !== 'Patient'"
            @click="setActiveSection('study-management')"
            class="nav-item"
          >
            <i :class="icons.book" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">Study Management</span>
          </li>
          <!-- User Management: only for Admin -->
          <li
            v-if="isAdmin"
            @click="navigate('/dashboard/user-info')"
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
      <div v-if="activeSection === 'study-management'">
        <h1>Study Management</h1>
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
            Open Study
          </button>
        </div>

        <!-- Study Dashboard Table -->
        <div v-if="showStudyOptions" class="study-dashboard">
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
                      class="btn-option"
                    >
                      Edit Study
                    </button>
                    <!-- Add Data: all except Patient -->
                    <button
                      v-if="role !== 'Patient'"
                      @click="addData(study)"
                      class="btn-option"
                    >
                      Add Data
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="back-button-container">
            <button @click="toggleStudyOptions" class="btn-back">
              <i :class="icons.arrowLeft"></i> Back
            </button>
          </div>
        </div>
      </div>
      <router-view v-else></router-view>
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
      console.log("Sidebar toggled. Collapsed:", this.sidebarCollapsed);
    },
    setActiveSection(section) {
      this.activeSection = section;
      this.showStudyOptions = false;
      console.log("Active section set to:", section);
    },
    toggleStudyOptions() {
      this.showStudyOptions = !this.showStudyOptions;
      console.log("Study options toggled:", this.showStudyOptions);
      if (this.showStudyOptions) {
        this.loadStudies();
      }
    },
    async loadStudies() {
      const token = this.$store.state.token;
      if (!token) {
        alert("Authentication error. Please log in again.");
        this.$router.push("/login");
        return;
      }
      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/studies", {
          headers: { Authorization: `Bearer ${token}` },
        });
        this.studies = response.data;
        console.log("Loaded studies:", this.studies);
      } catch (error) {
        console.error("Error loading studies:", error.response?.data || error.message);
        if (error.response && error.response.status === 401) {
          alert("Session expired. Please log in again.");
          this.$router.push("/login");
        } else {
          alert("Failed to load studies.");
        }
      }
    },
    formatDateTime(dateString) {
      if (!dateString) return "";
      const date = new Date(dateString);
      return date.toLocaleString("en-GB", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    },
    async editStudy(study) {
      // Clear any stored study data.
      localStorage.removeItem("setStudyDetails");
      localStorage.removeItem("scratchForms");

      const token = this.$store.state.token;
      if (!token) {
        alert("Authentication error. Please log in again.");
        this.$router.push("/login");
        return;
      }

      try {
        console.log("Fetching full study data for study ID:", study.id);
        const response = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${study.id}`,
          {
            headers: { Authorization: `Bearer ${token}` },
        });
        console.log("Full study response:", response.data);

        // Extract dynamic study data from the API response.
        const studyData = response.data.content && response.data.content.study_data;
        if (!studyData) {
          console.error("Study content is empty.");
          this.openGenericDialog("Study content is empty.");
          return;
        }

        // Extract and flatten meta_info.
        const meta = studyData.meta_info || {};
        const dynamicStudy = {
          id: study.id,
          name: meta.name,
          description: meta.description,
          studyType: meta.studyType || "Custom",
          numberOfForms: meta.numberOfForms || (studyData.forms ? studyData.forms.length : 0),
          metaInfo: {
            numberOfSubjects: meta.numberOfSubjects,
            numberOfVisits: meta.numberOfVisits,
            studyMetaDescription: meta.studyMetaDescription,
          },
          customFields: meta.customFields || [],
          metaCustomFields: meta.metaCustomFields || [],
          forms: studyData.forms
            ? studyData.forms.map(form => ({
                formName: form.form_name ? form.form_name : (form.formName || "Untitled Form"),
                sections: form.sections,
              }))
            : [],
        };

        // Update local state
        this.metaInfo = dynamicStudy.metaInfo;
        this.forms = dynamicStudy.forms;
        this.totalForms = dynamicStudy.numberOfForms;
        this.currentFormIndex = 0;
        this.activeSection =
          (this.forms[0] && this.forms[0].sections && this.forms[0].sections.length > 0) ? 0 : null;
        console.log("Loaded dynamic study data:", dynamicStudy);

        // Commit the dynamic study data to Vuex.
        this.$store.commit("setStudyDetails", dynamicStudy);
        console.log("Committed dynamic study data to Vuex:", dynamicStudy);

        // Store forms in localStorage for ScratchFormComponent.
        localStorage.setItem("scratchForms", JSON.stringify(dynamicStudy.forms));

        console.log("Navigating to edit study view for study ID:", study.id);
        this.$router.push({ name: "CreateFormScratch", params: { id: study.id } });
      } catch (error) {
        console.error("Error retrieving full study data:", error.response?.data || error.message);
        alert("Failed to load study data. Please try again.");
      }
    },
    addData(study) {
      console.log("Adding data to study:", study.id);
      this.$router.push({ name: "StudyDetail", params: { id: study.id } });
    },
    navigate(route) {
      this.activeSection = "";
      console.log("Navigating to route:", route);
      this.$router.push(route);
    },
    logout() {
      this.$store.commit("setUser", null);
      console.log("User logged out.");
      this.$router.push("/");
    },
    openGenericDialog(message, callback = null) {
      alert(message);
      if (callback) callback();
    },
  },
  mounted() {
    if (this.$route.path === "/dashboard") {
      this.activeSection = "study-management";
    }
  },
};
</script>

<style scoped>
/* Layout */
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

/* Header */
.dashboard-header {
  grid-area: header;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
}

.logo-container img {
  width: 110px;
}

.user-actions .btn-logout {
  background: none;
  border: none;
  font-size: 14px;
  color: #444;
  cursor: pointer;
}

.btn-logout:hover {
  text-decoration: underline;
}

/* Sidebar */
.dashboard-sidebar {
  grid-area: sidebar;
  background: #f9f9f9;
  padding: 20px;
  border-right: 1px solid #ddd;
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
  color: #444;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.3s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-item:hover {
  background: #eaeaea;
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

/* Study Dashboard Styles */
.study-dashboard {
  margin-top: 20px;
}

.study-dashboard h2 {
  margin-bottom: 15px;
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
  border-bottom: 1px solid #eaeaea;
}

.study-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #444;
}

.study-table tr:hover {
  background-color: #f9f9f9;
}

/* Action Buttons Container for gap */
.action-buttons {
  display: flex;
  gap: 10px;
}

.back-button-container {
  display: flex;
  justify-content: flex-start;
  margin-top: 10px;
}

.btn-back {
  padding: 8px 12px;
  background: #f0f0f0;
  border: 1px solid #bbb;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease;
  display: flex;
  align-items: center;
  gap: 5px;
}

.btn-back:hover {
  background: #e0e0e0;
  color: #333;
}

/* Horizontal Button Layout */
.button-container {
  display: flex;
  gap: 15px;
  margin-top: 20px;
}

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
