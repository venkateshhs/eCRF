import { createStore } from "vuex";
import axios from "axios";
import createPersistedState from "vuex-persistedstate";

// Dynamically set the base URL based on environment variables or defaults
const API_BASE_URL = process.env.VUE_APP_API_URL || "http://127.0.0.1:8000";

const store = createStore({
  state: {
    user: null, // User object after login
    token: null, // JWT token after successful login
    forms: [], // Store all forms
    currentForm: null, // Store the currently selected form for editing/viewing
    studyDetails: null, // Store study details (used in study creation)
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
      state.forms = [];
      state.currentForm = null;
      state.studyDetails = null;
    },
    setForms(state, forms) {
      state.forms = forms;
    },
    setCurrentForm(state, form) {
      state.currentForm = form;
    },
    setStudyDetails(state, payload) {
     state.studyDetails = {
        ...state.studyDetails,
        ...payload
      };
    },
    resetStudyDetails(state) {
      state.studyDetails = {};
    },
  },
  actions: {
    // Login action
    async login({ commit }, payload) {
      console.log("Attempting login with payload:", payload);
      try {
        const response = await axios.post(`${API_BASE_URL}/users/login`, payload);
        console.log("Login successful, API response:", response.data);
        const { access_token } = response.data;
        commit("setToken", access_token);
        console.log("access token:", response.data.access_token);
        localStorage.setItem("access_token", response.data.access_token);
        const userResponse = await axios.get(`${API_BASE_URL}/users/me`, {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        console.log("Fetched user data:", userResponse.data);
        commit("setUser", userResponse.data);
        return true;
      } catch (error) {
        console.error("Login failed, error from API:", error.response?.data || error.message);
        if (error.response?.status === 403) {
        throw error;
      }
        return false;
      }
    },

    // Register action
    async register(_, payload) {
      console.log("Registering user with payload:", payload);
      try {
        await axios.post(`${API_BASE_URL}/users/register`, payload);
        console.log("Registration successful");
        return true;
      } catch (error) {
        if (error.response?.status === 400) {
          console.error("Registration failed: Duplicate username or email.");
          throw new Error("Username or email already exists. Please choose another.");
        }
        console.error("Unexpected registration error:", error.response?.data || error.message);
        throw new Error("An unexpected error occurred during registration.");
      }
    },

    // Change password action
    async changePassword({ state }, payload) {
      console.log("Changing password:", payload);
      try {
        const response = await axios.post(
          `${API_BASE_URL}/users/change-password`,
          {
            username: state.user.username,
            new_password: payload.newPassword,
          },
          {
            headers: { Authorization: `Bearer ${state.token}` },
          }
        );
        console.log("Password changed successfully:", response.data);
        return true;
      } catch (error) {
        console.error("Error changing password:", error.response?.data || error.message);
        return false;
      }
    },

    // Fetch logged-in user data
    async fetchUserData({ commit }) {
      const token = localStorage.getItem("access_token");
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

    // Logout action
    logout({ commit }) {
      console.log("Logging out...");
      commit("clearAuth");
      localStorage.removeItem("access_token");
    },

    // Fetch all forms
    async fetchForms({ commit, state }) {
      try {
        const response = await axios.get(`${API_BASE_URL}/forms`, {
          headers: { Authorization: `Bearer ${state.token}` },
        });
        commit("setForms", response.data);
      } catch (error) {
        console.error("Error fetching forms:", error.response?.data || error.message);
      }
    },

    // Fetch a specific form by ID
    async fetchFormById({ commit, state }, id) {
      try {
        const response = await axios.get(`${API_BASE_URL}/forms/${id}`, {
          headers: { Authorization: `Bearer ${state.token}` },
        });
        commit("setCurrentForm", response.data);
      } catch (error) {
        console.error("Error fetching form:", error.response?.data || error.message);
      }
    },

    // Create a new form
    async createForm({ state }, form) {
      try {
        await axios.post(`${API_BASE_URL}/forms`, form, {
          headers: { Authorization: `Bearer ${state.token}` },
        });
      } catch (error) {
        console.error("Error creating form:", error.response?.data || error.message);
      }
    },

    // Update an existing form
    async updateForm({ state }, { id, form }) {
      try {
        await axios.put(`${API_BASE_URL}/forms/${id}`, form, {
          headers: { Authorization: `Bearer ${state.token}` },
        });
      } catch (error) {
        console.error("Error updating form:", error.response?.data || error.message);
      }
    },

    // Delete a form by ID
    async deleteForm({ state }, id) {
      try {
        await axios.delete(`${API_BASE_URL}/forms/${id}`, {
          headers: { Authorization: `Bearer ${state.token}` },
        });
      } catch (error) {
        console.error("Error deleting form:", error.response?.data || error.message);
      }
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.token,
    getUser: (state) => state.user,
    getForms: (state) => state.forms,
    getCurrentForm: (state) => state.currentForm,
    getStudyDetails: (state) => state.studyDetails,
  },
  plugins: [
    createPersistedState({
      key: "myAppStudyDetails",
      paths: ["studyDetails"],
      storage: window.localStorage,
    }),
  ],
});

export default store;
