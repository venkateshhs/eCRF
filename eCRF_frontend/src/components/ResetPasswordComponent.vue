<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="logo-container">
        <img src="../assets/logo.png" alt="case-e" class="logo" />
      </div>

      <template v-if="complete">
        <h1>Password updated</h1>
        <p class="intro">Your password has been reset. You can now sign in.</p>
        <router-link class="primary link-button" to="/login">Go to login</router-link>
      </template>

      <template v-else>
        <h1>Choose a new password</h1>
        <p v-if="username" class="account-name">
          Account: <strong>{{ username }}</strong>
        </p>
        <p class="intro">Use at least 8 characters, including a number and a special character.</p>
        <form @submit.prevent="resetPassword">
          <div class="form-group">
            <label for="new-password">New password</label>
            <input id="new-password" v-model="newPassword" type="password" autocomplete="new-password" required />
          </div>
          <div class="form-group">
            <label for="confirm-password">Confirm new password</label>
            <input id="confirm-password" v-model="confirmPassword" type="password" autocomplete="new-password" required />
          </div>
          <button class="primary" type="submit" :disabled="busy || !token">
            {{ busy ? "Updating…" : "Reset password" }}
          </button>
        </form>
        <router-link class="back-link" to="/forgot-password">Request a new link</router-link>
      </template>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
    <BuildInfoFooter class="build-footer" />
  </div>
</template>

<script>
import axios from "axios";
import BuildInfoFooter from "@/components/BuildInfoFooter.vue";

const envBase = (process.env.VUE_APP_API_URL || "").trim();
const API_BASE_URL = envBase ? envBase.replace(/\/+$/, "") : "";
const PASSWORD_RE = /^(?=.*[0-9])(?=.*[!@#$%^&*])\S{8,}$/;

export default {
  name: "ResetPasswordComponent",
  components: { BuildInfoFooter },
  data() {
    return {
      token: "",
      username: "",
      newPassword: "",
      confirmPassword: "",
      busy: false,
      complete: false,
      error: "",
    };
  },
  created() {
    this.token = typeof this.$route.query.token === "string" ? this.$route.query.token : "";
    if (!this.token) {
      this.error = "This password reset link is incomplete. Request a new link.";
    } else {
      this.validateToken();
    }
  },
  methods: {
    async validateToken() {
      try {
        const response = await axios.get(`${API_BASE_URL}/users/password-reset/validate`, {
          params: { token: this.token },
        });
        this.username = response.data?.username || "";
      } catch (err) {
        this.token = "";
        this.error = err.response?.data?.detail || "This password reset link is invalid or expired.";
      }
    },
    async resetPassword() {
      this.error = "";
      if (this.newPassword !== this.confirmPassword) {
        this.error = "Passwords do not match.";
        return;
      }
      if (!PASSWORD_RE.test(this.newPassword)) {
        this.error = "Password must be at least 8 characters and include a number and a special character.";
        return;
      }

      this.busy = true;
      try {
        await axios.post(`${API_BASE_URL}/users/password-reset/confirm`, {
          token: this.token,
          new_password: this.newPassword,
        });
        this.complete = true;
        this.token = "";
        this.newPassword = "";
        this.confirmPassword = "";
      } catch (err) {
        this.error = err.response?.data?.detail || "Unable to reset the password. Request a new link.";
      } finally {
        this.busy = false;
      }
    },
  },
};
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 32px 20px 58px;
  background: #f4f4f9;
}
.auth-card {
  width: min(420px, 100%);
  padding: 30px;
  box-sizing: border-box;
  border-radius: 10px;
  background: white;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  text-align: center;
}
.logo-container { text-align: left; margin-bottom: 20px; }
.logo { width: 150px; height: auto; }
.intro { color: #4b5563; line-height: 1.5; }
.account-name { margin: 18px 0 0; color: #1f2937; }
.form-group { margin: 20px 0; text-align: left; }
label { display: block; margin-bottom: 8px; font-weight: 600; }
input {
  width: 100%;
  padding: 11px 12px;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 1rem;
}
button, .link-button {
  width: 100%;
  display: block;
  margin-top: 10px;
  padding: 11px 14px;
  box-sizing: border-box;
  border-radius: 6px;
  cursor: pointer;
}
button:disabled { cursor: wait; opacity: 0.7; }
.primary { border: 1px solid #2563eb; background: #2563eb; color: white; text-decoration: none; }
.back-link { display: inline-block; margin-top: 22px; color: #2563eb; }
.error { margin-top: 18px; color: #b91c1c; line-height: 1.4; }
.build-footer { position: fixed; right: 0; bottom: 0; left: 0; }
</style>
