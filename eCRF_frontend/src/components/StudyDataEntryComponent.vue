<template>
  <div class="study-data-container" v-if="study">
    <!-- Back Buttons (hidden for shared links AND while Merge panel is open) -->
     <div class="back-buttons-container" v-if="!isShared">
       <!-- Merge mode back button (same styling/position) -->
       <button v-if="isMergeMode" @click="closeMergeStudy" class="btn-back">
        Back to Selection
       </button>

       <!-- Normal behavior -->
       <template v-else>
         <button v-if="showSelection" @click="goToDashboard" class="btn-back">
          Back to Dashboard
         </button>
         <button v-else @click="backToSelection" class="btn-back">
          Back to Selection
         </button>
       </template>
     </div>

    <!-- Header -->
    <div class="study-header-container">
      <div class="study-header">
        <h1 class="study-name">{{ study.metadata.study_name }}</h1>
        <p class="study-description">{{ study.metadata.study_description }}</p>
        <p class="study-meta">
          Subjects: {{ numberOfSubjects }} | Visits: {{ visitList.length }} | Groups: {{ groupList.length }}
        </p>
        <p v-if="isShared" class="shared-banner">
          Shared link (permission: <strong>{{ sharedPermission }}</strong>)
        </p>
      </div>

      <div class="details-panel">
        <div class="details-controls">
          <!-- Hide details toggle while Merge panel is open (keeps UI clean) -->
          <button v-if="!isMergeMode" @click="toggleDetails" class="details-toggle-btn">
            <i :class="showDetails ? icons.toggleUp : icons.toggleDown"></i>
            {{ showDetails ? 'Hide Study Details' : 'Show Study Details' }}
          </button>

          <!-- Merge Study button placed in the same row (simple, no teleport/mount hacks) -->
          <button
            v-if="showSelection && !isShared && !isMergeMode"
            type="button"
            class="btn-merge-study"
            @click="openMergeStudy"
          >
            Import data from other device
          </button>

          <!-- Share icon hidden for shared mode -->
          <button
            v-if="!showSelection && !isShared"
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
              <li v-for="[key, val] in studyInfoEntries" :key="key">
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

    <!-- Selection (hidden in shared mode; shared preselects) -->
    <template v-if="showSelection && !isShared">
      <!-- Matrix view (hidden when Merge is open) -->
      <SelectionMatrixView
        v-if="!isMergeMode"
        :matrixReady="matrixReady"
        :visitList="visitList"
        :selectedVisitIndex="selectedVisitIndex"
        :displayedVisitIndices="displayedVisitIndices"
        :subjects="sd.subjects"
        :visitLoading="visitLoading"
        :isFluidMatrix="isFluidMatrix"
        :subjectColStyle="subjectColStyle"
        :visitColStyle="visitColStyle"
        :statusClass="statusClassFast"
        :selectedVersion="selectedVersion"
        :infoIcon="icons.info"
        :showGroupColumn="canSeeGroupColumn"
        @update:selectedVisitIndex="selectedVisitIndex = $event"
        @add-subjects="openSubjectDialog"
        @select-cell="selectCell"
        @open-status-legend="openStatusLegend"
      />

      <!-- Merge Study panel (replaces matrix within the same container) -->
      <section v-else class="merge-panel">
        <!-- MergeStudy already has its own back button; no extra title/back here -->
        <MergeStudy :studyId="studyId" :returnTo="`/dashboard/studies/${studyId}/add-data`" />
      </section>
    </template>

    <!-- Entry Form -->
    <div v-else class="entry-form-wrapper">
      <div class="bread-crumb">
        <div class="crumb-left">
          <strong>Study:</strong> {{ study.metadata.study_name }}
          <strong>Subject:</strong> {{ sd.subjects?.[currentSubjectIndex]?.id }}
          <strong>Visit:</strong> {{ visitList[currentVisitIndex].name }}
          <span v-if="!isShared && selectedVersion" class="version-helper">Saving to Version {{ selectedVersion }}</span>
        </div>
        <button type="button" class="legend-btn" @click="openLegendDialog" :title="'Legend / What does * mean?'">
          <i :class="icons.help || 'fas fa-question-circle'"></i>
        </button>
      </div>

      <div class="entry-form-section">
        <h2>
          Enter Data for Subject: {{ sd.subjects?.[currentSubjectIndex]?.id }},
          Visit: “{{ visitList[currentVisitIndex].name }}”
        </h2>

        <!-- Only assigned sections are shown -->
        <div v-if="assignedModelIndices.length">
          <div
            v-for="mIdx in assignedModelIndices"
            :key="'sec-'+mIdx"
            class="section-block"
          >
            <h3>{{ selectedModels[mIdx].title }}</h3>

            <div
              v-for="(field, fIdx) in selectedModels[mIdx].fields"
              :key="'f-'+mIdx+'-'+fIdx"
              class="form-field"
            >
              <label :for="fieldId(mIdx, fIdx)" class="field-label">
                <span>{{ field.label || field.name || field.title }}</span>
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :disabled="!canEdit"
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
                :disabled="!canEdit"
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :disabled="!canEdit"
                @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); }"
                @change="validateField(mIdx, fIdx)"
              />

              <!-- LINEAR SCALE -->
              <FieldLinearScale
                v-else-if="field.type === 'slider' && field.constraints?.mode === 'linear'"
                :id="fieldId(mIdx, fIdx)"
                v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                v-bind="getLinearProps(field)"
                :disabled="!canEdit"
                @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); }"
                @change="validateField(mIdx, fIdx)"
              />

              <!-- FILE -->
              <FieldFileUpload
                v-else-if="field.type === 'file'"
                :id="fieldId(mIdx, fIdx)"
                :value="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                :constraints="field.constraints || {}"
                :readonly="!!field.constraints?.readonly || !canEdit"
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
                :readonly="!!field.constraints?.readonly || !canEdit"
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
              :disabled="blockingErrorsPresent || !canEdit"
              :title="!canEdit ? 'This shared link is view-only' : (blockingErrorsPresent ? 'Fix validation errors before saving' : 'Save Data')"
            >
              Save Data
            </button>
            <button type="button" class="btn-clear" @click="clearCurrentSection" title="Clear all inputs" :disabled="!canEdit">
              Clear
            </button>
          </div>
        </div>

        <div v-else class="no-assigned">
          <p>No sections are assigned to this Visit for your group.</p>
        </div>
      </div>
    </div>

    <!-- dialogs (unchanged except share hidden on shared) -->
    <div v-if="showShareDialog && !isShared" class="dialog-overlay">
      <div class="dialog">
        <h3>Generate Share Link</h3>
        <p>
          Sharing for Subject
          {{ shareParams.subjectIndex != null ? sd.subjects?.[shareParams.subjectIndex]?.id : 'N/A' }},
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

        <!-- Copy link UI (only after successful generation) -->
        <div v-if="generatedLink" class="share-result">
          <span class="share-result-text">Link generated.</span>
          <button type="button" class="btn-copy-link" @click="copyGeneratedLink">
            Copy link
          </button>
        </div>
        <div v-if="generatedLink" class="generated-link-preview" :title="generatedLink">
          {{ generatedLink }}
        </div>
        <div v-if="copyStatus" class="copy-status">
          {{ copyStatus }}
        </div>
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

    <!-- Constraint dialog -->
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

    <!-- Legend dialog (field-level) -->
    <div v-if="showLegendDialog" class="mini-overlay" @click.self="closeLegendDialog">
      <div class="mini-dialog" role="dialog" aria-modal="true">
        <div class="mini-head">
          <h4 class="mini-title">Legend</h4>
          <button class="mini-close" @click="closeLegendDialog" aria-label="Close">✕</button>
        </div>
        <ul class="mini-list">
          <li><span class="legend-swatch swatch-none"></span> None — no data saved yet.</li>
          <li><span class="legend-swatch swatch-partial"></span> Partial — some fields filled.</li>
          <li><span class="legend-swatch swatch-complete"></span> Complete — all assigned fields filled.</li>
          <li><span class="legend-swatch swatch-skipped"></span> Skipped — one or more required fields were skipped.</li>
        </ul>
      </div>
    </div>

    <!-- Legend dialog (selection status) -->
    <div v-if="showStatusLegend" class="mini-overlay" @click.self="closeStatusLegend">
      <div class="mini-dialog" role="dialog" aria-modal="true">
        <div class="mini-head">
          <h4 class="mini-title">Selection Status</h4>
          <button class="mini-close" @click="closeStatusLegend" aria-label="Close">✕</button>
        </div>
        <ul class="mini-list legend-explain">
          <li><span class="legend-swatch swatch-none"></span> None — no data saved yet.</li>
          <li><span class="legend-swatch swatch-partial"></span> Partial — some fields filled.</li>
          <li><span class="legend-swatch swatch-complete"></span> Complete — all assigned fields filled.</li>
          <li><span class="legend-swatch swatch-skipped"></span> Skipped — one or more required fields were skipped.</li>
        </ul>
      </div>
    </div>

    <!-- Add Subjects dialog (moved to its own component) -->
    <AddSubjectsDialog
      v-if="showSubjectDialog"
      :subjectCount="subjectCountDraft"
      :assignmentMethod="assignmentMethodDraft"
      :subjects="subjectDrafts"
      :groupData="groupList"
      :saving="savingSubjects"
      :error="subjectDialogError"
      @update:subjectCount="onSubjectCountChange"
      @update:assignmentMethod="onAssignmentMethodChange"
      @update:subjects="onSubjectsUpdate"
      @close="closeSubjectDialog"
      @save="saveNewSubjects"
    />

    <CustomDialog :message="dialogMessage" :isVisible="showDialog" @close="closeDialog" />

    <!-- Skip required dialog -->
    <div v-if="showSkipDialog" class="dialog-overlay">
      <div class="dialog dialog-wide">
        <h3>Fix validation before saving</h3>
        <p>
          The fields below are required but empty. You can fill them now or choose to
          <em>Skip for now</em> to save the rest.
        </p>

        <div class="skip-list">
          <div class="skip-row" v-for="item in skipCandidates" :key="item.key">
            <div class="skip-left">
              <div class="skip-title">
                <strong>{{ item.sectionTitle }}</strong> / {{ item.fieldLabel }}
              </div>
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
          <button @click="confirmSkipSelection" class="btn-primary" :disabled="!canEdit">
            Skip selected & Save
          </button>
          <button @click="cancelSkipSelection" class="btn-option">
            Cancel
          </button>
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
import SelectionMatrixView from "@/components/SelectionMatrixView.vue";
import AddSubjectsDialog from "@/components/AddSubjectsDialog.vue";
import { createAjv, validateFieldValue } from "@/utils/jsonschemaValidation";

