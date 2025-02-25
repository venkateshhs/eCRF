<template>
  <div class="create-form-container">
    <!-- Header -->
    <div class="header-container">
      <button @click="goBack" class="btn-back" title="Go Back">
        <i :class="icons.back"></i> Back
      </button>
    </div>

    <!-- Meta Information Section -->
    <div class="meta-info-container" :class="{ collapsed: metaInfoCollapsed }">
      <div class="meta-header">
        <h2>Study Meta Information</h2>
        <div class="meta-actions">
          <button @click="openMetaEditDialog" class="btn-meta-edit" title="Edit Meta Information">
            <i :class="icons.edit"></i>
          </button>
          <button
            @click="toggleMetaInfo"
            class="btn-meta-toggle"
            :title="metaInfoCollapsed ? 'Expand Meta Information' : 'Collapse Meta Information'"
          >
            <i :class="metaInfoCollapsed ? icons.toggleDown : icons.toggleUp"></i>
          </button>
        </div>
      </div>
      <div v-if="!metaInfoCollapsed">
        <p v-if="studyDetails.name"><strong>Study Name:</strong> {{ studyDetails.name }}</p>
        <p v-if="studyDetails.description"><strong>Description:</strong> {{ studyDetails.description }}</p>
        <p v-if="studyDetails.numberOfForms"><strong>Number of Forms:</strong> {{ studyDetails.numberOfForms }}</p>
        <p v-if="metaInfo.numberOfSubjects"><strong>Number of Subjects:</strong> {{ metaInfo.numberOfSubjects }}</p>
        <p v-if="metaInfo.numberOfVisits"><strong>Number of Visits per Subject:</strong> {{ metaInfo.numberOfVisits }}</p>
        <p v-if="metaInfo.studyMetaDescription"><strong>Study Meta Description:</strong> {{ metaInfo.studyMetaDescription }}</p>
      </div>
    </div>

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
                  :placeholder="field.placeholder"
                />
                <textarea
                  v-if="field.type === 'textarea'"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.placeholder"
                  :rows="field.rows"
                ></textarea>
                <input
                  v-if="field.type === 'number'"
                  type="number"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.placeholder"
                />
                <input
                  v-if="field.type === 'date'"
                  type="date"
                  :id="field.name"
                  v-model="field.value"
                />
                <select v-if="field.type === 'select'" :id="field.name" v-model="field.value">
                  <option v-for="option in field.options" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select>
                <div v-if="field.type === 'checkbox'" class="checkbox-group">
                  <label v-for="(option, i) in field.options" :key="i">
                    <input type="checkbox" v-model="field.value" :value="option" /> {{ option }}
                  </label>
                </div>
                <div v-if="field.type === 'radio'" class="radio-group">
                  <label v-for="option in field.options" :key="option">
                    <input
                      type="radio"
                      :name="field.name"
                      v-model="field.value"
                      :value="option"
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
            <button @click.prevent="saveForm" class="btn-primary" title="Save Form">
              Save Form
            </button>
            <button @click="navigateToSavedForms" class="btn-option" title="View Saved Forms">
              View Saved Forms
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
        <div v-if="activeTab === 'shacl'" class="shacl-components">
          <p>No SHACL components available.</p>
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

    <!-- Meta Edit Dialog Modal -->
    <div v-if="showMetaEditDialog" class="modal-overlay">
      <div class="modal meta-edit-modal">
        <h3>Edit Meta Information</h3>
        <div class="meta-edit-field">
          <label>Study Name:</label>
          <input type="text" v-model="metaEditForm.name" placeholder="Enter study name" />
        </div>
        <div class="meta-edit-field">
          <label>Description:</label>
          <textarea v-model="metaEditForm.description" placeholder="Enter description"></textarea>
        </div>
        <div class="meta-edit-field">
          <label>Number of Forms:</label>
          <input type="number" v-model.number="metaEditForm.numberOfForms" placeholder="Enter number of forms" />
        </div>
        <div class="meta-edit-field">
          <label>Number of Subjects:</label>
          <input type="number" v-model.number="metaEditForm.numberOfSubjects" placeholder="Enter number of subjects" />
        </div>
        <div class="meta-edit-field">
          <label>Number of Visits per Subject:</label>
          <input type="number" v-model.number="metaEditForm.numberOfVisits" placeholder="Enter number of visits" />
        </div>
        <div class="meta-edit-field">
          <label>Study Meta Description:</label>
          <textarea v-model="metaEditForm.studyMetaDescription" placeholder="Enter meta description"></textarea>
        </div>
        <div class="modal-actions">
          <button @click="saveMetaInfo" class="btn-primary modal-btn" title="Save Meta Information">Save</button>
          <button @click="closeMetaEditDialog" class="btn-option modal-btn" title="Cancel Meta Edit">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Reinitialization Confirmation Modal -->
    <div v-if="showReinitConfirm" class="modal-overlay">
      <div class="modal">
        <p>Changing the number of forms will reinitialize your current forms. Proceed?</p>
        <div class="modal-actions">
          <button @click="confirmReinit" class="btn-primary modal-btn" title="Confirm Reinitialization">Yes</button>
          <button @click="cancelReinit" class="btn-option modal-btn" title="Cancel Reinitialization">No</button>
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
        <h3>Edit Field Constraints</h3>
        <div v-if="currentFieldType === 'number'" class="constraints-fields">
          <div class="constraint-field">
            <label>Min Value:</label>
            <input type="number" v-model.number="constraintsForm.min" placeholder="Min" />
          </div>
          <div class="constraint-field">
            <label>Max Value:</label>
            <input type="number" v-model.number="constraintsForm.max" placeholder="Max" />
          </div>
          <div class="constraint-field">
            <label>Max Digits:</label>
            <input type="number" v-model.number="constraintsForm.maxDigits" placeholder="Max Digits" />
          </div>
        </div>
        <div v-else-if="currentFieldType === 'text' || currentFieldType === 'textarea'" class="constraints-fields">
          <div class="constraint-field">
            <label>Min Length:</label>
            <input type="number" v-model.number="constraintsForm.minLength" placeholder="Min Length" />
          </div>
          <div class="constraint-field">
            <label>Max Length:</label>
            <input type="number" v-model.number="constraintsForm.maxLength" placeholder="Max Length" />
          </div>
          <div class="constraint-field">
            <label>Pattern (Regex):</label>
            <input type="text" v-model="constraintsForm.pattern" placeholder="e.g. ^[A-Za-z]+$" />
          </div>
          <div class="constraint-field">
            <label>Required:</label>
            <input type="checkbox" v-model="constraintsForm.required" />
          </div>
        </div>
        <div class="modal-actions">
          <button @click="confirmConstraintsDialog" class="btn-primary modal-btn" title="Save Constraints">Save</button>
          <button @click="cancelConstraintsDialog" class="btn-option modal-btn" title="Cancel Constraints">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons"; // Make sure this file exports your icon classes

