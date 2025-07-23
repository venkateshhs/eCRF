<template>
  <div class="create-form-container">
    <!-- Header -->
    <div class="header-container">
      <button @click="goBack" class="btn-back" title="Go Back">
        <i :class="icons.back"></i> Back
      </button>
    </div>

    <div class="scratch-form-content">
      <!-- Available Fields -->
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
          <p class="template-instruction">Click class name to view attributes</p>
          <div
            v-for="(model, idx) in dataModels"
            :key="idx"
            class="available-section"
          >
            <div
              class="class-item clickable"
              @click="openModelDialog(model)"
            >
              {{ model.title }}
            </div>
          </div>
        </div>

        <!-- CUSTOM -->
        <div v-if="activeTab === 'custom'" class="custom-fields">
          <div
            v-for="(field, index) in generalFields"
            :key="index"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
          >
            <i :class="field.icon"></i>
            <span class="field-label">{{ field.label }}</span>
          </div>
        </div>

        <!-- SHACL -->
        <div v-if="activeTab === 'shacl'">
          <ShaclComponents :shaclComponents="shaclComponents" />
        </div>
      </div>

      <!-- Form Area -->
      <div class="form-area">
        <div class="sections-container">
          <!-- Sections or Protocol Matrix -->
          <div v-if="!showMatrix">
            <!-- Sections -->
            <div
              v-for="(section, si) in currentForm.sections"
              :key="si"
              class="form-section"
              :class="{ active: activeSection === si }"
              @click.self="setActiveSection(si)"
              tabindex="0"
            >
              <div class="section-header">
                <h3>{{ section.title }}</h3>
                <div class="field-actions">
                  <button
                    class="icon-button"
                    title="Edit Section Title"
                    @click.prevent="openInputDialog(
                      'Enter a new title for this section:',
                      section.title,
                      val => editSection(si, val)
                    )"
                  ><i :class="icons.edit"></i></button>
                  <button
                    class="icon-button"
                    title="Add New Section Below"
                    @click.prevent="addNewSectionBelow(si)"
                  ><i :class="icons.add"></i></button>
                  <button
                    class="icon-button"
                    title="Delete Section"
                    @click.prevent="confirmDeleteSection(si)"
                  ><i :class="icons.delete"></i></button>
                  <button
                    class="icon-button"
                    :title="section.collapsed ? 'Expand Section' : 'Collapse Section'"
                    @click.prevent="toggleSection(si)"
                  ><i :class="section.collapsed ? icons.toggleDown : icons.toggleUp"></i></button>
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
                          'Enter new label for the field:',
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
                        title="Edit Field Constraints"
                        @click.prevent="openConstraintsDialog(si, fi)"
                      ><i :class="icons.cog"></i></button>
                    </div>
                  </div>
                  <div class="field-box">
                    <input
                      v-if="field.type === 'text'"
                      type="text"
                      :id="field.name"
                      v-model="field.value"
                      :placeholder="field.constraints?.placeholder || field.placeholder"
                      :required="field.constraints?.required"
                      :readonly="field.constraints?.readonly"
                      :minlength="field.constraints?.minLength"
                      :maxlength="field.constraints?.maxLength"
                      :pattern="field.constraints?.pattern"
                    />
                    <textarea
                      v-else-if="field.type === 'textarea'"
                      :id="field.name"
                      v-model="field.value"
                      :placeholder="field.constraints?.placeholder || field.placeholder"
                      :required="field.constraints?.required"
                      :readonly="field.constraints?.readonly"
                      :minlength="field.constraints?.minLength"
                      :maxlength="field.constraints?.maxLength"
                      :pattern="field.constraints?.pattern"
                      :rows="field.rows"
                    ></textarea>
                    <input
                      v-else-if="field.type === 'number'"
                      type="number"
                      :id="field.name"
                      v-model="field.value"
                      :placeholder="field.constraints?.placeholder || field.placeholder"
                      :required="field.constraints?.required"
                      :readonly="field.constraints?.readonly"
                      :min="field.constraints?.min"
                      :max="field.constraints?.max"
                      :step="field.constraints?.step"
                    />
                    <input
                      v-else-if="field.type === 'date'"
                      type="date"
                      :id="field.name"
                      v-model="field.value"
                      :placeholder="field.constraints?.placeholder || field.placeholder"
                      :required="field.constraints?.required"
                      :readonly="field.constraints?.readonly"
                      :min="field.constraints?.minDate"
                      :max="field.constraints?.maxDate"
                    />
                    <select
                      v-else-if="field.type === 'select'"
                      :id="field.name"
                      v-model="field.value"
                      :required="field.constraints?.required"
                    >
                      <option
                        v-for="opt in field.options"
                        :key="opt"
                        :value="opt"
                      >{{ opt }}</option>
                    </select>
                    <div
                      v-else-if="field.type === 'checkbox'"
                      class="checkbox-group"
                    >
                      <label v-for="(opt, i) in field.options" :key="i">
                        <input
                          type="checkbox"
                          v-model="field.value"
                          :value="opt"
                          :required="field.constraints?.required"
                          :readonly="field.constraints?.readonly"
                        /> {{ opt }}
                      </label>
                    </div>
                    <div
                      v-else-if="field.type === 'radio'"
                      class="radio-group"
                    >
                      <label v-for="opt in field.options" :key="opt">
                        <input
                          type="radio"
                          :name="field.name"
                          v-model="field.value"
                          :value="opt"
                          :required="field.constraints?.required"
                        /> {{ opt }}
                      </label>
                    </div>
                    <button
                      v-else-if="field.type === 'button'"
                      type="button"
                      class="form-button"
                    >
                      {{ field.label }}
                    </button>
                    <small
                      v-if="field.constraints?.helpText"
                      class="help-text"
                    >{{ field.constraints.helpText }}</small>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Protocol Matrix -->
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
        <div class="form-actions" v-show="!showMatrix">
          <button @click.prevent="addNewSection" class="btn-option">
            + Add Section
          </button>
          <button @click.prevent="confirmClearForm" class="btn-option">
            Clear
          </button>
          <button @click.prevent="saveForm" class="btn-primary">
            Save Template
          </button>

          <button @click="openDownloadDialog" class="btn-option">
            Download Template
          </button>
          <button @click="openUploadDialog" class="btn-option">
            Upload Template
          </button>
          <button @click="openPreviewDialog" class="btn-option">
            Preview Template
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

    <!-- Model Dialog -->
    <div v-if="showModelDialog" class="modal-overlay">
      <div class="modal model-dialog">
        <h3>Select Properties for {{ currentModel.title }}</h3>
        <div class="model-prop-list">
          <div
            v-for="(prop, idx) in currentModel.fields"
            :key="idx"
            class="prop-row"
          >
            <div class="prop-info">
              <div class="prop-name">{{ prop.label }}</div>
              <div class="prop-desc">{{ prop.placeholder }}</div>
            </div>
            <div class="prop-check">
              <input type="checkbox" v-model="selectedProps[idx]" />
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="takeoverModel" class="btn-primary">
            Takeover
          </button>
          <button @click="showModelDialog = false" class="btn-option">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Preview Dialog -->
    <div v-if="showPreviewDialog" class="modal-overlay">
      <div class="modal preview-modal">
        <div class="preview-content">
          <FormPreview :form="forms[previewFormIndex]" />
        </div>
        <div class="modal-actions">
          <button @click="closePreviewDialog" class="btn-primary">Close</button>
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

    <!-- Input Dialog -->
    <div v-if="showInputDialog" class="modal-overlay">
      <div class="modal input-dialog-modal">
        <p>{{ inputDialogMessage }}</p>
        <input type="text" v-model="inputDialogValue" class="input-dialog-field" />
        <div class="modal-actions">
          <button @click="confirmInputDialog" class="btn-primary">Save</button>
          <button @click="cancelInputDialog" class="btn-option">Cancel</button>
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

    <!-- Constraints Dialog -->
    <div v-if="showConstraintsDialog" class="modal-overlay">
      <div class="modal constraints-edit-modal">
        <FieldConstraintsDialog
          :currentFieldType="currentFieldType"
          :constraintsForm="constraintsForm"
          @updateConstraints="confirmConstraintsDialog"
          @closeConstraintsDialog="cancelConstraintsDialog"
        />
      </div>
    </div>

    <!-- Download Dialog -->
    <div v-if="showDownloadDialog" class="modal-overlay">
      <div class="modal">
        <p>Select format to download the form:</p>
        <div class="modal-actions">
          <button @click="downloadFormData('json')" class="btn-primary">JSON</button>
          <button @click="downloadFormData('yaml')" class="btn-primary">YAML</button>
        </div>
        <div class="modal-actions">
          <button @click="closeDownloadDialog" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Upload Dialog -->
    <div v-if="showUploadDialog" class="modal-overlay">
      <div class="modal">
        <p>Select a YAML/JSON file to upload:</p>
        <input type="file" @change="handleFileChange" accept=".json,.yaml,.yml" />
        <div class="modal-actions">
          <button @click="closeUploadDialog" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import yaml from "js-yaml";