import MergeStudy from "@/components/MergeStudy.vue";

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
    SelectionMatrixView,
    AddSubjectsDialog,
    MergeStudy,
  },
  data() {
    return {
      study: null,
      showSelection: true,
      showDetails: false,

      // selection
      currentSubjectIndex: null,
      currentVisitIndex: null,
      currentGroupIndex: 0,

      // visit filter UI: -1 => All, else a single visit index
      selectedVisitIndex: -999,
      VISIT_THRESHOLD: 8,
      FLUID_VISIT_MAX: 6,

      // readiness flags
      matrixReady: false,

      // performance caches
      statusMap: new Map(),
      assignedLookup: [],
      subjectToGroupIdx: [],

      entryData: [],
      skipFlags: [],
      validationErrors: {},

      icons,
      showShareDialog: false,
      shareParams: { subjectIndex: null, visitIndex: null, groupIndex: null },
      shareConfig: { permission: "view", maxUses: 1, expiresInDays: 7 },
      generatedLink: "",
      copyStatus: "",
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
      showStatusLegend: false,

      // shared link
      shareToken: null,
      sharedPermission: "view",
      selectedVersion: null,
      studyVersions: [],
      templateCache: new Map(),

      entriesIndex: new Map(),
      hydrateCache: new Map(),
      visitLoading: false,

      // Add-subjects dialog state
      showSubjectDialog: false,
      subjectCountDraft: 1,
      assignmentMethodDraft: "Random",
      subjectDrafts: [],
      subjectDialogError: "",
      savingSubjects: false,

      // Merge mode (selection panel toggles to merge UI in same container)
      isMergeMode: false,
    };
  },

  computed: {
    canSeeGroupColumn() {
      if (!this.study?.metadata) return false;

      // creator
      const isCreator =
        this.study.metadata.created_by === this.$store.state.user?.id;

      // shared link with add permission
      const hasAddPermission =
        this.isShared && this.sharedPermission === "add";


      const isAdmin =
        this.$store.state.user?.role === "Administrator";

      return isCreator || hasAddPermission || isAdmin;
    },
    studyId() {
      const id = Number(this.$route.params.id);
      return Number.isFinite(id) ? id : null;
    },

    sd() {
      const sd =
        this.study && this.study.content && this.study.content.study_data;
      return (
        sd || {
          study: {},
          visits: [],
          groups: [],
          subjects: [],
          selectedModels: [],
          assignments: [],
        }
      );
    },
    studyInfoEntries() {
      const obj = (this.sd && this.sd.study) || {};
      try {
        return Object.entries(obj);
      } catch {
        return [];
      }
    },
    token() {
      return this.$store.state.token;
    },
    isShared() {
      return !!this.$route.params.token;
    },
    canEdit() {
      return !this.isShared || this.sharedPermission === "add";
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

    numberOfSubjects() {
      const sd = this.study?.content?.study_data;
      return sd?.subjectCount != null
        ? sd.subjectCount
        : sd?.subjects?.length || 0;
    },

    displayedVisitIndices() {
      if (!Array.isArray(this.visitList) || this.visitList.length === 0)
        return [];
      if (this.selectedVisitIndex === -1) {
        return this.visitList.map((_, i) => i);
      }
      const idx = Math.min(
        Math.max(this.selectedVisitIndex, 0),
        this.visitList.length - 1
      );
      return [idx];
    },

    isFluidMatrix() {
      return this.displayedVisitIndices.length <= this.FLUID_VISIT_MAX;
    },
    subjectColStyle() {
      if (!this.isFluidMatrix) return {};
      const pct = 28;
      return { width: pct + "%", maxWidth: "none", minWidth: "0" };
    },
    visitColStyle() {
      if (!this.isFluidMatrix) return {};
      const n = Math.max(this.displayedVisitIndices.length, 1);
      const pct = (72 / n).toFixed(4);
      return { width: pct + "%", maxWidth: "none", minWidth: "0" };
    },

    assignedModelIndices() {
      const v = Number.isInteger(this.currentVisitIndex)
        ? this.currentVisitIndex
        : 0;
      const g = Number.isInteger(this.currentGroupIndex)
        ? this.currentGroupIndex
        : 0;
      if (v == null || g == null) return [];
      return this.selectedModels
        .map((_, mIdx) => mIdx)
        .filter((mIdx) => !!this.assignments?.[mIdx]?.[v]?.[g]);
    },

    blockingErrorsPresent() {
      const keys = Object.keys(this.validationErrors || {});
      for (const k of keys) {
        const msg = this.validationErrors[k];
        if (!msg) continue;
        const idx = this.parseKey(k);
        if (!idx) continue;
        const { s, v, g, m, f } = idx;
        const isSkipped = !!(
          this.skipFlags[s]?.[v]?.[g]?.[m]?.[f]
        );
        if (isSkipped) continue;
        if (!/ is required\.$/.test(msg)) return true;
      }
      return false;
    },
  },

  async created() {
    this.ajv = createAjv();

    if (this.isShared) {
      const token = this.$route.params.token;
      await this.loadShared(token);
      this.matrixReady = true;
    } else {
      const studyId = this.$route.params.id;

      await this.loadStudy(studyId);
      await this.loadVersions(studyId);

      this.selectedVersion =
        this.studyVersions[this.studyVersions.length - 1]?.version || 1;

      await this.loadTemplateForSelectedVersion();

      this.selectedVisitIndex =
        this.visitList.length > this.VISIT_THRESHOLD ? 0 : -1;

      await this.loadExistingEntries(studyId);

      this.visitLoading = true;
      this.applyVersionView();
      this.prepareAssignmentsLookup();
      this.prepareSubjectGroupIndexMap();
      this.buildStatusCache();
      this.visitLoading = false;

      this.matrixReady = true;
    }
  },

  watch: {
    // Merge mode is controlled by query param: ?merge=1
    "$route.query.merge": {
      immediate: true,
      handler(val) {
        const next =
          val === "1" || val === 1 || val === true || val === "true";
        this.isMergeMode = next;
        if (next) this.showDetails = false; // keep header compact in merge view
      },
    },

    existingEntries: {
      handler() {
        if (this.selectedVisitIndex === -999) return;
        this.rebuildEntriesIndex();
        this.buildStatusCache();
      },
      deep: true,
    },
    study: {
      handler() {
        this.prepareAssignmentsLookup();
        this.prepareSubjectGroupIndexMap();
        if (this.selectedVisitIndex === -999) return;
        this.buildStatusCache();
      },
      deep: true,
    },
    async selectedVisitIndex(newVal) {
      if (newVal === -999) return;
      this.visitLoading = true;
      await this.$nextTick();
      this.applyVersionView();
      this.buildStatusCache();
      this.visitLoading = false;
    },
  },

  methods: {
    // --- Merge Study controls ---

    // --- Merge Study controls ---
    openMergeStudy() {
      if (this.isShared) return;
      const id = this.studyId || Number(this.$route.params.id);

      // Stay INSIDE dashboard layout and only toggle query
      this.$router.push({
        name: "DashboardAddData",
        params: { id },
        query: { ...this.$route.query, merge: "1" },
      });
    },

    closeMergeStudy() {
      const id = this.studyId || Number(this.$route.params.id);

      const q = { ...this.$route.query };
      delete q.merge;

      // Go back to the Add Data selection view (same screen with header)
      this.$router.push({
        name: "DashboardAddData",
        params: { id },
        query: q,
      });
    },


    safeVersionParams(v) {
      const n = Number(v);
      return Number.isFinite(n) && n >= 1 ? { version: n } : undefined;
    },

    mergeStudyDataFromTemplate(schema) {
      const prev =
        (this.study &&
          this.study.content &&
          this.study.content.study_data) ||
        {};
      const incoming = schema || {};

      const merged = {
        study: incoming.study ?? prev.study ?? {},
        subjects: Array.isArray(incoming.subjects)
          ? incoming.subjects
          : prev.subjects || [],
        groups: Array.isArray(incoming.groups)
          ? incoming.groups
          : prev.groups || [],
        visits: Array.isArray(incoming.visits)
          ? incoming.visits
          : prev.visits || [],
        selectedModels: Array.isArray(incoming.selectedModels)
          ? incoming.selectedModels
          : prev.selectedModels || [],
        assignments: Array.isArray(incoming.assignments)
          ? incoming.assignments
          : prev.assignments || [],
      };

      const content = this.study && this.study.content
        ? this.study.content
        : {};
      this.study = {
        ...this.study,
        content: {
          ...content,
          study_data: merged,
        },
      };
    },

    async loadVersions(studyId) {
      try {
        const resp = await axios.get(
          `/forms/studies/${studyId}/versions`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
          }
        );
        this.studyVersions = Array.isArray(resp.data)
          ? resp.data
          : [];
        this.studyVersions.sort((a, b) => a.version - b.version);
      } catch (e) {
        console.error("[Entry] loadVersions error", e);
        this.studyVersions = [{ version: 1, created_at: null }];
      }
    },

    applyTemplateSchema(schema) {
      const current =
        (this.study &&
          this.study.content &&
          this.study.content.study_data) ||
        {};

      const normalized = {
        study: schema?.study ?? current.study ?? {},
        subjects:
          Array.isArray(schema?.subjects) && schema.subjects.length
            ? schema.subjects
            : current.subjects || [],
        subjectCount: Number.isFinite(schema?.subjectCount)
          ? schema.subjectCount
          : current.subjectCount ??
            (current.subjects?.length || 0),
        visits:
          Array.isArray(schema?.visits) && schema.visits.length
            ? schema.visits
            : current.visits || [],
        groups:
          Array.isArray(schema?.groups) && schema.groups.length
            ? schema.groups
            : current.groups || [],
        selectedModels: Array.isArray(schema?.selectedModels)
          ? schema.selectedModels
          : current.selectedModels || [],
        assignments: Array.isArray(schema?.assignments)
          ? schema.assignments
          : current.assignments || [],
      };

      if (!this.study)
        this.study = { metadata: {}, content: { study_data: normalized } };
      else if (!this.study.content)
        this.study.content = { study_data: normalized };
      else this.study.content.study_data = normalized;

      this.initializeEntryData();
      this.prepareSubjectGroupIndexMap();
      this.prepareAssignmentsLookup();
      this.buildStatusCache();
    },

    async loadTemplateForSelectedVersion() {
      const studyId = this.study?.metadata?.id;
      if (!studyId || !this.selectedVersion) return;

      if (this.templateCache.has(this.selectedVersion)) {
        const cached = this.templateCache.get(this.selectedVersion);
        this.applyTemplateSchema(cached);
        return;
      }

      try {
        const resp = await axios.get(
          `/forms/studies/${studyId}/template`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
            params: { version: this.selectedVersion },
          }
        );
        const rawSchema = resp?.data?.schema || {};
        this.templateCache.set(this.selectedVersion, rawSchema);
        this.applyTemplateSchema(rawSchema);
      } catch (e) {
        console.error(
          "[Entry] loadTemplateForSelectedVersion error",
          e
        );
      }
    },

    onVersionChange() {
      this.hydrateCache.clear();
      this.loadTemplateForSelectedVersion().then(() => {
        this.applyVersionView();
        const nS = this.numberOfSubjects;
        const nV = this.visitList.length;
        if (
          this.currentSubjectIndex == null ||
          this.currentSubjectIndex >= nS
        )
          this.currentSubjectIndex = Math.min(0, nS - 1);
        if (
          this.currentVisitIndex == null ||
          this.currentVisitIndex >= nV
        )
          this.currentVisitIndex = Math.min(0, nV - 1);
        this.selectedVisitIndex =
          this.visitList.length > this.VISIT_THRESHOLD ? 0 : -1;
      });
    },

    rebuildEntriesIndex() {
      const m = new Map();
      for (const e of this.existingEntries || []) {
        const key = `${e.subject_index}|${e.visit_index}|${e.group_index}`;
        const arr = m.get(key) || [];
        arr.push(e);
        m.set(key, arr);
      }
      for (const [k, arr] of m) {
        arr.sort(
          (a, b) => Number(b.form_version) - Number(a.form_version)
        );
      }
      this.entriesIndex = m;
      this.hydrateCache.clear();
    },

    getBestEntryFor(s, v, g) {
      const key = `${s}|${v}|${g}`;
      const arr = this.entriesIndex.get(key);
      if (!arr || !arr.length) return null;

      const target = Number(this.selectedVersion);
      for (const e of arr) {
        if (Number(e.form_version) === target) return e;
      }
      for (const e of arr) {
        if (Number(e.form_version) <= target) return e;
      }
      return arr[0];
    },

    applyVersionView() {
      if (this.showSelection) return;

      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;
      const vIndices =
        this.selectedVisitIndex === -1
          ? Array.from({ length: nV }, (_, i) => i)
          : [
              Math.min(
                Math.max(this.selectedVisitIndex, 0),
                Math.max(nV - 1, 0)
              ),
            ];

      for (let s = 0; s < nS; s++) {
        const g = this.subjectToGroupIdx[s] ?? 0;
        for (const v of vIndices) this.hydrateCell(s, v, g);
      }
    },

    sectionDictKey(sectionObj) {
      return sectionObj?.title ?? "";
    },
    fieldDictKey(fieldObj, fallbackIndex) {
      return (
        fieldObj?.name ||
        fieldObj?.label ||
        fieldObj?.key ||
        fieldObj?.title ||
        `f${fallbackIndex}`
      );
    },
    arrayToDict(sectionFieldArray) {
      const out = {};
      (this.selectedModels || []).forEach((sec, sIdx) => {
        const sKey = this.sectionDictKey(sec);
        const fields = sec?.fields || [];
        const row = Array.isArray(sectionFieldArray?.[sIdx])
          ? sectionFieldArray[sIdx]
          : [];
        const inner = {};
        fields.forEach((f, fIdx) => {
          const fKey = this.fieldDictKey(f, fIdx);
          inner[fKey] =
            row[fIdx] != null ? row[fIdx] : this.defaultForField(f);
        });
        out[sKey] = inner;
      });
      return out;
    },
    flagsArrayToDict(flagsArr) {
      const out = {};
      (this.selectedModels || []).forEach((sec, sIdx) => {
        const sKey = this.sectionDictKey(sec);
        const row = Array.isArray(flagsArr?.[sIdx])
          ? flagsArr[sIdx]
          : [];
        const inner = {};
        (sec.fields || []).forEach((f, fIdx) => {
          const fKey = this.fieldDictKey(f, fIdx);
          inner[fKey] = !!row[fIdx];
        });
        out[sKey] = inner;
      });
      return out;
    },

    dictToArray(dataDict) {
      return (this.selectedModels || []).map((sec, sIdx) => {
        const sKey = this.sectionDictKey(sec);
        const inner =
          dataDict && typeof dataDict === "object"
            ? dataDict[sKey]
            : undefined;
        return (sec.fields || []).map((f, fIdx) => {
          const fKey = this.fieldDictKey(f, fIdx);
          const v = inner ? inner[fKey] : undefined;
          return v !== undefined ? v : this.defaultForField(f);
        });
      });
    },

    makeSectionFieldSkeleton() {
      return (this.selectedModels || []).map((sec) =>
        (sec.fields || []).map((f) => this.defaultForField(f))
      );
    },
    makeSkipSkeleton() {
      return (this.selectedModels || []).map((sec) =>
        (sec.fields || []).map(() => false)
      );
    },
    ensureSlot(s, v, g) {
      if (!this.entryData[s]) this.entryData[s] = [];
      if (!this.entryData[s][v]) this.entryData[s][v] = [];
      if (!this.entryData[s][v][g])
        this.entryData[s][v][g] = this.makeSectionFieldSkeleton();

      if (!this.skipFlags[s]) this.skipFlags[s] = [];
      if (!this.skipFlags[s][v]) this.skipFlags[s][v] = [];
      if (!this.skipFlags[s][v][g])
        this.skipFlags[s][v][g] = this.makeSkipSkeleton();

      if (!this.entryIds[s]) this.entryIds[s] = [];
      if (!this.entryIds[s][v]) this.entryIds[s][v] = [];
      if (typeof this.entryIds[s][v][g] === "undefined")
        this.entryIds[s][v][g] = null;
    },

    hydrateCell(s, v, g) {
      const cacheKey = `${s}|${v}|${g}|${this.selectedVersion}`;
      const cached = this.hydrateCache.get(cacheKey);
      if (cached) {
        this.entryData[s] ??= [];
        this.entryData[s][v] ??= [];
        this.entryData[s][v][g] = cached.dataArr;
        this.entryIds[s] ??= [];
        this.entryIds[s][v] ??= [];
        this.entryIds[s][v][g] = cached.id;
        this.skipFlags[s] ??= [];
        this.skipFlags[s][v] ??= [];
        this.skipFlags[s][v][g] = cached.skipFlags;
        return;
      }

      const best = this.getBestEntryFor(s, v, g);
      this.ensureSlot(s, v, g);
      if (!best) {
        this.hydrateCache.set(cacheKey, {
          dataArr: this.entryData[s][v][g],
          skipFlags: this.skipFlags[s][v][g],
          id: null,
        });
        return;
      }

      let arr;
      if (best.data && !Array.isArray(best.data) && typeof best.data === "object") {
        arr = this.dictToArray(best.data);
      } else {
        arr = Array.isArray(best.data)
          ? best.data
          : this.selectedModels.map((sec) =>
              sec.fields.map((f) => this.defaultForField(f))
            );
      }

      arr = (this.selectedModels || []).map((sec, sIdx) => {
        const row = Array.isArray(arr[sIdx]) ? arr[sIdx] : [];
        return (sec.fields || []).map((f, fIdx) =>
          row[fIdx] !== undefined ? row[fIdx] : this.defaultForField(f)
        );
      });

      this.entryData[s][v][g] = arr;
      this.entryIds[s][v][g] = best.id;

      const storedSkips = best.skipped_required_flags || best.skips;
      this.skipFlags[s][v][g] = Array.isArray(storedSkips)
        ? storedSkips
        : this.makeSkipSkeleton();

      this.hydrateCache.set(cacheKey, {
        dataArr: this.entryData[s][v][g],
        skipFlags: this.skipFlags[s][v][g],
        id: best.id,
      });
    },

    setDeepValue(s, v, g, m, f, val) {
      this.ensureSlot(s, v, g);
      if (!Array.isArray(this.entryData[s][v][g][m])) {
        const fields = this.selectedModels[m]?.fields || [];
        this.entryData[s][v][g][m] = fields.map((ff) =>
          this.defaultForField(ff)
        );
      }
      this.entryData[s][v][g][m][f] = val;
    },
    setDeepSkip(s, v, g, m, f, on) {
      this.ensureSlot(s, v, g);
      if (!Array.isArray(this.skipFlags[s][v][g][m])) {
        const fields = this.selectedModels[m]?.fields || [];
        this.skipFlags[s][v][g][m] = fields.map(() => false);
      }
      this.skipFlags[s][v][g][m][f] = !!on;
    },

    setEntryValue(mIdx, fIdx, val) {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.setDeepValue(s, v, g, mIdx, fIdx, val);
      this.clearError(mIdx, fIdx);
      this.validateField(mIdx, fIdx);
      this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
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
    parseKey(k) {
      const parts = String(k)
        .split("-")
        .map((x) => parseInt(x, 10));
      if (parts.length !== 5 || parts.some((n) => Number.isNaN(n)))
        return null;
      const [s, v, g, m, f] = parts;
      return { s, v, g, m, f };
    },

    onRawFileSelected(mIdx, fIdx, fileOrFiles) {
      const key = this.errorKey(mIdx, fIdx);
      const arr = Array.isArray(fileOrFiles)
        ? fileOrFiles
        : fileOrFiles
        ? [fileOrFiles]
        : [];
      const cur = Array.isArray(this.pendingFiles[key])
        ? this.pendingFiles[key]
        : this.pendingFiles[key]
        ? [this.pendingFiles[key]]
        : [];
      this.pendingFiles = { ...this.pendingFiles, [key]: [...cur, ...arr] };
    },

    getSliderProps(field) {
      const c = field?.constraints || {};
      const min = c.percent ? 1 : Number.isFinite(+c.min) ? +c.min : 1;
      const max = c.percent
        ? 100
        : Number.isFinite(+c.max)
        ? +c.max
        : c.percent
        ? 100
        : 5;
      const step =
        Number.isFinite(+c.step) && +c.step > 0 ? +c.step : 1;
      const marks = Array.isArray(c.marks) ? c.marks : [];
      return {
        min,
        max,
        step,
        readonly: !!c.readonly || !this.canEdit,
        percent: !!c.percent,
        showTicks: !!c.showTicks,
        marks,
      };
    },
    getLinearProps(field) {
      const c = field?.constraints || {};
      const min = Number.isFinite(+c.min) ? Math.round(+c.min) : 1;
      let max = Number.isFinite(+c.max) ? Math.round(+c.max) : 5;
      if (max <= min) max = min + 1;
      return {
        min,
        max,
        leftLabel: c.leftLabel || "",
        rightLabel: c.rightLabel || "",
        readonly: !!c.readonly || !this.canEdit,
      };
    },

    openLegendDialog() {
      this.showLegendDialog = true;
    },
    closeLegendDialog() {
      this.showLegendDialog = false;
    },

    openStatusLegend() {
      this.showStatusLegend = true;
    },
    closeStatusLegend() {
      this.showStatusLegend = false;
    },

    hasConstraints(field) {
      const c = field?.constraints || {};
      return Object.keys(c).some(
        (k) => k !== "required" && k !== "helpText"
      );
    },
    buildConstraintList(field) {
      const c = field?.constraints || {};
      const parts = [];
      if (c.readonly || !this.canEdit) parts.push("Read-only");
      if (field.type === "slider") {
        const mode = (c.mode || "slider").toLowerCase();
        if (mode === "slider") {
          parts.push(`Slider ${c.percent ? "(1–100%)" : ""}`);
          if (Number.isFinite(c.min)) parts.push(`Min: ${c.min}`);
          if (Number.isFinite(c.max)) parts.push(`Max: ${c.max}`);
          if (Number.isFinite(c.step)) parts.push(`Step: ${c.step}`);
          if (c.showTicks) parts.push("Show tick marks");
          if (Array.isArray(c.marks) && c.marks.length) {
            parts.push(
              `Labels: ${c.marks
                .map((m) => `${m.value}="${m.label}"`)
                .join(", ")}`
            );
          }
        } else {
          parts.push("Linear scale");
          parts.push(
            `Range: ${c.min ?? 1}–${c.max ?? 5} (integers)`
          );
          if (c.leftLabel) parts.push(`Left: “${c.leftLabel}”`);
          if (c.rightLabel) parts.push(`Right: “${c.rightLabel}”`);
        }
        return parts.length ? parts : ["No constraints."];
      }
      if (field.type === "text" || field.type === "textarea") {
        if (typeof c.minLength === "number")
          parts.push(`Min length: ${c.minLength}`);
        if (typeof c.maxLength === "number")
          parts.push(`Max length: ${c.maxLength}`);
        if (c.pattern) parts.push(`Pattern: ${c.pattern}`);
        if (c.transform && c.transform !== "none") {
          const t =
            c.transform.charAt(0).toUpperCase() +
            c.transform.slice(1).toLowerCase();
          parts.push(`Transform on save: ${t}`);
        }
      }
      if (field.type === "number") {
        if (typeof c.min === "number") parts.push(`Min: ${c.min}`);
        if (typeof c.max === "number") parts.push(`Max: ${c.max}`);
        if (typeof c.step === "number")
          parts.push(`Step: ${c.step}`);
        if (typeof c.minDigits === "number")
          parts.push(`Min digits: ${c.minDigits}`);
        if (typeof c.maxDigits === "number")
          parts.push(`Max digits: ${c.maxDigits}`);
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
        if (typeof c.step === "number")
          parts.push(`Step (sec): ${c.step}`);
      }
      if (field.type === "select" && c.allowMultiple)
        parts.push("Multiple selection: allowed");
      if (field.type === "file") {
        const storage =
          c.storagePreference === "url"
            ? "Link via URL"
            : "Local upload";
        parts.push(`Storage: ${storage}`);
        const allowedList = Array.isArray(c.allowedFormats)
          ? c.allowedFormats.filter(Boolean).map(String)
          : [];
        if (allowedList.length)
          parts.push(`Allowed: ${allowedList.join(", ")}`);
        const sizeNum = Number(c.maxSizeMB);
        if (Number.isFinite(sizeNum) && sizeNum > 0)
          parts.push(`Max size: ${sizeNum} MB`);
        if (c.allowMultipleFiles)
          parts.push("Multiple files: allowed");
        if (Array.isArray(c.modalities) && c.modalities.length)
          parts.push(`Modalities: ${c.modalities.join(", ")}`);
      }
      return parts.length ? parts : ["No constraints."];
    },
    openConstraintDialog(field) {
      this.constraintDialogFieldName =
        field?.label || field?.name || "Field";
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
        case "uppercase":
          return v.toUpperCase();
        case "lowercase":
          return v.toLowerCase();
        case "capitalize":
          return v.replace(/\b\w+/g, (w) =>
            w.charAt(0).toUpperCase() +
            w.slice(1).toLowerCase()
          );
        default:
          return v;
      }
    },
    onFieldBlur(mIdx, fIdx) {
      const def =
        this.selectedModels[mIdx].fields[fIdx] || {};
      const cons = def.constraints || {};
      if (def.type === "text" || def.type === "textarea") {
        const cur =
          this.entryData[this.currentSubjectIndex][
            this.currentVisitIndex
          ][this.currentGroupIndex][mIdx][fIdx];
        const transformed = this.applyTransform(cons.transform, cur);
        if (transformed !== cur) {
          this.setDeepValue(
            this.currentSubjectIndex,
            this.currentVisitIndex,
            this.currentGroupIndex,
            mIdx,
            fIdx,
            transformed
          );
        }
      }
      this.validateField(mIdx, fIdx);
    },
    applyTransformsForSection() {
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach(
          (def, fIdx) => {
            if (!def) return;
            const cons = def.constraints || {};
            if (
              def.type === "text" ||
              def.type === "textarea"
            ) {
              const cur =
                this.entryData[this.currentSubjectIndex][
                  this.currentVisitIndex
                ][this.currentGroupIndex][mIdx][fIdx];
              const t = this.applyTransform(cons.transform, cur);
              if (t !== cur)
                this.setDeepValue(
                  this.currentSubjectIndex,
                  this.currentVisitIndex,
                  this.currentGroupIndex,
                  mIdx,
                  fIdx,
                  t
                );
            }
          }
        );
      });
    },

    setError(mIdx, fIdx, msg) {
      const k = this.errorKey(mIdx, fIdx);
      this.validationErrors = {
        ...this.validationErrors,
        [k]: msg,
      };
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
      this.$router.push({
        name: "Dashboard",
        query: { openStudies: "true" },
      });
    },

    async loadStudy(studyId) {
      try {
        const resp = await axios.get(
          `/forms/studies/${studyId}`,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        this.study = resp.data;
        this.initializeEntryData();
      } catch (err) {
        console.error("[Entry] loadStudy error", err);
        this.showDialogMessage("Failed to load study details.");
      }
    },

    async loadShared(token) {
      try {
        const resp = await axios.get(
          `/forms/shared-api/${token}/`
        );
        const payload = resp.data || {};
        this.shareToken = token;
        this.sharedPermission = payload.permission || "view";
        this.study = payload.study;
        this.initializeEntryData();
        this.prepareAssignmentsLookup();
        this.prepareSubjectGroupIndexMap();

        this.currentSubjectIndex = payload.subject_index ?? 0;
        this.currentVisitIndex = payload.visit_index ?? 0;
        this.currentGroupIndex = payload.group_index ?? 0;
        this.ensureSlot(
          this.currentSubjectIndex,
          this.currentVisitIndex,
          this.currentGroupIndex
        );
        this.showSelection = false;
        this.validationErrors = {};
      } catch (e) {
        console.error("[Shared] load error", e);
        this.showDialogMessage(
          "Shared link is invalid or expired."
        );
      }
    },

    async loadExistingEntries(studyId) {
      try {
        const resp = await axios.get(
          `/forms/studies/${studyId}/data_entries`,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        const payload = Array.isArray(resp.data)
          ? resp.data
          : resp.data?.entries || [];
        this.existingEntries = payload;
        this.rebuildEntriesIndex();
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
      if (
        !ignoreDefaults &&
        Object.prototype.hasOwnProperty.call(
          c,
          "defaultValue"
        )
      )
        return c.defaultValue;
      if (
        !ignoreDefaults &&
        Object.prototype.hasOwnProperty.call(f, "value")
      )
        return f.value;
      switch (t) {
        case "checkbox":
          return false;
        case "radio":
        case "select":
          return allowMulti ? [] : "";
        case "number":
          return "";
        case "date":
        case "time":
        case "text":
        case "textarea":
        default:
          return "";
      }
    },

    clearCurrentSection() {
      if (!this.canEdit) return;
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.ensureSlot(s, v, g);
      this.assignedModelIndices.forEach((mIdx) => {
        const section = this.selectedModels[mIdx];
        section.fields.forEach((f, fIdx) => {
          const cons = f?.constraints || {};
          if (cons.readonly) {
            this.clearError(mIdx, fIdx);
            return;
          }
          const next = this.defaultForField(f, {
            ignoreDefaults: false,
          });
          this.setDeepValue(s, v, g, mIdx, fIdx, next);
          this.setDeepSkip(s, v, g, mIdx, fIdx, false);
          this.clearError(mIdx, fIdx);
        });
      });
      this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
    },

    initializeEntryData() {
      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;
      const nG = this.groupList.length;

      this.entryData = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () =>
          Array.from({ length: nG }, () => null)
        )
      );

      this.skipFlags = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () =>
          Array.from({ length: nG }, () => null)
        )
      );

      this.entryIds = Array.from({ length: nS }, () =>
        Array.from({ length: nV }, () =>
          Array.from({ length: nG }, () => null)
        )
      );

      this.validationErrors = {};
    },

    prepareAssignmentsLookup() {
      const nV = this.visitList.length;
      const nG = this.groupList.length;
      this.assignedLookup = Array.from({ length: nV }, (_, v) =>
        Array.from({ length: nG }, (_, g) =>
          this.selectedModels
            .map((_, mIdx) => mIdx)
            .filter(
              (mIdx) => !!this.assignments[mIdx]?.[v]?.[g]
            )
        )
      );
    },
    prepareSubjectGroupIndexMap() {
      const subjects =
        this.study?.content?.study_data?.subjects || [];
      this.subjectToGroupIdx = subjects.map((s) => {
        const name = (s.group || "").trim().toLowerCase();
        const gi = this.groupList.findIndex(
          (g) => (g.name || "").trim().toLowerCase() === name
        );
        return gi >= 0 ? gi : 0;
      });
    },

    async copyGeneratedLink() {
      const text = String(this.generatedLink || "");
      if (!text) return;

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
        } else {
          const ta = document.createElement("textarea");
          ta.value = text;
          ta.setAttribute("readonly", "");
          ta.style.position = "fixed";
          ta.style.top = "-9999px";
          ta.style.left = "-9999px";
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          ta.setSelectionRange(0, ta.value.length);
          const ok = document.execCommand("copy");
          document.body.removeChild(ta);
          if (!ok) throw new Error("execCommand(copy) failed");
        }

        this.copyStatus = "Copied!";
        setTimeout(() => {
          this.copyStatus = "";
        }, 1800);
      } catch (e) {
        console.error("Copy failed:", e);
        this.copyStatus = "Copy failed.";
        setTimeout(() => {
          this.copyStatus = "";
        }, 2200);
      }
    },

    buildStatusCache() {
      this.statusMap = new Map();
      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;

      const vIndices =
        this.selectedVisitIndex === -1
          ? Array.from({ length: nV }, (_, i) => i)
          : [
              Math.min(
                Math.max(this.selectedVisitIndex, 0),
                Math.max(nV - 1, 0)
              ),
            ];

      for (let s = 0; s < nS; s++) {
        const g = this.subjectToGroupIdx[s] ?? 0;
        for (const v of vIndices) {
          const e = this.getBestEntryFor(s, v, g);
          const key = `${s}|${v}`;

          if (!e) {
            this.statusMap.set(key, "none");
            continue;
          }

          const flags = e.skipped_required_flags;
          const hasSkip = !!(
            Array.isArray(flags) &&
            flags.some(
              (row) =>
                Array.isArray(row) && row.some((x) => !!x)
            )
          );
          if (hasSkip) {
            this.statusMap.set(key, "skipped");
            continue;
          }

          const assigned = this.assignedLookup?.[v]?.[g] || [];
          let total = 0;
          let filled = 0;

          if (e.data && !Array.isArray(e.data) && typeof e.data === "object") {
            for (const mIdx of assigned) {
              const sec = this.selectedModels[mIdx] || {};
              const sKey = this.sectionDictKey(sec);
              const secObj = e.data[sKey] || {};
              (sec.fields || []).forEach((f, fIdx) => {
                const fKey = this.fieldDictKey(f, fIdx);
                const val = secObj[fKey];
                total += 1;
                if (val != null && val !== "") filled += 1;
              });
            }
          } else if (Array.isArray(e.data)) {
            for (const mIdx of assigned) {
              const row = e.data[mIdx] || [];
              total += row.length;
              filled += row.filter(
                (vv) => vv != null && vv !== ""
              ).length;
            }
          }

          if (total === 0 || filled === 0)
            this.statusMap.set(key, "none");
          else if (filled === total)
            this.statusMap.set(key, "complete");
          else this.statusMap.set(key, "partial");
        }
      }
    },

    statusClassFast(sIdx, vIdx) {
      const s = this.statusMap.get(`${sIdx}|${vIdx}`) || "none";
      return s === "skipped" ? "status-skipped" : `status-${s}`;
    },

    selectCell(sIdx, vIdx) {
      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;

      this.currentSubjectIndex = Math.min(
        Math.max(sIdx ?? 0, 0),
        Math.max(nS - 1, 0)
      );
      this.currentVisitIndex = Math.min(
        Math.max(vIdx ?? 0, 0),
        Math.max(nV - 1, 0)
      );
      this.currentGroupIndex =
        this.subjectToGroupIdx[this.currentSubjectIndex] ?? 0;

      this.ensureSlot(
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex
      );
      this.prepareAssignmentsLookup();

      this.showSelection = false;
      this.validationErrors = {};

      this.visitLoading = true;
      this.hydrateCell(
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex
      );
      this.visitLoading = false;
    },

    backToSelection() {
      if (this.isShared) return;
      this.showSelection = true;
      this.showDetails = false;
      this.currentSubjectIndex = null;
      this.currentVisitIndex = null;
      this.currentGroupIndex = 0;
      this.validationErrors = {};
    },
    toggleDetails() {
      this.showDetails = !this.showDetails;
    },

    fieldId(mIdx, fIdx) {
      return `s${this.currentSubjectIndex}_v${this.currentVisitIndex}_g${this.currentGroupIndex}_m${mIdx}_f${fIdx}`;
    },

    isFieldSkipped(mIdx, fIdx) {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      return !!(
        this.skipFlags[s]?.[v]?.[g]?.[mIdx]?.[fIdx]
      );
    },
    setSkipForField(mIdx, fIdx, on) {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      if (
        !this.skipFlags[s] ||
        !this.skipFlags[s][v] ||
        !this.skipFlags[s][v][g]
      )
        return;
      this.setDeepSkip(s, v, g, mIdx, fIdx, on);
    },

    validateField(mIdx, fIdx) {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.ensureSlot(s, v, g);

      const def =
        this.selectedModels[mIdx].fields[fIdx] || {};
      const cons = def.constraints || {};
      const label = def.label || def.name || "This field";
      const val = this.entryData[s][v][g][mIdx][fIdx];
      const allowMultiFiles = !!cons.allowMultipleFiles;
      let isSkipped = !!(
        this.skipFlags[s]?.[v]?.[g]?.[mIdx]?.[fIdx]
      );

      const isEmpty = () => {
        if (def.type === "checkbox") return val !== true;
        if (def.type === "file") {
          if (allowMultiFiles) {
            const arr = Array.isArray(val) ? val : [];
            return arr.length === 0;
          } else {
            if (!val) return true;
            const src =
              val.source ||
              (val.file && val.file.source) ||
              "local";
            if (src === "url") {
              const url = (val.url || "").trim();
              return !url;
            }
            if (src === "local") {
              const meta =
                val.file && typeof val.file === "object"
                  ? val.file
                  : val;
              const sizeNum = Number(meta.size);
              return (
                !meta.name ||
                !Number.isFinite(sizeNum) ||
                sizeNum <= 0
              );
            }
            return true;
          }
        }
        if (Array.isArray(val)) return val.length === 0;
        return (
          val == null ||
          (typeof val === "string" && val.trim() === "")
        );
      };

      this.clearError(mIdx, fIdx);

      if (isSkipped) {
        if (isEmpty()) return true;
        this.setSkipForField(mIdx, fIdx, false);
        isSkipped = false;
      }

      if (cons.required && isEmpty()) {
        this.setError(mIdx, fIdx, `${label} is required.`);
        return false;
      }

      if (def.type === "slider") {
        if (val == null || val === "") return true;
        const mode = (cons.mode || "slider").toLowerCase();
        const n = Number(val);
        if (!Number.isFinite(n)) {
          this.setError(
            mIdx,
            fIdx,
            `${label} must be a number.`
          );
          return false;
        }
        if (mode === "slider") {
          const min = cons.percent ? 1 : (Number.isFinite(+cons.min) ? +cons.min : 1);
          const max = cons.percent ? 100 : (Number.isFinite(+cons.max) ? +cons.max : (cons.percent ? 100 : 5));
          const step = Number.isFinite(+cons.step) && +cons.step > 0 ? +cons.step : 1;
          if (n < min || n > max) { this.setError(mIdx, fIdx, `${label} must be between ${min} and ${max}.`); return false; }
          if (step >= 1) {
            const k = (n - min) / step;
            if (Math.abs(k - Math.round(k)) > 1e-9) {
              this.setError(
                mIdx,
                fIdx,
                `${label} must align to step ${step}.`
              );
              return false;
            }
          }
          return true;
        } else {
          const min = Number.isFinite(+cons.min)
            ? Math.round(+cons.min)
            : 1;
          const max = Number.isFinite(+cons.max)
            ? Math.round(+cons.max)
            : 5;
          if (
            n < min ||
            n > max ||
            Math.round(n) !== n
          ) {
            this.setError(
              mIdx,
              fIdx,
              `${label} must be an integer between ${min} and ${max}.`
            );
            return false;
          }
          return true;
        }
      }

      if (def.type !== "file") {
        const { valid, message } = validateFieldValue(
          this.ajv,
          def,
          val
        );
        if (!valid) {
          this.setError(
            mIdx,
            fIdx,
            message || `${label} is invalid.`
          );
          return false;
        }
      }

      if (def.type === "date" && val) {
        const cons =
          (this.selectedModels[mIdx].fields[fIdx] || {})
            .constraints || {};
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
            yyyy: /^(\d{4})$/,
          };
          const rx = map[fmt] || map[fmt.replace(".", "\\.")];
          if (!rx) return null;
          const m = rx.exec(String(s));
          if (!m) return null;
          let y, M, d;
          if (fmt === "dd.MM.yyyy") {
            d = +m[1];
            M = +m[2];
            y = +m[3];
          } else if (fmt === "MM-dd-yyyy") {
            M = +m[1];
            d = +m[2];
            y = +m[3];
          } else if (fmt === "dd-MM-yyyy") {
            d = +m[1];
            M = +m[2];
            y = +m[3];
          } else if (fmt === "yyyy-MM-dd") {
            y = +m[1];
            M = +m[2];
            d = +m[3];
          } else if (fmt === "MM/yyyy" || fmt === "MM-yyyy") {
            M = +m[1];
            y = +m[2];
            d = 1;
          } else if (fmt === "yyyy/MM" || fmt === "yyyy-MM") {
            y = +m[1];
            M = +m[2];
            d = 1;
          } else if (fmt === "yyyy") {
            y = +m[1];
            M = 1;
            d = 1;
          }
          return new Date(y, M - 1, d);
        };
        const d = parse(val);
        if (d) {
          if (cons.minDate) {
            const md = parse(cons.minDate);
            if (md && d < md) {
              this.setError(
                mIdx,
                fIdx,
                `${def.label || def.name || "This field"} must be ≥ ${cons.minDate}.`
              );
              return false;
            }
          }
          if (cons.maxDate) {
            const xd = parse(cons.maxDate);
            if (xd && d > xd) {
              this.setError(
                mIdx,
                fIdx,
                `${def.label || def.name || "This field"} must be ≤ ${cons.maxDate}.`
              );
              return false;
            }
          }
        }
      }

      if (def.type === "time" && val) {
        const cons =
          (this.selectedModels[mIdx].fields[fIdx] || {})
            .constraints || {};
        const toSec = (s) => {
          const mm =
            /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(String(s));
          if (!mm) return null;
          const h = +mm[1],
            mi = +mm[2],
            se = mm[3] ? +mm[3] : 0;
          return h * 3600 + mi * 60 + se;
        };
        const secs = toSec(val);
        if (secs != null) {
          if (cons.minTime) {
            const m = toSec(cons.minTime);
            if (m != null && secs < m) {
              this.setError(
                mIdx,
                fIdx,
                `${def.label || def.name || "This field"} must be ≥ ${cons.minTime}.`
              );
              return false;
            }
          }
          if (cons.maxTime) {
            const x = toSec(cons.maxTime);
            if (x != null && secs > x) {
              this.setError(
                mIdx,
                fIdx,
                `${def.label || def.name || "This field"} must be ≤ ${cons.maxTime}.`
              );
              return false;
            }
          }
        }
      }
      return true;
    },

    validateCurrentSection() {
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach(
          (_, fIdx) => {
            this.clearError(mIdx, fIdx);
          }
        );
      });

      let ok = true;
      this.assignedModelIndices.forEach((mIdx) => {
        this.selectedModels[mIdx].fields.forEach(
          (_, fIdx) => {
            const r = this.validateField(mIdx, fIdx);
            ok = ok && r;
          }
        );
      });
      return ok;
    },

    computeRequiredFailures() {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.ensureSlot(s, v, g);
      const items = [];
      this.assignedModelIndices.forEach((mIdx) => {
        const section = this.selectedModels[mIdx];
        (section.fields || []).forEach((f, fIdx) => {
          const c = f?.constraints || {};
          if (!c.required) return;
          if (this.skipFlags[s]?.[v]?.[g]?.[mIdx]?.[fIdx])
            return;
          const val = this.entryData[s][v][g][mIdx][fIdx];
          const empty =
            f.type === "checkbox"
              ? val !== true
              : f.type === "file"
              ? c.allowMultipleFiles
                ? !(
                    Array.isArray(val) &&
                    val.length > 0
                  )
                : !val ||
                  (val.source === "url"
                    ? !(
                        val.url &&
                        String(val.url).trim()
                      )
                    : !(
                        val.name &&
                        Number.isFinite(
                          Number(val.size)
                        )
                      ))
              : Array.isArray(val)
              ? val.length === 0
              : val == null ||
                (typeof val === "string" &&
                  val.trim() === "");
          if (empty) {
            items.push({
              key: this.errorKey(mIdx, fIdx),
              id: this.fieldId(mIdx, fIdx),
              sectionIndex: mIdx,
              fieldIndex: fIdx,
              sectionTitle:
                section.title || `Section ${mIdx + 1}`,
              fieldLabel:
                f.label ||
                f.name ||
                `Field ${fIdx + 1}`,
            });
          }
        });
      });
      return items;
    },

    async uploadPendingFilesForCurrentSection() {
      if (!this.canEdit) return;
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      const studyId = this.study?.metadata?.id;

      for (const mIdx of this.assignedModelIndices) {
        const section = this.selectedModels[mIdx];
        for (
          let fIdx = 0;
          fIdx < (section.fields || []).length;
          fIdx++
        ) {
          const def = section.fields[fIdx] || {};
          if (def.type !== "file") continue;

          const key = this.errorKey(mIdx, fIdx);
          const cons = def.constraints || {};
          const allowMulti = !!cons.allowMultipleFiles;
          const val = this.entryData[s][v][g][mIdx][fIdx];
          if (!val && !allowMulti) continue;

          const modalities = Array.isArray(
            def?.constraints?.modalities
          )
            ? def.constraints.modalities
            : [];
          const modalitiesJson = JSON.stringify(
            modalities || []
          );

          const pendingArr = Array.isArray(
            this.pendingFiles[key]
          )
            ? this.pendingFiles[key]
            : this.pendingFiles[key]
            ? [this.pendingFiles[key]]
            : [];
          const matchFile = (meta) =>
            pendingArr.find(
              (f) =>
                f &&
                meta &&
                f.name === meta.name &&
                Number(f.size) === Number(meta.size) &&
                (f.lastModified
                  ? f.lastModified === meta.lastModified
                  : true)
            );

          const base = this.isShared
            ? `/forms/shared/${this.shareToken}`
            : `/forms/studies/${studyId}`;

          if (allowMulti) {
            const items = Array.isArray(val) ? [...val] : [];
            for (let i = 0; i < items.length; i++) {
              const it = items[i];
              if (!it || it.dbId) continue;

              if (it.source === "local") {
                const file = matchFile(it);
                if (!file) continue;
                const fd = new FormData();
                fd.append("uploaded_file", file);
                fd.append(
                  "description",
                  def.label || def.name || ""
                );
                fd.append(
                  "modalities_json",
                  modalitiesJson
                );
                if (!this.isShared) {
                  fd.append("storage_option", "local");
                  fd.append("subject_index", String(s));
                  fd.append("visit_index", String(v));
                  fd.append("group_index", String(g));
                }
                const headers = this.isShared
                  ? { "Content-Type": "multipart/form-data" }
                  : {
                      Authorization: `Bearer ${this.token}`,
                      "Content-Type":
                        "multipart/form-data",
                    };
                const resp = await axios.post(
                  `${base}/files`,
                  fd,
                  { headers }
                );
                const saved = resp?.data || {};
                items[i] = {
                  ...it,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option:
                    saved.storage_option ||
                    (this.isShared ? "bids" : "local"),
                  file_name: saved.file_name || it.name,
                };
              } else if (
                it.source === "url" &&
                it.url
              ) {
                const fd = new FormData();
                fd.append("url", it.url);
                fd.append(
                  "description",
                  def.label || def.name || ""
                );
                fd.append(
                  "modalities_json",
                  modalitiesJson
                );
                const headers = this.isShared
                  ? {}
                  : {
                      Authorization: `Bearer ${this.token}`,
                    };
                const resp = await axios.post(
                  `${base}/files/url`,
                  fd,
                  { headers }
                );
                const saved = resp?.data || {};
                items[i] = {
                  ...it,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option: "url",
                  file_name: saved.file_name || "",
                };
              }
            }
            this.setDeepValue(
              s,
              v,
              g,
              mIdx,
              fIdx,
              items
            );
            delete this.pendingFiles[key];
          } else {
            if (!val) continue;

            if (
              val.source === "local" &&
              pendingArr[0] instanceof File
            ) {
              const file = pendingArr[0];
              const fd = new FormData();
              fd.append("uploaded_file", file);
              fd.append(
                "description",
                def.label || def.name || ""
              );
              fd.append(
                "modalities_json",
                modalitiesJson
              );
              if (!this.isShared) {
                fd.append("storage_option", "local");
                fd.append("subject_index", String(s));
                fd.append("visit_index", String(v));
                fd.append("group_index", String(g));
              }
              const headers = this.isShared
                ? { "Content-Type": "multipart/form-data" }
                : {
                    Authorization: `Bearer ${this.token}`,
                    "Content-Type":
                      "multipart/form-data",
                  };
              const resp = await axios.post(
                `${base}/files`,
                fd,
                { headers }
              );
              const saved = resp?.data || {};
              this.setDeepValue(
                s,
                v,
                g,
                mIdx,
                fIdx,
                {
                  ...val,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option:
                    saved.storage_option ||
                    (this.isShared ? "bids" : "local"),
                  file_name: saved.file_name || val.name,
                }
              );
              delete this.pendingFiles[key];
            }

            if (val.source === "url" && val.url) {
              const fd = new FormData();
              fd.append("url", val.url);
              fd.append(
                "description",
                def.label || def.name || ""
              );
              fd.append(
                "modalities_json",
                modalitiesJson
              );
              const headers = this.isShared
                ? {}
                : {
                    Authorization: `Bearer ${this.token}`,
                  };
              const resp = await axios.post(
                `${base}/files/url`,
                fd,
                { headers }
              );
              const saved = resp?.data || {};
              this.setDeepValue(
                s,
                v,
                g,
                mIdx,
                fIdx,
                {
                  ...val,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option: "url",
                  file_name: saved.file_name || "",
                }
              );
            }
          }
        }
      }
    },

    async submitData() {
      if (!this.canEdit) {
        this.showDialogMessage(
          "This shared link is view-only."
        );
        return;
      }

      this.applyTransformsForSection();

      const ok = this.validateCurrentSection();
      const blocking = Object.entries(
        this.validationErrors
      ).filter(([k, msg]) => {
        if (!msg) return false;
        const idx = this.parseKey(k);
        if (!idx) return true;
        const { s, v, g, m, f } = idx;
        const isSkipped = !!(
          this.skipFlags[s]?.[v]?.[g]?.[m]?.[f]
        );
        if (isSkipped) return false;
        return !/ is required\.$/.test(msg);
      });

      if (!ok && blocking.length) {
        this.showDialogMessage(
          "Please fix validation errors before saving."
        );
        return;
      }

      const requiredFailures = this.computeRequiredFailures();
      if (requiredFailures.length) {
        this.skipCandidates = requiredFailures;
        this.skipSelections = requiredFailures.reduce(
          (acc, it) => {
            acc[it.key] = false;
            return acc;
          },
          {}
        );
        this.showSkipDialog = true;
        return;
      }

      try {
        await this.uploadPendingFilesForCurrentSection();
      } catch (e) {
        console.error("File upload/register failed:", e);
        this.showDialogMessage(
          "File upload failed. Please try again."
        );
        return;
      }

      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.ensureSlot(s, v, g);
      const dictData = this.arrayToDict(
        this.entryData[s][v][g]
      );

      const rawSkipFlags = this.skipFlags[s][v][g];
      const flagsPayload = this.isShared
        ? this.flagsArrayToDict(rawSkipFlags)
        : rawSkipFlags;

      const payload = {
        study_id: this.study?.metadata?.id,
        subject_index: s,
        visit_index: v,
        group_index: g,
        data: dictData,
        skipped_required_flags: flagsPayload,
      };

      try {
        if (this.isShared) {
          const resp = await axios.post(
            `/forms/shared/${this.shareToken}/data`,
            payload
          );

          const saved = {
            id: resp?.data?.id,
            study_id: payload.study_id,
            subject_index: s,
            visit_index: v,
            group_index: g,
            data: dictData,
            skipped_required_flags:
              resp?.data?.skipped_required_flags ??
              rawSkipFlags,
            form_version:
              resp?.data?.form_version ??
              this.selectedVersion,
            created_at:
              resp?.data?.created_at ??
              new Date().toISOString(),
          };
          (this.existingEntries =
            this.existingEntries || []).push(saved);

          this.showDialogMessage(
            "Data saved successfully."
          );
          this.rebuildEntriesIndex();
          this.hydrateCache.delete(
            `${s}|${v}|${g}|${this.selectedVersion}`
          );
          this.applyVersionView();
          this.updateStatusCacheFor(s, v, g);
          return;
        }

        const headers = {
          headers: { Authorization: `Bearer ${this.token}` },
        };
        const existingId = this.entryIds[s][v][g];

        if (existingId) {
          const resp = await axios.put(
            `/forms/studies/${this.study.metadata.id}/data_entries/${existingId}`,
            payload,
            headers
          );
          this.showDialogMessage(
            "Data updated successfully."
          );
          const idx = this.existingEntries.findIndex(
            (x) => x.id === existingId
          );
          if (idx >= 0)
            this.existingEntries.splice(idx, 1, resp.data);
        } else {
          const params = this.safeVersionParams(
            this.selectedVersion
          );
          const resp = await axios.post(
            `/forms/studies/${this.study.metadata.id}/data`,
            payload,
            params ? { ...headers, params } : headers
          );
          const newId = resp?.data?.id;
          this.entryIds[s][v][g] = newId;
          const saved = {
            id: newId,
            study_id: this.study.metadata.id,
            subject_index: s,
            visit_index: v,
            group_index: g,
            data: dictData,
            skipped_required_flags:
              resp?.data?.skipped_required_flags ??
              rawSkipFlags,
            form_version:
              resp?.data?.form_version ??
              this.selectedVersion,
            created_at:
              resp?.data?.created_at ??
              new Date().toISOString(),
          };
          (this.existingEntries =
            this.existingEntries || []).push(saved);
          this.showDialogMessage(
            "Data saved successfully."
          );
        }

        this.rebuildEntriesIndex();
        this.hydrateCache.delete(
          `${s}|${v}|${g}|${this.selectedVersion}`
        );
        this.applyVersionView();
        this.updateStatusCacheFor(s, v, g);
      } catch (err) {
        console.error(err);
        this.showDialogMessage(
          "Failed to save data. Check console for details."
        );
      }
    },

    updateStatusCacheFor(s, v, g) {
      const e = this.getBestEntryFor(s, v, g);
      const key = `${s}|${v}`;
      if (!e) {
        this.statusMap.set(key, "none");
        return;
      }

      const flags = e.skipped_required_flags;
      const hasSkip = !!(
        Array.isArray(flags) &&
        flags.some(
          (row) =>
            Array.isArray(row) && row.some((x) => !!x)
        )
      );
      if (hasSkip) {
        this.statusMap.set(key, "skipped");
        return;
      }

      const assigned = this.assignedLookup?.[v]?.[g] || [];
      let total = 0,
        filled = 0;

      if (e.data && !Array.isArray(e.data) && typeof e.data === "object") {
        for (const mIdx of assigned) {
          const sec = this.selectedModels[mIdx] || {};
          const sKey = this.sectionDictKey(sec);
          const secObj = e.data[sKey] || {};
          (sec.fields || []).forEach((f, fIdx) => {
            const fKey = this.fieldDictKey(f, fIdx);
            const val = secObj[fKey];
            total += 1;
            if (val != null && val !== "") filled += 1;
          });
        }
      } else if (Array.isArray(e.data)) {
        for (const mIdx of assigned) {
          const row = e.data[mIdx] || [];
          total += row.length;
          filled += row.filter(
            (vv) => vv != null && vv !== ""
          ).length;
        }
      }

      if (total === 0 || filled === 0)
        this.statusMap.set(key, "none");
      else if (filled === total)
        this.statusMap.set(key, "complete");
      else this.statusMap.set(key, "partial");
    },

    confirmSkipSelection() {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.skipCandidates.forEach((it) => {
        const on = !!this.skipSelections[it.key];
        this.setDeepSkip(
          s,
          v,
          g,
          it.sectionIndex,
          it.fieldIndex,
          on
        );
        if (on) this.clearError(it.sectionIndex, it.fieldIndex);
      });
      this.showSkipDialog = false;
      this.submitData();
    },
    cancelSkipSelection() {
      this.showSkipDialog = false;
    },
    jumpToField(item) {
      this.showSkipDialog = false;
      this.$nextTick(() => {
        const el = document.getElementById(item.id);
        if (el && typeof el.focus === "function") el.focus();
      });
    },

    openShareDialog(sIdx, vIdx, gIdx) {
      this.shareParams = {
        subjectIndex: sIdx,
        visitIndex: vIdx,
        groupIndex: gIdx,
      };
      this.generatedLink = "";
      this.copyStatus = "";
      this.showShareDialog = true;
    },
    async createShareLink() {
      const { subjectIndex, visitIndex, groupIndex } =
        this.shareParams;
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
          "/forms/share-link/",
          payload,
          {
            headers: { Authorization: `Bearer ${this.token}` },
          }
        );
        this.generatedLink = resp.data.link;
        this.copyStatus = "";
      } catch (err) {
        this.generatedLink = "";
        this.copyStatus = "";
        if (err.response?.status === 403)
          this.permissionError = true;
      }
    },

    // --- Add Subjects flow ---

    openSubjectDialog() {
      if (this.isShared) {
        this.showDialogMessage(
          "Subjects can only be added from the main study, not from shared links."
        );
        return;
      }

      this.subjectCountDraft = 1;
      this.assignmentMethodDraft = "Random";
      this.subjectDialogError = "";

      this.generateSubjectDrafts();

      this.showSubjectDialog = true;
    },

    closeSubjectDialog() {
      this.showSubjectDialog = false;
      this.subjectDialogError = "";
    },

    onSubjectCountChange(val) {
      const n = Number(val) || 0;
      this.subjectCountDraft = n < 0 ? 0 : n;
      this.generateSubjectDrafts();
    },

    onAssignmentMethodChange(val) {
      this.assignmentMethodDraft = val;
      this.applyAssignmentMethod();
    },

    onSubjectsUpdate(list) {
      this.subjectDrafts = Array.isArray(list) ? list : [];
    },

    inferSubjectIdPattern() {
      const subjects = this.sd.subjects || [];
      if (!subjects.length) {
        return { prefix: "S", startIndex: 1, width: 3 };
      }

      const last = String(
        subjects[subjects.length - 1].id || ""
      ).trim();
      const match = /^(\D*?)(\d+)$/.exec(last);

      if (!match) {
        return {
          prefix: "S",
          startIndex: subjects.length + 1,
          width: 3,
        };
      }

      const prefix = match[1] || "";
      const width = match[2].length;
      const startIndex = parseInt(match[2], 10) + 1;

      return { prefix, startIndex, width };
    },

    generateSubjectDrafts() {
      const count = Number(this.subjectCountDraft) || 0;
      if (count <= 0) {
        this.subjectDrafts = [];
        return;
      }

      const existing = this.sd.subjects || [];
      const existingIds = new Set(
        existing
          .map((s) =>
            String(
              s.id || s.subject_id || ""
            ).trim()
          )
          .filter(Boolean)
      );

      const { prefix, startIndex, width } =
        this.inferSubjectIdPattern();
      const drafts = [];

      let num = startIndex;
      while (drafts.length < count) {
        const id = `${prefix}${String(num).padStart(
          width,
          "0"
        )}`;
        if (!existingIds.has(id)) {
          drafts.push({
            id,
            group: null,
          });
        }
        num += 1;
      }

      this.subjectDrafts = drafts;
      this.applyAssignmentMethod();
    },

    defaultGroupForIndex(index) {
      if (!this.groupList.length) return null;
      const g = this.groupList[
        index % this.groupList.length
      ];
      return g && g.name ? g.name : null;
    },

    applyAssignmentMethod() {
      if (!this.subjectDrafts.length || !this.groupList.length)
        return;

      const method = String(
        this.assignmentMethodDraft || ""
      ).toLowerCase();

      if (method === "random") {
        this.subjectDrafts = this.subjectDrafts.map(
          (s) => {
            const idx = Math.floor(
              Math.random() * this.groupList.length
            );
            const g = this.groupList[idx];
            return {
              ...s,
              group: g && g.name ? g.name : null,
            };
          }
        );
      } else if (method === "manual") {
        this.subjectDrafts = this.subjectDrafts.map(
          (s, idx) => {
            if (s.group) return s;
            return {
              ...s,
              group: this.defaultGroupForIndex(idx),
            };
          }
        );
      } else if (method === "skip") {
        this.subjectDrafts = this.subjectDrafts.map(
          (s, idx) => ({
            ...s,
            group:
              s.group || this.defaultGroupForIndex(idx),
          })
        );
      }
    },

    async saveNewSubjects() {
      if (this.isShared) {
        this.subjectDialogError =
          "Subjects cannot be added from a shared link.";
        return;
      }

      this.subjectDialogError = "";

      if (!this.subjectDrafts.length) {
        this.subjectDialogError =
          "Please configure at least one subject.";
        return;
      }

      const cleanedDrafts = this.subjectDrafts.map((s) => ({
        id: String(s.id || "").trim(),
        group: String(s.group || "").trim(),
      }));

      for (const s of cleanedDrafts) {
        if (!s.id) {
          this.subjectDialogError =
            "Each subject must have an ID.";
          return;
        }
        if (!s.group) {
          this.subjectDialogError =
            "Each subject must be assigned to a group.";
          return;
        }
      }

      const seen = new Set();
      for (const s of cleanedDrafts) {
        if (seen.has(s.id)) {
          this.subjectDialogError =
            "Duplicate subject IDs in the new subjects.";
          return;
        }
        seen.add(s.id);
      }

      const existing = this.sd.subjects || [];
      const existingIds = new Set(
        existing
          .map((s) =>
            String(
              s.id || s.subject_id || ""
            ).trim()
          )
          .filter(Boolean)
      );
      for (const s of cleanedDrafts) {
        if (existingIds.has(s.id)) {
          this.subjectDialogError = `Subject ID "${s.id}" already exists.`;
          return;
        }
      }

      const merged = [...existing, ...cleanedDrafts];

      const currentStudyData =
        (this.study &&
          this.study.content &&
          this.study.content.study_data) ||
        {};
      const updatedStudyData = {
        ...currentStudyData,
        subjects: merged,
        subjectCount: merged.length,
      };

      const payload = {
        study_metadata: this.study.metadata,
        study_content: {
          study_data: updatedStudyData,
        },
      };

      this.savingSubjects = true;
      try {
        await axios.put(
          `/forms/studies/${this.study.metadata.id}`,
          payload,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        if (
          this.study &&
          this.study.content &&
          this.study.content.study_data
        ) {
          this.study.content.study_data.subjects = merged;
          this.study.content.study_data.subjectCount =
            merged.length;
        }

        this.initializeEntryData();
        this.prepareSubjectGroupIndexMap();
        this.buildStatusCache();

        this.showSubjectDialog = false;
        this.subjectDrafts = [];
        this.subjectCountDraft = 1;
        this.assignmentMethodDraft = "Random";

        this.showDialogMessage(
          "Subjects added successfully."
        );
      } catch (e) {
        console.error("Failed to add subjects", e);
        this.subjectDialogError =
          "Failed to save subjects. Please try again.";
      } finally {
        this.savingSubjects = false;
      }
    },

    showDialogMessage(message) {
      this.dialogMessage = message;
      this.showDialog = true;
    },
    closeDialog() {
      this.showDialog = false;
      this.dialogMessage = "";
    },
  },
};
</script>

