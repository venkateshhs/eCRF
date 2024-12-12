<template>
  <div class="form-detail-container">
    <h1>View Saved Form</h1>
    <div v-if="form">
      <h2>{{ form.form_name }}</h2>
      <div v-for="(section, sectionIndex) in form.form_structure" :key="sectionIndex" class="form-section">
        <h3>{{ section.title }}</h3>
        <div v-for="(field, fieldIndex) in section.fields" :key="fieldIndex" class="form-group">
          <label :for="field.name">{{ field.label }}</label>
          <div class="field-box">
            <!-- Render fields dynamically -->
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
                <input type="radio" :name="field.name" v-model="field.value" :value="option" />
                {{ option }}
              </label>
            </div>
            <p v-if="field.type === 'paragraph'">{{ field.content }}</p>
          </div>
        </div>
      </div>
    </div>
    <p v-else>Loading form...</p>
    <button @click="goBack" class="btn-back">Back</button>
  </div>
</template>
<script>
import axios from "axios";

export default {
  name: "FormDetailComponent",
  data() {
    return {
      form: null, // The loaded form
    };
  },
  computed: {
    token() {
      return this.$store.state.token; // Retrieve the token from Vuex
    },
  },
  async created() {
    const formId = this.$route.params.id; // Get the form ID from route params
    await this.loadForm(formId);
  },
  methods: {
    async loadForm(formId) {
      try {
        const response = await axios.get(`http://127.0.0.1:8000/forms/${formId}`, {
          headers: {
            Authorization: `Bearer ${this.token}`,
          },
        });
        this.form = response.data;
      } catch (error) {
        console.error("Error loading form:", error.response?.data || error.message);
        alert("Failed to load the form.");
      }
    },
    goBack() {
      this.$router.push("/saved-forms"); // Navigate back to saved forms
    },
  },
};
</script>
<style scoped>
.form-detail-container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1, h2, h3 {
  text-align: center;
  color: #333;
}

.form-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.form-group {
  margin-bottom: 15px;
}

.field-box input,
.field-box textarea,
.field-box select {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

.btn-back {
  margin-top: 20px;
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.btn-back:hover {
  background-color: #0056b3;
}
</style>
