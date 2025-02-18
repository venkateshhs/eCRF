<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>

    <!-- Study Selection -->
    <div class="new-study-form">
      <h2>Create a New Study</h2>

      <label for="studyType">Select Case Study:</label>
      <select v-model="selectedCaseStudyName" @change="loadCaseStudyDetails">
        <option disabled value="">-- Select Case Study --</option>
        <option v-for="caseStudy in caseStudies" :key="caseStudy.name" :value="caseStudy.name">
          {{ caseStudy.name }}
        </option>
        <option value="custom">Custom Study</option>
      </select>

      <!-- Display Study Details for Non-Custom Study -->
      <div v-if="selectedCaseStudy && selectedCaseStudyName !== 'custom'">
        <h3>{{ selectedCaseStudy.name }}</h3>
        <p>{{ selectedCaseStudy.description }}</p>
        <!-- Number of Forms Input with Hint -->
        <label for="numForms">Number of Forms:</label>
        <input
          id="numForms"
          type="number"
          v-model.number="numberOfForms"
          placeholder="Enter number of forms"
        />
        <small class="hint">Different forms per visit per condition</small>

        <!-- Button to add meta information -->
        <button @click="openMetaDialog" class="btn-option">Add Study Meta Information</button>
      </div>

      <!-- Custom Study Creation -->
      <div v-if="selectedCaseStudyName === 'custom'" class="custom-study">
        <h3>Create Custom Study</h3>
        <label>Study Name:</label>
        <input type="text" v-model="customStudy.name" placeholder="Enter study name" required />

        <label>Study Description:</label>
        <textarea v-model="customStudy.description" placeholder="Enter study description" required></textarea>

        <label for="numFormsCustom">Number of Forms:</label>
        <input
          id="numFormsCustom"
          type="number"
          v-model.number="numberOfForms"
          placeholder="Enter number of forms"
        />
        <small class="hint">Different forms per visit per condition</small>

        <button @click="openMetaDialog" class="btn-option">Add Study Meta Information</button>
      </div>
    </div>

    <!-- Modal Dialog for Meta Information -->
    <div v-if="showMetaDialog" class="modal-overlay">
      <div class="modal">
        <h3>Study Meta Information</h3>
        <label>Number of Subjects:</label>
        <input
          type="number"
          v-model.number="metaInfo.numberOfSubjects"
          placeholder="Enter number of subjects"
        />

        <label>Number of Visits per Subject:</label>
        <input
          type="number"
          v-model.number="metaInfo.numberOfVisits"
          placeholder="Enter number of visits per subject"
        />

        <label>Study Meta Description:</label>
        <textarea
          v-model="metaInfo.studyMetaDescription"
          placeholder="Enter additional study information"
        ></textarea>

        <div class="modal-actions">
          <button @click="proceedToFormWithMeta" class="btn-primary">Proceed</button>
          <button @click="closeMetaDialog" class="btn-option">Cancel</button>
        </div>
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
      caseStudies: [], // API response with case study names and descriptions
      selectedCaseStudyName: "",
      selectedCaseStudy: null,
      customStudy: { name: "", description: "" },
      numberOfForms: 1,
      showMetaDialog: false,
      metaInfo: {
        numberOfSubjects: null,
        numberOfVisits: null,
        studyMetaDescription: "",
      },
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
          headers: { Authorization: `Bearer ${this.token}`, Accept: "application/json" },
        });
        this.caseStudies = response.data;
      } catch (error) {
        console.error("Error loading case studies:", error);
      }
    },
    loadCaseStudyDetails() {
      if (this.selectedCaseStudyName === "custom") {
        this.selectedCaseStudy = null;
      } else {
        this.selectedCaseStudy = this.caseStudies.find(
          cs => cs.name === this.selectedCaseStudyName
        );
      }
    },
    openMetaDialog() {
      if (!this.numberOfForms) this.numberOfForms = 1;
      this.showMetaDialog = true;
    },
    closeMetaDialog() {
      this.showMetaDialog = false;
    },
    proceedToFormWithMeta() {
      let studyDetails = {};
      if (this.selectedCaseStudyName === "custom") {
        studyDetails = { ...this.customStudy, isCustom: true };
      } else {
        studyDetails = { ...this.selectedCaseStudy };
      }
      studyDetails.numberOfForms = this.numberOfForms;
      studyDetails.metaInfo = { ...this.metaInfo };

      this.$router.push({
        name: "CreateFormScratch",
        query: { studyDetails: JSON.stringify(studyDetails) },
      });
    },
  },
};
</script>