export default {
  name: "ScratchFormComponent",
  data() {
    return {
      forms: [],
      currentFormIndex: 0,
      totalForms: 1,
      activeSection: 0,
      activeTab: "general",
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
      metaInfoCollapsed: true,
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
    hasMetaInfo() {
      return (
        this.studyDetails.name ||
        this.studyDetails.description ||
        this.studyDetails.numberOfForms ||
        this.metaInfo.numberOfSubjects ||
        this.metaInfo.numberOfVisits ||
        this.metaInfo.studyMetaDescription
      );
    },
    icons() {
      return icons;
    },
  },
  async mounted() {
    const details = this.$route.query.studyDetails ? JSON.parse(this.$route.query.studyDetails) : {};
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
      // Uncomment below to commit to the database:
      /*
      const formData = {
        form_name: this.currentForm.formName,
        form_structure: this.currentForm.sections,
      };
      try {
        await axios.post("http://127.0.0.1:8000/forms/save-form", formData, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
      } catch (error) {
        if (error.response?.status === 401) {
          this.openGenericDialog("Your session has expired. Please log in again.", () => {
            this.$router.push("/login");
          });
          return;
        } else {
          console.error("Error saving form:", error);
          this.openGenericDialog("Failed to save form. Please try again.");
          return;
        }
      }
      */
      this.saveDialogMessage = `Form "${this.currentForm.formName}" saved successfully!`;
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
    confirmConstraintsDialog() {
      const { sectionIndex, fieldIndex } = this.currentFieldIndices;
      this.currentForm.sections[sectionIndex].fields[fieldIndex].constraints = { ...this.constraintsForm };
      this.showConstraintsDialog = false;
    },
    cancelConstraintsDialog() {
      this.showConstraintsDialog = false;
    },
    // Meta Info Editing Methods
    openMetaEditDialog() {
      this.metaEditForm = {
        name: this.studyDetails.name || "",
        description: this.studyDetails.description || "",
        numberOfForms: this.studyDetails.numberOfForms || 1,
        numberOfSubjects: this.metaInfo.numberOfSubjects,
        numberOfVisits: this.metaInfo.numberOfVisits,
        studyMetaDescription: this.metaInfo.studyMetaDescription || "",
      };
      this.showMetaEditDialog = true;
    },
    closeMetaEditDialog() {
      this.showMetaEditDialog = false;
    },
    saveMetaInfo() {
      if (this.metaEditForm.numberOfForms !== this.totalForms) {
        this.pendingMetaEdit = { ...this.metaEditForm };
        this.showReinitConfirm = true;
        return;
      }
      this.updateMetaData();
      this.showMetaEditDialog = false;
    },
    updateMetaData() {
      this.studyDetails.name = this.metaEditForm.name;
      this.studyDetails.description = this.metaEditForm.description;
      this.studyDetails.numberOfForms = this.metaEditForm.numberOfForms;
      this.metaInfo.numberOfSubjects = this.metaEditForm.numberOfSubjects;
      this.metaInfo.numberOfVisits = this.metaEditForm.numberOfVisits;
      this.metaInfo.studyMetaDescription = this.metaEditForm.studyMetaDescription;
    },
    toggleMetaInfo() {
      this.metaInfoCollapsed = !this.metaInfoCollapsed;
    },
    // Reinitialization Confirmation Methods
    confirmReinit() {
      this.totalForms = this.pendingMetaEdit.numberOfForms;
      this.forms = [];
      for (let i = 0; i < this.totalForms; i++) {
        this.forms.push({
          formName: `Form${i + 1}`,
          sections: JSON.parse(JSON.stringify(this.defaultFormStructure)),
        });
      }
      this.currentFormIndex = 0;
      this.activeSection = 0;
      this.updateMetaData();
      this.showReinitConfirm = false;
      this.showMetaEditDialog = false;
      this.pendingMetaEdit = null;
    },
    cancelReinit() {
      this.showReinitConfirm = false;
      this.pendingMetaEdit = null;
    },
  },
};
</script>

<style lang="scss" scoped>
@import "@/assets/styles/_base.scss";

// Additional component-specific styles
.create-form-container {
  // Use full width and a light background
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  background-color: $light-background; // from your _variables.scss
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

/* Meta Information Section */
.meta-info-container {
  background: white;
  border: 1px solid $border-color;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  transition: padding 0.3s ease, font-size 0.3s ease;
  &.collapsed {
    padding: 5px 10px;
    font-size: 12px;
  }
}
.meta-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.meta-actions {
  display: flex;
  gap: 10px;
}
.btn-meta-edit,
.btn-meta-toggle {
  @include button-reset;
  background: $secondary-color;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  padding: 5px 8px;
  cursor: pointer;
  transition: background 0.3s ease;
  &:hover {
    background: $secondary-hover;
  }
}
.meta-info-container p {
  margin: 5px 0;
  font-size: 14px;
  color: $text-color;
}

/* Main Content Layout */
.scratch-form-content {
  display: flex;
  flex-wrap: nowrap;
  justify-content: space-between;
  gap: 20px;
}

/* Form Area */
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
  border: none;
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

/* Form Section */
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

/* Form Actions */
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

/* Icon Button */
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

/* Available Fields Section */
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

/* Modal Dialogs */
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
}
.modal-actions button {
  flex: 1;
}

/* Input Dialog Modal */
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

/* Meta Edit Modal */
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

/* Constraints Edit Modal */
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

/* Responsive Design */
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
