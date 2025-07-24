<template>
  <div class="user-info-container">
    <!-- ─── Tabs ─────────────────────────────────────────────────── -->
    <div class="tabs">
      <button
        v-for="tab in visibleTabs"
        :key="tab.key"
        :class="['tab-button', { active: currentTab === tab.key }]"
        @click="currentTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="tab-content">
      <!-- PROFILE TAB -->
      <section v-if="currentTab === 'profile'" class="profile-section">
        <h2>Profile</h2>
        <div class="user-details">
          <p><strong>Username:</strong> {{ user.username }}</p>
          <p><strong>First Name:</strong> {{ user.profile.first_name }}</p>
          <p><strong>Last Name:</strong> {{ user.profile.last_name }}</p>
          <p><strong>Email:</strong> {{ user.email }}</p>
        </div>
      </section>

      <!-- STUDY SETTINGS TAB -->
      <!-- only render this section if currentTab==='settings' AND (isAdmin||isPI) -->
        <section
          v-else-if="currentTab === 'settings' && (isAdmin || isPI)"
          class="settings-section"
        >
          <StudySettings />
        </section>


      <!-- CHANGE PASSWORD TAB -->
      <section v-else-if="currentTab === 'password'" class="password-section">
        <h2>Change Password</h2>
        <form @submit.prevent="handleChangePassword" class="password-form">
          <div class="form-group">
            <label for="new_password">New Password</label>
            <div class="password-wrapper">
              <input
                :type="showPassword ? 'text' : 'password'"
                id="new_password"
                v-model="newPassword"
                placeholder="At least 8 chars, number & special"
                required
              />
              <button
                type="button"
                class="toggle-password"
                @click="togglePasswordVisibility"
              >
                {{ showPassword ? "Hide" : "Show" }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label for="confirm_password">Confirm Password</label>
            <input
              :type="showPassword ? 'text' : 'password'"
              id="confirm_password"
              v-model="confirmPassword"
              placeholder="Retype new password"
              required
            />
          </div>

          <button type="submit" class="btn-change-password">
            Update Password
          </button>
        </form>
        <p v-if="passwordMessage" class="message">{{ passwordMessage }}</p>
        <p v-if="passwordError" class="error">{{ passwordError }}</p>
      </section>

      <!-- MANAGE USERS TAB (Admin Only) -->
      <section
        v-else-if="currentTab === 'management' && isAdmin"
        class="management-section"
      >
        <h2>Manage Users</h2>

        <!-- Create New User Form -->
        <form @submit.prevent="handleCreateUser" class="create-user-form">
          <h3>Create New User</h3>
          <div class="form-row">
            <input v-model="newUser.username" placeholder="Username" required />
            <input v-model="newUser.email" placeholder="Email" type="email" required />
          </div>
          <div class="form-row">
            <input v-model="newUser.first_name" placeholder="First Name" required />
            <input v-model="newUser.last_name" placeholder="Last Name" required />
          </div>
          <div class="form-row">
            <input
              v-model="newUser.password"
              placeholder="Password"
              type="password"
              required
            />
            <input
              v-model="newUser.confirmPassword"
              placeholder="Confirm Password"
              type="password"
              required
            />
          </div>
          <div class="form-row">
            <select v-model="newUser.role">
              <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <button type="submit" class="btn-option">Create User</button>
          <p v-if="userMgmtMessage" class="message">{{ userMgmtMessage }}</p>
          <p v-if="userMgmtError" class="error">{{ userMgmtError }}</p>
        </form>

        <!-- Existing Users Table -->
        <h3>Existing Users</h3>
        <table class="user-table">
          <thead>
            <tr>
              <th>Username</th><th>Email</th><th>Name</th><th>Role</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.username }}</td>
              <td>{{ u.email }}</td>
              <td>{{ u.profile.first_name }} {{ u.profile.last_name }}</td>
              <td>
                <select
                  :value="u.profile.role"
                  @change="onInitiateRoleChange(u, $event.target.value)"
                >
                  <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- Custom Confirm Dialog for Role Change -->
    <div v-if="showRoleDialog" class="dialog-overlay">
      <div class="dialog-box">
        <p>
          Change <strong>{{ pendingUser.username }}</strong>'s role to
          <strong>{{ pendingRole }}</strong>?
        </p>
        <div class="dialog-actions">
          <button @click="confirmRoleChange" class="btn-confirm">Yes</button>
          <button @click="cancelRoleChange" class="btn-cancel">No</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import StudySettings from "@/components/StudySettings.vue";

