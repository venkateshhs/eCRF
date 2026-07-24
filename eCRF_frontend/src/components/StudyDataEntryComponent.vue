<template>
  <div class="study-data-container" :class="{ 'is-entry-mode': !showSelection }" v-if="study">
    <!-- Back Buttons -->
    <div class="back-buttons-container" v-if="!isShared">
      <button v-if="isMergeMode" @click="closeMergeStudy" class="btn-back">
        Back to Selection
      </button>

      <template v-else>
        <button v-if="showSelection" @click="goToDashboard" class="btn-back">
          Back to Dashboard
        </button>
        <button v-else @click="requestBackToSelection" class="btn-back">
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
          <button v-if="!isMergeMode" @click="toggleDetails" class="details-toggle-btn">
            <i :class="showDetails ? icons.toggleUp : icons.toggleDown"></i>
            {{ showDetails ? "Hide Study Details" : "Show Study Details" }}
          </button>

          <button
            v-if="showSelection && !isShared && !isMergeMode"
            type="button"
            class="btn-merge-study"
            @click="openMergeStudy"
          >
            Import data from other device
          </button>

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
              <span class="details-key">{{ key }}:</span>
              <span class="details-value">{{ val }}</span>
            </li>
            </ul>
          </div>

          <div v-if="!showSelection" class="details-block">
            <strong>Visit Info:</strong>
            <ul>
              <li v-for="[key, val] in Object.entries(visitList[currentVisitIndex] || {})" :key="key">
                  <span class="details-key">{{ key }}:</span>
                  <span class="details-value">{{ val }}</span>
                </li>
            </ul>
          </div>
        </div>
      </div>

      <hr />
    </div>

    <!-- Selection -->
    <template v-if="showSelection && !isShared">
      <div v-if="!isMergeMode" class="selection-import-bar">
        <button type="button" class="import-btn" @click="openImportDialogFromSelection">
          <i :class="icons.upload || 'fas fa-file-import'"></i>
          Import Data
        </button>
      </div>

      <SelectionMatrixView
          v-if="!isMergeMode && matrixReady"
          :key="selectionMatrixKey"
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
          :statusProgress="statusProgressFast"
          :selectedVersion="selectedVersion"
          :infoIcon="icons.info"
          :showGroupColumn="canSeeGroupColumn"
          @update:selectedVisitIndex="selectedVisitIndex = $event"
          @add-subjects="openSubjectDialog"
          @select-cell="selectCell"
          @open-status-legend="openStatusLegend"
        />

        <div v-else-if="!isMergeMode" class="loading">
          <p>Loading selection matrix…</p>
        </div>

      <section v-else class="merge-panel">
        <MergeStudy :studyId="studyId" :returnTo="`/dashboard/studies/${studyId}/add-data`" />
      </section>
    </template>

    <!-- Entry Form -->
    <div v-else class="entry-form-wrapper">
      <div class="bread-crumb">
        <div class="crumb-left">
          <strong>Study:</strong> {{ study.metadata.study_name }}
          <strong>Subject:</strong> {{ sd.subjects?.[currentSubjectIndex]?.id }}
          <strong>Visit:</strong>
            <select
              v-if="!isShared && visitList.length > 1"
              class="entry-visit-select"
              :value="currentVisitIndex"
              :disabled="visitLoading || slotLoading"
              @change="onEntryVisitSelectorChange"
            >
              <option
                v-for="(visit, visitIdx) in visitList"
                :key="'entry-visit-' + visitIdx"
                :value="visitIdx"
              >
                {{ visit.name || `Visit ${visitIdx + 1}` }}
              </option>
            </select>

            <span v-else>
              {{ visitList[currentVisitIndex]?.name }}
            </span>
          <span v-if="!isShared && selectedVersion" class="version-helper">
            Saving to Version {{ selectedVersion }}
          </span>
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

          <button
            type="button"
            class="legend-btn"
            @click="openLegendDialog"
            title="Legend / What does * mean?"
          >
            <i :class="icons.help || 'fas fa-question-circle'"></i>
          </button>
        </div>
      </div>

      <div class="entry-form-section">
        <div class="entry-title-row">
          <h2 class="entry-title">
            Enter Data for Subject: {{ sd.subjects?.[currentSubjectIndex]?.id }},
            Visit: “{{ visitList[currentVisitIndex].name }}”
          </h2>

          <div class="entry-title-actions">
            <div
              v-if="assignedModelIndices.length"
              class="entry-search"
              @focusin="openEntrySearchResults"
              @focusout="closeEntrySearchResults"
            >
              <div class="entry-search-input-wrap">
                <i class="fas fa-search entry-search-icon" aria-hidden="true"></i>
                <input
                  v-model="entrySearchQuery"
                  type="search"
                  class="entry-search-input"
                  placeholder="Search Section or Field Name"
                  aria-label="Search visible sections or fields"
                  autocomplete="off"
                  @input="onEntrySearchInput"
                  @keydown.down.prevent="moveEntrySearchSelection(1)"
                  @keydown.up.prevent="moveEntrySearchSelection(-1)"
                  @keydown.enter.prevent="selectActiveEntrySearchResult"
                  @keydown.esc.prevent="closeEntrySearchImmediately"
                />
              </div>

              <div
                v-if="showEntrySearchResults && entrySearchQuery.trim()"
                class="entry-search-results"
                role="listbox"
                aria-label="Visible section and field search results"
              >
                <button
                  v-for="(result, resultIdx) in entrySearchResults"
                  :key="result.key"
                  type="button"
                  class="entry-search-result"
                  :class="{ active: entrySearchActiveIndex === resultIdx }"
                  role="option"
                  :aria-selected="entrySearchActiveIndex === resultIdx"
                  @mouseenter="entrySearchActiveIndex = resultIdx"
                  @mousedown.prevent="selectEntrySearchResult(result)"
                >
                  <span class="entry-search-result-type">
                    {{ result.type === "section" ? "Section" : "Field" }}
                  </span>
                  <span class="entry-search-result-text">
                    <strong>{{ result.label }}</strong>
                    <small v-if="result.type === 'field'">{{ result.sectionTitle }}</small>
                  </span>
                </button>

                <div v-if="!entrySearchResults.length" class="entry-search-empty">
                  No visible sections or fields found.
                </div>
              </div>
            </div>

            <button
              v-if="assignedModelIndices.length"
              type="button"
              class="section-collapse-all-btn"
              @click="toggleAllSectionsCollapse"
              :title="allSectionsCollapsed ? 'Unfold all sections' : 'Fold all sections'"
            >
              <i :class="allSectionsCollapsed ? 'fas fa-chevron-down' : 'fas fa-chevron-up'"></i>
            </button>
          </div>
        </div>

        <div
          v-if="assignedModelIndices.length && entryProgress.total"
          class="entry-progress"
          aria-live="polite"
        >
          <div class="entry-progress-summary">
            <div>
              <strong>Data entered: {{ entryProgress.percentage }}%</strong>
              <span>
                {{ entryProgress.completed }} of {{ entryProgress.total }}
                visible data point{{ entryProgress.total === 1 ? "" : "s" }}
              </span>
            </div>

            <span v-if="entryProgress.skipped" class="entry-progress-skipped">
              {{ entryProgress.skipped }} skipped
            </span>
          </div>

          <div
            class="entry-progress-track"
            role="progressbar"
            aria-label="Visible data entered"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="entryProgress.percentage"
          >
            <div
              class="entry-progress-fill"
              :style="{ width: `${entryProgress.percentage}%` }"
            ></div>
          </div>
        </div>

        <div v-if="valueAssignmentWarnings.length" class="value-assignment-warning">
          <strong>Automatic value assignment needs review:</strong>
          <span>{{ valueAssignmentWarnings.join(" ") }}</span>
        </div>

        <div v-if="assignedModelIndices.length" class="sections-stack">
          <template v-for="mIdx in assignedModelIndices" :key="'sec-wrap-' + mIdx">
            <section
              v-if="hasVisibleFieldsInSection(mIdx)"
              :key="'sec-' + mIdx"
              class="section-card"
              :class="{
                'section-card-search-highlight': entrySearchHighlightedSectionIndex === mIdx
              }"
              :data-section-index="mIdx"
            >
              <div class="section-card-header">
                  <h3 class="section-title">
                    {{ selectedModels[mIdx].title }}
                  </h3>

                  <div class="section-header-actions">
                    <button
                      v-if="hasSectionErrors(mIdx)"
                      type="button"
                      class="section-error-btn"
                      :title="`Go to validation error in this section (${sectionErrorCount(mIdx)})`"
                      @click="goToNextErrorInSection(mIdx)"
                    >
                      <i class="fas fa-exclamation-circle"></i>
                      <span>{{ sectionErrorCount(mIdx) }}</span>
                    </button>

                    <button
                      type="button"
                      class="section-collapse-btn"
                      @click="toggleSectionCollapse(mIdx)"
                      :title="isSectionCollapsed(mIdx) ? 'Unfold section' : 'Fold section'"
                    >
                      <i :class="isSectionCollapsed(mIdx) ? 'fas fa-chevron-down' : 'fas fa-chevron-up'"></i>
                    </button>
                  </div>
              </div>

                <div
                  v-if="validationMountAllSections || !isSectionCollapsed(mIdx)"
                  v-show="!isSectionCollapsed(mIdx)"
                  class="section-card-body"
                >
                <template
                  v-for="(field, fIdx) in selectedModels[mIdx].fields"
                  :key="'f-wrap-' + mIdx + '-' + fIdx"
                >
                  <div
                    v-if="isFieldVisible(mIdx, fIdx)"
                    :key="'f-' + mIdx + '-' + fIdx"
                    class="field-card"
                    :class="{
                        'field-card-has-error': !!fieldErrors(mIdx, fIdx),
                        'field-card-error-highlight': highlightedErrorKey === errorKey(mIdx, fIdx),
                        'field-card-search-highlight': entrySearchHighlightedFieldKey === `${mIdx}-${fIdx}`,
                        'field-card-has-reminder': hasPopupReminder(mIdx, fIdx)
                      }"
                    :data-error-key="errorKey(mIdx, fIdx)"
                    :data-search-key="`${mIdx}-${fIdx}`"
                  >
                    <div class="field-card-header">
                      <label :for="fieldId(mIdx, fIdx)" class="field-label">
                          <span class="field-label-main">
                            {{ field.label || field.name || field.title }}
                          </span>

                          <span v-if="field.constraints?.required" class="required">*</span>
                          <button
                            v-if="hasConstraints(field)"
                            type="button"
                            class="field-help-inline-btn"
                            title="Field constraints"
                            @click.prevent.stop="openConstraintDialog(field)"
                          >
                            <i class="fas fa-question-circle"></i>
                          </button>
                        </label>
                        <button
                          v-if="!isShared && canShowPreviousVisitImport(field, mIdx, fIdx) && !isImportedFromPreviousVisit(mIdx, fIdx)"
                          type="button"
                          class="field-icon-btn"
                          title="Import from previous visits"
                          @click="openPreviousVisitImportDialog(mIdx, fIdx)"
                        >
                          <i :class="icons.copy || 'fas fa-copy'"></i>
                        </button>

                        <button
                          v-if="!isShared && canShowPreviousVisitImport(field, mIdx, fIdx) && isImportedFromPreviousVisit(mIdx, fIdx)"
                          type="button"
                          class="field-icon-btn field-icon-btn-active"
                          :title="`Imported from ${importedPreviousVisitLabel(mIdx, fIdx)}. Click to make editable.`"
                          @click="unlockImportedPreviousVisit(mIdx, fIdx)"
                          :disabled="!canEdit"
                        >
                          <i :class="icons.lock || 'fas fa-lock'"></i>
                        </button>
                      </div>


                    <div v-if="field.constraints?.helpText" class="field-help-box">
                      {{ field.constraints.helpText }}
                    </div>

                    <div class="field-card-body">
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
                        @input="onLiveFieldInput(mIdx, fIdx)"
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
                        @input="onLiveFieldInput(mIdx, fIdx)"
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
                        @blur="onNumberFieldBlur(mIdx, fIdx)"
                        @input="onLiveFieldInput(mIdx, fIdx)"
                       />

                      <!-- CHECKBOX -->
                      <FieldCheckbox
                        v-else-if="field.type === 'checkbox'"
                        :id="fieldId(mIdx, fIdx)"
                        v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                        v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                        :disabled="isReadonlyField(field, mIdx, fIdx)"
                        @update:modelValue="onDiscreteFieldChanged(mIdx, fIdx)"
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
                        @update:modelValue="onDiscreteFieldChanged(mIdx, fIdx)"
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
                        @update:model-value="() => clearDateManualInputError(mIdx, fIdx)"
                        @manual-input-state="(state) => onDateManualInputState(mIdx, fIdx, state)"
                        @change="onDiscreteFieldChanged(mIdx, fIdx)"
                        @blur="onDiscreteFieldBlur(mIdx, fIdx)"
                      />

                      <!-- TIME -->
                      <FieldTime
                        v-else-if="field.type === 'time'"
                        :id="fieldId(mIdx, fIdx)"
                        v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                        :placeholder="field.placeholder || (field.constraints?.timeFormat || 'HH:mm')"
                        v-bind="selectedModels[mIdx].fields[fIdx].constraints"
                        :readonly="isReadonlyField(field, mIdx, fIdx)"
                        @change="onDiscreteFieldChanged(mIdx, fIdx)"
                        @blur="onDiscreteFieldBlur(mIdx, fIdx)"
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
                        @update:modelValue="onDiscreteFieldChanged(mIdx, fIdx)"
                      />

                      <!-- SLIDER -->
                      <FieldSlider
                        v-else-if="field.type === 'slider' && (field.constraints?.mode || 'slider') === 'slider'"
                        :id="fieldId(mIdx, fIdx)"
                        v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                        v-bind="getSliderProps(field)"
                        :disabled="isReadonlyField(field, mIdx, fIdx)"
                        @update:modelValue="onDiscreteFieldChanged(mIdx, fIdx)"
                      />

                      <!-- LINEAR -->
                      <FieldLinearScale
                        v-else-if="field.type === 'slider' && field.constraints?.mode === 'linear'"
                        :id="fieldId(mIdx, fIdx)"
                        v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                        v-bind="getLinearProps(field)"
                        :disabled="isReadonlyField(field, mIdx, fIdx)"
                        @update:modelValue="onDiscreteFieldChanged(mIdx, fIdx)"
                      />

                      <!-- TABLE -->
                      <FieldTable
                        v-else-if="field.type === 'table'"
                        :ref="`tableField_${mIdx}_${fIdx}`"
                        :id="fieldId(mIdx, fIdx)"
                        v-model="entryData[currentSubjectIndex][currentVisitIndex][currentGroupIndex][mIdx][fIdx]"
                        :field="field"
                        :readonly="isReadonlyField(field, mIdx, fIdx)"
                        @update:modelValue="onDiscreteFieldChanged(mIdx, fIdx)"
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
                        @download-file="downloadUploadedFile"
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
                        @input="onLiveFieldInput(mIdx, fIdx)"
                      />
                    </div>

                    <div v-if="fieldErrors(mIdx, fIdx)" class="error-message">
                      {{ fieldErrors(mIdx, fIdx) }}
                      <span
                        v-if="isFieldSkipped(mIdx, fIdx)"
                        class="skip-pill"
                        title="Required validation skipped for this field"
                      >
                        Skipped
                      </span>
                    </div>

                    <div v-else-if="isFieldSkipped(mIdx, fIdx)" class="error-message">
                      <span class="skip-pill" title="Required validation skipped for this field">
                        Skipped
                      </span>
                    </div>
                    <div
                      v-if="hasPopupReminder(mIdx, fIdx)"
                      class="popup-reminder-message"
                    >
                      <div
                        v-for="(msg, reminderIdx) in popupReminderMessages(mIdx, fIdx)"
                        :key="'popup-reminder-' + reminderIdx"
                      >
                        {{ msg }}
                      </div>
                    </div>
                    <div v-if="fieldCalcWarning(mIdx, fIdx)" class="calc-warning-message">
                      {{ fieldCalcWarning(mIdx, fIdx) }}
                    </div>
                  </div>
                </template>
              </div>
            </section>
          </template>

          <div class="form-actions">
            <button
              @click="submitData"
              class="btn-save"
              :disabled="blockingErrorsPresent || !canEdit"
              :title="!canEdit ? 'This shared link is view-only' : (blockingErrorsPresent ? 'Fix validation errors before saving' : 'Save Data')"
            >
              Save Data
            </button>

            <button
              type="button"
              class="btn-clear"
              @click="clearCurrentSection"
              title="Clear all inputs"
              :disabled="!canEdit"
            >
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
      :study-name="study?.metadata?.study_name || ''"
      :subject-label="shareParams.subjectIndex != null ? sd.subjects?.[shareParams.subjectIndex]?.id : 'N/A'"
      :visit-label="visitList[shareParams.visitIndex]?.name || 'N/A'"
      :group-label="shareDialogGroupLabel"
      :available-sections="shareDialogSections"
      :section-availability-by-visit="shareDialogSectionAvailabilityByVisit"
      :same-group-subjects="shareDialogSameGroupSubjects"
      :visits="visitList"
      :permission="shareConfig.permission"
      :max-uses="shareConfig.maxUses"
      :expires-in-days="shareConfig.expiresInDays"
      :generated-link="generatedLink"
      :generated-links="generatedLinks"
      :generating="shareLinkGenerating"
      :copy-status="copyStatus"
      :shared-links="sharedLinks"
      :shared-links-loading="sharedLinksLoading"
      @close="showShareDialog = false"
      @copy="copyGeneratedLink"
      @copy-link="copyAnySharedLink"
      @generate="onShareDialogGenerate"
      @bulk-generate="onBulkShareDialogGenerate"
      @load-shared-links="loadSharedLinks"
      @revoke-link="revokeSharedLink"
      @export-links="exportSharedLinksCsv"
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

    <AddSubjectsDialog
      v-if="showSubjectDialog"
      :subjectCount="subjectCountDraft"
      :assignmentMethod="assignmentMethodDraft"
      :subjectIdConfig="subjectIdConfigDraft"
      :subjects="subjectDrafts"
      :groupData="groupList"
      :saving="savingSubjects"
      :error="subjectDialogError"
      @update:subjectCount="onSubjectCountChange"
      @update:assignmentMethod="onAssignmentMethodChange"
      @update:subjectIdConfig="onSubjectIdConfigDraftChange"
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

    <CustomDialog
      :message="dialogMessage"
      :isVisible="showDialog"
      @close="closeDialog"
    />

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

    <PreviousVisitImportDialog
      :visible="showPreviousVisitImportDialog"
      :fieldLabel="previousVisitImportContext?.fieldLabel || ''"
      :options="previousVisitImportOptions"
      @close="closePreviousVisitImportDialog"
      @select="applyPreviousVisitImport"
    />

    <DataEntryConflictDialog
      :visible="showEntryConflictDialog"
      :conflicts="entryConflicts"
      @confirm="confirmEntryConflictResolution"
      @cancel="cancelEntryConflictResolution"
    />

    <div
      v-if="showUnsavedExitDialog"
      class="unsaved-exit-backdrop"
      role="dialog"
      aria-modal="true"
      @click.self="cancelUnsavedExit"
    >
      <div class="unsaved-exit-dialog">
        <div class="unsaved-exit-header">
          <h3>Unsaved changes</h3>
          <button
            type="button"
            class="unsaved-exit-close"
            aria-label="Close"
            @click="cancelUnsavedExit"
          >
            ×
          </button>
        </div>

        <div class="unsaved-exit-body">
          <p>
            You have unsaved changes in this data-entry form.
          </p>
          <p>
            Please save before leaving, or exit anyway and lose the changes.
          </p>
        </div>

        <div class="unsaved-exit-actions">
          <button
            type="button"
            class="btn-save"
            @click="saveAndLeaveFromUnsavedDialog"
            :disabled="blockingErrorsPresent || !canEdit"
            :title="!canEdit ? 'This shared link is view-only' : (blockingErrorsPresent ? 'Fix validation errors before saving' : 'Save and leave')"
          >
            Save and Leave
          </button>

          <button
            type="button"
            class="btn-unsaved-exit"
            @click="confirmUnsavedExit"
          >
            Exit anyway
          </button>
        </div>
      </div>
    </div>
    <button
      v-if="!showSelection"
      type="button"
      class="floating-scroll-btn"
      :class="{ 'is-up': scrollFloatingMode === 'top' }"
      :title="scrollFloatingMode === 'top' ? 'Go to top' : 'Go to bottom'"
      :aria-label="scrollFloatingMode === 'top' ? 'Go to top' : 'Go to bottom'"
      @click.prevent.stop="toggleScrollPosition"
    >
      <i :class="scrollFloatingMode === 'top' ? 'fas fa-arrow-up' : 'fas fa-arrow-down'"></i>
    </button>
  </div>
    <div v-else-if="pageError" class="loading load-error-state">
    <p>{{ pageError }}</p>
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
import PreviousVisitImportDialog from "@/components/dataentry/PreviousVisitImportDialog.vue";
import DataEntryConflictDialog from "@/components/dataentry/DataEntryConflictDialog.vue";
import FieldTable from "@/components/FieldTable.vue";
import {
  getCalculationRulesFromStudy,
  getCalculationFormulaForField,
  buildFieldLookup,
  getCalculatedTargetIdSet,
  computeCalculation,
  sectionHasVisibleFields,
  evaluateFieldVisibility,
  buildPopupReminderIndex,
  getPopupReminderMessagesForField,
} from "@/utils/formLogicRuntime";
import {
  inferSubjectIdConfigFromExistingSubjects,
  normalizeSubjectIdConfig,
  buildUniqueSubjectId,
  getNextSubjectSequenceNumber,
} from "@/utils/subjectIdUtils";
import {
  calculateDataEntryFieldProgress,
  calculateDataEntryProgress,
} from "@/utils/dataEntryProgress";
import {
  buildValueAssignmentFieldLookup,
  evaluateValueAssignments,
} from "@/utils/formValueAssignmentRuntime";
import { parseDateByConfiguredFormat } from "@/utils/dateFormatParsing";
import {
  inferUploadedFileFieldContext,
  uploadedFileId,
  uploadedFileName,
} from "@/utils/uploadedFiles";
import {
  applyConflictDecisions,
  mergeDataEntryFields,
} from "@/utils/dataEntryConflict";
import { mergeTableFieldConflict } from "@/utils/tableConflict";
import {
  buildPreviousVisitTableColumns,
  buildPreviousVisitTableRows,
  hasPreviousVisitTableData,
  selectPreviousVisitTableRows,
} from "@/utils/previousVisitTableImport";

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
    PreviousVisitImportDialog,
    DataEntryConflictDialog,
  },
  data() {
    return {
      study: null,
      pageError: "",
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
      statusRowsMap: new Map(),
      assignedLookup: [],
      subjectToGroupIdx: [],

      entryData: [],
      skipFlags: [],
      validationErrors: {},
      manualDateInputErrors: {},

      // calc warnings
      calcWarnings: {},
      valueAssignmentWarnings: [],

      icons,
      showShareDialog: false,
      shareLinkGenerating: false,
      shareParams: { subjectIndex: null, visitIndex: null, groupIndex: null },
      shareConfig: { permission: "view", maxUses: 1, expiresInDays: 7, allowed_section_ids: [] },
      generatedLinks: [],
      generatedLink: "",
      sharedLinks: [],
      sharedLinksLoading: false,
      copyStatus: "",
      permissionError: false,

      showDialog: false,
      dialogMessage: "",
      dialogAction: null,
      showSkipDialog: false,
      skipCandidates: [],
      skipSelections: {},
      showEntryConflictDialog: false,
      entryConflicts: [],
      pendingEntryConflict: null,

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
      studyFiles: [],
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
      collapsedSections: {},
      allSectionsCollapsed: false,
      highlightedErrorKey: "",
      entrySearchQuery: "",
      showEntrySearchResults: false,
      entrySearchActiveIndex: -1,
      entrySearchHighlightedSectionIndex: null,
      entrySearchHighlightedFieldKey: "",
      entrySearchHighlightTimer: null,
      entrySearchCloseTimer: null,
      entryProgress: {
        total: 0,
        completed: 0,
        incomplete: 0,
        skipped: 0,
        percentage: 0,
      },
      entryProgressTimer: null,
      entryProgressFieldCache: new Map(),
      entryProgressCacheSlot: "",
      progressVisibilityDependents: new Map(),
      scrollFloatingMode: "bottom",
      scrollListenerAttached: false,
      showPreviousVisitImportDialog: false,
      previousVisitImportOptions: [],
      previousVisitImportContext: null,
      importedPreviousVisitLocks: {},
      entryBaselineSnapshot: "",
      entryDirty: false,
      validationMountAllSections: false,
      runtimeFieldLookup: null,
      runtimeFieldLookupModels: null,
      runtimeValueAssignmentLookup: null,
      runtimeValueAssignmentLookupModels: null,
      runtimeCalculatedTargetIds: null,
      runtimeCalculatedStudy: null,
      runtimeCalculationFormulaCache: new Map(),
      runtimePopupReminderIndex: null,
      runtimePopupReminderIndexModels: null,
      runtimeCommitHandles: new Map(),
      pendingNavigationAction: null,
      showUnsavedExitDialog: false,
      subjectIdConfigDraft: null,
    };
  },

  computed: {
    shareDialogGroupLabel() {
      const sIdx = Number(this.shareParams?.subjectIndex);
      const subject = this.sd.subjects?.[sIdx];

      return String(subject?.group || "").trim() || "Unassigned";
    },

    shareDialogSameGroupSubjects() {
      const currentGroup = this.shareDialogGroupLabel;
      const subjects = Array.isArray(this.sd.subjects) ? this.sd.subjects : [];

      return subjects
        .map((subject, index) => ({
          index,
          id: String(subject?.id || subject?.subject_id || `Subject ${index + 1}`).trim(),
          group: String(subject?.group || "").trim() || "Unassigned",
        }))
        .filter((subject) => subject.group === currentGroup);
    },

    shareDialogSectionAvailabilityByVisit() {
      const gIdx = Number(this.shareParams?.groupIndex);
      const visits = Array.isArray(this.visitList) ? this.visitList : [];
      const selectedModels = Array.isArray(this.selectedModels) ? this.selectedModels : [];
      const assignments = Array.isArray(this.assignments) ? this.assignments : [];

      if (!Number.isInteger(gIdx) || gIdx < 0) return {};

      const out = {};

      visits.forEach((visit, vIdx) => {
        const validSections = [];

        selectedModels.forEach((section, mIdx) => {
          const assigned = !!assignments?.[mIdx]?.[vIdx]?.[gIdx];
          if (!assigned) return;

          const sectionId = String(
            section?._id ||
            section?.id ||
            section?.uuid ||
            ""
          ).trim();

          if (!sectionId) return;

          validSections.push({
            id: sectionId,
            title: section?.title || `Section ${mIdx + 1}`,
          });
        });

        out[vIdx] = validSections;
      });

      return out;
    },
    hasUnsavedEntryChanges() {
      if (this.showSelection) return false;
      if (!this.canEdit) return false;
      return this.entryDirty;
    },
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
    selectionMatrixKey() {
      return [
        this.selectedVisitIndex,
        this.displayedVisitIndices.join("_"),
        this.canSeeGroupColumn ? "group" : "nogroup",
        this.selectedVersion || "v0",
        this.numberOfSubjects,
        this.visitList.length,
      ].join("|");
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

    entrySearchResults() {
      const query = String(this.entrySearchQuery || "").trim().toLocaleLowerCase();
      if (!query) return [];

      const results = [];

      const matchRank = (values) => {
        const normalizedValues = values
          .map((value) => String(value || "").trim().toLocaleLowerCase())
          .filter(Boolean);

        if (normalizedValues.some((value) => value === query)) return 0;
        if (normalizedValues.some((value) => value.startsWith(query))) return 1;
        if (normalizedValues.some((value) => value.includes(query))) return 2;
        return -1;
      };

      this.assignedModelIndices.forEach((mIdx) => {
        if (!this.hasVisibleFieldsInSection(mIdx)) return;

        const section = this.selectedModels?.[mIdx] || {};
        const sectionTitle = section.title || `Section ${mIdx + 1}`;
        const sectionRank = matchRank([sectionTitle]);

        if (sectionRank >= 0) {
          results.push({
            key: `section-${mIdx}`,
            type: "section",
            label: sectionTitle,
            sectionTitle,
            sectionIndex: mIdx,
            fieldIndex: null,
            rank: sectionRank,
          });
        }

        (section.fields || []).forEach((field, fIdx) => {
          if (!this.isFieldVisible(mIdx, fIdx)) return;

          const fieldLabel =
            field?.label ||
            field?.name ||
            field?.title ||
            `Field ${fIdx + 1}`;
          const fieldRank = matchRank([
            fieldLabel,
            field?.label,
            field?.name,
            field?.title,
          ]);

          if (fieldRank < 0) return;

          results.push({
            key: `field-${mIdx}-${fIdx}`,
            type: "field",
            label: fieldLabel,
            sectionTitle,
            sectionIndex: mIdx,
            fieldIndex: fIdx,
            rank: fieldRank,
          });
        });
      });

      return results
        .sort((a, b) => {
          if (a.rank !== b.rank) return a.rank - b.rank;
          if (a.sectionIndex !== b.sectionIndex) {
            return a.sectionIndex - b.sectionIndex;
          }
          if (a.type !== b.type) return a.type === "section" ? -1 : 1;
          return (a.fieldIndex ?? -1) - (b.fieldIndex ?? -1);
        })
        .slice(0, 50);
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
        return;
      }

      const authOk = await this.ensureAuthReadyForAddData();
      if (!authOk) return;

      const studyId = this.$route.params.id;

      await this.loadStudy(studyId);

      if (!this.study) return;

      await this.loadVersions(studyId);

      this.selectedVersion =
        this.studyVersions[this.studyVersions.length - 1]?.version || 1;

      await this.loadTemplateForSelectedVersion();

      this.selectedVisitIndex =
        this.visitList.length > this.VISIT_THRESHOLD ? 0 : -1;

      await this.loadExistingEntries(studyId);
      await this.loadStudyFiles(studyId);

      this.visitLoading = true;
      this.applyVersionView();
      this.prepareAssignmentsLookup();
      this.prepareSubjectGroupIndexMap();
      this.buildStatusCache();
      this.visitLoading = false;

      this.matrixReady = true;
    },
  beforeUnmount() {
      this.detachFloatingScrollListener();
      this.clearEntrySearchTimers();
      if (this.entryProgressTimer) {
        window.clearTimeout(this.entryProgressTimer);
        this.entryProgressTimer = null;
      }
      this.cancelAllRuntimeFieldCommits();
      window.onbeforeunload = null;
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
    hasUnsavedEntryChanges(val) {
      window.onbeforeunload = val
        ? (event) => {
            event.preventDefault();
            event.returnValue = "";
            return "";
          }
        : null;
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
        this.runtimeFieldLookupModels = null;
        this.runtimeFieldLookup = null;
        this.runtimeValueAssignmentLookupModels = null;
        this.runtimeValueAssignmentLookup = null;
        this.runtimeCalculatedStudy = null;
        this.runtimeCalculatedTargetIds = null;
        this.runtimeCalculationFormulaCache = new Map();
        this.runtimePopupReminderIndexModels = null;
        this.runtimePopupReminderIndex = null;
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
    showSelection(val) {
      if (val) {
        this.resetEntrySearch();
        this.detachFloatingScrollListener();
        window.onbeforeunload = null;
        return;
      }

      this.$nextTick(() => {
        this.attachFloatingScrollListener();
        this.updateFloatingScrollMode();
        this.captureEntryBaseline();
        this.scheduleEntryProgressUpdate({ immediate: true });
      });
    },
    currentSubjectIndex() {
      this.resetEntrySearch();
      this.scheduleEntryProgressUpdate({ immediate: true });
    },
    currentVisitIndex() {
      this.resetEntrySearch();
      this.scheduleEntryProgressUpdate({ immediate: true });
    },
    currentGroupIndex() {
      this.resetEntrySearch();
      this.scheduleEntryProgressUpdate({ immediate: true });
    },
  },
  beforeRouteLeave(to, from, next) {
      if (!this.hasUnsavedEntryChanges) {
        window.onbeforeunload = null;
        next();
        return;
      }

      this.pendingNavigationAction = () => {
        window.onbeforeunload = null;
        next();
      };

      this.showUnsavedExitDialog = true;
  },

  methods: {
    calculateCurrentEntryProgress() {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;

      if (
        this.showSelection ||
        s == null ||
        v == null ||
        g == null
      ) {
        return {
          total: 0,
          completed: 0,
          incomplete: 0,
          skipped: 0,
          percentage: 0,
        };
      }

      this.ensureSlot(s, v, g);

      return calculateDataEntryProgress({
        sections: this.selectedModels,
        assignedSectionIndexes: this.assignedModelIndices,
        values: this.entryData?.[s]?.[v]?.[g] || [],
        skips: this.skipFlags?.[s]?.[v]?.[g] || [],
        isFieldVisible: (mIdx, fIdx) => this.isFieldVisible(mIdx, fIdx),
        isCalculatedField: (mIdx, fIdx) =>
          this.isCalculatedRuntimeField(mIdx, fIdx),
        hasFieldError: (mIdx, fIdx) => !!this.fieldErrors(mIdx, fIdx),
        getTableCellErrors: (mIdx, fIdx) =>
          this.getTableValidationState(mIdx, fIdx)?.cellErrors || {},
      });
    },

    updateEntryProgress() {
      this.rebuildEntryProgressCache();
    },

    currentProgressSlotKey() {
      return [
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex,
        this.selectedVersion,
      ].join("|");
    },

    progressFieldKey(mIdx, fIdx) {
      return `${mIdx}:${fIdx}`;
    },

    calculateProgressContribution(mIdx, fIdx) {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];

      return calculateDataEntryFieldProgress({
        field,
        value: this.entryData?.[s]?.[v]?.[g]?.[mIdx]?.[fIdx],
        skipped: !!this.skipFlags?.[s]?.[v]?.[g]?.[mIdx]?.[fIdx],
        visible: this.isFieldVisible(mIdx, fIdx),
        calculated: this.isCalculatedRuntimeField(mIdx, fIdx),
        hasError: !!this.fieldErrors(mIdx, fIdx),
        tableCellErrors: this.getTableValidationState(mIdx, fIdx)?.cellErrors || {},
      });
    },

    rebuildProgressVisibilityDependents() {
      const dependents = new Map();
      const lookup = this.getFieldLookup();

      (this.selectedModels || []).forEach((section, mIdx) => {
        (section?.fields || []).forEach((field, fIdx) => {
          const rules = field?.constraints?.visibilityLogic?.rules || [];
          rules.forEach((rule) => {
            const source = lookup.get(String(rule?.sourceFieldKey || ""));
            if (!source) return;
            const sourceKey = this.progressFieldKey(source.mIdx, source.fIdx);
            const targets = dependents.get(sourceKey) || new Set();
            targets.add(this.progressFieldKey(mIdx, fIdx));
            dependents.set(sourceKey, targets);
          });
        });
      });

      this.progressVisibilityDependents = dependents;
    },

    publishEntryProgressCache() {
      let total = 0;
      let completed = 0;
      let skipped = 0;

      this.entryProgressFieldCache.forEach((item) => {
        total += item.total;
        completed += item.completed;
        skipped += item.skipped;
      });

      this.entryProgress = {
        total,
        completed,
        incomplete: Math.max(0, total - completed),
        skipped,
        percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
      };
    },

    rebuildEntryProgressCache() {
      if (
        this.showSelection ||
        this.currentSubjectIndex == null ||
        this.currentVisitIndex == null ||
        this.currentGroupIndex == null
      ) {
        this.entryProgressFieldCache = new Map();
        this.entryProgressCacheSlot = "";
        this.entryProgress = this.calculateCurrentEntryProgress();
        return;
      }

      this.ensureSlot(
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex
      );
      const cache = new Map();
      this.assignedModelIndices.forEach((mIdx) => {
        (this.selectedModels?.[mIdx]?.fields || []).forEach((_, fIdx) => {
          cache.set(
            this.progressFieldKey(mIdx, fIdx),
            this.calculateProgressContribution(mIdx, fIdx)
          );
        });
      });
      this.entryProgressFieldCache = cache;
      this.entryProgressCacheSlot = this.currentProgressSlotKey();
      this.rebuildProgressVisibilityDependents();
      this.publishEntryProgressCache();
    },

    refreshEntryProgressFields(fields = []) {
      if (this.entryProgressCacheSlot !== this.currentProgressSlotKey()) {
        this.rebuildEntryProgressCache();
        return;
      }

      const pending = [...fields];
      const affected = new Set();
      while (pending.length) {
        const item = pending.shift();
        const key = typeof item === "string"
          ? item
          : this.progressFieldKey(item.mIdx, item.fIdx);
        if (affected.has(key)) continue;
        affected.add(key);
        (this.progressVisibilityDependents.get(key) || []).forEach((dependent) => {
          pending.push(dependent);
        });
      }

      affected.forEach((key) => {
        const [mIdx, fIdx] = key.split(":").map(Number);
        if (!this.assignedModelIndices.includes(mIdx)) {
          this.entryProgressFieldCache.delete(key);
          return;
        }
        this.entryProgressFieldCache.set(
          key,
          this.calculateProgressContribution(mIdx, fIdx)
        );
      });
      this.publishEntryProgressCache();
    },

    entryProgressStatus(progress) {
      if (!progress || Number(progress.total || 0) <= 0) return "none";
      if (Number(progress.skipped || 0) > 0) return "skipped";
      if (Number(progress.completed || 0) <= 0) return "none";
      return Number(progress.percentage || 0) >= 100 ? "complete" : "partial";
    },

    normalizeEntryProgressSnapshot(progress) {
      const total = Math.max(0, Number(progress?.total || 0));
      const completed = Math.max(0, Number(progress?.completed || 0));
      const skipped = Math.max(0, Number(progress?.skipped || 0));
      const percentage = total > 0
        ? Math.max(0, Math.min(100, Number(progress?.percentage || 0)))
        : 0;
      const incomplete = Math.max(0, Number(progress?.incomplete ?? (total - completed)));
      const snapshot = {
        total,
        completed,
        incomplete,
        skipped,
        percentage,
      };

      return {
        ...snapshot,
        status: this.entryProgressStatus(snapshot),
      };
    },

    calculateEntryProgressForSlot(s, v, g) {
      this.ensureSlot(s, v, g);

      const assignedSectionIndexes = this.assignedLookup?.[v]?.[g] || [];
      return calculateDataEntryProgress({
        sections: this.selectedModels,
        assignedSectionIndexes,
        values: this.entryData?.[s]?.[v]?.[g] || [],
        skips: this.skipFlags?.[s]?.[v]?.[g] || [],
        isFieldVisible: (mIdx, fIdx) => this.isFieldVisible(mIdx, fIdx),
        isCalculatedField: (mIdx, fIdx) =>
          this.isCalculatedRuntimeField(mIdx, fIdx),
        hasFieldError: (mIdx, fIdx) => !!this.fieldErrors(mIdx, fIdx),
        getTableCellErrors: (mIdx, fIdx) =>
          this.getTableValidationState(mIdx, fIdx)?.cellErrors || {},
      });
    },

    buildEntryProgressPayload(progress) {
      const snapshot = this.normalizeEntryProgressSnapshot(progress);
      return {
        progress_status: snapshot.status,
        progress_percentage: snapshot.percentage,
        progress_completed: snapshot.completed,
        progress_total: snapshot.total,
        progress_skipped: snapshot.skipped,
      };
    },

    getStoredEntryProgress(entry) {
      const hasProgress =
        entry?.progress_status != null ||
        entry?.progress_percentage != null ||
        entry?.progress_completed != null ||
        entry?.progress_total != null ||
        entry?.progress_skipped != null;
      if (!hasProgress) {
        return null;
      }

      return this.normalizeEntryProgressSnapshot({
        status: entry.progress_status,
        percentage: entry.progress_percentage,
        completed: entry.progress_completed,
        total: entry.progress_total,
        skipped: entry.progress_skipped,
      });
    },

    calculateProgressFromSavedEntry(entry, visitIndex, groupIndex) {
      if (!entry) return null;

      try {
        const values = entry.data && !Array.isArray(entry.data) && typeof entry.data === "object"
          ? this.dictToArray(entry.data)
          : Array.isArray(entry.data)
          ? entry.data
          : [];
        const skips = this.normalizeSkipFlagsShape(
          entry.skipped_required_flags || entry.skips || []
        );
        const assignedSectionIndexes = this.assignedLookup?.[visitIndex]?.[groupIndex] || [];

        return calculateDataEntryProgress({
          sections: this.selectedModels,
          assignedSectionIndexes,
          values,
          skips,
          isFieldVisible: (mIdx, fIdx) =>
            evaluateFieldVisibility(
              this.study,
              this.selectedModels,
              values,
              mIdx,
              fIdx,
              new Set(),
              this.getFieldLookup()
            ),
          isCalculatedField: (mIdx, fIdx) =>
            this.isCalculatedRuntimeField(mIdx, fIdx),
          hasFieldError: () => false,
          getTableCellErrors: () => ({}),
        });
      } catch (error) {
        console.warn("Failed to calculate saved entry progress", error);
        return null;
      }
    },

    entryStatusFromSavedEntry(entry, visitIndex, groupIndex) {
      const row = this.statusRowFromSavedEntry(entry, visitIndex, groupIndex);
      return row?.status || null;
    },

    statusRowFromSavedEntry(entry, visitIndex, groupIndex) {
      const storedProgress = this.getStoredEntryProgress(entry);
      if (storedProgress) {
        return {
          status: storedProgress.status,
          percentage: storedProgress.percentage,
          completed: storedProgress.completed,
          total: storedProgress.total,
          skipped: storedProgress.skipped,
        };
      }
      const calculatedProgress = this.calculateProgressFromSavedEntry(
        entry,
        visitIndex,
        groupIndex
      );
      if (!calculatedProgress) return null;

      const progress = this.normalizeEntryProgressSnapshot(calculatedProgress);
      return {
        status: progress.status,
        percentage: progress.percentage,
        completed: progress.completed,
        total: progress.total,
        skipped: progress.skipped,
      };
    },

    scheduleEntryProgressUpdate({ immediate = false } = {}) {
      if (this.entryProgressTimer) {
        window.clearTimeout(this.entryProgressTimer);
        this.entryProgressTimer = null;
      }

      if (immediate) {
        this.$nextTick(() => {
          this.updateEntryProgress();
        });
        return;
      }

      this.entryProgressTimer = window.setTimeout(() => {
        this.entryProgressTimer = null;
        this.updateEntryProgress();
      }, 180);
    },

    clearEntrySearchTimers() {
      if (this.entrySearchHighlightTimer) {
        window.clearTimeout(this.entrySearchHighlightTimer);
        this.entrySearchHighlightTimer = null;
      }

      if (this.entrySearchCloseTimer) {
        window.clearTimeout(this.entrySearchCloseTimer);
        this.entrySearchCloseTimer = null;
      }
    },

    clearEntrySearchHighlight() {
      if (this.entrySearchHighlightTimer) {
        window.clearTimeout(this.entrySearchHighlightTimer);
        this.entrySearchHighlightTimer = null;
      }

      this.entrySearchHighlightedSectionIndex = null;
      this.entrySearchHighlightedFieldKey = "";
    },

    resetEntrySearch() {
      this.clearEntrySearchTimers();
      this.entrySearchQuery = "";
      this.showEntrySearchResults = false;
      this.entrySearchActiveIndex = -1;
      this.entrySearchHighlightedSectionIndex = null;
      this.entrySearchHighlightedFieldKey = "";
    },

    onEntrySearchInput() {
      this.showEntrySearchResults = true;
      this.entrySearchActiveIndex = this.entrySearchResults.length ? 0 : -1;
      this.clearEntrySearchHighlight();
    },

    openEntrySearchResults() {
      if (this.entrySearchCloseTimer) {
        window.clearTimeout(this.entrySearchCloseTimer);
        this.entrySearchCloseTimer = null;
      }

      if (String(this.entrySearchQuery || "").trim()) {
        this.showEntrySearchResults = true;
      }
    },

    closeEntrySearchResults() {
      if (this.entrySearchCloseTimer) {
        window.clearTimeout(this.entrySearchCloseTimer);
      }

      this.entrySearchCloseTimer = window.setTimeout(() => {
        this.showEntrySearchResults = false;
        this.entrySearchActiveIndex = -1;
        this.entrySearchCloseTimer = null;
      }, 150);
    },

    closeEntrySearchImmediately() {
      if (this.entrySearchCloseTimer) {
        window.clearTimeout(this.entrySearchCloseTimer);
        this.entrySearchCloseTimer = null;
      }

      this.showEntrySearchResults = false;
      this.entrySearchActiveIndex = -1;
    },

    moveEntrySearchSelection(direction) {
      const count = this.entrySearchResults.length;
      if (!count) return;

      this.showEntrySearchResults = true;

      const current =
        this.entrySearchActiveIndex >= 0
          ? this.entrySearchActiveIndex
          : direction > 0
            ? -1
            : 0;

      this.entrySearchActiveIndex = (current + direction + count) % count;
    },

    selectActiveEntrySearchResult() {
      if (!this.entrySearchResults.length) return;

      const index =
        this.entrySearchActiveIndex >= 0
          ? this.entrySearchActiveIndex
          : 0;

      this.selectEntrySearchResult(
        this.entrySearchResults[index] || this.entrySearchResults[0]
      );
    },

    async selectEntrySearchResult(result) {
      if (!result) return;

      const mIdx = Number(result.sectionIndex);
      const isFieldResult =
        result.type === "field" &&
        Number.isInteger(Number(result.fieldIndex));
      const fIdx = isFieldResult ? Number(result.fieldIndex) : null;

      if (!Number.isInteger(mIdx) || !this.hasVisibleFieldsInSection(mIdx)) {
        return;
      }

      if (isFieldResult && !this.isFieldVisible(mIdx, fIdx)) {
        return;
      }

      if (this.isSectionCollapsed(mIdx)) {
        this.collapsedSections = {
          ...(this.collapsedSections || {}),
          [mIdx]: false,
        };
        this.syncAllSectionsCollapsedState();
      }

      this.closeEntrySearchImmediately();
      this.clearEntrySearchHighlight();

      await this.$nextTick();

      this.entrySearchHighlightedSectionIndex = mIdx;
      this.entrySearchHighlightedFieldKey = isFieldResult
        ? `${mIdx}-${fIdx}`
        : "";

      await this.$nextTick();

      const target = isFieldResult
        ? this.$el?.querySelector?.(`[data-search-key="${mIdx}-${fIdx}"]`)
        : this.$el?.querySelector?.(`[data-section-index="${mIdx}"]`);

      if (!target) {
        this.clearEntrySearchHighlight();
        return;
      }

      target.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });

      this.entrySearchHighlightTimer = window.setTimeout(() => {
        this.entrySearchHighlightedSectionIndex = null;
        this.entrySearchHighlightedFieldKey = "";
        this.entrySearchHighlightTimer = null;
      }, 2200);
    },

    getApiErrorDetail(err) {
      if (err?.response?.status === 503) {
        return err?.response?.data?.detail || "eCRF is under maintenance. Please try again later.";
      }

      const detail = err?.response?.data?.detail;

      if (Array.isArray(detail)) {
        return detail.map((d) => d?.msg || String(d)).join(", ");
      }

      if (detail) return String(detail);

      return "";
    },

    getSharedLoadErrorMessage(err) {
      const status = err?.response?.status;
      const detail = this.getApiErrorDetail(err).toLowerCase();

      if (status === 403 && detail.includes("usage limit")) {
        return "This shared link has reached its usage limit.";
      }

      if (status === 403 && detail.includes("expired")) {
        return "This shared link has expired.";
      }

      if (status === 404) {
        return "This shared link is invalid or no longer available.";
      }

      return "Unable to open this shared link.";
    },
    buildCurrentEntrySnapshot() {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;

      if (s == null || v == null || g == null) return "";

      this.ensureSlot(s, v, g);

      const data = this.entryData?.[s]?.[v]?.[g] || [];
      const skips = this.skipFlags?.[s]?.[v]?.[g] || [];
      const locks = this.importedPreviousVisitLocks || {};

      return JSON.stringify({
        data,
        skips,
        locks,
      });
    },

    captureEntryBaseline() {
      this.entryBaselineSnapshot = this.buildCurrentEntrySnapshot();
      this.entryDirty = false;
    },

    markEntryDirty() {
      if (!this.showSelection && this.canEdit) this.entryDirty = true;
    },

    requestBackToSelection() {
      if (this.hasUnsavedEntryChanges) {
        this.pendingNavigationAction = () => {
          this.forceBackToSelection();
        };
        this.showUnsavedExitDialog = true;
        return;
      }

      this.forceBackToSelection();
    },

    forceBackToSelection() {
      window.onbeforeunload = null;
      this.showUnsavedExitDialog = false;
      this.pendingNavigationAction = null;
      this.backToSelection();
    },

    cancelUnsavedExit() {
      this.showUnsavedExitDialog = false;
      this.pendingNavigationAction = null;
    },
    saveAndLeaveFromUnsavedDialog() {
      this.showUnsavedExitDialog = false;
      this.pendingNavigationAction = null;
      this.submitData();
    },

    confirmUnsavedExit() {
      const action = this.pendingNavigationAction;

      this.showUnsavedExitDialog = false;
      this.pendingNavigationAction = null;
      this.entryBaselineSnapshot = this.buildCurrentEntrySnapshot();
      this.entryDirty = false;
      window.onbeforeunload = null;

      if (typeof action === "function") {
        action();
      }
    },
    async ensureAuthReadyForAddData() {
      if (this.isShared) return true;

      if (this.$store.state.token && this.$store.state.user) {
        return true;
      }

      const ok = await this.$store.dispatch("initAuth");

      if (!ok) {
        this.$router.replace({
          path: "/login",
          query: { redirect: this.$route.fullPath },
        }).catch(() => null);

        return false;
      }

      return true;
    },
    getScrollRoot() {
      const candidates = [
        this.$el?.closest?.(".dashboard-main"),
        document.querySelector(".dashboard-main"),
        document.scrollingElement,
        document.documentElement,
      ].filter(Boolean);

      return (
        candidates.find((el) => {
          const style = window.getComputedStyle(el);
          const canScroll =
            /(auto|scroll)/.test(style.overflowY) ||
            el.scrollHeight > el.clientHeight + 2;

          return canScroll && el.scrollHeight > el.clientHeight + 2;
        }) ||
        document.scrollingElement ||
        document.documentElement
      );
    },

    getScrollTop(root) {
      if (root === document.scrollingElement || root === document.documentElement || root === document.body) {
        return window.scrollY || root.scrollTop || 0;
      }

      return root.scrollTop || 0;
    },

    getClientHeight(root) {
      if (root === document.scrollingElement || root === document.documentElement || root === document.body) {
        return window.innerHeight || document.documentElement.clientHeight || 0;
      }

      return root.clientHeight || 0;
    },

    updateFloatingScrollMode() {
      if (this.showSelection) return;

      const root = this.getScrollRoot();
      const scrollTop = this.getScrollTop(root);
      const viewportHeight = this.getClientHeight(root);
      const scrollHeight = root.scrollHeight || 0;

      const distanceFromBottom = scrollHeight - (scrollTop + viewportHeight);

      this.scrollFloatingMode = distanceFromBottom <= 180 ? "top" : "bottom";
    },

    toggleScrollPosition() {
      const root = this.getScrollRoot();

      const targetTop =
        this.scrollFloatingMode === "top"
          ? 0
          : Math.max(0, root.scrollHeight - this.getClientHeight(root));

      if (root === document.scrollingElement || root === document.documentElement || root === document.body) {
        window.scrollTo({
          top: targetTop,
          behavior: "smooth",
        });
      } else {
        root.scrollTo({
          top: targetTop,
          behavior: "smooth",
        });
      }

      window.setTimeout(() => {
        this.updateFloatingScrollMode();
      }, 350);
    },

    attachFloatingScrollListener() {
      if (this.scrollListenerAttached) return;

      const root = this.getScrollRoot();
      this._floatingScrollRoot = root;

      root.addEventListener("scroll", this.updateFloatingScrollMode, { passive: true });
      window.addEventListener("resize", this.updateFloatingScrollMode, { passive: true });

      this.scrollListenerAttached = true;

      this.$nextTick(() => {
        this.updateFloatingScrollMode();
      });
    },

    detachFloatingScrollListener() {
      if (!this.scrollListenerAttached) return;

      const root = this._floatingScrollRoot || this.getScrollRoot();

      root.removeEventListener("scroll", this.updateFloatingScrollMode);
      window.removeEventListener("resize", this.updateFloatingScrollMode);

      this._floatingScrollRoot = null;
      this.scrollListenerAttached = false;
    },
    buildSaveSuccessMessage(mode = "saved") {
      const subjectLabel =
        this.sd.subjects?.[this.currentSubjectIndex]?.id ||
        `Subject ${this.currentSubjectIndex + 1}`;

      const visitLabel =
        this.visitList?.[this.currentVisitIndex]?.name ||
        `Visit ${this.currentVisitIndex + 1}`;

      const actionText = mode === "updated" ? "updated" : "saved";

      return `Data ${actionText} successfully for:
    Subject: ${subjectLabel}
    Visit: ${visitLabel}

    To add data for another visit of this subject, use the Visit selector at the top.
    To add data for a different subject, go back to the selection table.`;
    },
    getCurrentValidationErrorItems() {
      const s0 = this.currentSubjectIndex;
      const v0 = this.currentVisitIndex;
      const g0 = this.currentGroupIndex;

      const items = [];

      Object.entries(this.validationErrors || {}).forEach(([key, message]) => {
        if (!message) return;

        const parsed = this.parseKey(key);
        if (!parsed) return;

        const { s, v, g, m, f } = parsed;

        if (s !== s0 || v !== v0 || g !== g0) return;

        const isSkipped = !!this.skipFlags?.[s]?.[v]?.[g]?.[m]?.[f];
        if (isSkipped) return;

        const section = this.selectedModels?.[m];
        const field = section?.fields?.[f];
        if (!section || !field) return;

        if (!this.assignedModelIndices.includes(m)) return;
        if (!this.hasVisibleFieldsInSection(m)) return;
        if (!this.isFieldVisible(m, f)) return;

        items.push({
          key,
          message,
          sectionIndex: m,
          fieldIndex: f,
          sectionTitle: section.title || `Section ${m + 1}`,
          fieldLabel: field.label || field.name || field.title || `Field ${f + 1}`,
        });
      });

      const sectionOrder = new Map(
        this.assignedModelIndices.map((mIdx, order) => [mIdx, order])
      );

      items.sort((a, b) => {
        const sa = sectionOrder.has(a.sectionIndex)
          ? sectionOrder.get(a.sectionIndex)
          : a.sectionIndex;

        const sb = sectionOrder.has(b.sectionIndex)
          ? sectionOrder.get(b.sectionIndex)
          : b.sectionIndex;

        if (sa !== sb) return sa - sb;
        return a.fieldIndex - b.fieldIndex;
      });

      return items;
    },

    getSectionErrorItems(mIdx) {
      return this.getCurrentValidationErrorItems().filter(
        (item) => item.sectionIndex === mIdx
      );
    },

    hasSectionErrors(mIdx) {
      return this.getSectionErrorItems(mIdx).length > 0;
    },

    sectionErrorCount(mIdx) {
      return this.getSectionErrorItems(mIdx).length;
    },

    async revealValidationError(item) {
      if (!item) return;

      const mIdx = item.sectionIndex;
      const fIdx = item.fieldIndex;

      if (this.isSectionCollapsed(mIdx)) {
        this.collapsedSections = {
          ...(this.collapsedSections || {}),
          [mIdx]: false,
        };
        this.syncAllSectionsCollapsedState();
      }

      await this.$nextTick();

      const key = this.errorKey(mIdx, fIdx);
      this.highlightedErrorKey = key;

      await this.$nextTick();

      const inputEl = document.getElementById(this.fieldId(mIdx, fIdx));
      const cardEl =
        inputEl?.closest?.(".field-card") ||
        document.querySelector(`[data-error-key="${key}"]`);

      const target = cardEl || inputEl;
      if (!target) return;

      target.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });

      window.setTimeout(() => {
        const focusTarget =
          inputEl ||
          target.querySelector?.("input, textarea, select, button, [tabindex]:not([tabindex='-1'])");

        if (focusTarget && typeof focusTarget.focus === "function") {
          try {
            focusTarget.focus({ preventScroll: true });
          } catch {
            focusTarget.focus();
          }
        }
      }, 350);
    },

    goToFirstValidationError() {
      const items = this.getCurrentValidationErrorItems();
      if (!items.length) return;

      this.revealValidationError(items[0]);
    },

    goToNextErrorInSection(mIdx) {
      const items = this.getSectionErrorItems(mIdx);
      if (!items.length) return;

      const currentIdx = items.findIndex(
        (item) => item.key === this.highlightedErrorKey
      );

      const nextIdx = currentIdx >= 0 ? (currentIdx + 1) % items.length : 0;
      this.revealValidationError(items[nextIdx]);
    },
    isSectionCollapsed(mIdx) {
      return !!this.collapsedSections?.[mIdx];
    },

    toggleSectionCollapse(mIdx) {
      this.collapsedSections = {
        ...(this.collapsedSections || {}),
        [mIdx]: !this.collapsedSections?.[mIdx],
      };

      this.syncAllSectionsCollapsedState();
    },

    toggleAllSectionsCollapse() {
      const nextCollapsed = !this.allSectionsCollapsed;
      const next = {};

      this.assignedModelIndices.forEach((mIdx) => {
        if (this.hasVisibleFieldsInSection(mIdx)) {
          next[mIdx] = nextCollapsed;
        }
      });

      this.collapsedSections = next;
      this.allSectionsCollapsed = nextCollapsed;
    },

    syncAllSectionsCollapsedState() {
      const visibleSectionIndices = this.assignedModelIndices.filter((mIdx) =>
        this.hasVisibleFieldsInSection(mIdx)
      );

      if (!visibleSectionIndices.length) {
        this.allSectionsCollapsed = false;
        return;
      }

      this.allSectionsCollapsed = visibleSectionIndices.every((mIdx) =>
        this.isSectionCollapsed(mIdx)
      );
    },
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

      if (this.entryProgressCacheSlot === this.currentProgressSlotKey()) {
        this.refreshEntryProgressFields([{ mIdx, fIdx }]);
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

        const rawSkipFlags = this.normalizeSkipFlagsShape(this.skipFlags[s][v][g]);
        this.skipFlags[s][v][g] = rawSkipFlags;
        const dictData = this.arrayToDict(this.entryData[s][v][g]);
        const progressPayload = this.buildEntryProgressPayload(
          this.calculateEntryProgressForSlot(s, v, g)
        );

        const payload = {
          study_id: this.study?.metadata?.id,
          subject_index: s,
          visit_index: v,
          group_index: g,
          data: dictData,
          skipped_required_flags: rawSkipFlags,
          ...progressPayload,
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
          else this.existingEntries.push(resp.data);
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
            progress_status: resp?.data?.progress_status ?? progressPayload.progress_status,
            progress_percentage: resp?.data?.progress_percentage ?? progressPayload.progress_percentage,
            progress_completed: resp?.data?.progress_completed ?? progressPayload.progress_completed,
            progress_total: resp?.data?.progress_total ?? progressPayload.progress_total,
            progress_skipped: resp?.data?.progress_skipped ?? progressPayload.progress_skipped,
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
  const originalManualDateInputErrors = this.manualDateInputErrors;
  const originalCalcWarnings = this.calcWarnings;
  const originalCurrentSubjectIndex = this.currentSubjectIndex;
  const originalCurrentVisitIndex = this.currentVisitIndex;
  const originalCurrentGroupIndex = this.currentGroupIndex;

  try {
    // lightweight deep clone only for simulation
    this.entryData = JSON.parse(JSON.stringify(this.entryData || []));
    this.skipFlags = JSON.parse(JSON.stringify(this.skipFlags || []));
    this.validationErrors = {};
    this.manualDateInputErrors = {};
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
    this.manualDateInputErrors = originalManualDateInputErrors;
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
      this.unlockImportedPreviousVisit(mIdx, fIdx);
      this.setDeepSkip(this.currentSubjectIndex, this.currentVisitIndex, this.currentGroupIndex, mIdx, fIdx, false);
      this.clearError(mIdx, fIdx);
      this.clearCalcWarningFor(mIdx, fIdx);
    });

    this.showSelection = false;
    this.validationErrors = {};
    this.manualDateInputErrors = {};
    this.calcWarnings = {};

    this.runAllCalculationsForCurrentCell();
    this.markEntryDirty();
    this.rebuildEntryProgressCache();

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
          this.unlockImportedPreviousVisit(mIdx, fIdx);
          this.setDeepSkip(s, v, g, mIdx, fIdx, false);
          this.clearError(mIdx, fIdx);
          this.clearCalcWarningFor(mIdx, fIdx);
        });

        this.runAllCalculationsForCurrentCell();
        this.markEntryDirty();
        this.rebuildEntryProgressCache();

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
    async onShareDialogGenerate(cfg) {
      if (this.shareLinkGenerating) return;

      this.shareConfig = {
        permission: cfg.permission,
        maxUses: cfg.maxUses,
        expiresInDays: cfg.expiresInDays,
        allowed_section_ids: cfg.allowed_section_ids || [],
      };

      this.generatedLink = "";
      this.generatedLinks = [];
      this.copyStatus = "";
      this.shareLinkGenerating = true;

      try {
        await this.createShareLink();
      } finally {
        this.shareLinkGenerating = false;
      }
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
      return evaluateFieldVisibility(
        this.study,
        this.selectedModels,
        cellData,
        mIdx,
        fIdx,
        new Set(),
        this.getFieldLookup()
      );
    },

    hasVisibleFieldsInSection(mIdx) {
      const cellData = this.getCurrentCellData();
      return sectionHasVisibleFields(
        this.study,
        this.selectedModels,
        cellData,
        mIdx,
        this.getFieldLookup()
      );
    },
    fieldCalcWarning(mIdx, fIdx) {
      const runtimeKey = this.currentCalcKey(mIdx, fIdx);
      const runtimeWarning = this.calcWarnings?.[runtimeKey];
      if (runtimeWarning) return runtimeWarning;

      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
      if (!field) return "";

      const key = this.progressFieldKey(mIdx, fIdx);
      if (!this.runtimeCalculationFormulaCache.has(key)) {
        this.runtimeCalculationFormulaCache.set(
          key,
          getCalculationFormulaForField(
            this.study,
            this.selectedModels,
            field,
            this.getFieldLookup()
          ) || ""
        );
      }
      return this.runtimeCalculationFormulaCache.get(key);
    },
    popupReminderMessages(mIdx, fIdx) {
      const cellData = this.getCurrentCellData();

      if (this.runtimePopupReminderIndexModels !== this.selectedModels) {
        this.runtimePopupReminderIndexModels = this.selectedModels;
        this.runtimePopupReminderIndex = buildPopupReminderIndex(this.selectedModels);
      }

      return getPopupReminderMessagesForField(
        this.study,
        this.selectedModels,
        cellData,
        mIdx,
        fIdx,
        this.getFieldLookup(),
        this.runtimePopupReminderIndex
      );
    },

    hasPopupReminder(mIdx, fIdx) {
      return this.popupReminderMessages(mIdx, fIdx).length > 0;
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
      if (!field) return false;
      if (field.computed || field.isCalculatedField) return true;

      if (this.runtimeCalculatedStudy !== this.study) {
        this.runtimeCalculatedStudy = this.study;
        this.runtimeCalculatedTargetIds = getCalculatedTargetIdSet(this.study);
      }
      const keys = [
        field?._id,
        field?.id,
        field?.field_id,
        field?.uid,
        field?.key,
        field?.name,
      ].filter(Boolean);
      return keys.some((key) => this.runtimeCalculatedTargetIds.has(String(key)));
    },

    isReadonlyField(field, mIdx, fIdx) {
      return (
        !!field?.constraints?.readonly ||
        !this.canEdit ||
        this.isCalculatedRuntimeField(mIdx, fIdx) ||
        this.isImportedFromPreviousVisit(mIdx, fIdx)
      );
    },
    slotFieldKey(s, v, g, m, f) {
      return `${s}-${v}-${g}-${m}-${f}`;
    },

    currentSlotFieldKey(mIdx, fIdx) {
      return this.slotFieldKey(
        this.currentSubjectIndex,
        this.currentVisitIndex,
        this.currentGroupIndex,
        mIdx,
        fIdx
      );
    },

    isImportSupportedField(field) {
      const type = String(field?.type || "").toLowerCase();
      return !["file", "button"].includes(type);
    },

    canShowPreviousVisitImport(field, mIdx, fIdx) {
      if (!this.canEdit) return false;
      if (this.currentSubjectIndex == null || this.currentVisitIndex == null || this.currentGroupIndex == null) return false;
      if (this.currentVisitIndex <= 0) return false;
      if (!this.isImportSupportedField(field)) return false;
      if (this.isCalculatedRuntimeField(mIdx, fIdx)) return false;
      return true;
    },

    isImportedFromPreviousVisit(mIdx, fIdx) {
      const key = this.currentSlotFieldKey(mIdx, fIdx);
      return !!this.importedPreviousVisitLocks?.[key];
    },

    importedPreviousVisitLabel(mIdx, fIdx) {
      const key = this.currentSlotFieldKey(mIdx, fIdx);
      const meta = this.importedPreviousVisitLocks?.[key];
      if (!meta) return "previous visit";
      return meta.visitLabel || "previous visit";
    },

    unlockImportedPreviousVisit(mIdx, fIdx) {
      const key = this.currentSlotFieldKey(mIdx, fIdx);
      if (!this.importedPreviousVisitLocks[key]) return;

      const next = { ...(this.importedPreviousVisitLocks || {}) };
      delete next[key];
      this.importedPreviousVisitLocks = next;
      this.markEntryDirty();
    },

    closePreviousVisitImportDialog() {
      this.showPreviousVisitImportDialog = false;
      this.previousVisitImportOptions = [];
      this.previousVisitImportContext = null;
    },

    extractFieldValueFromEntry(entry, mIdx, fIdx) {
      if (!entry) return undefined;

      if (entry.data && !Array.isArray(entry.data) && typeof entry.data === "object") {
        const section = this.selectedModels?.[mIdx];
        if (!section) return undefined;

        const sKey = this.sectionDictKey(section);
        const secObj = entry.data[sKey] || {};
        const field = section.fields?.[fIdx];

        return this.getValueFromSectionDict(secObj, field, fIdx);
      }

      if (Array.isArray(entry.data)) {
        return entry.data?.[mIdx]?.[fIdx];
      }

      return undefined;
    },

    hasReusablePreviousValue(field, value) {
      const type = String(field?.type || "").toLowerCase();

      if (!this.isImportSupportedField(field)) return false;

      if (type === "table") {
        return hasPreviousVisitTableData(field, value);
      }
      if (type === "checkbox") return typeof value === "boolean";
      if (Array.isArray(value)) return value.length > 0;
      if (typeof value === "number") return Number.isFinite(value);
      if (typeof value === "string") return value.trim() !== "";
      if (value == null) return false;

      return true;
    },

    formatPreviousVisitDisplayValue(value) {
      if (Array.isArray(value)) return value.join(", ");
      if (typeof value === "boolean") return value ? "Checked" : "Unchecked";
      if (value == null) return "";
      return String(value);
    },

    buildPreviousVisitImportOptions(mIdx, fIdx) {
      const s = this.currentSubjectIndex;
      const g = this.currentGroupIndex;
      const currentVisit = this.currentVisitIndex;
      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];

      if (s == null || g == null || currentVisit == null || !field) return [];

      const out = [];

      for (let visitIdx = currentVisit - 1; visitIdx >= 0; visitIdx--) {
        const entry = this.getBestEntryFor(s, visitIdx, g);
        if (!entry) continue;

        const rawValue = this.extractFieldValueFromEntry(entry, mIdx, fIdx);
        if (!this.hasReusablePreviousValue(field, rawValue)) continue;

        const createdAt = entry?.updated_at || entry?.created_at || "";
        let createdAtLabel = "";

        if (createdAt) {
          try {
            createdAtLabel = new Date(createdAt).toLocaleString();
          } catch {
            createdAtLabel = "";
          }
        }

        out.push({
          key: `${visitIdx}-${entry.id || "noid"}`,
          visitIndex: visitIdx,
          visitLabel: this.visitList?.[visitIdx]?.name || `Visit ${visitIdx + 1}`,
          rawValue,
          displayValue: this.formatPreviousVisitDisplayValue(rawValue),
          entryId: entry?.id || null,
          createdAtLabel,
          versionLabel: entry?.form_version ? `Version ${entry.form_version}` : "",
          isTable: String(field?.type || "").toLowerCase() === "table",
          tableColumns:
            String(field?.type || "").toLowerCase() === "table"
              ? buildPreviousVisitTableColumns(field, rawValue)
              : [],
        });

        const added = out[out.length - 1];
        if (added.isTable) {
          added.tableRows = buildPreviousVisitTableRows(
            rawValue,
            added.tableColumns
          );
        }
      }

      return out;
    },

    openPreviousVisitImportDialog(mIdx, fIdx) {
      const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
      if (!field) return;

      const options = this.buildPreviousVisitImportOptions(mIdx, fIdx);

      this.previousVisitImportContext = {
        modelIndex: mIdx,
        fieldIndex: fIdx,
        fieldLabel: field.label || field.name || `Field ${fIdx + 1}`,
      };

      this.previousVisitImportOptions = options;
      this.showPreviousVisitImportDialog = true;
    },

    applyPreviousVisitImport(option) {
      const ctx = this.previousVisitImportContext;
      if (!ctx || !option) return;

      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      const mIdx = ctx.modelIndex;
      const fIdx = ctx.fieldIndex;

      this.ensureSlot(s, v, g);

      const importedValue = option.isTable
        ? selectPreviousVisitTableRows(
            option.rawValue,
            option.selectedRowIndexes
          )
        : option.rawValue;
      this.setDeepValue(s, v, g, mIdx, fIdx, importedValue);
      this.setDeepSkip(s, v, g, mIdx, fIdx, false);
      this.clearError(mIdx, fIdx);
      this.clearCalcWarningFor(mIdx, fIdx);

      const key = this.slotFieldKey(s, v, g, mIdx, fIdx);
      this.importedPreviousVisitLocks = {
        ...(this.importedPreviousVisitLocks || {}),
        [key]: {
          sourceVisitIndex: option.visitIndex,
          sourceEntryId: option.entryId,
          visitLabel: option.visitLabel,
        },
      };

      this.markEntryDirty();
      this.validateField(mIdx, fIdx);
      this.onRuntimeFieldChanged(mIdx, fIdx);
      this.closePreviousVisitImportDialog();
    },

    getFieldLookup() {
      if (this.runtimeFieldLookupModels !== this.selectedModels) {
        this.runtimeFieldLookupModels = this.selectedModels;
        this.runtimeFieldLookup = buildFieldLookup(this.selectedModels);
      }
      return this.runtimeFieldLookup;
    },

    getValueAssignmentFieldLookup() {
      if (this.runtimeValueAssignmentLookupModels !== this.selectedModels) {
        this.runtimeValueAssignmentLookupModels = this.selectedModels;
        this.runtimeValueAssignmentLookup = buildValueAssignmentFieldLookup(
          this.selectedModels
        );
      }
      return this.runtimeValueAssignmentLookup;
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
      const initialAssignmentResult = this.runValueAssignmentsForCell(s, v, g);
      const changedFields = new Set(
        (initialAssignmentResult.updates || []).map((update) =>
          this.progressFieldKey(update.sectionIndex, update.fieldIndex)
        )
      );
      const rules = this.calculationRules || [];
      if (!rules.length) {
        return { ...initialAssignmentResult, changedFields: [...changedFields] };
      }

      const changedField =
        changedMIdx != null && changedFIdx != null
          ? this.selectedModels?.[changedMIdx]?.fields?.[changedFIdx]
          : null;

      let changedKeys = changedField
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

      if (initialAssignmentResult.changed) changedKeys = null;

      const sameValue = (left, right) =>
        Array.isArray(left) || Array.isArray(right)
          ? JSON.stringify(left) === JSON.stringify(right)
          : left === right;
      const maxPasses = Math.min(12, Math.max(2, rules.length + 2));
      let anyChanged = initialAssignmentResult.changed;
      let latestAssignmentResult = initialAssignmentResult;
      let settled = false;

      for (let pass = 0; pass < maxPasses; pass += 1) {
        const currentCellData = this.entryData?.[s]?.[v]?.[g] || [];
        let calculationsChanged = false;

        rules.forEach((rule) => {
          if (!rule?.target) return;

          // The first pass can stay scoped to the manually changed field.
          // Later passes evaluate all rules to settle assignment/calculation chains.
          if (pass === 0 && changedKeys) {
            let touchesChanged = false;

            if (rule.kind === "calc_expr") {
              const defs = Object.values(rule.symbolMap || {});
              touchesChanged = defs.some((def) =>
                changedKeys.has(String(def?.fieldId || ""))
              );
            } else if (Array.isArray(rule.sources)) {
              touchesChanged = rule.sources.some((src) =>
                changedKeys.has(String(src))
              );
            }

            if (!touchesChanged) return;
          }

          const targetMeta = this.getFieldMetaByRuleFieldId(rule.target);
          if (!targetMeta) return;
          const { mIdx, fIdx } = targetMeta;
          const previousValue = currentCellData?.[mIdx]?.[fIdx];
          const result = computeCalculation(
            rule,
            this.selectedModels,
            currentCellData,
            null,
            this.getFieldLookup()
          );

          if (!result.ok) {
            if (!sameValue(previousValue, null)) {
              this.setDeepValue(s, v, g, mIdx, fIdx, null);
              calculationsChanged = true;
              changedFields.add(this.progressFieldKey(mIdx, fIdx));
            }
            this.setCalcWarningByRuleTarget(
              s,
              v,
              g,
              rule.target,
              result.warning || "Calculation could not be applied."
            );
            return;
          }

          if (!sameValue(previousValue, result.value)) {
            this.setDeepValue(s, v, g, mIdx, fIdx, result.value);
            calculationsChanged = true;
            changedFields.add(this.progressFieldKey(mIdx, fIdx));
            this.clearError(mIdx, fIdx);

            const fieldDef = this.selectedModels?.[mIdx]?.fields?.[fIdx];
            if (fieldDef) this.validateField(mIdx, fIdx);
          }
          this.setCalcWarningByRuleTarget(s, v, g, rule.target, "");
        });

        latestAssignmentResult = this.runValueAssignmentsForCell(s, v, g);
        (latestAssignmentResult.updates || []).forEach((update) => {
          changedFields.add(
            this.progressFieldKey(update.sectionIndex, update.fieldIndex)
          );
        });
        anyChanged =
          anyChanged ||
          calculationsChanged ||
          latestAssignmentResult.changed;

        if (!calculationsChanged && !latestAssignmentResult.changed) {
          settled = true;
          break;
        }
        changedKeys = null;
      }

      if (!settled) {
        const warning =
          "Calculated fields and value assignments did not settle. Check for conflicting rules.";
        this.valueAssignmentWarnings = Array.from(
          new Set([...(this.valueAssignmentWarnings || []), warning])
        );
      }

      return {
        changed: anyChanged,
        updates: latestAssignmentResult.updates || [],
        warnings: latestAssignmentResult.warnings || [],
        changedFields: [...changedFields],
      };
    },

    runValueAssignmentsForCell(s, v, g) {
      if (s == null || v == null || g == null) {
        return { changed: false, updates: [], warnings: [] };
      }

      this.ensureSlot(s, v, g);
      const result = evaluateValueAssignments(
        this.study,
        this.selectedModels,
        this.entryData?.[s]?.[v]?.[g] || [],
        this.getValueAssignmentFieldLookup()
      );

      (result.updates || []).forEach((update) => {
        this.setDeepValue(
          s,
          v,
          g,
          update.sectionIndex,
          update.fieldIndex,
          update.value
        );
        this.setDeepSkip(
          s,
          v,
          g,
          update.sectionIndex,
          update.fieldIndex,
          false
        );
        this.clearError(update.sectionIndex, update.fieldIndex);
      });

      if (
        s === this.currentSubjectIndex &&
        v === this.currentVisitIndex &&
        g === this.currentGroupIndex
      ) {
        this.valueAssignmentWarnings = result.warnings || [];
      }

      return {
        changed: (result.updates || []).length > 0,
        updates: result.updates || [],
        warnings: result.warnings || [],
      };
    },

    runAllCalculationsForCurrentCell() {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      if (s == null || v == null || g == null) return;
      this.ensureSlot(s, v, g);
      this.runCalculationsForCell(s, v, g, null, null);
    },

    cancelRuntimeFieldCommit(key) {
      const handle = this.runtimeCommitHandles.get(key);
      if (!handle) return;
      if (handle.frameId != null) window.cancelAnimationFrame(handle.frameId);
      if (handle.timerId != null) window.clearTimeout(handle.timerId);
      this.runtimeCommitHandles.delete(key);
    },

    cancelAllRuntimeFieldCommits() {
      [...this.runtimeCommitHandles.keys()].forEach((key) => {
        this.cancelRuntimeFieldCommit(key);
      });
    },

    queueRuntimeFieldCommit(
      mIdx,
      fIdx,
      { afterPaint = false, updateProgress = true } = {}
    ) {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      if (s == null || v == null || g == null) return;
      this.ensureSlot(s, v, g);

      const key = `${s}|${v}|${g}|${mIdx}|${fIdx}`;
      this.cancelRuntimeFieldCommit(key);
      const handle = { frameId: null, timerId: null };
      this.runtimeCommitHandles.set(key, handle);

      const execute = () => {
        if (this.runtimeCommitHandles.get(key) !== handle) return;
        this.runtimeCommitHandles.delete(key);
        if (
          s !== this.currentSubjectIndex ||
          v !== this.currentVisitIndex ||
          g !== this.currentGroupIndex
        ) return;

        const result = this.runCalculationsForCell(s, v, g, mIdx, fIdx);
        this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
        if (updateProgress) {
          this.refreshEntryProgressFields([
            { mIdx, fIdx },
            ...(result?.changedFields || []),
          ]);
        }
      };

      const scheduleTimer = () => {
        handle.frameId = null;
        handle.timerId = window.setTimeout(execute, afterPaint ? 120 : 0);
      };

      if (afterPaint) {
        handle.frameId = window.requestAnimationFrame(scheduleTimer);
      } else {
        scheduleTimer();
      }
    },

    onLiveFieldInput(mIdx, fIdx) {
      this.markEntryDirty();
      this.clearError(mIdx, fIdx);
      this.queueRuntimeFieldCommit(mIdx, fIdx, {
        afterPaint: true,
        updateProgress: false,
      });
    },

    onNumberFieldBlur(mIdx, fIdx) {
      this.validateField(mIdx, fIdx);
      this.queueRuntimeFieldCommit(mIdx, fIdx, {
        afterPaint: false,
        updateProgress: true,
      });
    },

    onDiscreteFieldChanged(mIdx, fIdx) {
      this.markEntryDirty();
      this.validateField(mIdx, fIdx);
      this.clearError(mIdx, fIdx);
      this.queueRuntimeFieldCommit(mIdx, fIdx, {
        afterPaint: false,
        updateProgress: true,
      });
    },

    onDiscreteFieldBlur(mIdx, fIdx) {
      this.validateField(mIdx, fIdx);
      this.clearError(mIdx, fIdx);
      this.queueRuntimeFieldCommit(mIdx, fIdx, {
        afterPaint: false,
        updateProgress: true,
      });
    },

    onRuntimeFieldChanged(mIdx, fIdx) {
      // user changed something manually -> source errors may go away
      this.clearError(mIdx, fIdx);
      this.queueRuntimeFieldCommit(mIdx, fIdx, {
        afterPaint: false,
        updateProgress: true,
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
        await this.loadExistingEntries(this.study?.metadata?.id);
        this.buildStatusCache();
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

    studyFileRecordsForCell(sIdx, vIdx) {
      return (this.studyFiles || []).filter(
        (file) =>
          Number(file?.subject_index) === Number(sIdx) &&
          Number(file?.visit_index) === Number(vIdx)
      );
    },

    async downloadUploadedFile(file) {
      if (!file) return;

      const url =
        file.source === "url"
          ? file.url
          : String(file.storage_option || "").toLowerCase() === "url"
          ? file.file_path
          : "";

      if (url) {
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }

      const fileId = uploadedFileId(file);
      const studyId = this.study?.metadata?.id;

      if (!fileId || !studyId) {
        this.showDialogMessage("This file is not available for download yet. Please save the data first.");
        return;
      }

      if (!this.token) {
        this.$router.push("/login");
        return;
      }

      try {
        const response = await axios.get(
          `/forms/studies/${studyId}/files/${fileId}/download`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
            responseType: "blob",
          }
        );

        const blob = new Blob([response.data]);
        const objectUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = uploadedFileName(file) || "download";
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(objectUrl);
      } catch (e) {
        console.error("Failed to download uploaded file", e);
        this.showDialogMessage("Failed to download file.");
      }
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

    mergeStudyFileRecordsIntoSlotData(sIdx, vIdx, slotData) {
      if (!Array.isArray(slotData)) return slotData;

      this.studyFileRecordsForCell(sIdx, vIdx).forEach((file) => {
        const context = inferUploadedFileFieldContext(file, this.selectedModels);
        if (!context) return;

        const mIdx = Number(context.sectionIndex);
        const fIdx = Number(context.fieldIndex);
        const field = this.selectedModels?.[mIdx]?.fields?.[fIdx];
        if (!field || String(field.type || "").toLowerCase() !== "file") return;

        const fileId = String(file.id || file.dbId || file.file_id || "");
        if (!fileId) return;

        if (!Array.isArray(slotData[mIdx])) {
          slotData[mIdx] = (this.selectedModels[mIdx]?.fields || []).map((f) =>
            this.defaultForField(f)
          );
        }

        const current = slotData[mIdx][fIdx];
        const currentFiles = Array.isArray(current) ? [...current] : current ? [current] : [];
        const alreadyPresent = currentFiles.some(
          (item) => String(uploadedFileId(item) || "") === fileId
        );
        if (alreadyPresent) return;

        const mergedFile = {
          source: String(file.storage_option || "").toLowerCase() === "url" ? "url" : "local",
          name: file.file_name || uploadedFileName(file),
          dbId: file.id,
          file_path: file.file_path,
          storage_option: file.storage_option || "bids",
          file_name: file.file_name || uploadedFileName(file),
        };

        slotData[mIdx][fIdx] = field.constraints?.allowMultipleFiles
          ? [...currentFiles, mergedFile]
          : mergedFile;
      });

      return slotData;
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
        this.scheduleEntryProgressUpdate();
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
        this.scheduleEntryProgressUpdate();
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
      arr = this.mergeStudyFileRecordsIntoSlotData(s, v, arr);

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
      this.scheduleEntryProgressUpdate();
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
      this.markEntryDirty();
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
      const items = this.buildConstraintList(field);
      return Array.isArray(items) && items.length > 0 && items[0] !== "No constraints.";
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
      if (field.type === "radio" && c.allowMultiple)
        parts.push("Multiple selection: allowed");
      if (
        field.type === "radio" &&
        c.allowMultiple &&
        Array.isArray(c.dominantOptions) &&
        c.dominantOptions.length
      ) {
        parts.push(`Dominant options: ${c.dominantOptions.join(", ")}`);
      }
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

      if (this.highlightedErrorKey === k) {
        this.highlightedErrorKey = "";
      }
    },
    fieldErrors(mIdx, fIdx) {
      return this.validationErrors[this.errorKey(mIdx, fIdx)] || "";
    },

    onDateManualInputState(mIdx, fIdx, state) {
      if (!state || state.valid || state.empty) {
        this.clearDateManualInputError(mIdx, fIdx);
        return;
      }

      const format =
        state.format ||
        this.selectedModels[mIdx]?.fields?.[fIdx]?.constraints?.dateFormat ||
        "dd.MM.yyyy";
      const message = `Please add data in this format: ${format}.`;
      const key = this.errorKey(mIdx, fIdx);
      this.manualDateInputErrors = {
        ...this.manualDateInputErrors,
        [key]: message,
      };
      this.setError(mIdx, fIdx, message);
    },

    clearDateManualInputError(mIdx, fIdx) {
      const key = this.errorKey(mIdx, fIdx);
      if (key in this.manualDateInputErrors) {
        const next = { ...this.manualDateInputErrors };
        delete next[key];
        this.manualDateInputErrors = next;
      }
      this.clearError(mIdx, fIdx);
    },

    goToDashboard() {
      this.$router.push({
        name: "Dashboard",
        query: { openStudies: "true" },
      });
    },

    async loadStudy(studyId) {
      try {
        this.pageError = "";
        const resp = await axios.get(`/forms/studies/${studyId}`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });

        this.study = resp.data;
        this.initializeEntryData();
      } catch (err) {
        console.error("[Entry] loadStudy error", err);

        if (err?.response?.status === 401 || err?.response?.status === 403) {
          this.$router.replace({
            path: "/login",
            query: { redirect: this.$route.fullPath },
          }).catch(() => null);
          return;
        }

        this.study = null;
        this.matrixReady = false;
        this.pageError = this.getApiErrorDetail(err) || "Failed to load study details.";
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
        this.entryData[this.currentSubjectIndex][this.currentVisitIndex][this.currentGroupIndex] =
          this.dictToArray(payload.entry_data || {});
        this.skipFlags[this.currentSubjectIndex][this.currentVisitIndex][this.currentGroupIndex] =
          this.flagsDictToArray(payload.skipped_required_flags || {});
        this.entryIds[this.currentSubjectIndex][this.currentVisitIndex][this.currentGroupIndex] =
          payload.entry_id || null;
        this.currentRevisionToken = String(payload.revision_token || "");
        if (payload.form_version != null) {
          this.selectedVersion = Number(payload.form_version);
        }
        this.runAllCalculationsForCurrentCell();
        this.showSelection = false;
        this.validationErrors = {};
        this.manualDateInputErrors = {};
        this.$nextTick();
        this.allSectionsCollapsed = false;
        this.toggleAllSectionsCollapse();
        this.captureEntryBaseline();

      } catch (e) {
        console.error("[Shared] load error", e);

        this.study = null;
        this.matrixReady = false;
        this.pageError = this.getSharedLoadErrorMessage(e);
      }
    },

    async loadExistingEntries(studyId) {
      try {
        const statusResp = await axios.get(
          `/forms/studies/${studyId}/data_entry_statuses`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
            params: this.safeVersionParams(this.selectedVersion) || {},
          }
        );

        const rows = Array.isArray(statusResp.data)
          ? statusResp.data
          : statusResp.data?.statuses || [];
        const nextStatusRows = new Map();
        const nextStatusMap = new Map();

        rows.forEach((row) => {
          const key = `${row.subject_index}|${row.visit_index}`;
          const progress = this.getStoredEntryProgress(row);
          if (!progress) return;
          nextStatusRows.set(key, {
            status: progress.status,
            percentage: progress.percentage,
            completed: progress.completed,
            total: progress.total,
            skipped: progress.skipped,
          });
          nextStatusMap.set(key, progress.status);
        });

        this.statusRowsMap = nextStatusRows;
        this.statusMap = nextStatusMap;

        if (statusResp.data?.needs_progress_backfill) {
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
        } else {
          this.existingEntries = [];
          this.entriesIndex = new Map();
          this.hydrateCache.clear();
        }
      } catch (err) {
        console.error("Failed to load entry statuses", err);

        if (err?.response?.status === 503) {
          this.study = null;
          this.matrixReady = false;
          this.pageError = this.getApiErrorDetail(err);
          return;
        }

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
        } catch (fallbackErr) {
          console.error("Failed to load existing entries", fallbackErr);
        }
      }
    },

    async loadStudyFiles(studyId) {
      if (this.isShared || !studyId) {
        this.studyFiles = [];
        return;
      }

      try {
        const resp = await axios.get(`/forms/studies/${studyId}/files`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.studyFiles = Array.isArray(resp.data) ? resp.data : [];
        this.hydrateCache.clear();
      } catch (err) {
        console.warn("Failed to load uploaded files", err?.response?.data || err.message);
        if (err?.response?.status === 503) {
          this.study = null;
          this.matrixReady = false;
          this.pageError = this.getApiErrorDetail(err);
          return;
        }
        this.studyFiles = [];
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
          this.unlockImportedPreviousVisit(mIdx, fIdx);
          this.clearError(mIdx, fIdx);
          this.clearCalcWarningFor(mIdx, fIdx);
        });
      });
      this.runAllCalculationsForCurrentCell();
      this.markEntryDirty();
      this.rebuildEntryProgressCache();
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
      this.manualDateInputErrors = {};
      this.calcWarnings = {};
      this.entryDirty = false;
      this.entryProgressFieldCache = new Map();
      this.entryProgressCacheSlot = "";
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
      const nextRowsMap = new Map(this.statusRowsMap || []);
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
          for (const v of vIndices) {
            const key = `${s}|${v}`;
            nextMap.set(key, "none");
            nextRowsMap.delete(key);
          }
          continue;
        }

        for (const v of vIndices) {
          const key = `${s}|${v}`;
          const statusRow = this.statusRowsMap?.get(key);
          if (statusRow?.status) {
            nextMap.set(key, statusRow.status);
            continue;
          }

          const e = this.getBestEntryFor(s, v, g);

          if (!e) {
            nextMap.set(key, "none");
            nextRowsMap.delete(key);
            continue;
          }

          const row = this.statusRowFromSavedEntry(e, v, g);
          if (row?.status) {
            nextMap.set(key, row.status);
            nextRowsMap.set(key, row);
            continue;
          }

          nextMap.set(key, "none");
          nextRowsMap.delete(key);
        }
      }

      this.statusMap = nextMap;
      this.statusRowsMap = nextRowsMap;
    },

    statusClassFast(sIdx, vIdx) {
      const map = this.statusMap instanceof Map ? this.statusMap : new Map();
      const s = map.get(`${sIdx}|${vIdx}`) || "none";
      return s === "skipped" ? "status-skipped" : `status-${s}`;
    },

    statusProgressFast(sIdx, vIdx) {
      const row = this.statusRowsMap instanceof Map
        ? this.statusRowsMap.get(`${sIdx}|${vIdx}`)
        : null;
      if (!row) return { percentage: 0, label: "", status: "none" };

      const percentage = Math.max(0, Math.min(100, Number(row.percentage || 0)));
      return {
        percentage,
        label: row.status === "none" ? "" : `${percentage}%`,
        status: row.status || "none",
      };
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

      const arr = this.mergeStudyFileRecordsIntoSlotData(s, v, this.dictToArray(slot?.data || {}));
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

      // The entry screen can build its progress cache while this asynchronous
      // slot request is still loading, which leaves a valid cache containing
      // only the empty field skeleton. Rebuild after the saved values and skip
      // flags are applied so the initial bar matches the matrix calculation.
      if (
        !this.showSelection &&
        s === this.currentSubjectIndex &&
        v === this.currentVisitIndex &&
        g === this.currentGroupIndex
      ) {
        this.entryProgressFieldCache = new Map();
        this.entryProgressCacheSlot = "";
        this.scheduleEntryProgressUpdate({ immediate: true });
      }
    },

    async reloadLatestAfterConflict(latest) {
      if (!latest) return;
      this.applyLoadedSlotState(latest);
      await this.$nextTick();
      this.validationErrors = {};
      this.manualDateInputErrors = {};
      this.calcWarnings = {};
    },

    parseEntryBaseline() {
      try {
        const parsed = JSON.parse(this.entryBaselineSnapshot || "{}");
        return {
          data: Array.isArray(parsed?.data) ? parsed.data : this.makeSectionFieldSkeleton(),
          skips: Array.isArray(parsed?.skips) ? parsed.skips : this.makeSkipSkeleton(),
        };
      } catch (error) {
        console.warn("Unable to parse the data-entry baseline", error);
        return {
          data: this.makeSectionFieldSkeleton(),
          skips: this.makeSkipSkeleton(),
        };
      }
    },

    flagsDictToArray(flagsDict) {
      return (this.selectedModels || []).map((section) => {
        const sectionKey = this.sectionDictKey(section);
        const sectionFlags =
          flagsDict && typeof flagsDict === "object" ? flagsDict[sectionKey] : null;
        return (section?.fields || []).map((field, fieldIndex) =>
          !!this.getValueFromSectionDict(sectionFlags, field, fieldIndex)
        );
      });
    },

    entryConflictLabels(conflict) {
      const sectionIndex = (this.selectedModels || []).findIndex(
        (section) => this.sectionDictKey(section) === conflict.sectionKey
      );
      const section = this.selectedModels?.[sectionIndex] || null;
      const fieldIndex = (section?.fields || []).findIndex(
        (field, index) => this.fieldDictKey(field, index) === conflict.fieldKey
      );
      const field = section?.fields?.[fieldIndex] || null;

      return {
        ...conflict,
        field: field || {},
        fieldType: String(field?.type || "text").toLowerCase(),
        sectionLabel: section?.title || conflict.sectionKey || "Other",
        fieldLabel:
          field?.label ||
          field?.title ||
          field?.name ||
          conflict.fieldKey ||
          "Field",
      };
    },

    expandTableEntryConflicts(dataMerge) {
      const expanded = [];

      (dataMerge?.conflicts || []).forEach((conflict) => {
        const labeled = this.entryConflictLabels(conflict);
        if (labeled.fieldType !== "table") {
          expanded.push(labeled);
          return;
        }

        const tableMerge = mergeTableFieldConflict({
          parentKey: conflict.key,
          sectionKey: conflict.sectionKey,
          fieldKey: conflict.fieldKey,
          field: labeled.field,
          baseValue: conflict.originalValue,
          localValue: conflict.localValue,
          latestValue: conflict.latestValue,
        });

        if (!dataMerge.merged[conflict.sectionKey]) {
          dataMerge.merged[conflict.sectionKey] = {};
        }
        dataMerge.merged[conflict.sectionKey][conflict.fieldKey] =
          tableMerge.mergedValue;

        tableMerge.conflicts.forEach((cellConflict) => {
          if (cellConflict.conflictKind === "concurrent-table-row-addition") {
            expanded.push({
              ...cellConflict,
              sectionLabel: labeled.sectionLabel,
              fieldLabel: `${labeled.fieldLabel} · Row ${cellConflict.tableRowIndex + 1} · New row`,
              field: {
                ...labeled.field,
                type: "table-row",
                conflictColumns: cellConflict.tableColumns,
              },
              fieldType: "table-row",
            });
            return;
          }

          const columnField = {
            ...(cellConflict.tableColumn || {}),
            type: cellConflict.tableColumnType || "text",
          };
          expanded.push({
            ...cellConflict,
            sectionLabel: labeled.sectionLabel,
            fieldLabel: `${labeled.fieldLabel} · Row ${cellConflict.tableRowIndex + 1} · ${cellConflict.tableColumnLabel}`,
            field: columnField,
            fieldType: String(columnField.type || "text").toLowerCase(),
          });
        });
      });

      return expanded;
    },

    setConflictRetryState(dataDict, skipFlags, latest) {
      const s = this.currentSubjectIndex;
      const v = this.currentVisitIndex;
      const g = this.currentGroupIndex;
      this.ensureSlot(s, v, g);

      this.entryData[s][v][g] = this.dictToArray(dataDict || {});
      this.skipFlags[s][v][g] = this.normalizeSkipFlagsShape(skipFlags);
      this.entryIds[s][v][g] = latest?.entry_id || null;
      this.currentRevisionToken = String(latest?.revision_token || "");

      const latestDataArray = this.dictToArray(latest?.data || {});
      const latestSkipFlags = this.normalizeSkipFlagsShape(
        latest?.skipped_required_flags || []
      );
      this.entryBaselineSnapshot = JSON.stringify({
        data: latestDataArray,
        skips: latestSkipFlags,
        locks: this.importedPreviousVisitLocks || {},
      });
      this.entryDirty = true;
    },

    async handleEntrySaveConflict(latest, localData, localSkipFlags) {
      if (!latest) {
        this.showDialogMessage(
          "Another person changed this entry. Your values are still here; please try saving again."
        );
        return;
      }

      const baseline = this.parseEntryBaseline();
      const dataMerge = mergeDataEntryFields(
        this.arrayToDict(baseline.data),
        localData || {},
        latest.data || {}
      );

      const latestSkipArray = this.normalizeSkipFlagsShape(
        latest.skipped_required_flags || []
      );
      const skipMerge = mergeDataEntryFields(
        this.flagsArrayToDict(baseline.skips),
        this.flagsArrayToDict(localSkipFlags),
        this.flagsArrayToDict(latestSkipArray)
      );
      const mergedSkipArray = this.flagsDictToArray(skipMerge.merged);
      const displayConflicts = this.expandTableEntryConflicts(dataMerge);

      if (!displayConflicts.length) {
        this.setConflictRetryState(dataMerge.merged, mergedSkipArray, latest);
        await this.$nextTick();
        await this.submitData();
        return;
      }

      this.pendingEntryConflict = {
        latest,
        mergedData: dataMerge.merged,
        mergedSkipFlags: mergedSkipArray,
        conflicts: displayConflicts,
      };
      this.entryConflicts = displayConflicts;
      this.showEntryConflictDialog = true;
    },

    cancelEntryConflictResolution() {
      this.showEntryConflictDialog = false;
      this.entryConflicts = [];
      this.pendingEntryConflict = null;
      this.entryDirty = true;
    },

    async confirmEntryConflictResolution(decisions) {
      const pending = this.pendingEntryConflict;
      if (!pending) return;

      const resolvedData = applyConflictDecisions(
        pending.mergedData,
        pending.conflicts,
        decisions
      );

      this.showEntryConflictDialog = false;
      this.entryConflicts = [];
      this.pendingEntryConflict = null;
      this.setConflictRetryState(
        resolvedData,
        pending.mergedSkipFlags,
        pending.latest
      );
      await this.$nextTick();
      await this.submitData();
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
    onEntryVisitSelectorChange(event) {
      const nextVisitIndex = Number(event?.target?.value);
      const previousVisitIndex = this.currentVisitIndex;

      if (
        !Number.isInteger(nextVisitIndex) ||
        nextVisitIndex < 0 ||
        nextVisitIndex >= this.visitList.length
      ) {
        if (event?.target) event.target.value = previousVisitIndex;
        return;
      }

      if (nextVisitIndex === previousVisitIndex) return;

      if (this.hasUnsavedEntryChanges) {
        if (event?.target) event.target.value = previousVisitIndex;

        this.showDialogMessage(
          "Please save the current data before changing the visit."
        );
        return;
      }

      this.switchEntryVisitForCurrentSubject(nextVisitIndex);
    },

    async switchEntryVisitForCurrentSubject(nextVisitIndex) {
      if (this.isShared) return;

      const s = this.currentSubjectIndex;
      const g = this.currentGroupIndex;

      if (s == null || g == null || g < 0) return;

      this.currentVisitIndex = nextVisitIndex;

      this.ensureSlot(s, this.currentVisitIndex, g);
      this.prepareAssignmentsLookup();

      this.validationErrors = {};
      this.manualDateInputErrors = {};
      this.calcWarnings = {};
      this.tableValidationStates = {};
      this.highlightedErrorKey = "";
      this.collapsedSections = {};
      this.allSectionsCollapsed = false;
      this.currentRevisionToken = "";

      this.visitLoading = true;

      try {
        await this.loadCurrentSlotState();

        this.runAllCalculationsForCurrentCell();

        await this.$nextTick();

        this.allSectionsCollapsed = false;
        this.toggleAllSectionsCollapse();

        this.captureEntryBaseline();
        this.updateFloatingScrollMode();

        const root = this.getScrollRoot();
        if (
          root === document.scrollingElement ||
          root === document.documentElement ||
          root === document.body
        ) {
          window.scrollTo({ top: 0, behavior: "smooth" });
        } else {
          root.scrollTo({ top: 0, behavior: "smooth" });
        }
      } catch (e) {
        console.error("Failed to switch entry visit", e);
        this.showDialogMessage("Failed to load data for the selected visit.");
      } finally {
        this.visitLoading = false;
      }
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
      this.manualDateInputErrors = {};
      this.calcWarnings = {};

      this.visitLoading = true;
      await this.loadCurrentSlotState();
      this.runAllCalculationsForCurrentCell();
      await this.$nextTick();
      this.allSectionsCollapsed = false;
      this.toggleAllSectionsCollapse();
      this.captureEntryBaseline();
      this.visitLoading = false;
    },

    backToSelection() {
      if (this.isShared) return;
      this.detachFloatingScrollListener();
      this.buildStatusCache();
      this.showSelection = true;
      this.showDetails = false;
      this.currentSubjectIndex = null;
      this.currentVisitIndex = null;
      this.currentGroupIndex = 0;
      this.validationErrors = {};
      this.manualDateInputErrors = {};
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
      this.markEntryDirty();
      this.refreshEntryProgressFields([{ mIdx, fIdx }]);
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

      const manualDateMessage =
        this.manualDateInputErrors[this.errorKey(mIdx, fIdx)];
      if (def.type === "date" && manualDateMessage) {
        const fmt = cons.dateFormat || "dd.MM.yyyy";
        if (val && parseDateByConfiguredFormat(val, fmt)) {
          this.clearDateManualInputError(mIdx, fIdx);
        } else {
          this.setError(mIdx, fIdx, manualDateMessage);
          return false;
        }
      }

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
        const parse = (s) => parseDateByConfiguredFormat(s, fmt);
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

      if (!this.isShared && studyId) {
        await this.loadStudyFiles(studyId);
      }
    },

    async submitData() {
      if (!this.canEdit) {
        this.showDialogMessage("This shared link is view-only.");
        return;
      }

      this.cancelAllRuntimeFieldCommits();
      this.applyTransformsForSection();
      this.cancelAllRuntimeFieldCommits();
      this.runAllCalculationsForCurrentCell();

      this.validationMountAllSections = true;
      await this.$nextTick();
      const ok = this.validateCurrentSection();
      const tableFieldsInvalid = this.assignedModelIndices.some((mIdx) => {
        const fields = this.selectedModels?.[mIdx]?.fields || [];
        return fields.some((field, fIdx) => {
          if (field?.type !== "table") return false;
          if (!this.isFieldVisible(mIdx, fIdx)) return false;
          return !this.validateField(mIdx, fIdx);
        });
      });
      this.validationMountAllSections = false;
      this.rebuildEntryProgressCache();
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
          this.$nextTick(() => {
            this.goToFirstValidationError();
          });

          this.showDialogMessage("Please fix validation errors before saving.");
          return;
        }

      const requiredFailures = this.computeRequiredFailures();
      if (requiredFailures.length) {
          this.highlightedErrorKey = "";

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

      const rawSkipFlags = this.normalizeSkipFlagsShape(this.skipFlags[s][v][g]);
      this.skipFlags[s][v][g] = rawSkipFlags;
      const dictData = this.arrayToDict(this.entryData[s][v][g]);
      const progressPayload = this.buildEntryProgressPayload(
        this.calculateEntryProgressForSlot(s, v, g)
      );

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
        ...progressPayload,
      };

      try {
        if (this.isShared) {
          const auditLabel = hasAnySkip ? "Shared link data Entry (Skipped Required)" : "Shared link data Entry";
          const resp = await axios.post(`/forms/shared/${this.shareToken}/data`, payload, {
            params: {
              audit_label: auditLabel,
              expected_revision_token: this.currentRevisionToken,
            },
          });

          const saved = {
            id: resp?.data?.id,
            study_id: payload.study_id,
            subject_index: s,
            visit_index: v,
            group_index: g,
            data: dictData,
            skipped_required_flags: resp?.data?.skipped_required_flags ?? rawSkipFlags,
            progress_status: resp?.data?.progress_status ?? progressPayload.progress_status,
            progress_percentage: resp?.data?.progress_percentage ?? progressPayload.progress_percentage,
            progress_completed: resp?.data?.progress_completed ?? progressPayload.progress_completed,
            progress_total: resp?.data?.progress_total ?? progressPayload.progress_total,
            progress_skipped: resp?.data?.progress_skipped ?? progressPayload.progress_skipped,
            form_version: resp?.data?.form_version ?? this.selectedVersion,
            created_at: resp?.data?.created_at ?? new Date().toISOString(),
          };
          (this.existingEntries = this.existingEntries || []).push(saved);
          this.currentRevisionToken = String(resp?.data?.revision_token || "");
          this.entryIds[s][v][g] = resp?.data?.id || null;

          this.showDialogMessage(this.buildSaveSuccessMessage("saved"));
          this.captureEntryBaseline();
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

          this.showDialogMessage(
              this.buildSaveSuccessMessage("updated")
            );
          const idx = this.existingEntries.findIndex((x) => x.id === existingId);
          if (idx >= 0) this.existingEntries.splice(idx, 1, resp.data);
          else this.existingEntries.push(resp.data);
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
            progress_status: resp?.data?.progress_status ?? progressPayload.progress_status,
            progress_percentage: resp?.data?.progress_percentage ?? progressPayload.progress_percentage,
            progress_completed: resp?.data?.progress_completed ?? progressPayload.progress_completed,
            progress_total: resp?.data?.progress_total ?? progressPayload.progress_total,
            progress_skipped: resp?.data?.progress_skipped ?? progressPayload.progress_skipped,
            form_version: resp?.data?.form_version ?? this.selectedVersion,
            created_at: resp?.data?.created_at ?? new Date().toISOString(),
          };
          (this.existingEntries = this.existingEntries || []).push(saved);
          this.showDialogMessage(
          this.buildSaveSuccessMessage("saved")
        );
        }

        const latestSlot = await this.fetchRevisionTokenForSlot(s, v, g, this.selectedVersion);
        if (latestSlot) {
          this.applyLoadedSlotState(latestSlot);
        }
        this.captureEntryBaseline();
        this.rebuildEntriesIndex();
        this.hydrateCache.delete(`${s}|${v}|${g}|${this.selectedVersion}`);
        this.applyVersionView();
        this.updateStatusCacheFor(s, v, g);
      } catch (err) {
        console.error(err);

        if (err?.response?.status === 409) {
          const latest = err?.response?.data?.detail?.latest || null;
          await this.handleEntrySaveConflict(latest, dictData, rawSkipFlags);
          return;
        }

        this.showDialogMessage(
          err?.response?.status === 503
            ? this.getApiErrorDetail(err)
            : "Failed to save data. Check console for details."
        );
      }
    },

        updateStatusCacheFor(s, v, g) {
      const e = this.getBestEntryFor(s, v, g);
      const key = `${s}|${v}`;

      const nextMap = new Map(this.statusMap || []);

      if (!e) {
        nextMap.set(key, "none");
        const nextRowsMap = new Map(this.statusRowsMap || []);
        nextRowsMap.delete(key);
        this.statusRowsMap = nextRowsMap;
        this.statusMap = nextMap;
        return;
      }

      const row = this.statusRowFromSavedEntry(e, v, g);
      if (row?.status) {
        nextMap.set(key, row.status);
        const nextRowsMap = new Map(this.statusRowsMap || []);
        nextRowsMap.set(key, row);
        this.statusRowsMap = nextRowsMap;
        this.statusMap = nextMap;
        return;
      }

      nextMap.set(key, "none");
      const nextRowsMap = new Map(this.statusRowsMap || []);
      nextRowsMap.delete(key);
      this.statusRowsMap = nextRowsMap;
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
      this.skipSelections = {};

      this.$nextTick(() => {
        this.validateCurrentSection();
        this.highlightedErrorKey = "";
        this.goToFirstValidationError();
      });
    },
    jumpToField(item) {
      this.showSkipDialog = false;

      if (!item) return;

      this.$nextTick(() => {
        this.revealValidationError({
          key: item.key,
          sectionIndex: item.sectionIndex,
          fieldIndex: item.fieldIndex,
          sectionTitle: item.sectionTitle,
          fieldLabel: item.fieldLabel,
          message: this.validationErrors?.[item.key] || "",
        });
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
          id: String(sec?._id || sec?.id || sec?.uuid || "").trim(),
          title: sec?.title || "Untitled Section",
        }))
        .filter((s) => s.id);

      this.shareConfig = {
        permission: "view",
        maxUses: 1,
        expiresInDays: 7,
        allowed_section_ids: available.map((x) => x.id),
      };

      this.generatedLink = "";
      this.generatedLinks = [];
      this.copyStatus = "";
      this.showShareDialog = true;

      this.loadSharedLinks();
    },
    async loadSharedLinks() {
      if (!this.study?.metadata?.id || this.isShared) return;

      this.sharedLinksLoading = true;

      try {
        const resp = await axios.get(`/forms/studies/${this.study.metadata.id}/share-links`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });

        this.sharedLinks = Array.isArray(resp.data) ? resp.data : [];
      } catch (err) {
        console.error("Failed to load shared links", err);
        this.sharedLinks = [];

        if (err.response?.status === 403) {
          this.permissionError = true;
        }
      } finally {
        this.sharedLinksLoading = false;
      }
    },

    async revokeSharedLink(link) {
      const token = String(link?.token || "").trim();
      if (!token) return;

      try {
        await axios.post(
          `/forms/studies/${this.study.metadata.id}/share-links/${encodeURIComponent(token)}/revoke`,
          {},
          {
            headers: { Authorization: `Bearer ${this.token}` },
            params: { audit_label: "Revoke - Shareable Link" },
          }
        );

        await this.loadSharedLinks();
        this.showDialogMessage("Shared link invalidated successfully.");
      } catch (err) {
        console.error("Failed to revoke shared link", err);

        if (err.response?.status === 403) {
          this.permissionError = true;
        } else {
          this.showDialogMessage("Failed to invalidate shared link.");
        }
      }
    },

    async copyAnySharedLink(link) {
      const url = String(link?.link || link?.url || "").trim();

      if (!url) {
        this.copyStatus = "No link available to copy.";
        return;
      }

      try {
        await navigator.clipboard.writeText(url);
        this.copyStatus = "Copied!";
      } catch {
        this.copyStatus = "Could not copy link.";
      }
    },

    exportSharedLinksCsv(rows) {
      const items = Array.isArray(rows) && rows.length ? rows : this.sharedLinks;

      if (!items.length) {
        this.showDialogMessage("No shared links available to export.");
        return;
      }

      const csvEscape = (value) => {
        const text = String(value ?? "");
        return `"${text.replace(/"/g, '""')}"`;
      };

      const headers = [
        "Study Name",
        "Subject ID",
        "Group",
        "Visit",
        "Sections",
        "Permission",
        "Status",
        "Max Uses",
        "Used Count",
        "Remaining Uses",
        "Expires At",
        "Created At",
        "Shared Link",
      ];

      const lines = [headers.map(csvEscape).join(",")];

      items.forEach((item) => {
        const sectionTitles = Array.isArray(item.section_titles)
          ? item.section_titles
          : Array.isArray(item.sections)
            ? item.sections
            : [];

        lines.push([
          item.study_name || item.studyName || this.study?.metadata?.study_name || "",
          item.subject_id || item.subjectId || item.subject_label || "",
          item.group || "",
          item.visit_name || item.visitName || item.visit_label || "",
          sectionTitles.length ? sectionTitles.join("; ") : item.sections || "",
          item.permission || "",
          item.status || "",
          item.max_uses ?? item.maxUses ?? "",
          item.used_count ?? item.usedCount ?? "",
          item.remaining_uses ?? item.remainingUses ?? "",
          item.expires_at || item.expiresAt || "",
          item.created_at || item.createdAt || "",
          item.link || item.url || "",
        ].map(csvEscape).join(","));
      });

      const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");

      a.href = url;
      a.download = `shared-links-${this.study?.metadata?.id || "study"}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    async onBulkShareDialogGenerate(cfg) {
      if (this.shareLinkGenerating) return;

      const rows = Array.isArray(cfg?.rows) ? cfg.rows : [];
      const readyRows = rows.filter((row) => row.status === "Ready");

      if (!readyRows.length) {
        this.showDialogMessage("No valid subject/visit combinations are available for link generation.");
        return;
      }

      this.shareConfig = {
        permission: cfg.permission,
        maxUses: cfg.maxUses,
        expiresInDays: cfg.expiresInDays,
        allowed_section_ids: cfg.allowed_section_ids || [],
      };

      this.generatedLink = "";
      this.generatedLinks = [];
      this.copyStatus = "";
      this.shareLinkGenerating = true;

      // Let Vue update the button text/disabled state before starting the bulk loop.
      await this.$nextTick();

      const created = [];
      let failed = 0;

      try {
        for (const row of readyRows) {
          try {
            const payload = {
              study_id: this.study.metadata.id,
              subject_index: row.subjectIndex,
              visit_index: row.visitIndex,
              group_index: this.shareParams.groupIndex,
              permission: cfg.permission,
              max_uses: cfg.maxUses,
              expires_in_days: cfg.expiresInDays,
              allowed_section_ids: row.sectionIds || [],
            };

            const resp = await axios.post("/forms/share-link/", payload, {
              headers: { Authorization: `Bearer ${this.token}` },
              params: { audit_label: "Bulk Create - Shareable Link" },
            });

            created.push({
              studyName: this.study?.metadata?.study_name || "",
              subjectIndex: row.subjectIndex,
              subjectId: row.subjectId,
              group: row.group,
              visitIndex: row.visitIndex,
              visitName: row.visitName,
              sections: row.sectionTitles || [],
              permission: cfg.permission,
              maxUses: cfg.maxUses,
              expiresInDays: cfg.expiresInDays,
              link: resp.data.link,
              token: resp.data.token,
              createdAt: new Date().toISOString(),
            });
          } catch (err) {
            failed += 1;
            console.error("Bulk shared link generation failed", row, err);
          }
        }

        this.generatedLinks = created;

        if (created.length === 1) {
          this.generatedLink = created[0].link;
        }

        await this.$nextTick();

        await this.loadSharedLinks();

        if (failed) {
          this.showDialogMessage(`${created.length} link(s) generated. ${failed} link(s) failed.`);
        } else {
          this.showDialogMessage(`${created.length} shared link(s) generated successfully.`);
        }
      } finally {
        this.shareLinkGenerating = false;
      }
    },
    async createShareLink() {
      const { subjectIndex, visitIndex, groupIndex } = this.shareParams;

      if (
        subjectIndex == null ||
        visitIndex == null ||
        groupIndex == null
      ) {
        this.showDialogMessage("Please select a subject and visit before creating a shared link.");
        return false;
      }

      try {
        const payload = {
          study_id: this.study.metadata.id,
          subject_index: subjectIndex,
          visit_index: visitIndex,
          group_index: groupIndex,
          permission: this.shareConfig.permission,
          max_uses: this.shareConfig.maxUses,
          expires_in_days: this.shareConfig.expiresInDays,
          allowed_section_ids: this.shareConfig.allowed_section_ids || [],
        };

        const resp = await axios.post("/forms/share-link/", payload, {
          headers: { Authorization: `Bearer ${this.token}` },
          params: { audit_label: "Create - Sharable Link" },
        });

        this.generatedLink = resp.data?.link || "";
        this.generatedLinks = [];
        this.copyStatus = "";

        await this.$nextTick();

        // Refresh manage tab data after the generated card is already reactive.
        await this.loadSharedLinks();

        return true;
      } catch (err) {
        console.error("Failed to create shared link", err);

        const message =
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          "Failed to create shared link.";

        this.showDialogMessage(message);
        return false;
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

      const existingSubjects = this.sd.subjects || [];
      const inferred = inferSubjectIdConfigFromExistingSubjects(
        existingSubjects,
        this.sd.study || {},
        this.study?.metadata?.study_name || "Study",
        { useLast: true }
      );

      this.subjectIdConfigDraft = {
        ...inferred,
        startNumber: getNextSubjectSequenceNumber(existingSubjects, inferred),
        locked: false,
      };

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
    onSubjectIdConfigDraftChange(config) {
      this.subjectIdConfigDraft = {
        ...normalizeSubjectIdConfig(
          config || {},
          this.sd.study || {},
          this.study?.metadata?.study_name || "Study"
        ),
        locked: false,
      };

      this.generateSubjectDrafts();
    },

    onAssignmentMethodChange(val) {
      this.assignmentMethodDraft = val || "Random";
      this.generateSubjectDrafts();
    },
    generateSubjectDrafts() {
      const count = Number(this.subjectCountDraft) || 0;

      if (count <= 0) {
        this.subjectDrafts = [];
        return;
      }

      const existingSubjects = this.sd.subjects || [];

      const existingIds = new Set(
        existingSubjects
          .map((s) => String(s.id || s.subject_id || "").trim())
          .filter(Boolean)
      );

      const cfg = normalizeSubjectIdConfig(
        this.subjectIdConfigDraft ||
          inferSubjectIdConfigFromExistingSubjects(
            existingSubjects,
            this.sd.study || {},
            this.study?.metadata?.study_name || "Study",
            { useLast: true }
          ),
        this.sd.study || {},
        this.study?.metadata?.study_name || "Study"
      );

      const draftIds = new Set(existingIds);
      const drafts = [];

      for (let idx = 0; idx < count; idx += 1) {
        const sequenceNumber = Number(cfg.startNumber || 1) + idx;

        const id = buildUniqueSubjectId(
          cfg,
          sequenceNumber,
          draftIds,
          this.sd.study || {},
          this.study?.metadata?.study_name || "Study"
        );

        draftIds.add(id);

        drafts.push({
          id,
          group: null,
        });
      }

      this.subjectDrafts = drafts;
      this.applyAssignmentMethod();
    },
    onSubjectsUpdate(list) {
      this.subjectDrafts = Array.isArray(list) ? list : [];
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

    showDialogMessage(message, action = null) {
      this.dialogMessage = message;
      this.dialogAction = action;
      this.showDialog = true;
    },
    closeDialog() {
      const action = this.dialogAction;

      this.showDialog = false;
      this.dialogMessage = "";
      this.dialogAction = null;

      if (action === "backToSelection") {
        this.backToSelection();
      }
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
        this.manualDateInputErrors = {};
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
  width: 100%;
  box-sizing: border-box;
  margin: 24px auto;
  padding: 8px 42px 24px 42px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow-x: visible;
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
  color: #374151;
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

/* ========= Study header container ========= */
.study-header-container {
  margin-bottom: 24px;
  padding: 18px 20px;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.study-header {
  text-align: center;
  margin-bottom: 16px;
  padding: 4px 12px 12px;
}
.study-name {
  font-size: 26px;
  font-weight: 800;
  color: #111827;
  margin: 0 0 8px;
  line-height: 1.2;
}

.study-description {
  font-size: 15px;
  color: #4b5563;
  margin: 0 0 10px;
  line-height: 1.5;
}

.study-meta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 7px 13px;
  margin: 0;
}

.shared-banner {
  display: inline-flex;
  align-items: center;
  margin-top: 10px;
  font-size: 13px;
  color: #374151;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 999px;
  padding: 7px 12px;
}
/* Divider inside header card */
.study-header-container hr {
  margin: 16px 0 0;
  border: 0;
  border-top: 1px solid #e5e7eb;
}

/* ========= Details panel ========= */
.details-panel {
  margin-bottom: 0;
}

.details-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 0;
}

.details-toggle-btn {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  color: #374151;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.details-toggle-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.details-toggle-btn:active {
  transform: translateY(0);
}

.details-toggle-btn i {
  font-size: 13px;
}

/* Merge button in header controls */
.btn-merge-study {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #2563eb;
  color: #ffffff;
  border: 1px solid #2563eb;
  padding: 8px 13px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.btn-merge-study:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.btn-merge-study:active {
  transform: translateY(0);
}

/* Share button in header controls */
.share-icon {
  width: 38px;
  height: 38px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  cursor: pointer;
  font-size: 15px;
  padding: 0;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.share-icon:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.share-icon:active {
  transform: translateY(0);
}

/* Expanded details content */
.details-content {
  margin-top: 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: inset 0 1px 0 rgba(15, 23, 42, 0.02);
}

.details-block {
  margin-bottom: 16px;
}

.details-block:last-child {
  margin-bottom: 0;
}

.details-block strong {
  display: block;
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 8px;
}

.details-block ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}

.details-block li {
  font-size: 13px;
  color: #374151;
  background: #f9fafb;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 8px 10px;
  line-height: 1.4;
  word-break: break-word;
  font-weight: 400;
}

/* Merge button */
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
  gap: 12px;
}

.crumb-left {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.crumb-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.entry-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.entry-title {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.entry-title-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 1 auto;
  min-width: 0;
}

.entry-search {
  position: relative;
  width: clamp(260px, 32vw, 420px);
  min-width: 220px;
}

.entry-search-input-wrap {
  position: relative;
}

.entry-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
  font-size: 13px;
  pointer-events: none;
}

.entry-search-input {
  width: 100%;
  min-height: 38px;
  box-sizing: border-box;
  padding: 8px 34px 8px 34px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  font-size: 13px;
  outline: none;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.entry-search-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.entry-search-input::placeholder {
  color: #9ca3af;
}

.entry-search-results {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 300;
  max-height: 320px;
  overflow-y: auto;
  padding: 6px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.16);
}

.entry-search-result {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.entry-search-result:hover,
.entry-search-result.active {
  background: #eff6ff;
}

.entry-search-result-type {
  flex: 0 0 54px;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.4;
  text-transform: uppercase;
}

.entry-search-result-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.entry-search-result-text strong {
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.35;
}

.entry-search-result-text small {
  overflow-wrap: anywhere;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.35;
}

.entry-search-empty {
  padding: 12px 10px;
  color: #6b7280;
  font-size: 13px;
  text-align: center;
}

.entry-progress {
  margin: -4px 0 18px;
  padding: 12px 14px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #f8fafc;
}

.entry-progress-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #374151;
  font-size: 13px;
}

.entry-progress-summary > div {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.entry-progress-summary strong {
  color: #111827;
  font-size: 14px;
}

.entry-progress-summary span {
  color: #6b7280;
}

.entry-progress-skipped {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c !important;
  font-size: 12px;
  font-weight: 700;
}

.entry-progress-track {
  width: 100%;
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5e7eb;
}

.entry-progress-fill {
  height: 100%;
  min-width: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb 0%, #16a34a 100%);
  transition: width 0.28s ease;
}

.value-assignment-warning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: -4px 0 18px;
  padding: 10px 12px;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 13px;
  line-height: 1.4;
}

.section-collapse-all-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.section-collapse-all-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

/* Section stack */
.sections-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.entry-form-wrapper,
.entry-form-section,
.sections-stack,
.section-card {
  overflow: visible;
}

/* Section card */
.section-card {
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #f8fafc;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  overflow: visible;
}
.study-data-container.is-entry-mode {
  margin-top: 0;
  padding-top: 0;
}

.section-card-header {
  position: sticky;
  top: -8px;
  z-index: 40;

  padding: 18px 20px;
  background: #eef4f9;
  border-bottom: 1px solid #dbe4ee;
  border-radius: 12px 12px 0 0;

  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-card-header {
  position: sticky;
  top: -8px;
  z-index: 120;

  padding: 18px 20px;
  background: #eef4f9;
  border-bottom: 1px solid #dbe4ee;
  border-radius: 12px 12px 0 0;

  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
}

.section-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  line-height: 1.25;
}

.section-collapse-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.section-collapse-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}



.section-card-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Field card */
.field-card {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

/* Field header */
.field-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.field-label {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  color: #111827;
  font-weight: 600;
  line-height: 1.35;
}

.field-label-main {
  display: inline-block;
}

.field-label-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

/* Right-side square action buttons */
.field-icon-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.field-icon-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.field-icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-icon-btn-active {
  background: #eef2ff;
  border-color: #a5b4fc;
  color: #3730a3;
}

.required {
  color: #dc2626;
  margin-left: 2px;
}

/* Help text */
.field-help-box {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #f9fafb;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  white-space: pre-line;
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* Field body */
.field-card-body {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.entry-visit-select {
  min-width: 160px;
  max-width: 260px;
  height: 34px;
  padding: 6px 34px 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
  outline: none;
  cursor: pointer;
}

.entry-visit-select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
}

.entry-visit-select:disabled {
  background: #f3f4f6;
  color: #6b7280;
  cursor: not-allowed;
}
/* Inputs */
input[type="text"],
input[type="number"],
input[type="date"],
input[type="time"],
textarea,
select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-sizing: border-box;
  font-size: 14px;
  color: #1f2937;
  background: #fff;
  min-height: 44px;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

/* Errors / warnings */
.error-message {
  color: #dc2626;
  font-size: 12px;
  margin-top: 8px;
}

.calc-warning-message {
  color: #92400e;
  font-size: 12px;
  margin-top: 8px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 8px;
}

.skip-pill {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 8px;
  font-size: 11px;
  font-weight: 800;
  border-radius: 999px;
  background: #fef2f2;
  color: #7f1d1d;
  border: 1px solid #fecaca;
}

/* Empty state */
.no-assigned {
  font-style: italic;
  color: #6b7280;
  margin-top: 12px;
  padding: 16px;
  background: #f9fafb;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
}

/* Actions */
.form-actions {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
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
  transition: background 0.2s;
}
.load-error-state {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 16px;
  margin: 24px auto;
  max-width: 520px;
  text-align: center;
  font-weight: 600;
}

.btn-clear:hover {
  background: #d1d5db;
}

/* Loading */
.loading {
  text-align: center;
  padding: 50px;
  font-size: 16px;
  color: #6b7280;
}

/* Merge panel */
.merge-panel {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}
.floating-scroll-btn {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 900;
  width: 44px;
  height: 44px;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #ffffff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.16);
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.floating-scroll-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.2);
}

.floating-scroll-btn:active {
  transform: translateY(0);
}

.floating-scroll-btn i {
  font-size: 16px;
}

.floating-scroll-btn.is-up {
  background: #f8fafc;
}
/* Responsive */
@media (max-width: 900px) {
  .bread-crumb {
    flex-direction: column;
    align-items: stretch;
  }

  .crumb-actions {
    justify-content: flex-end;
  }
.floating-scroll-btn {
    right: 16px;
    bottom: 16px;
    width: 42px;
    height: 42px;
  }
}
.field-help-inline-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  margin-left: 6px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  vertical-align: middle;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}
.section-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.section-error-btn {
  height: 34px;
  min-width: 42px;
  padding: 0 10px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff1f2;
  color: #b91c1c;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.section-error-btn:hover {
  background: #ffe4e6;
  border-color: #fca5a5;
  color: #991b1b;
}

.field-card-has-error {
  border-color: #fca5a5;
  background: #fffafa;
}

.section-card-search-highlight {
  border-color: #2563eb;
  box-shadow:
    0 0 0 3px rgba(37, 99, 235, 0.14),
    0 10px 26px rgba(37, 99, 235, 0.12);
  animation: entry-search-pulse 1.1s ease-in-out 2;
}

.field-card-search-highlight {
  border-color: #2563eb;
  background: #f8fbff;
  box-shadow:
    0 0 0 3px rgba(37, 99, 235, 0.14),
    0 8px 22px rgba(37, 99, 235, 0.12);
  animation: entry-search-pulse 1.1s ease-in-out 2;
}

@keyframes entry-search-pulse {
  0% {
    box-shadow:
      0 0 0 0 rgba(37, 99, 235, 0.26),
      0 8px 22px rgba(37, 99, 235, 0.08);
  }

  50% {
    box-shadow:
      0 0 0 7px rgba(37, 99, 235, 0.12),
      0 8px 22px rgba(37, 99, 235, 0.15);
  }

  100% {
    box-shadow:
      0 0 0 3px rgba(37, 99, 235, 0.14),
      0 8px 22px rgba(37, 99, 235, 0.12);
  }
}

.field-card-error-highlight {
  border-color: #dc2626;
  box-shadow:
    0 0 0 3px rgba(220, 38, 38, 0.12),
    0 8px 22px rgba(220, 38, 38, 0.12);
  animation: field-error-pulse 1.1s ease-in-out 2;
}

@keyframes field-error-pulse {
  0% {
    box-shadow:
      0 0 0 0 rgba(220, 38, 38, 0.25),
      0 8px 22px rgba(220, 38, 38, 0.08);
  }

  50% {
    box-shadow:
      0 0 0 6px rgba(220, 38, 38, 0.12),
      0 8px 22px rgba(220, 38, 38, 0.14);
  }

  100% {
    box-shadow:
      0 0 0 3px rgba(220, 38, 38, 0.12),
      0 8px 22px rgba(220, 38, 38, 0.12);
  }
}
.field-help-inline-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}
.details-key {
  font-weight: 800;
  color: #111827;
}

.details-value {
  font-weight: 400;
  color: #374151;
}
.unsaved-exit-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.unsaved-exit-dialog {
  width: 100%;
  max-width: 460px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
  overflow: hidden;
}

.unsaved-exit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff7ed;
}

.unsaved-exit-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #9a3412;
}

.unsaved-exit-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #9a3412;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.unsaved-exit-close:hover {
  color: #7c2d12;
}

.unsaved-exit-body {
  padding: 16px;
}

.unsaved-exit-body p {
  margin: 0 0 10px;
  color: #374151;
  line-height: 1.45;
}

.unsaved-exit-body p:last-child {
  margin-bottom: 0;
}

.unsaved-exit-actions {
  padding: 12px 16px 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-unsaved-exit {
  background: #b91c1c;
  color: #ffffff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-unsaved-exit:hover {
  background: #991b1b;
}
.field-card-has-reminder {
  border-color: #f59e0b;
  background: #fffbeb;
}

.popup-reminder-message {
  margin-top: 8px;
  padding: 8px 10px;
  border: 1px solid #fbbf24;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 13px;
  line-height: 1.4;
}
@media (max-width: 768px) {
 .study-header-container {
    padding: 16px;
    border-radius: 12px;
  }

  .study-name {
    font-size: 22px;
  }

  .study-description {
    font-size: 14px;
  }

  .study-meta,
  .shared-banner {
    width: 100%;
    box-sizing: border-box;
    border-radius: 10px;
    flex-wrap: wrap;
  }
.details-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}



  .details-toggle-btn,
  .btn-merge-study {
    width: 100%;
  }

  .share-icon {
    margin-left: auto;
  }

  .details-block ul {
    grid-template-columns: 1fr;
  }
  .field-card-header {
    flex-direction: column;
    align-items: stretch;
  }
  .entry-title-row {
  flex-direction: column;
  align-items: stretch;
 }

 .entry-title-actions {
  width: 100%;
  flex-direction: column;
  align-items: stretch;
 }

 .entry-search {
  width: 100%;
  min-width: 0;
 }

 .entry-progress-summary {
  align-items: flex-start;
  flex-direction: column;
 }

 .section-collapse-all-btn {
  width: 100%;
  justify-content: center;
 }

.study-data-container {
  padding: 16px;
}
  .field-label-actions {
    justify-content: flex-start;
  }

  .details-controls {
    flex-wrap: wrap;
  }

  .form-actions {
    justify-content: stretch;
  }

  .btn-save,
  .btn-clear {
    width: 100%;
  }
  .section-card-header {
  align-items: flex-start;
}

.section-header-actions {
  align-self: flex-start;
}
}
</style>
