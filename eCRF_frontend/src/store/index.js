import { createStore } from "vuex";
import axios from "axios";

// Dynamically set the base URL based on environment variables or defaults
const API_BASE_URL = process.env.VUE_APP_API_URL || "http://127.0.0.1:8000";

const store = createStore({
  state: {
    user: null, // User object after login
    token: null, // JWT token after successful login
  },
  mutations: {
    setUser(state, user) {
      state.user = user;
    },
    setToken(state, token) {
      state.token = token;
    },
    clearAuth(state) {
      state.user = null;
      state.token = null;
    },
  },
  actions: {
    async login({ commit }, payload) {
      console.log("Attempting login with payload:", payload);

      try {
        // Step 1: Send login request to backend
        const response = await axios.post(`${API_BASE_URL}/users/login`, payload);
        console.log("Login successful, API response:", response.data);

        const { access_token } = response.data;

        // Step 2: Store token in Vuex and localStorage
        commit("setToken", access_token);
        localStorage.setItem("token", access_token);

        // Step 3: Fetch user data after successful login
        const userResponse = await axios.get(`${API_BASE_URL}/users/me`, {
          headers: { Authorization: `Bearer ${access_token}` },
        });

        console.log("Fetched user data:", userResponse.data);

        // Step 4: Store user data in Vuex
        commit("setUser", userResponse.data);

        return true; // Signal success to the component
      } catch (error) {
        console.error("Login failed, error from API:", error.response?.data || error.message);
        return false; // Signal failure to the component
      }
    },

    async register(_, payload) {
      console.log("Registering user with payload:", payload);

      try {
        // Send registration request to backend
        const response = await axios.post(`${API_BASE_URL}/users/register`, payload);
        console.log("Registration successful, API response:", response.data);

        return true; // Signal success to the component
      } catch (error) {
        if (error.response?.status === 400) {
          console.error("Registration failed: Duplicate username or email.");
          throw new Error("Username or email already exists. Please choose another.");
        }
        console.error("Unexpected registration error:", error.response?.data || error.message);
        throw new Error("An unexpected error occurred during registration.");
      }
    },

    async changePassword({ state }, payload) {
      console.log("Changing password:", payload);

      try {
        const response = await axios.post(
          `${API_BASE_URL}/users/change-password`,
          {
            username: state.user.username, // Use logged-in user details
            new_password: payload.newPassword,
          },
          {
            headers: { Authorization: `Bearer ${state.token}` },
          }
        );

        console.log("Password changed successfully:", response.data);
        return true; // Signal success
      } catch (error) {
        console.error("Error changing password:", error.response?.data || error.message);
        return false; // Signal failure
      }
    },

    async fetchUserData({ commit }) {
      const token = localStorage.getItem("token");
      if (!token) {
        console.warn("No token found in localStorage. Cannot fetch user data.");
        return false;
      }

      try {
        const response = await axios.get(`${API_BASE_URL}/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        console.log("Fetched user data:", response.data);
        commit("setUser", response.data);
        return true;
      } catch (error) {
        console.error("Failed to fetch user data:", error.response?.data || error.message);
        return false;
      }
    },

    logout({ commit }) {
      console.log("Logging out...");
      commit("clearAuth"); // Clear Vuex state
      localStorage.removeItem("token"); // Remove token from localStorage
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.token, // Check if user is authenticated
    getUser: (state) => state.user, // Get current user data
  },
});

export default store;
