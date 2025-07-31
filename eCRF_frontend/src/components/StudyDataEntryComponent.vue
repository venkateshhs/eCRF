<template>
  <div class="study-data-container" v-if="study">
    <!-- Back Buttons (Always at Top Left) -->
    <div class="back-buttons-container">
      <button v-if="showSelection" @click="goToDashboard" class="btn-back">
        <i :class="icons.back"></i> Back to Dashboard
      </button>
      <button v-if="!showSelection" @click="backToSelection" class="btn-back">
        <i :class="icons.back"></i> Back to Selection
      </button>
    </div>

    <!-- 1. STUDY DETAILS AND DETAILS PANEL (Below Back Buttons) -->
    <div class="study-header-container">
      <div class="study-header">
        <h1 class="study-name">{{ study.metadata.study_name }}</h1>
        <p class="study-description">{{ study.metadata.study_description }}</p>
        <p class="study-meta">
          Subjects: {{ numberOfSubjects }} |
          Visits: {{ visitList.length }} |
          Groups: {{ groupList.length }}
        </p>
      </div>
      <div class="details-panel">
        <div class="details-controls">
          <button @click="toggleDetails" class="details-toggle-btn">
            <i :class="showDetails ? icons.toggleUp : icons.toggleDown"></i>
            {{ showDetails ? 'Hide Details' : 'Show Details' }}
          </button>
          <button
            v-if="!showSelection"
            class="share-icon"
            title="Share this form link"
            @click="openShareDialog(currentSubjectIndex, currentVisitIndex, currentGroupIndex)"
          >
            <i :class="icons.share"></i>
          </button>
        </div>
        <div v-if="showDetails" class="details-content">
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
          <div v-if="!showSelection" class="details-block">
            <strong>Visit Info:</strong>
            <ul>
              <li
                v-for="[key, val] in Object.entries(visitList[currentVisitIndex] || {})"
                :key="key"
              >
                {{ key }}: {{ val }}
              </li>
            </ul>
          </div>
        </div>
      </div>
      <hr />
    </div>

    <!-- 2. SELECTION MATRIX: Subject × Visit -->
    <div v-if="showSelection">
      <h2>Select Subject × Visit</h2>
      <table class="selection-matrix">
        <thead>
          <tr>
            <th>Subject / Visit</th>
            <th v-for="combo in visitCombos" :key="'visit-th-' + combo.visitIndex">
              {{ combo.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(subject, sIdx) in study.content.study_data.subjects" :key="'subject-' + sIdx">
            <td class="subject-cell">{{ subject.id }}</td>
            <td v-for="combo in visitCombos" :key="'visit-td-' + sIdx + '-' + combo.visitIndex" class="visit-cell">
              <button
                class="select-btn"
                :class="{ 'visit-2-btn': combo.visitIndex === 1 }"
                @click="selectCell(sIdx, combo.visitIndex)"
              >
                Select
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 3. DATA-ENTRY FORM: Shown Once a Cell Is Chosen -->
    <div v-else class="entry-form-wrapper">
      <!-- 3.b BREADCRUMB (Exact Subject/Visit/Group) -->
      <div class="bread-crumb">
        <strong>Study:</strong> {{ study.metadata.study_name }}
        <strong>Subject:</strong> {{ study.content.study_data.subjects[currentSubjectIndex].id }}
        <strong>Visit:</strong> {{ visitList[currentVisitIndex].name }}
      </div>

      <!-- 3.c ENTRY FORM FIELDS -->
      <div class="entry-form-section">
        <h2>
          Enter Data for Subject: {{ study.content.study_data.subjects[currentSubjectIndex].id }},
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
                <span
                  v-if="field.constraints?.required"
                  class="required"
                >*</span>
              </label>

              <!-- TEXT INPUT -->
              <input
                v-if="field.type === 'text'"
                :id="fieldId(mIdx, fIdx)"
                type="text"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :placeholder="field.placeholder"
                :required="!!field.constraints?.required"
                :readonly="!!field.constraints?.readonly"
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
                :required="!!field.constraints?.required"
                :readonly="!!field.constraints?.readonly"
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
                :required="!!field.constraints?.required"
                :readonly="!!field.constraints?.readonly"
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
                :required="!!field.constraints?.required"
                :readonly="!!field.constraints?.readonly"
                :min="field.constraints?.minDate"
                :max="field.constraints?.maxDate"
              />

              <!-- SELECT -->
              <select
                v-else-if="field.type === 'select'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :required="!!field.constraints?.required"
              >
                <option value="" disabled>Select…</option>
                <option
                  v-for="opt in field.options"
                  :key="opt"
                  :value="opt"
                >{{ opt }}</option>
              </select>

              <!-- FALLBACK TEXT -->
              <input
                v-else
                :id="fieldId(mIdx, fIdx)"
                type="text"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :placeholder="field.placeholder"
                :required="!!field.constraints?.required"
                :readonly="!!field.constraints?.readonly"
              />

              <!-- ERROR MESSAGE -->
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
            <button @click="submitData" class="btn-save">
              Save Data
            </button>
          </div>
        </div>

        <div v-else class="no-assigned">
          <p>No sections are assigned to this Visit for your group.</p>
        </div>
      </div>
    </div>

    <!-- Share-link modal -->
    <div v-if="showShareDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>Generate Share Link</h3>
        <p>Sharing for Subject {{ shareParams.subjectIndex != null ? study.content.study_data.subjects[shareParams.subjectIndex]?.id : 'N/A' }}, Visit {{ visitList[shareParams.visitIndex]?.name }}</p>
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
          <input
            type="number"
            v-model.number="shareConfig.expiresInDays"
            min="1"
          />
        </label>
        <div class="dialog-actions">
          <button @click="createShareLink">Generate</button>
          <button @click="showShareDialog = false">Cancel</button>
        </div>
        <p v-if="generatedLink">
          <a :href="generatedLink" target="_blank">{{ generatedLink }}</a>
        </p>
      </div>
    </div>

    <!-- Permission-denied modal -->
    <div v-if="permissionError" class="dialog-overlay">
      <div class="dialog">
        <h3>Permission Denied</h3>
        <p>You do not have permission to create a share link. Please contact your administrator.</p>
        <div class="dialog-actions">
          <button @click="permissionError = false">Close</button>
        </div>
      </div>
    </div>

    <!-- Custom Dialog for Notifications -->
    <CustomDialog
      :message="dialogMessage"
      :isVisible="showDialog"
      @close="closeDialog"
    />
  </div>

  <div v-else class="loading">
    <p>Loading study details…</p>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";
import CustomDialog from "@/components/CustomDialog.vue";

export default {
  name: "StudyDataEntryComponent",
  components: { CustomDialog },
  data() {
    return {
      study: null,
      showSelection: true,
      showDetails: false,
      currentSubjectIndex: null,
      currentVisitIndex: null,
      currentGroupIndex: 0,
      entryData: [],
      validationErrors: {},
      icons,
      showShareDialog: false,
      shareParams: { subjectIndex: null, visitIndex: null, groupIndex: null },
      shareConfig: { permission: "view", maxUses: 1, expiresInDays: 7 },
      generatedLink: "",
      permissionError: false,
      showDialog: false,
      dialogMessage: "",
    };
  },

  computed: {
    token() {
      return this.$store.state.token;
    },
    visitList() {
      console.log("[DEBUG] Computing visitList:", this.study?.content?.study_data?.visits);
      return this.study?.content?.study_data?.visits || [];
    },
    groupList() {
      console.log("[DEBUG] Computing groupList:", this.study?.content?.study_data?.groups);
      return this.study?.content?.study_data?.groups || [];
    },
    selectedModels() {
      console.log("[DEBUG] Computing selectedModels:", this.study?.content?.study_data?.selectedModels);
      return this.study?.content?.study_data?.selectedModels || [];
    },
    assignments() {
      console.log("[DEBUG] Computing assignments:", this.study?.content?.study_data?.assignments);
      return this.study?.content?.study_data?.assignments || [];
    },
    numberOfSubjects() {
      const sd = this.study?.content?.study_data;
      const count = sd?.subjectCount != null ? sd.subjectCount : sd?.subjects?.length || 0;
      console.log("[DEBUG] Computing numberOfSubjects:", count);
      return count;
    },
    visitCombos() {
      const combos = this.visitList.map((visit, vIdx) => {
        console.log(`[DEBUG] Rendering visit combo: visitIndex=${vIdx}, label=Visit: ${visit.name}`);
        return {
          visitIndex: vIdx,
          label: `Visit: ${visit.name}`,
        };
      });
      console.log("[DEBUG] Computing visitCombos:", combos);
      return combos;
    },
    subjectIndices() {
      const indices = Array.from({ length: this.numberOfSubjects }, (_, i) => i);
      console.log("[DEBUG] Computing subjectIndices:", indices);
      return indices;
    },
    assignedModelIndices() {
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      console.log(`[DEBUG] Filtering models for visit ${v}, group ${g} (groupName: ${this.groupList[g]?.name || 'undefined'})`);
      console.log(`[DEBUG] assignments:`, this.assignments);
      const indices = this.selectedModels
        .map((_, mIdx) => mIdx)
        .filter((mIdx) => {
          const row = this.assignments[mIdx]?.[v];
          if (!row) {
            console.log(`[DEBUG] Model ${mIdx} has no assignments for visit ${v}`);
            return false;
          }
          const flag = !!row[g];
          console.log(
            `[DEBUG] Model ${mIdx} (“${this.selectedModels[mIdx]?.title || 'undefined'}”) → assigned to group ${g}? ${flag}`
          );
          return flag;
        });
      console.log("[DEBUG] assignedModelIndices result:", indices);
      return indices;
    },
  },

  async created() {
    const studyId = this.$route.params.id;
    console.log("[DEBUG] created() with studyId:", studyId);
    await this.loadStudy(studyId);
  },

  methods: {
    goToDashboard() {
      console.log("[DEBUG] goToDashboard()");
      this.$router.push({
        name: "Dashboard",
        query: { openStudies: "true" }
      });
    },
    async loadStudy(studyId) {
      console.log("[DEBUG] loadStudy()", studyId);
      try {
        const resp = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${studyId}`,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        this.study = resp.data;
        console.log("[DEBUG] Study loaded", this.study);
        this.initializeEntryData();
      } catch (err) {
        console.error("[ERROR] loading study", err);
        this.showDialogMessage("Failed to load study details.");
      }
    },

    initializeEntryData() {
      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;
      const nG = this.groupList.length;
      console.log(`[DEBUG] init entryData: ${nS}×${nV}×${nG}`);
      this.entryData = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () =>
          Array.from({ length: nG }, () =>
            this.selectedModels.map((sect) => sect.fields.map(() => ""))
          )
        )
      );
      console.log("[DEBUG] entryData matrix ready");
    },

    selectCell(sIdx, vIdx) {
      console.log(`[DEBUG] selectCell() → subject ${sIdx}, visit ${vIdx}`);
      this.currentSubjectIndex = sIdx;
      this.currentVisitIndex = vIdx;

      // Resolve subject's assigned group
      const subj = this.study.content.study_data.subjects[sIdx];
      console.log(`[DEBUG] subject[${sIdx}] =`, subj);
      const grpName = (subj.group || "").trim().toLowerCase();
      console.log(`[DEBUG] Subject group name (normalized): ${grpName}`);
      console.log(`[DEBUG] groupList:`, this.groupList);
      const idx = this.groupList.findIndex((g) => (g.name || "").trim().toLowerCase() === grpName);
      this.currentGroupIndex = idx >= 0 ? idx : 0;
      console.log(`[DEBUG] resolved groupIndex = ${this.currentGroupIndex}, groupName = ${this.groupList[this.currentGroupIndex]?.name || 'undefined'}`);

      this.showSelection = false;
      console.log("[DEBUG] showSelection set to false, rendering entry form");
    },

    backToSelection() {
      console.log("[DEBUG] backToSelection()");
      this.showSelection = true;
      this.showDetails = false;
      this.currentSubjectIndex = null;
      this.currentVisitIndex = null;
      this.currentGroupIndex = 0;
      this.validationErrors = {};
    },

    toggleDetails() {
      console.log("[DEBUG] toggleDetails() showDetails:", !this.showDetails);
      this.showDetails = !this.showDetails;
    },

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

    validateField(mIdx, fIdx) {
      const def = this.selectedModels[mIdx].fields[fIdx];
      const val =
        this.entryData[this.currentSubjectIndex][this.currentVisitIndex][
          this.currentGroupIndex
        ][mIdx][fIdx];
      const cons = def.constraints || {};
      const key = this.errorKey(mIdx, fIdx);
      this.$delete(this.validationErrors, key);

      if (cons.required && (val === "" || val == null)) {
        this.$set(this.validationErrors, key, `${def.label} is required.`);
        return false;
      }
      if (def.type === "number") {
        const num = Number(val);
        if (isNaN(num)) {
          this.$set(this.validationErrors, key, `${def.label} must be a number.`);
          return false;
        }
        if (cons.min != null && num < cons.min) {
          this.$set(this.validationErrors, key, `${def.label} ≥ ${cons.min}`);
          return false;
        }
        if (cons.max != null && num > cons.max) {
          this.$set(this.validationErrors, key, `${def.label} ≤ ${cons.max}`);
          return false;
        }
      }
      if (["text", "textarea"].includes(def.type)) {
        const str = String(val || "");
        if (cons.minLength != null && str.length < cons.minLength) {
          this.$set(
            this.validationErrors,
            key,
            `${def.label} needs ≥ ${cons.minLength} chars.`
          );
          return false;
        }
        if (cons.maxLength != null && str.length > cons.maxLength) {
          this.$set(
            this.validationErrors,
            key,
            `${def.label} allows ≤ ${cons.maxLength} chars.`
          );
          return false;
        }
        if (cons.pattern && !new RegExp(cons.pattern).test(str)) {
          this.$set(
            this.validationErrors,
            key,
            `${def.label} does not match pattern.`
          );
          return false;
        }
      }
      return true;
    },

    openShareDialog(sIdx, vIdx, gIdx) {
      console.log("[DEBUG] openShareDialog()", { sIdx, vIdx, gIdx });
      this.shareParams = { subjectIndex: sIdx, visitIndex: vIdx, groupIndex: gIdx };
      this.generatedLink = "";
      this.showShareDialog = true;
    },

    async createShareLink() {
      console.log("[DEBUG] createShareLink()", this.shareParams);
      const { subjectIndex, visitIndex, groupIndex } = this.shareParams;
      const payload = {
        study_id: this.study.metadata.id,
        subject_index: subjectIndex,
        visit_index: visitIndex,
        group_index: groupIndex,
        permission: this.shareConfig.permission,
        max_uses: this.shareConfig.maxUses,
        expires_in_days: this.shareConfig.expiresInDays,
      };
      try {
        const resp = await axios.post(
          "http://localhost:8000/forms/share-link/",
          payload,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        this.generatedLink = resp.data.link;
        console.log("[DEBUG] Share link generated:", this.generatedLink);
      } catch (err) {
        console.error("[ERROR] creating share link", err);
        this.generatedLink = null;
        if (err.response?.status === 403) {
          this.permissionError = true;
          console.log("[DEBUG] Permission error for share link");
        }
      }
    },

    validateCurrentSection() {
      console.log("[DEBUG] validateCurrentSection()");
      let ok = true;
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach((_, fIdx) => {
          if (!this.validateField(mIdx, fIdx)) ok = false;
        });
      });
      console.log("[DEBUG] Validation result:", ok);
      return ok;
    },

    async submitData() {
      console.log(
        `[DEBUG] submitData() → S:${this.currentSubjectIndex} V:${this.currentVisitIndex} G:${this.currentGroupIndex}`
      );
      if (!this.validateCurrentSection()) {
        this.showDialogMessage("Please fix validation errors before saving.");
        return;
      }
      const payload = {
        study_id: this.study.metadata.id,
        subject_index: this.currentSubjectIndex,
        visit_index: this.currentVisitIndex,
        group_index: this.currentGroupIndex,
        data:
          this.entryData[this.currentSubjectIndex][this.currentVisitIndex][
            this.currentGroupIndex
          ],
      };
      console.log("[DEBUG] Payload to submit:", payload);

      try {
        const resp = await axios.post(
          `http://127.0.0.1:8000/forms/studies/${this.study.metadata.id}/data`,
          payload,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        console.log("[DEBUG] Data saved response:", resp.data);
        this.showDialogMessage("Data saved successfully for this Subject/Visit.");
      } catch (err) {
        console.error("[ERROR] saving data:", err.response?.data || err.message);
        this.showDialogMessage("Failed to save data. Check console for details.");
      }
    },

    showDialogMessage(message) {
      console.log("[DEBUG] Showing dialog with message:", message);
      this.dialogMessage = message;
      this.showDialog = true;
    },
    closeDialog() {
      console.log("[DEBUG] Dialog closed");
      this.showDialog = false;
      this.dialogMessage = "";
    },
  },
};
</script>

<style scoped>
.study-data-container {
  max-width: 960px;
  margin: 24px auto;
  padding: 24px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Back Buttons (Always at Top Left) */
.back-buttons-container {
  margin-bottom: 16px;
}
.btn-back {
  background: #d1d5db;
  color: #1f2937;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-back:hover {
  background: #9ca3af;
}
.btn-back i {
  font-size: 14px;
}

/* 1. STUDY HEADER AND DETAILS PANEL */
.study-header-container {
  margin-bottom: 24px;
}
.study-header {
  text-align: center;
  margin-bottom: 16px;
}
.study-name {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}
.study-description {
  font-size: 16px;
  color: #4b5563;
  margin-bottom: 8px;
}
.study-meta {
  font-size: 14px;
  color: #6b7280;
}
hr {
  margin: 12px 0;
  border: 0;
  border-top: 1px solid #e5e7eb;
}

.details-panel {
  margin-bottom: 16px;
}
.details-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.details-toggle-btn {
  background: none;
  border: none;
  color: #374151;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.details-toggle-btn i {
  font-size: 14px;
}
.share-icon {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  font-size: 16px;
  padding: 6px;
  line-height: 1;
}
.share-icon i {
  font-family: 'Font Awesome 5 Free' !important;
  font-weight: 900;
  font-style: normal;
  display: inline-block;
}
.share-icon:hover {
  color: #374151;
}
.details-content {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
}
.details-block {
  margin-bottom: 16px;
}
.details-block strong {
  display: block;
  font-size: 14px;
  color: #1f2937;
  margin-bottom: 6px;
}
.details-block ul {
  margin: 0 0 12px 16px;
  padding: 0;
}
.details-block li {
  font-size: 14px;
  color: #374151;
}

/* 2. SELECTION MATRIX */
.selection-matrix {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 32px;
  table-layout: fixed;
}
.selection-matrix th,
.selection-matrix td {
  border: 1px solid #e5e7eb;
  padding: 12px;
  text-align: center;
  vertical-align: middle;
}
.selection-matrix th {
  background: #f9fafb;
  font-weight: 600;
  color: #1f2937;
}
.subject-cell {
  background: #f9fafb;
  font-weight: 500;
  color: #374151;
  width: 20%;
}
.visit-cell {
  width: 40%;
}
.select-btn {
  background: #e5e7eb;
  color: #1f2937;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
  display: block;
  margin: 0 auto;
}
.visit-2-btn {
  background: #e5e7eb;
}
.select-btn:hover {
  background: #d1d5db;
}

/* 3. DATA-ENTRY SECTION */
.bread-crumb {
  background: #f9fafb;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 24px;
  font-size: 14px;
  color: #374151;
}

.entry-form-section h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
}
.section-block {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #ffffff;
}
.section-block h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}
.form-field {
  margin-bottom: 16px;
}
.form-field label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}
.required {
  color: #dc2626;
  margin-left: 4px;
}
input[type="text"],
textarea,
input[type="number"],
input[type="date"],
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 14px;
  color: #1f2937;
}
input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}
.error-message {
  color: #dc2626;
  font-size: 12px;
  margin-top: 4px;
}
.no-assigned {
  font-style: italic;
  color: #6b7280;
  margin-top: 12px;
}
.form-actions {
  text-align: right;
  margin-top: 16px;
}
.btn-save {
  background: #16a34a;
  color: #ffffff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-save:hover {
  background: #15803d;
}

/* Loading State */
.loading {
  text-align: center;
  padding: 50px;
  font-size: 16px;
  color: #6b7280;
}

/* Modal overlays */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.dialog {
  background: #ffffff;
  padding: 1.5rem;
  border-radius: 8px;
  width: 320px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.dialog h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}
.dialog label {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  color: #374151;
}
.dialog label select,
.dialog label input {
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
.dialog-actions button:first-child {
  background: #e5e7eb;
  color: #1f2937;
}
.dialog-actions button:last-child {
  background: #e5e7eb;
  color: #1f2937;
}
.dialog-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.dialog-actions button:hover {
  background: #d1d5db;
}
.dialog p a {
  display: block;
  word-break: break-all;
  margin-top: 1rem;
  color: #374151;
  text-decoration: none;
}
.dialog p a:hover {
  text-decoration: underline;
}
</style>