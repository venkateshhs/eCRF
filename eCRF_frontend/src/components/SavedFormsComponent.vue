<template>
  <div class="saved-forms-container">
    <h1>Saved Forms</h1>
    <div v-if="savedForms.length > 0">
      <table>
        <thead>
          <tr>
            <th>Form Name</th>
            <th>Date Created</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="form in savedForms" :key="form.id">
            <td>{{ form.form_name }}</td>
            <td>{{ form.created_at }}</td>
            <td>
              <button @click="viewForm(form)">View</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else>No saved forms found.</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "SavedFormsViewComponent",
  data() {
    return {
      savedForms: [], // Array to store fetched forms
    };
  },
  computed: {
    token() {
      return this.$store.state.token; // Retrieve the token directly from Vuex
    },
  },
  async created() {
    await this.loadSavedForms(); // Load forms when component is created
  },
  methods: {
    async loadSavedForms() {
      console.log("Token being sent:", this.token); // Debug token

      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/saved-forms", {
          headers: {
            Authorization: `Bearer ${this.token}`,
          },
        });
        this.savedForms = response.data;
      } catch (error) {
        console.error("Error loading saved forms:", error.response?.data || error.message);
        if (error.response?.status === 401) {
          alert("Authentication error. Please log in again.");
          this.$router.push("/login");
        } else if (error.response?.status === 422) {
          alert("Validation error. Please check your request.");
        } else {
          alert("Failed to load saved forms.");
        }
      }
    },
    viewForm(form) {
      // Navigate to the FormDetail view, passing the form ID as a route parameter
      this.$router.push({ name: "FormDetail", params: { id: form.id } });
    },
  },
};
</script>

<style scoped>
.saved-forms-container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th,
td {
  border: 1px solid #ddd;
  padding: 10px;
  text-align: left;
}

th {
  background-color: #007bff;
  color: white;
}

button {
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}
</style>
