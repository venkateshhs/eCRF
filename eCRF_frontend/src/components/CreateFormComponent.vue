<template>
  <div class="create-form-container">
    <h1>Create Form</h1>
    <form @submit.prevent="handleSubmit">
      <div v-for="(field, index) in formFields" :key="index" class="form-group">
        <label :for="field.name">{{ field.label }}</label>
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
        />
        <select v-if="field.type === 'select'" :id="field.name" v-model="field.value">
          <option v-for="option in field.options" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
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
      formFields: [], // Will hold the dynamically loaded form fields
      message: null,
      errorMessage: null,
    };
  },
  created() {
    // Load the SHACL template when the component is created
    this.loadTemplate();
  },
  methods: {
    async loadTemplate() {
      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/templates/shacl");
        console.log("SHACL template loaded:", response.data);

        // Convert SHACL shapes to form fields
        this.formFields = response.data.map((shape) => ({
          name: shape.name,
          label: shape.label,
          type: shape.type,
          value: shape.default || "",
          placeholder: shape.placeholder || "",
          options: shape.options || [],
        }));
      } catch (error) {
        console.error("Error loading SHACL template:", error.response?.data || error.message);
        this.errorMessage = "Failed to load template. Please try again.";
      }
    },
    handleSubmit() {
      console.log("Form submitted with values:", this.formFields);
      // Optionally save the form data to the backend
      this.message = "Form submitted successfully!";
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

label {
  display: block;
  font-size: 14px;
  color: #555;
  margin-bottom: 5px;
}

input,
textarea,
select {
  width: 100%;
  padding: 10px;
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

.btn-submit {
  width: 100%;
  padding: 10px;
  font-size: 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-submit:hover {
  background-color: #0056b3;
}

.success-message {
  color: green;
  font-size: 14px;
  text-align: center;
}

.error-message {
  color: red;
  font-size: 14px;
  text-align: center;
}
</style>