<style scoped>
/* Container: Full width and full viewport height */
.study-creation-container {
  max-width: 900px;
  margin: auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

/* Headings */
h1 {
  text-align: center;
  color: #333;
}

/* New Study Form */
.new-study-form {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  margin-bottom: 20px;
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
  box-sizing: border-box;
}

.hint {
  font-size: 12px;
  color: #777;
  margin-top: 3px;
}

/* Minimalist Buttons */
.btn-option {
  display: block;
  width: 100%;
  padding: 10px;
  margin-top: 15px;
  background: #f7f7f7;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
  text-align: center;
  transition: background 0.3s ease;
}

.btn-option:hover {
  background: #e0e0e0;
}

.btn-next {
  background: #f7f7f7;
  color: black;
  padding: 10px 15px;
  border: 1px solid #ccc;
  border-radius: 5px;
  cursor: pointer;
  text-align: center;
  width: 100%;
  margin-top: 15px;
  transition: background 0.3s ease;
}

.btn-next:hover {
  background: #e0e0e0;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  width: 300px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.modal label {
  margin-top: 10px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.modal-actions button {
  flex: 1;
}

/* Study Creation Container */
.study-creation-container {
  width: 100%;
  min-height: 100vh;
  margin: 0 auto;
  padding: 20px;
  background-color: #f9f9f9;
}

/* Scratch Form Content */
.scratch-form-content {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

/* Form Area */
.form-area {
  flex: 3;
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #ddd;
}

/* Centered Editable Form Name */
.form-heading-container {
  text-align: center;
  margin-bottom: 20px;
}

.heading-input {
  font-size: 22px;
  font-weight: 500;
  text-align: center;
  border: none;
  border-bottom: 1px solid #ccc;
  outline: none;
  width: 100%;
  max-width: 400px;
}

/* Form Section */
.form-section {
  padding: 15px;
  border-bottom: 1px solid #ddd;
  transition: all 0.3s ease;
}

.form-section.active {
  background-color: #e7f3ff;
  border-left: 3px solid #444;
}

/* Section Header */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-actions {
  display: flex;
  gap: 10px;
}

/* Field Box */
.field-box {
  margin-top: 10px;
}

/* Input Styles */
input,
textarea,
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin-top: 5px;
  box-sizing: border-box;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #444;
  outline: none;
}

/* Form Actions: Horizontal Button Row */
.form-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}

.form-name-input {
  flex: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

/* Button Row Container */
.button-row {
  display: flex;
  gap: 15px;
  width: 100%;
}

/* Minimalist Buttons */
.btn-option {
  background: #f4f4f4;
  color: #333;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  text-align: center;
  cursor: pointer;
  transition: background 0.3s ease;
  flex: 1;
}

.btn-option:hover {
  background: #e0e0e0;
}

.btn-primary {
  background-color: #444;
  color: white;
  padding: 10px;
  border: none;
  border-radius: 5px;
  text-align: center;
  cursor: pointer;
  transition: background 0.3s ease;
  flex: 1;
}

.btn-primary:hover {
  background-color: #333;
}

/* Icon Button */
.icon-button {
  background: none;
  border: none;
  padding: 5px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  transition: background-color 0.3s ease;
}

.icon-button:hover {
  background-color: #f4f4f4;
}

/* Available Fields Section */
.available-fields {
  flex: 1;
  background-color: #fff;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  width: 320px;
  max-height: calc(100vh - 60px);
  overflow-y: auto;
}

/* Tabs for Available Fields */
.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.tabs button {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  background: #f4f4f4;
  flex: 1;
}

.tabs button.active {
  background-color: #444;
  color: white;
  border: none;
}

.tabs button:not(.active):hover {
  background-color: #e0e0e0;
}

/* Available Field Button */
.available-field-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  font-size: 14px;
  background-color: #f9f9f9;
  border: 1px solid #ccc;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-bottom: 10px;
}

.available-field-button i {
  font-size: 18px;
  color: #555;
}

.available-field-button:hover {
  background-color: #e0e0e0;
}

/* Responsive Design */
@media (max-width: 768px) {
  .scratch-form-content {
    flex-direction: column;
  }
  .form-area {
    max-width: 100%;
  }
  .available-fields {
    max-width: 100%;
    width: 100%;
  }
}
</style>
