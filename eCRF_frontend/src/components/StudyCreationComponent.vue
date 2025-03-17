<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>
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
      <div v-if="selectedCaseStudy && selectedCaseStudyName !== 'custom'">
        <h3>{{ selectedCaseStudy.name }}</h3>
        <p>{{ selectedCaseStudy.description }}</p>
        <div class="study-id-container">
          <label>Study ID (Persistent & Searchable):</label>
          <input type="text" :value="studyId" readonly class="study-id-input" />
        </div>
        <label for="numForms">Number of Forms:</label>
        <input id="numForms" type="number" v-model.number="numberOfForms" placeholder="Enter number of forms" />
        <small class="hint">Different forms per visit per condition</small>
      </div>
      <div v-if="selectedCaseStudyName === 'custom'" class="custom-study">
        <h3>Create Custom Study</h3>
        <label>Study Name:</label>
        <input type="text" v-model="customStudy.name" placeholder="Enter study name" @input="updateCustomStudyId" required />
        <label>Study Description:</label>
        <textarea v-model="customStudy.description" placeholder="Enter study description" required></textarea>
        <div class="study-id-container">
          <label>Study ID (Persistent & Searchable):</label>
          <input type="text" :value="studyId" readonly class="study-id-input" />
        </div>
        <label for="numFormsCustom">Number of Forms:</label>
        <input id="numFormsCustom" type="number" v-model.number="numberOfForms" placeholder="Enter number of forms" />
        <small class="hint">Different forms per visit per condition</small>
      </div>
      <!-- Toggle Switch for Meta Data -->
      <div class="meta-toggle-container">
        <label class="switch">
          <input type="checkbox" v-model="includeMeta" />
          <span class="slider round"></span>
        </label>
        <span class="toggle-label">Include Study Meta Information</span>
      </div>
      <!-- Meta Information Container (only if toggle is checked) -->
      <div v-if="includeMeta" class="meta-container">
        <label>Number of Subjects:</label>
        <input type="number" v-model.number="metaInfo.numberOfSubjects" placeholder="Enter number of subjects" />
        <label>Number of Visits per Subject:</label>
        <input type="number" v-model.number="metaInfo.numberOfVisits" placeholder="Enter number of visits per subject" />
        <label>Study Meta Description:</label>
        <textarea v-model="metaInfo.studyMetaDescription" placeholder="Enter additional study information"></textarea>
      </div>
    </div>
    <!-- Independent Proceed and Cancel Buttons -->
    <div class="form-actions">
      <button @click="proceedToFormWithMeta" class="btn-option">Proceed</button>
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
      selectedCaseStudyName: "",
      selectedCaseStudy: null,
      customStudy: { name: "", description: "" },
      numberOfForms: 1,
      includeMeta: false,
      studyId: "",
      metaInfo: { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" },
      studyCounter: 1,
    };
  },
  created() {
    console.log("Component created. Fetching study types.");
    this.fetchStudyTypes();
  },
  methods: {
    fetchStudyTypes() {
      fetch("/study_types.json")
        .then(response => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then(data => {
          this.caseStudies = data;
          console.log("Fetched study types:", data);
        })
        .catch(error => console.error("Error fetching study types:", error));
    },
    loadCaseStudyDetails() {
      console.log("Selected study type:", this.selectedCaseStudyName);
      if (this.selectedCaseStudyName === "custom") {
        this.selectedCaseStudy = null;
        this.updateCustomStudyId();
        console.log("Custom study selected. Updated study ID:", this.studyId);
      } else {
        this.selectedCaseStudy = this.caseStudies.find(cs => cs.name === this.selectedCaseStudyName);
        if (this.selectedCaseStudy) {
          this.studyId = this.generateStudyId(this.selectedCaseStudy.name);
          console.log("Non-custom study selected:", this.selectedCaseStudy, "Generated study ID:", this.studyId);
        } else {
          console.warn("No matching study found for:", this.selectedCaseStudyName);
        }
      }
    },
    generateStudyId(studyName) {
      console.log("Generating study ID for:", studyName);
      let prefix = "";
      if (this.selectedCaseStudyName === "custom") {
        prefix = "CS";
      } else {
        prefix = studyName.split(" ").map(word => word[0]).join("").toUpperCase().substring(0, 4);
      }
      const datePart = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const id = `${prefix}-${datePart}-${String(this.studyCounter).padStart(3, "0")}`;
      console.log("Generated study ID:", id);
      return id;
    },
    updateCustomStudyId() {
      console.log("Updating custom study ID. Custom study name:", this.customStudy.name);
      this.studyId = this.generateStudyId(this.customStudy.name);
      console.log("Updated study ID:", this.studyId);
    },
    proceedToFormWithMeta() {
      const studyDetails = {
        id: this.studyId,
        name: this.selectedCaseStudyName === "custom" ? this.customStudy.name : this.selectedCaseStudy.name,
        description: this.selectedCaseStudyName === "custom" ? this.customStudy.description : this.selectedCaseStudy.description,
        numberOfForms: this.numberOfForms,
        metaInfo: this.includeMeta ? { ...this.metaInfo } : {},
      };
      console.log("Proceeding with study details:", studyDetails);
      this.studyCounter++;
      console.log("Incremented study counter to:", this.studyCounter);
      this.$store.commit("setStudyDetails", studyDetails);
      this.$router.push({ name: "CreateFormScratch" });
    },
    cancelMetaInfo() {
      this.includeMeta = false;
      this.metaInfo = { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" };
      console.log("Meta information canceled and reset.");
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
.hint {
  font-size: 12px;
  color: #777;
  margin-top: 3px;
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
.btn-option:hover {
  background: #e0e0e0;
}
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
.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}
.modal-actions button {
  flex: 1;
}

/* Additional minimal CSS for new elements */
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
  padding: 15px;
  background-color: #fff;
  border: 1px solid #ccc;
  border-radius: 8px;
}
.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}
</style>
