<template>
  <div class="login-page">
    <div class="login-container">
      <div class="logo-container">
        <img src="../assets/logo.png" alt="Logo" class="logo" />
      </div>
      <h1>Login</h1>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">Username</label>
          <input type="text" id="username" v-model="username" placeholder="Enter your username" />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input type="password" id="password" v-model="password" placeholder="Enter your password" />
        </div>
        <button type="submit" class="btn-login">Login</button>
      </form>
      <p>
        New user? <router-link to="/register" class="register-link">Register here</router-link>
      </p>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: "LoginComponent",
  data() {
    return {
      username: "",
      password: "",
      error: null,
    };
  },
  methods: {
    async handleLogin() {
      const success = await this.$store.dispatch("login", {
        username: this.username,
        password: this.password,
      });
      if (success) {
        this.$router.push("/dashboard");
      } else {
        this.error = "Invalid username or password.";
      }
    },
  },
};
</script>

<style scoped>
/* General Styling */
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f4f4f9;
  font-family: Arial, sans-serif;
}

.login-container {
  width: 400px;
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
.login-form .form-group {
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

/* Button Styling */
.btn-login {
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

.btn-login:hover {
  background-color: #0056b3;
}

/* Links */
.register-link {
  color: #007bff;
  text-decoration: none;
}

.register-link:hover {
  text-decoration: underline;
}

/* Error Message */
.error {
  margin-top: 10px;
  color: red;
  font-size: 14px;
}
</style>
