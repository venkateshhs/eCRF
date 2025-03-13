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
          <li @click="setActiveSection('study-management')" class="nav-item">
            <i :class="icons.book" v-if="sidebarCollapsed"></i>
            <span v-if="!sidebarCollapsed">Study Management</span>
          </li>
          <li @click="navigate('/dashboard/user-info')" class="nav-item">
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
        <div class="button-container">
          <button @click="navigate('/dashboard/create-study')" class="btn-option">Create Study</button>
          <button @click="navigate('/dashboard/view-forms')" class="btn-option">Open Study</button>
        </div>
      </div>
      <router-view v-else></router-view>
    </main>
  </div>
</template>

<script>
import icons from "@/assets/styles/icons";

export default {
  name: "DashboardComponent",
  data() {
    return {
      sidebarCollapsed: false,
      activeSection: "study-management",
      icons,
    };
  },
  methods: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      console.log("Sidebar toggled. Collapsed:", this.sidebarCollapsed);
    },
    setActiveSection(section) {
      this.activeSection = section;
      console.log("Active section set to:", section);
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
