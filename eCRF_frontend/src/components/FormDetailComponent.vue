<template>
  <div class="form-detail-container">
    <h1>View Saved Study</h1>
    <div v-if="study">
      <!-- Study Metadata Header -->
      <div class="study-meta">
        <h2>{{ study.metadata.study_name }}</h2>
        <p>{{ study.metadata.study_description }}</p>
        <!-- Display additional meta info if available -->
        <div v-if="study.content.study_data.meta_info">
          <p><strong>Number of Forms:</strong> {{ study.content.study_data.meta_info.numberOfForms }}</p>
          <p><strong>Number of Subjects:</strong> {{ study.content.study_data.meta_info.numberOfSubjects }}</p>
          <p><strong>Number of Visits:</strong> {{ study.content.study_data.meta_info.numberOfVisits }}</p>
        </div>
      </div>
      <!-- Render Forms -->
      <div v-for="(form, formIndex) in study.content.study_data.forms" :key="formIndex" class="form">
        <h3>{{ form.form_name }}</h3>
        <div v-for="(section, sectionIndex) in form.sections" :key="sectionIndex" class="form-section">
          <h4>{{ section.title }}</h4>
          <div v-for="(field, fieldIndex) in section.fields" :key="fieldIndex" class="form-group">
            <label :for="field.name">{{ field.label }}</label>
            <div class="field-box">
              <!-- Render fields dynamically -->
              <input
                v-if="field.type === 'text'"
                type="text"
                :id="field.name"
                v-model="field.value"
                :placeholder="field.placeholder"
              />
              <textarea
                v-if="field.type === 'textarea'"
                :id="field.name"
                v-model="field.value"
                :placeholder="field.placeholder"
                :rows="field.rows"
              ></textarea>
              <input
                v-if="field.type === 'number'"
                type="number"
                :id="field.name"
                v-model="field.value"
                :placeholder="field.placeholder"
              />
              <input
                v-if="field.type === 'date'"
                type="date"
                :id="field.name"
                v-model="field.value"
              />
              <select v-if="field.type === 'select'" :id="field.name" v-model="field.value">
                <option v-for="option in field.options" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
              <div v-if="field.type === 'checkbox'" class="checkbox-group">
                <label v-for="(option, i) in field.options" :key="i">
                  <input type="checkbox" v-model="field.value" :value="option" /> {{ option }}
                </label>
              </div>
              <div v-if="field.type === 'radio'" class="radio-group">
                <label v-for="option in field.options" :key="option">
                  <input type="radio" :name="field.name" v-model="field.value" :value="option" />
                  {{ option }}
                </label>
              </div>
              <p v-if="field.type === 'paragraph'">{{ field.content }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    <p v-else>Loading study...</p>
    <button @click="goBack" class="btn-back">Back</button>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyDetailComponent",
  data() {
    return {
      study: null, // Will hold the loaded study (StudyFull)
    };
  },
  computed: {
    token() {
      return this.$store.state.token; // Retrieve token from Vuex
    },
  },
  async created() {
    const studyId = this.$route.params.id; // Get the study ID from route params
    await this.loadStudy(studyId);
  },
  methods: {
    async loadStudy(studyId) {
      try {
        // Adjust the URL to match your backend endpoint
        const response = await axios.get(`http://127.0.0.1:8000/forms/studies/${studyId}`, {
          headers: {
            Authorization: `Bearer ${this.token}`,
          },
        });
        this.study = response.data;
      } catch (error) {
        console.error("Error loading study:", error.response?.data || error.message);
        alert("Failed to load the study.");
      }
    },
    goBack() {
      // Navigate back to the studies list view
      this.$router.push("/studies");
    },
  },
};
</script>

<style scoped>
.form-detail-container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1, h2, h3, h4 {
  text-align: center;
  color: #333;
}

.study-meta {
  margin-bottom: 20px;
  text-align: center;
}

.form {
  margin-bottom: 30px;
}

.form-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.form-group {
  margin-bottom: 15px;
}

.field-box input,
.field-box textarea,
.field-box select {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

.btn-back {
  margin-top: 20px;
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.btn-back:hover {
  background-color: #0056b3;
}
</style>
