<template>
  <div class="create-form-container">
    <h1>Create Form from Scratch</h1>

    <div class="scratch-form-content">
      <!-- Form Area (Left) -->
      <div class="form-area">
        <h2>Form Preview</h2>
        <form>
          <div v-for="(field, index) in formFields" :key="index" class="form-group">
            <div class="field-header">
              <label v-if="field.type !== 'button'" :for="field.name">{{ field.label }}</label>
              <div class="field-actions">
                <button
                  @click.prevent="editField(index)"
                  class="icon-button action-button edit-button"
                >
                  <i class="icon-pencil"></i> Edit
                </button>
                <button
                  @click.prevent="addSimilarField(index)"
                  class="icon-button action-button add-button"
                >
                  <i class="icon-plus"></i> Add
                </button>
                <button
                  @click.prevent="removeField(index)"
                  class="icon-button action-button delete-button"
                >
                  <i class="icon-trash"></i> Delete
                </button>
              </div>
            </div>

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
            <div v-if="field.type === 'checkbox'">
              <label>
                <input type="checkbox" v-model="field.value" /> {{ field.label }}
              </label>
            </div>
            <div v-if="field.type === 'radio'" class="radio-group">
              <label v-for="(option, i) in field.options" :key="option">
                <input
                  type="radio"
                  :name="field.name"
                  v-model="field.value"
                  :value="option"
                />
                {{ option }}
                <button @click.prevent="editRadioOption(index, i)" class="edit-button">
                  Edit
                </button>
                <button @click.prevent="removeRadioOption(index, i)" class="delete-button">
                  Remove
                </button>
              </label>
              <button @click.prevent="addRadioOption(index)" class="add-button">Add Option</button>
            </div>
            <div v-if="field.type === 'paragraph'" class="paragraph-field">
              <p>{{ field.content }}</p>
              <button @click.prevent="editParagraph(index)" class="edit-button">
                Edit Paragraph
              </button>
            </div>
            <button v-if="field.type === 'button'" type="button" class="form-button">
              {{ field.label }}
            </button>
          </div>
        </form>

        <!-- Fixed Position for Clear and Submit Buttons -->
        <div class="form-actions">
          <button @click.prevent="clearForm" class="btn-clear">Clear Form</button>
          <button @click.prevent="submitForm" class="btn-submit">Submit Form</button>
        </div>
      </div>

      <!-- Available Fields Area (Right) -->
      <div class="available-fields">
        <h2>Available Fields</h2>
        <div class="field-buttons">
          <button
            v-for="field in availableFields"
            :key="field.type"
            class="available-field-button"
            @click="addField(field)"
          >
            <i :class="field.icon"></i> {{ field.label }}
          </button>
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
      availableFields: [], // List of available fields
      formFields: [], // Fields added to the form
    };
  },
  async created() {
    await this.loadAvailableFields();
  },
  methods: {
    async loadAvailableFields() {
      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/available-fields");
        this.availableFields = response.data;
      } catch (error) {
        console.error("Error loading available fields:", error.response?.data || error.message);
      }
    },
    addField(field) {
      const newField = { ...field, name: `${field.type}_${Date.now()}` };
      this.formFields.push(newField);
    },
    removeField(index) {
      this.formFields.splice(index, 1);
    },
    editField(index) {
      const newLabel = prompt("Enter new label for the field:", this.formFields[index].label);
      if (newLabel !== null) {
        this.formFields[index].label = newLabel;
      }
    },
    addSimilarField(index) {
      const originalField = this.formFields[index];
      const newField = { ...originalField, name: `${originalField.name}_${Date.now()}` };
      this.formFields.splice(index + 1, 0, newField);
    },
    editRadioOption(fieldIndex, optionIndex) {
      const newOption = prompt(
        "Enter new value for the option:",
        this.formFields[fieldIndex].options[optionIndex]
      );
      if (newOption !== null) {
        this.formFields[fieldIndex].options.splice(optionIndex, 1, newOption);
      }
    },
    removeRadioOption(fieldIndex, optionIndex) {
      this.formFields[fieldIndex].options.splice(optionIndex, 1);
    },
    addRadioOption(fieldIndex) {
      const newOption = prompt("Enter a new option:");
      if (newOption) {
        this.formFields[fieldIndex].options.push(newOption);
      }
    },
    editParagraph(index) {
      const newContent = prompt(
        "Enter new content for the paragraph:",
        this.formFields[index].content
      );
      if (newContent !== null) {
        this.formFields[index].content = newContent;
      }
    },
    clearForm() {
      if (confirm("Are you sure you want to clear the form?")) {
        this.formFields = [];
      }
    },
    submitForm() {
      console.log("Form submitted with data:", this.formFields);
      alert("Form submitted successfully!");
    },
  },
};
</script>

<style scoped>
/* Reused CreateFormComponent Styles */
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

.scratch-form-content {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

.form-area {
  flex: 3;
  padding: 20px;
  margin-right: 20px;
  background-color: #f9f9f9;
  border-radius: 10px;
  position: relative;
}
.btn-clear {
  background-color: #ffc107;
  color: white;
  border: 50px;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
}
.btn-clear:hover {
  background-color: #e0a800;
}

.btn-submit:hover {
  background-color: #0056b3;
}

.available-fields {
  flex: 1;
  padding: 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 10px;
}

.field-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.available-field-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background-color: #f4f4f4;
  border: 1px solid #ccc;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.available-field-button:hover {
  background-color: #e0e0e0;
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
  border: 5px;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
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
