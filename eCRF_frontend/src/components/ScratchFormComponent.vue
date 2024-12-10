<template>
  <div class="create-form-container">
    <div class="header-container">
      <button @click="goBack" class="btn-back">⬅ Back</button>
      <h1>Create Form from Scratch</h1>
    </div>

    <div class="scratch-form-content">
      <!-- Form Area (Left) -->
      <div class="form-area">
        <h2>Form Preview</h2>
        <div
          v-for="(section, sectionIndex) in formSections"
          :key="sectionIndex"
          class="form-section"
          :class="{ active: activeSection === sectionIndex }"
          @click.self="setActiveSection(sectionIndex)"
        >
          <!-- Section Header -->
          <div class="section-header">
            <h3>{{ section.title }}</h3>
            <div class="field-actions">
              <button
                @click.prevent="editSection(sectionIndex)"
                class="icon-button edit-button"
              >
                <i class="fas fa-edit"></i>
              </button>
              <button
                @click.prevent="addNewSectionBelow(sectionIndex)"
                class="icon-button add-button"
              >
                <i class="fas fa-plus"></i>
              </button>
              <button
                @click.prevent="copySection(sectionIndex)"
                class="icon-button copy-button"
              >
                <i class="fas fa-copy"></i>
              </button>
              <button
                @click.prevent="deleteSection(sectionIndex)"
                class="icon-button delete-button"
              >
                <i class="fas fa-trash"></i>
              </button>
              <button
                @click.prevent="toggleSection(sectionIndex)"
                class="icon-button collapse-button"
              >
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
                  <button
                    @click.prevent="editField(sectionIndex, fieldIndex)"
                    class="icon-button edit-button"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button
                    @click.prevent="addSimilarField(sectionIndex, fieldIndex)"
                    class="icon-button add-button"
                  >
                    <i class="fas fa-plus"></i>
                  </button>
                  <button
                    @click.prevent="removeField(sectionIndex, fieldIndex)"
                    class="icon-button delete-button"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </div>

              <div class="field-box">
                <!-- Render Fields Dynamically -->
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
                <div v-if="field.type === 'paragraph'" class="paragraph-field">
                  <p>{{ field.content }}</p>
                </div>
                <button v-if="field.type === 'button'" type="button" class="form-button">
                  {{ field.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button @click.prevent="addNewSection" class="btn-add-section">+ Add Section</button>
          <button @click.prevent="clearForm" class="btn-clear">Clear Form</button>
          <button @click.prevent="submitForm" class="btn-submit">Submit Form</button>
        </div>
      </div>

      <!-- Available Fields Area (Right) -->
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
      generalFields: [],
      specializedFieldSections: [],
      activeSection: 0,
      activeTab: "general",
    };
  },
  async created() {
    await this.loadAvailableFields();
  },
  methods: {
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
      this.$router.back();
    },
    toggleSection(sectionIndex) {
  this.formSections.forEach((section, index) => {
    if (index === sectionIndex) {
      section.collapsed = !section.collapsed;
      if (!section.collapsed) {
        this.setActiveSection(sectionIndex); // Set the active section if expanded
      }
    } else {
      section.collapsed = true; // Collapse all other sections
    }
  });
},
    setActiveSection(sectionIndex) {
      this.activeSection = sectionIndex;
    },
    addFieldToActiveSection(field) {
  const section = this.formSections[this.activeSection];
  if (section.collapsed) {
    this.toggleSection(this.activeSection); // Expand the active section if collapsed
  }
  section.fields.push({ ...field, name: `${field.type}_${Date.now()}` }); // Ensure unique field name
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

  // Create a deep copy of the section
  const newSection = JSON.parse(JSON.stringify(sectionToCopy));

  // Modify the copied section's title and fields
  newSection.title = `${sectionToCopy.title} (Copy)`;
  newSection.fields = sectionToCopy.fields.map((field) => ({
    ...field,
    name: `${field.name}_copy_${Date.now()}`, // Ensure unique field name
  }));
  newSection.collapsed = true; // Collapse the new section initially

  // Insert the copied section into the list
  this.formSections.splice(sectionIndex + 1, 0, newSection);

  // Automatically expand the copied section
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
        field.label = newLabel;
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
/* Main container for the page */
.create-form-container {
  max-width: 1200px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
  color: #333;
}

/* Layout handling for the main content */
.scratch-form-content {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: 20px;
  flex-wrap: wrap; /* Enables wrapping for smaller screens */
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  cursor: pointer;
  font-size: 16px;
}
.general-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.collapse-button {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.field-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}
/* Form Preview (Left Side) */
.form-area {
  flex: 3;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 10px;
  position: relative;
  overflow: hidden; /* Prevents content overflow */
  word-wrap: break-word; /* Wraps long content */
}
/* Highlight active section with a brighter background and bold border */
.form-section {
  transition: all 0.3s ease;
  filter: brightness(1); /* Default reduced brightness */
}

.form-section.active {
  filter: brightness(1); /* Full brightness for active section */
  border: 1px solid #007bff; /* Highlight border */
  background-color: #e7f3ff; /* Subtle background color */
}

/* Collapse animation for sections */
.section-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease-in-out;
}

