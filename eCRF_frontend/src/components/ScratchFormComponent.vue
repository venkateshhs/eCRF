<template>
  <div class="create-form-container">
    <!-- Header -->
    <div class="header-container">
      <button @click="goBack" class="btn-back" title="Go Back">
        <i :class="icons.back"></i> Back
      </button>
    </div>

    <!-- Study Meta Information Section -->
    <StudyMetaInfo
      ref="studyMetaInfo"
      :studyDetails="studyDetails"
      :metaInfo="metaInfo"
      :metaInfoCollapsed="metaInfoCollapsed"
      @toggle-meta-info="toggleMetaInfo"
      @open-meta-edit-dialog="openMetaEditDialog"
      @reload-forms="reloadForms"
    />

    <!-- Main Content: Form Area & Available Fields -->
    <div class="scratch-form-content">
      <!-- Form Area -->
      <div class="form-area">
        <!-- Editable Form Name and Navigation -->
        <div class="form-heading-container">
          <button @click="prevForm" class="nav-button" :disabled="currentFormIndex === 0" title="Previous Form">
            <i :class="icons.prev"></i>
          </button>
          <input
            type="text"
            v-model="formName"
            class="form-name-input heading-input"
            placeholder="Untitled Form"
          />
          <button @click="nextForm" class="nav-button" :disabled="currentFormIndex === totalForms - 1" title="Next Form">
            <i :class="icons.next"></i>
          </button>
        </div>
        <div class="form-indicator">
          Form {{ currentFormIndex + 1 }} / {{ totalForms }} forms
        </div>

        <!-- Render Current Form Sections -->
        <div
          v-for="(section, sectionIndex) in currentForm.sections"
          :key="sectionIndex"
          class="form-section"
          :class="{ active: activeSection === sectionIndex }"
          @click.self="setActiveSection(sectionIndex)"
          tabindex="0"
        >
          <!-- Section Header -->
          <div class="section-header">
            <h3>{{ section.title }}</h3>
            <div class="field-actions">
              <button
                @click.prevent="openInputDialog('Enter a new title for this section:', section.title, newVal => editSection(sectionIndex, newVal))"
                class="icon-button"
                title="Edit Section Title"
              >
                <i :class="icons.edit"></i>
              </button>
              <button @click.prevent="addNewSectionBelow(sectionIndex)" class="icon-button" title="Add New Section Below">
                <i :class="icons.add"></i>
              </button>
              <button @click.prevent="copySection(sectionIndex)" class="icon-button" title="Copy Section">
                <i :class="icons.copy"></i>
              </button>
              <button
                @click.prevent="confirmDeleteSection(sectionIndex)"
                class="icon-button"
                title="Delete Section"
              >
                <i :class="icons.delete"></i>
              </button>
              <button @click.prevent="toggleSection(sectionIndex)" class="icon-button"
                      :title="section.collapsed ? 'Expand Section' : 'Collapse Section'">
                <i :class="section.collapsed ? icons.toggleDown : icons.toggleUp"></i>
              </button>
            </div>
          </div>
          <div v-if="!section.collapsed" class="section-content">
            <div
              v-for="(field, fieldIndex) in section.fields"
              :key="fieldIndex"
              class="form-group"
            >
              <div class="field-header">
                <label v-if="field.type !== 'button'" :for="field.name">{{ field.label }}</label>
                <div class="field-actions">
                  <button
                    @click.prevent="openInputDialog('Enter new label for the field:', field.label, newVal => editField(sectionIndex, fieldIndex, newVal))"
                    class="icon-button"
                    title="Edit Field Label"
                  >
                    <i :class="icons.edit"></i>
                  </button>
                  <button
                    @click.prevent="addSimilarField(sectionIndex, fieldIndex)"
                    class="icon-button"
                    title="Add Similar Field"
                  >
                    <i :class="icons.add"></i>
                  </button>
                  <button
                    @click.prevent="removeField(sectionIndex, fieldIndex)"
                    class="icon-button"
                    title="Delete Field"
                  >
                    <i :class="icons.delete"></i>
                  </button>
                  <button
                    @click.prevent="openConstraintsDialog(sectionIndex, fieldIndex)"
                    class="icon-button"
                    title="Edit Field Constraints"
                  >
                    <i :class="icons.cog"></i>
                  </button>
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
                  v-if="field.type === 'textarea'"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.constraints?.placeholder || field.placeholder"
                  :rows="field.rows"
                  :required="field.constraints?.required"
                  :readonly="field.constraints?.readonly"
                  :minlength="field.constraints?.minLength"
                  :maxlength="field.constraints?.maxLength"
                  :pattern="field.constraints?.pattern"
                ></textarea>
                <input
                  v-if="field.type === 'number'"
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
                  v-if="field.type === 'date'"
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
                  v-if="field.type === 'select'"
                  :id="field.name"
                  v-model="field.value"
                  :required="field.constraints?.required"
                >
                  <option v-for="option in field.options" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select>
                <div v-if="field.type === 'checkbox'" class="checkbox-group">
                  <label v-for="(option, i) in field.options" :key="i">
                    <input
                      type="checkbox"
                      v-model="field.value"
                      :value="option"
                      :required="field.constraints?.required"
                      :readonly="field.constraints?.readonly"
                    /> {{ option }}
                  </label>
                </div>
                <div v-if="field.type === 'radio'" class="radio-group">
                  <label v-for="option in field.options" :key="option">
                    <input
                      type="radio"
                      :name="field.name"
                      v-model="field.value"
                      :value="option"
                      :required="field.constraints?.required"
                    />
                    {{ option }}
                  </label>
                </div>
                <button
                  v-if="field.type === 'button'"
                  type="button"
                  class="form-button"
                  title="Button Action"
                >
                  {{ field.label }}
                </button>
                <small v-if="field.constraints?.helpText" class="help-text">{{ field.constraints.helpText }}</small>
              </div>
            </div>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <div class="button-row">
            <button @click.prevent="addNewSection" class="btn-option" title="Add New Section">
              + Add Section
            </button>
            <button @click.prevent="confirmClearForm" class="btn-option" title="Clear Form">
              Clear Form
            </button>
            <button @click.prevent="saveForm" class="btn-primary" title="Save Study">
              Save Study
            </button>
            <button @click="navigateToSavedForms" class="btn-option" title="View Saved Study">
              View Saved Study
            </button>
            <button @click="openDownloadDialog" class="btn-option" title="Download Form">
              Download Form
            </button>
            <button @click="openUploadDialog" class="btn-option" title="Upload Form">
              Upload Form
            </button>
            <button @click="openPreviewDialog" class="btn-option" title="Preview Form">
              Preview Form
            </button>
          </div>
        </div>
      </div>

      <!-- Available Fields Section -->
      <div class="available-fields">
        <h2>Available Fields</h2>
        <div class="tabs">
          <button :class="{ active: activeTab === 'general' }" @click="activeTab = 'general'" title="General Fields">
            General Fields
          </button>
          <button :class="{ active: activeTab === 'specialized' }" @click="activeTab = 'specialized'" title="Specialized Fields">
            Specialized Fields
          </button>
          <button :class="{ active: activeTab === 'shacl' }" @click="activeTab = 'shacl'" title="SHACL Components">
            SHACL Components
          </button>
        </div>
        <div v-if="activeTab === 'general'" class="general-fields">
          <div
            v-for="(field, index) in generalFields"
            :key="index"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
            :title="`Add field: ${field.label}`"
          >
            <i :class="field.icon"></i> {{ field.label }}
          </div>
        </div>
        <div v-if="activeTab === 'specialized'" class="specialized-fields">
          <div
            v-for="(section, sectionIndex) in specializedFieldSections"
            :key="sectionIndex"
            class="available-section"
          >
            <h3>{{ section.title }}</h3>
            <div class="field-buttons">
              <button
                v-for="(field, fieldIndex) in section.fields"
                :key="fieldIndex"
                class="available-field-button"
                @click="addFieldToActiveSection(field)"
                :title="`Add field: ${field.label}`"
              >
                <i :class="field.icon"></i> {{ field.label }}
              </button>
            </div>
          </div>
        </div>
        <div>
          <ShaclComponents v-if="activeTab === 'shacl'" :shaclComponents="shaclComponents" />
        </div>
      </div>
    </div>

    <!-- Preview Dialog Modal -->
    <div v-if="showPreviewDialog" class="modal-overlay">
      <div class="modal preview-modal">
        <FormPreview :form="currentForm" />
        <div class="modal-actions">
          <button @click="closePreviewDialog" class="btn-primary modal-btn" title="Close Preview">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Save Dialog Modal -->
    <div v-if="showSaveDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ saveDialogMessage }}</p>
        <button @click="closeSaveDialog" class="btn-primary modal-btn" title="Close Save Dialog">OK</button>
      </div>
    </div>

    <!-- Generic Dialog Modal -->
    <div v-if="showGenericDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ genericDialogMessage }}</p>
        <button @click="closeGenericDialog" class="btn-primary modal-btn" title="Close Alert">OK</button>
      </div>
    </div>

    <!-- Input Dialog Modal -->
    <div v-if="showInputDialog" class="modal-overlay">
      <div class="modal input-dialog-modal">
        <p>{{ inputDialogMessage }}</p>
        <input type="text" v-model="inputDialogValue" class="input-dialog-field" />
        <div class="modal-actions">
          <button @click="confirmInputDialog" class="btn-primary modal-btn" title="Save Input">Save</button>
          <button @click="cancelInputDialog" class="btn-option modal-btn" title="Cancel Input">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Confirm Dialog Modal -->
    <div v-if="showConfirmDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ confirmDialogMessage }}</p>
        <div class="modal-actions">
          <button @click="confirmDialogYes" class="btn-primary modal-btn" title="Confirm">Yes</button>
          <button @click="closeConfirmDialog" class="btn-option modal-btn" title="Cancel">No</button>
        </div>
      </div>
    </div>

    <!-- Constraints Edit Dialog Modal -->
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

    <!-- Download Dialog Modal -->
    <div v-if="showDownloadDialog" class="modal-overlay">
      <div class="modal">
        <p>Select format to download the form:</p>
        <div class="modal-actions">
          <button @click="downloadFormData('json')" class="btn-primary" title="Download as JSON">JSON</button>
          <button @click="downloadFormData('yaml')" class="btn-primary" title="Download as YAML">YAML</button>
        </div>
        <div class="modal-actions">
          <button @click="closeDownloadDialog" class="btn-option" title="Cancel">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Upload Dialog Modal -->
    <div v-if="showUploadDialog" class="modal-overlay">
      <div class="modal">
        <p>Select a YAML/JSON file to upload:</p>
        <input type="file" @change="handleFileChange" accept=".json,.yaml,.yml" />
        <div class="modal-actions">
          <button @click="closeUploadDialog" class="btn-option" title="Cancel">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";
