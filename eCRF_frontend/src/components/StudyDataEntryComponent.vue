<template>
  <div class="study-data-container" v-if="study">
    <!-- Back Buttons -->
    <div class="back-buttons-container">
      <button v-if="showSelection" @click="goToDashboard" class="btn-back">
        <i :class="icons.back"></i> Back to Dashboard
      </button>
      <button v-if="!showSelection" @click="backToSelection" class="btn-back">
        <i :class="icons.back"></i> Back to Selection
      </button>
    </div>

    <!-- Header -->
    <div class="study-header-container">
      <div class="study-header">
        <h1 class="study-name">{{ study.metadata.study_name }}</h1>
        <p class="study-description">{{ study.metadata.study_description }}</p>
        <p class="study-meta">
          Subjects: {{ numberOfSubjects }} | Visits: {{ visitList.length }} | Groups: {{ groupList.length }}
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
              <li v-for="[key, val] in Object.entries(study.content.study_data.study)" :key="key">
                {{ key }}: {{ val }}
              </li>
            </ul>
          </div>
          <div v-if="!showSelection" class="details-block">
            <strong>Visit Info:</strong>
            <ul>
              <li v-for="[key, val] in Object.entries(visitList[currentVisitIndex] || {})" :key="key">
                {{ key }}: {{ val }}
              </li>
            </ul>
          </div>
        </div>
      </div>
      <hr />
    </div>

    <!-- Selection -->
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
            <td
              v-for="combo in visitCombos"
              :key="'visit-td-' + sIdx + '-' + combo.visitIndex"
              class="visit-cell"
            >
              <button
                class="select-btn"
                :class="[ statusClass(sIdx, combo.visitIndex), { 'visit-2-btn': combo.visitIndex === 1 } ]"
                @click="selectCell(sIdx, combo.visitIndex)"
              >
                Select
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Entry Form -->
    <div v-else class="entry-form-wrapper">
      <div class="bread-crumb">
        <div class="crumb-left">
          <strong>Study:</strong> {{ study.metadata.study_name }}
          <strong>Subject:</strong> {{ study.content.study_data.subjects[currentSubjectIndex].id }}
          <strong>Visit:</strong> {{ visitList[currentVisitIndex].name }}
        </div>
        <button type="button" class="legend-btn" @click="openLegendDialog" :title="'Legend / What does * mean?'">
          <i :class="icons.help || 'fas fa-question-circle'"></i>
        </button>
      </div>

      <div class="entry-form-section">
        <h2>
          Enter Data for Subject: {{ study.content.study_data.subjects[currentSubjectIndex].id }},
          Visit: “{{ visitList[currentVisitIndex].name }}”
        </h2>

        <div v-if="assignedModelIndices.length">
          <div v-for="mIdx in assignedModelIndices" :key="mIdx" class="section-block">
            <h3>{{ selectedModels[mIdx].title }}</h3>

            <div
              v-for="(field, fIdx) in selectedModels[mIdx].fields"
              :key="fIdx"
              class="form-field"
            >
              <label :for="fieldId(mIdx, fIdx)" class="field-label">
                <span>{{ field.label }}</span>
                <span v-if="field.constraints?.required" class="required">*</span>
                <em v-if="field.constraints?.helpText" class="help-inline">
                  {{ field.constraints.helpText }}
                </em>
                <i
                  v-if="hasConstraints(field)"
                  class="fas fa-question-circle helper-icon"
                  @click="openConstraintDialog(field)"
                ></i>
              </label>

              <!-- TEXT -->
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
                @blur="onFieldBlur(mIdx, fIdx)"
                @input="clearError(mIdx, fIdx)"
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
                @blur="onFieldBlur(mIdx, fIdx)"
                @input="clearError(mIdx, fIdx)"
              ></textarea>

              <!-- NUMBER -->
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
                @blur="validateField(mIdx, fIdx)"
                @input="clearError(mIdx, fIdx)"
              />

              <!-- CHECKBOX -->
              <FieldCheckbox
                v-else-if="field.type === 'checkbox'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                @change="validateField(mIdx, fIdx)"
              />

              <!-- RADIO -->
              <FieldRadioGroup
                v-else-if="field.type === 'radio'"
                :id="fieldId(mIdx, fIdx)"
                :name="fieldId(mIdx, fIdx)"
                :options="field.options || []"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :default-value="field.constraints?.defaultValue"
                v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                @change="validateField(mIdx, fIdx)"
                @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); }"
              />

              <!-- DATE -->
              <DateFormatPicker
                v-else-if="field.type === 'date'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :format="field.constraints?.dateFormat || 'dd.MM.yyyy'"
                :placeholder="field.placeholder || (field.constraints?.dateFormat || 'dd.MM.yyyy')"
                :min-date="field.constraints?.minDate || null"
                :max-date="field.constraints?.maxDate || null"
                :readonly="!!field.constraints?.readonly"
                @change="validateField(mIdx, fIdx)"
                @blur="validateField(mIdx, fIdx)"
              />

              <!-- TIME -->
              <FieldTime
                v-else-if="field.type === 'time'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :placeholder="field.placeholder || (field.constraints?.timeFormat || 'HH:mm')"
                v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                @change="validateField(mIdx, fIdx)"
                @blur="validateField(mIdx, fIdx)"
              />

              <!-- SELECT -->
              <FieldSelect
                v-else-if="field.type === 'select'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :options="field.options || []"
                :multiple="!!field.constraints?.allowMultiple"
                :readonly="!!field.constraints?.readonly"
                :default-value="field.constraints?.defaultValue"
                :placeholder="'Select…'"
                @update:modelValue="() => validateField(mIdx, fIdx)"
              />

              <!-- SLIDER (mode=slider) -->
              <FieldSlider
                v-else-if="field.type === 'slider' && (field.constraints?.mode || 'slider') === 'slider'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                v-bind="getSliderProps(field)"
                @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); }"
                @change="validateField(mIdx, fIdx)"
              />

              <!-- LINEAR SCALE -->
              <FieldLinearScale
                v-else-if="field.type === 'slider' && field.constraints?.mode === 'linear'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                v-bind="getLinearProps(field)"
                @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); }"
                @change="validateField(mIdx, fIdx)"
              />

              <!-- FILE -->
              <FieldFileUpload
                v-else-if="field.type === 'file'"
                :id="fieldId(mIdx, fIdx)"
                :value="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :constraints="field.constraints || {}"
                :readonly="!!field.constraints?.readonly"
                :required="!!field.constraints?.required"
                stage="runtime"
                @input="(meta) => setEntryValue(mIdx, fIdx, meta)"
                @file-selected="(file) => onRawFileSelected(mIdx, fIdx, file)"
              />

              <!-- FALLBACK -->
              <input
                v-else
                :id="fieldId(mIdx, fIdx)"
                type="text"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :placeholder="field.placeholder"
                :required="!!field.constraints?.required"
                :readonly="!!field.constraints?.readonly"
                @blur="onFieldBlur(mIdx, fIdx)"
                @input="clearError(mIdx, fIdx)"
              />

              <!-- ERROR -->
              <div v-if="fieldErrors(mIdx, fIdx)" class="error-message">
                {{ fieldErrors(mIdx, fIdx) }}
                <span
                  v-if="isFieldSkipped(mIdx,fIdx)"
                  class="skip-pill"
                  title="Required validation skipped for this field"
                >Skipped</span>
              </div>
              <div v-else-if="isFieldSkipped(mIdx,fIdx)" class="error-message">
                <span class="skip-pill" title="Required validation skipped for this field">Skipped</span>
              </div>
            </div>

          </div>

          <!-- Actions -->
          <div class="form-actions">
            <button
              @click="submitData"
              class="btn-save"
              :disabled="blockingErrorsPresent"
              :title="blockingErrorsPresent ? 'Fix validation errors before saving' : 'Save Data'"
            >
              Save Data
            </button>
            <button type="button" class="btn-clear" @click="clearCurrentSection" title="Clear all inputs">
              Clear
            </button>
          </div>
        </div>

        <div v-else class="no-assigned">
          <p>No sections are assigned to this Visit for your group.</p>
        </div>
      </div>
    </div>

    <!-- dialogs (unchanged) -->
    <div v-if="showShareDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>Generate Share Link</h3>
        <p>
          Sharing for Subject
          {{ shareParams.subjectIndex != null ? study.content.study_data.subjects[shareParams.subjectIndex]?.id : 'N/A' }},
          Visit {{ visitList[shareParams.visitIndex]?.name }}
        </p>
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
          <a :href="generatedLink" target="_blank">{{ generatedLink }}</a>
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

    <div v-if="showConstraintDialog" class="mini-overlay" @click.self="closeConstraintDialog">
      <div class="mini-dialog" role="dialog" aria-modal="true">
        <div class="mini-head">
          <h4 class="mini-title">{{ constraintDialogFieldName }}</h4>
          <button class="mini-close" @click="closeConstraintDialog" aria-label="Close">✕</button>
        </div>
        <ul class="mini-list">
          <li v-for="(line, idx) in constraintDialogItems" :key="idx">{{ line }}</li>
        </ul>
      </div>
    </div>

    <div v-if="showLegendDialog" class="mini-overlay" @click.self="closeLegendDialog">
      <div class="mini-dialog" role="dialog" aria-modal="true">
        <div class="mini-head">
          <h4 class="mini-title">Legend</h4>
          <button class="mini-close" @click="closeLegendDialog" aria-label="Close">✕</button>
        </div>
        <ul class="mini-list">
          <li><strong class="required">*</strong> indicates a <em>required</em> field.</li>
        </ul>
      </div>
    </div>

    <CustomDialog :message="dialogMessage" :isVisible="showDialog" @close="closeDialog" />

    <div v-if="showSkipDialog" class="dialog-overlay">
      <div class="dialog dialog-wide">
        <h3>Fix validation before saving</h3>
        <p>The fields below are required but empty. You can fill them now or choose to <em>Skip for now</em> to save the rest.</p>

        <div class="skip-list">
          <div class="skip-row" v-for="item in skipCandidates" :key="item.key">
            <div class="skip-left">
              <div class="skip-title"><strong>{{ item.sectionTitle }}</strong> / {{ item.fieldLabel }}</div>
            </div>
            <div class="skip-right">
              <label class="skip-chk">
                <input type="checkbox" v-model="skipSelections[item.key]" />
                Skip for now
              </label>
              <button class="btn-jump" @click="jumpToField(item)">Go to field</button>
            </div>
          </div>
        </div>

        <div class="dialog-actions">
          <button @click="confirmSkipSelection" class="btn-primary">Skip selected & Save</button>
          <button @click="cancelSkipSelection" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="loading">
    <p>Loading study details…</p>
  </div>
