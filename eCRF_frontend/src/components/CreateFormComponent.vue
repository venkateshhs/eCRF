
<template>
  <div class="create-form-container">
    <div class="header">
      <h1>Create Form</h1>
      <button @click="navigateToScratch" class="btn-create-from-scratch">
        Create Form from Scratch
      </button>
    </div>

    <p>Select a template:</p>
    <select v-model="selectedTemplate" @change="handleTemplateSelection">
      <option disabled value="">-- Select a Template --</option>
      <option v-for="template in templates" :key="template" :value="template">
        {{ template }}
      </option>
    </select>

    <p v-if="loadingMessage">{{ loadingMessage }}</p>

    <form v-if="formFields.length > 0" @submit.prevent="handleSubmit">
      <div v-for="(field, index) in formFields" :key="index" class="form-group">
        <div class="field-header">
          <label :for="field.name">{{ field.label }}</label>
          <div class="field-actions">
            <button type="button" @click="editField(index)" class="icon-button">
              <i class="icon-pencil"></i>
            </button>
            <button type="button" @click="addSimilarField(index)" class="icon-button">
              <i class="icon-plus"></i>
            </button>
            <button type="button" @click="removeField(index)" class="icon-button">
              <i class="icon-trash"></i>
            </button>
          </div>
        </div>

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
          v-if="field.type === 'date'"
          type="date"
          :id="field.name"
          v-model="field.value"
        />
        <input
          v-if="field.type === 'number'"
          type="number"
          :id="field.name"
          v-model="field.value"
          :placeholder="field.placeholder"
        />
      </div>
      <button type="submit" class="btn-submit">Submit</button>
    </form>

    <p v-if="message" class="success-message">{{ message }}</p>
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "CreateFormComponent",
  data() {
    return {
      templates: [], // Available SHACL templates
      selectedTemplate: "", // Currently selected template name
      formFields: [], // Dynamically loaded fields
      loadingMessage: null,
      message: null,
      errorMessage: null,
    };
  },
  async created() {
    // Fetch available templates when the component is loaded
    await this.fetchTemplates();
  },
  methods: {
    async fetchTemplates() {
      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/templates");
        this.templates = response.data.templates;
      } catch (error) {
        console.error("Error fetching templates:", error.response?.data || error.message);
        this.errorMessage = "Failed to load available templates.";
      }
    },
    async handleTemplateSelection() {
      if (!this.selectedTemplate) {
        this.formFields = [];
        this.errorMessage = "No template selected.";
        return;
      }

      this.loadingMessage = `Loading ${this.selectedTemplate}...`;
      try {
        const response = await axios.get(
          `http://127.0.0.1:8000/forms/templates/shacl`,
          {
            params: { template_name: this.selectedTemplate },
          }
        );
        this.formFields = response.data.map((field) => ({
          name: field.name,
          label: field.label,
          type: field.type,
          value: field.default || "",
          placeholder: field.placeholder || "",
          rows: field.rows || 3, // For textarea-specific attributes
        }));
        this.loadingMessage = null;
      } catch (error) {
        console.error("Error loading SHACL template:", error.response?.data || error.message);
        this.errorMessage = error.response?.data?.detail || "Failed to load template. Please try again.";
        this.formFields = [];
      }
    },
    addSimilarField(index) {
      const originalField = this.formFields[index];
      const newField = {
        ...originalField,
        name: `${originalField.name}_${Date.now()}`, // Ensure unique field name
        label: `${originalField.label} (Copy)`,
        value: "",
      };
      this.formFields.splice(index + 1, 0, newField);
    },
    editField(index) {
      const field = this.formFields[index];
      const newLabel = prompt("Enter new label for the field:", field.label);
      if (newLabel !== null) {
        this.formFields[index].label = newLabel;
      }
    },
    removeField(index) {
      if (confirm("Are you sure you want to delete this field?")) {
        this.formFields.splice(index, 1);
      }
    },
    handleSubmit() {
      console.log("Form submitted with values:", this.formFields);
      this.message = "Form submitted successfully!";
    },
    navigateToScratch() {
      this.$router.push("/dashboard/create-form-scratch");
    },
  },
};
</script>


<style scoped>
.create-form-container {
  max-width: 800px;
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

.form-group {
  margin-bottom: 20px;
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

label {
  display: block;
  font-size: 14px;
  color: #555;
}

.field-actions {
  display: flex;
  gap: 10px;
}

input {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
  margin-top: 10px;
}

input:focus {
  border-color: #007bff;
  outline: none;
}

/* Generic Button Styles */
button {
  padding: 5px 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  background-color: #f4f4f4;
  color: #333;
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

button:hover {
  background-color: #e0e0e0;
}

/* Primary Button (e.g., Submit) */
.btn-submit {
  background-color: #007bff;
  color: white;
  border: none;
  margin-top: 20px;
  width: 100%;
  font-size: 16px;
}

.btn-submit:hover {
  background-color: #0056b3;
}

/* Success Message */
.success-message {
  color: green;
  font-size: 14px;
  text-align: center;
}

/* Error Message */
.error-message {
  color: red;
  font-size: 14px;
  text-align: center;
}
/* Generic Button Styles for Icons */
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
  font-size: 16px;
}

.icon-plus::before {
  content: "➕"; /* Plus for add */
  font-size: 16px;
}

.icon-trash::before {
  content: "🗑️"; /* Trash for delete */
  font-size: 16px;
}

/* Optional: Adjust for consistency with the rest of the project */
.field-actions {
  display: flex;
  gap: 10px;
}
textarea {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
  margin-top: 10px;
}

textarea:focus {
  border-color: #007bff;
  outline: none;
}
</style>

