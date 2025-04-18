<template>
  <div class="saved-forms-container">
    <h1>Saved Studies</h1>

    <div v-if="savedForms.length > 0">
      <table>
        <thead>
          <tr>
            <th>Study Name</th>
            <th>Study ID</th>
            <th>Date Created</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="study in savedForms" :key="study.id">
            <td>{{ study.study_name }}</td>
            <td>{{ study.id }}</td>
            <td>{{ formatDate(study.created_at) }}</td>
            <td>
              <button @click="viewForm(study)" class="btn-option">View</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-else class="no-forms">No saved studies found.</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "SavedFormsViewComponent",
  data() {
    return {
      savedForms: [], // Stores fetched studies
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
  },
  async created() {
    await this.loadSavedForms();
  },
  methods: {
    async loadSavedForms() {
      try {
        console.log("Loading saved studies...", this.token);
        const response = await axios.get("http://127.0.0.1:8000/forms/studies", {
          headers: {
            Authorization: `Bearer ${this.token}`,
          },
        });
        console.log("Saved studies loaded:", response.data);
        this.savedForms = response.data;
      } catch (error) {
        console.error("Error loading saved studies:", error.response?.data || error.message);
        if (error.response?.status === 401) {
          alert("Authentication error. Please log in again.");
          this.$router.push("/login");
        } else {
          alert("Failed to load saved studies.");
        }
      }
    },
    viewForm(study) {
      this.$router.push({ name: "FormDetail", params: { id: study.id } });
    },
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" });
    },
  },
};
</script>

<style scoped>
/* Container */
.saved-forms-container {
  max-width: 750px;
  margin: auto;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

h1 {
  text-align: center;
  font-weight: 500;
  color: #333;
}

/* Table Styles */
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eaeaea;
}

th {
  background: #f5f5f5;
  font-weight: 600;
  color: #444;
}

tr:hover {
  background-color: #f9f9f9;
}

/* No Studies Found */
.no-forms {
  text-align: center;
  color: #888;
  margin-top: 20px;
}

/* Minimalistic Button */
.btn-option {
  padding: 8px 12px;
  font-size: 14px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-option:hover {
  background: #e0e0e0;
}
</style>
