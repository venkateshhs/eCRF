<template>
  <div class="create-form-container">
    <div class="header-container">
      <button @click="goBack" class="btn-back">
        <i class="fas fa-arrow-left"></i> Back
      </button>
      <h1>Create Form from Scratch</h1>
    </div>

    <div class="scratch-form-content">
      <!-- Form Area -->
      <div class="form-area">
        <!-- Editable Form Name at Top Center -->
        <div class="form-heading-container">
          <input
            type="text"
            v-model="formName"
            class="form-name-input heading-input"
            placeholder="Untitled Form"
          />
        </div>

        <!-- Render Form Sections -->
        <div
          v-for="(section, sectionIndex) in formSections"
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
              <button @click.prevent="editSection(sectionIndex)" class="icon-button">
                <i class="fas fa-edit"></i>
              </button>
              <button @click.prevent="addNewSectionBelow(sectionIndex)" class="icon-button">
                <i class="fas fa-plus"></i>
              </button>
              <button @click.prevent="copySection(sectionIndex)" class="icon-button">
                <i class="fas fa-copy"></i>
              </button>
              <button @click.prevent="deleteSection(sectionIndex)" class="icon-button">
                <i class="fas fa-trash"></i>
              </button>
              <button @click.prevent="toggleSection(sectionIndex)" class="icon-button">
                <i :class="section.collapsed ? 'fas fa-angle-down' : 'fas fa-angle-up'"></i>
              </button>
            </div>
          </div>

          <!-- Section Content -->
          <div v-if="!section.collapsed" class="section-content">
            <div
              v-for="(field, fieldIndex) in section.fields"
              :key="fieldIndex"
              class="form-group"
            >
              <div class="field-header">
                <label v-if="field.type !== 'button'" :for="field.name">{{ field.label }}</label>
                <div class="field-actions">
                  <button @click.prevent="editField(sectionIndex, fieldIndex)" class="icon-button">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button @click.prevent="addSimilarField(sectionIndex, fieldIndex)" class="icon-button">
                    <i class="fas fa-plus"></i>
                  </button>
                  <button @click.prevent="removeField(sectionIndex, fieldIndex)" class="icon-button">
                    <i class="fas fa-trash"></i>
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
                <button v-if="field.type === 'button'" type="button" class="form-button">
                  {{ field.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Form Actions: Horizontally Aligned -->
        <div class="form-actions">
          <div class="button-row">
            <button @click.prevent="addNewSection" class="btn-option">+ Add Section</button>
            <button @click.prevent="clearForm" class="btn-option">Clear Form</button>
            <button @click.prevent="saveForm" class="btn-primary">Save Form</button>
            <button @click="navigateToSavedForms" class="btn-option">View Saved Forms</button>
          </div>
        </div>
      </div>

      <!-- Available Fields Area -->
      <div class="available-fields">
        <h2>Available Fields</h2>
        <div class="tabs">
          <button
            :class="{ active: activeTab === 'general' }"
            @click="activeTab = 'general'"
          >
            General Fields
          </button>
          <button
            :class="{ active: activeTab === 'specialized' }"
            @click="activeTab = 'specialized'"
          >
            Specialized Fields
          </button>
        </div>

        <!-- General Fields Tab -->
        <div v-if="activeTab === 'general'" class="general-fields">
          <div
            v-for="(field, index) in generalFields"
            :key="index"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
          >
            <i :class="field.icon"></i> {{ field.label }}
          </div>
        </div>

        <!-- Specialized Fields Tab -->
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
              >
                <i :class="field.icon"></i> {{ field.label }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "ScratchFormComponent",
  data() {
    return {
      formSections: [{ title: "Default Section", fields: [], collapsed: false }],
      savedForms: [],
      generalFields: [],
      specializedFieldSections: [],
      activeSection: 0,
      activeTab: "general",
      formName: "Untitled Form",
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
  },
  async mounted() {
    await this.loadAvailableFields();
  },
  methods: {
    navigateToSavedForms() {
      this.$router.push("/saved-forms");
    },
    async saveForm() {
      if (!this.token) {
        alert("Authentication error: No token found. Please log in again.");
        this.$router.push("/login");
        return;
      }
      const formData = {
        form_name: this.formName || "Untitled Form",
        form_structure: this.formSections,
      };
      try {
        await axios.post("http://127.0.0.1:8000/forms/save-form", formData, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        alert(`Form "${this.formName}" saved successfully!`);
      } catch (error) {
        if (error.response?.status === 401) {
          alert("Your session has expired. Please log in again.");
          this.$router.push("/login");
        } else {
          console.error("Error saving form:", error);
          alert("Failed to save form. Please try again.");
        }
      }
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
    toggleSection(sectionIndex) {
      this.formSections.forEach((section, index) => {
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
      const section = this.formSections[this.activeSection];
      if (section.collapsed) {
        this.toggleSection(this.activeSection);
      }
      section.fields.push({ ...field, name: `${field.type}_${Date.now()}` });
    },
    addNewSection() {
      this.formSections.push({
        title: `New Section ${this.formSections.length + 1}`,
        fields: [],
        collapsed: true,
      });
      this.toggleSection(this.formSections.length - 1);
    },
    addNewSectionBelow(index) {
      this.formSections.splice(index + 1, 0, {
        title: `New Section ${index + 2}`,
        fields: [],
        collapsed: true,
      });
      this.toggleSection(index + 1);
    },
    deleteSection(index) {
      if (confirm("Are you sure you want to delete this section?")) {
        this.formSections.splice(index, 1);
        if (this.activeSection >= index) {
          this.activeSection = Math.max(0, this.activeSection - 1);
        }
        if (this.formSections.length > 0) {
          this.toggleSection(this.activeSection);
        }
      }
    },
    editSection(index) {
      const newTitle = prompt("Enter a new title for this section:", this.formSections[index].title);
      if (newTitle) {
        this.formSections[index].title = newTitle;
      }
    },
    copySection(sectionIndex) {
      const sectionToCopy = this.formSections[sectionIndex];
      const newSection = JSON.parse(JSON.stringify(sectionToCopy));
      newSection.title = `${sectionToCopy.title} (Copy)`;
      newSection.fields = sectionToCopy.fields.map((field) => ({
        ...field,
        name: `${field.name}_copy_${Date.now()}`,
      }));
      newSection.collapsed = true;
      this.formSections.splice(sectionIndex + 1, 0, newSection);
      this.toggleSection(sectionIndex + 1);
    },
    clearForm() {
      if (confirm("Are you sure you want to clear the form?")) {
        this.formSections = [{ title: "Default Section", fields: [], collapsed: false }];
        this.activeSection = 0;
      }
    },
    submitForm() {
      console.log("Form submitted with data:", this.formSections);
      alert("Form submitted successfully!");
    },
    editField(sectionIndex, fieldIndex) {
      const field = this.formSections[sectionIndex].fields[fieldIndex];
      const newLabel = prompt("Enter new label for the field:", field.label);
      if (newLabel) {
        this.formSections[sectionIndex].fields[fieldIndex].label = newLabel;
      }
    },
    addSimilarField(sectionIndex, fieldIndex) {
      const field = this.formSections[sectionIndex].fields[fieldIndex];
      const newField = { ...field, name: `${field.type}_${Date.now()}` };
      this.formSections[sectionIndex].fields.splice(fieldIndex + 1, 0, newField);
    },
    removeField(sectionIndex, fieldIndex) {
      this.formSections[sectionIndex].fields.splice(fieldIndex, 1);
    },
  },
};
</script>

<style scoped>
/* Container: Full width, full viewport height */
.create-form-container {
  width: 100%;
  min-height: 100vh;
  margin: 0 auto;
  padding: 20px;
  background-color: #f9f9f9;
}

/* Header */
.header-container {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.btn-back {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #555;
}

h1 {
  font-size: 24px;
  font-weight: 500;
  color: #333;
  flex: 1;
  text-align: center;
}

/* Scratch Form Content */
.scratch-form-content {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

/* Form Area */
.form-area {
  flex: 3;
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #ddd;
}

/* Editable Form Heading */
.form-heading-container {
  text-align: center;
  margin-bottom: 20px;
}

.heading-input {
  font-size: 22px;
  font-weight: 500;
  text-align: center;
  border: none;
  border-bottom: 1px solid #ccc;
  outline: none;
  width: 100%;
  max-width: 400px;
}

/* Form Section */
.form-section {
  padding: 15px;
  border-bottom: 1px solid #ddd;
  transition: all 0.3s ease;
}

.form-section.active {
  background-color: #e7f3ff;
  border-left: 3px solid #444;
}

/* Section Header */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-actions {
  display: flex;
  gap: 10px;
}

/* Field Box */
.field-box {
  margin-top: 10px;
}

/* Input Styles */
input,
textarea,
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin-top: 5px;
  box-sizing: border-box;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #444;
  outline: none;
}

/* Form Actions: Horizontal Button Row */
.form-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}

.form-name-input {
  flex: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

/* Button Row */
.button-row {
  display: flex;
  gap: 15px;
  width: 100%;
}

/* Minimalist Buttons */
.btn-option {
  background: #f4f4f4;
  color: #333;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  text-align: center;
  cursor: pointer;
  transition: background 0.3s ease;
  flex: 1;
}

.btn-option:hover {
  background: #e0e0e0;
}

.btn-primary {
  background-color: #444;
  color: white;
  padding: 10px;
  border: none;
  border-radius: 5px;
  text-align: center;
  cursor: pointer;
  transition: background 0.3s ease;
  flex: 1;
}

.btn-primary:hover {
  background-color: #333;
}

/* Icon Button */
.icon-button {
  background: none;
  border: none;
  padding: 5px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  transition: background-color 0.3s ease;
}

.icon-button:hover {
  background-color: #f4f4f4;
}

/* Available Fields Section */
.available-fields {
  flex: 1;
  background-color: #fff;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  width: 320px;
  max-height: calc(100vh - 60px);
  overflow-y: auto;
}

/* Tabs for Available Fields */
.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.tabs button {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  background: #f4f4f4;
  flex: 1;
}

.tabs button.active {
  background-color: #444;
  color: white;
  border: none;
}

.tabs button:not(.active):hover {
  background-color: #e0e0e0;
}

/* Available Field Button */
.available-field-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  font-size: 14px;
  background-color: #f9f9f9;
  border: 1px solid #ccc;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-bottom: 10px;
}

.available-field-button i {
  font-size: 18px;
  color: #555;
}

.available-field-button:hover {
  background-color: #e0e0e0;
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
