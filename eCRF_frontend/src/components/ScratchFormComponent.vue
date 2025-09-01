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
            :class="{ active: activeTab === 'shacl' }"
            @click="activeTab = 'shacl'"
          >SHACL Components</button>
        </div>

        <!-- TEMPLATE -->
        <div v-if="activeTab === 'template'" class="template-fields">
          <p class="template-instruction">
            Click a model to pick properties
          </p>

          <div
            v-for="model in dataModels"
            :key="model.title"
            class="template-button"
            @click="openModelDialog(model)"
          >
            <div class="template-header">
              <i :class="modelIcon(model.title)"></i>
              {{ prettyModelTitle(model.title) }}
            </div>
            <div class="template-description">
              {{ model.description || "No description available." }}
            </div>
          </div>
        </div>

        <!-- CUSTOM -->
        <div v-if="activeTab === 'custom'" class="custom-fields">
          <div
            v-for="field in generalFields"
            :key="field.name || field.label"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
          >
            <i :class="field.icon"></i>
            <div class="field-info">
              <span class="field-label">{{ field.label }}</span>
            </div>
          </div>
        </div>

        <!-- SHACL -->
        <div v-if="activeTab === 'shacl'">
          <ShaclComponents :shaclComponents="shaclComponents" />
        </div>
      </div>

      <!-- ───────── Form Area / Protocol Matrix ───────── -->
      <div class="form-area">
        <div class="sections-container">
          <!-- Sections View -->
          <div v-if="!showMatrix">
            <div
              v-for="(section, si) in currentForm.sections"
              :key="si"
              class="form-section"
              :class="{ active: activeSection === si }"
              @click="onSectionClick(si)"
              :ref="'section-' + si"
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

              <div v-if="!section.collapsed" class="section-content">
                <div
                  v-for="(field, fi) in section.fields"
                  :key="fi"
                  class="form-group"
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
                      <!-- REPLACED raw input with FieldCheckbox -->
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
                        @click.stop.prevent="setActiveSection(si); removeField(si, fi)"
                      ><i :class="icons.delete"></i></button>

                      <!-- SINGLE SETTINGS BUTTON handles constraints + type-specific settings -->
                      <button
                        class="icon-button"
                        title="Settings"
                        @click.stop.prevent="setActiveSection(si); openConstraintsDialog(si, fi)"
                      ><i :class="icons.cog"></i></button>
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

                    <!-- DATE (uses real date picker component) -->
                    <DateFormatPicker
                      v-else-if="field.type === 'date'"
                      v-model="field.value"
                      :format="field.constraints?.dateFormat || 'dd.MM.yyyy'"
                      :placeholder="field.placeholder || (field.constraints?.dateFormat || 'dd.MM.yyyy')"
                      :min-date="field.constraints?.minDate || null"
                      :max-date="field.constraints?.maxDate || null"
                    />

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

                    <FieldRadioGroup
                      v-else-if="field.type === 'radio'"
                      :name="field.name"
                      :options="field.options"
                      v-model="field.value"
                    />

                    <!-- SLIDER or LINEAR based on constraints.mode -->
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
              </div>
            </div>
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
            Clear
          </button>
          <button @click.prevent="saveForm" class="btn-primary">
            Save Template
          </button>
          <button @click.prevent="downloadFormData" class="btn-option">
            Download Template
          </button>
          <button @click.prevent="openUploadDialog" class="btn-option">
            Upload Template
          </button>
          <button
            @click.prevent="handleProtocolClick"
            class="btn-option protocol-btn"
          >
            Schedule of Assessment
          </button>
        </div>
      </div>
    </div>

    <!-- ───────── Model Dialog ───────── -->
    <div v-if="showModelDialog" class="modal-overlay">
      <div class="modal model-dialog">
        <h3>Select Properties for {{ prettyModelTitle(currentModel.title) }}</h3>
        <div class="model-prop-list">
          <div
            v-for="(prop, i) in currentModel.fields"
            :key="prop.name"
            class="prop-row"
          >
            <div class="prop-info">
              <strong>{{ prop.label || prettyModelTitle(prop.name) }}</strong>
              <p v-if="prop.description" class="prop-desc">{{ prop.description }}</p>
            </div>
            <label class="prop-check">
              <input type="checkbox" :id="'prop-check-' + i" v-model="selectedProps[i]" />
            </label>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="takeoverModel" class="btn-primary">Takeover</button>
          <button @click="showModelDialog=false" class="btn-option">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- ───────── Constraints Dialog (unified) ───────── -->
    <div v-if="showConstraintsDialog" class="modal-overlay">
      <FieldConstraintsDialog
        :currentFieldType="currentFieldType"
        :constraintsForm="constraintsForm"
        @updateConstraints="confirmConstraintsDialog"
        @closeConstraintsDialog="cancelConstraintsDialog"
        @showGenericDialog="openGenericDialog"
      />
    </div>

    <!-- ───────── Preview Dialog ───────── -->
    <div v-if="showPreviewDialog" class="modal-overlay">
      <div class="modal preview-modal">
        <FormPreview :form="currentForm" />
        <div class="modal-actions">
          <button @click="closePreviewDialog" class="btn-primary">Close</button>
        </div>
      </div>
    </div>

    <!-- ───────── Upload Dialog ───────── -->
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

    <!-- ───────── Input Dialog ───────── -->
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

    <!-- ───────── Confirm Dialog ───────── -->
    <div v-if="showConfirmDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ confirmDialogMessage }}</p>
        <div class="modal-actions">
          <button @click="confirmDialogYes" class="btn-primary">Yes</button>
          <button @click="closeConfirmDialog" class="btn-option">No</button>
        </div>
      </div>
    </div>

    <!-- ───────── Generic Dialog ───────── -->
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
    FieldLinearScale
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
      inputDialogCallback: null
    };
  },
  computed: {
    icons()         { return icons; },
    studyDetails()  { return this.$store.state.studyDetails || {}; },
    currentForm()   { return this.forms[this.currentFormIndex] || { sections: [] }; },
    selectedModels(){
      return this.currentForm.sections.map(sec => ({ title: sec.title, fields: sec.fields }));
    }
  },
  watch: {
    visits: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    groups: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    selectedModels: { handler() { this.adjustAssignments(); }, immediate: true, deep: true },
    forms: {
      deep: true,
      handler(f) { localStorage.setItem("scratchForms", JSON.stringify(f)); }
    }
  },
  async mounted() {
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
      const res = await axios.get("http://127.0.0.1:8000/forms/available-fields");
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
  methods: {
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
      this.currentModel = model;
      this.selectedProps = model.fields.map(() => false);
      this.showModelDialog = true;
    },
    takeoverModel() {
      const chosen = this.currentModel.fields
        .filter((_, i) => this.selectedProps[i])
        .map(f => ({ ...f, description: f.description || "", constraints: f.constraints || {} }));
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

      // SLIDER defaults — 1..100, integer, no default value
      if (base.type === 'slider') {
        base.value = null; // no default
        base.constraints = {
          ...(base.constraints || {}),
          mode: 'slider',
          percent: false,
          min: 1,
          max: 100,
          step: 1
        };
      }

      // Date defaults
      if (base.type === 'date') {
        base.constraints = { ...base.constraints, dateFormat: base.constraints.dateFormat || 'dd.MM.yyyy' };
        base.placeholder = base.placeholder || base.constraints.dateFormat;
      }

      sec.fields.push(base);
    },

    editSection(i, v) { if (v) this.currentForm.sections[i].title = v; },
    editField(si, fi, v) { if (v) this.currentForm.sections[si].fields[fi].label = v; },

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
          (f.type === 'radio' || f.type === 'select') ? '' : f.value
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
      };
      this.showConstraintsDialog = true;
    },
    confirmConstraintsDialog(c) {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices;
      const f = this.currentForm.sections[sectionIndex].fields[fieldIndex];
      const originalType = f.type;

      // Non-slider
      if (originalType !== 'slider') {
        const norm = normalizeConstraints(originalType, c);

        if ((f.type === 'select' || f.type === 'radio') && Array.isArray(c.options)) {
          const cleaned = c.options.map(o => String(o || '').trim()).filter(Boolean);
          f.options = cleaned.length ? cleaned : ['Option 1'];
        }

        // ---------- Value shape & membership (radio/select) ----------
        if (f.type === 'radio') {
          // radios can be single or multi based on allowMultiple
          if (norm.allowMultiple) {
            // ensure array shape
            if (!Array.isArray(f.value)) f.value = [];
            // remove any values that no longer exist
            f.value = f.value.filter(v => f.options.includes(v));
            // if defaultValue provided, prefer it (array)
            if (Object.prototype.hasOwnProperty.call(norm, "defaultValue")) {
              const dv = Array.isArray(norm.defaultValue) ? norm.defaultValue : [];
              f.value = dv.filter(v => f.options.includes(v));
            }
          } else {
            // single-select: ensure scalar string
            if (Array.isArray(f.value)) f.value = f.value[0] || '';
            if (!f.options.includes(f.value)) f.value = '';
            // if defaultValue provided, prefer it (scalar)
            if (Object.prototype.hasOwnProperty.call(norm, "defaultValue")) {
              const dv = typeof norm.defaultValue === 'string' ? norm.defaultValue : '';
              f.value = f.options.includes(dv) ? dv : '';
            }
          }
        } else if (f.type === 'select') {
          // dropdown is ALWAYS single-select
          if (Array.isArray(f.value)) f.value = f.value[0] || '';
          if (!f.options.includes(f.value)) f.value = '';
          if (Object.prototype.hasOwnProperty.call(norm, "defaultValue")) {
            const dv = typeof norm.defaultValue === 'string' ? norm.defaultValue : '';
            f.value = f.options.includes(dv) ? dv : '';
          }
        }

        // ---------- Placeholder (skip for checkbox by design) ----------
        if (Object.prototype.hasOwnProperty.call(norm, "placeholder") && f.type !== 'checkbox') {
          f.placeholder = norm.placeholder || "";
        }

        if (
          f.type !== 'radio' &&
          f.type !== 'select' &&
          f.type !== 'slider' &&
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

        f.constraints = { ...norm };
        if (
          (f.value === '' || f.value === undefined || f.value === null) &&
          Object.prototype.hasOwnProperty.call(f.constraints, 'defaultValue')
        ) {
          f.value = f.constraints.defaultValue;
        }
        console.log("[SFC] saved NON-slider constraints:", { si: sectionIndex, fi: fieldIndex, constraints: f.constraints });
        this.showConstraintsDialog = false;
        return;
      }

      // Slider -> Linear mode (no marks)
      if (c.mode === 'linear') {
        console.log("[SFC] incoming LINEAR slider constraints:", c);
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
          // no marks intentionally
        };
        f.value = null; // no default
        console.log("[SFC] saved LINEAR slider constraints:", { si: sectionIndex, fi: fieldIndex, constraints: f.constraints });
        this.showConstraintsDialog = false;
        return;
      }

      // Slider -> Slider mode (KEEP MARKS)
      console.log("[SFC] incoming SLIDER constraints:", c);
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
        // ← IMPORTANT: keep marks so FieldSlider can render them
        marks: Array.isArray(c.marks) ? c.marks : []
      };

      const v = Number(f.value);
      f.value = Number.isFinite(v) && v >= min && v <= max ? v : null;
      console.log("[SFC] saved SLIDER constraints:", { si: sectionIndex, fi: fieldIndex, constraints: f.constraints });
      this.showConstraintsDialog = false;
    },

    cancelConstraintsDialog() { this.showConstraintsDialog = false; },

    saveForm() { this.openGenericDialog("Saved!"); },

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
      return 'text'
    }
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
  max-height: calc(100vh - 60px);
  overflow-y: auto;
  overflow-x: hidden;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.tabs button {
  padding: 10px;
  border: 1px solid $border-color;
  background: $secondary-color;
  border-radius: 4px;
  flex: 1;
  cursor: pointer;
}