<style scoped>
.study-data-container {
  max-width: none;
  margin: 24px auto;
  padding: 10px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;
}

/* Back buttons */
.back-buttons-container {
  margin-bottom: 16px;
}
 .btn-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px 14px;

  cursor: pointer;
  color: $text-color;
  font-size: 14px;
  line-height: 1;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.02s ease;
}

.btn-back:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.btn-back:active {
  transform: scale(0.98);
}

.btn-back i {
  font-size: 14px;
 }

/* Header */
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
.shared-banner {
  margin-top: 8px;
  font-size: 14px;
  color: #374151;
}
hr {
  margin: 12px 0;
  border: 0;
  border-top: 1px solid #e5e7eb;
}

/* Details panel */
.details-panel {
  margin-bottom: 16px;
}
.details-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end; /* keep on the right, as you asked */
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

/* Merge Study button (now sits in the header controls row) */
.btn-merge-study {
  background: #2563eb;
  color: #ffffff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-merge-study:hover {
  background: #1d4ed8;
}

/* Breadcrumb */
.bread-crumb {
  background: #f9fafb;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 24px;
  font-size: 14px;
  color: #374151;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.crumb-left {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.version-helper {
  font-size: 12px;
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 4px 8px;
}
.legend-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  line-height: 1;
  color: #6b7280;
}
.legend-btn:hover {
  color: #374151;
}

