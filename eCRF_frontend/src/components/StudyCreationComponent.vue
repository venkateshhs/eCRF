<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>

    <!-- Main Options -->
    <div class="options-container">
      <button @click="viewExistingStudies" class="btn-primary">View Existing Studies</button>
      <button @click="startNewStudy" class="btn-secondary">Create New Study</button>
    </div>

    <!-- New Study Creation -->
    <div v-if="creatingNewStudy" class="new-study-form">
      <h2>Create a New Study</h2>

      <label for="studyType">Select Case Study:</label>
      <select v-model="selectedCaseStudyName" @change="loadCaseStudyDetails">
        <option disabled value="">-- Select Case Study --</option>
        <option v-for="caseStudy in caseStudies" :key="caseStudy.name" :value="caseStudy.name">
          {{ caseStudy.name }}
        </option>
        <option value="custom">Custom Study</option>
      </select>

      <!-- Display Study Details -->
      <div v-if="selectedCaseStudy && selectedCaseStudyName !== 'custom'">
        <h3>{{ selectedCaseStudy.name }}</h3>
        <p>{{ selectedCaseStudy.description }}</p>
        <button @click="proceedToForm" class="btn-next">Proceed</button>
      </div>

      <!-- Custom Study Creation -->
      <div v-if="selectedCaseStudyName === 'custom'" class="custom-study">
        <h3>Create Custom Study</h3>
        <label>Study Name:</label>
        <input type="text" v-model="customStudy.name" placeholder="Enter study name" required />

        <label>Study Description:</label>
        <textarea v-model="customStudy.description" placeholder="Enter study description" required></textarea>

        <button @click="proceedToCustomStudy" class="btn-primary">Proceed with Custom Study</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyCreationComponent",
  data() {
    return {
      caseStudies: [],  // Stores API response
      creatingNewStudy: false,
      selectedCaseStudyName: "", // Holds selected study name
      selectedCaseStudy: null, // Stores selected study object
      customStudy: { name: "", description: "" },
    };
  },
  async created() {
    await this.loadCaseStudies();
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
  },
  methods: {
    async loadCaseStudies() {
      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/case-studies", {
          headers: { Authorization: `Bearer ${this.token}`, "Accept": "application/json" },
        });
        this.caseStudies = response.data;
      } catch (error) {
        console.error("Error loading case studies:", error);
      }
    },
    viewExistingStudies() {
      this.$router.push("/dashboard/view-forms");
    },
    startNewStudy() {
      this.creatingNewStudy = true;
    },
    loadCaseStudyDetails() {
      if (this.selectedCaseStudyName === "custom") {
        this.selectedCaseStudy = null;
      } else {
        this.selectedCaseStudy = this.caseStudies.find(cs => cs.name === this.selectedCaseStudyName);
      }
    },
    proceedToForm() {
      if (!this.selectedCaseStudy) return;

      this.$router.push({
        name: "CreateFormScratch",
        query: { studyDetails: JSON.stringify(this.selectedCaseStudy) },
      });
    },
    proceedToCustomStudy() {
      if (!this.customStudy.name.trim() || !this.customStudy.description.trim()) {
        alert("Please fill in all details for the custom study.");
        return;
      }

      this.$router.push({
        name: "CreateFormScratch",
        query: { studyDetails: JSON.stringify({ ...this.customStudy, isCustom: true }) },
      });
    },
  },
};
</script>

<style scoped>
/* Main Layout */
.study-creation-container {
  max-width: 900px;
  margin: auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
}

/* Options Container */
.options-container {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 30px;
}

.btn-primary, .btn-secondary {
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
}

.btn-primary {
  background-color: #007bff;
  color: white;
  border: none;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.btn-secondary {
  background-color: #28a745;
  color: white;
  border: none;
}

.btn-secondary:hover {
  background-color: #218838;
}

/* New Study Form */
.new-study-form {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
}

label {
  font-weight: bold;
  display: block;
  margin-top: 10px;
}

select, input, textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin-top: 5px;
}

/* Buttons */
.btn-next {
  background-color: #28a745;
  color: white;
  padding: 10px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  margin-top: 15px;
}

.btn-next:hover {
  background-color: #218838;
}

/* Custom Study Section */
.custom-study {
  margin-top: 20px;
}
</style>