.tabs button.active {
  background: $primary-color;
  color: white;
  border: none;
}

.template-fields,
.custom-fields,
.shacl {
  padding: 10px 0;
}

.template-instruction {
  font-style: italic;
  margin-bottom: 10px;
}

.class-item.clickable {
  cursor: pointer;
  padding: 5px 0;
  font-weight: bold;
}

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
.custom-fields .available-field-button:hover {
  background: #e3effd;
}
.custom-fields .field-label {
  flex: 1;
}

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

.section-content {
  display: flex;           /* vertical list */
  flex-direction: column;
  gap: 14px;               /* spacing between field cards */
}

/* Field "cards" */
.form-group {
  background: #ffffff;
  border: 1px solid $border-color;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.05s ease;
}
.form-group:hover {
  border-color: rgba(0,0,0,0.12);
  box-shadow: 0 6px 12px rgba(0,0,0,0.06);
}
.form-group:focus-within {
  border-color: rgba($primary-color, 0.6);
  box-shadow: 0 0 0 3px rgba($primary-color, 0.12);
}

/* Header inside each card */
.field-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.field-header > label {
  font-weight: 600;
  color: #111827;
  line-height: 1.25;
}

/* Small icon-only buttons for field actions */
.icon-button {
  border: none;
  background: transparent;
  padding: 6px;
  border-radius: 8px;
  cursor: pointer;
  line-height: 0;
  transition: background 0.15s ease, transform 0.02s ease;
}
.icon-button:hover { background: rgba(0,0,0,0.06); }
.icon-button:active { transform: scale(0.98); }
.icon-button i { font-size: 14px; color: #374151; }

/* Compact actions row */
.field-actions {
  display: flex;
  gap: 6px;
}

/* Input area in the card */
.field-box {
  margin-top: 6px;
}

/* Radios & checkboxes styling preserved */
.field-header .checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.field-header .checkbox-label input[type="checkbox"] {
  display: block !important;
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
  border: 2px solid #ccc;
  border-radius: 4px;
  background-color: #fff;
  appearance: none;
  position: relative;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.field-header .checkbox-label input[type="checkbox"]:checked {
  background-color: #444;
  border-color: #444;
}

.field-header .checkbox-label input[type="checkbox"]:checked::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 5px;
  width: 4px;
  height: 8px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.field-header .checkbox-label input[type="checkbox"]:hover:not(:checked) {
  border-color: #666;
}

.field-box .radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.field-box .radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-box .radio-label input[type="radio"],
.field-box .radio-label input[type="checkbox"] {
  display: block !important;
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
  border: 2px solid #ccc;
  border-radius: 50%;
  background-color: #fff;
  appearance: none;
  position: relative;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.field-box .radio-label input[type="radio"]:checked,
.field-box .radio-label input[type="checkbox"]:checked {
  background-color: #444;
  border-color: #444;
}

.field-box .radio-label input[type="radio"]:checked::after {
  content: '';
  position: absolute;
  top: 4px;
  left: 4px;
  width: 8px;
  height: 8px;
  background: #fff;
  border-radius: 50%;
}

.field-box .radio-label input[type="checkbox"]:checked::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 5px;
  width: 4px;
  height: 8px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.field-box .radio-label input[type="radio"]:hover:not(:checked),
.field-box .radio-label input[type="checkbox"]:hover:not(:checked) {
  border-color: #666;
}

/* Inputs in cards */
input,
textarea,
select {
  width: 100%;
  padding: 10px;
  border: 1px solid $border-color;
  border-radius: 8px;
  margin-top: 5px;
  background: #fff;
}

textarea {
  resize: vertical;
}

/* Help text inside cards */
.help-text {
  display: inline-block;
  margin-top: 6px;
  color: #6b7280;
}

/* FORM ACTIONS */
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

.btn-option {
  background: $secondary-color;
  padding: $button-padding;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 1;
}

.protocol-btn::after {
  content: ' →';
}

.btn-primary {
  background: $primary-color;
  color: white;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 1;
}

/* MODALS */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  max-width: 90%;
  max-height: 90%;
  overflow-y: auto;
}

.modal.model-dialog {
  width: 400px;
  max-height: 80vh;
  padding: 20px 16px;
}

.preview-modal {
  width: 500px;
  height: 80vh;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f2f3f4;
  padding: 10px;
}

.preview-content {
  flex: 1;
  background: white;
  padding: 10px;
  overflow-y: auto;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.input-dialog-field {
  width: 100%;
  padding: 8px;
  margin-top: 5px;
}

/* Template buttons */
.template-button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  width: 100%;
  padding: 10px 12px;
  margin: 6px 0;
  background-color: #f9fafb;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.template-button:hover {
  background-color: #f3f4f6;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.template-header {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  color: #111827;
  margin-bottom: 4px;
}

.template-header i {
  margin-right: 8px;
  font-size: 16px;
  color: #374151;
}

.template-description {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
</style>
