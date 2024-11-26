<template>
  <div class="create-form-container">
    <h1>Create a New Form</h1>

    <!-- Form Builder -->
    <div id="form-builder"></div>

    <!-- Buttons -->
    <div class="form-actions">
      <button class="btn-save" @click="getFormData">Get Form Data</button>
    </div>

    <!-- Display Form JSON -->
    <div class="form-json" v-if="formJson">
      <h2>Generated Form JSON</h2>
      <pre>{{ formJson }}</pre>
    </div>
  </div>
</template>

<script>
export default {
  name: "CreateFormComponent",
  data() {
    return {
      formBuilder: null, // To store the formBuilder instance
      formJson: null, // To store the generated JSON
    };
  },
  mounted() {
    // Initialize the formBuilder
    this.formBuilder = window.$("#form-builder").formBuilder();
  },
  methods: {
    getFormData() {
      // Get the form data (JSON format)
      this.formJson = this.formBuilder.actions.getData("json");
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

#form-builder {
  margin-bottom: 20px;
}

.form-actions {
  text-align: center;
}

.btn-save {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-save:hover {
  background-color: #0056b3;
}

.form-json {
  margin-top: 20px;
  padding: 10px;
  background-color: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 5px;
}

pre {
  font-size: 14px;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>