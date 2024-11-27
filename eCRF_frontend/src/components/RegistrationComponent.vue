<template>
  <div class="registration-page">
    <div class="registration-container">
      <div class="logo-container">
        <img src="../assets/logo.png" alt="Logo" class="logo" />
      </div>
      <h1>Register</h1>
      <form @submit.prevent="handleRegistration" class="registration-form">
        <div :class="['form-group', { 'error-group': errors.first_name }]">
          <label for="first_name">First Name<span class="mandatory">*</span></label>
          <input
            type="text"
            id="first_name"
            v-model="first_name"
            placeholder="Enter your first name"
          />
        </div>
        <div :class="['form-group', { 'error-group': errors.last_name }]">
          <label for="last_name">Last Name<span class="mandatory">*</span></label>
          <input
            type="text"
            id="last_name"
            v-model="last_name"
            placeholder="Enter your last name"
          />
        </div>
        <div :class="['form-group', { 'error-group': errors.email }]">
          <label for="email">Email<span class="mandatory">*</span></label>
          <input
            type="email"
            id="email"
            v-model="email"
            placeholder="Enter your email"
          />
        </div>
        <div :class="['form-group', { 'error-group': errors.username }]">
          <label for="username">Username<span class="mandatory">*</span></label>
          <input
            type="text"
            id="username"
            v-model="username"
            placeholder="Choose a username"
          />
        </div>
        <div :class="['form-group', { 'error-group': errors.password }]">
          <label for="password">Password<span class="mandatory">*</span></label>
          <div class="password-wrapper">
            <input
              :type="showPassword ? 'text' : 'password'"
              id="password"
              v-model="password"
              placeholder="Create a password"
            />
            <button type="button" class="toggle-password" @click="togglePasswordVisibility">
              {{ showPassword ? "Hide" : "Show" }}
            </button>
          </div>
          <p class="password-hint">Password must be at least 8 characters, include a number, and a special character.</p>
        </div>
        <div :class="['form-group', { 'error-group': errors.confirm_password }]">
          <label for="confirm_password">Confirm Password<span class="mandatory">*</span></label>
          <input
            type="password"
            id="confirm_password"
            v-model="confirm_password"
            placeholder="Confirm your password"
          />
        </div>
        <button type="submit" class="btn-register">Register</button>
      </form>
      <p v-if="message" class="success">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn-login-link" @click="goToLogin">Already have an account? Login</button>
    </div>
  </div>
</template>

<script>
export default {
  name: "RegistrationComponent",
  data() {
    return {
      first_name: "",
      last_name: "",
      email: "",
      username: "",
      password: "",
      confirm_password: "",
      message: null,
      error: null,
      showPassword: false,
      errors: {
        first_name: false,
        last_name: false,
        email: false,
        username: false,
        password: false,
        confirm_password: false,
      },
    };
  },
  methods: {
    togglePasswordVisibility() {
      this.showPassword = !this.showPassword;
    },
    validatePassword(password) {
      const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
      return passwordRegex.test(password);
    },
    handleValidation() {
      // Reset all errors
      this.errors = {
        first_name: !this.first_name.trim(),
        last_name: !this.last_name.trim(),
        email: !this.email.trim(),
        username: !this.username.trim(),
        password: !this.validatePassword(this.password),
        confirm_password: !this.confirm_password.trim() || this.password !== this.confirm_password,
      };

      // Return true if no errors
      return !Object.values(this.errors).some((hasError) => hasError);
    },
    async handleRegistration() {
      this.error = null;
  this.message = null;

  try {
    const success = await this.$store.dispatch("register", {
      first_name: this.first_name,
      last_name: this.last_name,
      email: this.email,
      username: this.username,
      password: this.password,
    });

    if (success) {
      this.message = "Registration successful! Redirecting to login...";
      setTimeout(() => {
        this.$router.push("/");
      }, 2000);
    }
  } catch (err) {
    // Display user-friendly error messages
    this.error = err.message || "An error occurred during registration.";

}
    },
    goToLogin() {
      this.$router.push("/");
    },
  },
};
</script>

<style scoped>
/* General Reset */
.registration-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f4f4f9;
  font-family: Arial, sans-serif;
}

.registration-container {
  width: 450px;
  padding: 30px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  text-align: center;
}

/* Logo Styling */
.logo-container {
  text-align: left;
  margin-bottom: 20px;
}

.logo {
  width: 120px;
  height: auto;
}

/* Form Styling */
.registration-form .form-group {
  margin-bottom: 20px;
  text-align: left;
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

.password-wrapper {
  display: flex;
  align-items: center;
  position: relative;
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

.password-hint {
  font-size: 12px;
  color: #777;
  margin-top: 5px;
}

/* Error Highlighting */
.error-group input {
  border-color: red;
}

.error-group label {
  color: red;
}

/* Mandatory Fields */
.mandatory {
  color: red;
  font-size: 14px;
  margin-left: 5px;
}

/* Button Styling */
.btn-register {
  width: 100%;
  padding: 10px;
  font-size: 16px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-register:hover {
  background-color: #218838;
}

.btn-login-link {
  margin-top: 20px;
  padding: 10px;
  font-size: 14px;
  background: none;
  border: 1px solid #007bff;
  color: #007bff;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-login-link:hover {
  background: #007bff;
  color: white;
}

/* Success Message */
.success {
  margin-top: 15px;
  color: #28a745;
  font-size: 14px;
}

/* Error Message */
.error {
  margin-top: 15px;
  color: red;
  font-size: 14px;
}
</style>
