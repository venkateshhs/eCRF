<template>
  <div class="study-selection-container">
    <h1>Select a Study Type</h1>
    <div v-if="studyTypes.length > 0">
      <div v-for="study in studyTypes" :key="study.id" class="study-type-card">
        <h2>{{ study.name }}</h2>
        <p>{{ study.description }}</p>
        <button @click="selectStudyType(study)">Select</button>
      </div>
    </div>
    <p v-else>No study types available.</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyTypeSelectionComponent",
  data() {
    return {
      studyTypes: [],
    };
  },
  async created() {
    await this.loadStudyTypes();
  },
  methods: {
    async loadStudyTypes() {
      try {
        const response = await axios.get("http://127.0.0.1:8000/study-types");
        this.studyTypes = response.data;
      } catch (error) {
        console.error("Error loading study types:", error.response?.data || error.message);
      }
    },
    selectStudyType(study) {
      this.$router.push({ name: "FormCreation", params: { studyId: study.id } });
    },
  },
};
</script>

<style scoped>
.study-selection-container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.study-type-card {
  margin-bottom: 20px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.study-type-card h2 {
  margin-bottom: 10px;
}

.study-type-card p {
  margin-bottom: 20px;
}

button {
  padding: 10px 20px;
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
