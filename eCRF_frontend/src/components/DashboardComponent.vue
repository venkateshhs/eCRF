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
                    <!-- Add Data: Admin, PI, Investigator -->
                    <button
                      v-if="isAdmin || isPI || isInvestigator"
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
    //whenever the URL has ?openStudies=true, we open the study list
    '$route.query.openStudies'(val) {
      if (val === 'true') {
        this.activeSection = 'study-management';
        this.showStudyOptions = true;
        this.loadStudies();
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
      if (this.showStudyOptions) this.loadStudies();
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
        this.studies = data;
      } catch (e) {
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
      if (!token) return alert("Please log in again.");
      // 1) fetch the full study_data payload
     const resp = await axios.get(
       `http://127.0.0.1:8000/forms/studies/${study.id}`,
       { headers: { Authorization: `Bearer ${token}` } }
     );
     const sd = resp.data.content?.study_data;
     console.log("data", sd)
     if (!sd) {
       return alert("Study content is empty.");
     }

     // 2) commit *all* parts of study_data so the wizard can pick them up
     this.$store.commit("setStudyDetails", {
       study:             sd.study,
       groups:            sd.groups,
       visits:            sd.visits,
       subjectCount:      sd.subjectCount,
       assignmentMethod:  sd.assignmentMethod,
       subjects:          sd.subjects,
     });

     // 2.a drop out of the "study-management" panel so <router-view> shows
      this.activeSection = "";

     // 3) route into Step 1 of the create‐study wizard
     this.$router.push({ name: "CreateStudy", params: { id: study.id } })
    },
    addData(study) {
      this.$router.push({ name: "StudyDetail", params: { id: study.id } });
    },
    navigate(to) {
      this.activeSection = "";
      this.$router.push(to);
    },
    logout() {
      this.$store.commit("setUser", null);
      this.$router.push("/login");
    },
  },
  mounted() {
    if (this.$route.path === "/dashboard") {
      this.activeSection = "study-management";
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
  border-bottom: 1px solid #ddd;
}
.logo-container img { width: 110px; }
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
  padding: 20px; border-right: 1px solid #ddd;
  transition: width 0.3s ease;
}
.dashboard-sidebar.collapsed { width: 70px; padding: 10px; }
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
.dashboard-sidebar nav ul { list-style: none; padding: 0; }
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
  grid-area: main; padding: 30px; background: #fff;
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
  width: 100%; border-collapse: collapse; margin-bottom: 15px;
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
  padding: 8px 12px; background: #f0f0f0; border: 1px solid #bbb;
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
  .dashboard-layout { grid-template-columns: 70px 1fr; }
  .dashboard-sidebar { width: 70px; }
  .dashboard-main { padding: 20px; }
}
</style>
