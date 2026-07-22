<template>
  <div class="create-form-container">
    <div class="scratch-form-content" :class="{ 'scratch-form-content-full': showMatrix || showLogic || showValueAssignments }">
      <!-- ───────── Available Fields ───────── -->
      <div v-if="!showMatrix && !showLogic && !showValueAssignments" class="available-fields">
        <div class="available-fields-topbar">
          <button @click="goBack" class="btn-back" title="Go Back">
            Back
          </button>
        </div>

        <h2>Available Fields</h2>

        <div class="tabs">
          <button
            :class="{ active: activeTab === 'template' }"
            @click="activeTab = 'template'"
          >Standard Template</button>
          <button
            :class="{ active: activeTab === 'custom' }"
            @click="activeTab = 'custom'"
          >Custom Fields</button>
          <button
            :class="{ active: activeTab === 'obi' }"
            @click="activeTab = 'obi'"
          >Ontology (OBI)</button>
          <button
            :class="{ active: activeTab === 'savedTemplates' }"
            @click="activeTab = 'savedTemplates'"
          >
            Saved Templates
          </button>
          <button
            v-if="false"
            :class="{ active: activeTab === 'shacl' }"
            @click="activeTab = 'shacl'"
          >SHACL Components</button>
        </div>

        <!-- TEMPLATE -->
        <div v-if="activeTab === 'template'" class="template-fields">
          <div class="available-fields-search">
            <input
              type="text"
              v-model="searchQuery"
              placeholder="Search available fields..."
              class="search-input"
              aria-label="Search available fields"
            />
          </div>

          <p class="template-instruction">
            Select a section and properties to add
          </p>
          <div class="tab-results">
            <div
              v-for="model in filteredDataModels"
              :key="model.title"
              class="template-button"
              :class="{ 'highlighted-model': searchQuery && (model.fields?.length || titleMatches(model.title)) }"
              @click="openModelDialog(model)"
            >
              <div class="template-header">
                <i :class="modelIcon(model.title)"></i>
                <span v-html="highlight(model.title)"></span>
              </div>
              <div class="template-description">
                {{ model.description || "No description available." }}
              </div>

              <!-- When searching, preview the matching fields for clarity -->
              <ul v-if="searchQuery && model.fields && model.fields.length" class="match-preview">
                <li v-for="f in previewMatches(model.fields)" :key="f.name">
                  <span v-html="highlight(f.label || prettyModelTitle(f.name))"></span>
                </li>
              </ul>
            </div>

            <!-- Empty state when no matches -->
            <div v-if="searchQuery && filteredDataModels.length === 0" class="no-matches">
              No matches found for "<strong>{{ searchQuery }}</strong>".
            </div>
          </div>
        </div>

        <!-- CUSTOM -->
        <div v-else-if="activeTab === 'custom'" class="custom-fields">
          <div
            v-for="field in generalFields"
            :key="field.name || field.label"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
          >
            <i :class="field.icon || fieldIcon(field.label)"></i>
            <div class="field-info">
              <span class="field-label">{{ field.label }}</span>
            </div>
          </div>
        </div>

        <!-- OBI -->
        <div v-else-if="activeTab === 'obi'" class="obi-fields">
          <div class="available-fields-search">
            <input
              type="text"
              v-model="obiQuery"
              placeholder="Search OBI terms…"
              class="search-input"
              aria-label="Search OBI terms"
              @input="onObiInput"
            />
          </div>

          <div class="obi-toolbar">
            <button
              class="btn-add-selected"
              :disabled="selectedTermIds.size === 0"
              @click="addSelectedObiTerms"
              title="Add selected OBI terms as fields"
            >
              Add Selected ({{ selectedTermIds.size }})
            </button>

            <div class="obi-stats" v-if="obiQuery.trim().length >= 2">
              <span v-if="!obiLoading" class="obi-count">
                {{ obiResults.length }} result{{ obiResults.length===1?'':'s' }}
              </span>
              <span v-else>Loading…</span>
            </div>
          </div>

          <!-- Scroll only the results, not the whole sidebar -->
          <div class="tab-results obi-list">
            <div
              v-for="t in obiResults"
              :key="t.id"
              class="obi-term-row"
            >
              <!-- Row 1: tiny checkbox at top-left -->
              <div class="obi-term-top">
                <input
                  type="checkbox"
                  class="obi-checkbox-small"
                  :checked="selectedTermIds.has(t.id)"
                  @change="onToggleObiTerm(t.id, $event)"
                  :aria-label="`Select ${t.label}`"
                />
                <span class="obi-selected-pill" v-if="selectedTermIds.has(t.id)">Selected</span>
              </div>

              <!-- Row 2: full result -->
              <div class="obi-term-body" @click="toggleByBody(t.id)">
                <div class="obi-term-label" v-html="obiHighlight(t.label)"></div>
                <div class="obi-term-meta">
                  <span class="obi-id">{{ t.id }}</span>
                </div>
                <div v-if="t.definition" class="obi-def" v-html="obiHighlight(t.definition)"></div>
                <div v-if="t.synonyms && t.synonyms.length" class="obi-syn">
                  <strong>Synonyms:</strong>
                  <span v-html="obiHighlight(formatSynonyms(t.synonyms))"></span>
                </div>
              </div>
            </div>

            <div v-if="obiError" class="obi-error">{{ obiError }}</div>
            <div v-if="!obiLoading && !obiResults.length && obiQuery.trim().length >= 2" class="obi-empty">
              No terms found.
            </div>
            <div v-if="obiQuery.trim().length < 2" class="obi-hint">
              Type at least 2 characters to search OBI.
            </div>
          </div>

          <!-- Show more -->
          <div class="obi-more" v-if="obiQuery.trim().length >= 2">
            <button
              class="btn-more"
              :disabled="obiLoading || !canShowMore"
              @click="showMore"
              title="Load more results"
            >
              Show more
            </button>
          </div>
        </div>
        <div v-else-if="activeTab === 'savedTemplates'" class="saved-template-fields">
          <div class="available-fields-search">
            <input
              type="text"
              v-model="savedTemplateQuery"
              placeholder="Search saved templates..."
              class="search-input"
              aria-label="Search saved templates"
            />
          </div>

          <div class="saved-template-toolbar">
            <button
              class="btn-add-selected"
              :disabled="savedTemplatesLoading"
              @click="loadSavedTemplates"
            >
              {{ savedTemplatesLoading ? "Loading…" : "Refresh" }}
            </button>

            <span class="obi-count">
              {{ filteredSavedTemplates.length }} result{{ filteredSavedTemplates.length === 1 ? "" : "s" }}
            </span>
          </div>

          <div class="tab-results saved-template-list">
            <div
              v-for="template in filteredSavedTemplates"
              :key="`${template._savedTemplateId}_${template._savedSectionIndex}`"
              class="template-button saved-template-card"
            >
              <div @click="openModelDialog(template)">
                <div class="template-header">
                  <i :class="template.sourceType === 'form' ? 'fas fa-file-alt' : 'fas fa-layer-group'"></i>
                  <span>{{ template.title }}</span>
                </div>

                <div class="saved-template-section-name">
                  {{ template.sectionTitle }}
                </div>

                <div class="template-description">
                  {{ template.description || "No description available." }}
                </div>

                <ul v-if="savedTemplateQuery && template.fields?.length" class="match-preview">
                  <li v-for="field in previewMatches(template.fields)" :key="field.name">
                    {{ field.label || prettyModelTitle(field.name) }}
                  </li>
                </ul>
              </div>

              <button
                  v-if="canDeleteSavedTemplate(template)"
                  class="saved-template-delete"
                  title="Delete saved template"
                  @click.stop.prevent="openDeleteSavedTemplateDialog(template)"
                >
                  <i :class="icons.delete"></i>
                </button>
            </div>

            <div v-if="savedTemplatesError" class="obi-error">
              {{ savedTemplatesError }}
            </div>

            <div
              v-if="!savedTemplatesLoading && filteredSavedTemplates.length === 0"
              class="no-matches"
            >
              No saved templates found.
            </div>
          </div>
        </div>

        <!-- SHACL -->
        <div v-else-if="false && activeTab === 'shacl'">
          <ShaclComponents :shaclComponents="shaclComponents" @takeover="onShaclTakeover" />
        </div>
      </div>

      <!-- ───────── Form Area / Protocol Matrix / Logic ───────── -->
      <div
        ref="scratchScrollEl"
        class="form-area"
        :class="{ 'form-area-full': showMatrix || showLogic || showValueAssignments }"
        @scroll.passive="onScratchScroll"
        @pointerenter="onBuilderPointerMove"
        @pointermove.passive="onBuilderPointerMove"
        @pointerleave="onBuilderPointerLeave"
      >
        <div class="sections-container" :class="{ 'value-assignments-sections-container': showValueAssignments }">
          <!-- Sections View -->
          <div v-if="!showMatrix && !showLogic && !showValueAssignments">
            <!-- Sticky builder toolbar -->
            <div ref="builderStickyBar" class="sections-topbar builder-sticky-bar">
              <div class="form-actions-inline">
                  <button @click.prevent="addNewSection" class="btn-option">
                    Add Section
                  </button>

                  <button
                    @click.prevent="openRearrangeDialog()"
                    class="btn-option"
                    title="Rearrange sections and fields"
                  >
                    Rearrange
                  </button>

                  <button
                    @click.prevent="openLogicAndCalculations"
                    class="btn-option"
                    title="Configure conditional logic and calculations"
                  >
                    Logic & Calculations
                  </button>

                  <button
                    @click.prevent="openValueAssignments"
                    class="btn-option"
                    title="Configure conditional value assignments"
                  >
                    Value Assignments
                  </button>

                  <button
                    @click.prevent="onUnsavedSaveAndExit"
                    class="btn-option"
                    :disabled="unsavedBusy"
                  >
                    {{ unsavedBusy ? "Saving…" : "Save Draft and Leave" }}
                  </button>

                  <button
                    @click.prevent="handleProtocolClick"
                    class="btn-option protocol-btn"
                  >
                    Create Visit Schedule
                  </button>
                </div>

                <div class="builder-toolbar-right">
                  <div class="additional-options" @click.stop>
                    <button
                      ref="additionalOptionsBtn"
                      class="btn-ellipsis"
                      title="Additional options"
                      @click.prevent="toggleAdditionalOptions"
                    >
                      <i :class="icons.ellipsisV || 'fas fa-ellipsis-v'"></i>
                    </button>

                    <div
                      v-if="showAdditionalOptions"
                      ref="additionalOptionsMenu"
                      class="options-menu"
                      role="menu"
                      aria-label="Additional options"
                    >
                      <button class="options-item" role="menuitem" @click.prevent="openImportCsvDialog">
                        Import CSV / Excel Template
                      </button>

                      <button class="options-item" role="menuitem" @click.prevent="onDownloadTemplate">
                        Download Template
                      </button>

                      <button class="options-item" role="menuitem" @click.prevent="onUploadTemplate">
                        Upload Template
                      </button>
                      <button class="options-item" role="menuitem" @click.prevent="openSaveTemplateFormDialog">
                          Save template/form
                      </button>

                      <button class="options-item danger" role="menuitem" @click.prevent="confirmClearForm">
                        Clear All
                      </button>
                    </div>
                  </div>

                  <div class="sections-topbar-actions">
                    <button
                      class="icon-button"
                      title="Expand all sections"
                      @click.prevent="expandAllSections"
                    >
                      <i :class="icons.toggleDown"></i>
                    </button>

                    <button
                      class="icon-button"
                      title="Collapse all sections"
                      @click.prevent="collapseAllSections"
                    >
                      <i :class="icons.toggleUp"></i>
                    </button>
                  </div>
                </div>


            </div>
            <div v-if="!currentForm.sections || currentForm.sections.length === 0" class="empty-builder-state">
              Add your first section to start building this form. You can add a section manually or choose fields from the left panel.
            </div>

            <transition-group name="reorder" tag="div" class="sections-list">
              <div
                v-for="(section, si) in currentForm.sections"
                :key="getSectionUid(section)"
                class="form-section"
                :class="{
                  active: activeSection === si,
                  'recently-added-section': recentlyAddedSectionUid === getSectionUid(section)
                }"
                @click="onSectionClick(si)"
                :ref="'section-' + si"
                :data-builder-section-index="si"
              >
                <div class="section-header">
                  <h3>{{ section.title }}</h3>
                  <div class="field-actions">
                    <button
                      class="icon-button"
                      title="Edit Section Title"
                      @click.stop.prevent="setActiveSection(si); openInputDialog(
                        'Enter new section title:',
                        section.title,
                        val => editSection(si, val)
                      )"
                    ><i :class="icons.edit"></i></button>

                    <button
                      class="icon-button"
                      title="Add Section Below"
                      @click.stop.prevent="setActiveSection(si); addNewSectionBelow(si)"
                    ><i :class="icons.add"></i></button>

                    <button
                      class="icon-button"
                      title="Delete Section"
                      @click.stop.prevent="setActiveSection(si); confirmDeleteSection(si)"
                    ><i :class="icons.delete"></i></button>

                    <button
                      class="icon-button"
                      :title="section.collapsed ? 'Expand' : 'Collapse'"
                      @click.stop.prevent="setActiveSection(si); toggleSection(si)"
                    >
                      <i :class="section.collapsed ? icons.toggleDown : icons.toggleUp"></i>
                    </button>
                  </div>
                </div>

                <div
                  v-if="!section.collapsed"
                  class="section-content-wrapper"
                  @dragover.prevent="onFieldContainerOver(si, $event)"
                  @drop.prevent="onFieldContainerDrop(si)"
                >
                  <transition-group name="reorder" tag="div" class="section-content">
                    <div
                      v-for="(field, fi) in section.fields"
                      :key="getFieldUid(field)"
                      class="form-group"
                      :class="[
                        getFieldDropClass(si, fi),
                        { 'recently-added-field': recentlyAddedFieldId === String(field._id || '') }
                      ]"
                      :data-builder-field-id="field._id || null"
                      @dragover.stop.prevent="onFieldDragOver(si, fi, $event)"
                      @drop.stop.prevent="onFieldDrop(si, fi)"
                    >
                      <div class="field-header">
                        <label
                          v-if="field.type !== 'button' && field.type !== 'checkbox'"
                          :for="field.name"
                        >
                          {{ field.label }}
                          <span v-if="field.constraints?.required" class="required-asterisk">*</span>
                        </label>
                        <label
                          v-else-if="field.type === 'checkbox'"
                          class="checkbox-label"
                          :for="field.name"
                        >
                          {{ field.label }}
                          <span v-if="field.constraints?.required" class="required-asterisk">*</span>
                          <FieldCheckbox
                            :id="field.name"
                            v-model="field.value"
                          />
                        </label>

                        <div class="field-actions">
                          <button
                            class="icon-button"
                            title="Edit Field Label"
                            @click.stop.prevent="setActiveSection(si); openInputDialog(
                              'Enter new field label:',
                              field.label,
                              val => editField(si, fi, val)
                            )"
                          ><i :class="icons.edit"></i></button>

                          <button
                            class="icon-button"
                            :title="field.type === 'table' ? 'Copy table' : 'Copy field (basic settings only)'"
                            @click.stop.prevent="setActiveSection(si); field.type === 'table' ? openTableCopyDialog(si, fi) : addSimilarField(si, fi)"
                          ><i :class="icons.add"></i></button>

                          <button
                            class="icon-button"
                            title="Delete Field"
                            @click.stop.prevent="setActiveSection(si, fi); confirmDeleteField(si, fi)"
                          ><i :class="icons.delete"></i></button>

                          <button
                            v-if="hasFieldDependencies(si, fi)"
                            class="icon-button"
                            title="View dependencies"
                            @click.stop.prevent="openDependencyInfoDialog(si, fi)"
                            ><i :class="icons.info || 'fas fa-question-circle'"></i></button>

                          <button
                            class="icon-button"
                            title="Settings"
                            @click.stop.prevent="onFieldSettingsClick(si, fi)"
                          ><i :class="icons.cog"></i></button>

                          <!-- MOVE: extreme right of each field (right of settings) -->
                          <span
                            class="drag-handle drag-handle-right"
                            draggable="true"
                            title="Move field"
                            @click.stop
                            @dragstart.stop="onFieldDragStart(si, fi, $event)"
                            @dragend="onDragEnd"
                          >
                            <i :class="icons.move || 'fas fa-grip-vertical'"></i>
                          </span>
                        </div>
                      </div>

                      <div class="field-box">
                        <!-- TEXT -->
                        <input
                          v-if="field.type === 'text'"
                          type="text"
                          v-model="field.value"
                          :placeholder="field.constraints?.placeholder || field.placeholder"
                        />

                        <!-- TEXTAREA -->
                        <textarea
                          v-else-if="field.type === 'textarea'"
                          v-model="field.value"
                          :rows="field.rows || 4"
                          :placeholder="field.constraints?.placeholder || field.placeholder"
                        ></textarea>

                        <!-- NUMBER -->
                        <input
                          v-else-if="field.type === 'number'"
                          type="number"
                          v-model.number="field.value"
                          :min="field.constraints?.min"
                          :max="field.constraints?.max"
                          :step="field.constraints?.step"
                          @input="enforceNumberDigitLimits(si, fi, $event)"
                          @blur="enforceNumberDigitLimits(si, fi, $event, true)"
                        />

                        <!-- DATE -->
                        <DateFormatPicker
                          v-else-if="field.type === 'date'"
                          v-model="field.value"
                          :format="field.constraints?.dateFormat || 'dd.MM.yyyy'"
                          :placeholder="field.placeholder || (field.constraints?.dateFormat || 'dd.MM.yyyy')"
                          :min-date="field.constraints?.minDate || null"
                          :max-date="field.constraints?.maxDate || null"
                        />

                        <!-- TIME -->
                        <FieldTime
                          v-else-if="field.type === 'time'"
                          v-model="field.value"
                          v-bind="field.constraints"
                          :hourCycle="field.constraints?.hourCycle || '24'"
                          :placeholder="field.placeholder || (field.constraints?.hourCycle === '12' ? 'hh:mm a' : 'HH:mm')"
                        />

                        <!-- SELECT -->
                        <select
                          v-else-if="field.type === 'select'"
                          v-model="field.value"
                        >
                          <option value="" disabled>Select…</option>
                          <option v-for="opt in field.options" :key="opt">{{ opt }}</option>
                        </select>

                        <!-- RADIO -->
                        <FieldRadioGroup
                          v-else-if="field.type === 'radio'"
                          :name="field.name"
                          :options="field.options"
                          v-model="field.value"
                        />

                        <!-- SLIDER / LINEAR -->
                        <FieldSlider
                          v-else-if="field.type === 'slider' && (field.constraints?.mode || 'slider') === 'slider'"
                          v-model="field.value"
                          :min="field.constraints?.min ?? 1"
                          :max="field.constraints?.max ?? 5"
                          :step="field.constraints?.step ?? 1"
                          :readonly="!!field.constraints?.readonly"
                          :percent="!!field.constraints?.percent"
                          :marks="field.constraints?.marks || []"
                        />
                        <FieldLinearScale
                          v-else-if="field.type === 'slider' && field.constraints?.mode === 'linear'"
                          v-model="field.value"
                          :min="field.constraints?.min ?? 1"
                          :max="field.constraints?.max ?? 5"
                          :left-label="field.constraints?.leftLabel || ''"
                          :right-label="field.constraints?.rightLabel || ''"
                          :readonly="!!field.constraints?.readonly"
                        />

                        <!-- FILE -->
                        <FieldFileUpload
                          v-else-if="field.type === 'file'"
                          v-model="field.value"
                          :constraints="field.constraints || {}"
                          :readonly="!!field.constraints?.readonly"
                          :required="!!field.constraints?.required"
                          stage="builder"
                        />
                        <!-- TABLE (REAL RENDER) -->
                        <FieldTable
                          v-else-if="field.type === 'table'"
                          mode="render"
                          :modelValue="field.value"
                          :field="field"
                          :form="currentForm"
                          :readonly="true"
                        />

                        <!-- BUTTON -->
                        <button
                          v-else-if="field.type === 'button'"
                          class="form-button"
                        >{{ field.label }}</button>

                        <!-- FALLBACK -->
                        <input
                          v-else
                          type="text"
                          v-model="field.value"
                          :placeholder="field.constraints?.placeholder || field.placeholder"
                        />

                        <small v-if="field.constraints?.helpText" class="help-text">
                          {{ field.constraints.helpText }}
                        </small>
                      </div>
                    </div>
                  </transition-group>

                  <div
                    v-if="dragState.kind === 'field'"
                    class="field-drop-end"
                    :class="{ 'drop-active': dragState.overSection === si && dragState.overField == null }"
                    @dragover.prevent="onFieldDropEndOver(si, $event)"
                    @drop.prevent="onFieldDropEnd(si)"
                  >
                    Drop field here (end of section)
                  </div>
                </div>
              </div>
            </transition-group>
          </div>

          <!-- Protocol Matrix View -->
          <div v-else-if="showMatrix">
            <ProtocolMatrix
              :visits="visits"
              :groups="groups"
              :selectedModels="selectedModels"
              :assignments="assignments"
              :forms="forms"
              @assignment-updated="onAssignmentUpdated"
              @edit-template="editTemplate"
            />
          </div>
          <div v-else-if="showLogic">
            <LogicCalculationsRoute
              :form="currentForm"
              @back-to-builder="closeLogicAndCalculations"
              @update-form-structure="applyLogicFormUpdate"
              @update-logic="applyLogicPayload"
            />
          </div>
          <div v-else-if="showValueAssignments" class="value-assignments-route-host">
            <LogicValueAssignmentsRoute
              :form="currentForm"
              @back-to-builder="closeValueAssignments"
              @update-form-structure="applyLogicFormUpdate"
              @update-logic="applyLogicPayload"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Table Configurator Dialog -->
    <div v-if="showTableConfigurator" class="modal-overlay">
      <div class="modal table-config-modal">
        <FieldTable
          mode="configure"
          :value="pendingTableField"
          :form="currentForm"
          @save="handleTableConfiguratorSave"
          @cancel="cancelTableConfigurator"
          @showGenericDialog="openGenericDialog"
        />
      </div>
    </div>

    <!-- Model Dialog -->
    <div v-if="showModelDialog" class="modal-overlay">
      <div class="modal model-dialog">
        <h3>Select Properties for {{ prettyModelTitle(currentModel.title) }}</h3>
        <div class="model-prop-toolbar">
          <button
            type="button"
            class="btn-option btn-select-all"
            @click="toggleSelectAllProps"
          >
            {{ allSelectablePropsSelected ? "Deselect All" : "Select All" }}
          </button>
        </div>
        <div class="model-prop-list">
          <div
            v-for="(prop, i) in currentModel.fields"
            :key="prop.name"
            class="prop-cell"
            :class="{
              selected: selectedProps[i],
              disabled: modelAddToExisting && isPropAlreadyInTargetSection(prop)
            }"
            @click="togglePropSelection(i, prop)"
          >
            <div class="prop-info">
              <strong class="prop-label">
                {{ prop.label || prettyModelTitle(prop.name) }}
              </strong>
              <p v-if="prop.description" class="prop-desc">
                {{ prop.description }}
              </p>
            </div>

            <input
              type="checkbox"
              :id="'prop-check-' + i"
              :checked="!!selectedProps[i]"
              class="prop-checkbox"
              :disabled="modelAddToExisting && isPropAlreadyInTargetSection(prop)"
              :title="(modelAddToExisting && isPropAlreadyInTargetSection(prop)) ? 'Already added in selected section' : ''"
              @click.stop
              @change="togglePropSelection(i, prop)"
            />
          </div>
        </div>

        <!-- selection (dropdown/hint) ABOVE checkbox, and block sits ABOVE takeover buttons -->
        <div class="model-target">
          <div class="model-target-selection">
            <div
              v-if="modelAddToExisting && currentForm.sections.length"
              class="model-target-select"
            >
              <div class="model-target-label">Add selected fields to:</div>
              <select v-model.number="modelTargetSectionIndex">
                <option
                  v-for="(s, idx) in currentForm.sections"
                  :key="getSectionUid(s)"
                  :value="idx"
                >
                  {{ idx === activeSection ? `[Current] ${s.title}` : s.title }}
                </option>
              </select>
            </div>

            <div v-else class="model-target-hint">
              <span v-if="currentForm.sections.length">
                Add as a new section (below: <strong>{{ currentForm.sections[activeSection]?.title }}</strong>)
              </span>
              <span v-else>
                Add as a new section
              </span>
            </div>
          </div>

          <label class="model-target-check">
            <input
              type="checkbox"
              v-model="modelAddToExisting"
              :disabled="!currentForm.sections.length"
            />
            Add to existing section
          </label>
        </div>

        <div class="modal-actions">
          <button @click="takeoverModel" class="btn-primary">Takeover</button>
          <button @click="showModelDialog = false" class="btn-option">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Constraints Dialog -->
    <div v-if="showConstraintsDialog" class="modal-overlay">
      <FieldConstraintsDialog
        :currentFieldType="currentFieldType"
        :constraintsForm="constraintsForm"
        :form="currentForm"
        :currentFieldKey="currentEditingFieldKey"
        :currentFieldLabel="currentEditingFieldLabel"
        :fieldDefinition="currentEditingFieldDefinition"
        @updateConstraints="confirmConstraintsDialog"
        @closeConstraintsDialog="cancelConstraintsDialog"
        @showGenericDialog="openGenericDialog"
      />
    </div>
    <FieldOptionRemapDialog
      :visible="showFieldOptionRemapDialog"
      :sourceFieldLabel="pendingFieldOptionRemapSourceLabel"
      :currentItem="fieldOptionRemapContext"
      :nextOptions="pendingFieldOptionRemapNextOptions"
      :currentIndex="pendingFieldOptionRemapIndex"
      :queueLength="pendingFieldOptionRemapQueue.length"
      @confirm="confirmFieldOptionRemapDialog"
      @cancel="cancelFieldOptionRemapDialog"
      @validation-error="openGenericDialog"
    />

    <!-- Preview Dialog -->
    <div v-if="showPreviewDialog" class="modal-overlay">
      <div class="modal preview-modal">
        <FormPreview :form="currentForm" />
        <div class="modal-actions">
          <button @click="closePreviewDialog" class="btn-primary">Close</button>
        </div>
      </div>
    </div>

    <!-- Rearrange Structure Dialog -->
    <div v-if="showRearrangeDialog" class="modal-overlay">
      <RearrangeStructureDialog
        :sections="currentForm.sections"
        :initialFocus="rearrangeInitialFocus"
        @close="closeRearrangeDialog"
        @save="applyRearrangedStructure"
      />
    </div>

    <!-- Import CSV / Excel Dialog -->
    <div v-if="showImportCsvDialog" class="modal-overlay import-overlay">
      <div class="modal-container">
        <ImportCsvTemplateDialog
          @close="closeImportCsvDialog"
          @import-fields="handleImportedCsvFields"
        />
      </div>
    </div>
    <SaveTemplateFormDialog
      :visible="showSaveTemplateFormDialog"
      :form="currentForm"
      :saving="saveTemplateBusy"
      @save="handleSaveTemplateForm"
      @close="closeSaveTemplateFormDialog"
    />
    <SaveTemplateFormDialog
      :visible="showDeleteSavedTemplateDialog"
      mode="delete"
      :form="selectedSavedTemplateForDelete?.form_schema || { sections: [] }"
      :saving="deleteTemplateBusy"
      @delete="handleDeleteSavedTemplate"
      @close="closeDeleteSavedTemplateDialog"
    />

    <!-- Upload Dialog -->
    <div v-if="showUploadDialog" class="modal-overlay">
      <div class="modal">
        <p>
          Select a JSON file containing exactly:<br/>
          <code>{ "sections": […] }</code>
        </p>
        <input type="file" @change="handleFileChange" accept=".json" />
        <div class="modal-actions">
          <button @click="closeUploadDialog" class="btn-option">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Input Dialog -->
    <div v-if="showInputDialog" class="modal-overlay">
      <div class="modal input-dialog-modal">
        <p>{{ inputDialogMessage }}</p>
        <input
          type="text"
          v-model="inputDialogValue"
          class="input-dialog-field"
        />
        <div class="modal-actions">
          <button @click="confirmInputDialog" class="btn-primary">Save</button>
          <button @click="cancelInputDialog" class="btn-option">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Dialog -->
    <div v-if="showConfirmDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ confirmDialogMessage }}</p>
        <div class="modal-actions">
          <button @click="confirmDialogYes" class="btn-primary">Yes</button>
          <button @click="closeConfirmDialog" class="btn-option">No</button>
        </div>
      </div>
    </div>

    <!-- Generic Dialog -->
    <div v-if="showGenericDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ genericDialogMessage }}</p>
        <button @click="closeGenericDialog" class="btn-primary">OK</button>
      </div>
    </div>

    <!-- Table Copy Dialog -->
    <div v-if="showTableCopyDialog" class="modal-overlay" @click.self="closeTableCopyDialog">
      <div class="modal table-copy-modal" role="dialog" aria-modal="true" aria-labelledby="table-copy-title">
        <h3 id="table-copy-title">Copy table</h3>
        <p class="table-copy-intro">Choose how much of this table should be copied.</p>

        <div class="table-copy-choices">
          <button type="button" class="table-copy-choice recommended" @click="confirmCompleteTableCopy">
            <strong>Copy complete table structure</strong>
            <span>
              Copies all columns, field types, options, and advanced settings—including show/hide logic.
              Entered data is not copied.
            </span>
            <span class="table-copy-recommended">Recommended</span>
          </button>

          <button type="button" class="table-copy-choice" @click="confirmBasicTableCopy">
            <strong>Copy basic table only</strong>
            <span>Copies only the basic field settings. Columns and advanced settings are not copied.</span>
          </button>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn-option" @click="closeTableCopyDialog">Cancel</button>
        </div>
      </div>
    </div>

    <!-- UNSAVED CHANGES DIALOG -->
    <div v-if="showUnsavedDialog" class="modal-overlay" @click.self="unsavedBusy ? null : onUnsavedKeepEditing()">
      <div class="modal">
        <p>{{ unsavedDialogMessage }}</p>
        <div class="modal-actions" style="display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px;">
          <button class="btn-option" @click="onUnsavedKeepEditing" :disabled="unsavedBusy">Keep editing</button>
          <button class="btn-option" @click="confirmScratchExitWithoutSaving" :disabled="unsavedBusy">Exit without saving</button>
          <button class="btn-primary" @click="onUnsavedSaveAndExit" :disabled="unsavedBusy">
            {{ unsavedBusy ? "Saving…" : "Save & Exit" }}
          </button>
        </div>
      </div>
    </div>

    <button
      v-if="!showMatrix && !showLogic && !showValueAssignments && hasScratchScrollableContent"
      type="button"
      class="floating-scroll-btn"
      :class="{ 'is-up': scratchScrollDirection === 'up' }"
      :title="scratchScrollDirection === 'up' ? 'Scroll to top' : 'Scroll to bottom'"
      @click="toggleScratchScroll"
    >
      <i :class="scratchScrollDirection === 'up' ? icons.toggleUp : icons.toggleDown"></i>
    </button>
  </div>
