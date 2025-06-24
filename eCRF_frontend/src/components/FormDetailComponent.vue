<template>
  <div class="study-data-container" v-if="study">
    <!-- ─────────────────────────────────────────────────── -->
    <!-- 1. STUDY DETAILS (Always Visible at the Top)       -->
    <!-- ─────────────────────────────────────────────────── -->
    <div class="study-header">
      <h1 class="study-name">{{ study.metadata.study_name }}</h1>
      <p class="study-description">{{ study.metadata.study_description }}</p>
      <p class="study-meta">
        Subjects: {{ NUMBER_OF_SUBJECTS }}|
        Visits: {{ visitList.length }}|
        Groups: {{ groupList.length }}
      </p>
      <hr />
    </div>

    <!-- ─────────────────────────────────────────────── -->
    <!-- 2. SELECTION MATRIX: Subject × (Visit)    -->
    <!-- ─────────────────────────────────────────────── -->
    <div v-if="showSelection">
      <h2>Select Subject × Visit </h2>
      <table class="selection-matrix">
        <thead>
          <tr>
            <th>Subject / Visit</th>
            <th v-for="(combo, cIdx) in visitCombos" :key="cIdx">
              Visit {{ visitList[combo.visitIndex].name }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="sIdx in subjectIndices" :key="sIdx">
            <td class="subject-cell">Subject {{ sIdx + 1 }}</td>
            <td v-for="(combo, cIdx) in visitCombos" :key="cIdx">
              <button
                class="select-btn"
                @click="selectCell(sIdx, combo.visitIndex, combo.groupIndex)"
              >
                Select
              </button>
              <button class="share-icon" title="Share this form link" @click="openShareDialog(sIdx, combo.visitIndex)"><i :class="icons.share"></i></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ─────────────────────────────────────────────────── -->
    <!-- 3. DATA‐ENTRY FORM: Shown Once a Cell Is Chosen    -->
    <!-- ─────────────────────────────────────────────────── -->
    <div v-else class="entry-form-wrapper">
      <!-- ─────────────────────────────────────────────── -->
      <!-- 3.a COLLAPSIBLE PANEL FOR “Study / Visit” INFO -->
      <!-- ─────────────────────────────────────────────── -->
      <div class="details-panel">
        <button @click="toggleDetails" class="details-toggle-btn">
          {{ showDetails ? 'Hide Details ▲' : 'Show Details ▼' }}
        </button>
        <button class="share-icon" title="Share this form link" @click="openShareDialog(currentSubjectIndex, currentVisitIndex)"><i :class="icons.share"></i></button>
        <div v-if="showDetails" class="details-content">
          <!-- ─────────────────────────────────────────── -->
          <!-- 3.a.i STUDY INFO                             -->
          <!-- ─────────────────────────────────────────── -->
          <div class="details-block">
            <strong>Study Info:</strong>
            <ul>
              <li
                v-for="[key, val] in Object.entries(study.content.study_data.study)"
                :key="key"
              >
                {{ key }}: {{ val }}
              </li>
            </ul>
          </div>

          <!-- ─────────────────────────────────────────── -->
          <!-- 3.a.ii VISIT INFO                             -->
          <!-- ─────────────────────────────────────────── -->
          <div class="details-block">
            <strong>Visit Info:</strong>
            <ul>
              <li
                v-for="[key, val] in Object.entries(visitList[currentVisitIndex])"
                :key="key"
              >
                {{ key }}: {{ val }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- ─────────────────────────────────────────────── -->
      <!-- 3.b BREADCRUMB (Exact Subject/Visit/Group)      -->
      <!-- ─────────────────────────────────────────────── -->
      <div class="bread-crumb">
        <strong>Study:</strong> {{ study.metadata.study_name }} &nbsp;|&nbsp;
        <strong>Subject:</strong> {{ currentSubjectIndex + 1 }} &nbsp;|&nbsp;
        <strong>Visit:</strong> {{ visitList[currentVisitIndex].name }}

      </div>

      <!-- ─────────────────────────────────────────────────── -->
      <!-- 3.c ENTRY FORM FIELDS                              -->
      <!-- ─────────────────────────────────────────────────── -->
      <div class="entry-form-section">
        <h2>
          Enter Data for Subject {{ currentSubjectIndex + 1 }},
          Visit: “{{ visitList[currentVisitIndex].name }}”

        </h2>

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

              <!-- NUMBER INPUT -->
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

              <!-- DATE INPUT -->
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
                <option value="" disabled>Select…</option>
                <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
              </select>

              <!-- FALLBACK TEXT -->
              <input
                v-else
                :id="fieldId(mIdx, fIdx)"
                type="text"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :placeholder="field.placeholder"
                :required="field.constraints?.required || false"
                :readonly="field.constraints?.readonly || false"
              />

              <!-- ERROR MESSAGE -->
              <div v-if="fieldErrors(mIdx, fIdx)" class="error-message">
                {{ fieldErrors(mIdx, fIdx) }}
              </div>
            </div>
          </div>

          <!-- Save Data Button -->
          <div class="form-actions">
            <button @click="submitData" class="btn-save">Save Data</button>
          </div>
        </div>

        <div v-else class="no-assigned">
          <p>No sections are assigned to this Visit/Group.</p>
        </div>
      </div>

      <!-- ─────────────────────────────────────────────────── -->
      <!-- 3.d “Back to Selection” Button                      -->
      <!-- ─────────────────────────────────────────────────── -->
      <div class="back-button-container">
        <button @click="backToSelection" class="btn-back">← Back to Selection</button>
      </div>
    </div>
  </div>

  <div v-else class="loading">
    <p>Loading study details…</p>
  </div>
  <!-- Share-link modal -->
<div v-if="showShareDialog" class="dialog-overlay">
  <div class="dialog">
    <h3>Generate Share Link</h3>
    <label>
      Permission:
      <select v-model="shareConfig.permission">
        <option value="view">View Only</option>
        <option value="add">Allow Add</option>
      </select>
    </label>
    <label>
      Max Uses:
      <input type="number" v-model.number="shareConfig.maxUses" min="1" />
    </label>
    <label>
      Expires in (days):
      <input type="number" v-model.number="shareConfig.expiresInDays" min="1" />
    </label>
    <div class="dialog-actions">
      <button @click="createShareLink">Generate</button>
      <button @click="showShareDialog = false">Cancel</button>
    </div>
    <p v-if="generatedLink">
      Link: <a :href="generatedLink" target="_blank">{{ generatedLink }}</a>
    </p>
  </div>
</div>
 <div v-if="permissionError" class="dialog-overlay">
    <div class="dialog">
      <h3>Permission Denied</h3>
      <p>You do not have permission to create a share link. Please contact your administrator.</p>
      <div class="dialog-actions">
        <button @click="permissionError = false">Close</button>
      </div>
    </div>
  </div>

</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons"

export default {
  name: "StudyDataEntryComponent",

  data() {
    return {
      study: null,
      showSelection: true,
      showDetails: false,               // Controls “Study/Visit/Group” toggle
      currentSubjectIndex: null,
      currentVisitIndex: null,
      currentGroupIndex: null,
      entryData: [],
      validationErrors: {},
      NUMBER_OF_SUBJECTS: 3,
      icons,
      showShareDialog: false,
      shareParams: { subjectIndex: null, visitIndex: null },
      shareConfig: { permission: 'view', maxUses: 1, expiresInDays: 7 },
      generatedLink: '',
      permissionError: false,
    };
  },

  computed: {
    token() {
      return this.$store.state.token;
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
    // Flatten (visit × group) combos into a single array
    visitCombos() {
      return this.visitList.map((visit, index) => ({
        visitIndex: index,
        groupIndex: 0,
        label: `Visit: ${visit.name}`,
      }));
    },
    // [0, 1, 2]
    subjectIndices() {
      return Array.from({ length: this.NUMBER_OF_SUBJECTS }, (_, i) => i);
    },
    // Which sections (models) are assigned under (visit, group)?
    assignedModelIndices() {
      if (
        this.currentVisitIndex === null ||
        this.currentGroupIndex === null
      ) {
        return [];
      }
      return this.selectedModels
        .map((_, mIdx) => mIdx)
        .filter((mIdx) =>
          this.assignments[mIdx]?.[this.currentVisitIndex]?.[this.currentGroupIndex]
        );
    },
  },

  async created() {
    const studyId = this.$route.params.id;
    await this.loadStudy(studyId);
  },

  methods: {
    // ───────────────────────────────────────────────
    // Load the full study object
    // ───────────────────────────────────────────────
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
        console.error(
          "Error loading study:",
          err.response?.data || err.message
        );
        alert("Failed to load study details.");
      }
    },

    // ───────────────────────────────────────────────
    // Initialize entryData as blanks for [subj][visit][group][section][field]
    // ───────────────────────────────────────────────
    initializeEntryData() {
      const nSubj = this.NUMBER_OF_SUBJECTS;
      const nVisits = this.visitList.length;
      const nGroups = this.groupList.length;
      this.entryData = Array.from({ length: nSubj }, () =>
        Array.from({ length: nVisits }, () =>
          Array.from({ length: nGroups }, () =>
            this.selectedModels.map((sect) =>
              sect.fields.map(() => "")
            )
          )
        )
      );
      console.log("Initialized entryData:", this.entryData);
    },

    // ───────────────────────────────────────────────
    // Selection-matrix click
    // ───────────────────────────────────────────────
    selectCell(sIdx, vIdx, gIdx) {
      this.currentSubjectIndex = sIdx;
      this.currentVisitIndex = vIdx;
      this.currentGroupIndex = 0;
      this.showSelection = false;
      console.log(
        `Selected Subject ${sIdx + 1}, Visit idx ${vIdx}, Group idx ${gIdx}`
      );
    },
    backToSelection() {
      this.showSelection = true;
      this.showDetails = false;        // Collapse toggle when going back
      this.currentSubjectIndex = null;
      this.currentVisitIndex = null;
      this.currentGroupIndex = null;
      this.validationErrors = {};
    },

    // ───────────────────────────────────────────────
    // Toggle “Show Details” (Study / Visit / Group)
    // ───────────────────────────────────────────────
    toggleDetails() {
      this.showDetails = !this.showDetails;
    },

    // ───────────────────────────────────────────────
    // Helpers: field ID & error key
    // ───────────────────────────────────────────────
    fieldId(mIdx, fIdx) {
      return `s${this.currentSubjectIndex}_v${this.currentVisitIndex}_g${this.currentGroupIndex}_m${mIdx}_f${fIdx}`;
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
    fieldErrors(mIdx, fIdx) {
      const key = this.errorKey(mIdx, fIdx);
      return this.validationErrors[key] || "";
    },

    // ───────────────────────────────────────────────
    // Validate a single field; returns true if valid
    // ───────────────────────────────────────────────
    validateField(mIdx, fIdx) {
      const fieldDef = this.selectedModels[mIdx].fields[fIdx];
      const value =
        this.entryData[this.currentSubjectIndex][this.currentVisitIndex][
          this.currentGroupIndex
        ][mIdx][fIdx];
      const constraints = fieldDef.constraints || {};
      const key = this.errorKey(mIdx, fIdx);

      this.$delete(this.validationErrors, key);

      // Required
      if (constraints.required && (value === "" || value === null)) {
        this.$set(
          this.validationErrors,
          key,
          `${fieldDef.label} is required.`
        );
        return false;
      }

      // Number checks
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

      // Text/textarea length & pattern
      if (
        fieldDef.type === "text" ||
        fieldDef.type === "textarea"
      ) {
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

      return true;
    },
    openShareDialog(sIdx, vIdx) {
      this.shareParams = { subjectIndex: sIdx, visitIndex: vIdx };
      this.generatedLink = "";
      this.showShareDialog = true;
    },

    async createShareLink() {
  const { subjectIndex, visitIndex } = this.shareParams;
  const payload = {
    study_id:       this.study.metadata.id,
    subject_index:  subjectIndex,
    visit_index:    visitIndex,
    permission:     this.shareConfig.permission,
    max_uses:       this.shareConfig.maxUses,
    expires_in_days:this.shareConfig.expiresInDays,
  };
  try {
    const resp = await axios.post("http://localhost:8000/forms/share-link/", payload, {
      headers: { Authorization: `Bearer ${this.token}` }
    });
    this.generatedLink = resp.data.link;
  } catch (err) {
    console.error(err);
    this.generatedLink = null;
     if (err.response?.status === 403) {
       // no permission
       this.permissionError = true;
     } else {
       this.error = err.response?.data?.detail || err.message;
     }

    this.error = err.response?.data?.detail || err.message;
  }
},

    // ───────────────────────────────────────────────
    // Validate ALL fields in current S/V/G
    // ───────────────────────────────────────────────
    validateCurrentSection() {
      let allValid = true;
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach((_, fIdx) => {
          const ok = this.validateField(mIdx, fIdx);
          if (!ok) allValid = false;
        });
      });
      return allValid;
    },

    // ───────────────────────────────────────────────
    // Submit data for this Subject/Visit/Group
    // ───────────────────────────────────────────────
    async submitData() {
      console.log(
        "submitData() for S/V/G:",
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex
      );
      const valid = this.validateCurrentSection();
      if (!valid) {
        alert("Please fix validation errors before saving.");
        return;
      }

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

      try {
        const resp = await axios.post(
          `http://127.0.0.1:8000/forms/studies/${this.study.metadata.id}/data`,
          payload,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        console.log("Data saved response:", resp.data);
        alert("Data saved successfully for this Subject/Visit/Group.");
      } catch (err) {
        console.error(
          "Error saving data:",
          err.response?.data || err.message
        );
        alert("Failed to save data. Check console for details.");
      }
    },
  },
};
</script>

<style scoped>
.study-data-container {
  max-width: 960px;
  margin: 20px auto;
  padding: 20px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  font-family: Arial, sans-serif;
}

/* ─────────────────────────────────────────────────── */
/* 1. STUDY DETAILS (Always Visible at Top) */
/* ─────────────────────────────────────────────────── */
.study-header {
  text-align: center;
  margin-bottom: 24px;
}
.study-name {
  font-size: 28px;
  color: #333333;
  margin-bottom: 8px;
}
.study-description {
  font-size: 16px;
  color: #555555;
  margin-bottom: 4px;
}
.study-meta {
  font-size: 14px;
  color: #777777;
}
hr {
  margin-top: 16px;
  margin-bottom: 24px;
  border: 0;
  border-top: 1px solid #e0e0e0;
}

/* ─────────────────────────────────────────────────── */
/* 2. SELECTION MATRIX */
/* ─────────────────────────────────────────────────── */
.selection-matrix {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 32px;
}
.selection-matrix th,
.selection-matrix td {
  border: 1px solid #cccccc;
  padding: 8px;
  text-align: center;
}
.selection-matrix th {
  background: #f2f2f2;
  font-weight: 600;
  color: #333;
}
.subject-cell {
  background: #fafafa;
  font-weight: bold;
}
.select-btn {
  background: #007bff;
  color: #fff;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}
.select-btn:hover {
  background: #0056b3;
}

/* ─────────────────────────────────────────────────── */
/* 3. DATA-ENTRY SECTION */
/* ─────────────────────────────────────────────────── */

/* 3.a Collapsible “Study / Visit / Group” info */
.details-panel {
  margin-bottom: 16px;
}
.details-toggle-btn {
  background: none;
  border: none;
  color: #007bff;
  font-size: 16px;
  cursor: pointer;
  margin-bottom: 8px;
}
.details-content {
  background: #f7f7f7;
  border: 1px solid #dddddd;
  border-radius: 4px;
  padding: 12px;
}
.details-block {
  margin-bottom: 12px;
}
.details-block strong {
  display: block;
  margin-bottom: 4px;
}
.details-block ul {
  margin: 0 0 12px 16px;
  padding: 0;
}
.details-block li {
  font-size: 14px;
  color: #333333;
}

/* 3.b Breadcrumb */
.bread-crumb {
  background: #f7f7f7;
  padding: 10px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 24px;
  font-size: 14px;
  color: #333333;
}

/* 3.c Form fields */
.entry-form-section h2 {
  font-size: 20px;
  margin-bottom: 16px;
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
.no-assigned {
  font-style: italic;
  color: #666666;
  margin-top: 12px;
}
.form-actions {
  text-align: right;
  margin-top: 16px;
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

/* 3.d Back button */
.back-button-container {
  text-align: center;
  margin-top: 24px;
}
.btn-back {
  background: #007bff;
  color: #ffffff;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.btn-back:hover {
  background: #0056b3;
}

/* ─────────────────────────────────────────────────── */
/* Loading State */
/* ─────────────────────────────────────────────────── */
.loading {
  text-align: center;
  padding: 50px;
  font-size: 16px;
  color: #666666;
}
/* overlay dims the rest of the page */
.dialog-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* the white “modal” box */
.dialog {
  background: #fff;
  padding: 1.5rem;
  border-radius: 0.5rem;
  width: 320px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  position: relative;
}

/* Title spacing */
.dialog h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.25rem;
}

/* Form fields within modal */
.dialog label {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.dialog label select,
.dialog label input {
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 0.25rem;
  font-size: 0.9rem;
  box-sizing: border-box;
}

/* Button row */
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

/* Primary “Generate” button */
.dialog-actions button:first-child {
  background: #4f46e5;
  color: #fff;
}

/* Secondary “Cancel” button */
.dialog-actions button:last-child {
  background: #e5e7eb;
  color: #333;
}

/* Modal buttons shared styles */
.dialog-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.9rem;
}

/* Generated link display */
.dialog p a {
  display: block;
  word-break: break-all;
  margin-top: 1rem;
  color: #007bff;
  text-decoration: underline;
}

</style>
