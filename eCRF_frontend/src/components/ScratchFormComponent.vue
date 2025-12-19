<template>
  <div class="create-form-container">
    <!-- Header -->
    <div class="header-container">
      <button @click="goBack" class="btn-back" title="Go Back">
        <i :class="icons.back"></i> Back
      </button>
    </div>

    <div class="scratch-form-content">
      <!-- ───────── Available Fields ───────── -->
      <div v-if="!showMatrix" class="available-fields">
        <h2>Available Fields</h2>

        <div class="tabs">
          <button
            :class="{ active: activeTab === 'template' }"
            @click="activeTab = 'template'"
          >Available Template</button>
          <button
            :class="{ active: activeTab === 'custom' }"
            @click="activeTab = 'custom'"
          >Custom Fields</button>
          <button
            :class="{ active: activeTab === 'obi' }"
            @click="activeTab = 'obi'"
          >Ontology (OBI)</button>
          <button
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

        <!-- SHACL -->
        <div v-else-if="activeTab === 'shacl'">
          <ShaclComponents :shaclComponents="shaclComponents" @takeover="onShaclTakeover" />
        </div>
      </div>

      <!-- ───────── Form Area / Protocol Matrix ───────── -->
      <div class="form-area">
        <div class="sections-container">
          <!-- Sections View -->
          <div v-if="!showMatrix">
            <transition-group name="reorder" tag="div" class="sections-list">
              <div
                v-for="(section, si) in currentForm.sections"
                :key="getSectionUid(section)"
                class="form-section"
                :class="[
                  { active: activeSection === si },
                  getSectionDropClass(si)
                ]"
                @click="onSectionClick(si)"
                :ref="'section-' + si"
                @dragover.prevent="onSectionDragOver(si, $event)"
                @drop.prevent="onSectionDrop(si)"
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
                    <span
                      class="drag-handle drag-handle-right"
                      draggable="true"
                      title="Move section"
                      @click.stop
                      @dragstart.stop="onSectionDragStart(si, $event)"
                      @dragend="onDragEnd"
                    >
                      <i :class="icons.move || 'fas fa-grip-vertical'"></i>
                    </span>

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
                      :class="getFieldDropClass(si, fi)"
                      @dragover.stop.prevent="onFieldDragOver(si, fi, $event)"
                      @drop.stop.prevent="onFieldDrop(si, fi)"
                    >
                      <div class="field-header">
                        <label
                          v-if="field.type !== 'button' && field.type !== 'checkbox'"
                          :for="field.name"
                        >
                          {{ field.label }}
                        </label>
                        <label
                          v-else-if="field.type === 'checkbox'"
                          class="checkbox-label"
                          :for="field.name"
                        >
                          {{ field.label }}
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
                            title="Add Similar Field"
                            @click.stop.prevent="setActiveSection(si); addSimilarField(si, fi)"
                          ><i :class="icons.add"></i></button>

                          <button
                            class="icon-button"
                            title="Delete Field"
                            @click.stop.prevent="setActiveSection(si, fi); removeField(si, fi)"
                          ><i :class="icons.delete"></i></button>

                          <button
                            class="icon-button"
                            title="Settings"
                            @click.stop.prevent="setActiveSection(si); openConstraintsDialog(si, fi)"
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
          <div v-else>
            <ProtocolMatrix
              :visits="visits"
              :groups="groups"
              :selectedModels="selectedModels"
              :assignments="assignments"
              @assignment-updated="onAssignmentUpdated"
              @edit-template="editTemplate"
            />
          </div>
        </div>

        <!-- Form Actions -->
        <div v-if="!showMatrix" class="form-actions">
          <button @click.prevent="addNewSection" class="btn-option">
            + Add Section
          </button>
          <button @click.prevent="confirmClearForm" class="btn-option">
            Clear All
          </button>

          <button
            @click.prevent="handleProtocolClick"
            class="btn-option protocol-btn"
          >
            Create Visit Schedule
          </button>
          <!-- Additional options (Download/Upload) -->
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
              <button class="options-item" role="menuitem" @click.prevent="onDownloadTemplate">
                Download Template
              </button>
              <button class="options-item" role="menuitem" @click.prevent="onUploadTemplate">
                Upload Template
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Model Dialog -->
    <div v-if="showModelDialog" class="modal-overlay">
      <div class="modal model-dialog">
        <h3>Select Properties for {{ prettyModelTitle(currentModel.title) }}</h3>
        <div class="model-prop-list">
          <div
            v-for="(prop, i) in currentModel.fields"
            :key="prop.name"
            class="prop-cell"
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
              v-model="selectedProps[i]"
              class="prop-checkbox"
              :disabled="modelAddToExisting && isPropAlreadyInTargetSection(prop)"
              :title="(modelAddToExisting && isPropAlreadyInTargetSection(prop)) ? 'Already added in selected section' : ''"
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
          <button @click="showModelDialog=false" class="btn-option">
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
        @updateConstraints="confirmConstraintsDialog"
        @closeConstraintsDialog="cancelConstraintsDialog"
        @showGenericDialog="openGenericDialog"
      />
    </div>

    <!-- Preview Dialog -->
    <div v-if="showPreviewDialog" class="modal-overlay">
      <div class="modal preview-modal">
        <FormPreview :form="currentForm" />
        <div class="modal-actions">
          <button @click="closePreviewDialog" class="btn-primary">Close</button>
        </div>
      </div>
    </div>

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
import { normalizeConstraints, coerceDefaultForType } from "@/utils/constraints";