import icons from "@/assets/styles/icons";
import ShaclComponents from "./ShaclComponents.vue";
import FieldConstraintsDialog from "./FieldConstraintsDialog.vue";
import FormPreview from "./FormPreview.vue";
import ProtocolMatrix from "./ProtocolMatrix.vue";

export default {
  name: "ScratchFormComponent",
  components: {
    ShaclComponents,
    FieldConstraintsDialog,
    FormPreview,
    ProtocolMatrix
  },
  data() {
    return {
      forms: [],
      currentFormIndex: 0,
      activeSection: 0,
      activeTab: "template",
      generalFields: [],
      dataModels: [],
      showModelDialog: false,
      currentModel: null,
      selectedProps: [],

      showMatrix: false,
      visits: [],
      groups: [],
      assignments: [],

      showConfirmDialog: false,
      confirmDialogMessage: "",
      confirmDialogCallback: null,

      showInputDialog: false,
      inputDialogMessage: "",
      inputDialogValue: "",
      inputDialogCallback: null,

      showGenericDialog: false,
      genericDialogMessage: "",
      genericDialogCallback: null,

      showConstraintsDialog: false,
      constraintsForm: {},
      currentFieldType: "",
      currentFieldIndices: {},

      showDownloadDialog: false,
      showUploadDialog: false,

      showPreviewDialog: false,
      previewFormIndex: 0,

      studyDetails: {}
    };
  },
  computed: {
    icons() { return icons; },
    token() { return this.$store.state.token; },
    currentForm() { return this.forms[this.currentFormIndex] || { sections: [] }; },
    selectedModels() {
      // include every section as a "model" in the matrix
      return this.currentForm.sections.map(sec => ({
       title: sec.title   ,
       fields: sec.fields}));
    }
  },
  watch: {
    visits:         { handler: "initAssignments", immediate: true },
    groups:         { handler: "initAssignments", immediate: true },
    selectedModels: { handler: "initAssignments", immediate: true },
    forms:          { handler(f) { localStorage.setItem("scratchForms", JSON.stringify(f)); }, deep: true }
  },
  async mounted() {
    const details = this.$store.state.studyDetails || {};
    this.studyDetails = details;
    this.visits = details.visits || [];
    this.groups = details.groups || [];
    this.forms = JSON.parse(localStorage.getItem("scratchForms") || "[]");

    try {
      const res = await axios.get("http://127.0.0.1:8000/forms/available-fields");
      this.generalFields = res.data;
    } catch (e) {
      console.error("Error loading general fields", e);
    }

    await this.loadDataModels();
  },
  methods: {
    goBack() { this.$router.back(); },
    initAssignments() {
      const m = this.selectedModels.length, v = this.visits.length, g = this.groups.length;
      this.assignments = Array.from({ length: m }, () =>
        Array.from({ length: v }, () =>
          Array.from({ length: g }, () => false)
        )
      );
    },

    handleProtocolClick() { this.showMatrix = true; },
    editTemplate()       { this.showMatrix = false; },

    // called when ProtocolMatrix emits assignment-updated
    onAssignmentUpdated({ mIdx, vIdx, gIdx, checked }) {
      this.assignments[mIdx][vIdx][gIdx] = checked;
    },
    addNewSection() {
      this.currentForm.sections.push({
        title: `Section ${this.currentForm.sections.length + 1}`,
        fields: [],
        collapsed: false
      });
      this.toggleSection(this.currentForm.sections.length - 1);
    },
    addNewSectionBelow(i) {
      this.currentForm.sections.splice(i+1, 0, {
        title: `Section ${i+2}`,
        fields: [],
        collapsed: false
      });
      this.toggleSection(i+1);
    },
    confirmDeleteSection(i) {
      this.openConfirmDialog("Delete this section?", () => {
        this.currentForm.sections.splice(i,1);
        this.activeSection = Math.max(0, this.activeSection-1);
      });
    },
    confirmClearForm() {
      this.openConfirmDialog("Clear all sections?", () => {
        this.currentForm.sections = [];
        this.activeSection = 0;
      });
    },
    toggleSection(i) {
      this.currentForm.sections.forEach((s,idx) => {
        s.collapsed = idx!==i ? true : !s.collapsed;
        if (!s.collapsed) this.activeSection = i;
      });
    },
    setActiveSection(i) { this.activeSection = i; },
    editSection(i,v)     { if(v) this.currentForm.sections[i].title = v; },

    openInputDialog(msg, def, cb) {
      this.inputDialogMessage = msg;
      this.inputDialogValue   = def;
      this.inputDialogCallback= cb;
      this.showInputDialog    = true;
    },
    confirmInputDialog() {
      if (this.inputDialogCallback) this.inputDialogCallback(this.inputDialogValue);
      this.showInputDialog = false;
    },
    cancelInputDialog() {
      this.showInputDialog = false;
    },

    addFieldToActiveSection(field) {
      const sec = this.currentForm.sections[this.activeSection];
      if (sec.collapsed) this.toggleSection(this.activeSection);
      sec.fields.push({ ...field });
    },
    editField(si,fi,v) {
      if (v) this.currentForm.sections[si].fields[fi].label = v;
    },
    addSimilarField(si,fi) {
      const f = this.currentForm.sections[si].fields[fi];
      const clone = { ...f, name: `${f.name}_${Date.now()}` };
      this.currentForm.sections[si].fields.splice(fi+1,0,clone);
    },
    removeField(si,fi) {
      this.currentForm.sections[si].fields.splice(fi,1);
    },

    openConfirmDialog(msg, cb) {
      this.confirmDialogMessage = msg;
      this.confirmDialogCallback = cb;
      this.showConfirmDialog    = true;
    },
    confirmDialogYes() {
      if (this.confirmDialogCallback) this.confirmDialogCallback();
      this.showConfirmDialog = false;
    },
    closeConfirmDialog() {
      this.showConfirmDialog = false;
    },

    openGenericDialog(msg, cb=null) {
      this.genericDialogMessage = msg;
      this.genericDialogCallback= cb;
      this.showGenericDialog    = true;
    },
    closeGenericDialog() {
      this.showGenericDialog = false;
      if (this.genericDialogCallback) {
        this.genericDialogCallback();
        this.genericDialogCallback = null;
      }
    },

    openConstraintsDialog(si, fi) {
      const f = this.currentForm.sections[si].fields[fi];
      this.currentFieldIndices = { sectionIndex: si, fieldIndex: fi };
      this.currentFieldType    = f.type;
      this.constraintsForm     = f.constraints ? { ...f.constraints } : {};
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

    async loadDataModels() {
      try {
        const res = await fetch("/study_schema.yaml");
        const doc = yaml.load(await res.text());
        this.dataModels = Object.entries(doc.classes)
          .filter(([n]) => n!=="Study")
          .map(([n,cls]) => ({
            title: n,
            fields: Object.entries(cls.attributes).map(([attr,def]) => {
              let type="text", r=(def.range||"").toLowerCase();
              if(r==="date"||r==="datetime") type="date";
              else if(["integer","decimal"].includes(r)) type="number";
              if(def.enum) type="select";
              return {
                name: `${attr}_${Date.now()}`,
                label: attr,
                type,
                options: def.enum||[],
                placeholder: def.description||"",
                value: "",
                constraints: { required: !!def.required }
              };
            })
          }));
      } catch(err) {
        console.error("Failed to load data models:", err);
      }
    },
    openModelDialog(model) {
      this.currentModel = model;
      this.selectedProps = model.fields.map(() => false);
      this.showModelDialog = true;
    },
    takeoverModel() {
      const chosen = this.currentModel.fields
        .filter((_,i) => this.selectedProps[i])
        .map(f => ({ ...f }));
      const newSection = {
        title: this.currentModel.title,
        collapsed: false,
        fields: chosen
      };
      this.currentForm.sections.splice(this.activeSection+1, 0, newSection);
      this.activeSection++;
      this.showModelDialog = false;
    },

    openDownloadDialog() {
      this.showDownloadDialog = true;
    },
    closeDownloadDialog() {
      this.showDownloadDialog = false;
    },
    downloadFormData(format) {
      const data = { studyDetails:this.studyDetails, forms:this.forms };
      let str, name;
      const pref = this.studyDetails.name?.trim().replace(/\s+/g,"_")||"formData";
      if(format==="json") {
        str = JSON.stringify(data,null,2);
        name = `${pref}.json`;
      } else {
        try {
          str = yaml.dump(data);
          name = `${pref}.yaml`;
        } catch {
          str="Error"; name="formData.txt";
        }
      }
      const blob = new Blob([str],{type:"text/plain"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = name; a.click();
      URL.revokeObjectURL(url);
      this.showDownloadDialog = false;
    },
    openUploadDialog() {
      this.showUploadDialog = true;
    },
    closeUploadDialog() {
      this.showUploadDialog = false;
    },
    handleFileChange(e) {
      const f = e.target.files[0];
      if(!f) return;
      const r = new FileReader();
      r.onload = evt => {
        let pd, ct=evt.target.result.trim();
        try { pd=JSON.parse(ct); }
        catch {
          try { pd=yaml.load(ct); }
          catch { return this.openGenericDialog("Invalid file."); }
        }
        if(pd.studyDetails) {
          this.studyDetails = pd.studyDetails;
          this.$store.commit("setStudyDetails",pd.studyDetails);
        }
        if(pd.forms) {
          this.forms = pd.forms;
          this.totalForms = pd.forms.length;
          this.currentFormIndex = 0;
          this.activeSection = 0;
        }
      };
      r.readAsText(f);
      this.showUploadDialog = false;
    },
    openPreviewDialog() {
      this.previewFormIndex = this.currentFormIndex;
      this.showPreviewDialog = true;
    },
    closePreviewDialog() {
      this.showPreviewDialog = false;
    },
    prevPreview() {
      if(this.previewFormIndex>0) this.previewFormIndex--;
    },
    nextPreview() {
      if(this.previewFormIndex<this.forms.length-1) this.previewFormIndex++;
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

/* MATRIX ACTIONS */
.matrix-actions {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  gap: 10px;
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