export default {
  name: "UserInfoComponent",
  components: { StudySettings },
  data() {
    return {
      currentTab: "profile",
      user: null,
      // Change Password
      newPassword: "",
      confirmPassword: "",
      showPassword: false,
      passwordMessage: null,
      passwordError: null,
      // Admin User Management
      roles: [
        "Administrator",
        "Investigator",
        "Principal Investigator",
        "No Access"
      ],
      newUser: {
        username: "",
        email: "",
        first_name: "",
        last_name: "",
        password: "",
        confirmPassword: "",
        role: "Investigator",
      },
      users: [],
      userMgmtError: null,
      userMgmtMessage: null,
      // Role‐change dialog
      showRoleDialog: false,
      pendingUser: null,
      pendingRole: null,
    };
  },
  computed: {
  userFromStore() {
    return this.$store.getters.getUser;
  },
  isAdmin() {
    return this.user?.profile?.role === "Administrator";
  },
  isPI() {
    return this.user?.profile?.role === "Principal Investigator";
  },
  visibleTabs() {
    const tabs = [
      { key: "profile",  label: "Profile" },
      //  only show Study Settings if Admin *or* PI
      ...(this.isAdmin || this.isPI
        ? [{ key: "settings", label: "Study Settings" }]
        : []),
      { key: "password", label: "Change Password" },
    ];
    if (this.isAdmin) {
      tabs.push({ key: "management", label: "User Management" });
    }
    return tabs;
  },
},

  async created() {
    // load current user
    this.user = this.userFromStore;
    if (!this.user) {
      await this.$store.dispatch("fetchUserData");
      this.user = this.$store.getters.getUser;
    }
    // if admin, load all users
    if (this.isAdmin) {
      this.fetchUsers();
    }
  },
  methods: {
    /* ─── Change Password ───────────────────────── */
    togglePasswordVisibility() {
      this.showPassword = !this.showPassword;
    },
    validatePassword(pw) {
      return /^(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$/.test(pw);
    },
    async handleChangePassword() {
      this.passwordMessage = this.passwordError = null;
      if (this.newPassword !== this.confirmPassword) {
        this.passwordError = "Passwords do not match.";
        return;
      }
      if (!this.validatePassword(this.newPassword)) {
        this.passwordError = "Must be ≥8 chars, include number & special.";
        return;
      }
      try {
        const ok = await this.$store.dispatch("changePassword", {
          newPassword: this.newPassword,
        });
        if (ok) {
          this.passwordMessage = "Password updated.";
          this.newPassword = this.confirmPassword = "";
        } else {
          this.passwordError = "Update failed.";
        }
      } catch {
        this.passwordError = "Error updating password.";
      }
    },

    /* ─── Admin: Fetch & Create Users ─────────── */
    async fetchUsers() {
      this.userMgmtError = null;
      try {
        const resp = await axios.get(
          "http://localhost:8000/users/admin/users",
          { headers: { Authorization: `Bearer ${this.$store.state.token}` } }
        );
        this.users = resp.data;
      } catch (err) {
        this.userMgmtError = err.response?.data?.detail || err.message;
      }
    },
    async handleCreateUser() {
      this.userMgmtError = this.userMgmtMessage = null;
      const u = this.newUser;
      if (
        !u.username ||
        !u.email ||
        !u.first_name ||
        !u.last_name ||
        !u.password ||
        !u.confirmPassword
      ) {
        this.userMgmtError = "All fields are required.";
        return;
      }
      if (u.password !== u.confirmPassword) {
        this.userMgmtError = "Passwords do not match.";
        return;
      }
      try {
        await axios.post(
          "http://localhost:8000/users/admin/users",
          {
            username: u.username,
            email: u.email,
            first_name: u.first_name,
            last_name: u.last_name,
            password: u.password,
            role: u.role,
          },
          { headers: { Authorization: `Bearer ${this.$store.state.token}` } }
        );
        this.userMgmtMessage = "User created successfully.";
        this.newUser = {
          username: "",
          email: "",
          first_name: "",
          last_name: "",
          password: "",
          confirmPassword: "",
          role: "Investigator",
        };
        this.fetchUsers();
      } catch (err) {
        this.userMgmtError = err.response?.data?.detail || err.message;
      }
    },

    /* ─── Admin: Change Role with Custom Dialog ── */
    onInitiateRoleChange(user, newRole) {
      this.pendingUser = user;
      this.pendingRole = newRole;
      this.showRoleDialog = true;
    },
    async confirmRoleChange() {
      try {
        await axios.patch(
          `http://localhost:8000/users/admin/users/${this.pendingUser.id}/role`,
          { role: this.pendingRole },
          { headers: { Authorization: `Bearer ${this.$store.state.token}` } }
        );
        this.pendingUser.profile.role = this.pendingRole;
      } catch (err) {
        alert("Failed to update role: " + (err.response?.data?.detail || err.message));
      } finally {
        this.showRoleDialog = false;
        this.pendingUser = this.pendingRole = null;
      }
    },
    cancelRoleChange() {
      this.showRoleDialog = false;
      this.pendingUser = this.pendingRole = null;
    },
  },
};
</script>

<style scoped>
.user-info-container {
  max-width: 900px;
  margin: 2rem auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  font-family: Arial, sans-serif;
  overflow: hidden;
}
/* ─── Tabs ───────────────────────────────────────── */
.tabs {
  display: flex;
  background: #f7f7f7;
  border-bottom: 1px solid #ddd;
}
.tab-button {
  flex: 1;
  padding: 12px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 15px;
  transition: background 0.2s;
}
.tab-button:hover { background: #eaeaea; }
.tab-button.active {
  background: #fff;
  border-bottom: 3px solid #4f46e5;
  font-weight: bold;
}
/* ─── Content ───────────────────────────────────── */
.tab-content { padding: 24px; }
/* ─── Profile ─────────────────────────────────── */
.profile-section h2 { margin-bottom: 1rem; }
.user-details p { margin: 6px 0; color: #555; }
/* ─── Settings ────────────────────────────────── */
.settings-section { /* if needed */ }
/* ─── Change Password ────────────────────────── */
.password-section {
  max-width: 480px;
  margin: 2rem auto;
  padding: 2rem;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.password-section h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  text-align: center;
  color: #333;
}
.password-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.form-group {
  display: flex;
  flex-direction: column;
}
.form-group label {
  font-size: 0.95rem;
  color: #444;
  margin-bottom: 0.5rem;
}
.password-wrapper {
  display: flex;
  align-items: center;
}
.password-wrapper input {
  flex: 1;
  padding: 0.6rem 0.8rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px 0 0 4px;
  outline: none;
}
.password-wrapper input:focus { border-color: #4f46e5; }
.toggle-password {
  padding: 0.6rem 0.8rem;
  background: #f0f0f0;
  border: 1px solid #ccc;
  border-left: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  font-size: 0.9rem;
}
.toggle-password:hover { background: #e5e7eb; }
.btn-change-password {
  align-self: stretch;
  padding: 0.8rem;
  background: #4f46e5;
  color: #fff;
  font-size: 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-change-password:hover { background: #3730a3; }
.password-section .message,
.password-section .error {
  margin-top: 1rem;
  text-align: center;
  font-size: 0.9rem;
}
.password-section .message { color: #16a34a; }
.password-section .error { color: #dc2626; }
/* ─── Manage Users ───────────────────────────── */
.management-section h2,
.management-section h3 {
  text-align: center;
  color: #333;
}
.create-user-form .form-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}
.create-user-form input,
.create-user-form select {
  flex: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.create-user-form button.btn-option {
  margin-top: 10px;
  padding: 8px 16px;
  background: #4f46e5;
  border: none;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
}
.create-user-form button.btn-option:hover {
  background: #3730a3;
}
.user-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}
.user-table th,
.user-table td {
  border: 1px solid #eee;
  padding: 8px;
  text-align: left;
}
.user-table th {
  background: #f9f9f9;
  font-weight: 600;
}
/* ─── Custom Confirm Dialog ─────────────────── */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.dialog-box {
  background: #fff;
  padding: 1.5rem;
  border-radius: 6px;
  max-width: 320px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.dialog-box p {
  margin-bottom: 1rem;
  font-size: 1rem;
}
.dialog-actions {
  display: flex;
  justify-content: space-around;
}
.btn-confirm {
  background: #4f46e5;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}
.btn-confirm:hover { background: #3730a3; }
.btn-cancel {
  background: #e5e7eb;
  color: #333;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}
.btn-cancel:hover { background: #d1d5db; }
</style>
