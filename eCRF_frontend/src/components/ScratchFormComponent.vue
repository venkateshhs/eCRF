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
            class="available-section"
            @click="openModelDialog(model)"
          >
            <h4>{{ model.title }}</h4>
            <p class="model-description">
              {{ model.description || "No description available." }}
            </p>
          </div>
        </div>

        <!-- CUSTOM -->
        <div v-if="activeTab === 'custom'" class="custom-fields">
          <div
            v-for="field in generalFields"
            :key="field.name"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
          >
            <i :class="field.icon"></i>
            <div class="field-info">
              <span class="field-label">{{ field.label }}</span>
              <small class="field-desc">{{ field.description }}</small>
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
              @click.self="setActiveSection(si)"
              :ref="'section-' + si"
            >
              <div class="section-header">
                <h3>{{ section.title }}</h3>
                <div class="field-actions">
                  <button
                    class="icon-button"
                    title="Edit Section Title"
                    @click.prevent="openInputDialog(
                      'Enter new section title:',
                      section.title,
                      val => editSection(si, val)
                    )"
                  ><i :class="icons.edit"></i></button>
                  <button
                    class="icon-button"
                    title="Add Section Below"
                    @click.prevent="addNewSectionBelow(si)"
                  ><i :class="icons.add"></i></button>
                  <button
                    class="icon-button"
                    title="Delete Section"
                    @click.prevent="confirmDeleteSection(si)"
                  ><i :class="icons.delete"></i></button>
                  <button
                    class="icon-button"
                    :title="section.collapsed ? 'Expand' : 'Collapse'"
                    @click.prevent="toggleSection(si)"
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
                    <label v-if="field.type !== 'button'" :for="field.name">
                      {{ field.label }}
                    </label>
                    <div class="field-actions">
                      <button
                        class="icon-button"
                        title="Edit Field Label"
                        @click.prevent="openInputDialog(
                          'Enter new field label:',
                          field.label,
                          val => editField(si, fi, val)
                        )"
                      ><i :class="icons.edit"></i></button>
                      <button
                        class="icon-button"
                        title="Add Similar Field"
                        @click.prevent="addSimilarField(si, fi)"
                      ><i :class="icons.add"></i></button>
                      <button
                        class="icon-button"
                        title="Delete Field"
                        @click.prevent="removeField(si, fi)"
                      ><i :class="icons.delete"></i></button>
                      <button
                        class="icon-button"
                        title="Edit Constraints"
                        @click.prevent="openConstraintsDialog(si, fi)"
                      ><i :class="icons.cog"></i></button>
                    </div>
                  </div>
                  <div class="field-box">
                    <!-- TEXT -->
                    <input
                      v-if="field.type==='text'"
                      type="text"
                      v-model="field.value"
                      :placeholder="field.constraints.placeholder || field.placeholder"
                    />
                    <!-- TEXTAREA -->
                    <textarea
                      v-else-if="field.type==='textarea'"
                      v-model="field.value"
                      :rows="field.rows||3"
                      :placeholder="field.constraints.placeholder || field.placeholder"
                    ></textarea>
                    <!-- NUMBER -->
                    <input
                      v-else-if="field.type==='number'"
                      type="number"
                      v-model.number="field.value"
                      :min="field.constraints.min"
                      :max="field.constraints.max"
                      :step="field.constraints.step"
                    />
                    <!-- DATE -->
                    <input
                      v-else-if="field.type==='date'"
                      type="date"
                      v-model="field.value"
                      :min="field.constraints.minDate"
                      :max="field.constraints.maxDate"
                    />
                    <!-- SELECT -->
                    <select
                      v-else-if="field.type==='select'"
                      v-model="field.value"
                    >
                      <option value="" disabled>Select…</option>
                      <option v-for="opt in field.options" :key="opt">{{ opt }}</option>
                    </select>
                    <!-- BUTTON -->
                    <button
                      v-else-if="field.type==='button'"
                      class="form-button"
                    >{{ field.label }}</button>
                    <small v-if="field.constraints.helpText" class="help-text">
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
            Protocol Matrix
          </button>
        </div>
      </div>
    </div>

    <!-- ───────── Model Dialog ───────── -->
    <div v-if="showModelDialog" class="modal-overlay">
      <div class="modal model-dialog">
        <h3>Select Properties for {{ currentModel.title }}</h3>
        <div class="model-prop-list">
          <div
            v-for="(prop, i) in currentModel.fields"
            :key="prop.name"
            class="prop-row"
          >
            <div class="prop-info">
              <strong>{{ prop.name }}</strong> —
              {{ prop.label }}
              <p class="prop-desc">{{ prop.description }}</p>
            </div>
            <div class="prop-check">
              <input type="checkbox" v-model="selectedProps[i]" />
            </div>
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

    <!-- ───────── Constraints Dialog ───────── -->
    <div v-if="showConstraintsDialog" class="modal-overlay">
      <FieldConstraintsDialog
        :currentFieldType="currentFieldType"
        :constraintsForm="constraintsForm"
        @updateConstraints="confirmConstraintsDialog"
        @closeConstraintsDialog="cancelConstraintsDialog"
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

