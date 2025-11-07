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
          <div class="header-row">
            <h2 class="section-title">User Management</h2>
            <button
              class="icon-btn"
              type="button"
              aria-label="User roles information"
              title="What do the roles mean?"
              @click="showRoleInfo = true"
            >
              <i :class="icons.info" class="info-icon" aria-hidden="true"></i>
            </button>
          </div>

          <div class="section-scroll">
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

            <div class="section-box">
              <h3 class="sub-title">Existing Users</h3>
              <div class="table-wrap">
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

            <div v-if="showRoleInfo" class="dialog">
              <div class="dialog-box">
                <h3 class="dialog-title">User Roles & Permissions</h3>
                <div class="dialog-text left">
                  <ul class="role-list">
                    <li>
                      <strong>Administrator</strong> - Full system-wide access. Can manage users and all studies.
                      Implicit access to every study. Cannot be granted per-study access (not needed).
                    </li>
                    <li>
                      <strong>Principal Investigator</strong> - For assigned studies, can view data and typically
                      manage study structure when permitted. Can also create and edit their own studies. No system user management rights.
                    </li>
                    <li>
                      <strong>Investigator</strong> - For assigned studies, can view and add data. Cannot edit study structure.
                    </li>
                    <li>
                      <strong>No Access</strong> - Account exists but cannot access the application.
                    </li>
                  </ul>
                </div>
                <div class="dialog-actions">
                  <button class="btn primary" @click="showRoleInfo = false">OK</button>
                </div>
              </div>
            </div>
            <!-- /Role info dialog -->
          </div>
        </section>

        <!-- STUDY ACCESS MANAGEMENT (Admin only) -->
        <section v-else-if="currentTab === 'studyAccess' && isAdmin" class="section">
          <h2 class="section-title">Study Access Management</h2>

          <div class="section-scroll">
            <div class="section-box">
              <h3 class="sub-title">Select Study</h3>
              <div class="form grid-2">
                <div class="form-field span-2">
                  <label>Study</label>
                  <select v-model="selectedStudyId" class="wide-select" @change="onStudyChange">
                    <option value="" disabled>Select a study…</option>
                    <option v-for="s in studies" :key="s.id" :value="s.id">
                      {{ s.study_name }} (ID: {{ s.id }})
                    </option>
                  </select>
                </div>
              </div>
              <p v-if="studyAccessMsg" class="msg ok">{{ studyAccessMsg }}</p>
              <p v-if="studyAccessErr" class="msg err">{{ studyAccessErr }}</p>
            </div>

            <div v-if="selectedStudyId" class="section-box">
              <h3 class="sub-title">
                Grant or Update Access — <span class="emph">{{ selectedStudyName }}</span>
              </h3>

              <div class="hint">
                Admin users already have full access across all studies and are hidden from the user list.
              </div>

              <form @submit.prevent="grantOrUpdateAccess" class="form grid-2">
                <div class="form-field span-2">
                  <label>User</label>
                  <select v-model="selectedUserId" class="wide-select" required>
                    <option value="" disabled>Select a user…</option>
                    <option
                      v-for="u in grantableUsers"
                      :key="u.id"
                      :value="u.id"
                      :disabled="u.id === selectedStudyOwnerId"
                    >
                      {{ u.username }} — {{ u.profile.first_name }} {{ u.profile.last_name }}
                      ({{ u.email }}) <span v-if="u.id === selectedStudyOwnerId"> — Owner</span>
                    </option>
                  </select>
                </div>

                <div class="form-field span-2">
                  <label>Permissions</label>
                  <div class="perm-row">
                    <label class="chk">
                      <input type="checkbox" v-model="permView" />
                      <span>View</span>
                    </label>
                    <label class="chk">
                      <input type="checkbox" v-model="permAdd" />
                      <span>Add Data</span>
                    </label>
                    <label class="chk">
                      <input type="checkbox" v-model="permEdit" />
                      <span>Edit Study</span>
                    </label>
                  </div>
                </div>

                <div class="form-actions span-2">
                  <button
                    class="btn primary"
                    type="submit"
                    :disabled="!selectedUserId || selectedUserId === selectedStudyOwnerId"
                    :title="selectedUserId === selectedStudyOwnerId ? 'Owner already has access' : ''"
                  >
                    Grant / Update
                  </button>
                </div>
              </form>
            </div>

            <div v-if="selectedStudyId" class="section-box">
              <h3 class="sub-title">Current Access</h3>
              <div class="table-wrap">
                <table class="table">
                  <colgroup>
                    <col />
                    <col />
                    <col />
                    <col style="width: 220px;" />
                    <col style="width: 140px;" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Email</th>
                      <th>Permissions</th>
                      <th>Granted By / At</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="g in studyAccess" :key="g.user_id">
                      <td class="wrap">
                        {{ g.username }} — {{ g.display_name }}
                        <span
                          v-if="g.user_id === selectedStudyOwnerId"
                          class="owner-pill"
                        >Owner</span>
                      </td>
                      <td class="wrap">{{ g.email }}</td>
                      <td class="wrap">
                        <span class="perm-chip" :class="{ on: g.permissions?.view }">View</span>
                        <span class="perm-chip" :class="{ on: g.permissions?.add_data }">Add</span>
                        <span class="perm-chip" :class="{ on: g.permissions?.edit_study }">Edit</span>
                      </td>
                      <td class="wrap">
                        <div>{{ g.created_by_display || "—" }}</div>
                        <div class="muted">{{ formatDate(g.created_at) }}</div>
                      </td>
                      <td>
                        <button
                          class="btn ghost"
                          :disabled="g.user_id === selectedStudyOwnerId"
                          :title="g.user_id === selectedStudyOwnerId ? 'Owner access cannot be revoked' : ''"
                          @click="openRevokeDialog(g.user_id, g.username || g.display_name)"
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                    <tr v-if="studyAccess.length === 0">
                      <td colspan="5" class="muted">No access granted yet.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-if="showRevokeDialog" class="dialog">
              <div class="dialog-box">
                <h3 class="dialog-title">Revoke Study Access</h3>
                <p class="dialog-text">
                  Are you sure you want to revoke <strong>{{ revokeTargetDisplay }}</strong>'s access to
                  <strong>{{ selectedStudyName }}</strong>?
                </p>
                <div class="dialog-actions">
                  <button class="btn primary" @click="confirmRevokeAccess">Yes, Revoke</button>
                  <button class="btn ghost" @click="closeRevokeDialog">Cancel</button>
                </div>
              </div>
            </div>

          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";
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

      // Role info dialog
      showRoleInfo: false,

      // Study Access (Admin)
      studies: [],
      selectedStudyId: "",
      studyAccess: [],
      allUsers: [],
      selectedUserId: "",
      permView: true,
      permAdd: true,
      permEdit: false,
      studyAccessMsg: null,
      studyAccessErr: null,

      // Revoke dialog
      showRevokeDialog: false,
      revokeTargetId: null,
      revokeTargetDisplay: "",
      icons,
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
      if (this.isAdmin) {
        tabs.push({ key: "management", label: "User Management" });
        tabs.push({ key: "studyAccess", label: "Study Access" });
      }
      return tabs;
    },
    selectedStudy() {
      const id = Number(this.selectedStudyId || 0);
      return this.studies.find((s) => Number(s.id) === id) || null;
    },
    selectedStudyName() {
      return this.selectedStudy ? this.selectedStudy.study_name : "this study";
    },
    selectedStudyOwnerId() {
      return this.selectedStudy ? Number(this.selectedStudy.created_by || 0) : 0;
    },
    grantableUsers() {
      const seen = new Set();
      const list = (this.allUsers || []).filter((u) => {
        const isAdmin = (u?.profile?.role || "") === "Administrator";
        if (isAdmin) return false;
        const key = u.id;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      return list.filter((u) => u.id !== this.selectedStudyOwnerId);
    },
  },
  async created() {
    this.user = this.userFromStore;
    if (!this.user) {
      await this.$store.dispatch("fetchUserData");
      this.user = this.$store.getters.getUser;
    }
    if (this.isAdmin) {
      await Promise.all([this.fetchUsers(), this.fetchAllUsers(), this.fetchStudies()]);
    }
  },
  methods: {
    authHeader() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },

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

    async fetchUsers() {
      this.userMgmtError = null;
      try {
        const resp = await axios.get("/users/admin/users", { headers: this.authHeader() });
        this.users = resp.data;
      } catch (err) {
        this.userMgmtError = err.response?.data?.detail || err.message;
      }
    },
    async fetchAllUsers() {
      try {
        const resp = await axios.get("/users/admin/users", { headers: this.authHeader() });
        this.allUsers = resp.data || [];
      } catch {
        this.allUsers = [];
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
          { headers: this.authHeader() }
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
        this.fetchAllUsers();
      } catch (err) {
        this.userMgmtError = err.response?.data?.detail || err.message;
      }
    },

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
          { headers: this.authHeader() }
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

    async fetchStudies() {
      try {
        const resp = await axios.get("/forms/studies", { headers: this.authHeader() });
        this.studies = resp.data || [];
      } catch {
        this.studies = [];
      }
    },
    async onStudyChange() {
      this.studyAccessMsg = this.studyAccessErr = null;
      this.selectedUserId = "";
      await this.fetchStudyAccess();
    },
    async fetchStudyAccess() {
      if (!this.selectedStudyId) {
        this.studyAccess = [];
        return;
      }
      try {
        const resp = await axios.get(`/forms/studies/${this.selectedStudyId}/access`, {
          headers: this.authHeader(),
        });
        this.studyAccess = resp.data || [];
      } catch (err) {
        this.studyAccessErr = err.response?.data?.detail || err.message;
        this.studyAccess = [];
      }
    },
    async grantOrUpdateAccess() {
      this.studyAccessMsg = this.studyAccessErr = null;
      const uid = Number(this.selectedUserId || 0);
      if (!this.selectedStudyId || !uid) {
        this.studyAccessErr = "Select a study and a user.";
        return;
      }
      if (uid === this.selectedStudyOwnerId) {
        this.studyAccessErr = "Owner already has full access.";
        return;
      }
      const sel = this.allUsers.find((u) => u.id === uid);
      if ((sel?.profile?.role || "") === "Administrator") {
        this.studyAccessErr = "Administrators already have full access; no grant is needed.";
        return;
      }
      try {
        await axios.post(
          `/forms/studies/${this.selectedStudyId}/access`,
          {
            user_id: uid,
            permissions: {
              view: !!this.permView,
              add_data: !!this.permAdd,
              edit_study: !!this.permEdit,
            },
          },
          { headers: this.authHeader() }
        );
        this.studyAccessMsg = "Access granted/updated.";
        await this.fetchStudyAccess();
      } catch (err) {
        this.studyAccessErr = err.response?.data?.detail || err.message;
      }
    },
    openRevokeDialog(userId, display) {
      if (Number(userId) === this.selectedStudyOwnerId) return;
      this.revokeTargetId = Number(userId);
      this.revokeTargetDisplay = display || `User #${userId}`;
      this.showRevokeDialog = true;
    },
    closeRevokeDialog() {
      this.showRevokeDialog = false;
      this.revokeTargetId = null;
      this.revokeTargetDisplay = "";
    },
    async confirmRevokeAccess() {
      try {
        await axios.delete(`/forms/studies/${this.selectedStudyId}/access/${this.revokeTargetId}`, {
          headers: this.authHeader(),
        });
        await this.fetchStudyAccess();
      } catch (err) {
        this.studyAccessErr = err.response?.data?.detail || err.message;
      } finally {
        this.closeRevokeDialog();
      }
    },

    formatDate(dt) {
      if (!dt) return "—";
      try {
        const d = new Date(dt);
        return d.toLocaleString();
      } catch {
        return String(dt);
      }
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

.layout {
  display: grid;
  grid-template-columns: 1fr;         /* single column */
  grid-template-rows: auto 1fr;       /* tabbar row + content row */
  gap: 16px;
}

/* Sidebar becomes a horizontal tabbar */
.sidebar {
  grid-column: 1 / -1;
  grid-row: 1;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 8px;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 6px;
  position: sticky;
  top: 16px;
  z-index: 5;
  overflow-x: auto;           /* allow horizontal scroll if many tabs */
  scrollbar-width: thin;
  width: 100%;
}

/* Tab button: horizontal pill */
.tab-btn {
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: #f9fafb;
  cursor: pointer;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  flex: 1 1 0;
  max-width: none;
  text-align: center;
}
.tab-btn:hover {
  background: #f3f4f6;
}
.tab-btn.active {
  background: #eef2ff;
  border-color: #c7d2fe;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}

/* Content area */
.content {
  grid-column: 1 / -1;
  grid-row: 2;
  display: grid;
  gap: 14px;
}
.section { display: grid; gap: 14px; }

/* ONLY container headings are bold */
.section-title {
  text-align: center;
  margin: 0 0 6px 0;
  font-size: 1.4rem;
  font-weight: 700;
  color: #111827;
}
.sub-title {
  margin: 0 0 8px 0;
  font-size: 1.05rem;
  font-weight: 500;
  color: #1f2937;
}
.emph { font-weight: 600; }

/* Header row with icon on right */
.header-row {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.icon-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  cursor: pointer;
  display: grid;
  place-items: center;
  padding: 0;
}
.icon-btn:hover .info-icon { color: #4338ca; }
.info-icon { font-size: 14px; color: #4b5563; line-height: 1; }

/* Tab-level scroll for large tabs */
.section-scroll {
  display: grid;
  gap: 14px;
  max-height: 72vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 2px;
}

/* Generic scrollable box */
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
  font-weight: 500;
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

/* Permissions row */
.perm-row {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}
.chk { display: inline-flex; align-items: center; gap: 8px; user-select: none; }
.chk input { transform: translateY(1px); }

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
.btn.primary { background: #4f46e5; color: #fff; }
.btn.primary:hover { background: #4338ca; }
.btn.ghost { background: #f3f4f6; color: #111827; border-color: #e5e7eb; }
.btn.ghost:hover { background: #e5e7eb; }

.form-actions { display: flex; gap: 10px; justify-content: center; }

/* Messages */
.msg { text-align: center; margin-top: 4px; font-size: 0.95rem; }
.msg.ok { color: #16a34a; }
.msg.err { color: #dc2626; }
.hint { color: #6b7280; font-size: 0.9rem; margin-bottom: 8px; }

/* Table */
.table-wrap {
  max-height: 56vh;
  overflow-y: auto;
  overflow-x: hidden;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  table-layout: fixed;
}
.table th, .table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: top;
  font-weight: 500;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.table thead th { background: #f9fafb; color: #374151; }

/* Wrap helper */
.wrap { white-space: normal !important; word-break: break-word !important; overflow-wrap: anywhere !important; }

/* Role cell + select */
.role-td { width: 180px; vertical-align: middle; }
.role-select-wrap { position: relative; display: flex; align-items: center; }
.role-select {
  appearance: none; -webkit-appearance: none; -moz-appearance: none;
  width: 100%; min-width: 160px; height: 38px; line-height: 38px;
  padding: 0 36px 0 12px;
  border: 1px solid #d1d5db; border-radius: 8px; background: #fff;
  font-size: 0.95rem; color: #111827; box-sizing: border-box;
}
.role-select:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.15); outline: none; }
.select-caret { position: absolute; right: 10px; pointer-events: none; font-size: 0.9rem; color: #6b7280; }

/* Permission chips */
.perm-chip {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px 6px 2px 0;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 0.85rem;
  color: #6b7280;
}
.perm-chip.on { border-color: #c7d2fe; background: #eef2ff; color: #3730a3; }
.owner-pill {
  margin-left: 8px;
  padding: 0 8px;
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #f59e0b;
  border-radius: 999px;
  font-size: 0.75rem;
}

/* Muted text */
.muted { color: #6b7280; font-size: 0.85rem; }

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
  width: min(480px, 92vw);
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  text-align: center;
}
.dialog-title { margin: 0 0 8px 0; font-weight: 700; font-size: 1.15rem; }
.dialog-text { margin: 0 0 14px 0; color: #374151; }
.dialog-text.left { text-align: left; }
.dialog-actions { display: flex; gap: 10px; justify-content: center; }
.role-list { margin: 0; padding-left: 18px; }
.role-list li { margin: 6px 0; }

/* Responsive (tabs already horizontal; just ensure spacing) */
@media (max-width: 980px) {
  .sidebar {
    border-radius: 10px;
    gap: 6px;
    top: 8px;
  }
  .tab-btn { padding: 8px 12px; font-size: 0.95rem; }
  .kv { grid-template-columns: 140px 1fr; }
  .table-wrap { max-height: 50vh; }
  @media (max-width: 520px) {
  .tab-btn { flex: 1 0 160px; } /* equal-ish width, allow scroll */
}
}
</style>
