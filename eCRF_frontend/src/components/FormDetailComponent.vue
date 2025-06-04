<template>
  <div class="study-data-container" v-if="study">
    <!-- Study Header -->
    <h1 class="study-name">{{ study.metadata.study_name }}</h1>

    <!-- Navigation Bars: Subject, Visit, Group -->
    <div class="navigation-bars">
      <!-- Subject Nav -->
      <div class="nav-item">
        <button @click="prevSubject" :disabled="currentSubjectIndex === 0" class="nav-btn">&lt;</button>
        <span class="nav-label">Subject {{ currentSubjectIndex + 1 }} / {{ numberOfSubjects }}</span>
        <button @click="nextSubject" :disabled="currentSubjectIndex === numberOfSubjects - 1" class="nav-btn">&gt;</button>
      </div>
      <!-- Visit Nav -->
      <div class="nav-item" v-if="visitList.length > 1">
        <button @click="prevVisit" :disabled="currentVisitIndex === 0" class="nav-btn">&lt;</button>
        <span class="nav-label">Visit: {{ visitList[currentVisitIndex].name }}</span>
        <button @click="nextVisit" :disabled="currentVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
      </div>
      <!-- Group Nav -->
      <div class="nav-item" v-if="groupList.length > 1">
        <button @click="prevGroup" :disabled="currentGroupIndex === 0" class="nav-btn">&lt;</button>
        <span class="nav-label">Group: {{ groupList[currentGroupIndex].name }}</span>
        <button @click="nextGroup" :disabled="currentGroupIndex === groupList.length - 1" class="nav-btn">&gt;</button>
      </div>
    </div>

    <!-- Editable Form for Assigned Sections -->
    <div class="entry-form-section">
      <h2>Enter Data for Subject {{ currentSubjectIndex + 1 }}, Visit “{{ visitList[currentVisitIndex].name }}”, Group “{{ groupList[currentGroupIndex].name }}”</h2>

      <div v-if="assignedModelIndices.length">
        <div
          v-for="mIdx in assignedModelIndices"
          :key="mIdx"
          class="section-block"
        >
          <h3>{{ selectedModels[mIdx].title }}</h3>
          <div
            v-for="(field, fIdx) in selectedModels[mIdx].fields"
            :key="fIdx"
            class="form-field"
          >
            <label :for="fieldId(mIdx, fIdx)">
              {{ field.label }}
              <span v-if="field.constraints?.required" class="required">*</span>
            </label>

            <!-- TEXT INPUT -->
            <input
              v-if="field.type === 'text'"
              :id="fieldId(mIdx, fIdx)"
              type="text"
              v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
              :placeholder="field.placeholder"
              :required="field.constraints?.required || false"
              :readonly="field.constraints?.readonly || false"
              :minlength="field.constraints?.minLength"
              :maxlength="field.constraints?.maxLength"
              :pattern="field.constraints?.pattern"
            />

            <!-- TEXTAREA -->
            <textarea
              v-else-if="field.type === 'textarea'"
              :id="fieldId(mIdx, fIdx)"
              v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
              :placeholder="field.placeholder"
              :required="field.constraints?.required || false"
              :readonly="field.constraints?.readonly || false"
              :minlength="field.constraints?.minLength"
              :maxlength="field.constraints?.maxLength"
              :pattern="field.constraints?.pattern"
              rows="4"
            ></textarea>

            <!-- NUMBER -->
            <input
              v-else-if="field.type === 'number'"
              :id="fieldId(mIdx, fIdx)"
              type="number"
              v-model.number="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
              :placeholder="field.placeholder"
              :required="field.constraints?.required || false"
              :readonly="field.constraints?.readonly || false"
              :min="field.constraints?.min"
              :max="field.constraints?.max"
              :step="field.constraints?.step"
            />

            <!-- DATE -->
            <input
              v-else-if="field.type === 'date'"
              :id="fieldId(mIdx, fIdx)"
              type="date"
              v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
              :placeholder="field.placeholder"
              :required="field.constraints?.required || false"
              :readonly="field.constraints?.readonly || false"
              :min="field.constraints?.minDate"
              :max="field.constraints?.maxDate"
            />

            <!-- SELECT -->
            <select
              v-else-if="field.type === 'select'"
              :id="fieldId(mIdx, fIdx)"
              v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
              :required="field.constraints?.required || false"
            >
              <option value="" disabled>Select...</option>
              <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
            </select>

            <!-- Unknown Type Fallback -->
            <input
              v-else
              :id="fieldId(mIdx, fIdx)"
              type="text"
              v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
              :placeholder="field.placeholder"
              :required="field.constraints?.required || false"
              :readonly="field.constraints?.readonly || false"
            />

            <!-- Validation Error Message -->
            <div
              v-if="fieldErrors(mIdx, fIdx)"
              class="error-message"
            >
              {{ fieldErrors(mIdx, fIdx) }}
            </div>
          </div>
        </div>

        <!-- Save Data Button -->
        <div class="form-actions">
          <button @click="submitData" class="btn-save">Save Data</button>
        </div>
      </div>

      <div v-else>
        <p>No sections assigned to this Visit/Group.</p>
      </div>
    </div>

    <!-- Back Button -->
    <button @click="goBack" class="btn-back">Back to List</button>
  </div>

  <div v-else class="loading">
    <p>Loading study details…</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyDataEntryComponent",
  data() {
    return {
      study: null,
      detailsCollapsed: false,
      currentSubjectIndex: 0,
      currentVisitIndex: 0,
      currentGroupIndex: 0,
      entryData: [], // Nested structure for subject→visit→group→section→field
      validationErrors: {}, // Will hold error messages per cell
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
    numberOfSubjects() {
      // If study.metadata.numberOfSubjects exists, use it; otherwise default to 1
      return this.study?.metadata?.numberOfSubjects || 1;
    },
    visitList() {
      return this.study?.content?.study_data?.visits || [];
    },
    groupList() {
      return this.study?.content?.study_data?.groups || [];
    },
    selectedModels() {
      return this.study?.content?.study_data?.selectedModels || [];
    },
    assignments() {
      return this.study?.content?.study_data?.assignments || [];
    },
    // Indices of models (sections) assigned at the current visit & group
    assignedModelIndices() {
      const vIdx = this.currentVisitIndex;
      const gIdx = this.currentGroupIndex;
      return this.selectedModels
        .map((_, mIdx) => mIdx)
        .filter((mIdx) => this.assignments[mIdx]?.[vIdx]?.[gIdx]);
    },
  },
  async created() {
    const studyId = this.$route.params.id;
    await this.loadStudy(studyId);
  },
  methods: {
    async loadStudy(studyId) {
      try {
        console.log("Loading study ID:", studyId);
        const resp = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${studyId}`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
          }
        );
        this.study = resp.data;
        console.log("Study loaded:", this.study);
        this.initializeEntryData();
      } catch (err) {
        console.error("Error loading study:", err.response?.data || err.message);
        alert("Failed to load study details.");
      }
    },
    initializeEntryData() {
      const nSubj = this.numberOfSubjects;
      const nVisits = this.visitList.length;
      const nGroups = this.groupList.length;
      const nSections = this.selectedModels.length;
      // Build 5‐dimensional array: [subjects][visits][groups][sections][fields]
      this.entryData = Array.from({ length: nSubj }, () =>
        Array.from({ length: nVisits }, () =>
          Array.from({ length: nGroups }, () =>
            // For each section, build an array of field‐values
            this.selectedModels.map((sect) =>
              sect.fields.map(() => "") // initialize each field to empty string
            )
          )
        )
      );
      console.log("Initialized entryData structure:", this.entryData);
    },
    fieldId(mIdx, fIdx) {
      // Unique ID for each input
      return `s${this.currentSubjectIndex}_v${this.currentVisitIndex}_g${this.currentGroupIndex}_m${mIdx}_f${fIdx}`;
    },
    // Return validation message for a given section/field, or empty string
    fieldErrors(mIdx, fIdx) {
      const key = this.errorKey(mIdx, fIdx);
      return this.validationErrors[key] || "";
    },
    errorKey(mIdx, fIdx) {
      return [
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex,
        mIdx,
        fIdx,
      ].join("-");
    },
    validateField(mIdx, fIdx) {
      const fieldDef = this.selectedModels[mIdx].fields[fIdx];
      const value =
        this.entryData[this.currentSubjectIndex][this.currentVisitIndex][
          this.currentGroupIndex
        ][mIdx][fIdx];
      const constraints = fieldDef.constraints || {};
      const key = this.errorKey(mIdx, fIdx);

      // Reset previous error
      this.$delete(this.validationErrors, key);

      if (constraints.required && (value === "" || value === null)) {
        this.$set(
          this.validationErrors,
          key,
          `${fieldDef.label} is required.`
        );
        return false;
      }
      if (fieldDef.type === "number") {
        const numeric = Number(value);
        if (isNaN(numeric)) {
          this.$set(
            this.validationErrors,
            key,
            `${fieldDef.label} must be a number.`
          );
          return false;
        }
        if (constraints.min != null && numeric < constraints.min) {
          this.$set(
            this.validationErrors,
            key,
            `${fieldDef.label} must be ≥ ${constraints.min}.`
          );
          return false;
        }
        if (constraints.max != null && numeric > constraints.max) {
          this.$set(
            this.validationErrors,
            key,
            `${fieldDef.label} must be ≤ ${constraints.max}.`
          );
          return false;
        }
      }
      if (fieldDef.type === "text" || fieldDef.type === "textarea") {
        const str = String(value || "");
        if (
          constraints.minLength != null &&
          str.length < constraints.minLength
        ) {
          this.$set(
            this.validationErrors,
            key,
            `${fieldDef.label} must have at least ${constraints.minLength} characters.`
          );
          return false;
        }
        if (
          constraints.maxLength != null &&
          str.length > constraints.maxLength
        ) {
          this.$set(
            this.validationErrors,
            key,
            `${fieldDef.label} must have at most ${constraints.maxLength} characters.`
          );
          return false;
        }
        if (constraints.pattern) {
          const regex = new RegExp(constraints.pattern);
          if (!regex.test(str)) {
            this.$set(
              this.validationErrors,
              key,
              `${fieldDef.label} does not match required pattern.`
            );
            return false;
          }
        }
      }
      // No error
      return true;
    },
    validateCurrentSection() {
      let allValid = true;
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach((_, fIdx) => {
          const valid = this.validateField(mIdx, fIdx);
          if (!valid) allValid = false;
        });
      });
      return allValid;
    },
    async submitData() {
      console.log(
        "submitData() called for S/V/G:",
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex
      );
      // Validate all fields in this section
      const valid = this.validateCurrentSection();
      if (!valid) {
        alert("Please fix validation errors before saving.");
        return;
      }

      // Prepare payload
      const payload = {
        study_id: this.study.metadata.id,
        subject_index: this.currentSubjectIndex,
        visit_index: this.currentVisitIndex,
        group_index: this.currentGroupIndex,
        data: this.entryData[this.currentSubjectIndex][
          this.currentVisitIndex
        ][this.currentGroupIndex],
      };

      console.log("Payload to submit:", payload);
      // Assume endpoint: POST /forms/studies/{id}/data
      try {
        const resp = await axios.post(
          `http://127.0.0.1:8000/forms/studies/${this.study.metadata.id}/data`,
          payload,
          {
            headers: { Authorization: `Bearer ${this.token}` },
          }
        );
        console.log("Data saved response:", resp.data);
        alert("Data saved successfully for this Subject/Visit/Group.");
      } catch (err) {
        console.error("Error saving data:", err.response?.data || err.message);
        alert("Failed to save data. Check console for details.");
      }
    },
    prevSubject() {
      if (this.currentSubjectIndex > 0) {
        this.currentSubjectIndex--;
        console.log("Switched to subject:", this.currentSubjectIndex);
      }
    },
    nextSubject() {
      if (this.currentSubjectIndex < this.numberOfSubjects - 1) {
        this.currentSubjectIndex++;
        console.log("Switched to subject:", this.currentSubjectIndex);
      }
    },
    prevVisit() {
      if (this.currentVisitIndex > 0) {
        this.currentVisitIndex--;
        console.log("Switched to visit:", this.currentVisitIndex);
      }
    },
    nextVisit() {
      if (this.currentVisitIndex < this.visitList.length - 1) {
        this.currentVisitIndex++;
        console.log("Switched to visit:", this.currentVisitIndex);
      }
    },
    prevGroup() {
      if (this.currentGroupIndex > 0) {
        this.currentGroupIndex--;
        console.log("Switched to group:", this.currentGroupIndex);
      }
    },
    nextGroup() {
      if (this.currentGroupIndex < this.groupList.length - 1) {
        this.currentGroupIndex++;
        console.log("Switched to group:", this.currentGroupIndex);
      }
    },
    goBack() {
      this.$router.push("/saved-forms");
    },
  },
};
</script>