export default {
  name: "ScratchFormComponent",
  components: {
    ShaclComponents,
    ProtocolMatrix,
    FieldConstraintsDialog,
    FormPreview,
    DateFormatPicker,
    FieldCheckbox,
    FieldRadioGroup,
    FieldTime,
    FieldSlider,
    FieldLinearScale,
    FieldFileUpload
  },
  data() {
    return {
      forms: JSON.parse(localStorage.getItem("scratchForms") || "[]"),
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

      dragState: {
        kind: null,          // "section" | "field" | null
        fromSection: null,
        fromField: null,
        overSection: null,
        overField: null,
        position: null       // "before" | "after" | "end" | null
      },

      uidCounter: 1,
      sectionUidMap: new WeakMap(),
      fieldUidMap: new WeakMap(),

      showAdditionalOptions: false,
    };
  },
  computed: {
    icons()         { return icons; },
    studyDetails()  { return this.$store.state.studyDetails || {}; },
    currentForm()   { return this.forms[this.currentFormIndex] || { sections: [] }; },
    selectedModels(){
      return this.currentForm.sections.map(sec => ({ title: sec.title, fields: sec.fields }));
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
            (f.name  || "").toLowerCase().includes(q)
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
    }
  },
  watch: {
    visits: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    groups: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    selectedModels: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    forms: {
      deep: true,
      handler(f) { localStorage.setItem("scratchForms", JSON.stringify(f)); }
    },
    // If user leaves the template tab, clear the search to avoid confusion when returning
    activeTab(newVal) {
      if (newVal !== 'template' && this.searchQuery) this.searchQuery = "";
      if (newVal !== 'obi') {
        this.resetObiState();
      }
    },

    // when adding to existing section, pre-check/disable already-added props
    modelAddToExisting() {
      this.$nextTick(() => this.syncSelectedPropsForExistingSection());
    },
    modelTargetSectionIndex() {
      this.$nextTick(() => this.syncSelectedPropsForExistingSection());
    }
  },
  async mounted() {
    document.addEventListener("click", this.onGlobalClick);
    if (this.studyDetails.study_metadata?.id) {
      const stored = localStorage.getItem("scratchForms");
      if (stored) {
        try { this.forms = JSON.parse(stored); } catch { this.forms = [{ sections: [] }]; }
      } else if (Array.isArray(this.studyDetails.forms)) {
        this.forms = JSON.parse(JSON.stringify(this.studyDetails.forms));
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } else {
        this.forms = [{ sections: [] }];
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      }
    } else {
      localStorage.removeItem("scratchForms");
      this.forms = [{ sections: [] }];
    }

    this.visits = Array.isArray(this.studyDetails.visits) ? JSON.parse(JSON.stringify(this.studyDetails.visits)) : [];
    this.groups  = Array.isArray(this.studyDetails.groups)  ? JSON.parse(JSON.stringify(this.studyDetails.groups))  : [];
    this.adjustAssignments();

    try {
      const res = await axios.get("/forms/available-fields");
      this.generalFields = res.data.map((f, idx) => ({
        ...f,
        name: f.name || `${f.type}_${idx}`,
        description: f.helpText || f.placeholder || "",
        options: (f.type === 'select' || f.type === 'radio')
          ? (Array.isArray(f.options) && f.options.length ? f.options : ['Option 1'])
          : (f.options || []),
        constraints: f.constraints || {}
      }));
    } catch (e) {
      console.error("Failed to load custom fields", e);
    }

    await this.loadDataModels();
  },
   beforeUnmount() {
      document.removeEventListener("click", this.onGlobalClick);
    },
  methods: {
    /* ---------- Stable keys (no mutation) ---------- */
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

    /* ---------- Model dialog helpers (prevent duplicates) ---------- */
    clampSectionIndex(i) {
      const n = this.currentForm.sections.length;
      if (!n) return 0;
      const x = Number.isInteger(i) ? i : 0;
      return Math.max(0, Math.min(x, n - 1));
    },
    getTargetSectionForModelDialog() {
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
      // Only apply pre-checking when user is adding to an existing section.
      if (!this.showModelDialog) return;
      if (!this.modelAddToExisting) return;
      if (!this.currentModel || !Array.isArray(this.currentModel.fields)) return;

      const sec = this.getTargetSectionForModelDialog();
      if (!sec || !Array.isArray(sec.fields)) return;

      const existing = new Set(sec.fields.map(f => String(f?.name || "")));
      this.currentModel.fields.forEach((p, i) => {
        const nm = String(p?.name || "");
        if (nm && existing.has(nm)) {
          // Check it (informational) and disable via template condition.
          this.$set(this.selectedProps, i, true);
        }
      });
    },

    /* ---------- Drag helpers ---------- */
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

    getSectionDropClass(si) {
      if (this.dragState.kind !== "section") return "";
      if (this.dragState.overSection !== si) return "";
      return this.dragState.position === "after" ? "drop-after" : "drop-before";
    },
    getFieldDropClass(si, fi) {
      if (this.dragState.kind !== "field") return "";
      if (this.dragState.overSection !== si) return "";
      if (this.dragState.overField !== fi) return "";
      return this.dragState.position === "after" ? "drop-after" : "drop-before";
    },

    /* ---------- Section drag/drop ---------- */
    onSectionDragStart(si, evt) {
      if (this.showMatrix) return;
      this.dragState.kind = "section";
      this.dragState.fromSection = si;
      this.dragState.fromField = null;

      try {
        evt.dataTransfer.effectAllowed = "move";
        evt.dataTransfer.setData("text/plain", "section");
      } catch { /* ignore */ }
    },
    onSectionDragOver(targetIndex, evt) {
      if (this.dragState.kind !== "section") return;
      const el = evt.currentTarget;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const after = (evt.clientY - rect.top) > rect.height / 2;
      this.dragState.overSection = targetIndex;
      this.dragState.overField = null;
      this.dragState.position = after ? "after" : "before";
    },
    onSectionDrop(targetIndex) {
      if (this.dragState.kind !== "section") return;

      const sections = this.forms[this.currentFormIndex].sections || [];
      const from = this.dragState.fromSection;
      if (!Number.isInteger(from) || from < 0 || from >= sections.length) {
        return this.onDragEnd();
      }

      const movingObj = sections[from];

      let to = targetIndex + (this.dragState.position === "after" ? 1 : 0);
      if (from < to) to -= 1;
      to = Math.max(0, Math.min(to, sections.length - 1));

      // Even if dropped back on itself, requirement says moved section should be active
      // so we'll still set active to its current index.
      if (to !== from) {
        sections.splice(from, 1);
        sections.splice(to, 0, movingObj);

        // Move matching assignments slice (critical: no regression)
        if (Array.isArray(this.assignments) && this.assignments.length) {
          const a = this.assignments;
          if (from >= 0 && from < a.length) {
            const movedA = a.splice(from, 1)[0];
            a.splice(to, 0, movedA);
            this.assignments = a;
            this.$store.commit("setStudyDetails", { ...this.studyDetails, assignments: this.assignments });
          }
        }
      }

      // Requirement: moved section becomes active
      const newIdx = sections.indexOf(movingObj);
      this.activeSection = newIdx >= 0 ? newIdx : 0;

      this.$nextTick(() => this.focusSection(this.activeSection));
      this.onDragEnd();
    },

    /* ---------- Field drag/drop ---------- */
    onFieldDragStart(si, fi, evt) {
      if (this.showMatrix) return;
      this.dragState.kind = "field";
      this.dragState.fromSection = si;
      this.dragState.fromField = fi;

      try {
        evt.dataTransfer.effectAllowed = "move";
        evt.dataTransfer.setData("text/plain", "field");
      } catch { /* ignore */ }
    },
    onFieldDragOver(si, fi, evt) {
      if (this.dragState.kind !== "field") return;
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

      const form_s = this.dragState.fromSection;
      const fromF = this.dragState.fromField;
      const toS = si;

      const sections = this.forms[this.currentFormIndex].sections || [];
      const fromSec = sections[form_s];
      const toSec = sections[toS];
      if (!fromSec || !toSec) return this.onDragEnd();

      const fromFields = fromSec.fields || [];
      const toFields = toSec.fields || [];

      if (!Number.isInteger(fromF) || fromF < 0 || fromF >= fromFields.length) {
        return this.onDragEnd();
      }

      let insertAt = fi + (this.dragState.position === "after" ? 1 : 0);

      const moved = fromFields.splice(fromF, 1)[0];
      if (form_s === toS && insertAt > fromF) insertAt -= 1;

      insertAt = Math.max(0, Math.min(insertAt, toFields.length));
      toFields.splice(insertAt, 0, moved);

      // Requirement: destination section becomes active
      this.activeSection = toS;
      this.$nextTick(() => this.focusSection(this.activeSection));
      this.onDragEnd();
    },

    onFieldDropEndOver(si) {
      if (this.dragState.kind !== "field") return;
      this.dragState.overSection = si;
      this.dragState.overField = null;
      this.dragState.position = "end";
    },
    onFieldDropEnd(si) {
      if (this.dragState.kind !== "field") return;

      const form_s = this.dragState.fromSection;
      const fromF = this.dragState.fromField;
      const toS = si;

      const sections = this.forms[this.currentFormIndex].sections || [];
      const fromSec = sections[form_s];
      const toSec = sections[toS];
      if (!fromSec || !toSec) return this.onDragEnd();

      const fromFields = fromSec.fields || [];
      const toFields = toSec.fields || [];

      if (!Number.isInteger(fromF) || fromF < 0 || fromF >= fromFields.length) {
        return this.onDragEnd();
      }

      const moved = fromFields.splice(fromF, 1)[0];
      let insertAt = toFields.length;
      if (form_s === toS && insertAt > fromF) insertAt -= 1;

      insertAt = Math.max(0, Math.min(insertAt, toFields.length));
      toFields.splice(insertAt, 0, moved);

      // Requirement: destination section becomes active
      this.activeSection = toS;
      this.$nextTick(() => this.focusSection(this.activeSection));
      this.onDragEnd();
    },

    onFieldContainerOver(si) {
      if (this.dragState.kind !== "field") return;
      this.dragState.overSection = si;
      this.dragState.overField = null;
      this.dragState.position = "end";
    },
    onFieldContainerDrop(si) {
      if (this.dragState.kind !== "field") return;
      this.onFieldDropEnd(si);
    },

    /* ---------- OBI search ---------- */
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
      // new query → reset limit to default
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
      this.requestedLimit = this.requestedLimit + this.limitStep;
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
      // keep it reasonable in UI
      const arr = (list || []).slice(0, 6);
      return arr.join(", ");
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

    /* ---------- Existing functionality ---------- */
    onShaclTakeover(section) {
      const insertAt = Math.min(this.activeSection + 1, this.currentForm.sections.length);
      const sec = {
        title: section.title,
        fields: (section.fields || []).map(f => ({
          ...f,
          constraints: f.constraints || {}
        })),
        collapsed: false,
        source: "shacl"
      };
      this.forms[this.currentFormIndex].sections.splice(insertAt, 0, sec);
      this.activeSection = insertAt;
      this.$nextTick(() => this.focusSection(insertAt));
      this.adjustAssignments();
    },

    goBack() { this.$router.back() },
    prettyModelTitle(s) { return this.$formatLabel ? this.$formatLabel(s) : String(s || '') },
    modelIcon(title) {
      const key = String(title || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      return this.icons[key] || 'fas fa-book';
    },
    fieldIcon(label) {
      const key = String(label || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      return this.icons[key] || 'fas fa-dot-circle';
    },

    // highlight helper for search matches
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
      return q && (String(title || "").toLowerCase().includes(q));
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
      this.activeSection = i;
      const section = this.currentForm.sections[i];
      if (section && section.collapsed) section.collapsed = false;
      this.focusSection(i);
    },

    openConfirmDialog(msg, cb) { this.confirmDialogMessage = msg; this.confirmCallback = cb; this.showConfirmDialog = true; },
    confirmDialogYes() { this.showConfirmDialog = false; if (this.confirmCallback) this.confirmCallback(); },
    closeConfirmDialog() { this.showConfirmDialog = false; },
    openGenericDialog(msg, cb) { this.genericDialogMessage = msg; this.genericCallback = cb; this.showGenericDialog = true; },
    closeGenericDialog() { this.showGenericDialog = false; if (this.genericCallback) this.genericCallback(); },

    openInputDialog(msg, def, cb) { this.inputDialogMessage = msg; this.inputDialogValue = def; this.inputDialogCallback = cb; this.showInputDialog = true; },
    confirmInputDialog() { this.showInputDialog = false; if (this.inputDialogCallback) this.inputDialogCallback(this.inputDialogValue); },
    cancelInputDialog() { this.showInputDialog = false; },

    adjustAssignments() {
      const m = this.selectedModels.length;
      const v = this.visits.length;
      const g = this.groups.length;
      if (m === 0 || v === 0 || g === 0) { this.assignments = []; return; }
      if (this.studyDetails.study_metadata?.id && Array.isArray(this.studyDetails.assignments)) {
        const old = this.studyDetails.assignments;
        const fresh = [];
        for (let mi = 0; mi < m; mi++) {
          fresh[mi] = [];
          for (let vi = 0; vi < v; vi++) {
            fresh[mi][vi] = [];
            for (let gi = 0; gi < g; gi++) {
              const ov = old[mi]?.[vi]?.[gi];
              fresh[mi][vi][gi] = typeof ov === 'boolean' ? ov : false;
            }
          }
        }
        this.assignments = fresh;
      } else {
        this.assignments = Array.from({ length: m }, () =>
          Array.from({ length: v }, () => Array.from({ length: g }, () => false))
        );
      }
    },

    handleProtocolClick() { this.showMatrix = true; },
    editTemplate() { this.showMatrix = false; },
    onAssignmentUpdated({ mIdx, vIdx, gIdx, checked }) {
      this.assignments[mIdx][vIdx][gIdx] = checked;
      this.$store.commit("setStudyDetails", { ...this.studyDetails, assignments: this.assignments });
    },

    focusSection(i) {
      this.$nextTick(() => {
        const ref = this.$refs[`section-${i}`];
        const el = Array.isArray(ref) ? ref[0] : ref;
        if (el?.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    },

    openModelDialog(model) {
      const full = this.dataModels.find(d => d.title === model.title) || model;
      this.currentModel = full;
      this.selectedProps = full.fields.map(() => false);

      // Default: add as new section (below current active section)
      this.modelAddToExisting = false;
      this.modelTargetSectionIndex = this.clampSectionIndex(this.activeSection);

      this.showModelDialog = true;

      // If user later toggles to existing, watcher will pre-check already-added props.
    },

    takeoverModel() {
      const chosen = this.currentModel.fields
        .filter((_, i) => this.selectedProps[i])
        .map(f => ({ ...f, description: f.description || "", constraints: f.constraints || {} }));

      // Add to existing section: NO DUPLICATES (skip already-present field.name)
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
          // Skip duplicates instead of renaming (prevents “selected twice” duplicates)
          if (nm && existingNames.has(nm)) return;

          existingNames.add(nm);
          targetSec.fields.push({ ...f });
          added += 1;
        });

        // Requirement: destination section becomes active
        this.activeSection = idx;
        this.$nextTick(() => this.focusSection(idx));

        // If nothing new was added, still close; optional info dialog:
        if (added === 0) {
          this.openGenericDialog(`All selected field(s) already exist in "${targetSec.title}".`);
        }

        this.showModelDialog = false;
        return;
      }

      // Add as a NEW section (existing behavior)
      const insertAt = Math.min(this.activeSection + 1, this.currentForm.sections.length);
      const sec = { title: this.currentModel.title, fields: chosen, collapsed: false, source: "template" };
      this.forms[this.currentFormIndex].sections.splice(insertAt, 0, sec);
      this.activeSection = insertAt;
      this.$nextTick(() => this.focusSection(insertAt));
      this.adjustAssignments();
      this.showModelDialog = false;
    },

    addNewSection() {
      const sec = { title: `Section ${this.currentForm.sections.length + 1}`, fields: [], collapsed: false, source: "manual" };
      this.forms[this.currentFormIndex].sections.push(sec);
      this.activeSection = this.currentForm.sections.length - 1;
      this.adjustAssignments();
      this.focusSection(this.activeSection);
    },
    addNewSectionBelow(i) {
      const current = this.currentForm.sections[i];
      const sec = {
        title: `${current.title} (Copy)`,
        fields: current.fields.map(field => ({
          ...field,
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
        this.currentForm.sections.splice(i, 1);
        this.activeSection = Math.max(0, this.activeSection - 1);
        this.adjustAssignments();
      });
    },

    confirmClearForm() {
      this.openConfirmDialog("Do you want to clear all sections?", () => {
        this.forms[this.currentFormIndex].sections = [];
        this.activeSection = 0;
        this.adjustAssignments();
      });
    },

    toggleSection(i) {
      const section = this.forms[this.currentFormIndex].sections[i];
      section.collapsed = !section.collapsed;
    },
    setActiveSection(i) { this.activeSection = i; this.focusSection(i); },

    addFieldToActiveSection(field) {
      if (!this.currentForm.sections.length) this.addNewSection();
      const sec = this.currentForm.sections[this.activeSection];
      if (sec.collapsed) this.toggleSection(this.activeSection);

      const base = {
        name: `${(field.name || field.type)}_${Date.now()}`,
        label: field.label,
        type: field.type,
        options: (field.type === 'select' || field.type === 'radio')
          ? (Array.isArray(field.options) && field.options.length ? [...field.options] : ['Option 1'])
          : (field.options || []),
        placeholder: field.description || field.placeholder || '',
        value: field.type === 'checkbox' ? false : "",
        constraints: field.constraints || {}
      };

      // SLIDER defaults
      if (base.type === 'slider') {
        base.value = null;
        base.constraints = {
          ...(base.constraints || {}),
          mode: base.constraints?.mode || 'slider',
          percent: !!base.constraints?.percent,
          min: Number.isFinite(base.constraints?.min) ? base.constraints.min : (base.constraints?.percent ? 1 : 1),
          max: Number.isFinite(base.constraints?.max) ? base.constraints.max : (base.constraints?.percent ? 100 : 100),
          step: Number.isFinite(base.constraints?.step) ? base.constraints.step : 1,
          marks: Array.isArray(base.constraints?.marks) ? base.constraints.marks : (base.constraints?.marks || [])
        };
      }

      // Date defaults
      if (base.type === 'date') {
        base.constraints = { ...base.constraints, dateFormat: base.constraints?.dateFormat || 'dd.MM.yyyy' };
        base.placeholder = base.placeholder || base.constraints.dateFormat;
      }

      // File defaults
      if (base.type === 'file') {
        base.value = null;
        base.icon = base.icon || icons.paperclip;
        const provided = base.constraints || {};
        // default modality from label (or fallback to name)
        const fallbackMod = (String(base.label || '').trim()) || base.name;

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
          //  Default to label/name when user hasn’t picked any modality
          modalities: (Array.isArray(provided.modalities) && provided.modalities.length)
            ? provided.modalities
            : [fallbackMod],
          // default true when not specified
          allowMultipleFiles: (provided.allowMultipleFiles === undefined) ? true : !!provided.allowMultipleFiles
        };
      }

      sec.fields.push(base);
    },

    editSection(i, v) { if (v) this.currentForm.sections[i].title = v; },
    editField(si, fi, v) {
      if (!v) return;
      const f = this.currentForm.sections[si].fields[fi];
      const prevLabel = f.label;
      f.label = v;

      // If it's a file field and modalities were not explicitly chosen,
      // keep the auto-derived modality in sync with the label.
      if (f.type === 'file') {
        const mods = Array.isArray(f.constraints?.modalities) ? f.constraints.modalities : [];
        const prevTrim = String(prevLabel || '').trim();

        // Update when: none selected OR was previously auto-derived from the old label
        if (!mods.length || (mods.length === 1 && String(mods[0] || '').trim() === prevTrim)) {
          const next = (String(v || '').trim()) || f.name;
          f.constraints = { ...(f.constraints || {}), modalities: [next] };
        }
      }
    },

    enforceNumberDigitLimits(sectionIndex, fieldIndex, evt, onBlur = false) {
      const field = this.currentForm.sections[sectionIndex].fields[fieldIndex];
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
          // leave as-is; validate elsewhere
        }
      }
    },

    addSimilarField(si, fi) {
      const f = this.currentForm.sections[si].fields[fi];
      const clone = {
        ...f,
        name: `${f.name}_${Date.now()}`,
        options: f.options ? [...f.options] : [],
        constraints: f.constraints || {},
        value:
          f.type === 'radio' && f.constraints?.allowMultiple ? [] :
          (f.type === 'radio' || f.type === 'select') ? '' :
          (f.type === 'slider' ? null :
          (f.type === 'file' ? null : f.value))
      };
      this.currentForm.sections[si].fields.splice(fi + 1, 0, clone);
    },
    removeField(si, fi) { this.currentForm.sections[si].fields.splice(fi, 1); },

    openConstraintsDialog(si, fi) {
      const f = this.currentForm.sections[si].fields[fi];
      this.currentFieldIndices = { sectionIndex: si, fieldIndex: fi };
      this.currentFieldType = f.type === 'slider' ? 'slider' : f.type;

      this.constraintsForm = {
        ...(f.constraints || {}),
        type: this.currentFieldType,
        options: (f.type === 'select' || f.type === 'radio') ? (f.options || []) : undefined,
        dateFormat: f.type === 'date'
          ? (f.constraints?.dateFormat || 'dd.MM.yyyy')
          : undefined,
        ...(f.type === 'slider' ? {
          mode: f.constraints?.mode === 'linear' ? 'linear' : 'slider',
          min: Number.isFinite(f.constraints?.min) ? f.constraints.min : 1,
          max: Number.isFinite(f.constraints?.max) ? f.constraints.max : 100,
          step: Number.isFinite(f.constraints?.step) ? f.constraints.step : 1,
          percent: !!f.constraints?.percent
        } : {})
        // file-specific keys already present in f.constraints (allowedFormats, maxSizeMB, etc.)
      };
      this.showConstraintsDialog = true;
    },
    confirmConstraintsDialog(c) {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices;
      const f = this.currentForm.sections[sectionIndex].fields[fieldIndex];
      const originalType = f.type;

      if (originalType === 'file') {
        // Assign cleaned constraints as emitted by FieldConstraintsDialog
        const cleaned = {
          helpText: c.helpText || "",
          required: !!c.required,
          readonly: !!c.readonly,
          allowedFormats: Array.isArray(c.allowedFormats) ? c.allowedFormats : [],
          maxSizeMB: (Number.isFinite(c.maxSizeMB) && c.maxSizeMB > 0) ? Number(c.maxSizeMB) : undefined,
          storagePreference: (c.storagePreference === 'url') ? 'url' : 'local',
          modalities: Array.isArray(c.modalities)
            ? c.modalities.filter(Boolean).map(String)
            : [],
          allowMultipleFiles: c.allowMultipleFiles !== false // default true
        };

        // If user hasn’t selected any modality, default to field label
        if (!cleaned.modalities.length) {
          const fallback = (String(f.label || '').trim()) || f.name;
          cleaned.modalities = [fallback];
          console.log("[ScratchForm] Constraints: defaulted modalities to", cleaned.modalities, "for", fallback);
        }

        f.constraints = cleaned;
        // Keep current value as-is; builder doesn’t persist files
        this.showConstraintsDialog = false;
        return;
      }
      // Non-slider
      if (originalType !== 'slider') {
        const norm = normalizeConstraints(originalType, c);

        // Choice types: keep existing handling
        if ((f.type === 'select' || f.type === 'radio') && Array.isArray(c.options)) {
          const cleaned = c.options.map(o => String(o || '').trim()).filter(Boolean);
          f.options = cleaned.length ? cleaned : ['Option 1'];
        }

        if (f.type === 'radio') {
          if (norm.allowMultiple) {
            if (!Array.isArray(f.value)) f.value = [];
            f.value = f.value.filter(v => f.options.includes(v));
            if (Object.prototype.hasOwnProperty.call(norm, "defaultValue")) {
              const dv = Array.isArray(norm.defaultValue) ? norm.defaultValue : [];
              f.value = dv.filter(v => f.options.includes(v));
            }
          } else {
            if (Array.isArray(f.value)) f.value = f.value[0] || '';
            if (!f.options.includes(f.value)) f.value = '';
            if (Object.prototype.hasOwnProperty.call(norm, "defaultValue")) {
              const dv = typeof norm.defaultValue === 'string' ? norm.defaultValue : '';
              f.value = f.options.includes(dv) ? dv : '';
            }
          }
        } else if (f.type === 'select') {
          if (Array.isArray(f.value)) f.value = f.value[0] || '';
          if (!f.options.includes(f.value)) f.value = '';
          if (Object.prototype.hasOwnProperty.call(norm, "defaultValue")) {
            const dv = typeof norm.defaultValue === 'string' ? norm.defaultValue : '';
            f.value = f.options.includes(dv) ? dv : '';
          }
        }

        if (Object.prototype.hasOwnProperty.call(norm, "placeholder") && f.type !== 'checkbox' && f.type !== 'file') {
          f.placeholder = norm.placeholder || "";
        }

        if (
          f.type !== 'radio' &&
          f.type !== 'select' &&
          f.type !== 'slider' &&
          f.type !== 'file' &&
          Object.prototype.hasOwnProperty.call(norm, "defaultValue")
        ) {
          const coerced = coerceDefaultForType(f.type, norm.defaultValue);
          if (coerced !== undefined) f.value = coerced;
        }

        if (f.type === 'date' && (c.dateFormat || norm.dateFormat)) {
          const fmt = c.dateFormat || norm.dateFormat;
          f.placeholder = fmt;
          norm.dateFormat = fmt;
        }

        if (originalType === 'file') {
          const fileKeys = [
            "allowedFormats","maxSizeMB","allowLocal","allowUrl","storagePreference","modalities","allowMultipleFiles"
          ];
          const extra = {};
          fileKeys.forEach(k => {
            if (Object.prototype.hasOwnProperty.call(c, k)) extra[k] = c[k];
          });
          f.constraints = { ...norm, ...extra };
        } else {
          f.constraints = { ...norm };
        }

        if (
          (f.value === '' || f.value === undefined || f.value === null) &&
          Object.prototype.hasOwnProperty.call(f.constraints, 'defaultValue') &&
          f.type !== 'file'
        ) {
          f.value = f.constraints.defaultValue;
        }

        this.showConstraintsDialog = false;
        return;
      }

      // Slider -> Linear mode
      if (c.mode === 'linear') {
        let min = Number.isFinite(+c.min) ? Math.round(+c.min) : 1;
        let max = Number.isFinite(+c.max) ? Math.round(+c.max) : 5;
        if (max <= min) max = min + 1;
        if (max - min + 1 > 10) max = min + 9;

        f.constraints = {
          mode: 'linear',
          required: !!c.required,
          readonly: !!c.readonly,
          helpText: c.helpText || '',
          min, max,
          leftLabel: c.leftLabel || '',
          rightLabel: c.rightLabel || ''
        };
        f.value = null;
        this.showConstraintsDialog = false;
        return;
      }

      // Slider -> Slider mode
      let min = Number.isFinite(+c.min) ? +c.min : 1;
      let max = Number.isFinite(+c.max) ? +c.max : (c.percent ? 100 : 5);
      if (max <= min) max = min + 1;
      let step = Number.isFinite(+c.step) && +c.step > 0 ? +c.step : (c.percent ? 1 : 1);

      f.constraints = {
        mode: 'slider',
        required: !!c.required,
        readonly: !!c.readonly,
        helpText: c.helpText || '',
        percent: !!c.percent,
        min, max, step,
        marks: Array.isArray(c.marks) ? c.marks : []
      };

      const v = Number(f.value);
      f.value = Number.isFinite(v) && v >= min && v <= max ? v : null;
      this.showConstraintsDialog = false;
    },

    cancelConstraintsDialog() { this.showConstraintsDialog = false; },

    downloadFormData() {
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
      a.href = url; a.download = name; a.click();
      URL.revokeObjectURL(url);
    },

    openUploadDialog() { this.showUploadDialog = true; },
    closeUploadDialog() { this.showUploadDialog = false; },
    handleFileChange(e) {
      const file = e.target.files[0];
      if (!file) return this.openGenericDialog("No file selected.");
      const reader = new FileReader();
      reader.onload = evt => {
        try {
          const pd = JSON.parse(evt.target.result);
          if (Array.isArray(pd.sections)) {
            pd.sections = pd.sections.map(sec => ({
              ...sec,
              fields: sec.fields.map(field => ({
                ...field,
                constraints: field.constraints || {}
              }))
            }));
            this.currentForm.sections = pd.sections;
            this.adjustAssignments();
          } else throw new Error("Bad format");
        } catch (err) {
          console.error(err);
          this.openGenericDialog("Invalid file. Expect `{ \"sections\": [...] }`.");
        }
      };
      reader.readAsText(file);
      this.showUploadDialog = false;
    },

    async loadDataModels() {
      try {
        const res = await fetch("/template_schema.yaml")
        const doc = yaml.load(await res.text())
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
          }))
      } catch (e) { console.error("Failed to load data models:", e) }
    },
    resolveType(def) {
      const ui = def.ui || {}
      const dt = String(def.datatype || '').toLowerCase()
      const range = String(def.range || '').toLowerCase()
      if (ui.widget === 'textarea' || dt === 'textarea') return 'textarea'
      if (ui.widget === 'radio'    || dt === 'radio')    return 'radio'
      if (ui.widget === 'dropdown' || dt === 'dropdown' || def.enum) return 'select'
      if (range === 'date' || range === 'datetime') return 'date'
      if (['integer','decimal','number'].includes(range)) return 'number'
      if (ui.widget === 'file' || dt === 'file' || range === 'file') return 'file'
      return 'text'
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
    },
  }
};
</script>

