<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="logo-container">
        <img src="../assets/logo.png" alt="case-e" class="logo" />
      </div>

      <template v-if="stage === 'lookup'">
        <h1>Forgot password</h1>
        <p class="intro">Enter the username you use to sign in.</p>
        <form @submit.prevent="lookupAccount">
          <div class="form-group">
            <label for="reset-username">Username</label>
            <input
              id="reset-username"
              v-model.trim="username"
              type="text"
              autocomplete="username"
              required
              maxlength="50"
              placeholder="Enter your username"
            />
          </div>
          <button class="primary" type="submit" :disabled="busy">
            {{ busy ? "Checking…" : "Continue" }}
          </button>
        </form>
      </template>

      <template v-else-if="stage === 'confirm'">
        <h1>Confirm email</h1>
        <p class="intro">
          Send a password-reset link to <strong>{{ maskedEmail }}</strong>?
        </p>
        <button class="primary" type="button" :disabled="busy" @click="sendResetEmail">
          {{ busy ? "Sending…" : "Send reset link" }}
        </button>
        <button class="secondary" type="button" :disabled="busy" @click="startAgain">
          Use another username
        </button>
      </template>

      <template v-else>
        <h1>Check your email</h1>
        <p class="intro">
          A one-time password-reset link was sent to <strong>{{ maskedEmail }}</strong>.
          The link will expire shortly.
        </p>
      </template>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <router-link class="back-link" to="/login">Back to login</router-link>
    </div>
    <BuildInfoFooter class="build-footer" />
  </div>
</template>

<script>
import axios from "axios";
import BuildInfoFooter from "@/components/BuildInfoFooter.vue";

const envBase = (process.env.VUE_APP_API_URL || "").trim();
const API_BASE_URL = envBase ? envBase.replace(/\/+$/, "") : "";

export default {
  name: "ForgotPasswordComponent",
  components: { BuildInfoFooter },
  data() {
    return {
      username: "",
      maskedEmail: "",
      confirmationToken: "",
      stage: "lookup",
      busy: false,
      error: "",
    };
  },
  methods: {
    errorMessage(err, fallback) {
      return err.response?.data?.detail || fallback;
    },
    async lookupAccount() {
      this.error = "";
      this.busy = true;
      try {
        const response = await axios.post(`${API_BASE_URL}/users/password-reset/lookup`, {
          username: this.username,
        });
        if (!response.data?.eligible) {
          this.error = "No password-recovery email is available for that username.";
          return;
        }
        this.maskedEmail = response.data.masked_email;
        this.confirmationToken = response.data.confirmation_token;
        this.stage = "confirm";
      } catch (err) {
        this.error = this.errorMessage(err, "Unable to check the account. Try again later.");
      } finally {
        this.busy = false;
      }
    },
    async sendResetEmail() {
      this.error = "";
      this.busy = true;
      try {
        await axios.post(`${API_BASE_URL}/users/password-reset/request`, {
          confirmation_token: this.confirmationToken,
        });
        this.confirmationToken = "";
        this.stage = "sent";
      } catch (err) {
        this.error = this.errorMessage(err, "Unable to send the reset email. Try again later.");
      } finally {
        this.busy = false;
      }
    },
    startAgain() {
      this.stage = "lookup";
      this.maskedEmail = "";
      this.confirmationToken = "";
      this.error = "";
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
.form-group { margin: 24px 0; text-align: left; }
label { display: block; margin-bottom: 8px; font-weight: 600; }
input {
  width: 100%;
  padding: 11px 12px;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 1rem;
}
button { width: 100%; margin-top: 10px; padding: 11px 14px; border-radius: 6px; cursor: pointer; }
button:disabled { cursor: wait; opacity: 0.7; }
.primary { border: 1px solid #2563eb; background: #2563eb; color: white; }
.secondary { border: 1px solid #94a3b8; background: white; color: #334155; }
.back-link { display: inline-block; margin-top: 22px; color: #2563eb; }
.error { margin-top: 18px; color: #b91c1c; line-height: 1.4; }
.build-footer { position: fixed; right: 0; bottom: 0; left: 0; }
</style>