</template>

<script>
/* eslint-disable */
import axios from "axios";
import icons from "@/assets/styles/icons";
import CustomDialog from "@/components/CustomDialog.vue";
import DateFormatPicker from "@/components/DateFormatPicker.vue";
import FieldCheckbox from "@/components/fields/FieldCheckbox.vue";
import FieldRadioGroup from "@/components/fields/FieldRadioGroup.vue";
import FieldTime from "@/components/fields/FieldTime.vue";
import FieldSelect from "@/components/fields/FieldSelect.vue";
import FieldSlider from "@/components/fields/FieldSlider.vue";
import FieldLinearScale from "@/components/fields/FieldLinearScale.vue";
import FieldFileUpload from "@/components/fields/FieldFileUpload.vue";

import { createAjv, validateFieldValue } from "@/utils/jsonschemaValidation";

export default {
  name: "StudyDataEntryComponent",
  components: {
    CustomDialog,
    DateFormatPicker,
    FieldCheckbox,
    FieldRadioGroup,
    FieldTime,
    FieldSelect,
    FieldSlider,
    FieldLinearScale,
    FieldFileUpload,
  },
  data() {
    return {
      study: null,
      showSelection: true,
      showDetails: false,
      currentSubjectIndex: null,
      currentVisitIndex: null,
      currentGroupIndex: 0,

      entryData: [],
      skipFlags: [],
      validationErrors: {},

      icons,
      showShareDialog: false,
      shareParams: { subjectIndex: null, visitIndex: null, groupIndex: null },
      shareConfig: { permission: "view", maxUses: 1, expiresInDays: 7 },
      generatedLink: "",
      permissionError: false,

      showDialog: false,
      dialogMessage: "",
      showSkipDialog: false,
      skipCandidates: [],
      skipSelections: {},

      existingEntries: [],
      entryIds: [],
      ajv: null,

      showConstraintDialog: false,
      constraintDialogFieldName: "",
      constraintDialogItems: [],

      showLegendDialog: false,

      pendingFiles: {},
    };
  },

  computed: {
    token() { return this.$store.state.token; },
    visitList() { return this.study?.content?.study_data?.visits || []; },
    groupList() { return this.study?.content?.study_data?.groups || []; },
    selectedModels() { return this.study?.content?.study_data?.selectedModels || []; },
    assignments() { return this.study?.content?.study_data?.assignments || []; },
    numberOfSubjects() {
      const sd = this.study?.content?.study_data;
      return sd?.subjectCount != null ? sd.subjectCount : sd.subjects?.length || 0;
    },
    visitCombos() {
      return this.visitList.map((visit, vIdx) => ({ visitIndex: vIdx, label: `Visit: ${visit.name}` }));
    },
    assignedModelIndices() {
      const v = this.currentVisitIndex, g = this.currentGroupIndex;
      return this.selectedModels.map((_, mIdx) => mIdx).filter((mIdx) => !!this.assignments[mIdx]?.[v]?.[g]);
    },
    blockingErrorsPresent() {
      const keys = Object.keys(this.validationErrors || {});
      for (const k of keys) {
        const msg = this.validationErrors[k];
        if (!msg) continue;
        const idx = this.parseKey(k);
        if (!idx) continue;
        const { s, v, g, m, f } = idx;
        const isSkipped = !!(this.skipFlags[s]?.[v]?.[g]?.[m]?.[f]);
        if (isSkipped) continue;
        if (!/ is required\.$/.test(msg)) return true;
      }
      return false;
    },
  },

  async created() {
    this.ajv = createAjv();
    const studyId = this.$route.params.id;
    await this.loadStudy(studyId);
    await this.loadExistingEntries(studyId);
  },

  methods: {
    // --- tiny helpers for Vue 3 reactivity on deep arrays ---
    setDeepValue(s, v, g, m, f, val) {
      this.entryData[s][v][g][m][f] = val;
      // Optional nudge: replace inner row to ensure watchers pick it up if needed
      this.entryData[s][v][g][m] = [...this.entryData[s][v][g][m]];
    },
    setDeepSkip(s, v, g, m, f, on) {
      this.skipFlags[s][v][g][m][f] = !!on;
      this.skipFlags[s][v][g][m] = [...this.skipFlags[s][v][g][m]];
    },

    // ---------- deep set for file (reactive!) ----------
    setEntryValue(mIdx, fIdx, val) {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      console.log("[Entry] setEntryValue", { s, v, g, mIdx, fIdx, val });
      this.setDeepValue(s, v, g, mIdx, fIdx, val);
      this.clearError(mIdx, fIdx);
      this.validateField(mIdx, fIdx);
    },

    errorKey(mIdx, fIdx) {
      return [this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex, mIdx, fIdx].join("-");
    },
    parseKey(k) {
      const parts = String(k).split("-").map((x) => parseInt(x, 10));
      if (parts.length !== 5 || parts.some((n) => Number.isNaN(n))) return null;
      const [s, v, g, m, f] = parts;
      return { s, v, g, m, f };
    },

       onRawFileSelected(mIdx, fIdx, fileOrFiles) {
      // derive the stable per-field key (subject/visit/group/section/field)
      const key = this.errorKey(mIdx, fIdx);
      const arr = Array.isArray(fileOrFiles)
        ? fileOrFiles
        : (fileOrFiles ? [fileOrFiles] : []);
      console.log("[Entry] onRawFileSelected", { key, count: arr.length });
      const cur = Array.isArray(this.pendingFiles[key])
        ? this.pendingFiles[key]
        : (this.pendingFiles[key] ? [this.pendingFiles[key]] : []);
      // reassign to preserve Vue 3 reactivity when adding props
      this.pendingFiles = { ...this.pendingFiles, [key]: [...cur, ...arr] };
    },

    getSliderProps(field) {
      const c = field?.constraints || {};
      const min = c.percent ? 1 : (Number.isFinite(+c.min) ? +c.min : 1);
      const max = c.percent ? 100 : (Number.isFinite(+c.max) ? +c.max : (c.percent ? 100 : 5));
      const step = Number.isFinite(+c.step) && +c.step > 0 ? +c.step : 1;
      const marks = Array.isArray(c.marks) ? c.marks : [];
      return { min, max, step, readonly: !!c.readonly, percent: !!c.percent, showTicks: !!c.showTicks, marks };
    },
    getLinearProps(field) {
      const c = field?.constraints || {};
      const min = Number.isFinite(+c.min) ? Math.round(+c.min) : 1;
      let max = Number.isFinite(+c.max) ? Math.round(+c.max) : 5;
      if (max <= min) max = min + 1;
      return { min, max, leftLabel: c.leftLabel || "", rightLabel: c.rightLabel || "", readonly: !!c.readonly };
    },

    openLegendDialog() { this.showLegendDialog = true; },
    closeLegendDialog() { this.showLegendDialog = false; },

    hasConstraints(field) {
      const c = field?.constraints || {};
      const keys = Object.keys(c).filter((k) => k !== "required" && k !== "helpText");
      return keys.length > 0;
    },
    buildConstraintList(field) {
      const c = field?.constraints || {};
      const parts = [];
      if (c.readonly) parts.push("Read-only");
      if (field.type === "slider") {
        const mode = (c.mode || "slider").toLowerCase();
        if (mode === "slider") {
          parts.push(`Slider ${c.percent ? "(1–100%)" : ""}`);
          if (Number.isFinite(c.min)) parts.push(`Min: ${c.min}`);
          if (Number.isFinite(c.max)) parts.push(`Max: ${c.max}`);
          if (Number.isFinite(c.step)) parts.push(`Step: ${c.step}`);
          if (c.showTicks) parts.push("Show tick marks");
          if (Array.isArray(c.marks) && c.marks.length) {
            parts.push(`Labels: ${c.marks.map(m => `${m.value}="${m.label}"`).join(", ")}`);
          }
        } else {
          parts.push("Linear scale");
          parts.push(`Range: ${c.min ?? 1}–${c.max ?? 5} (integers)`);
          if (c.leftLabel) parts.push(`Left: “${c.leftLabel}”`);
          if (c.rightLabel) parts.push(`Right: “${c.rightLabel}”`);
        }
        return parts.length ? parts : ["No constraints."];
      }
      if (field.type === "text" || field.type === "textarea") {
        if (typeof c.minLength === "number") parts.push(`Min length: ${c.minLength}`);
        if (typeof c.maxLength === "number") parts.push(`Max length: ${c.maxLength}`);
        if (c.pattern) parts.push(`Pattern: ${c.pattern}`);
        if (c.transform && c.transform !== "none") {
          const t = c.transform.charAt(0).toUpperCase() + c.transform.slice(1).toLowerCase();
          parts.push(`Transform on save: ${t}`);
        }
      }
      if (field.type === "number") {
        if (typeof c.min === "number") parts.push(`Min: ${c.min}`);
        if (typeof c.max === "number") parts.push(`Max: ${c.max}`);
        if (typeof c.step === "number") parts.push(`Step: ${c.step}`);
        if (typeof c.minDigits === "number") parts.push(`Min digits: ${c.minDigits}`);
        if (typeof c.maxDigits === "number") parts.push(`Max digits: ${c.maxDigits}`);
        if (c.integerOnly) parts.push("Integer only");
      }
      if (field.type === "date") {
        if (c.dateFormat) parts.push(`Date format: ${c.dateFormat}`);
        if (c.minDate) parts.push(`Min date: ${c.minDate}`);
        if (c.maxDate) parts.push(`Max date: ${c.maxDate}`);
      }
      if (field.type === "time") {
        if (c.minTime) parts.push(`Min time: ${c.minTime}`);
        if (c.maxTime) parts.push(`Max time: ${c.maxTime}`);
        if (typeof c.step === "number") parts.push(`Step (sec): ${c.step}`);
      }
      if (field.type === "select" && c.allowMultiple) {
        parts.push("Multiple selection: allowed");
      }
      if (field.type === "file") {
      const storage = (c.storagePreference === "url") ? "Link via URL" : "Local upload";
      parts.push(`Storage: ${storage}`);

      // Only show "Allowed" when formats are restricted
      const allowedList = Array.isArray(c.allowedFormats)
        ? c.allowedFormats.filter(Boolean).map(String)
        : [];
      if (allowedList.length) {
        parts.push(`Allowed: ${allowedList.join(", ")}`);
      }

      // Only show Max size when it's a valid positive number
      const sizeNum = Number(c.maxSizeMB);
      if (Number.isFinite(sizeNum) && sizeNum > 0) {
        parts.push(`Max size: ${sizeNum} MB`);
      }

      if (c.allowMultipleFiles) parts.push("Multiple files: allowed");
      if (Array.isArray(c.modalities) && c.modalities.length) {
        parts.push(`Modalities: ${c.modalities.join(", ")}`);
      }
    }

      return parts.length ? parts : ["No constraints."];
    },
    openConstraintDialog(field) {
      this.constraintDialogFieldName = field?.label || "Field";
      this.constraintDialogItems = this.buildConstraintList(field);
      this.showConstraintDialog = true;
    },
    closeConstraintDialog() {
      this.showConstraintDialog = false;
      this.constraintDialogFieldName = "";
      this.constraintDialogItems = [];
    },

    applyTransform(transform, value) {
      const v = value == null ? "" : String(value);
      switch (String(transform || "none").toLowerCase()) {
        case "uppercase": return v.toUpperCase();
        case "lowercase": return v.toLowerCase();
        case "capitalize": return v.replace(/\b\w+/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
        default: return v;
      }
    },
    onFieldBlur(mIdx, fIdx) {
      const def = this.selectedModels[mIdx].fields[fIdx] || {};
      const cons = def.constraints || {};
      if (def.type === "text" || def.type === "textarea") {
        const cur = this.entryData[this.currentSubjectIndex][this.currentVisitIndex][this.currentGroupIndex][mIdx][fIdx];
        const transformed = this.applyTransform(cons.transform, cur);
        if (transformed !== cur) {
          this.setDeepValue(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex, mIdx, fIdx, transformed);
        }
      }
      this.validateField(mIdx, fIdx);
    },
    applyTransformsForSection() {
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach((def, fIdx) => {
          if (!def) return;
          const cons = def.constraints || {};
          if (def.type === "text" || def.type === "textarea") {
            const cur = this.entryData[this.currentSubjectIndex][this.currentVisitIndex][this.currentGroupIndex][mIdx][fIdx];
            const t = this.applyTransform(cons.transform, cur);
            if (t !== cur) {
              this.setDeepValue(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex, mIdx, fIdx, t);
            }
          }
        });
      });
    },

    setError(mIdx, fIdx, msg) {
      const k = this.errorKey(mIdx, fIdx);
      this.validationErrors = { ...this.validationErrors, [k]: msg };
    },
    clearError(mIdx, fIdx) {
      const k = this.errorKey(mIdx, fIdx);
      if (k in this.validationErrors) {
        const next = { ...this.validationErrors };
        delete next[k];
        this.validationErrors = next;
      }
    },
    fieldErrors(mIdx, fIdx) {
      return this.validationErrors[this.errorKey(mIdx, fIdx)] || "";
    },

    goToDashboard() {
      this.$router.push({ name: "Dashboard", query: { openStudies: "true" } });
    },
    async loadStudy(studyId) {
      try {
        const resp = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${studyId}`,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        this.study = resp.data;
        this.initializeEntryData();
        console.log("[Entry] Study loaded", { id: studyId, models: (this.selectedModels || []).length });
      } catch (err) {
        console.error("[Entry] loadStudy error", err);
        this.showDialogMessage("Failed to load study details.");
      }
    },
    async loadExistingEntries(studyId) {
      try {
        const resp = await axios.get(
          `http://127.0.0.1:8000/forms/studies/${studyId}/data_entries`,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        this.existingEntries = Array.isArray(resp.data) ? resp.data : (resp.data?.entries || []);
        this.populateFromExisting();
        console.log("[Entry] Existing entries", { count: (this.existingEntries || []).length });
      } catch (err) {
        console.error("Failed to load existing entries", err);
      }
    },

    defaultForField(f, { ignoreDefaults = false } = {}) {
      const c = f?.constraints || {};
      const t = String(f?.type || "").toLowerCase();
      const allowMulti = !!c.allowMultiple;
      if (t === "slider") return null;
      if (t === "file") return c.allowMultipleFiles ? [] : null;
      if (!ignoreDefaults && Object.prototype.hasOwnProperty.call(c, "defaultValue")) return c.defaultValue;
      if (!ignoreDefaults && Object.prototype.hasOwnProperty.call(f, "value")) return f.value;
      switch (t) {
        case "checkbox": return false;
        case "radio":
        case "select": return allowMulti ? [] : "";
        case "number": return "";
        case "date":
        case "time":
        case "text":
        case "textarea":
        default: return "";
      }
    },
    clearCurrentSection() {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      this.assignedModelIndices.forEach((mIdx) => {
        const section = this.selectedModels[mIdx];
        section.fields.forEach((f, fIdx) => {
          const cons = f?.constraints || {};
          if (cons.readonly) {
            this.clearError(mIdx, fIdx);
            return;
          }
          const next = this.defaultForField(f, { ignoreDefaults: false });
          this.setDeepValue(s, v, g, mIdx, fIdx, next);
          this.setDeepSkip(s, v, g, mIdx, fIdx, false);
          this.clearError(mIdx, fIdx);
        });
      });
    },
    initializeEntryData() {
      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;
      const nG = this.groupList.length;

      this.entryData = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () =>
          Array.from({ length: nG }, () =>
            this.selectedModels.map((sect) => sect.fields.map((f) => this.defaultForField(f)))
          )
        )
      );

      this.skipFlags = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () =>
          Array.from({ length: nG }, () =>
            this.selectedModels.map((sect) => sect.fields.map(() => false))
          )
        )
      );

      this.entryIds = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () => Array.from({ length: nG }, () => null))
      );

      this.validationErrors = {};
      console.log("[Entry] initializeEntryData matrix ready");
    },
    populateFromExisting() {
      this.initializeEntryData();
      (Array.isArray(this.existingEntries) ? this.existingEntries : []).forEach((e) => {
        const { subject_index: s, visit_index: v, group_index: g, data, id } = e;
        if (this.entryData[s] && this.entryData[s][v] && this.entryData[s][v][g]) {
          this.entryData[s][v][g] = data;
          this.entryIds[s][v][g] = id;

          const storedSkips = e.skipped_required_flags || e.skips;
          if (storedSkips) {
            this.skipFlags[s][v][g] = storedSkips;
          }
        }
      });
      console.log("[Entry] Populated matrix from existing");
    },

    selectCell(sIdx, vIdx) {
      this.currentSubjectIndex = sIdx;
      this.currentVisitIndex = vIdx;
      const subj = this.study.content.study_data.subjects[sIdx];
      const grpName = (subj.group || "").trim().toLowerCase();
      const idx = this.groupList.findIndex(
        (g) => (g.name || "").trim().toLowerCase() === grpName
      );
      this.currentGroupIndex = idx >= 0 ? idx : 0;
      this.showSelection = false;
      this.validationErrors = {};
      console.log("[Entry] Selected cell", { sIdx, vIdx, gIdx: this.currentGroupIndex });
    },
    backToSelection() {
      this.showSelection = true;
      this.showDetails = false;
      this.currentSubjectIndex = null;
      this.currentVisitIndex = null;
      this.currentGroupIndex = 0;
      this.validationErrors = {};
    },
    toggleDetails() { this.showDetails = !this.showDetails; },

    fieldId(mIdx, fIdx) {
      return `s${this.currentSubjectIndex}_v${this.currentVisitIndex}_g${this.currentGroupIndex}_m${mIdx}_f${fIdx}`;
    },

    isFieldSkipped(mIdx, fIdx) {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      return !!(this.skipFlags[s]?.[v]?.[g]?.[mIdx]?.[fIdx]);
    },
    setSkipForField(mIdx, fIdx, on) {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      if (!this.skipFlags[s] || !this.skipFlags[s][v] || !this.skipFlags[s][v][g]) return;
      this.setDeepSkip(s, v, g, mIdx, fIdx, on);
    },

    // ---------- VALIDATION ----------
    validateField(mIdx, fIdx) {
      const def = this.selectedModels[mIdx].fields[fIdx] || {};
      const cons = def.constraints || {};
      const label = def.label || "This field";
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      const val = this.entryData[s][v][g][mIdx][fIdx];
      const allowMultiFiles = !!cons.allowMultipleFiles;
      let isSkipped = !!this.skipFlags[s][v][g][mIdx][fIdx];

      const isEmpty = () => {
        if (def.type === "checkbox") return val !== true;
        if (def.type === "file") {
          if (allowMultiFiles) {
            const arr = Array.isArray(val) ? val : [];
            return arr.length === 0;
          } else {
            if (!val) return true;
            const src = val.source || (val.file && val.file.source) || "local";
            if (src === "url") {
              const url = (val.url || "").trim();
              return !url;
            }
            if (src === "local") {
              const meta = (val.file && typeof val.file === "object") ? val.file : val;
              const sizeNum = Number(meta.size);
              return !meta.name || !Number.isFinite(sizeNum) || sizeNum <= 0;
            }
            return true;
          }
        }
        if (Array.isArray(val)) return val.length === 0;
        return (val == null || (typeof val === "string" && val.trim() === ""));
      };

      console.log("[Validate] field", {
        label, key: this.errorKey(mIdx, fIdx), type: def.type, cons, value: val
      });

      this.clearError(mIdx, fIdx);

      if (isSkipped) {
        if (isEmpty()) return true;
        this.setSkipForField(mIdx, fIdx, false);
        isSkipped = false;
      }

      if (cons.required && isEmpty()) {
        this.setError(mIdx, fIdx, `${label} is required.`);
        console.warn("[Validate] required failed", { label, mIdx, fIdx });
        return false;
      }

      if (def.type === "slider") {
        if (val == null || val === "") return true;
        const mode = (cons.mode || "slider").toLowerCase();
        const n = Number(val);
        if (!Number.isFinite(n)) {
          this.setError(mIdx, fIdx, `${label} must be a number.`);
          return false;
        }
        if (mode === "slider") {
          const min = cons.percent ? 1 : (Number.isFinite(+cons.min) ? +cons.min : 1);
          const max = cons.percent ? 100 : (Number.isFinite(+cons.max) ? +cons.max : (cons.percent ? 100 : 5));
          const step = Number.isFinite(+cons.step) && +cons.step > 0 ? +cons.step : 1;
          if (n < min || n > max) {
            this.setError(mIdx, fIdx, `${label} must be between ${min} and ${max}.`);
            return false;
          }
          if (step >= 1) {
            const k = (n - min) / step;
            if (Math.abs(k - Math.round(k)) > 1e-9) {
              this.setError(mIdx, fIdx, `${label} must align to step ${step}.`);
              return false;
            }
          }
          return true;
        } else {
          const min = Number.isFinite(+cons.min) ? Math.round(+cons.min) : 1;
          const max = Number.isFinite(+cons.max) ? Math.round(+cons.max) : 5;
          if (n < min || n > max || Math.round(n) !== n) {
            this.setError(mIdx, fIdx, `${label} must be an integer between ${min} and ${max}.`);
            return false;
          }
          return true;
        }
      }

      if (def.type !== "file") {
        const { valid, message } = validateFieldValue(this.ajv, def, val);
        if (!valid) {
          this.setError(mIdx, fIdx, message || `${label} is invalid.`);
          console.warn("[Validate] schema failed", { label, message });
          return false;
        }
      }

      if (def.type === "date" && val) {
        const fmt = cons.dateFormat || "dd.MM.yyyy";
        const parse = (s) => {
          const map = {
            "dd.MM.yyyy": /^(\d{2})\.(\d{2})\.(\d{4})$/,
            "MM-dd-yyyy": /^(\d{2})-(\d{2})-(\d{4})$/,
            "dd-MM-yyyy": /^(\d{2})-(\d{2})-(\d{4})$/,
            "yyyy-MM-dd": /^(\d{4})-(\d{2})-(\d{2})$/,
            "MM/yyyy": /^(\d{2})\/(\d{4})$/,
            "MM-yyyy": /^(\d{2})-(\d{4})$/,
            "yyyy/MM": /^(\d{4})\/(\d{2})$/,
            "yyyy-MM": /^(\d{4})-(\d{2})$/,
            "yyyy": /^(\d{4})$/,
          };
          const rx = map[fmt] || map[fmt.replace(".", "\\.")];
          if (!rx) return null;
          const m = rx.exec(String(s));
          if (!m) return null;
          let y, M, d;
          if (fmt === "dd.MM.yyyy") { d=+m[1]; M=+m[2]; y=+m[3]; }
          else if (fmt === "MM-dd-yyyy") { M=+m[1]; d=+m[2]; y=+m[3]; }
          else if (fmt === "dd-MM-yyyy") { d=+m[1]; M=+m[2]; y=+m[3]; }
          else if (fmt === "yyyy-MM-dd") { y=+m[1]; M=+m[2]; d=+m[3]; }
          else if (fmt === "MM/yyyy" || "MM-yyyy") { M=+m[1]; y=+m[2]; d=1; }
          else if (fmt === "yyyy/MM" || "yyyy-MM") { y=+m[1]; M=+m[2]; d=1; }
          else if (fmt === "yyyy") { y=+m[1]; M=1; d=1; }
          return new Date(y, M-1, d);
        };
        const d = parse(val);
        if (d) {
          if (cons.minDate) {
            const md = parse(cons.minDate);
            if (md && d < md) { this.setError(mIdx, fIdx, `${def.label || "This field"} must be ≥ ${cons.minDate}.`); return false; }
          }
          if (cons.maxDate) {
            const xd = parse(cons.maxDate);
            if (xd && d > xd) { this.setError(mIdx, fIdx, `${def.label || "This field"} must be ≤ ${cons.maxDate}.`); return false; }
          }
        }
      }

      if (def.type === "time" && val) {
        const toSec = (s) => {
          const mm = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(String(s));
          if (!mm) return null;
          const h = +mm[1], mi = +mm[2], se = mm[3] ? +mm[3] : 0;
          return h * 3600 + mi * 60 + se;
        };
        const secs = toSec(val);
        if (secs != null) {
          if (cons.minTime) {
            const m = toSec(cons.minTime);
            if (m != null && secs < m) { this.setError(mIdx, fIdx, `${def.label || "This field"} must be ≥ ${cons.minTime}.`); return false; }
          }
          if (cons.maxTime) {
            const x = toSec(cons.maxTime);
            if (x != null && secs > x) { this.setError(mIdx, fIdx, `${def.label || "This field"} must be ≤ ${cons.maxTime}.`); return false; }
          }
        }
      }
      return true;
    },

    validateCurrentSection() {
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach((_, fIdx) => { this.clearError(mIdx, fIdx); });
      });

      let ok = true;
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach((_, fIdx) => {
          const r = this.validateField(mIdx, fIdx);
          ok = ok && r;
        });
      });
      return ok;
    },

    computeRequiredFailures() {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      const items = [];
      this.assignedModelIndices.forEach((mIdx) => {
        const section = this.selectedModels[mIdx];
        (section.fields || []).forEach((f, fIdx) => {
          const c = f?.constraints || {};
          if (!c.required) return;
          if (this.skipFlags[s][v][g][mIdx][fIdx]) return;
          const val = this.entryData[s][v][g][mIdx][fIdx];
          const empty =
            (f.type === "checkbox" ? val !== true :
            f.type === "file"? (c.allowMultipleFiles? !(Array.isArray(val) && val.length > 0): (!val || (val.source === "url"? !(val.url && String(val.url).trim()): !(val.name && Number.isFinite(Number(val.size)))))):
            Array.isArray(val) ? val.length === 0 :
            (val == null || (typeof val === "string" && val.trim() === "")));
          if (empty) {
            items.push({
              key: this.errorKey(mIdx, fIdx),
              id: this.fieldId(mIdx, fIdx),
              sectionIndex: mIdx,
              fieldIndex: fIdx,
              sectionTitle: section.title || `Section ${mIdx + 1}`,
              fieldLabel: f.label || `Field ${fIdx + 1}`,
            });
          }
        });
      });
      return items;
    },

    // ---------- FILE UPLOADS ----------
    async uploadPendingFilesForCurrentSection() {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      const studyId = this.study?.metadata?.id;

      for (const mIdx of this.assignedModelIndices) {
        const section = this.selectedModels[mIdx];
        for (let fIdx = 0; fIdx < (section.fields || []).length; fIdx++) {
          const def = section.fields[fIdx] || {};
          if (def.type !== "file") continue;

          const key = this.errorKey(mIdx, fIdx);
          const cons = def.constraints || {};
         const allowMulti = !!cons.allowMultipleFiles;
         const val = this.entryData[s][v][g][mIdx][fIdx];
         if (!val && !allowMulti) continue;

          const modalities = Array.isArray(def?.constraints?.modalities) ? def.constraints.modalities : [];
          const modalitiesJson = JSON.stringify(modalities || []);

          const pendingArr = Array.isArray(this.pendingFiles[key]) ? this.pendingFiles[key] : (this.pendingFiles[key] ? [this.pendingFiles[key]] : []);

          // Helper to find matching raw File for a meta
          const matchFile = (meta) => pendingArr.find(f =>
            f && meta && f.name === meta.name && Number(f.size) === Number(meta.size) && (!!f.lastModified ? f.lastModified === meta.lastModified : true)
          );

          if (allowMulti) {
            const items = Array.isArray(val) ? [...val] : [];
            // Upload local metas
            for (let i = 0; i < items.length; i++) {
              const it = items[i];
              if (!it || it.dbId) continue;
              if (it.source === "local") {
                const file = matchFile(it);
                if (!file) continue;
                console.log("[Upload] POST /files (multi)", { key, name: file.name, size: file.size, modalities });
                const fd = new FormData();
                fd.append("uploaded_file", file);
                fd.append("description", def.label || "");
                fd.append("storage_option", "local");
                fd.append("subject_index", String(s));
                fd.append("visit_index", String(v));
                fd.append("group_index", String(g));
                fd.append("modalities_json", modalitiesJson);
                const resp = await axios.post(
                  `http://127.0.0.1:8000/forms/studies/${studyId}/files`,
                  fd,
                  { headers: { Authorization: `Bearer ${this.token}`, "Content-Type": "multipart/form-data" } }
                );
                const saved = resp?.data || {};
                items[i] = {
                  ...it,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option: saved.storage_option || "local",
                  file_name: saved.file_name || it.name,
                };
              } else if (it.source === "url" && it.url) {
                try {
                  console.log("[Upload] POST /files/url (multi)", { key, url: it.url, modalities });
                  const fd = new FormData();
                  fd.append("url", it.url);
                  fd.append("description", def.label || "");
                  fd.append("storage_option", "url");
                  fd.append("subject_index", String(s));
                  fd.append("visit_index", String(v));
                  fd.append("group_index", String(g));
                  fd.append("modalities_json", modalitiesJson);
                  const resp = await axios.post(
                    `http://127.0.0.1:8000/forms/studies/${studyId}/files/url`,
                    fd,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                  );
                  const saved = resp?.data || {};
                  items[i] = {
                    ...it,
                    dbId: saved.id,
                    file_path: saved.file_path,
                    storage_option: "url",
                    file_name: saved.file_name || "",
                  };
                } catch (e) {
                  console.warn("URL record create failed; keeping raw URL.", e);
                }
              }
            }
            this.setDeepValue(s, v, g, mIdx, fIdx, items);
            delete this.pendingFiles[key];
          } else {
            // Single-file behavior (unchanged)
            if (!val) continue;
            if (val.source === "local" && (pendingArr[0] instanceof File)) {
              const file = pendingArr[0];
              console.log("[Upload] POST /files", { key, name: file.name, size: file.size, modalities });
              const fd = new FormData();
              fd.append("uploaded_file", file);
              fd.append("description", def.label || "");
              fd.append("storage_option", "local");
              fd.append("subject_index", String(s));
              fd.append("visit_index", String(v));
              fd.append("group_index", String(g));
              fd.append("modalities_json", modalitiesJson);
              const resp = await axios.post(
                `http://127.0.0.1:8000/forms/studies/${studyId}/files`,
                fd,
                { headers: { Authorization: `Bearer ${this.token}`, "Content-Type": "multipart/form-data" } }
              );
              const saved = resp?.data || {};
              this.setDeepValue(s, v, g, mIdx, fIdx, {
                ...val,
                dbId: saved.id,
                file_path: saved.file_path,
                storage_option: saved.storage_option || "local",
                file_name: saved.file_name || val.name,
              });
              delete this.pendingFiles[key];
            }
            if (val.source === "url" && val.url) {
              try {
                console.log("[Upload] POST /files/url", { key, url: val.url, modalities });
                const fd = new FormData();
                fd.append("url", val.url);
                fd.append("description", def.label || "");
                fd.append("storage_option", "url");
                fd.append("subject_index", String(s));
                fd.append("visit_index", String(v));
                fd.append("group_index", String(g));
                fd.append("modalities_json", modalitiesJson);
                const resp = await axios.post(
                  `http://127.0.0.1:8000/forms/studies/${studyId}/files/url`,
                  fd,
                  { headers: { Authorization: `Bearer ${this.token}` } }
                );
                const saved = resp?.data || {};
                this.setDeepValue(s, v, g, mIdx, fIdx, {
                  ...val,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option: "url",
                  file_name: saved.file_name || ""
                });
              } catch (e) {
                console.warn("URL record create failed; continuing with raw URL only.", e);
              }
            }
          }
        }
      }
    },

    async submitData() {
      this.applyTransformsForSection();

      const ok = this.validateCurrentSection();
      const blocking = Object.entries(this.validationErrors)
        .filter(([k, msg]) => {
          if (!msg) return false;
          const idx = this.parseKey(k);
          if (!idx) return true;
          const { s, v, g, m, f } = idx;
          const isSkipped = !!(this.skipFlags[s]?.[v]?.[g]?.[m]?.[f]);
          if (isSkipped) return false;
          return !/ is required\.$/.test(msg);
        });

      if (!ok && blocking.length) {
        console.warn("[Entry] blocking validation errors", this.validationErrors);
        this.showDialogMessage("Please fix validation errors before saving.");
        return;
      }

      const requiredFailures = this.computeRequiredFailures();
      if (requiredFailures.length) {
        this.skipCandidates = requiredFailures;
        this.skipSelections = requiredFailures.reduce((acc, it) => { acc[it.key] = false; return acc; }, {});
        this.showSkipDialog = true;
        return;
      }

      try {
        await this.uploadPendingFilesForCurrentSection();
      } catch (e) {
        console.error("File upload/register failed:", e);
        this.showDialogMessage("File upload failed. Please try again.");
        return;
      }

      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      const payload = {
        study_id: this.study.metadata.id,
        subject_index: s,
        visit_index: v,
        group_index: g,
        data: this.entryData[s][v][g],
        skipped_required_flags: this.skipFlags[s][v][g],
      };
      const existingId = this.entryIds[s][v][g];

      try {
        if (existingId) {
          const resp = await axios.put(
            `http://127.0.0.1:8000/forms/studies/${this.study.metadata.id}/data_entries/${existingId}`,
            payload,
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          console.log("[Entry] updated", { id: existingId });
          this.showDialogMessage("Data updated successfully.");
          const idx = this.existingEntries.findIndex(x => x.id === existingId);
          if (idx >= 0) this.existingEntries.splice(idx, 1, resp.data);
        } else {
          const resp = await axios.post(
            `http://127.0.0.1:8000/forms/studies/${this.study.metadata.id}/data`,
            payload,
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          const newId = resp?.data?.id;
          this.entryIds[s][v][g] = newId;
          const saved = {
            id: newId,
            study_id: this.study.metadata.id,
            subject_index: s,
            visit_index: v,
            group_index: g,
            data: this.entryData[s][v][g],
            skipped_required_flags: resp?.data?.skipped_required_flags ?? this.skipFlags[s][v][g],
            form_version: resp?.data?.form_version ?? 1,
            created_at: resp?.data?.created_at ?? new Date().toISOString(),
          };
          (this.existingEntries = this.existingEntries || []).push(saved);
          console.log("[Entry] created", { id: newId });
          this.showDialogMessage("Data saved successfully.");
        }
      } catch (err) {
        console.error(err);
        this.showDialogMessage("Failed to save data. Check console for details.");
      }
    },

    confirmSkipSelection() {
      const s = this.currentSubjectIndex, v = this.currentVisitIndex, g = this.currentGroupIndex;
      this.skipCandidates.forEach((it) => {
        const on = !!this.skipSelections[it.key];
        this.setDeepSkip(s, v, g, it.sectionIndex, it.fieldIndex, on);
        if (on) this.clearError(it.sectionIndex, it.fieldIndex);
        console.log("[Entry] confirmSkipSelection set", {
          s, v, g, m: it.sectionIndex, f: it.fieldIndex, on
        });
      });
      this.showSkipDialog = false;
      this.submitData();
    },
    cancelSkipSelection() { this.showSkipDialog = false; },
    jumpToField(item) {
      this.showSkipDialog = false;
      this.$nextTick(() => {
        const el = document.getElementById(item.id);
        if (el && typeof el.focus === "function") el.focus();
      });
    },

    openShareDialog(sIdx, vIdx, gIdx) {
      this.shareParams = { subjectIndex: sIdx, visitIndex: vIdx, groupIndex: gIdx };
      this.generatedLink = "";
      this.showShareDialog = true;
    },
    async createShareLink() {
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
        const resp = await axios.post("http://localhost:8000/forms/share-link/", {
          ...payload
        }, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.generatedLink = resp.data.link;
      } catch (err) {
        if (err.response?.status === 403) this.permissionError = true;
      }
    },

    showDialogMessage(message) { this.dialogMessage = message; this.showDialog = true; },
    closeDialog() { this.showDialog = false; this.dialogMessage = ""; },

    statusFor(sIdx, vIdx) {
      const subj = this.study.content.study_data.subjects[sIdx];
      const name = (subj.group || "").trim().toLowerCase();
      const gi = this.groupList.findIndex((g) => (g.name || "").trim().toLowerCase() === name);
      const gIdx = gi >= 0 ? gi : 0;

      const e = (Array.isArray(this.existingEntries) ? this.existingEntries : []).find(
        (x) => x.subject_index === sIdx && x.visit_index === vIdx && x.group_index === gIdx
      );
      if (!e) return "none";

      const hasSkip = !!(e.skipped_required_flags && e.skipped_required_flags.some(row => Array.isArray(row) && row.some(Boolean)));
      if (hasSkip) return "skipped";

      const assigned = this.assignments.map((_, i) => i).filter((i) => this.assignments[i]?.[vIdx]?.[gIdx]);
      const flat = assigned.flatMap((i) => e.data[i] || []);
      const total = flat.length;
      const filled = flat.filter((v) => v != null && v !== "").length;
      if (filled === 0) return "none";
      if (filled === total) return "complete";
      return "partial";
    },
    statusClass(sIdx, vIdx) {
      const s = this.statusFor(sIdx, vIdx);
      return s === "skipped" ? "status-skipped" : `status-${s}`;
    },
  },
};
</script>