import StudyMetaInfo from "./StudyMetaInfo.vue";
import ShaclComponents from "./ShaclComponents.vue";
import FieldConstraintsDialog from "./FieldConstraintsDialog.vue";
import FormPreview from "./FormPreview.vue";
import yaml from "js-yaml";

export default {
  name: "ScratchFormComponent",
  components: { StudyMetaInfo, ShaclComponents, FieldConstraintsDialog, FormPreview },
  data() {
    return {
      forms: [],
      currentFormIndex: 0,
      totalForms: 1,
      activeSection: 0,
      activeTab: "general",
      shaclComponents: [],
      generalFields: [],
      specializedFieldSections: [],
      showSaveDialog: false,
      saveDialogMessage: "",
      showGenericDialog: false,
      genericDialogMessage: "",
      genericDialogCallback: null,
      showInputDialog: false,
      inputDialogMessage: "",
      inputDialogValue: "",
      inputDialogCallback: null,
      defaultFormStructure: [{ title: "Default Section", fields: [], collapsed: false }],
      studyDetails: {},
      metaInfo: {
        numberOfSubjects: null,
        numberOfVisits: null,
        studyMetaDescription: ""
      },
      metaInfoCollapsed: true,
      showMetaEditDialog: false,
      metaEditForm: {
        name: "",
        description: "",
        numberOfForms: null,
        numberOfSubjects: null,
        numberOfVisits: null,
        studyMetaDescription: ""
      },
      showReinitConfirm: false,
      pendingMetaEdit: null,
      showConfirmDialog: false,
      confirmDialogMessage: "",
      confirmDialogCallback: null,
      showConstraintsDialog: false,
      constraintsForm: {
        min: null,
        max: null,
        maxDigits: null,
        minLength: null,
        maxLength: null,
        pattern: "",
        required: false,
      },
      currentFieldConstraints: null,
      currentFieldType: "",
      currentFieldIndices: { sectionIndex: null, fieldIndex: null },
      showDownloadDialog: false,
      showUploadDialog: false,
      showPreviewDialog: false,
      // For any additional form-level file attachments if needed
      selectedFiles: [],
      // storageOption for form-level attachments; meta file attachments come from StudyMetaInfo
      storageOption: "db"
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
    currentForm() {
      return this.forms[this.currentFormIndex] || { formName: "", sections: [] };
    },
    formName: {
      get() {
        return this.currentForm.formName;
      },
      set(value) {
        this.forms[this.currentFormIndex] = {
          ...this.currentForm,
          formName: value,
        };
      },
    },
    icons() {
      return icons;
    },
  },
  async mounted() {
    // Get studyDetails from Vuex store
    const details = this.$store.state.studyDetails || {};
    this.studyDetails = details;
    this.totalForms = details.numberOfForms || 1;
    if (details.metaInfo) {
      this.metaInfo = details.metaInfo;
    }
    for (let i = 0; i < this.totalForms; i++) {
      this.forms.push({
        formName: `Form${i + 1}`,
        sections: JSON.parse(JSON.stringify(this.defaultFormStructure)),
      });
    }
    await this.loadAvailableFields();
  },
  methods: {
    // Normalizes form keys from formName to form_name as expected by backend schema.
    normalizeForms(formsArray) {
      return formsArray.map(form => ({
        form_name: form.formName,
        sections: form.sections
      }));
    },
    reloadForms(newTotal) {
      this.totalForms = newTotal;
      this.forms = [];
      for (let i = 0; i < this.totalForms; i++) {
        this.forms.push({
          formName: `Form${i + 1}`,
          sections: JSON.parse(JSON.stringify(this.defaultFormStructure)),
        });
      }
      this.currentFormIndex = 0;
      this.activeSection = 0;
    },
    navigateToSavedForms() {
      this.$router.push("/saved-forms");
    },
    async saveForm() {
      if (!this.token) {
        this.openGenericDialog("Authentication error: No token found. Please log in again.", () => {
          this.$router.push("/login");
        });
        return;
      }
      // Build the study payload
      const studyData = {
        name: this.studyDetails.name || "Untitled Study",
        description: this.studyDetails.description || "",
        meta_info: JSON.stringify(this.metaInfo),
        // Normalize forms so that keys match the backend schema (form_name vs formName)
        forms: JSON.stringify(this.normalizeForms(this.forms)),
        storage_option: this.storageOption,
      };

      // Conditionally add number_of_subjects and number_of_visits if defined
      if (this.metaInfo.numberOfSubjects !== undefined) {
        studyData.number_of_subjects = this.metaInfo.numberOfSubjects;
      }
      if (this.metaInfo.numberOfVisits !== undefined) {
        studyData.number_of_visits = this.metaInfo.numberOfVisits;
      }

      const formData = new FormData();
      for (const key in studyData) {
        formData.append(key, studyData[key]);
      }

      // Append meta file attachments from StudyMetaInfo component
      if (this.$refs.studyMetaInfo) {
        const metaComp = this.$refs.studyMetaInfo;
        if (metaComp.metaFiles && metaComp.metaFiles.length > 0) {
          metaComp.metaFiles.forEach(fileObj => {
            formData.append("meta_files", fileObj.file);
            formData.append("meta_file_descriptions", fileObj.description || "");
          });
          formData.append("meta_storage_option", metaComp.metaStorageOption);
        }
      }

      // Append any additional form-level file attachments if needed
      if (this.selectedFiles && this.selectedFiles.length > 0) {
        Array.from(this.selectedFiles).forEach(file => {
          formData.append("files", file);
        });
      }

      // Debug: Log all FormData entries
      for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(`${key}: ${value.name} (${value.type})`);
        } else {
          console.log(`${key}:`, value);
        }
      }

      try {
        const response = await axios.post("http://127.0.0.1:8000/forms/save-study", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Bearer ${this.token}`,
          },
        });
        this.openSaveDialog(`Study "${response.data.name}" saved successfully!`);
      } catch (error) {
        console.error("Error saving study:", error.response?.data || error.message);
        this.openGenericDialog("Failed to save study. Please try again.");
      }
    },
    // Added missing openSaveDialog method
    openSaveDialog(message) {
      this.saveDialogMessage = message;
      this.showSaveDialog = true;
    },
    closeSaveDialog() {
      this.showSaveDialog = false;
      if (this.currentFormIndex < this.totalForms - 1) {
        this.nextForm();
      } else {
        this.openGenericDialog("All forms have been saved.");
      }
    },
    openGenericDialog(message, callback = null) {
      this.genericDialogMessage = message;
      this.genericDialogCallback = callback;
      this.showGenericDialog = true;
    },
    closeGenericDialog() {
      this.showGenericDialog = false;
      if (this.genericDialogCallback) {
        this.genericDialogCallback();
        this.genericDialogCallback = null;
      }
    },
    openInputDialog(message, defaultValue, callback) {
      this.inputDialogMessage = message;
      this.inputDialogValue = defaultValue;
      this.inputDialogCallback = callback;
      this.showInputDialog = true;
    },
    confirmInputDialog() {
      if (this.inputDialogCallback) {
        this.inputDialogCallback(this.inputDialogValue);
      }
      this.showInputDialog = false;
      this.inputDialogMessage = "";
      this.inputDialogValue = "";
      this.inputDialogCallback = null;
    },
    cancelInputDialog() {
      this.showInputDialog = false;
      this.inputDialogMessage = "";
      this.inputDialogValue = "";
      this.inputDialogCallback = null;
    },
    openConfirmDialog(message, callback) {
      this.confirmDialogMessage = message;
      this.confirmDialogCallback = callback;
      this.showConfirmDialog = true;
    },
    confirmDialogYes() {
      if (this.confirmDialogCallback) {
        this.confirmDialogCallback();
      }
      this.closeConfirmDialog();
    },
    closeConfirmDialog() {
      this.showConfirmDialog = false;
      this.confirmDialogMessage = "";
      this.confirmDialogCallback = null;
    },
    async loadAvailableFields() {
      try {
        const generalResponse = await axios.get("http://127.0.0.1:8000/forms/available-fields");
        const specializedResponse = await axios.get("http://127.0.0.1:8000/forms/specialized-fields");
        this.generalFields = generalResponse.data || [];
        this.specializedFieldSections = specializedResponse.data || [];
      } catch (error) {
        console.error("Error loading fields:", error.response?.data || error.message);
      }
    },
    goBack() {
      this.$router.back("/dashboard");
    },
    prevForm() {
      if (this.currentFormIndex > 0) {
        this.currentFormIndex--;
        this.activeSection = 0;
      }
    },
    nextForm() {
      if (this.currentFormIndex < this.totalForms - 1) {
        this.currentFormIndex++;
        this.activeSection = 0;
      }
    },
    toggleSection(sectionIndex) {
      this.currentForm.sections.forEach((section, index) => {
        if (index === sectionIndex) {
          section.collapsed = !section.collapsed;
          if (!section.collapsed) {
            this.setActiveSection(sectionIndex);
          }
        } else {
          section.collapsed = true;
        }
      });
    },
    setActiveSection(sectionIndex) {
      this.activeSection = sectionIndex;
    },
    addFieldToActiveSection(field) {
      const section = this.currentForm.sections[this.activeSection];
      if (section.collapsed) {
        this.toggleSection(this.activeSection);
      }
      section.fields.push({ ...field, name: `${field.type}_${Date.now()}` });
    },
    addNewSection() {
      this.currentForm.sections.push({
        title: `New Section ${this.currentForm.sections.length + 1}`,
        fields: [],
        collapsed: true,
      });
      this.toggleSection(this.currentForm.sections.length - 1);
    },
    addNewSectionBelow(index) {
      this.currentForm.sections.splice(index + 1, 0, {
        title: `New Section ${index + 2}`,
        fields: [],
        collapsed: true,
      });
      this.toggleSection(index + 1);
    },
    confirmDeleteSection(index) {
      if (this.currentForm.sections.length === 1 && this.currentForm.sections[0].title === "Default Section") {
        this.openGenericDialog("Default section cannot be deleted.");
        return;
      }
      this.openConfirmDialog("Are you sure you want to delete this section?", () => {
        this.currentForm.sections.splice(index, 1);
        if (this.activeSection >= index) {
          this.activeSection = Math.max(0, this.activeSection - 1);
        }
        if (this.currentForm.sections.length > 0) {
          this.toggleSection(this.activeSection);
        }
      });
    },
    confirmClearForm() {
      this.openConfirmDialog("Are you sure you want to clear the form?", () => {
        this.currentForm.sections = [{ title: "Default Section", fields: [], collapsed: false }];
        this.activeSection = 0;
      });
    },
    editSection(index, newVal) {
      if (newVal) {
        this.currentForm.sections[index].title = newVal;
      }
    },
    editField(sectionIndex, fieldIndex, newVal) {
      if (newVal) {
        this.currentForm.sections[sectionIndex].fields[fieldIndex].label = newVal;
      }
    },
    copySection(sectionIndex) {
      const sectionToCopy = this.currentForm.sections[sectionIndex];
      const newSection = JSON.parse(JSON.stringify(sectionToCopy));
      newSection.title = `${sectionToCopy.title} (Copy)`;
      newSection.fields = sectionToCopy.fields.map((field) => ({
        ...field,
        name: `${field.name}_copy_${Date.now()}`,
      }));
      newSection.collapsed = true;
      this.currentForm.sections.splice(sectionIndex + 1, 0, newSection);
      this.toggleSection(sectionIndex + 1);
    },
    clearForm() {
      this.confirmClearForm();
    },
    submitForm() {
      console.log("Form submitted with data:", this.currentForm.sections);
      this.openGenericDialog("Form submitted successfully!");
    },
    addSimilarField(sectionIndex, fieldIndex) {
      const field = this.currentForm.sections[sectionIndex].fields[fieldIndex];
      const newField = { ...field, name: `${field.type}_${Date.now()}` };
      this.currentForm.sections[sectionIndex].fields.splice(fieldIndex + 1, 0, newField);
    },
    removeField(sectionIndex, fieldIndex) {
      this.currentForm.sections[sectionIndex].fields.splice(fieldIndex, 1);
    },
    // Field Constraints Editing Methods
    openConstraintsDialog(sectionIndex, fieldIndex) {
      const field = this.currentForm.sections[sectionIndex].fields[fieldIndex];
      this.currentFieldIndices = { sectionIndex, fieldIndex };
      this.currentFieldType = field.type;
      if (field.constraints) {
        this.constraintsForm = { ...field.constraints };
      } else {
        if (field.type === "number") {
          this.constraintsForm = { min: null, max: null, maxDigits: null };
        } else if (field.type === "text" || field.type === "textarea") {
          this.constraintsForm = { minLength: null, maxLength: null, pattern: "", required: false };
        } else {
          this.constraintsForm = {};
        }
      }
      this.showConstraintsDialog = true;
    },
    confirmConstraintsDialog(updatedConstraints) {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices;
      const field = this.currentForm.sections[sectionIndex].fields[fieldIndex];
      field.constraints = { ...updatedConstraints };
      if (field.type === "text" || field.type === "textarea") {
        field.placeholder = updatedConstraints.placeholder || field.placeholder;
        field.required = updatedConstraints.required || false;
        field.readonly = updatedConstraints.readonly || false;
        field.minLength = updatedConstraints.minLength;
        field.maxLength = updatedConstraints.maxLength;
        field.pattern = updatedConstraints.pattern;
      }
      if (field.type === "number") {
        field.placeholder = updatedConstraints.placeholder || field.placeholder;
        field.required = updatedConstraints.required || false;
        field.readonly = updatedConstraints.readonly || false;
        field.min = updatedConstraints.min;
        field.max = updatedConstraints.max;
        field.step = updatedConstraints.step;
      }
      if (field.type === "date") {
        field.placeholder = updatedConstraints.placeholder || field.placeholder;
        field.required = updatedConstraints.required || false;
        field.readonly = updatedConstraints.readonly || false;
        field.minDate = updatedConstraints.minDate;
        field.maxDate = updatedConstraints.maxDate;
      }
      if (field.type === "select" || field.type === "radio" || field.type === "checkbox") {
        field.required = updatedConstraints.required || false;
      }
      if (updatedConstraints.defaultValue !== undefined) {
        field.value = updatedConstraints.defaultValue;
      }
      this.showConstraintsDialog = false;
    },
    cancelConstraintsDialog() {
      this.showConstraintsDialog = false;
    },
    // Download Form Methods
    openDownloadDialog() {
      this.showDownloadDialog = true;
    },
    closeDownloadDialog() {
      this.showDownloadDialog = false;
    },
    downloadFormData(format) {
      const dataToDownload = {
        studyDetails: this.studyDetails,
        metaInfo: this.metaInfo,
        forms: this.forms
      };
      let dataStr;
      let fileName;
      const namePrefix = (this.studyDetails.name && this.studyDetails.name.trim() !== "")
                      ? this.studyDetails.name.trim().replace(/\s+/g, "_")
                      : "formData";
      if (format === "json") {
        dataStr = JSON.stringify(dataToDownload, null, 2);
        fileName = `${namePrefix}.json`;
      } else if (format === "yaml") {
        try {
          dataStr = yaml.dump(dataToDownload);
          fileName = `${namePrefix}.yaml`;
        } catch (e) {
          console.error("YAML conversion error", e);
          dataStr = "Error converting to YAML";
          fileName = "formData.txt";
        }
      }
      const blob = new Blob([dataStr], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      link.click();
      URL.revokeObjectURL(url);
      this.showDownloadDialog = false;
    },
    // Upload Form Methods
    openUploadDialog() {
      this.showUploadDialog = true;
    },
    closeUploadDialog() {
      this.showUploadDialog = false;
    },
    handleFileChange(e) {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        const fileContent = evt.target.result;
        let parsedData;
        const trimmedContent = fileContent.trim();
        try {
          parsedData = JSON.parse(trimmedContent);
        } catch (jsonErr) {
          try {
            parsedData = yaml.load(trimmedContent);
          } catch (yamlErr) {
            this.openGenericDialog("Failed to parse file. Please ensure it's valid JSON or YAML.");
            return;
          }
        }
        if (parsedData.studyDetails) {
          this.studyDetails = parsedData.studyDetails;
        }
        if (parsedData.metaInfo) {
          this.metaInfo = parsedData.metaInfo;
        }
        if (parsedData.forms) {
          this.forms = parsedData.forms;
          this.totalForms = parsedData.forms.length;
          this.currentFormIndex = 0;
          this.activeSection = (this.forms[0] && this.forms[0].sections && this.forms[0].sections.length > 0) ? 0 : null;
        } else {
          this.openGenericDialog("Uploaded file does not contain valid form data.");
        }
      };
      reader.readAsText(file);
      this.closeUploadDialog();
    },
    // Preview Methods
    openPreviewDialog() {
      this.showPreviewDialog = true;
    },
    closePreviewDialog() {
      this.showPreviewDialog = false;
    },
  },
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
h1 {
  font-size: 24px;
  font-weight: 500;
  color: $text-color;
  flex: 1;
  text-align: center;
}
.scratch-form-content {
  display: flex;
  flex-wrap: nowrap;
  justify-content: space-between;
  gap: 20px;
}
.form-area {
  flex: 1;
  background: white;
  padding: 20px;
  border: 1px solid $border-color;
  border-radius: 8px;
  min-width: 600px;
}
.form-heading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 10px;
  background: white;
  padding: 10px;
  border: 1px solid $border-color;
  border-radius: 8px;
}
.heading-input {
  font-size: 22px;
  font-weight: 500;
  text-align: center;
  border-bottom: 1px solid $border-color;
  outline: none;
  width: 100%;
  max-width: 400px;
}
.nav-button {
  background: $secondary-color;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  padding: $button-padding;
  cursor: pointer;
  transition: background 0.3s ease;
  &:hover {
    background: $secondary-hover;
  }
}
.form-indicator {
  text-align: center;
  font-size: 16px;
  color: $text-color;
  margin-bottom: 20px;
}
.form-section {
  padding: 15px;
  border-bottom: 1px solid $border-color;
  transition: all 0.3s ease;
  &.active {
    background: #e7f3ff;
    border-left: 3px solid $text-color;
  }
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
  box-sizing: border-box;
}
input:focus,
textarea:focus,
select:focus {
  border-color: $text-color;
  outline: none;
}
.help-text {
  font-size: 12px;
  color: $secondary-color;
  margin-top: 3px;
}
.form-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}
.button-row {
  display: flex;
  gap: 15px;
  width: 100%;
}
.btn-option {
  background: $secondary-color;
  color: $text-color;
  padding: $button-padding;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  text-align: center;
  cursor: pointer;
  transition: background 0.3s ease;
  flex: 1;
  &:hover {
    background: $secondary-hover;
  }
}
.btn-primary {
  background: $primary-color;
  color: white;
  padding: $button-padding;
  border: none;
  border-radius: $button-border-radius;
  text-align: center;
  cursor: pointer;
  transition: background 0.3s ease;
  flex: 1;
  &:hover {
    background: $primary-hover;
  }
}
.icon-button {
  @include button-reset;
  padding: 5px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  transition: background-color 0.3s ease;
  &:hover {
    background-color: $secondary-hover;
  }
}
.available-fields {
  flex-shrink: 0;
  background: white;
  padding: 20px;
  border: 1px solid $border-color;
  border-radius: 8px;
  width: 320px;
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
  border-radius: $button-border-radius;
  cursor: pointer;
  background: $secondary-color;
  flex: 1;
  &:hover {
    background: $secondary-hover;
  }
}
.tabs button.active {
  background: $primary-color;
  color: white;
  border: none;
}
.tabs button:not(.active):hover {
  background: $secondary-hover;
}
.available-field-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  font-size: 14px;
  background: #f9f9f9;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-bottom: 10px;
  i {
    font-size: 18px;
    color: $text-color;
  }
  &:hover {
    background: $secondary-hover;
  }
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 300px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.modal p {
  margin-bottom: 15px;
  text-align: center;
}
.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}
.modal-actions button {
  flex: 1;
}
.input-dialog-modal {
  width: 300px;
}
.input-dialog-field {
  width: 100%;
  padding: 8px;
  border: 1px solid $border-color;
  border-radius: 5px;
  margin-bottom: 15px;
  box-sizing: border-box;
}
.meta-edit-modal {
  width: 350px;
}
.meta-edit-field {
  margin-bottom: 10px;
  label {
    font-weight: bold;
    margin-bottom: 5px;
    display: block;
  }
  input,
  textarea {
    width: 100%;
    padding: 6px;
    border: 1px solid $border-color;
    border-radius: 4px;
    box-sizing: border-box;
  }
}
.constraints-edit-modal {
  width: 300px;
}
.constraints-fields {
  margin-bottom: 15px;
}
.constraint-field {
  margin-bottom: 10px;
  label {
    font-weight: bold;
    margin-bottom: 3px;
    display: block;
  }
  input {
    width: 100%;
    padding: 6px;
    border: 1px solid $border-color;
    border-radius: 4px;
    box-sizing: border-box;
  }
}
.preview-modal {
  width: 500px;
  max-height: 80vh;
  overflow-y: auto;
}
@media (max-width: 768px) {
  .scratch-form-content {
    flex-direction: column;
  }
  .form-area {
    max-width: 100%;
  }
  .available-fields {
    max-width: 100%;
    width: 100%;
  }
}
</style>