<style lang="scss" scoped>
@import "@/assets/styles/_base.scss";

.create-form-container {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  background-color: $light-background;
}

.header-container {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.btn-back {
  @include button-reset;
  font-size: 16px;
  color: $text-color;
}

.scratch-form-content {
  display: flex;
  gap: 20px;
}

/* AVAILABLE FIELDS */
.available-fields {
  width: 300px;
  background: white;
  padding: 20px;
  border: 1px solid $border-color;
  border-radius: 8px;
  /* don't scroll whole sidebar */
  max-height: none;
  overflow: visible;
}

.available-fields-search {
  margin: 0 0 12px 0;
  display: flex;
  justify-content: center;
}
.search-input {
  width: 94%;
  padding: 8px 10px;
  border: 1px solid $border-color;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
}
.search-input:focus {
  outline: none;
  border-color: $primary-color;
  box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
}

/* Wrap tabs to prevent overflow & SHACL breakage */
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.tabs button {
  padding: 8px;
  border: 1px solid $border-color;
  background: $secondary-color;
  border-radius: 6px;
  flex: 1 1 48%;
  min-width: 120px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1.2;
  white-space: normal;
  word-wrap: break-word;
}
.tabs button.active {
  background: $primary-color;
  color: white;
  border: none;
}

.template-fields,
.custom-fields,
.shacl,
.obi-fields {
  padding: 10px 0;
}

/* Scroll area for lists (template & OBI) only) */
.tab-results {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px; /* keep scrollbar off text */
}

/* TEMPLATE */
.template-instruction {
  font-style: italic;
  margin-bottom: 10px;
}
.template-button { display:flex; flex-direction:column; align-items:flex-start; justify-content:flex-start; width:100%; padding:10px 12px; margin:6px 0; background-color:#f9fafb; border:1px solid #d1d5db; border-radius:6px; cursor:pointer; transition: background .2s, box-shadow .2s, border-color .2s; box-sizing:border-box; }
.template-button:hover { background-color:#f3f4f6; box-shadow:0 2px 6px rgba(0,0,0,0.05); }
.template-header { display:flex; align-items:center; font-weight:600; font-size:14px; color:#111827; margin-bottom:4px; gap:8px; }
.template-header i { font-size:16px; color:#374151; }
.template-description { font-size:12px; color: #6b7280; line-height:1.4; overflow-wrap:anywhere; }
.highlighted-model { border-color: $primary-color; background: #f3f6ff; }
.match-preview { margin: 6px 0 0 22px; padding-left: 14px; list-style: disc; color: #374151; font-size: 12px; }
.no-matches { margin-top: 10px; font-size: 13px; color: #6b7280; }

/* CUSTOM FIELDS */
.custom-fields .available-field-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #f0f4f8;
  border: 1px solid $border-color;
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.custom-fields .available-field-button:hover { background: #e3effd; }
.custom-fields .field-label { flex: 1; }

/* OBI styles */
.obi-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.btn-add-selected {
  background: $primary-color;
  color: white;
  padding: 6px 10px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
}
.btn-add-selected:disabled { opacity: 0.5; cursor: not-allowed; }
.obi-list { /* uses .tab-results scrolling */ }

.obi-term-row {
  margin: 8px 0;
  border-radius: 8px;
  background: #fafafa;
  border: 1px solid #e5e7eb;
  display: grid;
  grid-template-rows: auto 1fr; /* two rows */
  grid-template-columns: 1fr;   /* body spans full width in row 2 */
}

/* Row 1: tiny checkbox left */
.obi-term-top {
  padding: 6px 8px 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.obi-checkbox-small {
  width: 16px;
  height: 16px;
  accent-color: $primary-color;
}
.obi-selected-pill {
  background: #eef6ff;
  color: #0b62d6;
  border: 1px solid #cfe2ff;
  border-radius: 9999px;
  padding: 2px 8px;
  font-size: 11px;
}

/* Row 2: full result */
.obi-term-body {
  padding: 6px 10px 10px 10px;
  cursor: pointer;
}
.obi-term-label {
  font-weight: 600;
  color: #111827;
  word-break: break-word;
}
.obi-term-meta {
  font-size: 12px;
  color: #6b7280;
  margin: 2px 0 4px;
  word-break: break-all;
}
.obi-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.obi-def, .obi-syn {
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

.obi-error { color: #b91c1c; margin-top: 6px; }
.obi-empty, .obi-hint { font-size: 12px; color: #6b7280; margin-top: 6px; }

.obi-more { margin-top: 8px; display: flex; justify-content: center; }
.btn-more {
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 12px;
}
.btn-more:disabled { opacity: 0.5; cursor: not-allowed; }

.obi-count { font-size: 12px; color: #6b7280; }

/* FORM AREA */
.form-area {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: white;
  padding: 20px;
  border: 1px solid $border-color;
  border-radius: 8px;
  min-width: 600px;
  height: calc(100vh - 60px);
}

.sections-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 10px;
  position: relative;
}

.sections-list { display: block; }

.reorder-move { transition: transform 180ms ease; }

.form-section {
  padding: 15px;
  border-bottom: 1px solid $border-color;
  background: #f5f5f5;
  margin-bottom: 10px;
  border-radius: 8px;
}

.form-section.active {
  background: #e7f3ff;
  border-left: 3px solid $text-color;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.field-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* Drag handles (right-aligned) */
.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: grab;
  user-select: none;
  color: #374151;
  background: rgba(0,0,0,0.04);
}
.drag-handle:hover { background: rgba(0,0,0,0.08); }
.drag-handle:active { cursor: grabbing; }

/* Keep it visually aligned with icon buttons */
.drag-handle-right {
  margin-left: 2px;
}

.drop-before { box-shadow: 0 -3px 0 0 rgba($primary-color, 0.55) inset; }
.drop-after  { box-shadow: 0  3px 0 0 rgba($primary-color, 0.55) inset; }

.section-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-content { display:flex; flex-direction:column; gap:14px; }
.form-group {
  background: #ffffff;
  border: 1px solid $border-color;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.05s ease;
}

.field-header { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:8px; }
.field-header > label { font-weight: 600; color: #111827; line-height: 1.25; }

.icon-button {
  border:none;
  background:transparent;
  padding:6px;
  border-radius:8px;
  cursor:pointer;
  line-height:0;
  transition: background 0.15s ease, transform 0.02s ease;
}
.icon-button:hover { background: rgba(0,0,0,0.06); }
.icon-button:active { transform: scale(0.98); }
.icon-button i { font-size:14px; color:#374151; }

input, textarea, select {
  width: 96%;
  padding: 10px;
  border: 1px solid $border-color;
  border-radius: 8px;
  margin-top: 5px;
  background: #fff;
}

.help-text { display:inline-block; margin-top:6px; color:#6b7280; }

.field-drop-end {
  border: 1px dashed rgba($primary-color, 0.35);
  border-radius: 10px;
  padding: 10px;
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  background: rgba($primary-color, 0.04);
}
.field-drop-end.drop-active {
  border-color: rgba($primary-color, 0.7);
  background: rgba($primary-color, 0.08);
  color: #374151;
}

/* actions footer */
.form-actions {
  position: sticky;
  bottom: 0;
  background: white;
  padding: 15px 0;
  border-top: 1px solid $border-color;
  display: flex;
  justify-content: center;
  gap: 15px;
  z-index: 10;
}
.additional-options {
  position: relative;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.btn-ellipsis {
  background: $secondary-color;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  padding: $button-padding;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.options-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  min-width: 200px;
  background: white;
  border: 1px solid $border-color;
  border-radius: 10px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
  padding: 6px;
  z-index: 50;
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
  color: $text-color;
}

.options-item:hover {
  background: rgba(0, 0, 0, 0.06);
}
.btn-option {
  background: $secondary-color;
  padding: $button-padding;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 1;
}

.protocol-btn::after { content: ' →'; }

.btn-primary {
  background: $primary-color;
  color: white;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 1;
}

/* modals (unchanged) */
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
.modal { background:white; padding:20px; border-radius:8px; max-width:90%; max-height:90%; overflow-y:auto; }
.modal.model-dialog { width:400px; max-height:80vh; padding:20px 16px; }
.preview-modal { width:500px; height:80vh; display:flex; flex-direction:column; }
.preview-header { display:flex; justify-content:space-between; align-items:center; background:#f2f3f4; padding:10px; }
.preview-content { flex:1; background:white; padding:10px; overflow-y:auto; }
.modal-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:10px; }
.input-dialog-field { width:100%; padding:8px; margin-top:5px; }
.model-prop-list {
  margin-top: 10px;
  display: grid;
  /* Responsive 2+ columns, never too narrow */
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px 12px;
}

.prop-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  box-sizing: border-box;
  cursor: pointer;
}

.prop-cell:hover {
  background: #f3f4f6;
}

.prop-info {
  flex: 1 1 auto;
  min-width: 0;         /* allows natural wrapping, no per-letter layout */
  text-align: left;     /* force left alignment even if a parent has text-align:right */
}

.prop-label {
  display: block;
  font-weight: 600;
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
/* Fix checkbox layout in "Select Properties" dialog */
.model-prop-list .prop-checkbox {
  width: auto;        /* undo global input width */
  padding: 0;         /* no text-input padding */
  margin-top: 0;      /* align vertically with label */
  border: none;       /* remove text-input border */
  border-radius: 0;
}
.model-prop-list .prop-cell { align-items: center; }
.model-prop-list .prop-info { text-align: left; }

/* --- Model dialog target block: tighten spacing + fix checkbox sizing --- */
.model-target {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eef0f3;

  display: flex;
  flex-direction: column;
  gap: 6px;            /* was too large → made checkbox look "floating" */
}

.model-target-selection {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-target-hint {
  margin: 0;
  padding: 0;
}

/* Keep the checkbox directly below the hint/dropdown and on one line */
.model-target-check {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;

  margin: 0;          /* remove any inherited spacing */
  padding: 0;

  white-space: nowrap;        /* "Add to existing section" single line */
  overflow: hidden;
  text-overflow: ellipsis;    /* prevent wrap in narrow modal */
  line-height: 1.1;
}

/* Override global input styling that makes checkboxes huge/fuzzy */
.model-target-check input[type="checkbox"] {
  width: auto !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;

  /* optional: nicer alignment */
  transform: translateY(1px);
}

</style>
