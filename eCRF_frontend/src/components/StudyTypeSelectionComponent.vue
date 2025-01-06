<template>
  <div class="study-planner-container">
    <h1>Plan Your Study</h1>

    <!-- Study Type Selection -->
    <div v-if="studyTypes.length > 0">
      <h2>Select a Study Type</h2>
      <ul>
        <li
          v-for="study in studyTypes"
          :key="study.id"
          @click="selectStudyType(study)"
          :class="{ selected: selectedStudyType?.id === study.id }"
        >
          <h3>{{ study.name }}</h3>
          <p>{{ study.description }}</p>
        </li>
      </ul>
    </div>

    <!-- Form Selection -->
    <div v-if="selectedStudyType">
      <h2>Forms for {{ selectedStudyType.name }}</h2>
      <ul>
        <li v-for="form in selectedStudyType.forms" :key="form.id">
          <label>
            <input type="checkbox" :value="form" v-model="selectedForms" />
            {{ form.name }} - {{ form.description }}
          </label>
        </li>
      </ul>

      <button @click="confirmStudyPlan" class="btn-confirm">Confirm Study Plan</button>
    </div>

    <!-- Selected Study Plan -->
    <div v-if="studyPlan.length > 0">
      <h2>Your Study Plan</h2>
      <ul>
        <li v-for="form in studyPlan" :key="form.id">{{ form.name }} - {{ form.description }}</li>
      </ul>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyPlanner",
  data() {
    return {
      studyTypes: [],
      selectedStudyType: null,
      selectedForms: [],
      studyPlan: [],
    };
  },
  async created() {
    await this.loadStudyTypes();
  },
  methods: {
    async loadStudyTypes() {
      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/study-types");
        this.studyTypes = response.data;
      } catch (error) {
        console.error("Error loading study types:", error);
        alert("Failed to load study types.");
      }
    },
    selectStudyType(study) {
      this.selectedStudyType = study;
      this.selectedForms = []; // Reset selected forms
    },
    confirmStudyPlan() {
      if (this.selectedForms.length === 0) {
        alert("Please select at least one form.");
        return;
      }
      this.studyPlan = [...this.selectedForms];
      alert("Study plan confirmed!");
    },
  },
};
</script>

<style scoped>
.study-planner-container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1, h2 {
  text-align: center;
  color: #333;
}

ul {
  list-style: none;
  padding: 0;
}

li {
  margin: 10px 0;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 5px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

li.selected {
  background-color: #e7e7e7;
  font-weight: bold;
}

label {
  display: flex;
  align-items: center;
}

input[type="checkbox"] {
  margin-right: 10px;
}

.btn-confirm {
  display: block;
  margin: 20px auto;
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.btn-confirm:hover {
  background-color: #0056b3;
}
</style>
