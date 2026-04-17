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
          <div v-if="!isMergeMode" class="selection-import-bar">
      <button
        type="button"
        class="import-btn"
        @click="openImportDialogFromSelection"
      >
        <i :class="icons.upload || 'fas fa-file-import'"></i>
        Import Data
      </button>
    </div>
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
        <div class="crumb-actions">
          <button
            v-if="canEdit"
            type="button"
            class="import-btn"
            @click="openImportDialog"
            title="Import data from CSV or Excel"
          >
            <i :class="icons.upload || 'fas fa-file-import'"></i>
            Import Data
          </button>

          <button type="button" class="legend-btn" @click="openLegendDialog" :title="'Legend / What does * mean?'">
            <i :class="icons.help || 'fas fa-question-circle'"></i>
          </button>
        </div>
      </div>

      <div class="entry-form-section">
        <h2>
          Enter Data for Subject: {{ sd.subjects?.[currentSubjectIndex]?.id }},
          Visit: “{{ visitList[currentVisitIndex].name }}”
        </h2>

        <!-- Only assigned sections are shown -->
        <div v-if="assignedModelIndices.length">
          <template v-for="mIdx in assignedModelIndices" :key="'sec-wrap-' + mIdx">
            <div
              v-if="hasVisibleFieldsInSection(mIdx)"
              :key="'sec-' + mIdx"
              class="section-block"
            >
              <h3>{{ selectedModels[mIdx].title }}</h3>

              <template v-for="(field, fIdx) in selectedModels[mIdx].fields" :key="'f-wrap-' + mIdx + '-' + fIdx">
                <div
                  v-if="isFieldVisible(mIdx, fIdx)"
                  :key="'f-' + mIdx + '-' + fIdx"
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
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    :minlength="field.constraints?.minLength"
                    :maxlength="field.constraints?.maxLength"
                    :pattern="field.constraints?.pattern"
                    @blur="onFieldBlur(mIdx, fIdx)"
                    @input="() => { clearError(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <!-- TEXTAREA -->
                  <textarea
                    v-else-if="field.type === 'textarea'"
                    :id="fieldId(mIdx, fIdx)"
                    v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    :placeholder="field.placeholder"
                    :required="!!field.constraints?.required"
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    :minlength="field.constraints?.minLength"
                    :maxlength="field.constraints?.maxLength"
                    :pattern="field.constraints?.pattern"
                    rows="4"
                    @blur="onFieldBlur(mIdx, fIdx)"
                    @input="() => { clearError(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  ></textarea>

                  <!-- NUMBER -->
                  <input
                    v-else-if="field.type === 'number'"
                    :id="fieldId(mIdx, fIdx)"
                    type="number"
                    v-model.number="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    :placeholder="field.placeholder"
                    :required="!!field.constraints?.required"
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    :min="field.constraints?.min"
                    :max="field.constraints?.max"
                    :step="field.constraints?.step"
                    @blur="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                    @input="() => { clearError(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <!-- CHECKBOX -->
                  <FieldCheckbox
                    v-else-if="field.type === 'checkbox'"
                    :id="fieldId(mIdx, fIdx)"
                    v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                    :disabled="isReadonlyField(field, mIdx, fIdx)"
                    @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
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
                    :disabled="isReadonlyField(field, mIdx, fIdx)"
                    @change="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                    @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
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
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    @change="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                    @blur="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <!-- TIME -->
                  <FieldTime
                    v-else-if="field.type === 'time'"
                    :id="fieldId(mIdx, fIdx)"
                    v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    :placeholder="field.placeholder || (field.constraints?.timeFormat || 'HH:mm')"
                    v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    @change="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                    @blur="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <!-- SELECT -->
                  <FieldSelect
                    v-else-if="field.type === 'select'"
                    :id="fieldId(mIdx, fIdx)"
                    v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    :options="field.options || []"
                    :multiple="!!field.constraints?.allowMultiple"
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    :default-value="field.constraints?.defaultValue"
                    :placeholder="'Select…'"
                    @update:modelValue="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <!-- SLIDER -->
                  <FieldSlider
                    v-else-if="field.type === 'slider' && (field.constraints?.mode || 'slider') === 'slider'"
                    :id="fieldId(mIdx, fIdx)"
                    v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    v-bind="getSliderProps(field)"
                    :disabled="isReadonlyField(field, mIdx, fIdx)"
                    @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                    @change="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <!-- LINEAR SCALE -->
                  <FieldLinearScale
                    v-else-if="field.type === 'slider' && field.constraints?.mode === 'linear'"
                    :id="fieldId(mIdx, fIdx)"
                    v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    v-bind="getLinearProps(field)"
                    :disabled="isReadonlyField(field, mIdx, fIdx)"
                    @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                    @change="() => { validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />
                  <!-- TABLE -->
                  <FieldTable
                      v-else-if="field.type === 'table'"
                      :ref="`tableField_${mIdx}_${fIdx}`"
                      :id="fieldId(mIdx, fIdx)"
                      v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                      :field="field"
                      :readonly="isReadonlyField(field, mIdx, fIdx)"
                      @update:modelValue="() => { clearError(mIdx, fIdx); validateField(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                      @validation-state="(payload) => onTableValidationState(mIdx, fIdx, payload)"
                    />

                  <!-- FILE -->
                  <FieldFileUpload
                    v-else-if="field.type === 'file'"
                    :id="fieldId(mIdx, fIdx)"
                    :value="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                    :constraints="field.constraints || {}"
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
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
                    :readonly="isReadonlyField(field, mIdx, fIdx)"
                    @blur="onFieldBlur(mIdx, fIdx)"
                    @input="() => { clearError(mIdx, fIdx); onRuntimeFieldChanged(mIdx, fIdx); }"
                  />

                  <div v-if="fieldErrors(mIdx, fIdx)" class="error-message">
                    {{ fieldErrors(mIdx, fIdx) }}
                    <span
                      v-if="isFieldSkipped(mIdx, fIdx)"
                      class="skip-pill"
                      title="Required validation skipped for this field"
                    >Skipped</span>
                  </div>
                  <div v-else-if="isFieldSkipped(mIdx, fIdx)" class="error-message">
                    <span class="skip-pill" title="Required validation skipped for this field">Skipped</span>
                  </div>

                  <div v-if="fieldCalcWarning(mIdx, fIdx)" class="calc-warning-message">
                    {{ fieldCalcWarning(mIdx, fIdx) }}
                  </div>
                </div>
              </template>
            </div>
          </template>

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

    <StudyShareDialog
      v-if="showShareDialog && !isShared"
      :visible="showShareDialog"
      :subject-label="shareParams.subjectIndex != null ? sd.subjects?.[shareParams.subjectIndex]?.id : 'N/A'"
      :visit-label="visitList[shareParams.visitIndex]?.name || 'N/A'"
      :available-sections="shareDialogSections"
      :permission="shareConfig.permission"
      :max-uses="shareConfig.maxUses"
      :expires-in-days="shareConfig.expiresInDays"
      :generated-link="generatedLink"
      :copy-status="copyStatus"
      @close="showShareDialog = false"
      @copy="copyGeneratedLink"
      @generate="onShareDialogGenerate"
    />

    <PermissionDeniedDialog
      :visible="permissionError"
      @close="permissionError = false"
    />

    <StudyConstraintDialog
      :visible="showConstraintDialog"
      :title="constraintDialogFieldName"
      :items="constraintDialogItems"
      @close="closeConstraintDialog"
    />

    <StudyLegendDialogs
      :showLegendDialog="showLegendDialog"
      :showStatusLegend="showStatusLegend"
      @close-legend="closeLegendDialog"
      @close-status-legend="closeStatusLegend"
    />

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

    <GroupAssignDialog
      :visible="showGroupAssignDialog"
      :groupAssignScope="groupAssignScope"
      :groupAssignSelectedGroup="groupAssignSelectedGroup"
      :groupAssignError="groupAssignError"
      :savingGroupAssign="savingGroupAssign"
      :groupAssignDrafts="groupAssignDrafts"
      :groupList="groupList"
      @close="closeGroupAssignDialog"
      @save="saveGroupAssignment"
      @update:groupAssignScope="groupAssignScope = $event"
      @update:groupAssignSelectedGroup="groupAssignSelectedGroup = $event"
      @update:groupAssignDrafts="groupAssignDrafts = $event"
    />

    <CustomDialog :message="dialogMessage" :isVisible="showDialog" @close="closeDialog" />

    <SkipRequiredDialog
      :visible="showSkipDialog"
      :skipCandidates="skipCandidates"
      :skipSelections="skipSelections"
      :canEdit="canEdit"
      @confirm="confirmSkipSelectionFromDialog"
      @cancel="cancelSkipSelection"
      @jump="jumpToField"
    />
    <StudyDataImportDialog
      v-if="showImportDialog"
      :visible="showImportDialog"
      :available-fields="importableFields"
      :subjects="importDialogSubjects"
      :visit-label="visitList[selectedVisitIndex === -1 ? 0 : selectedVisitIndex]?.name || ''"
      :preview-rows="importPreviewRows"
      :preview-summary="importPreviewSummary"
      :analyzing="importAnalyzing"
      :committing="importCommitting"
      @close="closeImportDialog"
      @analyze="buildImportPreview"
      @commit="commitImportPreview"
    />
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
import StudyShareDialog from "@/components/dataentry/StudyShareDialog.vue";
import PermissionDeniedDialog from "@/components/dataentry/PermissionDeniedDialog.vue";
import StudyConstraintDialog from "@/components/dataentry/StudyConstraintDialog.vue";
import StudyLegendDialogs from "@/components/dataentry/StudyLegendDialogs.vue";
import GroupAssignDialog from "@/components/dataentry/GroupAssignDialog.vue";
import SkipRequiredDialog from "@/components/dataentry/SkipRequiredDialog.vue";
import StudyDataImportDialog from "@/components/dataentry/StudyDataImportDialog.vue";
import FieldTable from "@/components/FieldTable.vue";
import {
  getCalculationRulesFromStudy,
  getCalculationFormulaForField,
  buildFieldLookup,
  isCalculatedRuntimeField as isCalculatedRuntimeFieldUtil,
  computeCalculation,
  sectionHasVisibleFields,
  evaluateFieldVisibility,
} from "@/utils/formLogicRuntime";

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
    FieldTable,
    FieldFileUpload,
    SelectionMatrixView,
    AddSubjectsDialog,
    MergeStudy,
    StudyShareDialog,
    PermissionDeniedDialog,
    StudyConstraintDialog,
    StudyLegendDialogs,
    GroupAssignDialog,
    SkipRequiredDialog,
    StudyDataImportDialog,
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

      // calc warnings
      calcWarnings: {},

      icons,
      showShareDialog: false,
      shareParams: { subjectIndex: null, visitIndex: null, groupIndex: null },
      shareConfig: { permission: "view", maxUses: 1, expiresInDays: 7, allowed_section_ids: [] },
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
      showGroupAssignDialog: false,
      groupAssignScope: "one", // "one" | "all"
      groupAssignSelectedGroup: "",
      groupAssignSubjectIndex: null,
      groupAssignVisitIndex: null,
      groupAssignError: "",
      savingGroupAssign: false,
      groupAssignDrafts: [],
      showImportDialog: false,
      importPreviewRows: [],
      importPreviewSummary: {
      totalRows: 0,
      readyRows: 0,
      warningRows: 0,
      errorRows: 0,
    },
      importPreviewPayload: null,
      importAnalyzing: false,
      importCommitting: false,

      currentRevisionToken: "",
      slotLoading: false,
      tableValidationStates: {},
    };
  },

  computed: {
    importDialogSubjects() {
      const subjects = Array.isArray(this.sd?.subjects) ? this.sd.subjects : [];

      return subjects.map((s, idx) => {
        const subjectLabel = String(s?.id || s?.subject_id || `Subject ${idx + 1}`).trim();
        const groupName = String(s?.group || "").trim();

        return {
          index: idx,
          label: subjectLabel,
          groupLabel: groupName || "Unassigned",
        };
      });
    },
    importableFields() {
      const models = Array.isArray(this.selectedModels) ? this.selectedModels : [];
      const assigned = Array.isArray(this.assignedModelIndices) ? this.assignedModelIndices : [];

      const out = [];

      assigned.forEach((mIdx) => {
        const section = models[mIdx] || {};
        const fields = Array.isArray(section.fields) ? section.fields : [];

        fields.forEach((field, fIdx) => {
          out.push({
            key: `${mIdx}-${fIdx}`,
            modelIndex: mIdx,
            fieldIndex: fIdx,
            sectionTitle: section.title || `Section ${mIdx + 1}`,
            fieldLabel: field.label || field.name || field.title || `Field ${fIdx + 1}`,
            fieldName: field.name || field.label || field.title || `Field ${fIdx + 1}`,
            fieldType: field.type || "text",
          });
        });
      });

      return out;
    },
    shareDialogSections() {
      const v = Number(this.shareParams?.visitIndex);
      const g = Number(this.shareParams?.groupIndex);

      if (!Number.isInteger(v) || v < 0) return [];
      if (!Number.isInteger(g) || g < 0) return [];

      const selectedModels = Array.isArray(this.selectedModels) ? this.selectedModels : [];
      const assignments = Array.isArray(this.assignments) ? this.assignments : [];

      return selectedModels
        .map((section, mIdx) => {
          const assigned = !!assignments?.[mIdx]?.[v]?.[g];
          if (!assigned) return null;

          const realId = String(
            section?._id ||
            section?.id ||
            section?.uuid ||
            ""
          ).trim();

          if (!realId) return null;

          return {
            id: realId,
            title: section?.title || `Section ${mIdx + 1}`,
            modelIndex: mIdx,
          };
        })
        .filter(Boolean);
    },

    shareableSectionsForCurrentCell() {
      const v = this.shareParams?.visitIndex;
      const g = this.shareParams?.groupIndex;

      if (v == null || g == null) return [];

      return (this.selectedModels || [])
        .map((sec, mIdx) => ({ sec, mIdx }))
        .filter(({ mIdx }) => !!this.assignments?.[mIdx]?.[v]?.[g])
        .map(({ sec }) => {
          const realId = String(sec?._id || sec?.id || sec?.uuid || "").trim();
          if (!realId) return null;

          return {
            id: realId,
            title: sec?.title || "Untitled Section"
          };
        })
        .filter(Boolean);
    },
    unassignedSubjectIndices() {
      const subjects = this.sd.subjects || [];
      const out = [];
      for (let i = 0; i < subjects.length; i++) {
        const g = String(subjects[i]?.group || "").trim();
        if (!g) out.push(i);
      }
      return out;
    },
    canSeeGroupColumn() {
      if (!this.study?.metadata) return false;

      const isCreator = this.study.metadata.created_by === this.$store.state.user?.id;
      const hasAddPermission = this.isShared && this.sharedPermission === "add";
      const isAdmin = this.$store.state.user?.role === "Administrator";

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
      const v = Number.isInteger(this.currentVisitIndex) ? this.currentVisitIndex : 0;
      const g = Number.isInteger(this.currentGroupIndex) ? this.currentGroupIndex : 0;
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

    calculationRules() {
      return getCalculationRulesFromStudy(this.study);
    },

    shareDialogSubjectLabel() {
      const idx = this.shareParams?.subjectIndex;
      return idx != null ? (this.sd.subjects?.[idx]?.id || "N/A") : "N/A";
    },

    shareDialogVisitLabel() {
      const idx = this.shareParams?.visitIndex;
      return this.visitList?.[idx]?.name || "";
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
  validateTableChild(mIdx, fIdx) {
      const refName = `tableField_${mIdx}_${fIdx}`;
      const comp = this.$refs?.[refName];

      if (!comp) return true;

      const instance = Array.isArray(comp) ? comp[0] : comp;
      if (!instance || typeof instance.validateForSubmit !== "function") {
        return true;
      }

      return instance.validateForSubmit();
    },
  onTableValidationState(mIdx, fIdx, payload) {
      const key = this.errorKey(mIdx, fIdx);
      const next = { ...(this.tableValidationStates || {}) };

      next[key] = {
        valid: !!payload?.valid,
        message: payload?.message || "",
        cellErrors: payload?.cellErrors || {},
      };

      this.tableValidationStates = next;

      if (payload?.valid) {
        this.clearError(mIdx, fIdx);
      } else {
        this.setError(
          mIdx,
          fIdx,
          payload?.message || "Table contains invalid cells."
        );
      }
    },

  getTableValidationState(mIdx, fIdx) {
      return this.tableValidationStates?.[this.errorKey(mIdx, fIdx)] || null;
    },


  normalizeSkipFlagsShape(rawFlags) {
      const skeleton = this.makeSkipSkeleton();

      if (!Array.isArray(rawFlags)) return skeleton;

      return skeleton.map((sectionRow, mIdx) => {
        const incomingRow = rawFlags[mIdx];

        if (!Array.isArray(incomingRow)) {
          return [...sectionRow];
        }

        return sectionRow.map((_, fIdx) => !!incomingRow[fIdx]);
      });
    },
  async commitImportPreview() {
  try {
    this.importCommitting = true;

    const validRows = (this.importPreviewRows || []).filter((r) => r.status === "Ready");
    if (!validRows.length) {
      this.showDialogMessage("No valid rows are available to commit.");
      return;
    }

    let committed = 0;
    let failed = 0;

    for (const row of validRows) {
      try {
        const s = row.targetSubjectIndex;
        const v = row.targetVisitIndex;
        const g = row.targetGroupIndex;

        if (s == null || v == null || g == null) {
          failed += 1;
          continue;
        }

        this.currentSubjectIndex = s;
        this.currentVisitIndex = v;
        this.currentGroupIndex = g;

        this.ensureSlot(s, v, g);

        row.importedFields.forEach((item) => {
          const mIdx = Number(item.modelIndex);
          const fIdx = Number(item.fieldIndex);
          const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
          if (!field) return;
          if (this.isReadonlyField(field, mIdx, fIdx)) return;

          const parsed = this.normalizeImportedValueForField(field, item.rawValue);
          this.setDeepValue(s, v, g, mIdx, fIdx, parsed);
          this.setDeepSkip(s, v, g, mIdx, fIdx, false);
        });

        this.runCalculationsForCell(s, v, g, null, null);

        const dictData = this.arrayToDict(this.entryData[s][v][g]);
        const rawSkipFlags = this.normalizeSkipFlagsShape(this.skipFlags[s][v][g]);
        this.skipFlags[s][v][g] = rawSkipFlags;

        const payload = {
          study_id: this.study?.metadata?.id,
          subject_index: s,
          visit_index: v,
          group_index: g,
          data: dictData,
          skipped_required_flags: rawSkipFlags,
        };

        const headers = {
          headers: { Authorization: `Bearer ${this.token}` },
        };

        const slot = await this.fetchRevisionTokenForSlot(s, v, g, this.selectedVersion);
        const expectedRevisionToken = String(slot?.revision_token || "");
        const existing = slot?.entry_id ? { id: slot.entry_id } : this.getBestEntryFor(s, v, g);

        if (existing?.id) {
          const resp = await axios.put(
            `/forms/studies/${this.study.metadata.id}/data_entries/${existing.id}`,
            payload,
            {
              ...headers,
              params: {
                audit_label: "Bulk Import Update",
                expected_revision_token: expectedRevisionToken,
              },
            }
          );
          const idx = this.existingEntries.findIndex((x) => x.id === existing.id);
          if (idx >= 0) this.existingEntries.splice(idx, 1, resp.data);
        } else {
          const params = this.safeVersionParams(this.selectedVersion);
          const resp = await axios.post(
            `/forms/studies/${this.study.metadata.id}/data`,
            payload,
            {
              ...headers,
              params: {
                ...(params || {}),
                audit_label: "Bulk Import Create",
                expected_revision_token: expectedRevisionToken,
              },
            }
          );

          const newId = resp?.data?.id;
          this.entryIds[s][v][g] = newId;
          this.existingEntries.push({
            id: newId,
            study_id: this.study.metadata.id,
            subject_index: s,
            visit_index: v,
            group_index: g,
            data: dictData,
            skipped_required_flags: rawSkipFlags,
            form_version: resp?.data?.form_version ?? this.selectedVersion,
            created_at: resp?.data?.created_at ?? new Date().toISOString(),
          });
        }
        this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
        this.updateStatusCacheFor(s, v, g);
        committed += 1;
      } catch (e) {
        console.error("Bulk import row commit failed", row, e);
        failed += 1;
      }
    }

    this.rebuildEntriesIndex();
    this.buildStatusCache();
    this.closeImportDialog();

    if (failed) {
      this.showDialogMessage(`Bulk import finished. ${committed} row(s) committed, ${failed} row(s) failed during save.`);
    } else {
      this.showDialogMessage(`Bulk import finished successfully. ${committed} row(s) committed.`);
    }
  } catch (e) {
    console.error("Bulk import commit failed", e);
    this.showDialogMessage("Failed to commit bulk import.");
  } finally {
    this.importCommitting = false;
  }
},
  simulateImportedRowValidation({
  targetSubjectIndex,
  targetVisitIndex,
  targetGroupIndex,
  importedFields,
}) {
  const issues = [];

  const originalEntryData = this.entryData;
  const originalSkipFlags = this.skipFlags;
  const originalValidationErrors = this.validationErrors;
  const originalCalcWarnings = this.calcWarnings;
  const originalCurrentSubjectIndex = this.currentSubjectIndex;
  const originalCurrentVisitIndex = this.currentVisitIndex;
  const originalCurrentGroupIndex = this.currentGroupIndex;

  try {
    // lightweight deep clone only for simulation
    this.entryData = JSON.parse(JSON.stringify(this.entryData || []));
    this.skipFlags = JSON.parse(JSON.stringify(this.skipFlags || []));
    this.validationErrors = {};
    this.calcWarnings = {};

    this.currentSubjectIndex = targetSubjectIndex;
    this.currentVisitIndex = targetVisitIndex;
    this.currentGroupIndex = targetGroupIndex;

    this.ensureSlot(targetSubjectIndex, targetVisitIndex, targetGroupIndex);

    importedFields.forEach((item) => {
      const mIdx = Number(item.modelIndex);
      const fIdx = Number(item.fieldIndex);

      if (!this.assignments?.[mIdx]?.[targetVisitIndex]?.[targetGroupIndex]) {
        issues.push(
          `${item.sectionTitle} → ${item.fieldLabel}: section is not assigned for this visit/group.`
        );
        return;
      }

      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
      if (!field) {
        issues.push(`${item.sectionTitle} → ${item.fieldLabel}: field not found in current template.`);
        return;
      }

      if (this.isReadonlyField(field, mIdx, fIdx)) {
        issues.push(`${item.sectionTitle} → ${item.fieldLabel}: field is read-only and cannot be imported.`);
        return;
      }

      const normalized = this.normalizeImportedValueForField(field, item.rawValue);
      this.setDeepValue(targetSubjectIndex, targetVisitIndex, targetGroupIndex, mIdx, fIdx, normalized);
      this.setDeepSkip(targetSubjectIndex, targetVisitIndex, targetGroupIndex, mIdx, fIdx, false);
    });

    this.runCalculationsForCell(targetSubjectIndex, targetVisitIndex, targetGroupIndex, null, null);

    const assigned = this.selectedModels
      .map((_, mIdx) => mIdx)
      .filter((mIdx) => !!this.assignments?.[mIdx]?.[targetVisitIndex]?.[targetGroupIndex]);

    assigned.forEach((mIdx) => {
      const section = this.selectedModels?.[mIdx];
      (section?.fields || []).forEach((field, fIdx) => {
        if (!this.hasVisibleFieldsInSection(mIdx)) return;
        if (!this.isFieldVisible(mIdx, fIdx)) return;

        const valid = this.validateField(mIdx, fIdx);
        if (!valid) {
          const msg = this.fieldErrors(mIdx, fIdx);
          if (msg) {
            issues.push(`${section?.title || `Section ${mIdx + 1}`} → ${field?.label || field?.name || `Field ${fIdx + 1}`}: ${msg}`);
          }
        }
      });
    });

    return { issues };
  } finally {
    this.entryData = originalEntryData;
    this.skipFlags = originalSkipFlags;
    this.validationErrors = originalValidationErrors;
    this.calcWarnings = originalCalcWarnings;
    this.currentSubjectIndex = originalCurrentSubjectIndex;
    this.currentVisitIndex = originalCurrentVisitIndex;
    this.currentGroupIndex = originalCurrentGroupIndex;
  }
},
async buildImportPreview(payload) {
  try {
    this.importAnalyzing = true;
    this.importPreviewRows = [];
    this.importPreviewSummary = {
      totalRows: 0,
      readyRows: 0,
      warningRows: 0,
      errorRows: 0,
    };
    this.importPreviewPayload = payload || null;

    const rows = Array.isArray(payload?.dataRows) ? payload.dataRows : [];
    const columns = Array.isArray(payload?.columns) ? payload.columns : [];
    const mappings = payload?.mappings || {};
    const metadataMapping = payload?.metadataMapping || {};
    const mode = String(payload?.mode || "single");

    const previewRows = [];

    for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
      const row = rows[rowIndex] || [];
      const issues = [];
      let targetSubjectIndex = null;
      let targetVisitIndex = null;
      let targetGroupIndex = null;

      const getMeta = (key) => {
        const idx = metadataMapping?.[key];
        if (idx == null || idx === "") return "";
        return String(row[Number(idx)] ?? "").trim();
      };

      const subjectValue = getMeta("subject");
      const visitValue = getMeta("visit");
      const groupValue = getMeta("group");

      // match subject
      if (mode === "single") {
        targetSubjectIndex = Number(payload?.selectedSubjectIndex);
      } else {
        const normalizedSubject = String(subjectValue || "").trim().toLowerCase();
        targetSubjectIndex = (this.sd.subjects || []).findIndex((s) => {
          const sid = String(s?.id || s?.subject_id || "").trim().toLowerCase();
          return sid && sid === normalizedSubject;
        });

        if (targetSubjectIndex < 0) {
          issues.push(`Subject "${subjectValue || "blank"}" was not found in this study.`);
          targetSubjectIndex = null;
        }
      }

      // visit
      if (mode === "single") {
        targetVisitIndex =
          this.selectedVisitIndex === -1
            ? 0
            : Number.isInteger(this.selectedVisitIndex)
            ? this.selectedVisitIndex
            : 0;
      } else {
        const normalizedVisit = String(visitValue || "").trim().toLowerCase();
        const matchedVisitIndex = this.visitList.findIndex((v) => {
          return String(v?.name || "").trim().toLowerCase() === normalizedVisit;
        });

        if (matchedVisitIndex < 0) {
          issues.push(`Visit "${visitValue || "blank"}" was not found in this study.`);
          targetVisitIndex = null;
        } else {
          targetVisitIndex = matchedVisitIndex;
        }
      }

      // group
      if (targetSubjectIndex != null && targetSubjectIndex >= 0) {
        targetGroupIndex = this.subjectToGroupIdx?.[targetSubjectIndex];
        if (targetGroupIndex == null || targetGroupIndex < 0) {
          issues.push(`Matched subject does not have a valid assigned group.`);
          targetGroupIndex = null;
        }
      }

      if (mode === "all" && targetGroupIndex != null && targetGroupIndex >= 0) {
        const expectedGroup = String(this.groupList?.[targetGroupIndex]?.name || "").trim().toLowerCase();
        const actualGroup = String(groupValue || "").trim().toLowerCase();

        if (!actualGroup) {
          issues.push(`Group value is missing in the spreadsheet row.`);
        } else if (expectedGroup && actualGroup !== expectedGroup) {
          issues.push(`Group "${groupValue}" does not match the subject group "${this.groupList?.[targetGroupIndex]?.name || ""}".`);
        }
      }

      // mapped values
      let mappedValueCount = 0;
      const importedFields = [];

      Object.keys(mappings || {}).forEach((colIndexStr) => {
        const targetKey = mappings[colIndexStr];
        if (!targetKey) return;

        const colIndex = Number(colIndexStr);
        const rawValue = row[colIndex];

        if (rawValue == null || String(rawValue).trim() === "") return;

        const targetField = this.importableFields.find((f) => f.key === targetKey);
        if (!targetField) return;

        importedFields.push({
          columnIndex: colIndex,
          rawValue,
          modelIndex: targetField.modelIndex,
          fieldIndex: targetField.fieldIndex,
          sectionTitle: targetField.sectionTitle,
          fieldLabel: targetField.fieldLabel,
        });
        mappedValueCount += 1;
      });

      if (!mappedValueCount) {
        issues.push("No mapped spreadsheet values were found in this row.");
      }

      // run actual form pipeline only if metadata matched enough
      if (
        targetSubjectIndex != null &&
        targetVisitIndex != null &&
        targetGroupIndex != null &&
        mappedValueCount > 0
      ) {
        const validationResult = this.simulateImportedRowValidation({
          targetSubjectIndex,
          targetVisitIndex,
          targetGroupIndex,
          importedFields,
        });

        if (validationResult?.issues?.length) {
          issues.push(...validationResult.issues);
        }
      }

      let status = "Ready";
      if (issues.length) {
        const hasHardError = issues.some((x) =>
          /not found|does not match|required|invalid|must be|readonly|not assigned/i.test(String(x))
        );
        status = hasHardError ? "Error" : "Warning";
      }

      previewRows.push({
        rowIndex,
        subjectLabel:
          targetSubjectIndex != null && targetSubjectIndex >= 0
            ? String(this.sd.subjects?.[targetSubjectIndex]?.id || "")
            : subjectValue || "",
        visitLabel:
          targetVisitIndex != null && targetVisitIndex >= 0
            ? String(this.visitList?.[targetVisitIndex]?.name || "")
            : visitValue || "",
        groupLabel:
          targetGroupIndex != null && targetGroupIndex >= 0
            ? String(this.groupList?.[targetGroupIndex]?.name || "")
            : groupValue || "",
        mappedValueCount,
        status,
        issues,
        targetSubjectIndex,
        targetVisitIndex,
        targetGroupIndex,
        importedFields,
      });
    }

    // duplicate target check for bulk
    if (mode === "all") {
      const keyMap = new Map();
      previewRows.forEach((r) => {
        if (
          r.targetSubjectIndex != null &&
          r.targetVisitIndex != null &&
          r.targetGroupIndex != null
        ) {
          const key = `${r.targetSubjectIndex}|${r.targetVisitIndex}|${r.targetGroupIndex}`;
          const arr = keyMap.get(key) || [];
          arr.push(r.rowIndex);
          keyMap.set(key, arr);
        }
      });

      previewRows.forEach((r) => {
        const key = `${r.targetSubjectIndex}|${r.targetVisitIndex}|${r.targetGroupIndex}`;
        const arr = keyMap.get(key) || [];
        if (arr.length > 1) {
          r.issues.push(
            `Multiple spreadsheet rows target the same Subject / Visit / Group (${arr.map((x) => `row ${x + 1}`).join(", ")}).`
          );
          r.status = "Error";
        }
      });
    }

    this.importPreviewRows = previewRows;
    this.importPreviewSummary = {
      totalRows: previewRows.length,
      readyRows: previewRows.filter((r) => r.status === "Ready").length,
      warningRows: previewRows.filter((r) => r.status === "Warning").length,
      errorRows: previewRows.filter((r) => r.status === "Error").length,
    };
  } catch (e) {
    console.error("Failed to build import preview", e);
    this.showDialogMessage("Failed to build import preview.");
  } finally {
    this.importAnalyzing = false;
  }
},
  closeImportDialog() {
      this.showImportDialog = false;
      this.importPreviewRows = [];
      this.importPreviewSummary = {
        totalRows: 0,
        readyRows: 0,
        warningRows: 0,
        errorRows: 0,
      };
      this.importPreviewPayload = null;
      this.importAnalyzing = false;
      this.importCommitting = false;
    },
  openImportDialogFromSelection() {
  if (this.isShared) return;

  if (!this.visitList.length) {
    this.showDialogMessage("No visits available for import.");
    return;
  }

  if (this.selectedVisitIndex === -1) {
    this.selectedVisitIndex = 0;
  }

  this.showImportDialog = true;
},
normalizeImportedValueForField(field, rawValue) {
  const type = String(field?.type || "text").toLowerCase();
  const c = field?.constraints || {};

  if (rawValue == null) return this.defaultForField(field);
  const text = String(rawValue).trim();

  if (text === "") return this.defaultForField(field);

  if (type === "number" || type === "slider") {
    const n = Number(String(rawValue).replace(/,/g, "."));
    return Number.isFinite(n) ? n : this.defaultForField(field);
  }

  if (type === "checkbox") {
    const v = text.toLowerCase();
    return ["true", "yes", "y", "1", "checked"].includes(v);
  }

  if (type === "select") {
    if (c.allowMultiple) {
      return text.split(",").map((x) => x.trim()).filter(Boolean);
    }
    return text;
  }

  if (type === "radio" || type === "date" || type === "time") {
    return text;
  }

  if (type === "file") {
    return this.defaultForField(field);
  }

  return text;
},

applyImportedRowFromDialog(payload) {
  try {
    if (payload?.mode !== "single") {
      this.showDialogMessage("Only single-subject import is supported right now.");
      return;
    }

    const targetSubjectIndex = Number(payload?.targetSubjectIndex);
    if (!Number.isInteger(targetSubjectIndex) || targetSubjectIndex < 0) {
      this.showDialogMessage("Invalid target subject selected.");
      return;
    }

    const visitIdx =
      this.selectedVisitIndex === -1
        ? 0
        : Number.isInteger(this.selectedVisitIndex)
        ? this.selectedVisitIndex
        : 0;

    const targetGroupIdx = this.subjectToGroupIdx?.[targetSubjectIndex];

    if (targetGroupIdx == null || targetGroupIdx < 0) {
      this.showDialogMessage("Selected subject does not have a valid group assigned.");
      return;
    }

    this.currentSubjectIndex = targetSubjectIndex;
    this.currentVisitIndex = visitIdx;
    this.currentGroupIndex = targetGroupIdx;

    this.ensureSlot(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex);

    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (!items.length) {
      this.showDialogMessage("No mapped values found to import.");
      return;
    }

    items.forEach((item) => {
      const mIdx = Number(item.modelIndex);
      const fIdx = Number(item.fieldIndex);

      if (!Number.isInteger(mIdx) || !Number.isInteger(fIdx)) return;

      // only import if actually assigned for this subject's group and current visit
      if (!this.assignments?.[mIdx]?.[visitIdx]?.[targetGroupIdx]) return;

      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
      if (!field) return;
      if (this.isReadonlyField(field, mIdx, fIdx)) return;

      const parsed = this.normalizeImportedValueForField(field, item.rawValue);

      this.setDeepValue(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex, mIdx, fIdx, parsed);
      this.setDeepSkip(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex, mIdx, fIdx, false);
      this.clearError(mIdx, fIdx);
      this.clearCalcWarningFor(mIdx, fIdx);
    });

    this.showSelection = false;
    this.validationErrors = {};
    this.calcWarnings = {};

    this.runAllCalculationsForCurrentCell();

    this.assignedModelIndices.forEach((mIdx) => {
      (this.selectedModels?.[mIdx]?.fields || []).forEach((field, fIdx) => {
        if (this.isReadonlyField(field, mIdx, fIdx)) return;
        this.validateField(mIdx, fIdx);
      });
    });

    this.hydrateCache.delete(`${this.currentSubjectIndex}|${this.currentVisitIndex}|${this.currentGroupIndex}|${this.selectedVersion}`);
    this.showImportDialog = false;

    if (payload?.metadataReview?.hasMetadataMismatch) {
      this.showDialogMessage("Data imported into the selected subject with metadata mismatch warning. Please review before saving.");
    } else {
      this.showDialogMessage("Data imported into the selected subject. Please review and click Save Data.");
    }
  } catch (e) {
    console.error("Import apply failed", e);
    this.showDialogMessage("Failed to import selected row.");
  }
},
    openImportDialog() {
      if (!this.canEdit) {
        this.showDialogMessage("This shared link is view-only.");
        return;
      }

      if (
        this.currentSubjectIndex == null ||
        this.currentVisitIndex == null ||
        this.currentGroupIndex == null
      ) {
        this.showDialogMessage("Please open a subject/visit entry form first.");
        return;
      }

      this.showImportDialog = true;
    },


    applyImportedRowToCurrentForm(payload) {
      try {
        const items = Array.isArray(payload?.items) ? payload.items : [];
        if (!items.length) {
          this.showDialogMessage("No mapped values found to import.");
          return;
        }

        const s = this.currentSubjectIndex;
        const v = this.currentVisitIndex;
        const g = this.currentGroupIndex;

        this.ensureSlot(s, v, g);

        items.forEach((item) => {
          const mIdx = Number(item.modelIndex);
          const fIdx = Number(item.fieldIndex);

          if (!Number.isInteger(mIdx) || !Number.isInteger(fIdx)) return;

          const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
          if (!field) return;

          if (this.isReadonlyField(field, mIdx, fIdx)) return;

          const parsed = this.normalizeImportedValueForField(field, item.rawValue);

          this.setDeepValue(s, v, g, mIdx, fIdx, parsed);
          this.setDeepSkip(s, v, g, mIdx, fIdx, false);
          this.clearError(mIdx, fIdx);
          this.clearCalcWarningFor(mIdx, fIdx);
        });

        this.runAllCalculationsForCurrentCell();

        this.assignedModelIndices.forEach((mIdx) => {
          (this.selectedModels?.[mIdx]?.fields || []).forEach((field, fIdx) => {
            if (this.isReadonlyField(field, mIdx, fIdx)) return;
            this.validateField(mIdx, fIdx);
          });
        });

        this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
        this.showImportDialog = false;
        this.showDialogMessage("Data imported into form. Please review and click Save Data.");
      } catch (e) {
        console.error("Import apply failed", e);
        this.showDialogMessage("Failed to import selected row into the form.");
      }
    },
    onShareDialogGenerate(cfg) {
      this.shareConfig = {
        permission: cfg.permission,
        maxUses: cfg.maxUses,
        expiresInDays: cfg.expiresInDays,
        allowed_section_ids: cfg.allowed_section_ids || []
      };

      this.createShareLink();
    },
    getCurrentCellData() {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;

      if (s == null || v == null || g == null) return [];
      this.ensureSlot(s, v, g);
      return this.entryData?.[s]?.[v]?.[g] || [];
    },

    isFieldVisible(mIdx, fIdx) {
      const cellData = this.getCurrentCellData();
      return evaluateFieldVisibility(this.study, this.selectedModels, cellData, mIdx, fIdx);
    },

    hasVisibleFieldsInSection(mIdx) {
      const cellData = this.getCurrentCellData();
      return sectionHasVisibleFields(this.study, this.selectedModels, cellData, mIdx);
    },
    fieldCalcWarning(mIdx, fIdx) {
      const runtimeKey = this.currentCalcKey(mIdx, fIdx);
      const runtimeWarning = this.calcWarnings?.[runtimeKey];
      if (runtimeWarning) return runtimeWarning;

      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
      if (!field) return "";

      return getCalculationFormulaForField(this.study, this.selectedModels, field) || "";
    },
    /* ============================================================
       CALC RUNTIME HELPERS
       ============================================================ */
    calcKey(s, v, g, m, f) {
      return `${s}-${v}-${g}-${m}-${f}`;
    },
    currentCalcKey(mIdx, fIdx) {
      return this.calcKey(
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex,
        mIdx,
        fIdx
      );
    },
    setCalcWarningFor(mIdx, fIdx, msg) {
      const k = this.currentCalcKey(mIdx, fIdx);
      const next = { ...this.calcWarnings };
      if (msg) next[k] = msg;
      else delete next[k];
      this.calcWarnings = next;
    },
    clearCalcWarningFor(mIdx, fIdx) {
      this.setCalcWarningFor(mIdx, fIdx, "");
    },

    isCalculatedRuntimeField(mIdx, fIdx) {
      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
      return isCalculatedRuntimeFieldUtil(this.study, field);
    },

    isReadonlyField(field, mIdx, fIdx) {
      return !!field?.constraints?.readonly || !this.canEdit || this.isCalculatedRuntimeField(mIdx, fIdx);
    },

    getFieldLookup() {
      return buildFieldLookup(this.selectedModels);
    },

    getFieldMetaByRuleFieldId(ruleFieldId) {
      if (!ruleFieldId) return null;
      const lookup = this.getFieldLookup();
      return lookup.get(String(ruleFieldId)) || null;
    },

    getCellValueByFieldId(s, v, g, ruleFieldId) {
      const meta = this.getFieldMetaByRuleFieldId(ruleFieldId);
      if (!meta) return undefined;
      const { mIdx, fIdx } = meta;
      return this.entryData?.[s]?.[v]?.[g]?.[mIdx]?.[fIdx];
    },

    setCellValueByFieldId(s, v, g, ruleFieldId, value) {
      const meta = this.getFieldMetaByRuleFieldId(ruleFieldId);
      if (!meta) return false;
      const { mIdx, fIdx } = meta;
      this.setDeepValue(s, v, g, mIdx, fIdx, value);
      return true;
    },

    clearCalcWarningByRuleTarget(s, v, g, targetId) {
      const meta = this.getFieldMetaByRuleFieldId(targetId);
      if (!meta) return;
      const { mIdx, fIdx } = meta;
      const k = this.calcKey(s, v, g, mIdx, fIdx);
      const next = { ...this.calcWarnings };
      delete next[k];
      this.calcWarnings = next;
    },

    setCalcWarningByRuleTarget(s, v, g, targetId, msg) {
      const meta = this.getFieldMetaByRuleFieldId(targetId);
      if (!meta) return;
      const { mIdx, fIdx } = meta;
      const k = this.calcKey(s, v, g, mIdx, fIdx);
      const next = { ...this.calcWarnings };
      if (msg) next[k] = msg;
      else delete next[k];
      this.calcWarnings = next;
    },

    runCalculationsForCell(s, v, g, changedMIdx = null, changedFIdx = null) {
      const rules = this.calculationRules || [];
      if (!rules.length) return;

      const changedField = changedMIdx != null && changedFIdx != null
        ? this.selectedModels?.[changedMIdx]?.fields?.[changedFIdx]
        : null;

      const changedKeys = changedField
        ? new Set(
            [
              changedField?._id,
              changedField?.id,
              changedField?.field_id,
              changedField?.uid,
              changedField?.key,
              changedField?.name,
              changedField?.label,
            ]
              .filter(Boolean)
              .map(String)
          )
        : null;

      rules.forEach((rule) => {
        if (!rule?.target || !Array.isArray(rule?.sources) || !rule.sources.length) return;

        if (changedKeys) {
          const touchesChanged = rule.sources.some((src) => changedKeys.has(String(src)));
          if (!touchesChanged) return;
        }

        const sourceValues = rule.sources.map((srcId) => this.getCellValueByFieldId(s, v, g, srcId));
        const result = computeCalculation(rule, sourceValues);

        if (!result.ok) {
          this.setCellValueByFieldId(s, v, g, rule.target, null);
          this.setCalcWarningByRuleTarget(s, v, g, rule.target, result.warning || "Calculation could not be applied.");
          return;
        }

        const targetMeta = this.getFieldMetaByRuleFieldId(rule.target);
        if (!targetMeta) return;

        const { mIdx, fIdx } = targetMeta;
        this.setDeepValue(s, v, g, mIdx, fIdx, result.value);
        this.clearError(mIdx, fIdx);
        this.setCalcWarningByRuleTarget(s, v, g, rule.target, "");

        const fieldDef = this.selectedModels?.[mIdx]?.fields?.[fIdx];
        if (fieldDef) {
          this.validateField(mIdx, fIdx);
        }
      });
    },

    runAllCalculationsForCurrentCell() {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      if (s == null || v == null || g == null) return;
      this.ensureSlot(s, v, g);
      this.runCalculationsForCell(s, v, g, null, null);
    },

    onRuntimeFieldChanged(mIdx, fIdx) {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      if (s == null || v == null || g == null) return;
      this.ensureSlot(s, v, g);

      // user changed something manually -> source errors may go away
      this.clearError(mIdx, fIdx);

      this.$nextTick(() => {
        this.runCalculationsForCell(s, v, g, mIdx, fIdx);
      });
    },

    /* ============================================================
       MERGE CONTROLS
       ============================================================ */
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
        (this.study && this.study.content && this.study.content.study_data) || {};
      const incoming = schema || {};

      // Preserve ALL existing keys by default, then overlay schema.
      // Then we normalize the known array fields safely.
      const merged = {
        ...prev,
        ...incoming,

        // keep/merge nested study object instead of overwriting
        study: {
          ...(prev.study || {}),
          ...(incoming.study || {}),
        },

        subjects: Array.isArray(incoming.subjects)
          ? incoming.subjects
          : Array.isArray(prev.subjects)
          ? prev.subjects
          : [],

        groups: Array.isArray(incoming.groups)
          ? incoming.groups
          : Array.isArray(prev.groups)
          ? prev.groups
          : [],

        visits: Array.isArray(incoming.visits)
          ? incoming.visits
          : Array.isArray(prev.visits)
          ? prev.visits
          : [],

        selectedModels: Array.isArray(incoming.selectedModels)
          ? incoming.selectedModels
          : Array.isArray(prev.selectedModels)
          ? prev.selectedModels
          : [],

        assignments: Array.isArray(incoming.assignments)
          ? incoming.assignments
          : Array.isArray(prev.assignments)
          ? prev.assignments
          : [],
      };

      //  keep subjectCount stable if schema doesn't provide it
      if (!Number.isFinite(merged.subjectCount)) {
        const n = Array.isArray(merged.subjects) ? merged.subjects.length : 0;
        merged.subjectCount = n;
      }

      const content = this.study && this.study.content ? this.study.content : {};
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
        (this.study && this.study.content && this.study.content.study_data) || {};

      const incoming = schema || {};

      //  Preserve current keys (assignmentMethod, skipSubjectCreationNow, etc.)
      // Overlay schema, then normalize known parts.
      const normalized = {
        ...current,
        ...incoming,

        // merge nested study object instead of replacing it
        study: {
          ...(current.study || {}),
          ...(incoming.study || {}),
        },

        subjects:
          Array.isArray(incoming.subjects) && incoming.subjects.length
            ? incoming.subjects
            : Array.isArray(current.subjects)
            ? current.subjects
            : [],

        visits:
          Array.isArray(incoming.visits) && incoming.visits.length
            ? incoming.visits
            : Array.isArray(current.visits)
            ? current.visits
            : [],

        groups:
          Array.isArray(incoming.groups) && incoming.groups.length
            ? incoming.groups
            : Array.isArray(current.groups)
            ? current.groups
            : [],

        selectedModels: Array.isArray(incoming.selectedModels)
          ? incoming.selectedModels
          : Array.isArray(current.selectedModels)
          ? current.selectedModels
          : [],

        assignments: Array.isArray(incoming.assignments)
          ? incoming.assignments
          : Array.isArray(current.assignments)
          ? current.assignments
          : [],
      };

      //  subjectCount: keep schema value if valid, else keep current, else derive
      if (Number.isFinite(incoming.subjectCount)) {
        normalized.subjectCount = incoming.subjectCount;
      } else if (Number.isFinite(current.subjectCount)) {
        normalized.subjectCount = current.subjectCount;
      } else {
        normalized.subjectCount = Array.isArray(normalized.subjects) ? normalized.subjects.length : 0;
      }

      if (!this.study) {
        this.study = { metadata: {}, content: { study_data: normalized } };
      } else if (!this.study.content) {
        this.study.content = { study_data: normalized };
      } else {
        this.study.content.study_data = normalized;
      }

      this.initializeEntryData();
      this.prepareSubjectGroupIndexMap();
      this.prepareAssignmentsLookup();
      this.buildStatusCache();
    },

        async loadTemplateForSelectedVersion() {
      const studyId = this.study?.metadata?.id;
      if (!studyId || !this.selectedVersion) return;

      const currentSubjects = Array.isArray(this.study?.content?.study_data?.subjects)
        ? this.study.content.study_data.subjects
        : [];
      const currentSubjectCount = Number.isFinite(this.study?.content?.study_data?.subjectCount)
        ? this.study.content.study_data.subjectCount
        : currentSubjects.length;

      if (this.templateCache.has(this.selectedVersion)) {
        const cached = this.templateCache.get(this.selectedVersion);
        this.applyTemplateSchema({
          ...cached,
          subjects: currentSubjects,
          subjectCount: currentSubjectCount,
        });
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

        this.applyTemplateSchema({
          ...rawSchema,
          subjects: currentSubjects.length ? currentSubjects : (rawSchema.subjects || []),
          subjectCount: currentSubjects.length ? currentSubjectCount : rawSchema.subjectCount,
        });
      } catch (e) {
        console.error("[Entry] loadTemplateForSelectedVersion error", e);
      }
    },

    async onVersionChange() {
      this.hydrateCache.clear();
      await this.loadTemplateForSelectedVersion();

      if (!this.showSelection) {
        await this.loadCurrentSlotState();
      } else {
        this.applyVersionView();
      }

      const nS = this.numberOfSubjects;
      const nV = this.visitList.length;
      if (this.currentSubjectIndex == null || this.currentSubjectIndex >= nS) this.currentSubjectIndex = Math.min(0, nS - 1);
      if (this.currentVisitIndex == null || this.currentVisitIndex >= nV) this.currentVisitIndex = Math.min(0, nV - 1);
      this.selectedVisitIndex = this.visitList.length > this.VISIT_THRESHOLD ? 0 : -1;
    },

    rebuildEntriesIndex() {
  const m = new Map();

  for (const e of this.existingEntries || []) {
    const key = `${e.subject_index}|${e.visit_index}|${e.group_index}`;
    const arr = m.get(key) || [];
    arr.push(e);
    m.set(key, arr);
  }

  const tsNum = (x) => {
    const a = x?.updated_at ? Date.parse(x.updated_at) : NaN;
    if (Number.isFinite(a)) return a;
    const b = x?.created_at ? Date.parse(x.created_at) : NaN;
    if (Number.isFinite(b)) return b;
    return 0;
  };

  for (const [, arr] of m) {
    arr.sort((a, b) => {
      const fv = Number(b.form_version || 0) - Number(a.form_version || 0);
      if (fv !== 0) return fv;

      const t = tsNum(b) - tsNum(a);
      if (t !== 0) return t;

      return Number(b.id || 0) - Number(a.id || 0);
    });
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
        const g = this.subjectToGroupIdx[s];
        if (g == null || g < 0) continue;
        for (const v of vIndices) this.hydrateCell(s, v, g);
      }
    },

    sectionDictKey(sectionObj) {
      return sectionObj?.title ?? "";
    },
    fieldDictKey(fieldObj, fallbackIndex) {
      return (
        fieldObj?.id ||
        fieldObj?._id ||
        fieldObj?.name ||
        fieldObj?.field_id ||
        fieldObj?.uid ||
        fieldObj?.key ||
        fieldObj?.label ||
        fieldObj?.title ||
        `f${fallbackIndex}`
      );
    },
    arrayToDict(sectionFieldArray) {
      const out = {};
      (this.selectedModels || []).forEach((sec, sIdx) => {
        const sKey = this.sectionDictKey(sec);
        const fields = sec?.fields || [];
        const row = Array.isArray(sectionFieldArray?.[sIdx]) ? sectionFieldArray[sIdx] : [];
        const inner = {};

        fields.forEach((f, fIdx) => {
          const fKey = this.fieldDictKey(f, fIdx); //  now resolves to f.id when present
          inner[fKey] = row[fIdx] != null ? row[fIdx] : this.defaultForField(f);
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
        getValueFromSectionDict(secObj, field, fIdx) {
      if (!secObj || typeof secObj !== "object") return undefined;

      const candidates = [
        field?.id,
        field?._id,
        field?.field_id,
        field?.uid,
        field?.key,
        field?.name,
        field?.label,
        field?.title,
        `f${fIdx}`,
      ].filter(Boolean);

      for (const k of candidates) {
        if (Object.prototype.hasOwnProperty.call(secObj, k)) {
          return secObj[k];
        }
      }

      return undefined;
    },

    dictToArray(dataDict) {
      return (this.selectedModels || []).map((sec) => {
        const sKey = this.sectionDictKey(sec);
        const inner = (dataDict && typeof dataDict === "object") ? dataDict[sKey] : undefined;

        return (sec.fields || []).map((f, fIdx) => {
          // Try multiple candidate keys
          const candidates = [
            f?.id,
            f?._id,
            f?.field_id,
            f?.uid,
            f?.key,
            f?.name,
            f?.label,
            f?.title,
            `f${fIdx}`,
          ].filter(Boolean);

          let v = undefined;
          if (inner && typeof inner === "object") {
            for (const k of candidates) {
              if (Object.prototype.hasOwnProperty.call(inner, k)) {
                v = inner[k];
                break;
              }
            }
          }

          // Checkbox must become boolean for FieldCheckbox
          if (String(f?.type || "").toLowerCase() === "checkbox") {
            if (v === undefined) return false;
            return v === true || v === 1 || v === "1" || v === "true";
          }

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
        this.runCalculationsForCell(s, v, g, null, null);
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
        this.runCalculationsForCell(s, v, g, null, null);
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
      this.skipFlags[s][v][g] = this.normalizeSkipFlagsShape(storedSkips);

      this.hydrateCache.set(cacheKey, {
        dataArr: this.entryData[s][v][g],
        skipFlags: this.skipFlags[s][v][g],
        id: best.id,
      });

      this.runCalculationsForCell(s, v, g, null, null);
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
      this.onRuntimeFieldChanged(mIdx, fIdx);
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
      this.onRuntimeFieldChanged(mIdx, fIdx);
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
              if (t !== cur) {
                this.setDeepValue(
                  this.currentSubjectIndex,
                  this.currentVisitIndex,
                  this.currentGroupIndex,
                  mIdx,
                  fIdx,
                  t
                );
                this.onRuntimeFieldChanged(mIdx, fIdx);
              }
            }
          });
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
          `/forms/shared-api/${token}`
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
        this.ensureSlot(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex);
        this.runAllCalculationsForCurrentCell();
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
          {
            headers: { Authorization: `Bearer ${this.token}` },
            params: { current_only: true },
          }
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
      if (t === "table") {
      if (
          !ignoreDefaults &&
          Object.prototype.hasOwnProperty.call(c, "defaultValue") &&
          c.defaultValue != null
        ) {
          return c.defaultValue;
        }
        if (
          !ignoreDefaults &&
          Object.prototype.hasOwnProperty.call(f, "value") &&
          f.value != null
        ) {
          return f.value;
        }
        return [];
      }
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
          if (this.isCalculatedRuntimeField(mIdx, fIdx)) {
            this.clearError(mIdx, fIdx);
            this.clearCalcWarningFor(mIdx, fIdx);
            return;
          }
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
          this.clearCalcWarningFor(mIdx, fIdx);
        });
      });
      this.runAllCalculationsForCurrentCell();
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
      this.calcWarnings = {};
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
        const raw = (s.group || "");
        const name = String(raw).trim();
        if (!name) return -1;
        const low = name.toLowerCase();
        const gi = this.groupList.findIndex(
          (g) => (g.name || "").trim().toLowerCase() === low
        );
        return gi >= 0 ? gi : -1;
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
      const nextMap = new Map();
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
        const g = this.subjectToGroupIdx[s];

        if (g == null || g < 0) {
          for (const v of vIndices) nextMap.set(`${s}|${v}`, "none");
          continue;
        }

        for (const v of vIndices) {
          const e = this.getBestEntryFor(s, v, g);
          const key = `${s}|${v}`;

          if (!e) {
            nextMap.set(key, "none");
            continue;
          }

          const flags = e.skipped_required_flags;
          const hasSkip = !!(
            Array.isArray(flags) &&
            flags.some((row) => Array.isArray(row) && row.some((x) => !!x))
          );

          if (hasSkip) {
            nextMap.set(key, "skipped");
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
                const val = this.getValueFromSectionDict
                  ? this.getValueFromSectionDict(secObj, f, fIdx)
                  : secObj[this.fieldDictKey(f, fIdx)];

                total += 1;

                if (Array.isArray(val)) {
                  if (val.length > 0) filled += 1;
                } else if (typeof val === "boolean") {
                  if (val === true) filled += 1;
                } else if (val != null && String(val).trim() !== "") {
                  filled += 1;
                }
              });
            }
          } else if (Array.isArray(e.data)) {
            for (const mIdx of assigned) {
              const row = e.data[mIdx] || [];
              total += row.length;
              filled += row.filter((vv) => {
                if (Array.isArray(vv)) return vv.length > 0;
                if (typeof vv === "boolean") return vv === true;
                return vv != null && String(vv).trim() !== "";
              }).length;
            }
          }

          if (total === 0 || filled === 0) {
            nextMap.set(key, "none");
          } else if (filled === total) {
            nextMap.set(key, "complete");
          } else {
            nextMap.set(key, "partial");
          }
        }
      }

      this.statusMap = nextMap;
    },

    statusClassFast(sIdx, vIdx) {
      const map = this.statusMap instanceof Map ? this.statusMap : new Map();
      const s = map.get(`${sIdx}|${vIdx}`) || "none";
      return s === "skipped" ? "status-skipped" : `status-${s}`;
    },
    async loadCurrentSlotState() {
      if (this.isShared) return;

      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;

      if (s == null || v == null || g == null) return;
      if (!this.study?.metadata?.id) return;

      try {
        this.slotLoading = true;

        const params = {
          subject_index: s,
          visit_index: v,
          group_index: g,
          ...(this.safeVersionParams(this.selectedVersion) || {}),
        };

        const resp = await axios.get(
          `/forms/studies/${this.study.metadata.id}/slot-data`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
            params,
          }
        );

        this.applyLoadedSlotState(resp.data);
      } catch (e) {
        console.error("Failed to load slot state", e);
        this.showDialogMessage("Failed to load latest data for this cell.");
      } finally {
        this.slotLoading = false;
      }
    },

    applyLoadedSlotState(slot) {
      const s = Number(slot?.subject_index);
      const v = Number(slot?.visit_index);
      const g = Number(slot?.group_index);

      if (!Number.isInteger(s) || !Number.isInteger(v) || !Number.isInteger(g)) return;

      this.ensureSlot(s, v, g);

      const arr = this.dictToArray(slot?.data || {});
      const skips = this.normalizeSkipFlagsShape(slot?.skipped_required_flags);

      this.entryData[s][v][g] = arr;
      this.skipFlags[s][v][g] = skips;
      this.entryIds[s][v][g] = slot?.entry_id || null;
      this.currentRevisionToken = String(slot?.revision_token || "");

      const cacheKey = `${s}|${v}|${g}|${this.selectedVersion}`;
      this.hydrateCache.set(cacheKey, {
        dataArr: arr,
        skipFlags: skips,
        id: slot?.entry_id || null,
      });

      this.runCalculationsForCell(s, v, g, null, null);
    },

    async reloadLatestAfterConflict(latest) {
      if (!latest) return;
      this.applyLoadedSlotState(latest);
      await this.$nextTick();
      this.validationErrors = {};
      this.calcWarnings = {};
    },

    async fetchRevisionTokenForSlot(s, v, g, versionOverride = null) {
      const params = {
        subject_index: s,
        visit_index: v,
        group_index: g,
        ...(this.safeVersionParams(versionOverride != null ? versionOverride : this.selectedVersion) || {}),
      };

      const resp = await axios.get(
        `/forms/studies/${this.study.metadata.id}/slot-data`,
        {
          headers: { Authorization: `Bearer ${this.token}` },
          params,
        }
      );

      return resp?.data || null;
    },
    async selectCell(sIdx, vIdx) {
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

      const g = this.subjectToGroupIdx[this.currentSubjectIndex];

      if (g == null || g < 0) {
        this.openGroupAssignDialog(this.currentSubjectIndex, this.currentVisitIndex);
        return;
      }

      this.currentGroupIndex = g;

      this.ensureSlot(
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex
      );
      this.prepareAssignmentsLookup();

      this.showSelection = false;
      this.validationErrors = {};
      this.calcWarnings = {};

      this.visitLoading = true;
      await this.loadCurrentSlotState();
      this.runAllCalculationsForCurrentCell();
      this.visitLoading = false;
    },

    backToSelection() {
      if (this.isShared) return;
      this.buildStatusCache();
      this.showSelection = true;
      this.showDetails = false;
      this.currentSubjectIndex = null;
      this.currentVisitIndex = null;
      this.currentGroupIndex = 0;
      this.validationErrors = {};
      this.calcWarnings = {};
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

      // Hidden conditional fields must not be validated
      if (!this.isFieldVisible(mIdx, fIdx)) {
        this.clearError(mIdx, fIdx);
        return true;
      }

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

        if (def.type === "table") {
          const rows = val?.rows;
          return !Array.isArray(rows) || rows.length === 0;
        }

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

      if (def.type === "table") {
          const childOk = this.validateTableChild(mIdx, fIdx);
          const tableState = this.getTableValidationState(mIdx, fIdx);

          if (!childOk) {
            this.setError(
              mIdx,
              fIdx,
              tableState?.message || `${label} contains invalid cells.`
            );
            return false;
          }

          // If child validation ran but parent still has no state, treat as invalid
          if (!tableState) {
            this.setError(
              mIdx,
              fIdx,
              `${label} contains invalid cells.`
            );
            return false;
          }

          if (!tableState.valid) {
            this.setError(
              mIdx,
              fIdx,
              tableState.message || `${label} contains invalid cells.`
            );
            return false;
          }

          return true;
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
          if (n < min || n > max) {
            this.setError(mIdx, fIdx, `${label} must be between ${min} and ${max}.`);
            return false;
          }
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
          const min = Number.isFinite(+cons.min) ? Math.round(+cons.min) : 1;
          const max = Number.isFinite(+cons.max) ? Math.round(+cons.max) : 5;
          if (n < min || n > max || Math.round(n) !== n) {
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
        const { valid, message } = validateFieldValue(this.ajv, def, val);
        if (!valid) {
          this.setError(mIdx, fIdx, message || `${label} is invalid.`);
          return false;
        }
      }

      if (def.type === "date" && val) {
        const cons = (this.selectedModels[mIdx].fields[fIdx] || {}).constraints || {};
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
        const cons = (this.selectedModels[mIdx].fields[fIdx] || {}).constraints || {};
        const toSec = (s) => {
          const mm = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(String(s));
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
        this.selectedModels[mIdx].fields.forEach((_, fIdx) => {
          this.clearError(mIdx, fIdx);
        });
      });

      let ok = true;
      this.assignedModelIndices.forEach((mIdx) => {
        if (!this.hasVisibleFieldsInSection(mIdx)) return;

        this.selectedModels[mIdx].fields.forEach((_, fIdx) => {
          if (!this.isFieldVisible(mIdx, fIdx)) {
            this.clearError(mIdx, fIdx);
            return;
          }

          const r = this.validateField(mIdx, fIdx);
          ok = ok && r;
        });
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
      if (!this.hasVisibleFieldsInSection(mIdx)) return;

      (section.fields || []).forEach((f, fIdx) => {
        const c = f?.constraints || {};
        if (!c.required) return;
        if (!this.isFieldVisible(mIdx, fIdx)) return;
        if (this.skipFlags[s]?.[v]?.[g]?.[mIdx]?.[fIdx]) return;

        const val = this.entryData[s][v][g][mIdx][fIdx];
          const empty =
            f.type === "checkbox"
              ? val !== true
              : f.type === "file"
              ? c.allowMultipleFiles
                ? !(Array.isArray(val) && val.length > 0)
                : !val || (val.source === "url" ? !(val.url && String(val.url).trim()) : !(val.name && Number.isFinite(Number(val.size))))
              : Array.isArray(val)
              ? val.length === 0
              : val == null || (typeof val === "string" && val.trim() === "");
          if (empty) {
            items.push({
              key: this.errorKey(mIdx, fIdx),
              id: this.fieldId(mIdx, fIdx),
              sectionIndex: mIdx,
              fieldIndex: fIdx,
              sectionTitle: section.title || `Section ${mIdx + 1}`,
              fieldLabel: f.label || f.name || `Field ${fIdx + 1}`,
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

          const pendingArr = Array.isArray(this.pendingFiles[key]) ? this.pendingFiles[key] : this.pendingFiles[key] ? [this.pendingFiles[key]] : [];
          const matchFile = (meta) =>
            pendingArr.find(
              (f) =>
                f &&
                meta &&
                f.name === meta.name &&
                Number(f.size) === Number(meta.size) &&
                (f.lastModified ? f.lastModified === meta.lastModified : true)
            );

          const base = this.isShared ? `/forms/shared/${this.shareToken}` : `/forms/studies/${studyId}`;

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
                fd.append("description", def.label || def.name || "");
                fd.append("modalities_json", modalitiesJson);
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
                      "Content-Type": "multipart/form-data",
                    };
                const resp = await axios.post(`${base}/files`, fd, {
                  headers,
                  params: { audit_label: "Upload File (Local)" },
                });
                const saved = resp?.data || {};
                items[i] = {
                  ...it,
                  dbId: saved.id,
                  file_path: saved.file_path,
                  storage_option: saved.storage_option || (this.isShared ? "bids" : "local"),
                  file_name: saved.file_name || it.name,
                };
              } else if (it.source === "url" && it.url) {
                const fd = new FormData();
                fd.append("url", it.url);
                fd.append("description", def.label || def.name || "");
                fd.append("modalities_json", modalitiesJson);
                const headers = this.isShared ? {} : { Authorization: `Bearer ${this.token}` };
                const resp = await axios.post(`${base}/files/url`, fd, {
                  headers,
                  params: { audit_label: "Upload - File (URL)" },
                });
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
            this.setDeepValue(s, v, g, mIdx, fIdx, items);
            delete this.pendingFiles[key];
          } else {
            if (!val) continue;

            if (val.source === "local" && pendingArr[0] instanceof File) {
              const file = pendingArr[0];
              const fd = new FormData();
              fd.append("uploaded_file", file);
              fd.append("description", def.label || def.name || "");
              fd.append("modalities_json", modalitiesJson);
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
                    "Content-Type": "multipart/form-data",
                  };
              const resp = await axios.post(`${base}/files`, fd, {
                headers,
                params: { audit_label: "Upload - File (Local)" },
              });
              const saved = resp?.data || {};
              this.setDeepValue(s, v, g, mIdx, fIdx, {
                ...val,
                dbId: saved.id,
                file_path: saved.file_path,
                storage_option: saved.storage_option || (this.isShared ? "bids" : "local"),
                file_name: saved.file_name || val.name,
              });
              delete this.pendingFiles[key];
            }

            if (val.source === "url" && val.url) {
              const fd = new FormData();
              fd.append("url", val.url);
              fd.append("description", def.label || def.name || "");
              fd.append("modalities_json", modalitiesJson);
              const headers = this.isShared ? {} : { Authorization: `Bearer ${this.token}` };
              const resp = await axios.post(`${base}/files/url`, fd, {
                headers,
                params: { audit_label: "Upload - File (URL)" },
              });
              const saved = resp?.data || {};
              this.setDeepValue(s, v, g, mIdx, fIdx, {
                ...val,
                dbId: saved.id,
                file_path: saved.file_path,
                storage_option: "url",
                file_name: saved.file_name || "",
              });
            }
          }
        }
      }
    },

    async submitData() {
  if (!this.canEdit) {
    this.showDialogMessage("This shared link is view-only.");
    return;
  }

  this.applyTransformsForSection();
  this.runAllCalculationsForCurrentCell();

  const ok = this.validateCurrentSection();
  const tableFieldsInvalid = this.assignedModelIndices.some((mIdx) => {
  const fields = this.selectedModels?.[mIdx]?.fields || [];
  return fields.some((field, fIdx) => {
    if (field?.type !== "table") return false;
    if (!this.isFieldVisible(mIdx, fIdx)) return false;
    return !this.validateField(mIdx, fIdx);
        });
    });
  const blocking = Object.entries(this.validationErrors).filter(([k, msg]) => {
    if (!msg) return false;
    const idx = this.parseKey(k);
    if (!idx) return true;
    const { s, v, g, m, f } = idx;
    const isSkipped = !!(this.skipFlags[s]?.[v]?.[g]?.[m]?.[f]);
    if (isSkipped) return false;
    return !/ is required\.$/.test(msg);
  });

  if ((!ok && blocking.length) || tableFieldsInvalid) {
      this.showDialogMessage("Please fix validation errors before saving.");
      return;
    }

  const requiredFailures = this.computeRequiredFailures();
  if (requiredFailures.length) {
    this.skipCandidates = requiredFailures;
    this.skipSelections = requiredFailures.reduce((acc, it) => {
      acc[it.key] = false;
      return acc;
    }, {});
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

  const s = this.currentSubjectIndex,
    v = this.currentVisitIndex,
    g = this.currentGroupIndex;
  this.ensureSlot(s, v, g);

  const dictData = this.arrayToDict(this.entryData[s][v][g]);

  const rawSkipFlags = this.normalizeSkipFlagsShape(this.skipFlags[s][v][g]);
  this.skipFlags[s][v][g] = rawSkipFlags;

  const flagsPayload = this.isShared
      ? this.flagsArrayToDict(rawSkipFlags)
      : rawSkipFlags;

  const hasAnySkip = !!(
    Array.isArray(rawSkipFlags) && rawSkipFlags.some((row) => Array.isArray(row) && row.some((x) => !!x))
  );

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
      const auditLabel = hasAnySkip ? "Shared link data Entry (Skipped Required)" : "Shared link data Entry";
      const resp = await axios.post(`/forms/shared/${this.shareToken}/data`, payload, {
        params: { audit_label: auditLabel },
      });

      const saved = {
        id: resp?.data?.id,
        study_id: payload.study_id,
        subject_index: s,
        visit_index: v,
        group_index: g,
        data: dictData,
        skipped_required_flags: resp?.data?.skipped_required_flags ?? rawSkipFlags,
        form_version: resp?.data?.form_version ?? this.selectedVersion,
        created_at: resp?.data?.created_at ?? new Date().toISOString(),
      };
      (this.existingEntries = this.existingEntries || []).push(saved);

      this.showDialogMessage("Data saved successfully.");
      this.rebuildEntriesIndex();
      this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
      this.applyVersionView();
      this.updateStatusCacheFor(s, v, g);
      return;
    }

    const headers = {
      headers: { Authorization: `Bearer ${this.token}` },
    };
    const existingId = this.entryIds[s][v][g];

    if (!this.currentRevisionToken) {
      const slot = await this.fetchRevisionTokenForSlot(s, v, g, this.selectedVersion);
      this.currentRevisionToken = String(slot?.revision_token || "");
    }

    if (existingId) {
      const auditLabel = hasAnySkip ? "Update/Edit Data Entry (Skipped Required)" : "Update/Edit Data Entry";
      const resp = await axios.put(
        `/forms/studies/${this.study.metadata.id}/data_entries/${existingId}`,
        payload,
        {
          ...headers,
          params: {
            audit_label: auditLabel,
            expected_revision_token: this.currentRevisionToken,
          },
        }
      );

      this.showDialogMessage("Data updated successfully.");
      const idx = this.existingEntries.findIndex((x) => x.id === existingId);
      if (idx >= 0) this.existingEntries.splice(idx, 1, resp.data);
    } else {
      const params = this.safeVersionParams(this.selectedVersion);
      const auditLabel = hasAnySkip ? "New Data Entry (Skipped Required)" : params ? "New Data Entry (Versioned)" : "New Data Entry";
      const resp = await axios.post(
        `/forms/studies/${this.study.metadata.id}/data`,
        payload,
        {
          ...headers,
          params: {
            ...(params || {}),
            audit_label: auditLabel,
            expected_revision_token: this.currentRevisionToken,
          },
        }
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
        skipped_required_flags: resp?.data?.skipped_required_flags ?? rawSkipFlags,
        form_version: resp?.data?.form_version ?? this.selectedVersion,
        created_at: resp?.data?.created_at ?? new Date().toISOString(),
      };
      (this.existingEntries = this.existingEntries || []).push(saved);
      this.showDialogMessage("Data saved successfully.");
    }

    const latestSlot = await this.fetchRevisionTokenForSlot(s, v, g, this.selectedVersion);
    if (latestSlot) {
      this.applyLoadedSlotState(latestSlot);
    }

    this.rebuildEntriesIndex();
    this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
    this.applyVersionView();
    this.updateStatusCacheFor(s, v, g);
  } catch (err) {
    console.error(err);

    if (err?.response?.status === 409) {
      const latest = err?.response?.data?.detail?.latest || null;
      if (latest) {
        await this.reloadLatestAfterConflict(latest);
      }
      this.showDialogMessage(
        "This entry was changed in the backend after you opened it. Latest values were reloaded. Please review your values and save again."
      );
      return;
    }

    this.showDialogMessage("Failed to save data. Check console for details.");
  }
},

        updateStatusCacheFor(s, v, g) {
      const e = this.getBestEntryFor(s, v, g);
      const key = `${s}|${v}`;

      const nextMap = new Map(this.statusMap || []);

      if (!e) {
        nextMap.set(key, "none");
        this.statusMap = nextMap;
        return;
      }

      const flags = e.skipped_required_flags;
      const hasSkip = !!(
        Array.isArray(flags) &&
        flags.some((row) => Array.isArray(row) && row.some((x) => !!x))
      );

      if (hasSkip) {
        nextMap.set(key, "skipped");
        this.statusMap = nextMap;
        return;
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
            const val = this.getValueFromSectionDict
              ? this.getValueFromSectionDict(secObj, f, fIdx)
              : secObj[this.fieldDictKey(f, fIdx)];

            total += 1;

            if (Array.isArray(val)) {
              if (val.length > 0) filled += 1;
            } else if (typeof val === "boolean") {
              if (val === true) filled += 1;
            } else if (val != null && String(val).trim() !== "") {
              filled += 1;
            }
          });
        }
      } else if (Array.isArray(e.data)) {
        for (const mIdx of assigned) {
          const row = e.data[mIdx] || [];
          total += row.length;
          filled += row.filter((vv) => {
            if (Array.isArray(vv)) return vv.length > 0;
            if (typeof vv === "boolean") return vv === true;
            return vv != null && String(vv).trim() !== "";
          }).length;
        }
      }

      if (total === 0 || filled === 0) {
        nextMap.set(key, "none");
      } else if (filled === total) {
        nextMap.set(key, "complete");
      } else {
        nextMap.set(key, "partial");
      }

      this.statusMap = nextMap;
    },

    confirmSkipSelection() {
      const s = this.currentSubjectIndex,
        v = this.currentVisitIndex,
        g = this.currentGroupIndex;
      this.skipCandidates.forEach((it) => {
        const on = !!this.skipSelections[it.key];
        this.setDeepSkip(s, v, g, it.sectionIndex, it.fieldIndex, on);
        if (on) this.clearError(it.sectionIndex, it.fieldIndex);
      });
      this.showSkipDialog = false;
      this.submitData();
    },

    confirmSkipSelectionFromDialog(nextSelections) {
      this.skipSelections = { ...(nextSelections || {}) };
      this.confirmSkipSelection();
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

      const available = (this.selectedModels || [])
        .map((sec, mIdx) => ({ sec, mIdx }))
        .filter(({ mIdx }) => !!this.assignments?.[mIdx]?.[vIdx]?.[gIdx])
        .map(({ sec }) => ({
          id: String(sec?._id || sec?.id || "").trim(),
          title: sec?.title || "Untitled Section"
        }))
        .filter(s => s.id);

      this.shareConfig = {
        permission: "view",
        maxUses: 1,
        expiresInDays: 7,
        allowed_section_ids: available.map(x => x.id)
      };

      this.generatedLink = "";
      this.copyStatus = "";
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
        allowed_section_ids: this.shareConfig.allowed_section_ids || []
      };
      try {
        const resp = await axios.post("/forms/share-link/", payload, {
          headers: { Authorization: `Bearer ${this.token}` },
          params: { audit_label: "Create - Sharable Link" },
        });
        this.generatedLink = resp.data.link;
        this.copyStatus = "";
        this.showShareDialog = true;
      } catch (err) {
        this.generatedLink = "";
        this.copyStatus = "";
        if (err.response?.status === 403) this.permissionError = true;
      }
    },

    openSubjectDialog() {
      if (this.isShared) {
        this.showDialogMessage("Subjects can only be added from the main study, not from shared links.");
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

      const last = String(subjects[subjects.length - 1].id || "").trim();
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
          .map((s) => String(s.id || s.subject_id || "").trim())
          .filter(Boolean)
      );

      const { prefix, startIndex, width } = this.inferSubjectIdPattern();
      const drafts = [];

      let num = startIndex;
      while (drafts.length < count) {
        const id = `${prefix}${String(num).padStart(width, "0")}`;
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
      const g = this.groupList[index % this.groupList.length];
      return g && g.name ? g.name : null;
    },

    applyAssignmentMethod() {
      if (!this.subjectDrafts.length || !this.groupList.length) return;

      const method = String(this.assignmentMethodDraft || "").toLowerCase();

      if (method === "random") {
        this.subjectDrafts = this.subjectDrafts.map((s) => {
          const idx = Math.floor(Math.random() * this.groupList.length);
          const g = this.groupList[idx];
          return {
            ...s,
            group: g && g.name ? g.name : null,
          };
        });
      } else if (method === "manual") {
        this.subjectDrafts = this.subjectDrafts.map((s, idx) => {
          if (s.group) return s;
          return {
            ...s,
            group: this.defaultGroupForIndex(idx),
          };
        });
      } else if (method === "skip") {
        this.subjectDrafts = this.subjectDrafts.map((s, idx) => ({
          ...s,
          group: s.group || this.defaultGroupForIndex(idx),
        }));
      }
    },

    async saveNewSubjects() {
      if (this.isShared) {
        this.subjectDialogError = "Subjects cannot be added from a shared link.";
        return;
      }

      this.subjectDialogError = "";

      if (!this.subjectDrafts.length) {
        this.subjectDialogError = "Please configure at least one subject.";
        return;
      }

      const cleanedDrafts = this.subjectDrafts.map((s) => ({
        id: String(s.id || "").trim(),
        group: String(s.group || "").trim(),
      }));

      for (const s of cleanedDrafts) {
        if (!s.id) {
          this.subjectDialogError = "Each subject must have an ID.";
          return;
        }
        if (!s.group) {
          this.subjectDialogError = "Each subject must be assigned to a group.";
          return;
        }
      }

      const seen = new Set();
      for (const s of cleanedDrafts) {
        if (seen.has(s.id)) {
          this.subjectDialogError = "Duplicate subject IDs in the new subjects.";
          return;
        }
        seen.add(s.id);
      }

      const existing = this.sd.subjects || [];
      const existingIds = new Set(
        existing
          .map((s) => String(s.id || s.subject_id || "").trim())
          .filter(Boolean)
      );
      for (const s of cleanedDrafts) {
        if (existingIds.has(s.id)) {
          this.subjectDialogError = `Subject ID "${s.id}" already exists.`;
          return;
        }
      }

      const merged = [...existing, ...cleanedDrafts];

      const currentStudyData = (this.study && this.study.content && this.study.content.study_data) || {};
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
        await axios.put(`/forms/studies/${this.study.metadata.id}`, payload, {
          headers: { Authorization: `Bearer ${this.token}` },
          params: { audit_label: "New Subjects (Add)" },
        });

                if (this.study && this.study.content && this.study.content.study_data) {
          this.study.content.study_data = {
            ...this.study.content.study_data,
            subjects: merged,
            subjectCount: merged.length,
          };
        }

        // very important: clear stale template cache before reloading
        this.templateCache.clear();
        this.hydrateCache.clear();
        this.currentRevisionToken = "";

        await this.loadVersions(this.study.metadata.id);
        this.selectedVersion =
          this.studyVersions[this.studyVersions.length - 1]?.version || 1;

        await this.loadTemplateForSelectedVersion();

        // force fresh subjects into current study state even if template endpoint
        // returns an older schema snapshot without the newly added subjects
        if (this.study && this.study.content && this.study.content.study_data) {
          this.study.content.study_data = {
            ...this.study.content.study_data,
            subjects: merged,
            subjectCount: merged.length,
          };
        }

        this.prepareSubjectGroupIndexMap();
        this.prepareAssignmentsLookup();

        this.initializeEntryData();
        await this.loadExistingEntries(this.study.metadata.id);
        this.buildStatusCache();

        this.showSubjectDialog = false;
        this.subjectDrafts = [];
        this.subjectCountDraft = 1;
        this.assignmentMethodDraft = "Random";

        await this.$nextTick();

        this.showDialogMessage("Subjects added successfully.");
      } catch (e) {
        console.error("Failed to add subjects", e);
        this.subjectDialogError = "Failed to save subjects. Please try again.";
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
    openGroupAssignDialog(subjectIndex, visitIndex) {
      this.groupAssignSubjectIndex = subjectIndex;
      this.groupAssignVisitIndex = visitIndex;

      this.groupAssignScope = "one";
      this.groupAssignSelectedGroup = this.groupList?.[0]?.name || "";
      this.groupAssignError = "";

      const subjects = this.study?.content?.study_data?.subjects || [];
      const drafts = [];

      for (let i = 0; i < subjects.length; i++) {
        const s = subjects[i] || {};
        const id = String(s.id || s.subject_id || "").trim();
        const grp = String(s.group || "").trim();
        if (!grp) {
          drafts.push({
            index: i,
            id,
            group: this.groupList?.[0]?.name || "",
          });
        }
      }

      this.groupAssignDrafts = drafts;
      this.showGroupAssignDialog = true;
    },

    closeGroupAssignDialog() {
      this.showGroupAssignDialog = false;
      this.groupAssignError = "";
      this.groupAssignSubjectIndex = null;
      this.groupAssignVisitIndex = null;
    },

    async saveGroupAssignment() {
      if (this.isShared) {
        this.groupAssignError = "Group assignment cannot be done from a shared link.";
        return;
      }

      const groupName = String(this.groupAssignSelectedGroup || "").trim();
      if (!groupName) {
        this.groupAssignError = "Please select a group.";
        return;
      }

      const sd = this.study?.content?.study_data || {};
      const subjects = Array.isArray(sd.subjects) ? [...sd.subjects] : [];

      if (!subjects.length) {
        this.groupAssignError = "No subjects found.";
        return;
      }

      const scope = String(this.groupAssignScope || "one").toLowerCase();
      const sIdx = Number(this.groupAssignSubjectIndex);

      if (!Number.isInteger(sIdx) || sIdx < 0 || sIdx >= subjects.length) {
        this.groupAssignError = "Invalid subject.";
        return;
      }

      let updatedSubjects;

      if (scope === "all") {
        const drafts = Array.isArray(this.groupAssignDrafts) ? this.groupAssignDrafts : [];

        if (!drafts.length) {
          this.groupAssignError = "No unassigned subjects found.";
          return;
        }

        for (const d of drafts) {
          const g = String(d.group || "").trim();
          if (!g) {
            this.groupAssignError = "Each listed subject must be assigned to a group.";
            return;
          }
        }

        const map = new Map(drafts.map((d) => [Number(d.index), String(d.group || "").trim()]));

        updatedSubjects = subjects.map((s, idx) => {
          const cur = String(s.group || "").trim();
          if (cur) return s;
          const chosen = map.get(idx);
          return chosen ? { ...s, group: chosen } : s;
        });
      } else {
        updatedSubjects = subjects.map((s, idx) => (idx === sIdx ? { ...s, group: groupName } : s));
      }

      const updatedStudyData = {
        ...sd,
        subjects: updatedSubjects,
        subjectCount: updatedSubjects.length,
      };

      const payload = {
        study_metadata: this.study.metadata,
        study_content: { study_data: updatedStudyData },
      };

      this.savingGroupAssign = true;
      this.groupAssignError = "";

      try {
        await axios.put(`/forms/studies/${this.study.metadata.id}`, payload, {
          headers: { Authorization: `Bearer ${this.token}` },
          params: { audit_label: scope === "all" ? "Update - Subject Groups (All)" : "Update - Subject Group" },
        });

        this.study.content.study_data.subjects = updatedSubjects;
        this.study.content.study_data.subjectCount = updatedSubjects.length;

        this.prepareSubjectGroupIndexMap();

        const g = this.subjectToGroupIdx[sIdx];
        if (g == null || g < 0) {
          this.groupAssignError = "Group assignment failed. Please try again.";
          return;
        }

        this.currentSubjectIndex = sIdx;
        this.currentVisitIndex = Number(this.groupAssignVisitIndex) || 0;
        this.currentGroupIndex = g;

        this.ensureSlot(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex);
        this.prepareAssignmentsLookup();

        this.showSelection = false;
        this.validationErrors = {};
        this.calcWarnings = {};
        this.hydrateCell(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex);
        this.runAllCalculationsForCurrentCell();

        this.showGroupAssignDialog = false;
      } catch (e) {
        console.error("Failed to assign group", e);
        this.groupAssignError = "Failed to save group assignment. Please try again.";
      } finally {
        this.savingGroupAssign = false;
      }
    },
  },
};
</script>
<style scoped>
.selection-import-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.import-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #2563eb;
  color: #ffffff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.import-btn:hover {
  background: #1d4ed8;
}
.study-data-container {
  max-width: none;
  margin: 24px auto;
  padding: 10px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
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
.calc-warning-message {
  color: #92400e;
  font-size: 12px;
  margin-top: 4px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 8px;
}
.crumb-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.import-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #2563eb;
  color: #ffffff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.import-btn:hover {
  background: #1d4ed8;
}
</style>