<style scoped>
.study-data-container {
  max-width: 900px;
  margin: 20px auto;
  padding: 20px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  font-family: Arial, sans-serif;
}
.study-name {
  text-align: center;
  margin-bottom: 20px;
  font-size: 28px;
  color: #333333;
}

/* Navigation Bars */
.navigation-bars {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
}
.nav-item {
  display: flex;
  align-items: center;
}
.nav-btn {
  background: #007bff;
  color: #ffffff;
  border: none;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}
.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.nav-label {
  margin: 0 8px;
  font-weight: bold;
  color: #333333;
}

/* Collapsible Metadata */
.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f7f7f7;
  padding: 10px 15px;
  border: 1px solid #dddddd;
  border-radius: 4px;
  margin-bottom: 0;
}
.header-text {
  font-size: 16px;
  font-weight: bold;
  color: #333333;
}
.toggle-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #007bff;
}
.details-section {
  background: #fafafa;
  padding: 15px;
  border: 1px solid #dddddd;
  border-radius: 4px;
  margin-bottom: 20px;
}
.details-section p {
  margin: 6px 0;
  color: #555555;
  font-size: 14px;
}
.details-section ul {
  list-style: disc inside;
  margin: 8px 0;
  padding-left: 20px;
}
.details-section li {
  margin: 4px 0;
  font-size: 14px;
  color: #555555;
}

