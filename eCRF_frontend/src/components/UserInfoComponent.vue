<template>
  <div class="user-info-container">
    <h1>User Info</h1>

    <div class="user-details">
      <p><strong>Username:</strong> {{ user?.username }}</p>
      <p><strong>First Name:</strong> {{ user?.profile?.first_name }}</p>
      <p><strong>Last Name:</strong> {{ user?.profile?.last_name }}</p>
      <p><strong>Email:</strong> {{ user?.email }}</p>
    </div>
    <div class="settings-button">
      <button @click="goToSettings" class="btn-settings">Study Settings</button>
    </div>
    <div class="change-password">
      <h2>Change Password</h2>
      <form @submit.prevent="handleChangePassword">
        <div class="form-group">
          <label for="new_password">New Password</label>
          <div class="password-wrapper">
            <input
              :type="showPassword ? 'text' : 'password'"
              id="new_password"
              v-model="newPassword"
              placeholder="Enter new password"
            />
            <button type="button" class="toggle-password" @click="togglePasswordVisibility">
              {{ showPassword ? "Hide" : "Show" }}
            </button>
          </div>
        </div>
        <div class="form-group">
          <label for="confirm_password">Confirm Password</label>
          <input
            type="password"
            id="confirm_password"
            v-model="confirmPassword"
            placeholder="Confirm new password"
          />
        </div>
        <button type="submit" class="btn-change-password">Change Password</button>
      </form>
      <p v-if="passwordMessage" class="message">{{ passwordMessage }}</p>
      <p v-if="passwordError" class="error">{{ passwordError }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: "UserInfoComponent",
  data() {
    return {
      user: null,
      newPassword: "",
      confirmPassword: "",
      showPassword: false,
      passwordMessage: null,
      passwordError: null,
    };
  },
  computed: {
    userFromStore() {
      return this.$store.getters.getUser;
    },
  },
  created() {
    this.user = this.userFromStore;
    if (!this.user) {
      console.warn("User not found in Vuex store. Fetching from backend...");
      this.$store.dispatch("fetchUserData").then(() => {
        this.user = this.$store.getters.getUser;
      });
    }
  },
  methods: {
    goToSettings() {
      this.$router.push("/settings");
    },
    validatePassword(password) {
      const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
      return passwordRegex.test(password);
    },
    async handleChangePassword() {
      this.passwordMessage = null;
      this.passwordError = null;
      if (!this.newPassword || !this.confirmPassword) {
        this.passwordError = "All fields are required.";
        return;
      }
      if (!this.validatePassword(this.newPassword)) {
        this.passwordError =
          "Password must be at least 8 characters, include a number, and a special character.";
        return;
      }
      if (this.newPassword !== this.confirmPassword) {
        this.passwordError = "Passwords do not match.";
        return;
      }
      try {
        const success = await this.$store.dispatch("changePassword", {
          newPassword: this.newPassword,
        });
        if (success) {
          this.passwordMessage = "Password changed successfully.";
          this.newPassword = "";
          this.confirmPassword = "";
        } else {
          this.passwordError = "Failed to change password.";
        }
      } catch (error) {
        this.passwordError = "An error occurred while changing your password.";
        console.error(error);
      }
    },
    togglePasswordVisibility() {
      this.showPassword = !this.showPassword;
    },
  },
};
</script>

<style scoped>
/* ... existing styles ... */
.settings-button {
  text-align: center;
  margin: 20px 0;
}
.btn-settings {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #28a745;
  border: none;
  color: #fff;
  border-radius: 5px;
  cursor: pointer;
}
.btn-settings:hover {
  background-color: #218838;
}

<style scoped>
.user-info-container {
  max-width: 600px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1, h2 {
  text-align: center;
  color: #333;
}

.user-details {
  margin-bottom: 30px;
}

p {
  font-size: 16px;
  color: #555;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  font-size: 14px;
  color: #555;
  margin-bottom: 5px;
}

input {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}

input:focus {
  border-color: #007bff;
  outline: none;
}

/* Password Wrapper Styling */
.password-wrapper {
  display: flex;
  align-items: center;
}

.toggle-password {
  margin-left: 10px;
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  font-size: 14px;
}

.toggle-password:hover {
  text-decoration: underline;
}

.btn-change-password {
  width: 100%;
  padding: 10px;
  font-size: 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-change-password:hover {
  background-color: #0056b3;
}

.message {
  color: green;
  font-size: 14px;
}

.error {
  color: red;
  font-size: 14px;
}
</style>