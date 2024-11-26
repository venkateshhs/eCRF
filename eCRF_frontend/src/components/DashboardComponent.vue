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
      <nav v-if="!sidebarCollapsed">
        <ul>
          <li v-for="item in menuItems" :key="item.name" @click="navigate(item.route)">
            {{ item.label }}
          </li>
        </ul>
      </nav>
    </aside>

    <!-- Main Content Area -->
    <main :class="['dashboard-main', { expanded: sidebarCollapsed }]">
      <router-view></router-view>
    </main>
  </div>
</template>

<script>
export default {
  name: "DashboardComponent",
  data() {
    return {
      sidebarCollapsed: false, // Tracks the visibility of the sidebar
      menuItems: [
        { name: "userInfo", label: "User Info", route: "/dashboard/user-info" },
        { name: "createForm", label: "Create Form", route: "/dashboard/create-form" },
        { name: "viewForms", label: "View Forms", route: "/dashboard/view-forms" },
        { name: "analytics", label: "Analytics", route: "/dashboard/analytics" },
      ],
    };
  },
  methods: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed; // Toggles the collapse state
    },
    navigate(route) {
      this.$router.push(route); // Navigate to the selected route
    },
    logout() {
      this.$store.commit("setUser", null); // Clear user info in Vuex
      this.$router.push("/"); // Redirect to login page
    },
  },
};
</script>

<style scoped>
/* General Layout */
.dashboard-layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main";
  grid-template-rows: 70px 1fr;
  grid-template-columns: 250px 1fr; /* Sidebar starts expanded */
  height: 100vh;
  font-family: Arial, sans-serif;
  transition: grid-template-columns 0.3s ease; /* Smooth resize */
}

.dashboard-header {
  grid-area: header;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #007bff;
  color: white;
}

.logo-container img {
  width: 120px;
}

.user-actions .btn-logout {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 16px;
}

/* Sidebar */
.dashboard-sidebar {
  grid-area: sidebar;
  background-color: #f4f4f9;
  padding: 20px;
  border-right: 1px solid #ddd;
  transition: width 0.3s ease; /* Smooth collapse/expand */
}

.dashboard-sidebar.collapsed {
  width: 70px; /* Collapsed width */
}

.hamburger-menu {
  background: none;
  border: none;
  padding: 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hamburger-menu span {
  display: block;
  width: 25px;
  height: 3px;
  background-color: #333;
  margin: 5px 0;
  transition: all 0.3s ease;
}

.hamburger-menu:hover span {
  background-color: #007bff;
}

.dashboard-sidebar nav ul {
  list-style: none;
  padding: 0;
}

.dashboard-sidebar nav li {
  margin: 10px 0;
  cursor: pointer;
  font-size: 16px;
}

.dashboard-sidebar nav li:hover {
  color: #007bff;
}

/* Main Content Area */
.dashboard-main {
  grid-area: main;
  padding: 20px;
  background: #fff;
  transition: margin-left 0.3s ease; /* Smooth resize */
}

.dashboard-main.expanded {
  margin-left: -180px; /* Shrinks based on sidebar width */
}

.dashboard-main h1 {
  color: #333;
}
</style>