/* Entry Form Section */
.entry-form-section {
  margin-bottom: 30px;
}
.entry-form-section h2 {
  margin-bottom: 12px;
  font-size: 20px;
  color: #333333;
}
.section-block {
  margin-bottom: 24px;
  padding: 12px;
  border: 1px solid #dddddd;
  border-radius: 4px;
  background: #fdfdfd;
}
.section-block h3 {
  margin-top: 0;
  font-size: 18px;
  color: #444444;
}
.form-field {
  margin-bottom: 14px;
}
.form-field label {
  display: block;
  margin-bottom: 4px;
  font-weight: bold;
  color: #333333;
}
.required {
  color: #d00;
  margin-left: 4px;
}
input[type="text"],
textarea,
input[type="number"],
input[type="date"],
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #cccccc;
  border-radius: 4px;
  box-sizing: border-box;
}
.error-message {
  color: #d00;
  font-size: 12px;
  margin-top: 4px;
}

/* Form Actions */
.form-actions {
  text-align: right;
}
.btn-save {
  background: #28a745;
  color: #ffffff;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}
.btn-save:hover {
  background: #218838;
}

/* Back Button */
.btn-back {
  display: block;
  margin: 0 auto 20px;
  padding: 10px 20px;
  background: #007bff;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.btn-back:hover {
  background: #0056b3;
}

.loading {
  text-align: center;
  padding: 50px;
  font-size: 16px;
  color: #666666;
}
</style>
