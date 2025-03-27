<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>
    <div class="new-study-form">
      <h2>Create a New Study</h2>

      <!-- Study Name (Mandatory) -->
      <label for="studyName">Study Name: <span class="required">*</span></label>
      <input type="text" id="studyName" v-model="customStudy.name" placeholder="Enter study name" required />
      <small v-if="showErrors && !customStudy.name" class="error-text">
        Study name is required.
      </small>

      <!-- Study Description (Mandatory) -->
      <label for="studyDescription">Study Description: <span class="required">*</span></label>
      <textarea id="studyDescription" v-model="customStudy.description" placeholder="Enter study description" required></textarea>
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
      <!-- Case Study Description -->
      <div v-if="selectedCaseStudy && selectedCaseStudyName !== 'custom'">
        <h3>{{ selectedCaseStudy.name }}</h3>
        <p>{{ selectedCaseStudy.description }}</p>
      </div>

      <!-- Number of Forms -->
      <label for="numForms">Number of Forms:</label>
      <input
        id="numForms"
        type="number"
        v-model.number="numberOfForms"
        placeholder="Enter number of forms"
        min="1"
        max="1000"
        step="1"
        :class="{ 'error-input': showErrors && (!Number.isInteger(numberOfForms) || numberOfForms < 1 || numberOfForms > 1000) }"
      />
      <small v-if="showErrors && (!Number.isInteger(numberOfForms) || numberOfForms < 1 || numberOfForms > 1000)" class="error-text">
        Number of forms must be a whole number between 1 and 1000.
      </small>
      <small class="hint">Different forms per visit per condition</small>

      <!-- Study Custom Fields Container (appears immediately after number of forms) -->
      <div class="custom-fields-section" v-if="customFields.length">
        <h3>Study Custom Fields</h3>
        <div v-for="(field, index) in customFields" :key="index" class="custom-field-row">
          <div class="custom-field-display">
            <label class="added-field-label">{{ field.fieldName }}</label>
            <div class="added-field-value">
              <template v-if="field.fieldType === 'date'">
                <input type="date" v-model="field.fieldValue" class="field-value" />
              </template>
              <template v-else-if="field.fieldType === 'number'">
                <input type="number" v-model="field.fieldValue" class="field-value" />
              </template>
              <template v-else-if="field.fieldType === 'area'">
                <textarea v-model="field.fieldValue" class="field-value"></textarea>
              </template>
              <template v-else>
                <input type="text" v-model="field.fieldValue" class="field-value" />
              </template>
            </div>
          </div>
          <button type="button" @click="removeField(index, false)" class="remove-btn">Remove</button>
        </div>
      </div>

      <!-- Meta Information Container (always visible) -->
      <div class="meta-info-container">
        <h3>Meta Information</h3>
        <label>Number of Subjects:</label>
        <input type="number" v-model.number="metaInfo.numberOfSubjects" placeholder="Enter number of subjects" />
        <label>Number of Visits per Subject:</label>
        <input type="number" v-model.number="metaInfo.numberOfVisits" placeholder="Enter number of visits per subject" />
        <label>Study Meta Description:</label>
        <textarea v-model="metaInfo.studyMetaDescription" placeholder="Enter additional study information"></textarea>
      </div>

      <!-- Meta Custom Fields Container (appears immediately after meta info) -->
      <div class="custom-fields-section" v-if="metaCustomFields.length">
        <h3>Meta Custom Fields</h3>
        <div v-for="(field, index) in metaCustomFields" :key="index" class="custom-field-row">
          <div class="custom-field-display">
            <label class="added-field-label">{{ field.fieldName }}</label>
            <div class="added-field-value">
              <template v-if="field.fieldType === 'date'">
                <input type="date" v-model="field.fieldValue" class="field-value" />
              </template>
              <template v-else-if="field.fieldType === 'number'">
                <input type="number" v-model="field.fieldValue" class="field-value" />
              </template>
              <template v-else-if="field.fieldType === 'area'">
                <textarea v-model="field.fieldValue" class="field-value"></textarea>
              </template>
              <template v-else>
                <input type="text" v-model="field.fieldValue" class="field-value" />
              </template>
            </div>
          </div>
          <button type="button" @click="removeField(index, true)" class="remove-btn">Remove</button>
        </div>
      </div>

      <!-- Toggle Slider for Unified Custom Field Editor -->
      <div class="meta-toggle-container">
        <label class="switch">
          <input type="checkbox" v-model="showCustomFieldEditor" />
          <span class="slider"></span>
        </label>
        <span class="toggle-label">Show Custom Field Editor</span>
      </div>

      <!-- Unified Custom Field Editor (shown when toggle is on) -->
      <div class="new-field-section" v-if="showCustomFieldEditor">
        <h3>Add New Custom Field</h3>
        <div class="custom-field-inputs">
          <select v-model="newField.fieldType" class="field-type">
            <option value="">Select Field Type</option>
            <option value="text">Text</option>
            <option value="number">Number</option>
            <option value="date">Date</option>
            <option value="area">Area</option>
          </select>
          <input type="text" v-model="newField.fieldName" placeholder="Field Name" class="field-name" />
          <template v-if="newField.fieldType === 'date'">
            <input type="date" v-model="newField.fieldValue" class="field-value" />
          </template>
          <template v-else-if="newField.fieldType === 'number'">
            <input type="number" v-model="newField.fieldValue" class="field-value" />
          </template>
          <template v-else-if="newField.fieldType === 'area'">
            <textarea v-model="newField.fieldValue" placeholder="Field Value" class="field-value"></textarea>
          </template>
          <template v-else>
            <input type="text" v-model="newField.fieldValue" placeholder="Field Value" class="field-value" />
          </template>
          <!-- Checkbox to mark whether this field is meta data -->
          <label class="meta-checkbox-label">
            <input type="checkbox" v-model="newField.isMeta" />
            Meta Data Field
          </label>
          <button type="button" @click="addField" class="add-btn">Add Field</button>
        </div>
      </div>

    </div>

    <!-- Proceed & Cancel Buttons -->
    <div class="form-actions">
      <button @click="validateAndProceed" class="btn-option">Proceed</button>
      <button @click="resetForm" class="btn-option">Cancel</button>
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
      metaInfo: { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" },
      // Unified new field object for the custom field editor.
      newField: { fieldType: "", fieldName: "", fieldValue: "", isMeta: false },
      // Arrays for added custom fields.
      customFields: [],
      metaCustomFields: [],
      // Toggle for showing the unified custom field editor.
      showCustomFieldEditor: false,
      showErrors: false,
    };
  },
  created() {
    this.fetchStudyTypes();
  },
  methods: {
    fetchStudyTypes() {
      fetch("/study_types.json")
        .then(response => response.json())
        .then(data => {
          this.caseStudies = data;
        })
        .catch(error => console.error("Error fetching study types:", error));
    },
    loadCaseStudyDetails() {
      if (this.selectedCaseStudyName === "custom") {
        this.selectedCaseStudy = null;
      } else {
        this.selectedCaseStudy = this.caseStudies.find(cs => cs.name === this.selectedCaseStudyName);
      }
    },
    addField() {
      // Validate that field type and name are provided.
      if (!this.newField.fieldType || !this.newField.fieldName) return;
      if (this.newField.isMeta) {
        this.metaCustomFields.push({ ...this.newField });
      } else {
        this.customFields.push({ ...this.newField });
      }
      // Reset the new field editor.
      this.newField = { fieldType: "", fieldName: "", fieldValue: "", isMeta: false };
    },
    removeField(index, isMeta) {
      if (isMeta) {
        this.metaCustomFields.splice(index, 1);
      } else {
        this.customFields.splice(index, 1);
      }
    },
    validateAndProceed() {
      this.showErrors = true;
      if (!this.customStudy.name || !this.customStudy.description) return;
      // Validate that numberOfForms is a whole number and between 1 and 1000.
      if (!Number.isInteger(this.numberOfForms) || this.numberOfForms < 1 || this.numberOfForms > 1000) return;
      localStorage.removeItem("studyDetails");
      localStorage.removeItem("scratchForms");
      const studyDetails = {
        name: this.customStudy.name,
        description: this.customStudy.description,
        numberOfForms: this.numberOfForms,
        metaInfo: { ...this.metaInfo },
        customFields: this.customFields,
        metaCustomFields: this.metaCustomFields,
        studyType: this.selectedCaseStudyName || "custom"
      };
      this.$store.commit("setStudyDetails", studyDetails);
      this.$router.push({ name: "CreateFormScratch" });
    },
    resetForm() {
      this.selectedCaseStudyName = "custom";
      this.selectedCaseStudy = null;
      this.customStudy = { name: "", description: "" };
      this.numberOfForms = 1;
      this.metaInfo = { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" };
      this.customFields = [];
      this.metaCustomFields = [];
      this.newField = { fieldType: "", fieldName: "", fieldValue: "", isMeta: false };
      this.showCustomFieldEditor = false;
      this.showErrors = false;
    },
  },
};
</script>