.form-section:not(.active) .section-content {
  max-height: 0;
}

.form-section.active .section-content {
  max-height: 1000px; /* Large enough to fit expanded content */
}

/* Collapse animation for sections */
.section-content {
  transition: max-height 0.3s ease-in-out;
}
.form-area form {
  display: flex;
  flex-direction: column; /* Ensures fields are stacked vertically */
  gap: 15px; /* Adds consistent spacing between fields */
}

/* Field Layout */
.field-layout {
  border: 1px solid #ddd;
  margin-bottom: 15px;
  padding: 15px;
  border-radius: 5px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Optional shadow for separation */
}

/* Handles overflow issues for dynamically added fields */
.field-box {
  width: 100%; /* Ensures the field takes full width of its container */
  max-width: 100%; /* Prevents exceeding container width */
  padding: 10px;
  background-color: #fdfdfd;
  border-radius: 5px;
}

/* Input field styles */
input,
textarea,
select {
  width: 100%; /* Ensures the field fills the container */
  padding: 10px;
  margin-top: 5px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #007bff;
  outline: none;
}

/* Actions for editing fields (add/edit/delete buttons) */
.field-actions {
  display: flex;
  gap: 10px;
}

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

.icon-pencil::before {
  content: "✏️"; /* Pencil for edit */
}

.icon-plus::before {
  content: "➕"; /* Plus for add */
}

.icon-trash::before {
  content: "🗑️"; /* Trash for delete */
}

/* Right-side available fields section */
.available-fields {
  flex: 1;
  padding: 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 10px;
  max-width: 300px; /* Prevents the available fields from growing too wide */
  overflow: auto; /* Ensures scrollable content if needed */
}

.tabs {
  display: flex;
  justify-content: space-around;
  margin-bottom: 15px;
}

.tabs button {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
}

.tabs button.active {
  background-color: #007bff;
  color: white;
  border: none;
}

.tabs button:not(.active):hover {
  background-color: #f4f4f4;
}

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
}

.available-field-button i {
  font-size: 18px;
  color: #007bff;
}

.available-field-button:hover {
  background-color: #e0e0e0;
}

/* Form action buttons (Submit and Clear) */
.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  gap: 20px;
}

.btn-clear {
  background-color: #ffc107;
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 16px;
}

.btn-clear:hover {
  background-color: #e0a800;
}

.btn-submit {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 16px;
}

.btn-submit:hover {
  background-color: #0056b3;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .scratch-form-content {
    flex-direction: column; /* Stacks the form and available fields */
  }

  .form-area {
    max-width: 100%;
  }

  .available-fields {
    max-width: 100%;
  }
}
</style>