<style scoped>
/* matrix */
.selection-matrix { width: 100%; border-collapse: collapse; margin-bottom: 32px; table-layout: fixed; }
.selection-matrix th, .selection-matrix td { border: 1px solid #e5e7eb; padding: 12px; text-align: center; vertical-align: middle; }
.selection-matrix th { background: #f9fafb; font-weight: 600; color: #1f2937; }
.subject-cell { background: #f9fafb; font-weight: 500; color: #374151; width: 20%; }
.visit-cell { width: 40%; }
.select-btn { color: #fff; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: opacity 0.2s; display: block; margin: 0 auto; }
.select-btn.status-none { background: #e5e7eb; color: #1f2937; }       /* gray */
.select-btn.status-partial { background: #fbbf24; }                    /* yellow */
.select-btn.status-complete { background: #16a34a; }                   /* green */
.select-btn.status-skipped { background: #ef4444; }                    /* red */
.select-btn:hover { opacity: 0.8; }

/* container */
.study-data-container { max-width: 960px; margin: 24px auto; padding: 24px; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

/* back buttons */
.back-buttons-container { margin-bottom: 16px; }
.btn-back { background: #d1d5db; color: #1f2937; border: none; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 6px; }
.btn-back:hover { background: #9ca3af; }
.btn-back i { font-size: 14px; }

/* header */
.study-header-container { margin-bottom: 24px; }
.study-header { text-align: center; margin-bottom: 16px; }
.study-name { font-size: 24px; font-weight: 600; color: #1f2937; margin-bottom: 8px; }
.study-description { font-size: 16px; color: #4b5563; margin-bottom: 8px; }
.study-meta { font-size: 14px; color: #6b7280; }
hr { margin: 12px 0; border: 0; border-top: 1px solid #e5e7eb; }

/* details panel */
.details-panel { margin-bottom: 16px; }
.details-controls { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.details-toggle-btn { background: none; border: none; color: #374151; font-size: 14px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.details-toggle-btn i { font-size: 14px; }
.share-icon { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 16px; padding: 6px; line-height: 1; }
.share-icon i { font-family: 'Font Awesome 5 Free' !important; font-weight: 900; font-style: normal; display: inline-block; }
.share-icon:hover { color: #374151; }
.details-content { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 16px; }
.details-block { margin-bottom: 16px; }
.details-block strong { display: block; font-size: 14px; color: #1f2937; margin-bottom: 6px; }
.details-block ul { margin: 0 0 12px 16px; padding: 0; }
.details-block li { font-size: 14px; color: #374151; }

/* breadcrumb */
.bread-crumb { background: #f9fafb; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 24px; font-size: 14px; color: #374151; display: flex; align-items: center; justify-content: space-between; }
.crumb-left { display: flex; gap: 10px; flex-wrap: wrap; }
.legend-btn { background: transparent; border: none; cursor: pointer; padding: 2px 6px; line-height: 1; color: #6b7280; }
.legend-btn:hover { color: #374151; }

/* section + fields */
.entry-form-section h2 { font-size: 18px; font-weight: 600; color: #1f2937; margin-bottom: 16px; }
.section-block { margin-bottom: 16px; padding: 16px; border: 1px solid #e5e7eb; border-radius: 6px; background: #ffffff; }
.section-block h3 { margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1f2937; }
.form-field { margin-bottom: 16px; }
.field-label { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.helper-icon { font-size: 14px; color: #6b7280; cursor: pointer; }
.helper-icon:hover { color: #374151; }
.form-field label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #1f2937; }
.required { color: #dc2626; margin-left: 4px; }
.help-inline { font-style: italic; color: #6b7280; margin-left: 8px; }

/* inputs */
input[type="text"], textarea, input[type="number"], input[type="date"], select {
  width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; font-size: 14px; color: #1f2937;
}
input:focus, textarea:focus, select:focus { outline: none; border-color: #6b7280; box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1); }

/* errors */
.error-message { color: #dc2626; font-size: 12px; margin-top: 4px; }

/* empty state */
.no-assigned { font-style: italic; color: #6b7280; margin-top: 12px; }

/* actions */
.form-actions { text-align: right; margin-top: 16px; }
.btn-save { background: #16a34a; color: #ffffff; border: none; padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; transition: background 0.2s; }
.btn-save[disabled] { opacity: 0.5; cursor: not-allowed; }
.btn-save:hover:not([disabled]) { background: #15803d; }

.btn-clear { background: #e5e7eb; color: #1f2937; border: none; padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; margin-left: 8px; transition: background 0.2s; }
.btn-clear:hover { background: #d1d5db; }

/* overlay+dialogs */
.loading { text-align: center; padding: 50px; font-size: 16px; color: #6b7280; }
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.dialog { background: #ffffff; padding: 1.5rem; border-radius: 8px; width: 320px; max-width: 90%; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); }
.dialog h3 { margin: 0 0 1rem 0; font-size: 1.25rem; font-weight: 600; color: #1f2937; }
.dialog label { display: block; margin-bottom: 0.75rem; font-size: 0.9rem; color: #374151; }
.dialog label select, .dialog label input { width: 100%; margin-top: 0.25rem; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9rem; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; }
.dialog-actions button:first-child { background: #e5e7eb; color: #1f2937; }
.dialog-actions button:last-child { background: #e5e7eb; color: #1f2937; }
.dialog-actions button { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.dialog-actions button:hover { background: #d1d5db; }
.dialog p a { display: block; word-break: break-all; margin-top: 1rem; color: #374151; text-decoration: none; }
.dialog p a:hover { text-decoration: underline; }

/* mini dialog */
.mini-overlay { position: fixed; inset: 0; background: rgba(17,24,39,0.35); display: flex; align-items: center; justify-content: center; z-index: 1200; }
.mini-dialog { width: 360px; max-width: 92%; background: #fff; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); padding: 12px 12px 10px; }
.mini-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.mini-title { margin: 0; font-size: 16px; font-weight: 600; color: #111827; }
.mini-close { background: transparent; border: none; font-size: 16px; line-height: 1; cursor: pointer; color: #6b7280; }
.mini-close:hover { color: #111827; }
.mini-list { margin: 0; padding-left: 18px; color: #374151; font-size: 14px; }
.mini-list li { margin: 4px 0; }

/* skip dialog */
.dialog-wide { width: 680px; max-width: 95%; }
.skip-list { max-height: 360px; overflow: auto; border: 1px dashed #e5e7eb; padding: 8px; border-radius: 8px; margin: 10px 0; }
.skip-row { display: flex; align-items: center; justify-content: space-between; padding: 8px; border-bottom: 1px solid #f3f4f6; gap: 12px; }
.skip-row:last-child { border-bottom: none; }
.skip-left { min-width: 0; }
.skip-title { font-size: 14px; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.skip-right { display: flex; align-items: center; gap: 8px; }
.skip-chk { display: inline-flex; align-items: center; gap: 8px; }
.btn-jump { background: #e5e7eb; color: #111827; border: none; padding: 6px 10px; border-radius: 6px; cursor: pointer; }
.btn-jump:hover { background: #d1d5db; }

.btn-primary { background: #2563eb; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; }
.btn-option { background: #e5e7eb; color: #111827; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; }

/* tiny pill near error */
.skip-pill {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  font-size: 11px;
  border-radius: 999px;
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
}
</style>