/* Sections + fields */
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
.field-label {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.helper-icon {
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
}
.helper-icon:hover {
  color: #374151;
}
.required {
  color: #dc2626;
  margin-left: 4px;
}
.help-inline {
  font-style: italic;
  color: #6b7280;
  margin-left: 8px;
}

/* Inputs */
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
  background: #fff;
}
input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

/* Errors */
.error-message {
  color: #dc2626;
  font-size: 12px;
  margin-top: 4px;
}

/* Empty state */
.no-assigned {
  font-style: italic;
  color: #6b7280;
  margin-top: 12px;
}

/* Actions */
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
.btn-save[disabled] {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-save:hover:not([disabled]) {
  background: #15803d;
}
.btn-clear {
  background: #e5e7eb;
  color: #1f2937;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  margin-left: 8px;
  transition: background 0.2s;
}
.btn-clear:hover {
  background: #d1d5db;
}

/* Generic dialogs */
.loading {
  text-align: center;
  padding: 50px;
  font-size: 16px;
  color: #6b7280;
}
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
.dialog-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.dialog-actions button:first-child,
.dialog-actions button:last-child {
  background: #e5e7eb;
  color: #1f2937;
}

/* Share result + copy button layout */
.share-result {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
}
.share-result-text {
  font-size: 13px;
  color: #374151;
}
.btn-copy-link {
  background: #2563eb;
  color: #ffffff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.btn-copy-link:hover {
  background: #1d4ed8;
}
.generated-link-preview {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  word-break: break-all;
}
.copy-status {
  margin-top: 6px;
  font-size: 12px;
  color: #374151;
}

/* Mini dialog (constraints / legends) */
.mini-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.mini-dialog {
  width: 360px;
  max-width: 92%;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  padding: 12px 12px 10px;
}
.mini-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.mini-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}
.mini-close {
  background: transparent;
  border: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}
