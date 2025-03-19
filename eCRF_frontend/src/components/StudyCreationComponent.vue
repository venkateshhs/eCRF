<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>
    <div class="new-study-form">
      <h2>Create a New Study</h2>

      <!-- Study Name (Mandatory) -->
      <label for="studyName">Study Name: <span class="required">*</span></label>
      <input
        type="text"
        id="studyName"
        v-model="customStudy.name"
        placeholder="Enter study name"
        required
      />
      <small v-if="showErrors && !customStudy.name" class="error-text">
        Study name is required.
      </small>

      <!-- Study Description (Mandatory) -->
      <label for="studyDescription">Study Description: <span class="required">*</span></label>
      <textarea
        id="studyDescription"
        v-model="customStudy.description"
        placeholder="Enter study description"
        required
      ></textarea>
      <small v-if="showErrors && !customStudy.description" class="error-text">
        Study description is required.
      </small>

      <!-- Case Study Selection -->
      <label for="studyType">Select Case Study Type:</label>
      <select id="studyType" v-model="selectedCaseStudyName" @change="loadCaseStudyDetails">
        <option value="custom">Custom Study</option>
        <option v-for="caseStudy in caseStudies" :key="caseStudy.name" :value="caseStudy.name">
          {{ caseStudy.name }}
        </option>
      </select>

      <!-- Auto-Generated Study ID -->
      <div class="study-id-container">
        <label>Study ID (Persistent & Searchable):</label>
        <input type="text" :value="studyId" readonly class="study-id-input" />
      </div>

      <!-- Case Study Description -->
      <div v-if="selectedCaseStudy && selectedCaseStudyName !== 'custom'">
        <h3>{{ selectedCaseStudy?.name }}</h3>
        <p>{{ selectedCaseStudy?.description }}</p>
      </div>

      <!-- Number of Forms -->
      <label for="numForms">Number of Forms:</label>
      <input
        id="numForms"
        type="number"
        v-model.number="numberOfForms"
        placeholder="Enter number of forms"
      />
      <small class="hint">Different forms per visit per condition</small>

      <!-- Metadata Toggle Button using a Toggle Switch -->
      <div class="meta-toggle-container">
        <label class="switch">
          <input type="checkbox" v-model="includeMeta" />
          <span class="slider"></span>
        </label>
        <span class="toggle-label">Include Study Meta Information</span>
      </div>

      <!-- Metadata Inputs (Only if Toggle is Checked) -->
      <div v-if="includeMeta" class="meta-container">
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
      </div>
    </div>

    <!-- Proceed & Cancel Buttons -->
    <div class="form-actions">
      <button @click="validateAndProceed" class="btn-option">Proceed</button>
      <button @click="cancelMetaInfo" class="btn-option">Cancel</button>
    </div>
  </div>
</template>

<script>
export default {
  name: "StudyCreationComponent",
  data() {
    return {
      caseStudies: [],
      selectedCaseStudyName: "custom",
      selectedCaseStudy: null,
      customStudy: { name: "", description: "" },
      numberOfForms: 1,
      includeMeta: false,
      studyId: "",
      metaInfo: { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" },
      studyCounter: 1,
      showErrors: false,
    };
  },
  created() {
    this.fetchStudyTypes();
    // Pre-generate study ID on load if custom study is selected.
    if (this.selectedCaseStudyName === "custom") {
      this.studyId = this.generateStudyId("CUSTOM");
    }
  },
  methods: {
    fetchStudyTypes() {
      fetch("/study_types.json")
        .then((response) => response.json())
        .then((data) => {
          this.caseStudies = data;
        })
        .catch((error) => console.error("Error fetching study types:", error));
    },
    loadCaseStudyDetails() {
      if (this.selectedCaseStudyName === "custom") {
        this.selectedCaseStudy = null;
        // Generate study ID for custom study when switching to custom.
        this.studyId = this.generateStudyId("CUSTOM");
      } else {
        this.selectedCaseStudy = this.caseStudies.find(
          (cs) => cs.name === this.selectedCaseStudyName
        );
        if (this.selectedCaseStudy) {
          this.studyId = this.generateStudyId(this.selectedCaseStudy.name);
        }
      }
    },
    generateStudyId(studyName) {
      const prefix =
        this.selectedCaseStudyName === "custom"
          ? "CS"
          : studyName?.split(" ").map((word) => word[0]).join("").toUpperCase().substring(0, 4);
      const datePart = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      return `${prefix}-${datePart}-${String(this.studyCounter).padStart(3, "0")}`;
    },
    validateAndProceed() {
      this.showErrors = true;
      if (!this.customStudy.name || !this.customStudy.description) return;
      const studyDetails = {
        id: this.studyId,
        name: this.customStudy.name,
        description: this.customStudy.description,
        numberOfForms: this.numberOfForms,
        metaInfo: this.includeMeta ? { ...this.metaInfo } : {},
      };
      this.studyCounter++;
      this.$store.commit("setStudyDetails", studyDetails);
      this.$router.push({ name: "CreateFormScratch" });
    },
    cancelMetaInfo() {
      if (!this.includeMeta) {
        // If toggle is off, erase all data and reload the original form.
        this.resetForm();
      } else {
        // If toggle is on, perform current functionality: clear meta info and turn off toggle.
        this.includeMeta = false;
        this.metaInfo = { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" };
      }
    },
    resetForm() {
      // Reset all form fields to their initial state.
      this.selectedCaseStudyName = "custom";
      this.selectedCaseStudy = null;
      this.customStudy = { name: "", description: "" };
      this.numberOfForms = 1;
      this.includeMeta = false;
      this.metaInfo = { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" };
      this.showErrors = false;
      this.studyId = this.generateStudyId("CUSTOM");
    },
  },
};
</script>

<style scoped>
.study-id-container {
  margin-top: 10px;
}
.study-id-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  background-color: #f3f3f3;
  border-radius: 5px;
  cursor: not-allowed;
  color: #555;
}
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
select,
input,
textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin-top: 5px;
  box-sizing: border-box;
}
.btn-option {
  display: block;
  width: 100%;
  padding: 10px;
  margin-top: 15px;
  background: #f7f7f7;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  text-align: center;
}

/* Toggle Switch Styling */
.meta-toggle-container {
  margin-top: 15px;
  display: flex;
  align-items: center;
}
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
  margin-right: 10px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.4s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.4s;
  border-radius: 50%;
}
.switch input:checked + .slider {
  background-color: #2196F3;
}
.switch input:checked + .slider:before {
  transform: translateX(26px);
}
.toggle-label {
  font-size: 14px;
  color: #333;
}
.meta-container {
  margin-top: 15px;
}

/* Error text styling */
.error-text {
  color: red;
  font-size: 12px;
  margin-top: 3px;
  display: block;
}
</style>