<style scoped>
.study-creation-container {
  max-width: 1200px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
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
  font-size: 14px;
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

/* Meta Info Container */
.meta-info-container {
  margin-top: 20px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #fff;
}

/* Toggle Slider Styling (from reference code) */
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

/* Use the same toggle styling for our custom field editor toggle */
.custom-field-toggle-container {
  margin-top: 20px;
  display: flex;
  align-items: center;
}

/* New Field Input Section */
.new-field-section {
  margin-top: 20px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #fff;
}
.new-field-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
}
.custom-field-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.field-type,
.field-name,
.field-value {
  flex: 1 1 150px;
}
.meta-checkbox-label {
  display: flex;
  align-items: center;
  font-size: 14px;
  margin-top: 5px;
}
.meta-checkbox-label input {
  margin-right: 5px;
}
.add-btn {
  background-color: #ccc;
  border: 1px solid #bbb;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
}
.add-btn:hover {
  background-color: #bbb;
}

/* Added Fields Lists */
.custom-fields-section {
  border: 1px dashed #ccc;
  padding: 10px;
  margin-top: 10px;
  border-radius: 5px;
}
.custom-fields-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
}
.custom-field-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}
.custom-field-display {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.added-field-label {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 5px;
}
.added-field-value input,
.added-field-value textarea {
  width: 100%;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}
.remove-btn {
  align-self: flex-end;
  margin-left: 10px;
  background-color: #ccc;
  border: 1px solid #bbb;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
}
.remove-btn:hover {
  background-color: #bbb;
}
/* Error text styling */
.error-text {
  color: red;
  font-size: 12px;
  margin-top: 3px;
  display: block;
}

/* Error input styling */
.error-input {
  border-color: red;
}
</style>
