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

      <!-- Added Custom Fields List (Main) -->
      <div class="custom-fields-section" v-if="customFields.length">
        <h3>Added Custom Fields</h3>
        <div
          v-for="(field, index) in customFields"
          :key="index"
          class="custom-field-row"
        >
          <div class="custom-field-display">
            <!-- Field Name rendered as label similar to other fields -->
            <label class="added-field-label">{{ field.fieldName }}</label>
            <!-- Field Value rendered as the appropriate control -->
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
          <button type="button" @click="removeCustomField(index, 'main')" class="remove-btn">
            Remove
          </button>
        </div>
      </div>

      <!-- New Custom Field Input (Main) -->
      <div class="new-field-section">
        <h3>Add New Custom Field</h3>
        <div class="custom-field-inputs">
          <select v-model="newCustomField.fieldType" class="field-type">
            <option value="">Select Field Type</option>
            <option value="text">Text</option>
            <option value="number">Number</option>
            <option value="date">Date</option>
            <option value="area">Area</option>
          </select>
          <input
            type="text"
            v-model="newCustomField.fieldName"
            placeholder="Field Name"
            class="field-name"
          />
          <template v-if="newCustomField.fieldType === 'date'">
            <input type="date" v-model="newCustomField.fieldValue" class="field-value" />
          </template>
          <template v-else-if="newCustomField.fieldType === 'number'">
            <input type="number" v-model="newCustomField.fieldValue" class="field-value" />
          </template>
          <template v-else-if="newCustomField.fieldType === 'area'">
            <textarea
              v-model="newCustomField.fieldValue"
              placeholder="Field Value"
              class="field-value"
            ></textarea>
          </template>
          <template v-else>
            <input type="text" v-model="newCustomField.fieldValue" placeholder="Field Value" class="field-value" />
          </template>
          <button type="button" @click="addField('main')" class="add-btn">Add Field</button>
        </div>
      </div>

      <!-- Metadata Toggle Button -->
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

        <!-- Added Meta Custom Fields List -->
        <div class="custom-fields-section meta-custom-fields" v-if="metaCustomFields.length">
          <h3>Added Meta Custom Fields</h3>
          <div
            v-for="(field, index) in metaCustomFields"
            :key="index"
            class="custom-field-row"
          >
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
            <button type="button" @click="removeCustomField(index, 'meta')" class="remove-btn">
              Remove
            </button>
          </div>
        </div>

        <!-- New Meta Custom Field Input -->
        <div class="new-field-section">
          <h3>Add New Meta Custom Field</h3>
          <div class="custom-field-inputs">
            <select v-model="newMetaCustomField.fieldType" class="field-type">
              <option value="">Select Field Type</option>
              <option value="text">Text</option>
              <option value="number">Number</option>
              <option value="date">Date</option>
              <option value="area">Area</option>
            </select>
            <input
              type="text"
              v-model="newMetaCustomField.fieldName"
              placeholder="Field Name"
              class="field-name"
            />
            <template v-if="newMetaCustomField.fieldType === 'date'">
              <input type="date" v-model="newMetaCustomField.fieldValue" class="field-value" />
            </template>
            <template v-else-if="newMetaCustomField.fieldType === 'number'">
              <input type="number" v-model="newMetaCustomField.fieldValue" class="field-value" />
            </template>
            <template v-else-if="newMetaCustomField.fieldType === 'area'">
              <textarea
                v-model="newMetaCustomField.fieldValue"
                placeholder="Field Value"
                class="field-value"
              ></textarea>
            </template>
            <template v-else>
              <input type="text" v-model="newMetaCustomField.fieldValue" placeholder="Field Value" class="field-value" />
            </template>
            <button type="button" @click="addField('meta')" class="add-btn">Add Field</button>
          </div>
        </div>
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
      // studyId is removed; generated on the server.
      studyId: "",
      metaInfo: { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" },
      // Arrays to store added custom fields.
      customFields: [],
      metaCustomFields: [],
      // Temporary objects for new custom field inputs.
      newCustomField: { fieldType: "", fieldName: "", fieldValue: "" },
      newMetaCustomField: { fieldType: "", fieldName: "", fieldValue: "" },
      studyCounter: 1,
      showErrors: false,
    };
  },
  created() {
    this.fetchStudyTypes();
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
      } else {
        this.selectedCaseStudy = this.caseStudies.find(
          (cs) => cs.name === this.selectedCaseStudyName
        );
      }
    },
    // Adds a new custom field to the specified section (main or meta)
    addField(section) {
      if (section === "main") {
        if (!this.newCustomField.fieldType || !this.newCustomField.fieldName) return;
        this.customFields.push({ ...this.newCustomField });
        this.newCustomField = { fieldType: "", fieldName: "", fieldValue: "" };
      } else if (section === "meta") {
        if (!this.newMetaCustomField.fieldType || !this.newMetaCustomField.fieldName) return;
        this.metaCustomFields.push({ ...this.newMetaCustomField });
        this.newMetaCustomField = { fieldType: "", fieldName: "", fieldValue: "" };
      }
    },
    // Removes a custom field by index from the specified section.
    removeCustomField(index, section) {
      if (section === "main") {
        this.customFields.splice(index, 1);
      } else if (section === "meta") {
        this.metaCustomFields.splice(index, 1);
      }
    },
    validateAndProceed() {
      this.showErrors = true;
      if (!this.customStudy.name || !this.customStudy.description) return;
      const studyDetails = {
        // The server will generate the unique study ID.
        name: this.customStudy.name,
        description: this.customStudy.description,
        numberOfForms: this.numberOfForms,
        metaInfo: this.includeMeta
          ? { ...this.metaInfo, customFields: this.metaCustomFields }
          : {},
        customFields: this.customFields,
      };
      this.studyCounter++;
      this.$store.commit("setStudyDetails", studyDetails);
      this.$router.push({ name: "CreateFormScratch" });
    },
    cancelMetaInfo() {
      if (!this.includeMeta) {
        this.resetForm();
      } else {
        this.includeMeta = false;
        this.metaInfo = { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" };
        this.metaCustomFields = [];
      }
    },
    resetForm() {
      this.selectedCaseStudyName = "custom";
      this.selectedCaseStudy = null;
      this.customStudy = { name: "", description: "" };
      this.numberOfForms = 1;
      this.includeMeta = false;
      this.metaInfo = { numberOfSubjects: null, numberOfVisits: null, studyMetaDescription: "" };
      this.customFields = [];
      this.metaCustomFields = [];
      this.newCustomField = { fieldType: "", fieldName: "", fieldValue: "" };
      this.newMetaCustomField = { fieldType: "", fieldName: "", fieldValue: "" };
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

/* Added Fields List */
.custom-fields-section {
  border: 1px dashed #ccc;
  padding: 10px;
  margin-bottom: 20px;
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

/* Error text styling */
.error-text {
  color: red;
  font-size: 12px;
  margin-top: 3px;
  display: block;
}
</style>
