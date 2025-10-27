<template>
  <div class="user-info-container">
    <div class="layout">
      <!-- Sidebar (vertical tabs) -->
      <aside class="sidebar">
        <button
          v-for="tab in visibleTabs"
          :key="tab.key"
          :class="['tab-btn', { active: currentTab === tab.key }]"
          @click="currentTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </aside>

      <!-- Main content -->
      <main class="content">
        <!-- PROFILE -->
        <section v-if="currentTab === 'profile'" class="section">
          <h2 class="section-title">Profile</h2>
          <div class="section-box scrollable">
            <div class="card">
              <div class="kv">
                <span class="k">Username</span>
                <span class="v">{{ user.username }}</span>
              </div>
              <div class="kv">
                <span class="k">First Name</span>
                <span class="v">{{ user.profile.first_name }}</span>
              </div>
              <div class="kv">
                <span class="k">Last Name</span>
                <span class="v">{{ user.profile.last_name }}</span>
              </div>
              <div class="kv">
                <span class="k">Email</span>
                <span class="v">{{ user.email }}</span>
              </div>
              <div class="kv">
                <span class="k">Role</span>
                <span class="v role-pill" :data-role="user.profile.role">{{ user.profile.role }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- STUDY SETTINGS -->
        <section v-else-if="currentTab === 'settings' && (isAdmin || isPI)" class="section">
          <h2 class="section-title">Study Settings</h2>
          <p class="disclaimer">
            Note: Study Settings are not fully implemented yet. This section is a work in progress.
          </p>
          <div class="section-box scrollable">
            <StudySettings />
          </div>
        </section>

        <!-- CHANGE PASSWORD -->
        <section v-else-if="currentTab === 'password'" class="section">
          <h2 class="section-title">Change Password</h2>
          <div class="section-box scrollable">
            <form @submit.prevent="handleChangePassword" class="form">
              <div class="form-field">
                <label for="new_password">New Password</label>
                <div class="input-row">
                  <input
                    :type="showPassword ? 'text' : 'password'"
                    id="new_password"
                    v-model="newPassword"
                    placeholder="At least 8 chars, includes a number & special character"
                    required
                  />
                  <button type="button" class="btn ghost" @click="togglePasswordVisibility">
                    {{ showPassword ? "Hide" : "Show" }}
                  </button>
                </div>
              </div>

              <div class="form-field">
                <label for="confirm_password">Confirm Password</label>
                <input
                  :type="showPassword ? 'text' : 'password'"
                  id="confirm_password"
                  v-model="confirmPassword"
                  placeholder="Retype new password"
                  required
                />
              </div>

              <div class="form-actions">
                <button type="submit" class="btn primary">Update Password</button>
              </div>

              <p v-if="passwordMessage" class="msg ok">{{ passwordMessage }}</p>
              <p v-if="passwordError" class="msg err">{{ passwordError }}</p>
            </form>
          </div>
        </section>

        <!-- USER MANAGEMENT -->
        <section v-else-if="currentTab === 'management' && isAdmin" class="section">
          <h2 class="section-title">User Management</h2>

          <!-- Tab-level scroll container -->
          <div class="section-scroll">
            <!-- Create User -->
            <div class="section-box">
              <h3 class="sub-title">Create New User</h3>
              <form @submit.prevent="handleCreateUser" class="form grid-2">
                <div class="form-field">
                  <label>Username</label>
                  <input v-model="newUser.username" placeholder="e.g., jdoe" required />
                </div>
                <div class="form-field">
                  <label>Email</label>
                  <input v-model="newUser.email" type="email" placeholder="user@example.com" required />
                </div>
                <div class="form-field">
                  <label>First Name</label>
                  <input v-model="newUser.first_name" placeholder="First name" required />
                </div>
                <div class="form-field">
                  <label>Last Name</label>
                  <input v-model="newUser.last_name" placeholder="Last name" required />
                </div>
                <div class="form-field">
                  <label>Password</label>
                  <input v-model="newUser.password" type="password" placeholder="Set a password" required />
                </div>
                <div class="form-field">
                  <label>Confirm Password</label>
                  <input v-model="newUser.confirmPassword" type="password" placeholder="Retype password" required />
                </div>
                <div class="form-field span-2">
                  <label>Role</label>
                  <select v-model="newUser.role" class="wide-select">
                    <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
                  </select>
                </div>

                <div class="form-actions span-2">
                  <button type="submit" class="btn primary">Create User</button>
                </div>

                <p v-if="userMgmtMessage" class="msg ok span-2">{{ userMgmtMessage }}</p>
                <p v-if="userMgmtError" class="msg err span-2">{{ userMgmtError }}</p>
              </form>
            </div>

            <!-- Users Table -->
            <div class="section-box">
              <h3 class="sub-title">Existing Users</h3>
              <div class="table-wrap no-x-scroll">
                <table class="table">
                  <colgroup>
                    <col />
                    <col />
                    <col />
                    <col style="width: 180px;" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th>Username</th>
                      <th>Email</th>
                      <th>Name</th>
                      <th>Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="u in users" :key="u.id">
                      <td class="wrap">{{ u.username }}</td>
                      <td class="wrap" :title="u.email">{{ u.email }}</td>
                      <td class="wrap" :title="`${u.profile.first_name} ${u.profile.last_name}`">
                        {{ u.profile.first_name }} {{ u.profile.last_name }}
                      </td>
                      <td class="role-td">
                        <div class="role-select-wrap">
                          <select
                            :value="u.profile.role"
                            class="role-select"
                            @change="onInitiateRoleChange(u, $event.target.value)"
                          >
                            <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
                          </select>
                          <span class="select-caret" aria-hidden="true">▾</span>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Role change dialog -->
            <div v-if="showRoleDialog" class="dialog">
              <div class="dialog-box">
                <p>
                  Change <strong>{{ pendingUser.username }}</strong>'s role to
                  <strong>{{ pendingRole }}</strong>?
                </p>
                <div class="dialog-actions">
                  <button @click="confirmRoleChange" class="btn primary">Yes</button>
                  <button @click="cancelRoleChange" class="btn ghost">No</button>
                </div>
              </div>
            </div>
          </div>
          <!-- /section-scroll -->
        </section>
      </main>
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

      // Change password
      newPassword: "",
      confirmPassword: "",
      showPassword: false,
      passwordMessage: null,
      passwordError: null,

      // Admin
      roles: ["Administrator", "Investigator", "Principal Investigator", "No Access"],
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

      // Role dialog
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
      const tabs = [{ key: "profile", label: "Profile" }];
      if (this.isAdmin || this.isPI) tabs.push({ key: "settings", label: "Study Settings" });
      tabs.push({ key: "password", label: "Change Password" });
      if (this.isAdmin) tabs.push({ key: "management", label: "User Management" });
      return tabs;
    },
  },
  async created() {
    this.user = this.userFromStore;
    if (!this.user) {
      await this.$store.dispatch("fetchUserData");
      this.user = this.$store.getters.getUser;
    }
    if (this.isAdmin) {
      this.fetchUsers();
    }
  },
  methods: {
    /* Change Password */
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

    /* Admin: Users */
    async fetchUsers() {
      this.userMgmtError = null;
      try {
        const resp = await axios.get("/users/admin/users", {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        });
        this.users = resp.data;
      } catch (err) {
        this.userMgmtError = err.response?.data?.detail || err.message;
      }
    },
    async handleCreateUser() {
      this.userMgmtError = this.userMgmtMessage = null;
      const u = this.newUser;
      if (!u.username || !u.email || !u.first_name || !u.last_name || !u.password || !u.confirmPassword) {
        this.userMgmtError = "All fields are required.";
        return;
      }
      if (u.password !== u.confirmPassword) {
        this.userMgmtError = "Passwords do not match.";
        return;
      }
      try {
        await axios.post(
          "/users/admin/users",
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

    /* Role dialog */
    onInitiateRoleChange(user, newRole) {
      this.pendingUser = user;
      this.pendingRole = newRole;
      this.showRoleDialog = true;
    },
    async confirmRoleChange() {
      try {
        await axios.patch(
          `/users/admin/users/${this.pendingUser.id}/role`,
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
/* Container */
.user-info-container {
  max-width: 1100px;
  margin: 24px auto;
  padding: 0 16px;
  box-sizing: border-box;
}

/* Vertical layout */
.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
}

/* Sidebar */
.sidebar {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  display: grid;
  gap: 8px;
  height: fit-content;
  position: sticky;
  top: 16px;
}
.tab-btn {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  cursor: pointer;
  /* not bold for tab labels */
  font-weight: 500;
  text-align: left;
}
.tab-btn.active {
  background: #eef2ff;
  border-color: #c7d2fe;
}

/* Content area */
.content { display: grid; gap: 14px; }
.section { display: grid; gap: 14px; }

/* ONLY container headings are bold */
.section-title {
  text-align: center;
  margin: 0 0 6px 0;
  font-size: 1.4rem;
  font-weight: 700; /* keep bold here */
  color: #111827;
}
.sub-title {
  margin: 0 0 8px 0;
  font-size: 1.05rem;
  font-weight: 500; /* not bold */
  color: #1f2937;
}

/* Tab-level scroll (User Management entire tab) */
.section-scroll {
  display: grid;
  gap: 14px;
  max-height: 72vh;
  overflow-y: auto;
  overflow-x: hidden; /* prevent horizontal scroll */
  padding-right: 2px;
}

/* Boxes */
.section-box {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}
.section-box.scrollable {
  max-height: 72vh;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Profile card */
.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.kv {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px dashed #e5e7eb;
}
.kv:last-child { border-bottom: none; }
/* keys (labels) NOT bold */
.k { color: #6b7280; font-weight: 500; }
.v { color: #111827; min-width: 0; word-break: break-word; }
.role-pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  font-size: 0.9rem;
}

/* Disclaimer */
.disclaimer {
  text-align: center;
  margin: -4px 0 8px 0;
  color: #6b7280;
  font-style: italic;
}

/* Forms */
.form { display: grid; gap: 14px; }
.grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
}
.span-2 { grid-column: 1 / -1; }
.form-field { display: grid; gap: 6px; min-width: 0; }
.form-field label {
  font-size: 0.92rem;
  color: #374151;
  font-weight: 500; /* not bold */
}
.form-field input,
.form-field select {
  width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.95rem;
  background: #fff;
  outline: none;
  box-sizing: border-box;
}
.form-field input:focus,
.form-field select:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
.wide-select { width: 100%; min-width: 260px; }

/* Input row (password show/hide) */
.input-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}

/* Buttons */
.btn {
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
}
.btn.primary {
  background: #4f46e5;
  color: #fff;
}
.btn.primary:hover { background: #4338ca; }
.btn.ghost {
  background: #f3f4f6;
  color: #111827;
  border-color: #e5e7eb;
}
.btn.ghost:hover { background: #e5e7eb; }

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

/* Messages */
.msg { text-align: center; margin-top: 4px; font-size: 0.95rem; }
.msg.ok { color: #16a34a; }
.msg.err { color: #dc2626; }

/* Table */
.table-wrap {
  max-height: 56vh;
  overflow-y: auto;
  overflow-x: hidden; /* prevent horizontal scroll */
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  table-layout: fixed; /* makes wrapping predictable */
}
.table th, .table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: top;
  /* NOT bold for table headers/cells, and wrap text */
  font-weight: 500;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.table thead th {
  background: #f9fafb;
  color: #374151;
}

/* Wrap helper (applied to text cells) */
.wrap {
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: anywhere !important;
}

/* Role cell + select appearance */
.role-td {
  width: 180px;
  vertical-align: middle;
}
.role-select-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.role-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  width: 100%;
  min-width: 160px;
  height: 38px;
  line-height: 38px;
  padding: 0 36px 0 12px; /* space for caret */
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  font-size: 0.95rem;
  color: #111827;
  box-sizing: border-box;
}
.role-select:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
  outline: none;
}
.select-caret {
  position: absolute;
  right: 10px;
  pointer-events: none;
  font-size: 0.9rem;
  color: #6b7280;
}

/* Dialog */
.dialog {
  position: fixed; inset: 0; display: grid; place-items: center;
  background: rgba(0,0,0,0.45);
  z-index: 50;
}
.dialog-box {
  background: #fff;
  border-radius: 12px;
  padding: 18px 16px;
  width: min(420px, 90vw);
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  text-align: center;
}
.dialog-actions { display: flex; gap: 10px; justify-content: center; margin-top: 12px; }

/* Responsive */
@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: static; display: flex; gap: 8px; }
  .tab-btn { flex: 1; text-align: center; }
  .grid-2 { grid-template-columns: 1fr; }
  .kv { grid-template-columns: 140px 1fr; }
  .table-wrap { max-height: 50vh; }
}
</style>