.mini-close:hover {
  color: #111827;
}
.mini-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 14px;
}
.mini-list li {
  margin: 4px 0;
}

/* Legend swatches */
.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  display: inline-block;
  margin-right: 8px;
  vertical-align: -1px;
}
.swatch-none {
  background: #e5e7eb;
}
.swatch-partial {
  background: #fbbf24;
}
.swatch-complete {
  background: #16a34a;
}
.swatch-skipped {
  background: #ef4444;
}
.legend-explain li {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Skip dialog */
.dialog-wide {
  width: 680px;
  max-width: 95%;
}
.skip-list {
  max-height: 360px;
  overflow: auto;
  border: 1px dashed #e5e7eb;
  padding: 8px;
  border-radius: 8px;
  margin: 10px 0;
}
.skip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px;
  border-bottom: 1px solid #f3f4f6;
  gap: 12px;
}
.skip-row:last-child {
  border-bottom: none;
}
.skip-left {
  min-width: 0;
}
.skip-title {
  font-size: 14px;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.skip-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.skip-chk {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn-jump {
  background: #e5e7eb;
  color: #111827;
  border: none;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.btn-jump:hover {
  background: #d1d5db;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
  border: none;
}
.btn-option {
  background: #e5e7eb;
  color: #111827;
}

/* Tiny pill near error */
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

/* Merge panel shown instead of matrix, within same container */
.merge-panel {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}
</style>