export default {
  name: "ScratchFormComponent",

  components: {
    ShaclComponents,
    ProtocolMatrix,
    FieldConstraintsDialog,
    FormPreview
  },

  data() {
    return {
      // sections & form state
      forms: JSON.parse(localStorage.getItem("scratchForms") || "[]"),
      currentFormIndex: 0,
      activeSection: 0,

      // tabs / available fields
      activeTab: "template",
      generalFields: [],
      dataModels: [],

      // model dialog
      showModelDialog: false,
      currentModel: null,
      selectedProps: [],

      // protocol matrix
      showMatrix: false,
      visits: [],
      groups: [],
      assignments: [],

      // confirm / generic dialogs
      showConfirmDialog: false,
      confirmDialogMessage: "",
      confirmCallback: null,
      showGenericDialog: false,
      genericDialogMessage: "",
      genericCallback: null,

      // constraints
      showConstraintsDialog: false,
      constraintsForm: {},
      currentFieldType: "",
      currentFieldIndices: {},

      // preview
      showPreviewDialog: false,

      // upload
      showUploadDialog: false,

      // input
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
      return this.currentForm.sections.map(sec => ({
        title:  sec.title,
        fields: sec.fields
      }));
    }
  },

  watch: {
    visits:         { handler: "initAssignments", immediate: true },
    groups:         { handler: "initAssignments", immediate: true },
    selectedModels: { handler: "initAssignments", immediate: true },
    forms: {
      deep: true,
      handler(f) {
        localStorage.setItem("scratchForms", JSON.stringify(f));
      }
    }
  },

  async mounted() {
    // ─── New vs Edit: clear old scratch‐forms on NEW study
    console.log("this.studyDetails", this.studyDetails)
    if (this.studyDetails.study_metadata?.id) {
      // Editing an existing study: load from localStorage or fallback
      const stored = localStorage.getItem("scratchForms");
      console.log("scratchForms", stored)
      if (stored) {
        try {
          this.forms = JSON.parse(stored);
        } catch {
          this.forms = [{ sections: [] }];
        }
      } else if (Array.isArray(this.studyDetails.forms)) {
        // fallback to Vuex payload (if you committed `forms` there)
        this.forms = JSON.parse(JSON.stringify(this.studyDetails.forms));
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      } else {
        this.forms = [{ sections: [] }];
        localStorage.setItem("scratchForms", JSON.stringify(this.forms));
      }
    } else {
      // New study: clear any leftover and start fresh
      localStorage.removeItem("scratchForms");
      this.forms = [{ sections: [] }];
    }
    // load visits/groups
    this.visits = Array.isArray(this.studyDetails.visits)
      ? this.studyDetails.visits : [];
    this.groups = Array.isArray(this.studyDetails.groups)
      ? this.studyDetails.groups : [];

    // fetch custom fields
    try {
      const res = await axios.get(
        "http://127.0.0.1:8000/forms/available-fields"
      );
      this.generalFields = res.data.map(f => ({
        ...f,
        description: f.helpText || f.placeholder || ""
      }));
    } catch (e) {
      console.error("Failed to load custom fields", e);
    }

    // load data models from YAML
    await this.loadDataModels();
  },

  methods: {
    // ── Navigation & dialogs ──
    goBack() { this.$router.back() },

    openConfirmDialog(msg, cb) {
      this.confirmDialogMessage = msg;
      this.confirmCallback       = cb;
      this.showConfirmDialog     = true;
    },
    confirmDialogYes() {
      this.showConfirmDialog = false;
      this.confirmCallback && this.confirmCallback();
    },
    closeConfirmDialog() {
      this.showConfirmDialog = false;
    },

    openGenericDialog(msg, cb) {
      this.genericDialogMessage = msg;
      this.genericCallback      = cb;
      this.showGenericDialog    = true;
    },
    closeGenericDialog() {
      this.showGenericDialog = false;
      this.genericCallback && this.genericCallback();
    },

    openInputDialog(msg, def, cb) {
      this.inputDialogMessage  = msg;
      this.inputDialogValue    = def;
      this.inputDialogCallback = cb;
      this.showInputDialog     = true;
    },
    confirmInputDialog() {
      this.showInputDialog = false;
      this.inputDialogCallback && this.inputDialogCallback(this.inputDialogValue);
    },
    cancelInputDialog() {
      this.showInputDialog = false;
    },

    // ── Protocol Matrix ──
    initAssignments() {
      const m = this.selectedModels.length,
            v = this.visits.length,
            g = this.groups.length;
      this.assignments = Array.from({ length: m }, () =>
        Array.from({ length: v }, () =>
          Array.from({ length: g }, () => false)
        )
      );
    },
    handleProtocolClick() { this.showMatrix = true },
    editTemplate()       { this.showMatrix = false },
    onAssignmentUpdated({ mIdx, vIdx, gIdx, checked }) {
      this.assignments[mIdx][vIdx][gIdx] = checked;
    },

    // ── Sections & Fields ──
    focusSection(i) {
      this.$nextTick(() => {
        const sectionRef = this.$refs[`section-${i}`];
        if (sectionRef && sectionRef[0]) {
          sectionRef[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    },

    openModelDialog(model) {
      this.currentModel    = model;
      this.selectedProps   = model.fields.map(() => false);
      this.showModelDialog = true;
    },
    takeoverModel() {
      const chosen = this.currentModel.fields
        .filter((_, i) => this.selectedProps[i])
        .map(f => ({ ...f, description: f.description || "" }));
      const sec = {
        title:     this.currentModel.title,
        fields:    chosen,
        collapsed: false,
        source:    "template"
      };
      const idx = this.activeSection + 1;
      this.forms[this.currentFormIndex].sections.splice(idx, 0, sec);
      this.activeSection   = idx;
      this.showModelDialog = false;
      this.initAssignments();
      this.focusSection(idx);
      this.$forceUpdate();
    },

    addNewSection() {
      const sec = {
        title:     `Section ${this.currentForm.sections.length + 1}`,
        fields:    [],
        collapsed: false,
        source:    "manual"
      };
      this.forms[this.currentFormIndex].sections.push(sec);
      this.activeSection = this.currentForm.sections.length - 1;
      this.initAssignments();
      this.focusSection(this.activeSection);
      this.$forceUpdate();
    },
    addNewSectionBelow(i) {
      const currentSection = this.currentForm.sections[i];
      const sec = {
        title:     `${currentSection.title} (Copy)`,
        fields:    currentSection.fields.map(field => ({
          ...field,
          name: `${field.name}_${Date.now()}`
        })),
        collapsed: false,
        source:    currentSection.source
      };
      const idx = i + 1;
      this.forms[this.currentFormIndex].sections.splice(idx, 0, sec);
      this.activeSection = idx;
      this.initAssignments();
      this.focusSection(idx);
      this.$forceUpdate();
    },

    confirmDeleteSection(i) {
      this.openConfirmDialog("Delete this section?", () => {
        this.currentForm.sections.splice(i, 1);
        this.activeSection = Math.max(0, this.activeSection - 1);
        this.initAssignments();
      });
    },

    confirmClearForm() {
      this.openConfirmDialog(
        "Do you want to clear all sections?",
        () => {
          this.forms[this.currentFormIndex].sections = [];
          this.activeSection = 0;
          this.initAssignments();
          this.$forceUpdate();
        }
      );
    },

    toggleSection(i) {
      const section = this.forms[this.currentFormIndex].sections[i];
      section.collapsed = !section.collapsed;
      if (!section.collapsed) {
        this.activeSection = i;
        this.forms[this.currentFormIndex].sections.forEach((s, idx) => {
          if (idx !== i) s.collapsed = true;
        });
        this.focusSection(i);
      }
      this.$forceUpdate();
    },
    setActiveSection(i) {
      this.activeSection = i;
      this.forms[this.currentFormIndex].sections.forEach((s, idx) => {
        s.collapsed = idx !== i;
      });
      this.focusSection(i);
      this.$forceUpdate();
    },

    addFieldToActiveSection(field) {
      if (!this.currentForm.sections.length) {
        this.addNewSection();
      }
      const sec = this.currentForm.sections[this.activeSection];
      if (sec.collapsed) this.toggleSection(this.activeSection);

      sec.fields.push({
        name:        `${field.name}_${Date.now()}`,
        label:       field.label,
        type:        field.type,
        options:     field.options || [],
        placeholder: field.description || field.placeholder,
        value:       "",
        constraints: { ...field.constraints }
      });
    },

    editSection(i, v) {
      if (v) this.currentForm.sections[i].title = v;
    },
    editField(si, fi, v) {
      if (v) this.currentForm.sections[si].fields[fi].label = v;
    },
    addSimilarField(si, fi) {
      const f     = this.currentForm.sections[si].fields[fi];
      const clone = { ...f, name: `${f.name}_${Date.now()}` };
      this.currentForm.sections[si].fields.splice(fi + 1, 0, clone);
    },
    removeField(si, fi) {
      this.currentForm.sections[si].fields.splice(fi, 1);
    },

    openConstraintsDialog(si, fi) {
      const f = this.currentForm.sections[si].fields[fi];
      this.currentFieldIndices   = { sectionIndex: si, fieldIndex: fi };
      this.currentFieldType      = f.type;
      this.constraintsForm       = { ...f.constraints };
      this.showConstraintsDialog = true;
    },
    confirmConstraintsDialog(c) {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices;
      const f = this.currentForm.sections[sectionIndex].fields[fieldIndex];
      f.constraints = { ...c };
      this.showConstraintsDialog = false;
    },
    cancelConstraintsDialog() {
      this.showConstraintsDialog = false;
    },

    // ── Save / Download / Upload ──
    saveForm() {
      this.openGenericDialog("Saved!");
      // … your existing save logic …
    },

    downloadFormData() {
      const payload = {
        sections: this.currentForm.sections.map(sec => ({
          title:  sec.title,
          fields: sec.fields,
          source: sec.source
        }))
      };
      const str  = JSON.stringify(payload, null, 2),
            name = "sections.json";
      const blob = new Blob([str], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    },

    openUploadDialog() {
      this.showUploadDialog = true;
    },
    closeUploadDialog() {
      this.showUploadDialog = false;
    },
    handleFileChange(e) {
      const file = e.target.files[0];
      if (!file) {
        this.openGenericDialog("No file selected.");
        return;
      }
      const reader = new FileReader();
      reader.onload = evt => {
        try {
          const pd = JSON.parse(evt.target.result);
          if (Array.isArray(pd.sections)) {
            this.currentForm.sections = pd.sections;
            this.initAssignments();
          } else {
            throw new Error("Bad format");
          }
        } catch (err) {
          console.error(err);
          this.openGenericDialog(
            "Invalid file. Expect `{ \"sections\": [...] }`."
          );
        }
      };
      reader.readAsText(file);
      this.showUploadDialog = false;
    },

    // ── Load YAML Models ──
    async loadDataModels() {
      try {
        const res = await fetch("/study_schema.yaml");
        const doc = yaml.load(await res.text());
        this.dataModels = Object.entries(doc.classes)
          .filter(([n]) => n !== "Study")
          .map(([n, cls]) => ({
            title:       n,
            description: cls.description || "",
            fields: Object.entries(cls.attributes).map(([attr, def]) => ({
              name:        attr,
              label:       def.label || attr,
              description: def.description || "",
              type:        this.resolveType(def),
              options:     def.enum || [],
              constraints: { required: !!def.required },
              placeholder: def.description || ""
            }))
          }));
      } catch (e) {
        console.error("Failed to load data models:", e);
      }
    },
    resolveType(def) {
      const r = (def.range || "").toLowerCase();
      if (r === "date" || r === "datetime") return "date";
      if (["integer", "decimal"].includes(r)) return "number";
      if (def.enum) return "select";
      return "text";
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

.available-section {
  margin-bottom: 8px;
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
  background: #f5f5f5; /* Light gray background for non-active sections */
  margin-bottom: 10px; /* Added padding between sections */
}

.form-section.active {
  background: #e7f3ff;
  border-left: 3px solid $text-color;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-actions {
  display: flex;
  gap: 10px;
}

.field-box {
  margin-top: 10px;
}

input,
textarea,
select {
  width: 100%;
  padding: 8px;
  border: 1px solid $border-color;
  border-radius: 5px;
  margin-top: 5px;
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

.prop-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.prop-info {
  flex: 1;
  margin-right: 12px;
}

.prop-name {
  font-weight: bold;
}

.prop-desc {
  font-size: 0.9em;
  color: #666;
  margin-top: 4px;
}

.prop-check {
  flex-shrink: 0;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .scratch-form-content {
    flex-direction: column;
  }
  .form-area,
  .available-fields {
    width: 100%;
  }
}
</style>