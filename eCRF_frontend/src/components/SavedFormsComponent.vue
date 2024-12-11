<template>
  <div class="saved-forms-page">
    <div class="header-container">
      <button @click="goBack" class="btn-back">⬅ Back</button>
      <h1>Saved Forms</h1>
    </div>
    <div v-if="savedForms.length > 0">
      <ul>
        <li v-for="form in savedForms" :key="form.id">
          <button @click.prevent="loadForm(form)">{{ form.form_name }}</button>
        </li>
      </ul>
    </div>
    <p v-else>No saved forms found. Create and save a new form to get started!</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "SavedFormsComponent",
  data() {
    return {
      savedForms: [],
    };
  },
  async mounted() {
    await this.loadSavedForms();
  },
  methods: {
    async loadSavedForms() {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          console.error("No access token found.");
          return;
        }

        const response = await axios.get("http://127.0.0.1:8000/forms/load-saved-forms", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        this.savedForms = response.data;
      } catch (error) {
        console.error("Error loading saved forms:", error.response?.data || error.message);
      }
    },
    loadForm(form) {
      alert(`Loaded form "${form.form_name}"!`);
    },
    goBack() {
      this.$router.push("/dashboard/create-form-scratch"); // Navigate back to ScratchFormComponent
    },
  },
};
</script>