</template>

<script>
import axios from "axios";
import yaml from "js-yaml";
import icons from "@/assets/styles/icons";
import ShaclComponents from "./ShaclComponents.vue";
import ProtocolMatrix from "./ProtocolMatrix.vue";
import FieldConstraintsDialog from "./FieldConstraintsDialog.vue";
import FormPreview from "./FormPreview.vue";
import DateFormatPicker from "./DateFormatPicker.vue";
import FieldCheckbox from "@/components/fields/FieldCheckbox.vue";
import FieldRadioGroup from "@/components/fields/FieldRadioGroup.vue";
import FieldTime from "@/components/fields/FieldTime.vue";
import FieldSlider from "@/components/fields/FieldSlider.vue";
import FieldLinearScale from "@/components/fields/FieldLinearScale.vue";
import FieldFileUpload from "@/components/fields/FieldFileUpload.vue";
import LogicCalculationsRoute from "./LogicCalculationsRoute.vue";
import LogicValueAssignmentsRoute from "./LogicValueAssignmentsRoute.vue";
import ImportCsvTemplateDialog from "./ImportCsvTemplateDialog.vue";
import RearrangeStructureDialog from "@/components/RearrangeStructureDialog.vue";
import FieldTable from "@/components/FieldTable.vue";
import FieldOptionRemapDialog from "@/components/FieldOptionRemapDialog.vue";
import SaveTemplateFormDialog from "@/components/SaveTemplateFormDialog.vue";
import { copyCompleteTableStructure } from "@/utils/tableFieldCopy";
import { calculateContainedRevealScrollTop } from "@/utils/builderScrollFocus";
export default {
  name: "ScratchFormComponent",
  components: {
    ImportCsvTemplateDialog,
    ShaclComponents,
    ProtocolMatrix,
    LogicCalculationsRoute,
    LogicValueAssignmentsRoute,
    FieldConstraintsDialog,
    FormPreview,
    DateFormatPicker,
    FieldCheckbox,
    FieldRadioGroup,
    FieldTime,
    FieldSlider,
    FieldLinearScale,
    FieldFileUpload,
    FieldTable,
    RearrangeStructureDialog,
    FieldOptionRemapDialog,
    SaveTemplateFormDialog,
  },

  beforeRouteLeave(to, from, next) {
  // IMPORTANT:
  // When ProtocolMatrix is open, let ProtocolMatrix handle unsaved guard/dialog.
  // This prevents double dialogs (one from Scratch + one from ProtocolMatrix).
    if (this.showMatrix || this.showLogic || this.showValueAssignments) {
      next();
      return;
    }

  // Allow navigation if explicitly allowed (save/discard flows)
    if (this.scratchAllowInternalNav) {
      next();
      return;
    }

  // IMPORTANT FIX:
  // Going back from Forms builder to Study Creation step 1 is internal step navigation,
  // not an exit from study creation, so do NOT show unsaved dialog.
    const isBackToStudyCreationStep5 =
      to?.name === "CreateStudy" && String(to?.query?.step || "") === "1";

    if (isBackToStudyCreationStep5) {
      next();
      return;
    }

  // If dialog already open, block duplicate navigation attempts
    if (this.showUnsavedDialog) {
      next(false);
      return;
    }

    const isDirty = !!this.$store.state.studyCreationDirty;

    if (!isDirty) {
      next();
      return;
    }

  // Block route navigation and open the same dialog
    this.openScratchUnsavedDialog(() => this.$router.push(to.fullPath));
    next(false);
  },
  data() {
    let initialForms = [];
    try {
      const parsed = JSON.parse(localStorage.getItem("scratchForms") || "[]");
      initialForms = Array.isArray(parsed) ? parsed : [];
    } catch {
      initialForms = [];
    }

    // FIX: never allow empty forms array at startup
    if (!initialForms.length) initialForms = [{ sections: [] }];

    return {
      forms: initialForms,
      currentFormIndex: 0,
      activeSection: 0,
      activeTab: "template",
      generalFields: [],
      dataModels: [],
      shaclComponents: [],
      showModelDialog: false,
      currentModel: null,
      selectedProps: [],
      showMatrix: false,
      showLogic: false,
      showValueAssignments: false,
      visits: [],
      groups: [],
      assignments: [],
      showConfirmDialog: false,
      confirmDialogMessage: "",
      confirmCallback: null,
      showGenericDialog: false,
      genericDialogMessage: "",
      genericCallback: null,
      showConstraintsDialog: false,
      constraintsForm: {},
      currentFieldType: "",
      currentFieldIndices: {},
      showPreviewDialog: false,
      showUploadDialog: false,
      showInputDialog: false,
      inputDialogMessage: "",
      inputDialogValue: "",
      inputDialogCallback: null,
      showTableConfigurator: false,
      pendingTableField: null,
      showTableCopyDialog: false,
      pendingTableCopyIndices: null,

      // Template search
      searchQuery: "",

      // OBI search state
      obiQuery: "",
      obiResults: [],
      obiLoading: false,
      obiError: "",
      selectedTermIds: new Set(),
      obiDebounceTimer: null,

      // Limit controls
      requestedLimit: 50,
      limitStep: 50,

      // Template takeover target controls
      modelAddToExisting: false,
      modelTargetSectionIndex: 0,

      showImportCsvDialog: false,

      dragState: {
        kind: null,
        fromSection: null,
        fromField: null,
        overSection: null,
        overField: null,
        position: null
      },

      uidCounter: 1,
      sectionUidMap: new WeakMap(),
      fieldUidMap: new WeakMap(),

      showAdditionalOptions: false,

      // --- GLOBAL DIRTY FLAG (do not mark dirty during initial hydration) ---
      hydratingScratch: true,

      // --- SAVE & EXIT (Scratch local dialog/handler) ---
      scratchUnsavedBusy: false,
      scratchAllowInternalNav: false,
      // --- UNSAVED CHANGES DIALOG (ScratchFormComponent exit guard) ---
      showUnsavedDialog: false,
      unsavedDialogMessage: "You are exiting study creation. Do you want to continue editing? If you leave now, your current progress will be saved as Draft in Dashboard.",
      unsavedPendingAction: null,
      unsavedBusy: false,

      showRearrangeDialog: false,
      rearrangeInitialFocus: null,

      showFieldOptionRemapDialog: false,
      fieldOptionRemapContext: null,
      pendingFieldOptionRemapResolve: null,
      pendingFieldOptionRemapQueue: [],
      pendingFieldOptionRemapSourceLabel: "",
      pendingFieldOptionRemapIndex: 0,
      pendingFieldOptionRemapNextOptions: [],
      scratchScrollDirection: "down",
      hasScratchScrollableContent: false,
      builderStickyResizeObserver: null,
      builderPointerPosition: null,
      activeSectionScrollFrame: null,
      addedFieldRevealFrame: null,
      suppressScrollActiveUntil: 0,
      recentlyAddedSectionUid: "",
      recentlyAddedFieldId: "",
      recentlyAddedHighlightTimer: null,

      showSaveTemplateFormDialog: false,
      saveTemplateBusy: false,

      savedTemplates: [],
      savedTemplateQuery: "",
      savedTemplatesLoading: false,
      savedTemplatesError: "",

      showDeleteSavedTemplateDialog: false,
      selectedSavedTemplateForDelete: null,
      deleteTemplateBusy: false,
    };
  },

  computed: {
    filteredSavedTemplates() {
      const q = String(this.savedTemplateQuery || "").trim().toLowerCase();
      const templates = Array.isArray(this.savedTemplates) ? this.savedTemplates : [];

      if (!q) return templates;

      return templates.filter(template => {
        const text = [
          template.title,
          template.description,
          ...(template.fields || []).flatMap(field => [
            field.label,
            field.name,
            field.type,
            field.description
          ])
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return text.includes(q);
      });
    },
    currentEditingFieldDefinition() {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices || {};
      const field = this.currentForm.sections?.[sectionIndex]?.fields?.[fieldIndex];
      return field ? JSON.parse(JSON.stringify(field)) : {};
    },
    allSelectablePropsSelected() {
      if (!this.currentModel || !Array.isArray(this.currentModel.fields) || !this.currentModel.fields.length) {
        return false;
      }

      const selectableIndexes = this.currentModel.fields
        .map((prop, i) => ({ prop, i }))
        .filter(({ prop }) => !(this.modelAddToExisting && this.isPropAlreadyInTargetSection(prop)));

      if (!selectableIndexes.length) return false;

      return selectableIndexes.every(({ i }) => !!this.selectedProps[i]);
    },
    currentEditingFieldKey() {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices || {};
      const field = this.currentForm.sections?.[sectionIndex]?.fields?.[fieldIndex];
      if (!field) return "";
      return this.getFieldLogicKey(field, sectionIndex, fieldIndex);
    },

    currentEditingFieldLabel() {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices || {};
      const field = this.currentForm.sections?.[sectionIndex]?.fields?.[fieldIndex];
      if (!field) return "";
      return field.label || field.name || "";
    },
    icons() { return icons; },
    studyDetails() { return this.$store.state.studyDetails || {}; },

    // FIX: self-healing current form so UI always has a real mutable target
    currentForm() {
      this.ensureCurrentFormExists();
      return this.forms[this.currentFormIndex];
    },

    selectedModels() {
      return (this.currentForm.sections || []).map(sec => ({
        _id: sec._id,
        title: sec.title,
        fields: sec.fields
      }));
    },

    filteredDataModels() {
      const models = this.dataModels || [];
      const q = (this.searchQuery || "").trim().toLowerCase();
      if (!q) return models;

      return models
        .map(m => {
          const titleMatches = (m.title || "").toLowerCase().includes(q);
          const matchingFields = (m.fields || []).filter(f =>
            (f.label || "").toLowerCase().includes(q) ||
            (f.name || "").toLowerCase().includes(q)
          );

          if (titleMatches || matchingFields.length) {
            return { ...m, fields: matchingFields.length ? matchingFields : m.fields };
          }
          return null;
        })
        .filter(Boolean);
    },

    canShowMore() {
      const qOk = this.obiQuery.trim().length >= 2;
      return qOk && (this.obiResults.length >= this.requestedLimit) && !this.obiLoading;
    },

    authHeader() {
      const token = this.$store.state.token;
      return token ? { Authorization: `Bearer ${token}` } : {};
    },

    currentUserId() {
      return this.$store.state.user?.id || null;
    },

    currentStudyId() {
      return this.studyDetails?.study_metadata?.id ?? this.studyDetails?.study?.id ?? null;
    }
  },

  watch: {
    visits: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    groups: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    selectedModels: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },

    forms: {
      deep: true,
      handler(f) {
        localStorage.setItem("scratchForms", JSON.stringify(f));
        if (!this.hydratingScratch) {
          this.$store.commit("setStudyCreationDirty", true);
        }
      }
    },
    "currentForm.sections": {
      deep: true,
      handler() {
        this.$nextTick(() => {
          this.updateScratchScrollState();
        });
      }
    },

    activeTab(newVal) {
      if (newVal !== "template" && this.searchQuery) this.searchQuery = "";
      if (newVal !== "obi") this.resetObiState();
      if (newVal !== "savedTemplates" && this.savedTemplateQuery) {
        this.savedTemplateQuery = "";
      }

      if (newVal === "savedTemplates") {
        this.loadSavedTemplates();
      }
    },

    modelAddToExisting() {
      this.$nextTick(() => this.syncSelectedPropsForExistingSection());
    },

    modelTargetSectionIndex() {
      this.$nextTick(() => this.syncSelectedPropsForExistingSection());
    }
  },

  async mounted() {
    document.addEventListener("click", this.onGlobalClick);
    window.addEventListener("beforeunload", this.beforeUnloadHandler);
    window.addEventListener("resize", this.updateScratchScrollState);
    this.hydratingScratch = true;

    const hasStudyForms =
      Array.isArray(this.studyDetails.forms) && this.studyDetails.forms.length;

    const isEditMode = !!this.currentStudyId;
    console.log("[Scratch] mounted studyDetails =", JSON.parse(JSON.stringify(this.studyDetails || {})));
    console.log("[Scratch] mounted studyDetails.forms =", JSON.parse(JSON.stringify(this.studyDetails?.forms || [])));
    console.log("[Scratch] mounted currentStudyId =", this.currentStudyId);
    if (isEditMode && hasStudyForms) {
      this.forms = JSON.parse(JSON.stringify(this.studyDetails.forms));
      console.log("[Scratch] mounted hydrated forms =", JSON.parse(JSON.stringify(this.forms || [])));
      console.log("[Scratch] mounted hydrated current form =", JSON.parse(JSON.stringify(this.forms?.[this.currentFormIndex] || {})));
      console.log("[Scratch] mounted hydrated current logic =", JSON.parse(JSON.stringify(this.forms?.[this.currentFormIndex]?.logic || {})));
      localStorage.setItem("scratchForms", JSON.stringify(this.forms));
    } else {
      const stored = localStorage.getItem("scratchForms");

      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          this.forms = (Array.isArray(parsed) && parsed.length) ? parsed : [{ sections: [] }];
        } catch {
          this.forms = [{ sections: [] }];
        }
      } else if (hasStudyForms) {
        this.forms = JSON.parse(JSON.stringify(this.studyDetails.forms));
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } else {
        this.forms = [{ sections: [] }];
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      }
    }

    this.normalizeAllForms();

      // FIX: ensure current slot always exists after hydration too
    this.ensureCurrentFormExists();

    this.visits = Array.isArray(this.studyDetails.visits)
      ? JSON.parse(JSON.stringify(this.studyDetails.visits))
      : [];
    this.groups = Array.isArray(this.studyDetails.groups)
      ? JSON.parse(JSON.stringify(this.studyDetails.groups))
      : [];
    this.adjustAssignments();

    try {
      const res = await axios.get("/forms/available-fields");
      this.generalFields = res.data.map((f, idx) => ({
        ...f,
        name: f.name || `${f.type}_${idx}`,
        description: f.helpText || f.placeholder || "",
        options: (f.type === "select" || f.type === "radio")
          ? (Array.isArray(f.options) && f.options.length ? f.options : ["Option 1"])
          : (f.options || []),
        constraints: f.constraints || {}
      }));
      this.generalFields.push({
        name: "table",
        label: "Table",
        type: "table",
        icon: "fas fa-table",
        description: "2D tabular input with configurable columns and row expansion",
        constraints: {}
      });
    } catch (e) {
      console.error("Failed to load custom fields", e);
    }

    await this.loadDataModels();
    await this.loadSavedTemplates();
    this.$nextTick(() => {
      this.hydratingScratch = false;
      this.refreshBuilderStickyObserver();
      this.updateScratchScrollState();
    });
  },

  beforeUnmount() {
    document.removeEventListener("click", this.onGlobalClick);
    window.removeEventListener("beforeunload", this.beforeUnloadHandler);
    window.removeEventListener("resize", this.updateScratchScrollState);
    if (this.builderStickyResizeObserver) {
      this.builderStickyResizeObserver.disconnect();
      this.builderStickyResizeObserver = null;
    }
    if (this.activeSectionScrollFrame !== null) {
      window.cancelAnimationFrame(this.activeSectionScrollFrame);
      this.activeSectionScrollFrame = null;
    }
    if (this.addedFieldRevealFrame !== null) {
      window.cancelAnimationFrame(this.addedFieldRevealFrame);
      this.addedFieldRevealFrame = null;
    }
    if (this.recentlyAddedHighlightTimer) {
      window.clearTimeout(this.recentlyAddedHighlightTimer);
      this.recentlyAddedHighlightTimer = null;
    }
  },

  methods: {
    openDeleteSavedTemplateDialog(template) {
      const record = template?._savedTemplateRecord;

      if (!record) {
        this.openGenericDialog("Could not find saved template details.");
        return;
      }

      this.selectedSavedTemplateForDelete = record;
      this.showDeleteSavedTemplateDialog = true;
    },

    closeDeleteSavedTemplateDialog() {
      if (this.deleteTemplateBusy) return;

      this.showDeleteSavedTemplateDialog = false;
      this.selectedSavedTemplateForDelete = null;
    },

    async handleDeleteSavedTemplate(payload) {
      if (this.deleteTemplateBusy) return;

      const record = this.selectedSavedTemplateForDelete;

      if (!record?.id) {
        this.openGenericDialog("Could not identify saved template.");
        return;
      }

      try {
        this.deleteTemplateBusy = true;

        if (payload.type === "all") {
          await axios.delete(`/forms/saved-templates/${record.id}`, {
            headers: this.authHeader
          });
        } else {
          const sections = Array.isArray(record?.form_schema?.sections)
            ? record.form_schema.sections
            : [];

          const deleteIndexes = new Set(payload.sectionIndexes || []);

          const remainingSections = sections.filter((_, index) => !deleteIndexes.has(index));

          if (!remainingSections.length) {
            await axios.delete(`/forms/saved-templates/${record.id}`, {
              headers: this.authHeader
            });
          } else {
            await axios.patch(
              `/forms/saved-templates/${record.id}`,
              {
                form_schema: {
                  ...record.form_schema,
                  sections: remainingSections
                },
                source_type: remainingSections.length === 1 ? "section_subset" : record.source_type
              },
              {
                headers: this.authHeader
              }
            );
          }
        }

        this.showDeleteSavedTemplateDialog = false;
        this.selectedSavedTemplateForDelete = null;

        await this.loadSavedTemplates();

        this.openGenericDialog("Saved template updated successfully.");
      } catch (e) {
        console.error("Failed to delete saved template/sections", e);

        const message =
          e?.response?.data?.detail ||
          e?.response?.data?.message ||
          "Failed to delete saved template.";

        this.openGenericDialog(message);
      } finally {
        this.deleteTemplateBusy = false;
      }
    },
    canDeleteSavedTemplate(template) {
      const role = String(this.$store.state.user?.profile?.role || this.$store.state.user?.role || "")
        .trim()
        .toLowerCase();

      const isAdmin = role === "admin";
      const isOwner = Number(template?._createdBy) === Number(this.currentUserId);

      return isAdmin || isOwner;
    },
    openSaveTemplateFormDialog() {
      this.closeAdditionalOptions();
      this.ensureCurrentFormExists();
      this.showSaveTemplateFormDialog = true;
    },

    closeSaveTemplateFormDialog() {
      if (this.saveTemplateBusy) return;
      this.showSaveTemplateFormDialog = false;
    },

    async handleSaveTemplateForm(meta) {
      if (this.saveTemplateBusy) return;

      try {
        this.saveTemplateBusy = true;

        const payload = this.buildSavedTemplatePayload(meta);

        await axios.post("/forms/saved-templates", payload, {
          headers: this.authHeader
        });

        this.showSaveTemplateFormDialog = false;
        await this.loadSavedTemplates();
        this.activeTab = "savedTemplates";

        this.openGenericDialog("Template saved successfully.");
      } catch (e) {
        console.error("Failed to save reusable template", e);

        const message =
          e?.response?.data?.detail ||
          e?.response?.data?.message ||
          "Failed to save template.";

        this.openGenericDialog(message);
      } finally {
        this.saveTemplateBusy = false;
      }
    },

    buildSavedTemplatePayload(meta) {
      this.ensureCurrentFormExists();

      const isSelectedSections = meta.type === "sections";

      const selectedSections = isSelectedSections
        ? (meta.sectionIndexes || []).map(index => this.currentForm.sections?.[index])
        : this.currentForm.sections;

      const sections = (selectedSections || [])
        .filter(Boolean)
        .map(section => this.toReusableBasicSection(section));

      return {
        title: meta.title,
        description: meta.description,
        source_type: isSelectedSections ? "section_subset" : "form",
        form_schema: {
          sections
        }
      };
    },
    toReusableBasicSection(section) {
      return {
        _id: section._id || this.uuidForLogic(),
        title: section.title || "Untitled Section",
        description: section.description || "",
        collapsed: false,
        fields: Array.isArray(section.fields)
          ? section.fields.map(field => this.toReusableBasicField(field))
          : []
      };
    },

    toReusableBasicField(field) {
      const cloned = JSON.parse(JSON.stringify(field || {}));

      return {
        ...cloned,
        _id: cloned._id || this.uuidForLogic(),
        value: this.emptyReusableFieldValue(cloned),
        constraints: this.getBasicConstraintsForCopiedField(cloned)
      };
    },

    emptyReusableFieldValue(field) {
      const type = String(field?.type || "").toLowerCase();

      if (type === "checkbox") return false;
      if (type === "file") return [];
      if (type === "table") return { rows: [] };

      return "";
    },

    async loadSavedTemplates() {
      if (this.savedTemplatesLoading) return;

      try {
        this.savedTemplatesLoading = true;
        this.savedTemplatesError = "";

        const res = await axios.get("/forms/saved-templates", {
          headers: this.authHeader
        });

        const records = Array.isArray(res.data)
          ? res.data
          : Array.isArray(res.data?.items)
            ? res.data.items
            : [];

        this.savedTemplates = records.flatMap(record =>
          this.savedTemplateRecordToModels(record)
        );
      } catch (e) {
        console.error("Failed to load reusable templates", e);
        this.savedTemplatesError = "Failed to load saved templates.";
        this.savedTemplates = [];
      } finally {
        this.savedTemplatesLoading = false;
      }
    },

    savedTemplateRecordToModels(record) {
      const sections = Array.isArray(record?.form_schema?.sections)
        ? record.form_schema.sections
        : [];

      if (!sections.length) return [];

      return sections.map((section, index) => ({
        _savedTemplateId: record.id,
        _savedSectionIndex: index,
        _createdBy: record.created_by,

        // keep full original record for delete/edit
        _savedTemplateRecord: record,

        sourceType: record.source_type,

        // Keep saved template title same
        title: record.title,

        // Add section name separately so cards are distinguishable
        sectionTitle: section.title || `Section ${index + 1}`,

        description: record.description,
        fields: Array.isArray(section.fields) ? section.fields : []
      }));
    },

    async deleteSavedTemplate(template) {
      const id = template?._savedTemplateId || template?.id;

      if (!id) {
        this.openGenericDialog("Could not identify saved template.");
        return;
      }

      try {
        await axios.delete(`/forms/saved-templates/${id}`, {
          headers: this.authHeader
        });

        await this.loadSavedTemplates();

        this.openGenericDialog("Template deleted successfully.");
      } catch (e) {
        console.error("Failed to delete saved template", e);

        const message =
          e?.response?.data?.detail ||
          e?.response?.data?.message ||
          "Failed to delete template.";

        this.openGenericDialog(message);
      }
    },
    getScratchScrollEl() {
      const el = this.$refs.scratchScrollEl;
      return Array.isArray(el) ? el[0] : el;
    },

    getBuilderStickyBar() {
      const el = this.$refs.builderStickyBar;
      return Array.isArray(el) ? el[0] : el;
    },

    updateBuilderStickyHeight() {
      this.$nextTick(() => {
        const scrollEl = this.getScratchScrollEl();
        const stickyBar = this.getBuilderStickyBar();
        if (!scrollEl || !stickyBar) return;

        const height = Math.ceil(stickyBar.getBoundingClientRect().height || 64);
        scrollEl.style.setProperty("--builder-sticky-height", `${height}px`);
      });
    },

    refreshBuilderStickyObserver() {
      this.$nextTick(() => {
        if (this.builderStickyResizeObserver) {
          this.builderStickyResizeObserver.disconnect();
          this.builderStickyResizeObserver = null;
        }

        const stickyBar = this.getBuilderStickyBar();
        if (stickyBar && typeof ResizeObserver !== "undefined") {
          this.builderStickyResizeObserver = new ResizeObserver(() => {
            this.updateBuilderStickyHeight();
          });
          this.builderStickyResizeObserver.observe(stickyBar);
        }

        this.updateBuilderStickyHeight();
      });
    },

    updateScratchScrollState() {
      this.updateBuilderStickyHeight();

      this.$nextTick(() => {
        const el = this.getScratchScrollEl();
        if (!el) {
          this.hasScratchScrollableContent = false;
          this.scratchScrollDirection = "down";
          return;
        }

        const canScroll = el.scrollHeight > el.clientHeight + 4;
        this.hasScratchScrollableContent = canScroll;

        if (!canScroll) {
          this.scratchScrollDirection = "down";
          return;
        }

        const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
        this.scratchScrollDirection = nearBottom ? "up" : "down";
      });
    },

    onScratchScroll() {
      const el = this.getScratchScrollEl();
      if (!el) return;

      const canScroll = el.scrollHeight > el.clientHeight + 4;
      this.hasScratchScrollableContent = canScroll;

      if (!canScroll) {
        this.scratchScrollDirection = "down";
        return;
      }

      const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
      this.scratchScrollDirection = nearBottom ? "up" : "down";
      this.scheduleActiveSectionFromPointer();
    },

    onBuilderPointerMove(event) {
      const pointerType = String(event?.pointerType || "mouse").toLowerCase();
      if (pointerType !== "mouse" && pointerType !== "pen") return;

      this.builderPointerPosition = {
        x: Number(event.clientX),
        y: Number(event.clientY),
      };
    },

    onBuilderPointerLeave() {
      this.builderPointerPosition = null;
    },

    scheduleActiveSectionFromPointer() {
      if (
        !this.builderPointerPosition ||
        Date.now() < this.suppressScrollActiveUntil ||
        this.activeSectionScrollFrame !== null
      ) {
        return;
      }

      this.activeSectionScrollFrame = window.requestAnimationFrame(() => {
        this.activeSectionScrollFrame = null;
        if (
          !this.builderPointerPosition ||
          Date.now() < this.suppressScrollActiveUntil
        ) {
          return;
        }

        const scrollEl = this.getScratchScrollEl();
        if (!scrollEl) return;

        const { x, y } = this.builderPointerPosition;
        const scrollRect = scrollEl.getBoundingClientRect();
        if (
          !Number.isFinite(x) ||
          !Number.isFinite(y) ||
          x < scrollRect.left ||
          x > scrollRect.right ||
          y < scrollRect.top ||
          y > scrollRect.bottom
        ) {
          return;
        }

        const pointedElement = document.elementFromPoint(x, y);
        const sectionElement = pointedElement?.closest?.(".form-section");
        if (!sectionElement || !scrollEl.contains(sectionElement)) return;

        const sectionIndex = Number(sectionElement.dataset.builderSectionIndex);
        if (
          Number.isInteger(sectionIndex) &&
          sectionIndex >= 0 &&
          sectionIndex < this.currentForm.sections.length &&
          sectionIndex !== this.activeSection
        ) {
          this.activeSection = sectionIndex;
        }
      });
    },

    revealAddedField(sectionIndex, field) {
      const fieldId = String(field?._id || "");
      const section = this.currentForm.sections?.[sectionIndex];
      if (!fieldId || !section) return;

      this.activeSection = sectionIndex;
      this.recentlyAddedSectionUid = this.getSectionUid(section);
      this.recentlyAddedFieldId = fieldId;

      if (this.recentlyAddedHighlightTimer) {
        window.clearTimeout(this.recentlyAddedHighlightTimer);
      }
      this.recentlyAddedHighlightTimer = window.setTimeout(() => {
        this.recentlyAddedSectionUid = "";
        this.recentlyAddedFieldId = "";
        this.recentlyAddedHighlightTimer = null;
      }, 2200);

      this.$nextTick(() => {
        if (this.addedFieldRevealFrame !== null) {
          window.cancelAnimationFrame(this.addedFieldRevealFrame);
        }

        this.addedFieldRevealFrame = window.requestAnimationFrame(() => {
          this.addedFieldRevealFrame = null;
          const scrollEl = this.getScratchScrollEl();
          if (!scrollEl) return;

          const fieldElement = Array.from(
            scrollEl.querySelectorAll("[data-builder-field-id]")
          ).find((element) => element.dataset.builderFieldId === fieldId);
          if (!fieldElement) return;

          const containerRect = scrollEl.getBoundingClientRect();
          const fieldRect = fieldElement.getBoundingClientRect();
          const stickyHeight = Math.ceil(
            this.getBuilderStickyBar()?.getBoundingClientRect().height || 0
          );
          const sectionHeader = fieldElement
            .closest(".form-section")
            ?.querySelector(".section-header");
          const sectionHeaderHeight = Math.ceil(
            sectionHeader?.getBoundingClientRect().height || 0
          );
          const targetScrollTop = calculateContainedRevealScrollTop({
            scrollTop: scrollEl.scrollTop,
            scrollHeight: scrollEl.scrollHeight,
            clientHeight: scrollEl.clientHeight,
            containerTop: containerRect.top,
            targetTop: fieldRect.top,
            targetHeight: fieldRect.height,
            topClearance: stickyHeight + sectionHeaderHeight + 16,
          });

          // Keep pointer-based tracking from selecting a section underneath a
          // closing dialog while this intentional inner-container scroll runs.
          this.suppressScrollActiveUntil = Date.now() + 1200;
          scrollEl.scrollTo({ top: targetScrollTop, behavior: "smooth" });
          this.updateScratchScrollState();
        });
      });
    },

    toggleScratchScroll() {
      const el = this.getScratchScrollEl();
      if (!el) return;

      const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;

      if (nearBottom || this.scratchScrollDirection === "up") {
        el.scrollTo({
          top: 0,
          behavior: "smooth"
        });
      } else {
        el.scrollTo({
          top: el.scrollHeight,
          behavior: "smooth"
        });
      }
    },
    normalizeAllForms() {
      if (!Array.isArray(this.forms)) {
        this.forms = [];
      }

      this.forms = this.forms.map((form) => {
        const safeForm = form && typeof form === "object" ? form : {};

        return {
          ...safeForm,
          sections: Array.isArray(safeForm.sections) ? safeForm.sections : [],
          logic: {
            version: safeForm.logic?.version || 1,
            calculations: Array.isArray(safeForm.logic?.calculations) ? safeForm.logic.calculations : [],
            conditions: Array.isArray(safeForm.logic?.conditions) ? safeForm.logic.conditions : [],
            valueAssignments: Array.isArray(safeForm.logic?.valueAssignments) ? safeForm.logic.valueAssignments : []
          }
        };
      });

      if (!this.forms.length) {
        this.forms = [{
          sections: [],
          logic: { version: 1, calculations: [], conditions: [], valueAssignments: [] }
        }];
      }
    },

    getBasicConstraintsForCopiedField(field) {
      const c = JSON.parse(JSON.stringify(field?.constraints || {}));
      const type = String(field?.type || "").toLowerCase();

      const basic = {
        required: !!c.required,
        readonly: !!c.readonly,
        helpText: c.helpText || "",
        placeholder: c.placeholder || "",
      };

      if (type === "date") {
        basic.dateFormat = c.dateFormat || "dd.MM.yyyy";
      }

      if (type === "time") {
        basic.hourCycle = c.hourCycle || "24";
      }

      if (type === "slider") {
        basic.mode = c.mode === "linear" ? "linear" : "slider";
        basic.min = Number.isFinite(c.min) ? c.min : 1;
        basic.max = Number.isFinite(c.max) ? c.max : 100;
        basic.step = Number.isFinite(c.step) ? c.step : 1;
        basic.percent = !!c.percent;
        basic.leftLabel = c.leftLabel || "";
        basic.rightLabel = c.rightLabel || "";
        basic.marks = Array.isArray(c.marks) ? JSON.parse(JSON.stringify(c.marks)) : [];
      }

      if (type === "file") {
        basic.allowedFormats = Array.isArray(c.allowedFormats) ? [...c.allowedFormats] : [];
        basic.storagePreference = c.storagePreference === "url" ? "url" : "local";
        basic.allowMultipleFiles = c.allowMultipleFiles !== false;
        basic.modalities = Array.isArray(c.modalities) ? [...c.modalities] : [];
      }

      // DO NOT copy advanced logic
      basic.visibilityLogic = {
        action: "show",
        match: "all",
        rules: []
      };

      return basic;
    },

    haveChoiceOptionsChanged(previousField, nextField) {
      const prevType = String(previousField?.type || "").toLowerCase();
      const nextType = String(nextField?.type || "").toLowerCase();

      if (!["radio", "select"].includes(prevType) || !["radio", "select"].includes(nextType)) {
        return false;
      }

      const prev = (Array.isArray(previousField?.options) ? previousField.options : [])
        .map(v => String(v || "").trim())
        .filter(Boolean);

      const next = (Array.isArray(nextField?.options) ? nextField.options : [])
        .map(v => String(v || "").trim())
        .filter(Boolean);

      if (prev.length !== next.length) return true;

      for (let i = 0; i < prev.length; i++) {
        if (prev[i] !== next[i]) return true;
      }

      return false;
    },

    buildBuilderFieldLookup() {
      const lookup = new Map();

      (this.currentForm.sections || []).forEach((section, si) => {
        (section.fields || []).forEach((field, fi) => {
          const keys = [
            field?._id,
            field?.id,
            field?.field_id,
            field?.uid,
            field?.key,
            field?.name,
          ].filter(Boolean);

          const meta = { section, field, sectionIndex: si, fieldIndex: fi };

          keys.forEach((k) => {
            lookup.set(String(k), meta);
          });
        });
      });

      return lookup;
    },

    getFieldDisplayName(sectionIndex, fieldIndex) {
      const section = this.currentForm.sections?.[sectionIndex];
      const field = section?.fields?.[fieldIndex];
      if (!field) return "Unknown field";
      const sectionTitle = section?.title || `Section ${sectionIndex + 1}`;
      const fieldTitle = field.label || field.name || `Field ${fieldIndex + 1}`;
      return `${sectionTitle} → ${fieldTitle}`;
    },

    getDependentFieldsFor(sectionIndex, fieldIndex) {
      const sourceField = this.currentForm.sections?.[sectionIndex]?.fields?.[fieldIndex];
      if (!sourceField) return [];

      const sourceKey = this.getFieldLogicKey(sourceField, sectionIndex, fieldIndex);

      const out = [];

      (this.currentForm.sections || []).forEach((section, si) => {
        (section.fields || []).forEach((field, fi) => {
          if (si === sectionIndex && fi === fieldIndex) return;

          const rules = field?.constraints?.visibilityLogic?.rules;
          if (!Array.isArray(rules) || !rules.length) return;

          const matches = rules
            .map((rule, ri) => ({ rule, ri }))
            .filter(({ rule }) => String(rule?.sourceFieldKey || "") === String(sourceKey));

          if (matches.length) {
            out.push({
              sectionIndex: si,
              fieldIndex: fi,
              section,
              field,
              matches,
            });
          }
        });
      });

      return out;
    },

    getDependenciesOfField(sectionIndex, fieldIndex) {
      const field = this.currentForm.sections?.[sectionIndex]?.fields?.[fieldIndex];
      const rules = field?.constraints?.visibilityLogic?.rules;
      if (!Array.isArray(rules) || !rules.length) return [];

      const lookup = this.buildBuilderFieldLookup();

      return rules.map((rule) => {
        const src = lookup.get(String(rule?.sourceFieldKey || ""));
        return {
          rule,
          sourceLabel: src
            ? this.getFieldDisplayName(src.sectionIndex, src.fieldIndex)
            : `Unknown source (${rule?.sourceFieldKey || "missing"})`
        };
      });
    },

    hasFieldDependencies(sectionIndex, fieldIndex) {
      return (
        this.getDependentFieldsFor(sectionIndex, fieldIndex).length > 0 ||
        this.getDependenciesOfField(sectionIndex, fieldIndex).length > 0
      );
    },

    openDependencyInfoDialog(sectionIndex, fieldIndex) {
      const currentLabel = this.getFieldDisplayName(sectionIndex, fieldIndex);
      const dependents = this.getDependentFieldsFor(sectionIndex, fieldIndex);
      const dependencies = this.getDependenciesOfField(sectionIndex, fieldIndex);

      const dependentText = dependents.length
        ? dependents
            .map((d) => {
              const rulesText = d.matches
                .map(({ rule }) => {
                  const val = Array.isArray(rule?.value)
                    ? `[${rule.value.join(", ")}]`
                    : (rule?.value ?? "");
                  return `${rule?.operator || "eq"} ${val}`;
                })
                .join(" | ");
              return `• ${this.getFieldDisplayName(d.sectionIndex, d.fieldIndex)} (${rulesText})`;
            })
            .join("\n")
        : "• No fields depend on this field.";

      const dependencyText = dependencies.length
        ? dependencies
            .map((d) => {
              const val = Array.isArray(d.rule?.value)
                ? `[${d.rule.value.join(", ")}]`
                : (d.rule?.value ?? "");
              return `• ${d.sourceLabel} (${d.rule?.operator || "eq"} ${val})`;
            })
            .join("\n")
        : "• This field does not depend on any other field.";

      this.openGenericDialog(
        `Field: ${currentLabel}\n\n` +
        `Depends on this field:\n${dependentText}\n\n` +
        `This field depends on:\n${dependencyText}`
      );
    },

    collectRemovedChoiceOptions(previousField, nextField) {
      const previousOptions = (Array.isArray(previousField?.options) ? previousField.options : [])
        .map(v => String(v ?? "").trim())
        .filter(Boolean);

      const nextOptions = (Array.isArray(nextField?.options) ? nextField.options : [])
        .map(v => String(v ?? "").trim())
        .filter(Boolean);

      return previousOptions.filter(v => !nextOptions.includes(v));
    },

    extractMatchingRemovedValues(candidate, removedOptions) {
      if (Array.isArray(candidate)) {
        return candidate
          .map(v => String(v ?? "").trim())
          .filter(v => v && removedOptions.includes(v));
      }

      const single = String(candidate ?? "").trim();
      return single && removedOptions.includes(single) ? [single] : [];
    },

    removeAffectedDependentVisibilityRules({ sourceSectionIndex, sourceFieldIndex, previousField, nextField }) {
      const removedOptions = this.collectRemovedChoiceOptions(previousField, nextField);
      if (!removedOptions.length) return;

      const dependents = this.getDependentFieldsFor(sourceSectionIndex, sourceFieldIndex);
      if (!dependents.length) return;

      const impactedFields = [];
      const sourceFieldLabel = previousField?.label || previousField?.name || "Field";
      const sourceFieldKey = this.getFieldLogicKey(previousField, sourceSectionIndex, sourceFieldIndex);

      dependents.forEach((dep) => {
        const rules = dep.field?.constraints?.visibilityLogic?.rules;
        if (!Array.isArray(rules) || !rules.length) return;

        const remainingRules = [];
        const removedRuleSummaries = [];

        rules.forEach((rule) => {
          const sameSource = String(rule?.sourceFieldKey || "") === String(sourceFieldKey);

          if (!sameSource) {
            remainingRules.push(rule);
            return;
          }

          const matchesValue = this.extractMatchingRemovedValues(rule?.value, removedOptions);
          const matchesValueTo = this.extractMatchingRemovedValues(rule?.valueTo, removedOptions);
          const matchedRemovedValues = [...new Set([...matchesValue, ...matchesValueTo])];

          if (matchedRemovedValues.length) {
            removedRuleSummaries.push({
              operator: String(rule?.operator || "rule"),
              removedValues: matchedRemovedValues,
            });
          } else {
            remainingRules.push(rule);
          }
        });

        if (removedRuleSummaries.length) {
          dep.field.constraints = dep.field.constraints || {};
          dep.field.constraints.visibilityLogic = dep.field.constraints.visibilityLogic || {
            action: "show",
            match: "all",
            rules: []
          };

          dep.field.constraints.visibilityLogic.rules = remainingRules;

          impactedFields.push({
            fieldLabel: this.getFieldDisplayName(dep.sectionIndex, dep.fieldIndex),
            removedRuleSummaries,
          });
        }
      });

      if (!impactedFields.length) return;

      const messageLines = [
        `Options were changed in "${sourceFieldLabel}".`,
        ``,
        `Some removed option values were still used in visibility logic, so those affected visibility rule(s) were removed automatically.`,
        ``,
        `Please review and add visibility logic again if still needed.`,
        ``,
        `Affected field(s):`
      ];

      impactedFields.forEach((item) => {
        messageLines.push(`• ${item.fieldLabel}`);
        item.removedRuleSummaries.forEach((summary) => {
          messageLines.push(`  - ${summary.operator}: ${summary.removedValues.join(", ")}`);
        });
      });

      this.openGenericDialog(messageLines.join("\n"));
    },

    removeAffectedValueAssignmentRulesForOptions({
      sourceSectionIndex,
      sourceFieldIndex,
      previousField,
      nextField,
    }) {
      const removedOptions = this.collectRemovedChoiceOptions(previousField, nextField);
      if (!removedOptions.length) return;

      const fieldKey = this.getFieldLogicKey(
        previousField,
        sourceSectionIndex,
        sourceFieldIndex
      );
      const rules = this.currentForm?.logic?.valueAssignments;
      if (!Array.isArray(rules) || !rules.length) return;

      this.currentForm.logic.valueAssignments = rules.filter((rule) => {
        const targetUsesRemovedOutput =
          String(rule?.targetFieldKey || "") === String(fieldKey) &&
          removedOptions.includes(String(rule?.outputValue ?? ""));

        const conditionUsesRemovedValue = (rule?.conditions || []).some(
          (condition) =>
            String(condition?.sourceFieldKey || "") === String(fieldKey) &&
            (
              this.extractMatchingRemovedValues(condition?.value, removedOptions).length ||
              this.extractMatchingRemovedValues(condition?.valueTo, removedOptions).length
            )
        );

        return !targetUsesRemovedOutput && !conditionUsesRemovedValue;
      });
    },

    removeValueAssignmentReferencesForFields(fields = []) {
      const keys = new Set(
        fields.flatMap(({ field, sectionIndex, fieldIndex }) => [
          this.getFieldLogicKey(field, sectionIndex, fieldIndex),
          field?._id,
          field?.id,
          field?.name,
        ]).filter(Boolean).map(String)
      );

      const rules = this.currentForm?.logic?.valueAssignments;
      if (!keys.size || !Array.isArray(rules)) return;

      this.currentForm.logic.valueAssignments = rules.filter((rule) => {
        if (keys.has(String(rule?.targetFieldKey || ""))) return false;
        return !(rule?.conditions || []).some((condition) =>
          keys.has(String(condition?.sourceFieldKey || ""))
        );
      });
    },

    togglePropSelection(i, prop) {
      if (this.modelAddToExisting && this.isPropAlreadyInTargetSection(prop)) return;

      const next = [...this.selectedProps];
      next[i] = !next[i];
      this.selectedProps = next;
    },

    toggleSelectAllProps() {
      if (!this.currentModel || !Array.isArray(this.currentModel.fields)) return;

      const next = [...this.selectedProps];

      if (this.allSelectablePropsSelected) {
        this.currentModel.fields.forEach((prop, i) => {
          if (this.modelAddToExisting && this.isPropAlreadyInTargetSection(prop)) return;
          next[i] = false;
        });
      } else {
        this.currentModel.fields.forEach((prop, i) => {
          if (this.modelAddToExisting && this.isPropAlreadyInTargetSection(prop)) return;
          next[i] = true;
        });
      }

      this.selectedProps = next;
    },

    openRearrangeDialog(focus = null) {
      this.ensureCurrentFormExists();
      this.ensurePersistentIdsForLogic();
      this.rearrangeInitialFocus = focus || null;
      this.showRearrangeDialog = true;
    },

    closeRearrangeDialog() {
      this.showRearrangeDialog = false;
      this.rearrangeInitialFocus = null;
    },

    applyRearrangedStructure(nextSections) {
      this.ensureCurrentFormExists();

      const safeSections = Array.isArray(nextSections)
        ? JSON.parse(JSON.stringify(nextSections))
        : [];

      this.forms[this.currentFormIndex].sections = safeSections;
      this.adjustAssignments();

      try {
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } catch (e) {
        console.error("Failed to persist rearranged structure", e);
      }

      this.$store.commit("setStudyDetails", {
        ...this.studyDetails,
        forms: JSON.parse(JSON.stringify(this.forms || []))
      });

      if (safeSections.length) {
        this.activeSection = Math.max(0, Math.min(this.activeSection, safeSections.length - 1));
        this.$nextTick(() => this.focusSection(this.activeSection));
      } else {
        this.activeSection = 0;
      }

      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }

      this.closeRearrangeDialog();
    },

    expandAllSections() {
      this.ensureCurrentFormExists();
      (this.currentForm.sections || []).forEach(sec => {
        sec.collapsed = false;
      });
      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }
    },

    collapseAllSections() {
      this.ensureCurrentFormExists();
      (this.currentForm.sections || []).forEach(sec => {
        sec.collapsed = true;
      });
      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }
    },

    onFieldSettingsClick(si, fi) {
      this.ensureCurrentFormExists();

      const field = this.currentForm.sections?.[si]?.fields?.[fi];
      if (!field) return;

      //SPECIAL CASE: TABLE -> open table configurator
      if (field.type === "table") {
        this.pendingTableField = JSON.parse(JSON.stringify(field));
        this.currentFieldIndices = { sectionIndex: si, fieldIndex: fi };
        this.showTableConfigurator = true;
        return;
      }

      this.openConstraintsDialog(si, fi);
    },
    openTableConfigurator(field) {
  // IMPORTANT: reset edit indices for new table creation
      this.currentFieldIndices = {};

      this.pendingTableField = {
        _id: this.uuidForLogic(),
        label: field?.label || "Table",
        name: `table_${Date.now()}`,
        type: "table",
        value: { rows: [] },
        constraints: {
          helpText: "",
          required: false,
          readonly: false,
          visibilityLogic: {
            action: "show",
            match: "all",
            rules: []
          }
        },
        tableConfig: {
          version: 1,
          mode: "2d",
          initialRows: 1,
          allowAddRows: true,
          showRowNumbers: true,
          columns: [
            {
              id: `col_${Date.now()}_1`,
              key: "column_1",
              label: "Column 1",
              type: "text",
              options: [],
              constraints: {}
            }
          ]
        }
      };

      this.showTableConfigurator = true;
    },

    handleTableConfiguratorSave(result) {
      if (!result?.ok) {
        this.openGenericDialog(result?.error || "Invalid table configuration.");
        return;
      }

      const builtField = JSON.parse(JSON.stringify(result.payload || {}));
      if (!builtField) return;

      this.ensureCurrentFormExists();

      const { sectionIndex, fieldIndex } = this.currentFieldIndices || {};
      const isEditingExisting =
        Number.isInteger(sectionIndex) &&
        Number.isInteger(fieldIndex) &&
        !!this.currentForm.sections?.[sectionIndex]?.fields?.[fieldIndex] &&
        this.currentForm.sections[sectionIndex].fields[fieldIndex]?.type === "table";

      if (isEditingExisting) {
        const existing = this.currentForm.sections[sectionIndex].fields[fieldIndex];

    // Preserve stable identity/name unless intentionally changed later
        builtField._id = existing._id || builtField._id || this.uuidForLogic();
        builtField.name = existing.name || builtField.name || `table_${Date.now()}`;

        this.currentForm.sections[sectionIndex].fields.splice(fieldIndex, 1, builtField);
      } else {
        if (!this.currentForm.sections.length) {
          this.addNewSection();
        }

        const sec = this.currentForm.sections[this.activeSection];
        if (!sec) {
          this.openGenericDialog("No active section available.");
          return;
        }

        if (sec.collapsed) sec.collapsed = false;

        const baseName = String(builtField.name || `table_${Date.now()}`).trim() || `table_${Date.now()}`;
        const existingNames = new Set((sec.fields || []).map(f => String(f?.name || "")));

        let uniqueName = baseName;
        let counter = 2;
        while (existingNames.has(uniqueName)) {
          uniqueName = `${baseName}_${counter}`;
          counter += 1;
        }

        builtField.name = uniqueName;
        builtField._id = builtField._id || this.uuidForLogic();

        sec.fields.push(builtField);
        this.revealAddedField(
          this.activeSection,
          sec.fields[sec.fields.length - 1]
        );
      }

      this.showTableConfigurator = false;
      this.pendingTableField = null;
      this.currentFieldIndices = {};

      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }
    },

    cancelTableConfigurator() {
      this.showTableConfigurator = false;
      this.pendingTableField = null;
    },

    openImportCsvDialog() {
      this.closeAdditionalOptions();
      this.showImportCsvDialog = true;
    },

    closeImportCsvDialog() {
      this.showImportCsvDialog = false;
    },

    handleImportedCsvFields(importedFields) {
      this.ensureCurrentFormExists();

      const fields = Array.isArray(importedFields) ? importedFields : [];
      if (!fields.length) {
        this.openGenericDialog("No fields were generated from the selected file.");
        return;
      }

      if (!this.currentForm.sections.length) {
        this.addNewSection();
      }

      const sec = this.currentForm.sections[this.activeSection];
      if (!sec) {
        this.openGenericDialog("No active section available.");
        return;
      }

      if (sec.collapsed) sec.collapsed = false;

      const existingNames = new Set((sec.fields || []).map(f => String(f?.name || "")));
      let added = 0;

      fields.forEach((field, idx) => {
        let candidateName = String(field?.name || `imported_field_${Date.now()}_${idx}`).trim();
        if (!candidateName) {
          candidateName = `imported_field_${Date.now()}_${idx}`;
        }

        let uniqueName = candidateName;
        let counter = 2;
        while (existingNames.has(uniqueName)) {
          uniqueName = `${candidateName}_${counter}`;
          counter += 1;
        }
        existingNames.add(uniqueName);

        sec.fields.push({
          ...JSON.parse(JSON.stringify(field)),
          _id: field?._id || this.uuidForLogic(),
          name: uniqueName,
          constraints: {
            visibilityLogic: {
              action: "show",
              match: "all",
              rules: []
            },
            ...(JSON.parse(JSON.stringify(field?.constraints || {})))
          }
        });

        added += 1;
      });

      this.showImportCsvDialog = false;

      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }

      this.openGenericDialog(`${added} field(s) imported into "${sec.title}".`);
    },

    uuidForLogic() {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
      return `id_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    },

    getFieldLogicKey(field, sectionIndex, fieldIndex) {
      if (!field || typeof field !== "object") return "";

      // Prefer persistent ID if available
      if (field._id) return String(field._id);

      // Fallback to name
      if (field.name) return String(field.name);

      // Last fallback
      return `section_${sectionIndex}_field_${fieldIndex}`;
    },

    applyLogicFormUpdate(updatedForm) {
      this.ensureCurrentFormExists();
      if (!updatedForm || typeof updatedForm !== "object") return;

      this.forms.splice(this.currentFormIndex, 1, JSON.parse(JSON.stringify(updatedForm)));

      try {
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } catch (e) {
        console.error("Failed to persist updated form from logic builder", e);
      }

      this.$store.commit("setStudyDetails", {
        ...this.studyDetails,
        forms: JSON.parse(JSON.stringify(this.forms || []))
      });

      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }
    },

    applyLogicPayload(logicPayload) {
      this.ensureCurrentFormExists();

      if (!this.forms[this.currentFormIndex].logic || typeof this.forms[this.currentFormIndex].logic !== "object") {
        this.forms[this.currentFormIndex].logic = { version: 1, calculations: [], conditions: [], valueAssignments: [] };
      }

      this.forms[this.currentFormIndex].logic = {
        version: logicPayload?.version || 2,
        calculations: Array.isArray(logicPayload?.calculations) ? logicPayload.calculations : [],
        conditions: Array.isArray(logicPayload?.conditions) ? logicPayload.conditions : [],
        valueAssignments: Array.isArray(logicPayload?.valueAssignments) ? logicPayload.valueAssignments : []
      };

      try {
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } catch (e) {
        console.error("Failed to persist logic payload", e);
      }

      this.$store.commit("setStudyDetails", {
        ...this.studyDetails,
        forms: JSON.parse(JSON.stringify(this.forms || []))
      });

      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }
    },

    onLogicUpdated(nextLogic) {
      this.ensureCurrentFormExists();

      const safeLogic = {
        version: nextLogic?.version || 2,
        calculations: Array.isArray(nextLogic?.calculations)
          ? JSON.parse(JSON.stringify(nextLogic.calculations))
          : [],
        conditions: Array.isArray(nextLogic?.conditions)
          ? JSON.parse(JSON.stringify(nextLogic.conditions))
          : [],
        valueAssignments: Array.isArray(nextLogic?.valueAssignments)
          ? JSON.parse(JSON.stringify(nextLogic.valueAssignments))
          : []
      };

      if (this.$set) this.$set(this.currentForm, "logic", safeLogic);
      else this.currentForm.logic = safeLogic;

      try {
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } catch (e) {
        console.error("Failed to persist logic into scratchForms", e);
      }

      if (!this.hydratingScratch) {
        this.$store.commit("setStudyCreationDirty", true);
      }
    },

    openLogicAndCalculations() {
      this.ensurePersistentIdsForLogic();

      try {
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } catch (e) {
        console.error("Failed to persist scratchForms before opening logic view", e);
      }

      this.showMatrix = false;
      this.showValueAssignments = false;
      this.showLogic = true;
    },

    openValueAssignments() {
      this.ensurePersistentIdsForLogic();

      try {
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } catch (e) {
        console.error("Failed to persist scratchForms before opening value assignments", e);
      }

      this.showMatrix = false;
      this.showLogic = false;
      this.showValueAssignments = true;
    },

    ensurePersistentIdsForLogic() {
      this.ensureCurrentFormExists();

      const form = this.forms[this.currentFormIndex];
      if (!form) return;

      (form.sections || []).forEach(sec => {
        if (!sec._id) sec._id = this.uuidForLogic();
        if (!Array.isArray(sec.fields)) sec.fields = [];

        sec.fields.forEach(f => {
          if (!f._id) f._id = this.uuidForLogic();
          if (!f.constraints || typeof f.constraints !== "object") {
            f.constraints = {};
          }
        });
      });

      if (!form.logic || typeof form.logic !== "object") {
        form.logic = { version: 1, calculations: [], conditions: [], valueAssignments: [] };
      }
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];
      if (!Array.isArray(form.logic.conditions)) form.logic.conditions = [];
      if (!Array.isArray(form.logic.valueAssignments)) form.logic.valueAssignments = [];
      if (!form.logic.version) form.logic.version = 1;

      // Mark dirty because IDs/logic are structural metadata
      if (!this.hydratingScratch) this.$store.commit("setStudyCreationDirty", true);
    },

    beforeUnloadHandler(e) {
      const isDirty = !!this.$store.state.studyCreationDirty;
      if (!isDirty) return;

      e.preventDefault();
      e.returnValue = "";
    },

    openScratchUnsavedDialog(pendingAction) {
      this.unsavedPendingAction = typeof pendingAction === "function" ? pendingAction : null;
      this.showUnsavedDialog = true;
    },

    onUnsavedKeepEditing() {
      if (this.unsavedBusy) return;
      this.showUnsavedDialog = false;
      this.unsavedPendingAction = null;
    },

    async confirmScratchExitWithoutSaving() {
      if (this.unsavedBusy) return;

      try {
        this.unsavedBusy = true;

        // User chose to leave without saving -> clear dirty flag
        this.$store.commit("setStudyCreationDirty", false);

        // allow one internal navigation without reopening dialog
        this.scratchAllowInternalNav = true;

        const pending = this.unsavedPendingAction;
        this.showUnsavedDialog = false;
        this.unsavedPendingAction = null;

        if (pending) {
          await Promise.resolve(pending());
        } else {
          await this.$router.back();
        }
      } finally {
        this.unsavedBusy = false;
        // release flag after nav tick
        this.$nextTick(() => {
          this.scratchAllowInternalNav = false;
        });
      }
    },
    ensureCurrentFormExists() {
      if (!Array.isArray(this.forms)) {
        this.forms = [{ sections: [], logic: { version: 1, calculations: [], conditions: [], valueAssignments: [] } }];
      }

      if (!Number.isInteger(this.currentFormIndex) || this.currentFormIndex < 0) {
        this.currentFormIndex = 0;
      }

      if (!this.forms.length) {
        this.forms.push({ sections: [], logic: { version: 1, calculations: [], conditions: [], valueAssignments: [] } });
      }

      if (!this.forms[this.currentFormIndex]) {
        while (this.forms.length <= this.currentFormIndex) {
          this.forms.push({ sections: [], logic: { version: 1, calculations: [], conditions: [], valueAssignments: [] } });
        }
      }

      const form = this.forms[this.currentFormIndex];
      if (!form || typeof form !== "object") {
        if (this.$set) {
          this.$set(this.forms, this.currentFormIndex, {
            sections: [],
            logic: { version: 1, calculations: [], conditions: [], valueAssignments: [] }
          });
        } else {
          this.forms[this.currentFormIndex] = {
            sections: [],
            logic: { version: 1, calculations: [], conditions: [], valueAssignments: [] }
          };
        }
      }

      if (!Array.isArray(this.forms[this.currentFormIndex].sections)) {
        if (this.$set) this.$set(this.forms[this.currentFormIndex], "sections", []);
        else this.forms[this.currentFormIndex].sections = [];
      }

      if (!this.forms[this.currentFormIndex].logic || typeof this.forms[this.currentFormIndex].logic !== "object") {
        if (this.$set) {
          this.$set(this.forms[this.currentFormIndex], "logic", {
            version: 1,
            calculations: [],
            conditions: [],
            valueAssignments: []
          });
        } else {
          this.forms[this.currentFormIndex].logic = {
            version: 1,
            calculations: [],
            conditions: [],
            valueAssignments: []
          };
        }
      }

      if (!Array.isArray(this.forms[this.currentFormIndex].logic.calculations)) {
        if (this.$set) this.$set(this.forms[this.currentFormIndex].logic, "calculations", []);
        else this.forms[this.currentFormIndex].logic.calculations = [];
      }

      if (!Array.isArray(this.forms[this.currentFormIndex].logic.conditions)) {
        if (this.$set) this.$set(this.forms[this.currentFormIndex].logic, "conditions", []);
        else this.forms[this.currentFormIndex].logic.conditions = [];
      }

      if (!Array.isArray(this.forms[this.currentFormIndex].logic.valueAssignments)) {
        if (this.$set) this.$set(this.forms[this.currentFormIndex].logic, "valueAssignments", []);
        else this.forms[this.currentFormIndex].logic.valueAssignments = [];
      }

      if (!this.forms[this.currentFormIndex].logic.version) {
        if (this.$set) this.$set(this.forms[this.currentFormIndex].logic, "version", 1);
        else this.forms[this.currentFormIndex].logic.version = 1;
      }

      return this.forms[this.currentFormIndex];
    },

    buildScratchStudyPayload() {
      const details = this.studyDetails || {};
      const studyNode = JSON.parse(JSON.stringify(details.study || {}));
      const meta = details.study_metadata || {};

      const normalizedForms = JSON.parse(JSON.stringify(this.forms || [])).map(form => ({
        sections: Array.isArray(form.sections)
          ? form.sections.map(sec => ({
              ...sec,
              fields: Array.isArray(sec.fields)
                ? sec.fields.map(field => ({
                    ...field,
                    constraints: field.constraints || {}
                  }))
                : []
            }))
          : [],
        logic: {
          version: form.logic?.version || 1,
          calculations: Array.isArray(form.logic?.calculations) ? form.logic.calculations : [],
          conditions: Array.isArray(form.logic?.conditions) ? form.logic.conditions : [],
          valueAssignments: Array.isArray(form.logic?.valueAssignments) ? form.logic.valueAssignments : []
        }
      }));

      const selectedModels = (this.currentForm.sections || []).map(sec => ({
        _id: sec._id || this.uuidForLogic(),
        title: sec.title,
        fields: JSON.parse(JSON.stringify(sec.fields || [])).map(field => ({
          ...field,
          _id: field._id || this.uuidForLogic(),
          constraints: field.constraints || {}
        }))
      }));

      const studyName =
        studyNode.title ||
        studyNode.study_name ||
        studyNode.name ||
        meta.study_name ||
        "Untitled Study";

      const studyDescription =
        studyNode.description ||
        studyNode.study_description ||
        meta.study_description ||
        "";

      const normalizedStudy = {
        ...studyNode,
        title: studyName,
        name: studyName,
        study_name: studyName,
        description: studyDescription,
        study_description: studyDescription
      };

      return {
        study_metadata: {
          created_by: meta.created_by || this.currentUserId,
          study_name: studyName,
          study_description: studyDescription
        },
        study_content: {
          study_data: {
            study: normalizedStudy,
            groups: JSON.parse(JSON.stringify(details.groups || this.groups || [])),
            visits: JSON.parse(JSON.stringify(details.visits || this.visits || [])),
            subjectCount: Number(details.subjectCount ?? 0),
            assignmentMethod: details.assignmentMethod || "Random",
            subjects: JSON.parse(JSON.stringify(details.subjects || [])),
            assignments: JSON.parse(JSON.stringify(this.assignments || details.assignments || [])),
            skipSubjectCreationNow: !!details.skipSubjectCreationNow,

            // old structure kept for compatibility
            selectedModels,

            // new canonical full builder structure
            forms: normalizedForms
          }
        }
      };
    },

    async persistScratchToBackend() {
      this.ensurePersistentIdsForLogic();
      const token = this.$store.state.token;
      if (!token) {
        this.$router.push("/login");
        return { ok: false, message: "Please log in again." };
      }

      this.ensureCurrentFormExists();

      const selectedFormsForStore = JSON.parse(JSON.stringify(this.forms || [])).map(form => ({
        sections: (form.sections || []).map(sec => ({
          ...sec,
          fields: (sec.fields || []).map(field => ({
            ...field,
            constraints: field.constraints || {}
          }))
        })),
        logic: {
          version: form.logic?.version || 1,
          calculations: Array.isArray(form.logic?.calculations) ? form.logic.calculations : [],
          conditions: Array.isArray(form.logic?.conditions) ? form.logic.conditions : [],
          valueAssignments: Array.isArray(form.logic?.valueAssignments) ? form.logic.valueAssignments : []
        }
      }));

      this.$store.commit("setStudyDetails", {
        ...this.studyDetails,
        assignments: JSON.parse(JSON.stringify(this.assignments || [])),
        forms: selectedFormsForStore
      });

      const payload = this.buildScratchStudyPayload();
      const existingId = this.currentStudyId;

      try {
        if (existingId) {
          await axios.put(
            `/forms/studies/${existingId}`,
            payload,
            {
              headers: this.authHeader,
                // audit_label: user clicked "Save & Exit" from ScratchForm (builder) while a study already exists (edit/update)
              params: { audit_label: "Existing Study Updated" }
            }
          );

          this.$store.commit("setStudyDetails", {
            ...this.studyDetails,
            study_metadata: {
              ...(this.studyDetails.study_metadata || {}),
              id: Number(existingId),
              study_name: payload.study_metadata.study_name,
              study_description: payload.study_metadata.study_description
            },
            study: {
              ...(this.studyDetails.study || {}),
              ...payload.study_content.study_data.study,
              id: Number(existingId)
            },
            assignments: payload.study_content.study_data.assignments,
            forms: selectedFormsForStore
          });

          return { ok: true, id: Number(existingId), mode: "update" };
        }

        const lastCompletedStep =
          this.$route?.query?.step != null ? String(this.$route.query.step) : "6";

        const resp = await axios.post(
          `/forms/studies/?status=DRAFT&last_completed_step=${encodeURIComponent(lastCompletedStep)}`,
          payload,
          {
            headers: this.authHeader,
            // audit_label: user clicked "Save & Exit" from ScratchForm (builder) and backend creates a DRAFT study
            params: { audit_label: "Save & Exit - Create New Study Draft" }
          }
        );

        const meta = resp.data?.metadata || resp.data?.study_metadata || {};
        const createdId = meta.id ?? resp.data?.id;

        if (createdId == null) {
          return { ok: false, message: "Draft created but ID was not returned." };
        }

        this.$store.commit("setStudyDetails", {
          ...this.studyDetails,
          study_metadata: {
            ...(this.studyDetails.study_metadata || {}),
            id: Number(createdId),
            study_name: meta.study_name || payload.study_metadata.study_name,
            study_description: meta.study_description || payload.study_metadata.study_description,
            status: String(meta.status || "DRAFT").toUpperCase()
          },
          study: {
            ...(payload.study_content.study_data.study || {}),
            id: Number(createdId)
          },
          groups: payload.study_content.study_data.groups || [],
          visits: payload.study_content.study_data.visits || [],
          subjectCount: payload.study_content.study_data.subjectCount || 0,
          assignmentMethod: payload.study_content.study_data.assignmentMethod || "Random",
          subjects: payload.study_content.study_data.subjects || [],
          assignments: payload.study_content.study_data.assignments || [],
          skipSubjectCreationNow: !!payload.study_content.study_data.skipSubjectCreationNow,
          forms: selectedFormsForStore
        });

        return { ok: true, id: Number(createdId), mode: "create" };
      } catch (e) {
        const msg =
          e?.response?.data?.detail ||
          e?.response?.data?.message ||
          e?.message ||
          "Failed to save study from Scratch.";
        console.error("[ScratchForm] Save & Exit failed:", e);
        return { ok: false, message: String(msg) };
      }
    },

    // Hook your "Save & Exit" button/dialog to this method
    async onUnsavedSaveAndExit() {
      if (this.unsavedBusy) return;
      this.unsavedBusy = true;

      try {
        const res = await this.persistScratchToBackend();
        if (!res.ok) {
          this.openGenericDialog(res.message || "Failed to save.");
          return;
        }

        // Saved successfully -> clear dirty + close dialog
        this.$store.commit("setStudyCreationDirty", false);
        this.showUnsavedDialog = false;
        this.unsavedPendingAction = null;

        this.scratchAllowInternalNav = true;
        this.$router.push("/dashboard").finally(() => {
          this.scratchAllowInternalNav = false;
        });
      } finally {
        this.unsavedBusy = false;
      }
    },

    /* ---------- Stable keys ---------- */
    getSectionUid(sectionObj) {
      if (!sectionObj || typeof sectionObj !== "object") return String(Math.random());
      if (!this.sectionUidMap.has(sectionObj)) {
        this.sectionUidMap.set(sectionObj, `sec_${this.uidCounter++}`);
      }
      return this.sectionUidMap.get(sectionObj);
    },

    getFieldUid(fieldObj) {
      if (!fieldObj || typeof fieldObj !== "object") return String(Math.random());
      if (!this.fieldUidMap.has(fieldObj)) {
        this.fieldUidMap.set(fieldObj, `fld_${this.uidCounter++}`);
      }
      return this.fieldUidMap.get(fieldObj);
    },

    clampSectionIndex(i) {
      this.ensureCurrentFormExists();
      const n = this.currentForm.sections.length;
      if (!n) return 0;
      const x = Number.isInteger(i) ? i : 0;
      return Math.max(0, Math.min(x, n - 1));
    },

    getTargetSectionForModelDialog() {
      this.ensureCurrentFormExists();
      const sections = this.currentForm.sections || [];
      if (!sections.length) return null;
      const idx = this.clampSectionIndex(this.modelTargetSectionIndex);
      return sections[idx] || null;
    },

    isPropAlreadyInTargetSection(prop) {
      if (!this.modelAddToExisting) return false;
      const sec = this.getTargetSectionForModelDialog();
      if (!sec) return false;
      const name = String(prop?.name || "");
      if (!name) return false;
      return Array.isArray(sec.fields) && sec.fields.some(f => String(f?.name || "") === name);
    },

    syncSelectedPropsForExistingSection() {
      if (!this.showModelDialog) return;
      if (!this.modelAddToExisting) return;
      if (!this.currentModel || !Array.isArray(this.currentModel.fields)) return;

      const sec = this.getTargetSectionForModelDialog();
      if (!sec || !Array.isArray(sec.fields)) return;

      const existing = new Set(sec.fields.map(f => String(f?.name || "")));
      this.currentModel.fields.forEach((p, i) => {
        const nm = String(p?.name || "");
        if (nm && existing.has(nm)) {
          this.$set(this.selectedProps, i, true);
        }
      });
    },

    onDragEnd() {
      this.dragState = {
        kind: null,
        fromSection: null,
        fromField: null,
        overSection: null,
        overField: null,
        position: null
      };
    },

    getFieldDropClass(si, fi) {
      if (this.dragState.kind !== "field") return "";
      if (this.dragState.overSection !== si) return "";
      if (this.dragState.overField !== fi) return "";
      return this.dragState.position === "after" ? "drop-after" : "drop-before";
    },

    onFieldDragStart(si, fi, evt) {
      if (this.showMatrix) return;
      this.dragState.kind = "field";
      this.dragState.fromSection = si;
      this.dragState.fromField = fi;

      try {
        evt.dataTransfer.effectAllowed = "move";
        evt.dataTransfer.setData("text/plain", "field");
      } catch (err) { console.error(err); }
    },

    onFieldDragOver(si, fi, evt) {
      if (this.dragState.kind !== "field") return;
      if (this.dragState.fromSection !== si) return;

      const el = evt.currentTarget;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const after = (evt.clientY - rect.top) > rect.height / 2;

      this.dragState.overSection = si;
      this.dragState.overField = fi;
      this.dragState.position = after ? "after" : "before";
    },

    onFieldDrop(si, fi) {
      if (this.dragState.kind !== "field") return;
      this.ensureCurrentFormExists();

      const sourceSectionIndex = this.dragState.fromSection;
      const fromF = this.dragState.fromField;
      const toS = si;

      if (sourceSectionIndex !== toS) {
        this.onDragEnd();
        return;
      }

      const sections = this.forms[this.currentFormIndex].sections || [];
      const sec = sections[sourceSectionIndex];
      if (!sec) return this.onDragEnd();

      const fields = sec.fields || [];
      if (!Number.isInteger(fromF) || fromF < 0 || fromF >= fields.length) {
        return this.onDragEnd();
      }

      let insertAt = fi + (this.dragState.position === "after" ? 1 : 0);

      const moved = fields.splice(fromF, 1)[0];
      if (insertAt > fromF) insertAt -= 1;

      insertAt = Math.max(0, Math.min(insertAt, fields.length));
      fields.splice(insertAt, 0, moved);

      this.activeSection = toS;
      this.$nextTick(() => this.focusSection(this.activeSection));
      this.onDragEnd();
    },

    onFieldDropEndOver(si) {
      if (this.dragState.kind !== "field") return;
      if (this.dragState.fromSection !== si) return;

      this.dragState.overSection = si;
      this.dragState.overField = null;
      this.dragState.position = "end";
    },

    onFieldDropEnd(si) {
      if (this.dragState.kind !== "field") return;
      this.ensureCurrentFormExists();

      const sourceSectionIndex = this.dragState.fromSection;
      const fromF = this.dragState.fromField;

      if (sourceSectionIndex !== si) {
        this.onDragEnd();
        return;
      }

      const sections = this.forms[this.currentFormIndex].sections || [];
      const sec = sections[sourceSectionIndex];
      if (!sec) return this.onDragEnd();

      const fields = sec.fields || [];
      if (!Number.isInteger(fromF) || fromF < 0 || fromF >= fields.length) {
        return this.onDragEnd();
      }

      const moved = fields.splice(fromF, 1)[0];
      let insertAt = fields.length;
      if (insertAt > fromF) insertAt -= 1;

      insertAt = Math.max(0, Math.min(insertAt, fields.length));
      fields.splice(insertAt, 0, moved);

      this.activeSection = si;
      this.$nextTick(() => this.focusSection(this.activeSection));
      this.onDragEnd();
    },

    onFieldContainerOver(si) {
      if (this.dragState.kind !== "field") return;
      if (this.dragState.fromSection !== si) return;

      this.dragState.overSection = si;
      this.dragState.overField = null;
      this.dragState.position = "end";
    },

    onFieldContainerDrop(si) {
      if (this.dragState.kind !== "field") return;
      if (this.dragState.fromSection !== si) {
        this.onDragEnd();
        return;
      }
      this.onFieldDropEnd(si);
    },

    resetObiState() {
      this.obiQuery = "";
      this.obiResults = [];
      this.obiError = "";
      this.selectedTermIds = new Set();
      this.requestedLimit = 50;
      clearTimeout(this.obiDebounceTimer);
      this.obiDebounceTimer = null;
    },

    onObiInput() {
      this.requestedLimit = 50;
      clearTimeout(this.obiDebounceTimer);
      this.obiDebounceTimer = setTimeout(() => {
        this.fetchObiTerms();
      }, 250);
    },

    async fetchObiTerms() {
      const q = (this.obiQuery || "").trim();
      if (q.length < 2) {
        this.obiResults = [];
        this.obiError = "";
        return;
      }

      this.obiLoading = true;
      this.obiError = "";
      try {
        const { data } = await axios.get("/ontology/obi/search", {
          params: { query: q, limit: this.requestedLimit }
        });

        const arr = Array.isArray(data?.results) ? data.results : [];
        const seen = new Set();
        const out = [];

        arr.forEach(term => {
          const id = String(term.id || "").trim();
          if (!id || seen.has(id)) return;
          seen.add(id);
          out.push({
            id,
            label: String(term.name || "").trim() || id,
            definition: String(term.def || "").trim(),
            synonyms: Array.isArray(term.synonyms) ? term.synonyms : []
          });
        });

        this.obiResults = out;
      } catch (e) {
        this.obiError = e?.response?.data?.detail || e.message || "Search failed.";
        this.obiResults = [];
      } finally {
        this.obiLoading = false;
      }
    },

    showMore() {
      this.requestedLimit += this.limitStep;
      this.fetchObiTerms();
    },

    obiHighlight(text) {
      const q = (this.obiQuery || "").trim();
      const src = String(text || "");
      if (!q) return this.escapeHtml(src);
      try {
        const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig");
        return this.escapeHtml(src).replace(re, "<mark>$1</mark>");
      } catch {
        return this.escapeHtml(src);
      }
    },

    formatSynonyms(list) {
      return (list || []).slice(0, 6).join(", ");
    },

    onToggleObiTerm(termId, evt) {
      const next = new Set(this.selectedTermIds);
      if (evt?.target?.checked) next.add(termId);
      else next.delete(termId);
      this.selectedTermIds = new Set(next);
    },

    toggleByBody(termId) {
      const next = new Set(this.selectedTermIds);
      if (next.has(termId)) next.delete(termId);
      else next.add(termId);
      this.selectedTermIds = next;
    },

    addSelectedObiTerms() {
      this.ensureCurrentFormExists();
      if (!this.currentForm.sections.length) this.addNewSection();

      const si = this.activeSection;
      const sec = this.currentForm.sections[si];
      if (sec.collapsed) this.toggleSection(si);

      const selected = this.obiResults.filter(t => this.selectedTermIds.has(t.id));
      if (!selected.length) return;

      const now = Date.now();
      selected.forEach((t, idx) => {
        const safe = this.slugify(t.label || t.id || "obi_term");
        sec.fields.push({
          name: `${safe}_${now}_${idx}`,
          label: t.label || t.id,
          type: "text",
          value: "",
          placeholder: "",
          constraints: {
            helpText: `${t.id}${t.definition ? " — " + t.definition : ""}`
          }
        });
      });

      this.selectedTermIds = new Set();
      this.openGenericDialog(`Added ${selected.length} OBI field(s) to "${sec.title}".`);
    },

    slugify(s) {
      return String(s || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
    },

    onShaclTakeover(section) {
      this.ensureCurrentFormExists();
      const insertAt = Math.min(this.activeSection + 1, this.currentForm.sections.length);
      const sec = {
        _id: this.uuidForLogic(),
        title: section.title,
        fields: (section.fields || []).map(f => ({
          ...JSON.parse(JSON.stringify(f)),
          _id: f._id || this.uuidForLogic(),
          constraints: JSON.parse(JSON.stringify(f.constraints || {}))
        })),
        collapsed: false,
        source: "shacl"
      };
      this.forms[this.currentFormIndex].sections.splice(insertAt, 0, sec);
      this.activeSection = insertAt;
      this.$nextTick(() => this.focusSection(insertAt));
      this.adjustAssignments();
    },

    goBack() {
      if (this.showLogic) {
        this.showLogic = false;
        return;
      }

      if (this.showValueAssignments) {
        this.showValueAssignments = false;
        return;
      }

      // If ProtocolMatrix is open, just go back to study creation step 5
      if (this.showMatrix) {
        const q = { ...this.$route.query, step: "5" };
        this.scratchAllowInternalNav = true;
        this.$router
          .push({
            name: "CreateStudy",
            params: this.$route.params?.id ? { id: this.$route.params.id } : {},
            query: q
          })
          .finally(() => {
            this.scratchAllowInternalNav = false;
          });
        return;
      }

      // IMPORTANT FIX:
      // Back from ScratchForm should always return to Study Creation step 1,
      // both for new study creation and edit mode.
      const q = { ...this.$route.query, step: "1" };

      this.scratchAllowInternalNav = true;
      this.$router
        .push({
          name: "CreateStudy",
          params: this.$route.params?.id ? { id: this.$route.params.id } : {},
          query: q
        })
        .finally(() => {
          this.scratchAllowInternalNav = false;
        });
    },

    prettyModelTitle(s) {
      return this.$formatLabel ? this.$formatLabel(s) : String(s || "");
    },

    modelIcon(title) {
      const key = String(title || "").toLowerCase().replace(/[^a-z0-9]/g, "");
      return this.icons[key] || "fas fa-book";
    },

    fieldIcon(label) {
      const key = String(label || "").toLowerCase().replace(/[^a-z0-9]/g, "");
      return this.icons[key] || "fas fa-dot-circle";
    },

    highlight(text) {
      const q = (this.searchQuery || "").trim();
      if (!q) return this.escapeHtml(text || "");
      try {
        const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")})`, "ig");
        return this.escapeHtml(text || "").replace(re, "<mark>$1</mark>");
      } catch {
        return this.escapeHtml(text || "");
      }
    },

    titleMatches(title) {
      const q = (this.searchQuery || "").trim().toLowerCase();
      return q && String(title || "").toLowerCase().includes(q);
    },

    previewMatches(fields) {
      return (fields || []).slice(0, 5);
    },

    escapeHtml(s) {
      return String(s || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    },

    onSectionClick(i) {
      this.ensureCurrentFormExists();

      const section = this.currentForm.sections[i];
      if (!section) return;

      this.activeSection = i;

      // If user clicks a collapsed section, expand it.
      // Do not call focusSection here, because the user already clicked
      // the section in its current viewport position.
      if (section.collapsed) {
        section.collapsed = false;
      }
    },

    openConfirmDialog(msg, cb) {
      this.confirmDialogMessage = msg;
      this.confirmCallback = cb;
      this.showConfirmDialog = true;
    },

    confirmDialogYes() {
      this.showConfirmDialog = false;
      if (this.confirmCallback) this.confirmCallback();
    },

    closeConfirmDialog() {
      this.showConfirmDialog = false;
    },

    openGenericDialog(msg, cb) {
      this.genericDialogMessage = msg;
      this.genericCallback = cb;
      this.showGenericDialog = true;
    },

    closeGenericDialog() {
      this.showGenericDialog = false;
      if (this.genericCallback) this.genericCallback();
    },

    openInputDialog(msg, def, cb) {
      this.inputDialogMessage = msg;
      this.inputDialogValue = def;
      this.inputDialogCallback = cb;
      this.showInputDialog = true;
    },

    confirmInputDialog() {
      this.showInputDialog = false;
      if (this.inputDialogCallback) this.inputDialogCallback(this.inputDialogValue);
    },

    cancelInputDialog() {
      this.showInputDialog = false;
    },

    adjustAssignments() {
      const m = this.selectedModels.length;
      const v = this.visits.length;
      const g = this.groups.length;

      if (m === 0 || v === 0 || g === 0) {
        this.assignments = [];
        return;
      }

      // IMPORTANT FIX:
      // Prefer current local assignments first, then fallback to store assignments.
      const old =
        Array.isArray(this.assignments) && this.assignments.length
          ? this.assignments
          : (Array.isArray(this.studyDetails.assignments) ? this.studyDetails.assignments : []);

      const fresh = [];
      for (let mi = 0; mi < m; mi++) {
        fresh[mi] = [];
        for (let vi = 0; vi < v; vi++) {
          fresh[mi][vi] = [];
          for (let gi = 0; gi < g; gi++) {
            const ov = old[mi]?.[vi]?.[gi];
            fresh[mi][vi][gi] = typeof ov === "boolean" ? ov : false;
          }
        }
      }

      this.assignments = fresh;

      this.$store.commit("setStudyDetails", {
        ...this.studyDetails,
        assignments: JSON.parse(JSON.stringify(this.assignments))
      });
    },

    handleProtocolClick() {
      this.showLogic = false;
      this.showValueAssignments = false;
      this.showMatrix = true;
    },
    editTemplate() {
      this.showMatrix = false;
      this.refreshBuilderStickyObserver();
    },
    closeLogicAndCalculations() {
      this.showMatrix = false;
      this.showLogic = false;
      this.refreshBuilderStickyObserver();
    },

    closeValueAssignments() {
      this.showMatrix = false;
      this.showLogic = false;
      this.showValueAssignments = false;
      this.refreshBuilderStickyObserver();
    },

    onAssignmentUpdated({ mIdx, vIdx, gIdx, checked }) {
      this.assignments[mIdx][vIdx][gIdx] = checked;
      this.$store.commit("setStudyDetails", { ...this.studyDetails, assignments: this.assignments });
      if (!this.hydratingScratch) this.$store.commit("setStudyCreationDirty", true);
    },

    focusSection(i) {
      this.$nextTick(() => {
        const ref = this.$refs[`section-${i}`];
        const el = Array.isArray(ref) ? ref[0] : ref;
        if (el?.scrollIntoView) el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    },

    openModelDialog(model) {
      this.ensureCurrentFormExists();

      const full = this.dataModels.find(d => d.title === model.title) || model;
      this.currentModel = full;
      this.selectedProps = full.fields.map(() => false);

      this.modelAddToExisting = false;
      this.modelTargetSectionIndex = this.clampSectionIndex(this.activeSection);

      this.showModelDialog = true;
    },

    takeoverModel() {
      this.ensureCurrentFormExists();

      const chosen = this.currentModel.fields
        .filter((_, i) => this.selectedProps[i])
        .map(f => ({ ...f, description: f.description || "", constraints: f.constraints || {} }));

      if (this.modelAddToExisting && this.currentForm.sections.length) {
        const sections = this.forms[this.currentFormIndex].sections;
        const idx = this.clampSectionIndex(this.modelTargetSectionIndex);
        const targetSec = sections[idx];
        if (!targetSec) {
          this.showModelDialog = false;
          return;
        }

        if (targetSec.collapsed) targetSec.collapsed = false;

        const existingNames = new Set((targetSec.fields || []).map(ff => String(ff?.name || "")));
        let added = 0;

        chosen.forEach(f => {
          const nm = String(f?.name || "");
          if (nm && existingNames.has(nm)) return;
          existingNames.add(nm);
          targetSec.fields.push({
            ...JSON.parse(JSON.stringify(f)),
            _id: f._id || this.uuidForLogic(),
            constraints: JSON.parse(JSON.stringify(f.constraints || {}))
          });
          added += 1;
        });

        this.activeSection = idx;
        this.$nextTick(() => this.focusSection(idx));

        if (added === 0) {
          this.openGenericDialog(`All selected field(s) already exist in "${targetSec.title}".`);
        }

        this.showModelDialog = false;
        return;
      }

      const insertAt = Math.min(this.activeSection + 1, this.currentForm.sections.length);
      const sec = {
        _id: this.uuidForLogic(),
        title: this.currentModel.title,
        fields: chosen.map(f => ({
          ...JSON.parse(JSON.stringify(f)),
          _id: f._id || this.uuidForLogic(),
          constraints: JSON.parse(JSON.stringify(f.constraints || {}))
        })),
        collapsed: false,
        source: "template"
      };

      this.forms[this.currentFormIndex].sections.splice(insertAt, 0, sec);
      this.activeSection = insertAt;
      this.$nextTick(() => this.focusSection(insertAt));
      this.adjustAssignments();
      this.showModelDialog = false;
    },

    addNewSection() {
      this.ensureCurrentFormExists();

      const sections = this.forms[this.currentFormIndex].sections || [];

      const insertAt =
        sections.length === 0
          ? 0
          : Math.max(0, Math.min(this.activeSection + 1, sections.length));

      const sec = {
        _id: this.uuidForLogic(),
        title: `Section ${sections.length + 1}`,
        fields: [],
        collapsed: false,
        source: "manual"
      };

      sections.splice(insertAt, 0, sec);
      this.activeSection = insertAt;
      this.adjustAssignments();
      this.focusSection(insertAt);
    },

    addNewSectionBelow(i) {
      this.ensureCurrentFormExists();

      const current = this.currentForm.sections[i];
      if (!current) return;

      const sec = {
        _id: this.uuidForLogic(),
        title: `${current.title} (Copy)`,
        fields: (current.fields || []).map(field => ({
          ...field,
          _id: this.uuidForLogic(),
          name: `${field.name}_${Date.now()}`,
          constraints: field.constraints || {}
        })),
        collapsed: false,
        source: current.source
      };

      const idx = i + 1;
      this.forms[this.currentFormIndex].sections.splice(idx, 0, sec);
      this.activeSection = idx;
      this.adjustAssignments();
      this.focusSection(idx);
    },

    confirmDeleteSection(i) {
      this.openConfirmDialog("Delete this section?", () => {
        this.ensureCurrentFormExists();

        const sectionIndex = Number(i);
        const sections = this.currentForm.sections || [];

        if (
          !Number.isInteger(sectionIndex) ||
          sectionIndex < 0 ||
          sectionIndex >= sections.length
        ) {
          return;
        }

        // Keep assignment rows aligned with section rows.
        // ProtocolMatrix uses selectedModels index (mIdx) to read assignments[mIdx],
        // so when a section is deleted, its assignment row must be deleted too.
        this.removeValueAssignmentReferencesForFields(
          (sections[sectionIndex]?.fields || []).map((field, fieldIndex) => ({
            field,
            sectionIndex,
            fieldIndex,
          }))
        );
        sections.splice(sectionIndex, 1);

        if (Array.isArray(this.assignments) && sectionIndex < this.assignments.length) {
          this.assignments.splice(sectionIndex, 1);
        }

        this.activeSection = sections.length
          ? Math.max(0, Math.min(sectionIndex, sections.length - 1))
          : 0;

        this.adjustAssignments();

        if (!this.hydratingScratch) {
          this.$store.commit("setStudyCreationDirty", true);
        }
      });
    },
    confirmDeleteField(si, fi) {
      this.ensureCurrentFormExists();

      const field = this.currentForm.sections?.[si]?.fields?.[fi];
      if (!field) return;

      this.openConfirmDialog("Delete this field?", () => {
        this.ensureCurrentFormExists();
        this.removeField(si, fi);
      });
    },

    confirmClearForm() {
      this.openConfirmDialog("Do you want to clear all sections?", () => {
        this.ensureCurrentFormExists();
        this.forms[this.currentFormIndex].sections = [];
        this.forms[this.currentFormIndex].logic.valueAssignments = [];
        this.activeSection = 0;
        this.adjustAssignments();
      });
    },

    toggleSection(i) {
      this.ensureCurrentFormExists();
      const section = this.forms[this.currentFormIndex].sections[i];
      if (!section) return;
      section.collapsed = !section.collapsed;
    },

    setActiveSection(i) {
      this.ensureCurrentFormExists();
      this.activeSection = i;
    },

    addFieldToActiveSection(field) {
      // FIX: guard before mutation
      this.ensureCurrentFormExists();
      if (field.type === "table") {
        this.openTableConfigurator(field);
        return;
      }
      if (!this.currentForm.sections.length) this.addNewSection();

      const sec = this.currentForm.sections[this.activeSection];
      if (!sec) return;
      if (sec.collapsed) this.toggleSection(this.activeSection);

      const base = {
        _id: this.uuidForLogic(),
        name: `${(field.name || field.type)}_${Date.now()}`,
        label: field.label,
        type: field.type,
        options: (field.type === "select" || field.type === "radio")
          ? (Array.isArray(field.options) && field.options.length ? [...field.options] : ["Option 1"])
          : (field.options || []),
        placeholder: field.description || field.placeholder || "",
        value: field.type === "checkbox" ? false : "",
        constraints: JSON.parse(JSON.stringify(field.constraints || {}))
      };

      if (base.type === "slider") {
        base.value = null;
        base.constraints = {
          ...(base.constraints || {}),
          mode: base.constraints?.mode || "slider",
          percent: !!base.constraints?.percent,
          min: Number.isFinite(base.constraints?.min) ? base.constraints.min : 1,
          max: Number.isFinite(base.constraints?.max) ? base.constraints.max : 100,
          step: Number.isFinite(base.constraints?.step) ? base.constraints.step : 1,
          marks: Array.isArray(base.constraints?.marks) ? base.constraints.marks : (base.constraints?.marks || [])
        };
      }

      if (base.type === "date") {
        base.constraints = { ...base.constraints, dateFormat: base.constraints?.dateFormat || "dd.MM.yyyy" };
        base.placeholder = base.placeholder || base.constraints.dateFormat;
      }

      if (base.type === "file") {
        base.value = null;
        base.icon = base.icon || icons.paperclip;
        const provided = base.constraints || {};
        const fallbackMod = (String(base.label || "").trim()) || base.name;

        base.constraints = {
          helpText: provided.helpText || "",
          required: !!provided.required,
          readonly: !!provided.readonly,
          allowedFormats: Array.isArray(provided.allowedFormats)
            ? provided.allowedFormats.map(String).map(s => s.trim()).filter(Boolean)
            : [],
          maxSizeMB: (Number.isFinite(provided.maxSizeMB) && Number(provided.maxSizeMB) > 0)
            ? Number(provided.maxSizeMB)
            : undefined,
          storagePreference: (provided.storagePreference === "url") ? "url" : "local",
          modalities: (Array.isArray(provided.modalities) && provided.modalities.length)
            ? provided.modalities
            : [fallbackMod],
          allowMultipleFiles: (provided.allowMultipleFiles === undefined) ? true : !!provided.allowMultipleFiles
        };
      }

      sec.fields.push(base);
      this.revealAddedField(
        this.activeSection,
        sec.fields[sec.fields.length - 1]
      );
    },

    editSection(i, v) {
      this.ensureCurrentFormExists();
      if (v) this.currentForm.sections[i].title = v;
    },

    editField(si, fi, v) {
      this.ensureCurrentFormExists();
      if (!v) return;

      const f = this.currentForm.sections[si]?.fields?.[fi];
      if (!f) return;

      const prevLabel = f.label;
      f.label = v;

      if (f.type === "file") {
        const mods = Array.isArray(f.constraints?.modalities) ? f.constraints.modalities : [];
        const prevTrim = String(prevLabel || "").trim();

        if (!mods.length || (mods.length === 1 && String(mods[0] || "").trim() === prevTrim)) {
          const next = (String(v || "").trim()) || f.name;
          f.constraints = { ...(f.constraints || {}), modalities: [next] };
        }
      }
    },

    enforceNumberDigitLimits(sectionIndex, fieldIndex, evt, onBlur = false) {
      this.ensureCurrentFormExists();

      const field = this.currentForm.sections[sectionIndex]?.fields?.[fieldIndex];
      if (!field) return;

      const c = field.constraints || {};
      if (!c.integerOnly) return;

      const el = evt?.target || null;
      let raw = el ? String(el.value ?? "") : String(field.value ?? "");
      const digits = raw.replace(/\D+/g, "");

      if (Number.isFinite(c.maxDigits) && c.maxDigits > 0 && digits.length > c.maxDigits) {
        const trimmed = digits.slice(0, c.maxDigits);
        field.value = trimmed === "" ? "" : Number(trimmed);
        if (el) el.value = field.value;
        return;
      }

      if (onBlur && Number.isFinite(c.minDigits) && c.minDigits > 0) {
        if (digits.length > 0 && digits.length < c.minDigits) {
          // no-op, validation elsewhere
        }
      }
    },

    addSimilarField(si, fi) {
      this.ensureCurrentFormExists();

      const f = this.currentForm.sections[si]?.fields?.[fi];
      if (!f) return;

      const baseName = String(f.name || "field").replace(/_\d+$/, "");
      let candidateName = `${baseName}_${Date.now()}`;

      const existingNames = new Set(
        (this.currentForm.sections[si]?.fields || []).map(field => String(field?.name || ""))
      );

      let uniqueName = candidateName;
      let counter = 2;
      while (existingNames.has(uniqueName)) {
        uniqueName = `${candidateName}_${counter}`;
        counter += 1;
      }

      const originalLabel = String(f.label || "Field").trim() || "Field";
      let candidateLabel = `${originalLabel}_copy`;

      const existingLabels = new Set(
        (this.currentForm.sections[si]?.fields || []).map(field => String(field?.label || "").trim())
      );

      let uniqueLabel = candidateLabel;
      let labelCounter = 2;
      while (existingLabels.has(uniqueLabel)) {
        uniqueLabel = `${candidateLabel}_${labelCounter}`;
        labelCounter += 1;
      }

      const clone = {
        _id: this.uuidForLogic(),
        name: uniqueName,
        label: uniqueLabel,
        type: f.type,
        placeholder: f.placeholder || "",
        description: f.description || "",
        rows: f.type === "textarea" ? (f.rows || 4) : undefined,
        options: Array.isArray(f.options) ? JSON.parse(JSON.stringify(f.options)) : [],
        value:
          f.type === "checkbox" ? false :
          f.type === "slider" ? null :
          f.type === "file" ? null :
          f.type === "radio" && f.constraints?.allowMultiple ? [] :
          "",
        constraints: this.getBasicConstraintsForCopiedField(f),
      };

      if (clone.type !== "textarea") {
        delete clone.rows;
      }

      this.currentForm.sections[si].fields.splice(fi + 1, 0, clone);

      this.openGenericDialog("Basic settings are copied. Advanced settings are not copied.");
    },

    openTableCopyDialog(si, fi) {
      this.ensureCurrentFormExists();

      const field = this.currentForm.sections?.[si]?.fields?.[fi];
      if (!field || field.type !== "table") return;

      this.pendingTableCopyIndices = { sectionIndex: si, fieldIndex: fi };
      this.showTableCopyDialog = true;
    },

    closeTableCopyDialog() {
      this.showTableCopyDialog = false;
      this.pendingTableCopyIndices = null;
    },

    confirmBasicTableCopy() {
      const indices = this.pendingTableCopyIndices;
      this.closeTableCopyDialog();
      if (!indices) return;
      this.addSimilarField(indices.sectionIndex, indices.fieldIndex);
    },

    confirmCompleteTableCopy() {
      const indices = this.pendingTableCopyIndices;
      this.closeTableCopyDialog();
      if (!indices) return;

      const { sectionIndex: si, fieldIndex: fi } = indices;
      const source = this.currentForm.sections?.[si]?.fields?.[fi];
      if (!source || source.type !== "table") return;

      const baseName = String(source.name || "table").replace(/_\d+$/, "");
      const nameSeed = `${baseName}_${Date.now()}`;
      const existingNames = new Set(
        (this.currentForm.sections[si]?.fields || []).map((field) => String(field?.name || ""))
      );
      let uniqueName = nameSeed;
      let nameCounter = 2;
      while (existingNames.has(uniqueName)) {
        uniqueName = `${nameSeed}_${nameCounter}`;
        nameCounter += 1;
      }

      const sourceLabel = String(source.label || "Table").trim() || "Table";
      const labelSeed = `${sourceLabel}_copy`;
      const existingLabels = new Set(
        (this.currentForm.sections[si]?.fields || []).map((field) => String(field?.label || "").trim())
      );
      let uniqueLabel = labelSeed;
      let labelCounter = 2;
      while (existingLabels.has(uniqueLabel)) {
        uniqueLabel = `${labelSeed}_${labelCounter}`;
        labelCounter += 1;
      }

      const clone = copyCompleteTableStructure(source, {
        fieldId: this.uuidForLogic(),
        name: uniqueName,
        label: uniqueLabel,
        createColumnId: (_, index) => `table_col_${this.uuidForLogic()}_${index + 1}`,
      });

      this.currentForm.sections[si].fields.splice(fi + 1, 0, clone);
      this.openGenericDialog(
        "The complete table structure was copied, including advanced settings and show/hide logic. Entered data was not copied."
      );
    },

    removeField(si, fi) {
      this.ensureCurrentFormExists();
      const field = this.currentForm.sections?.[si]?.fields?.[fi];
      if (field) {
        this.removeValueAssignmentReferencesForFields([
          { field, sectionIndex: si, fieldIndex: fi },
        ]);
      }
      this.currentForm.sections[si]?.fields?.splice(fi, 1);
    },

    openConstraintsDialog(si, fi) {
      this.ensureCurrentFormExists();

      const f = this.currentForm.sections[si]?.fields?.[fi];
      if (!f) return;

      this.currentFieldIndices = { sectionIndex: si, fieldIndex: fi };
      this.currentFieldType = f.type === "slider" ? "slider" : f.type;

      const existing = JSON.parse(JSON.stringify(f.constraints || {}));

      this.constraintsForm = {
        ...existing,
        type: this.currentFieldType,

        // choice options for dialog
        options: (f.type === "select" || f.type === "radio")
          ? (Array.isArray(f.options) ? [...f.options] : [])
          : existing.options,

        // date defaults
        dateFormat: f.type === "date"
          ? (existing.dateFormat || "dd.MM.yyyy")
          : existing.dateFormat,

        // slider defaults
        ...(f.type === "slider" ? {
          mode: existing.mode === "linear" ? "linear" : "slider",
          min: Number.isFinite(existing.min) ? existing.min : 1,
          max: Number.isFinite(existing.max) ? existing.max : 100,
          step: Number.isFinite(existing.step) ? existing.step : 1,
          percent: !!existing.percent
        } : {})
      };

      this.showConstraintsDialog = true;
    },

    async confirmConstraintsDialog(payload) {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices;
      const f = this.currentForm.sections[sectionIndex]?.fields?.[fieldIndex];
      if (!f) {
        this.showConstraintsDialog = false;
        return;
      }

      const previousField = JSON.parse(JSON.stringify(f));
      const nextField = payload?.field;

      if (!nextField || typeof nextField !== "object") {
        this.showConstraintsDialog = false;
        return;
      }

      const preserved = {
        _id: f._id,
        name: f.name,
        label: f.label,
      };

      const mergedField = {
        ...f,
        ...nextField,
        ...preserved,
        constraints: {
          ...(nextField.constraints || {}),
        },
      };

      if (!Array.isArray(mergedField.options)) {
        mergedField.options = [];
      }

      if (mergedField.type !== "textarea") {
        delete mergedField.rows;
      } else {
        mergedField.rows = Number.isFinite(Number(mergedField.rows))
          ? Number(mergedField.rows)
          : 4;
      }

      if (mergedField.type !== "table") {
        delete mergedField.tableConfig;
        if (!Array.isArray(mergedField.value)) {
          if (mergedField.type === "checkbox") mergedField.value = false;
          else if (mergedField.type === "slider") mergedField.value = null;
          else if (mergedField.type === "file") {
            mergedField.value = mergedField.constraints?.allowMultipleFiles ? [] : null;
          } else {
            mergedField.value = mergedField.value ?? "";
          }
        }
      }

      if (mergedField.type === "select") {
        mergedField.constraints = { ...(mergedField.constraints || {}) };
        delete mergedField.constraints.allowMultiple;
        if (!mergedField.options.includes(mergedField.value)) {
          mergedField.value = "";
        }
      }

      if (mergedField.type === "radio") {
        const allowMultiple = !!mergedField.constraints?.allowMultiple;
        if (allowMultiple) {
          if (!Array.isArray(mergedField.value)) {
            mergedField.value = mergedField.value ? [mergedField.value] : [];
          }
          mergedField.value = mergedField.value.filter((v) => mergedField.options.includes(v));
        } else {
          if (Array.isArray(mergedField.value)) {
            mergedField.value = mergedField.value[0] || "";
          }
          if (!mergedField.options.includes(mergedField.value)) {
            mergedField.value = "";
          }
        }
      }

      if (mergedField.type === "checkbox") {
        mergedField.value = !!mergedField.value;
      }

      if (mergedField.type === "date") {
        mergedField.placeholder =
          mergedField.constraints?.dateFormat || mergedField.placeholder || "dd.MM.yyyy";
      }

      if (mergedField.type === "file") {
        mergedField.icon = mergedField.icon || icons.paperclip;
        const fallbackMod = String(mergedField.label || "").trim() || mergedField.name;
        if (
          !Array.isArray(mergedField.constraints?.modalities) ||
          !mergedField.constraints.modalities.length
        ) {
          mergedField.constraints.modalities = [fallbackMod];
        }
        mergedField.value =
          mergedField.constraints?.allowMultipleFiles !== false ? [] : null;
      }

      // IMPORTANT: if choice options changed, remove affected visibility logic rules
      const optionsChanged = this.haveChoiceOptionsChanged(previousField, mergedField);
      if (optionsChanged) {
        this.removeAffectedDependentVisibilityRules({
          sourceSectionIndex: sectionIndex,
          sourceFieldIndex: fieldIndex,
          previousField,
          nextField: mergedField,
        });
        this.removeAffectedValueAssignmentRulesForOptions({
          sourceSectionIndex: sectionIndex,
          sourceFieldIndex: fieldIndex,
          previousField,
          nextField: mergedField,
        });
      }

      if (["file", "table", "button"].includes(String(mergedField.type || "").toLowerCase())) {
        this.removeValueAssignmentReferencesForFields([
          {
            field: previousField,
            sectionIndex,
            fieldIndex,
          },
        ]);
      }

      this.currentForm.sections[sectionIndex].fields.splice(fieldIndex, 1, mergedField);

      if (Array.isArray(payload?.conversionWarnings) && payload.conversionWarnings.length) {
        this.openGenericDialog(
          `Field type updated. Please review the converted settings.\n\n${payload.conversionWarnings.join("\n")}`
        );
      }

      this.showConstraintsDialog = false;
    },

    cancelConstraintsDialog() {
      this.showConstraintsDialog = false;
    },

    downloadFormData() {
      this.ensureCurrentFormExists();

      const payload = {
        sections: this.currentForm.sections.map(sec => ({
          title: sec.title,
          fields: sec.fields,
          source: sec.source
        }))
      };

      const str = JSON.stringify(payload, null, 2);
      const name = "sections.json";
      const blob = new Blob([str], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    },

    openUploadDialog() { this.showUploadDialog = true; },
    closeUploadDialog() { this.showUploadDialog = false; },

    handleFileChange(e) {
      this.ensureCurrentFormExists();

      const file = e.target.files[0];
      if (!file) return this.openGenericDialog("No file selected.");

      const reader = new FileReader();
      reader.onload = evt => {
        try {
          const pd = JSON.parse(evt.target.result);
          if (Array.isArray(pd.sections)) {
            pd.sections = pd.sections.map(sec => ({
              ...sec,
              _id: sec._id || this.uuidForLogic(),
              fields: (sec.fields || []).map(field => ({
                ...field,
                _id: field._id || this.uuidForLogic(),
                constraints: field.constraints || {}
              }))
            }));
            this.currentForm.sections = pd.sections;
            this.adjustAssignments();
          } else {
            throw new Error("Bad format");
          }
        } catch (err) {
          console.error(err);
          this.openGenericDialog('Invalid file. Expect `{ "sections": [...] }`.');
        }
      };

      reader.readAsText(file);
      this.showUploadDialog = false;
    },

    async loadDataModels() {
      try {
        const res = await fetch("/template_schema.yaml");
        const doc = yaml.load(await res.text());
        this.dataModels = Object.entries(doc.classes)
          .filter(([n]) => n !== "Study")
          .map(([n, cls]) => ({
            title: n,
            description: cls.description || "",
            fields: Object.entries(cls.attributes).map(([attr, def]) => ({
              name: attr,
              label: def.label || this.prettyModelTitle(attr),
              description: def.description || "",
              type: this.resolveType(def),
              options: def.enum || [],
              rows: def.ui?.rows,
              constraints: { required: !!def.required, ...(def.constraints || {}) },
              placeholder: def.ui?.placeholder || def.description || ""
            }))
          }));
      } catch (e) {
        console.error("Failed to load data models:", e);
      }
    },

    resolveType(def) {
      const ui = def.ui || {};
      const dt = String(def.datatype || "").toLowerCase();
      const range = String(def.range || "").toLowerCase();

      if (ui.widget === "textarea" || dt === "textarea") return "textarea";
      if (ui.widget === "radio" || dt === "radio") return "radio";
      if (ui.widget === "dropdown" || dt === "dropdown" || def.enum) return "select";
      if (range === "date" || range === "datetime") return "date";
      if (["integer", "decimal", "number"].includes(range)) return "number";
      if (ui.widget === "file" || dt === "file" || range === "file") return "file";
      return "text";
    },

    toggleAdditionalOptions() {
      this.showAdditionalOptions = !this.showAdditionalOptions;
    },

    closeAdditionalOptions() {
      this.showAdditionalOptions = false;
    },

    onGlobalClick(e) {
      if (!this.showAdditionalOptions) return;

      const btn = this.$refs.additionalOptionsBtn;
      const menu = this.$refs.additionalOptionsMenu;

      const btnEl = Array.isArray(btn) ? btn[0] : btn;
      const menuEl = Array.isArray(menu) ? menu[0] : menu;

      if (btnEl && btnEl.contains(e.target)) return;
      if (menuEl && menuEl.contains(e.target)) return;

      this.showAdditionalOptions = false;
    },

    onDownloadTemplate() {
      this.closeAdditionalOptions();
      this.downloadFormData();
    },

    onUploadTemplate() {
      this.closeAdditionalOptions();
      this.openUploadDialog();
    }
  }
};
</script>
<style lang="scss" scoped>
@import "@/assets/styles/_base.scss";

/* =========================
   PAGE SHELL
   ========================= */
.create-form-container {
  width: 100%;
  height: 100vh;
  min-height: 0;
  padding: 16px 20px;
  background-color: $light-background;
  box-sizing: border-box;
  overflow: hidden;
}

.scratch-form-content {
  display: flex;
  gap: 20px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.scratch-form-content-full {
  display: block;
  width: 100%;
  min-width: 0;
  margin-top: 0;
}

/* =========================
   BACK BUTTON
   ========================= */
.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #dddddd;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
  color: #374151;
  font-size: 14px;
  line-height: 1;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    transform 0.02s ease;
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

/* =========================
   LEFT AVAILABLE FIELDS PANEL
   ========================= */
.available-fields {
  width: 300px;
  flex: 0 0 300px;
  min-height: 0;
  height: 100%;
  background: #ffffff;
  padding: 20px;
  border: 1px solid $border-color;
  border-radius: 12px;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.available-fields-topbar {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
  flex: 0 0 auto;
}

.available-fields h2 {
  margin: 0 0 14px;
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  line-height: 1.25;
  flex: 0 0 auto;
}

.available-fields-search {
  margin: 0 0 12px 0;
  display: flex;
  justify-content: center;
  flex: 0 0 auto;
}

.search-input {
  width: 100%;
  min-height: 40px;
  padding: 9px 11px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #1f2937;
  background: #ffffff;
  box-sizing: border-box;
}

.search-input:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

/* =========================
   TABS
   ========================= */
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  flex: 0 0 auto;
}

.tabs button {
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 8px;
  flex: 1 1 48%;
  min-width: 120px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  white-space: normal;
  word-wrap: break-word;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.tabs button:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.tabs button.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.16);
}

.template-fields,
.custom-fields,
.shacl,
.obi-fields {
  padding: 10px 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.template-fields,
.obi-fields {
  flex: 1 1 auto;
  overflow: hidden;
}

.custom-fields {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.tab-results {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.template-fields .tab-results,
.obi-fields .tab-results {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.template-instruction {
  font-style: italic;
  margin: 0 0 10px;
  color: #6b7280;
  font-size: 13px;
  flex: 0 0 auto;
}

/* =========================
   TEMPLATE FIELD CARDS
   ========================= */
.template-button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  width: 100%;
  padding: 10px 12px;
  margin: 8px 0;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition:
    background 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease;
  box-sizing: border-box;
}

.template-button:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.template-header {
  display: flex;
  align-items: center;
  font-weight: 700;
  font-size: 14px;
  color: #111827;
  margin-bottom: 4px;
  gap: 8px;
}

.template-header i {
  font-size: 16px;
  color: #374151;
}

.template-description {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.highlighted-model {
  border-color: #2563eb;
  background: #eef4ff;
}

.match-preview {
  margin: 6px 0 0 22px;
  padding-left: 14px;
  list-style: disc;
  color: #374151;
  font-size: 12px;
}

.no-matches {
  margin-top: 10px;
  font-size: 13px;
  color: #6b7280;
}

/* =========================
   CUSTOM FIELD BUTTONS
   ========================= */
.custom-fields .available-field-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.custom-fields .available-field-button:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.custom-fields .field-label {
  flex: 1;
  color: #111827;
  font-weight: 600;
}

/* =========================
   OBI PANEL
   ========================= */
.obi-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  flex: 0 0 auto;
}

.btn-add-selected {
  min-height: 36px;
  background: #2563eb;
  color: #ffffff;
  padding: 7px 11px;
  border-radius: 8px;
  border: 1px solid #2563eb;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.btn-add-selected:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.btn-add-selected:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.obi-term-row {
  margin: 8px 0;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  display: grid;
  grid-template-rows: auto 1fr;
  grid-template-columns: 1fr;
}

.obi-term-top {
  padding: 6px 8px 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.obi-checkbox-small {
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
}

.obi-selected-pill {
  background: #eef2ff;
  color: #3730a3;
  border: 1px solid #c7d2fe;
  border-radius: 9999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
}

.obi-term-body {
  padding: 6px 10px 10px 10px;
  cursor: pointer;
}

.obi-term-label {
  font-weight: 700;
  color: #111827;
  word-break: break-word;
}

.obi-term-meta {
  font-size: 12px;
  color: #6b7280;
  margin: 2px 0 4px;
  word-break: break-all;
}

.obi-def,
.obi-syn {
  font-size: 12px;
  color: #374151;
  white-space: normal;
  word-wrap: anywhere;
}

.obi-term-body mark,
.template-button mark {
  background: #fff3cd;
  padding: 0 2px;
  border-radius: 2px;
}

.obi-error {
  color: #b91c1c;
  margin-top: 6px;
}

.obi-empty,
.obi-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
}

.obi-more {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  flex: 0 0 auto;
}

.btn-more {
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #3730a3;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.btn-more:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.obi-count {
  font-size: 12px;
  color: #6b7280;
}

/* =========================
   MAIN FORM AREA
   ========================= */
.form-area {
  --builder-sticky-height: 64px;

  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  height: 100%;

  background: #ffffff;
  border: 1px solid $border-color;
  border-radius: 12px;

  overflow-y: auto;
  overflow-x: hidden;

  box-sizing: border-box;
  scroll-behavior: smooth;
}

.form-area-full {
  width: 100%;
  min-width: 0;
  height: calc(100vh - 40px);
  min-height: calc(100vh - 40px);
  overflow: visible;
}

.sections-container {
  flex: 0 0 auto;
  min-width: 0;
  position: relative;
  padding: 0 14px 18px;
  overflow: visible;
  box-sizing: border-box;
}

.form-area-full .sections-container {
  overflow: hidden;
  padding: 0;
}

.form-area-full .sections-container > div {
  width: 100%;
  min-width: 0;
}

.form-area-full .sections-container > .value-assignments-route-host {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.form-area-full .sections-container.value-assignments-sections-container {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* =========================
   STICKY BUILDER TOOLBAR
   ========================= */
.sections-topbar {
  position: sticky;
  top: 0;
  z-index: 250;

  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;

  min-width: 0;
  min-height: var(--builder-sticky-height);
  margin-bottom: 16px;
  padding: 10px 12px;

  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 0 0 12px 12px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.10);

  box-sizing: border-box;
  overflow: visible;
}

.builder-sticky-bar {
  overflow: visible;
}

.form-actions-inline {
  display: flex;
  align-items: center;
  gap: 8px;

  flex: 1 1 auto;
  min-width: 0;

  flex-wrap: wrap;
  overflow: visible;
  padding-bottom: 0;
}

.form-actions-inline .btn-option,
.form-actions-inline .btn-primary {
  flex: 0 1 auto;
  white-space: nowrap;
}

.builder-toolbar-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  position: relative;
  overflow: visible;
}

.additional-options {
  position: relative;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  overflow: visible;
}

.sections-topbar-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  margin-left: 0;
  white-space: nowrap;
}

.sections-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.reorder-move {
  transition: transform 180ms ease;
}

/* =========================
   EMPTY STATE
   ========================= */
.empty-builder-state {
  font-style: italic;
  color: #6b7280;
  margin-top: 12px;
  padding: 16px;
  background: #f9fafb;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
}

/* =========================
   SECTION CARD - ADD DATA STYLE
   ========================= */
.form-section {
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #f8fafc;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  overflow: visible;
  padding: 0;
  margin: 0;
}

.form-section.active {
  background: #f8fafc;
  border-left: 3px solid #374151;
}

.form-section.recently-added-section {
  animation: recently-added-section-glow 2.2s ease-out;
}

.section-header {
  position: sticky;
  top: calc(var(--builder-sticky-height));
  z-index: 160;

  padding: 18px 20px;
  background: #eef4f9;
  border-bottom: 1px solid #dbe4ee;
  border-radius: 12px 12px 0 0;

  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  margin-bottom: 0;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
}

.section-header h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  line-height: 1.25;
  word-break: break-word;
}

.section-header .field-actions {
  flex-shrink: 0;
}

.section-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  overflow: visible;
}

.section-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  overflow: visible;
}

/* =========================
   FIELD CARD - ADD DATA STYLE
   ========================= */
.form-group {
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.05s ease;
  overflow: visible;
}

.form-group:hover {
  border-color: #d1d5db;
}

.form-group.recently-added-field {
  animation: recently-added-field-glow 2.2s ease-out;
}

@keyframes recently-added-section-glow {
  0%, 35% {
    border-color: #60a5fa;
    background: #eff6ff;
    box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.2), 0 10px 28px rgba(37, 99, 235, 0.14);
  }
  100% {
    border-color: #dbe4ee;
    background: #f8fafc;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  }
}

@keyframes recently-added-field-glow {
  0%, 35% {
    border-color: #3b82f6;
    background: #f8fbff;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
  }
  100% {
    border-color: #e5e7eb;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }
}

@media (prefers-reduced-motion: reduce) {
  .form-section.recently-added-section {
    animation: none;
    border-color: #60a5fa;
    background: #eff6ff;
  }

  .form-group.recently-added-field {
    animation: none;
    border-color: #3b82f6;
    background: #f8fbff;
  }
}

.field-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.field-header > label {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  color: #111827;
  font-weight: 600;
  line-height: 1.35;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.required-asterisk {
  color: #dc2626;
  font-weight: 700;
  line-height: 1;
}

/* =========================
   ACTION BUTTONS
   ========================= */
.field-actions {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  flex-shrink: 0;
}

.icon-button {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  line-height: 1;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.icon-button:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
}

.icon-button:active {
  transform: translateY(0);
}

.icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-button i {
  font-size: 13px;
  color: currentColor;
}

.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: grab;
  user-select: none;
  color: #374151;
  background: #ffffff;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.drag-handle:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
}

.drag-handle:active {
  cursor: grabbing;
  transform: translateY(0);
}

.drag-handle-right {
  margin-left: 2px;
}

/* =========================
   FIELD BODY / INPUTS
   ========================= */
.field-box {
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: auto;
  overflow-y: visible;
}

input,
textarea,
select {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  margin-top: 5px;
  background: #ffffff;
  color: #1f2937;
  box-sizing: border-box;
  font-size: 14px;
}

textarea {
  min-height: 88px;
  resize: vertical;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

.help-text {
  display: block;
  margin-top: 8px;
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

/* =========================
   TABLE WIDTH FIX INSIDE SCRATCH
   ========================= */
.field-box :deep(.field-table-root) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.field-box :deep(.table-runtime-shell),
.field-box :deep(.table-runtime-wrap) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.field-box :deep(.table-runtime-wrap) {
  overflow-x: auto;
  overflow-y: visible;
  border-radius: 10px;
}

.field-box :deep(.table-runtime) {
  width: max-content;
  min-width: 100%;
}

/* =========================
   DROP INDICATORS
   ========================= */
.drop-before {
  box-shadow: 0 -3px 0 0 rgba(37, 99, 235, 0.55) inset;
}

.drop-after {
  box-shadow: 0 3px 0 0 rgba(37, 99, 235, 0.55) inset;
}

.field-drop-end {
  border: 1px dashed rgba(37, 99, 235, 0.35);
  border-radius: 10px;
  padding: 10px;
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  background: rgba(37, 99, 235, 0.04);
}

.field-drop-end.drop-active {
  border-color: rgba(37, 99, 235, 0.7);
  background: rgba(37, 99, 235, 0.08);
  color: #374151;
}

/* =========================
   BUILDER ACTION BUTTONS
   ========================= */
.btn-option,
.btn-primary,
.btn-ellipsis {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  padding: 7px 10px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.btn-option {
  background: #ffffff;
  color: #374151;
  border: 1px solid #d1d5db;
  flex: 0 0 auto;
}

.btn-option:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: 1px solid #2563eb;
  flex: 0 0 auto;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.btn-option:disabled,
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ellipsis {
  width: 36px;
  height: 36px;
  padding: 0;
  background: #ffffff;
  color: #374151;
  border: 1px solid #d1d5db;
  flex: 0 0 auto;
}

.btn-ellipsis:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.options-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 220px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  padding: 6px;
  z-index: 1000;
}

.options-item {
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.options-item:hover {
  background: #f3f4f6;
  color: #111827;
}

.options-item.danger {
  color: #b91c1c;
}

/* =========================
   MODALS
   ========================= */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
  box-sizing: border-box;
}

.modal {
  background: #ffffff;
  padding: 20px;
  border-radius: 12px;
  max-width: 90%;
  max-height: 90%;
  overflow-y: auto;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
  box-sizing: border-box;
}

.modal p {
  margin: 0;
  white-space: pre-line;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.6;
  color: #374151;
}

.modal.model-dialog {
  width: min(92vw, 720px);
  max-height: 80vh;
  padding: 20px 16px;
}

.preview-modal {
  width: min(92vw, 720px);
  height: 80vh;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 10px;
}

.preview-content {
  flex: 1;
  background: #ffffff;
  padding: 10px;
  overflow-y: auto;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.table-copy-modal {
  width: min(92vw, 620px);
}

.table-copy-modal h3 {
  margin: 0 0 6px;
  color: #111827;
}

.table-copy-intro {
  margin-bottom: 16px !important;
}

.table-copy-choices {
  display: grid;
  gap: 12px;
}

.table-copy-choice {
  position: relative;
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 16px;
  text-align: left;
  color: #1f2937;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  cursor: pointer;
}

.table-copy-choice:hover,
.table-copy-choice:focus-visible {
  border-color: #2563eb;
  background: #f8faff;
  outline: none;
}

.table-copy-choice.recommended {
  border-color: #93c5fd;
  padding-right: 112px;
}

.table-copy-choice strong {
  color: #111827;
  font-size: 15px;
}

.table-copy-choice span:not(.table-copy-recommended) {
  color: #4b5563;
  line-height: 1.45;
}

.table-copy-recommended {
  position: absolute;
  top: 14px;
  right: 14px;
  padding: 3px 8px;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

@media (max-width: 520px) {
  .table-copy-choice.recommended {
    padding-right: 16px;
  }

  .table-copy-recommended {
    position: static;
    justify-self: start;
  }
}

.input-dialog-field {
  width: 100%;
  padding: 8px;
  margin-top: 8px;
}

/* =========================
   MODEL PROPERTY DIALOG
   ========================= */
.model-prop-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.btn-select-all {
  flex: 0 0 auto;
}

.model-prop-list {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px 12px;
}

.prop-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  box-sizing: border-box;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease;
}

.prop-cell:hover {
  background: #f3f4f6;
}

.prop-cell.selected {
  border-color: #2563eb;
  background: #eef4ff;
}

.prop-cell.disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.prop-info {
  flex: 1 1 auto;
  min-width: 0;
  text-align: left;
}

.prop-label {
  display: block;
  font-weight: 700;
  color: #111827;
  word-break: break-word;
}

.prop-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.prop-checkbox {
  flex: 0 0 auto;
  margin-left: 6px;
}

.model-prop-list .prop-checkbox {
  width: auto;
  padding: 0;
  margin-top: 0;
  border: none;
  border-radius: 0;
}

.model-target {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eef0f3;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-target-selection {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-target-hint {
  margin: 0;
  padding: 0;
  color: #374151;
}

.model-target-check {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  margin: 0;
  padding: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.1;
}

.model-target-check input[type="checkbox"] {
  width: auto !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  transform: translateY(1px);
}

/* =========================
   IMPORT / TABLE MODALS
   ========================= */
.modal-overlay.import-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.table-config-modal {
  width: min(96vw, 1060px);
  max-height: 90vh;
  overflow-y: auto;
}

.table-builder-preview {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.table-builder-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.table-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #374151;
  font-size: 12px;
  border: 1px solid #c7d2fe;
}

.table-preview-wrap {
  overflow: auto;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #ffffff;
}

.table-preview-table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
}

.table-preview-table th,
.table-preview-table td {
  border: 1px solid #e5e7eb;
  padding: 10px;
  text-align: left;
  vertical-align: top;
}

.table-head-title {
  font-weight: 700;
  color: #111827;
}

.table-head-type {
  margin-top: 2px;
  font-size: 11px;
  color: #6b7280;
  text-transform: capitalize;
}

.table-cell-placeholder {
  color: #9ca3af;
  font-size: 13px;
}

/* =========================
   FLOATING SCROLL BUTTON
   ========================= */
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

/* =========================
   LABEL HELPERS
   ========================= */
.field-label-with-required {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  color: #111827;
  line-height: 1.25;
}
.saved-template-card {
  position: relative;
}

.saved-template-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: #fee2e2;
  color: #b91c1c;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.saved-template-delete:hover {
  background: #fecaca;
}
.saved-template-fields {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.saved-template-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 8px 0 10px;
}

.saved-template-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.saved-template-card {
  cursor: pointer;
}

.saved-template-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  font-size: 11px;
  color: #6b7280;
}

.saved-template-meta span {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 999px;
  padding: 3px 8px;
}

.saved-template-meta .saved-template-type {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
}

.saved-template-card mark {
  background: #fef3c7;
  color: #92400e;
  padding: 0 2px;
  border-radius: 3px;
}
.saved-template-section-name {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #374151;
}
/* =========================
   RESPONSIVE
   ========================= */
@media (max-width: 1100px) {
  .create-form-container {
    padding: 16px;
  }

  .scratch-form-content {
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .available-fields {
    width: 100%;
    min-width: 0;
    flex: 0 0 34vh;
    height: 34vh;
    max-height: 34vh;
  }

  .form-area {
    --builder-sticky-height: 64px;
    flex: 1 1 auto;
    height: auto;
    min-height: 0;
  }

  .sections-topbar {
    align-items: flex-start;
  }

  .form-actions-inline {
    flex-wrap: wrap;
    overflow: visible;
  }
}

@media (max-width: 900px) {
  .create-form-container {
    height: 100vh;
    padding: 12px;
  }

  .scratch-form-content {
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .available-fields {
    width: 100%;
    flex: 0 0 34vh;
    height: 34vh;
    max-height: 34vh;
  }

  .form-area {
    --builder-sticky-height: 64px;
    flex: 1 1 auto;
    min-height: 0;
  }

  .sections-topbar {
    align-items: flex-start;
    flex-direction: row;
  }

  .form-actions-inline {
    flex-wrap: wrap;
    overflow: visible;
  }

  .form-actions-inline .btn-option,
  .form-actions-inline .btn-primary {
    flex: 0 1 auto;
  }

  .builder-toolbar-right {
    flex: 0 0 auto;
  }

  .sections-topbar-actions {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex: 0 0 auto;
    margin-left: 0;
    white-space: nowrap;
  }

  .floating-scroll-btn {
    right: 16px;
    bottom: 16px;
    width: 42px;
    height: 42px;
  }
}

@media (max-width: 768px) {
  .create-form-container {
    padding: 12px;
  }

  .form-area {
    --builder-sticky-height: 64px;
  }

  .sections-topbar {
    flex-direction: row;
    align-items: flex-start;
  }

  .builder-toolbar-right {
    width: auto;
    flex: 0 0 auto;
  }

  .sections-topbar-actions {
    width: auto;
    justify-content: flex-end;
    flex: 0 0 auto;
  }

  .section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .section-header h3 {
    font-size: 20px;
  }

  .field-header {
    flex-direction: column;
    align-items: stretch;
  }

  .field-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .form-actions-inline {
    width: auto;
    flex-wrap: wrap;
    overflow: visible;
  }

  .form-actions-inline .btn-option,
  .form-actions-inline .btn-primary {
    width: auto;
    flex: 0 1 auto;
  }

  .additional-options {
    width: auto;
    flex: 0 0 auto;
  }

  .btn-ellipsis {
    width: 36px;
    height: 36px;
  }

  .options-menu {
    right: 0;
    left: auto;
    width: auto;
    min-width: 220px;
  }

  .modal-overlay {
    padding: 12px;
  }

  .modal {
    max-width: 100%;
  }

  .model-prop-list {
    grid-template-columns: 1fr;
  }
}
</style>
