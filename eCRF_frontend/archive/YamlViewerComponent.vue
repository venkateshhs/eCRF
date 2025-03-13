<template>
  <div class="yaml-viewer">
    <h1>{{ yamlData.name }} Configuration</h1>

    <form @submit.prevent="saveForm">
      <div v-for="(field, fieldName) in yamlData.slots" :key="fieldName" class="form-group">
        <label :for="fieldName">{{ field.description }}</label>

        <!-- Text Input -->
        <input v-if="field.range === 'string'"
               type="text"
               v-model="formData[fieldName]"
               :id="fieldName"
               required />

        <!-- Number Input -->
        <input v-if="field.range === 'integer'"
               type="number"
               v-model="formData[fieldName]"
               :id="fieldName"
               required />

        <!-- Date Input -->
        <input v-if="field.range === 'date'"
               type="date"
               v-model="formData[fieldName]"
               :id="fieldName"
               required />

        <!-- Multi-valued Fields (Array Inputs) -->
        <div v-if="field.multivalued">
          <div v-for="(value, index) in formData[fieldName]" :key="index">
            <input type="text" v-model="formData[fieldName][index]" />
            <button @click="removeValue(fieldName, index)" type="button">Remove</button>
          </div>
          <button @click="addValue(fieldName)" type="button">Add</button>
        </div>

      </div>
      <button type="submit">Save</button>
    </form>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "YamlViewerComponent",
  props: ["category", "fileName"],
  data() {
    return {
      yamlData: {},
      formData: {},
    };
  },
  async created() {
    await this.loadYamlFile();
  },
  computed: {
    token() {
      return this.$store.state.token;
    }
  },
  methods: {
    async loadYamlFile() {
      if (!this.token) {
        alert("Authentication error: No token found. Please log in again.");
        this.$router.push("/login");
        return;
      }

      try {
        const response = await axios.get(`http://127.0.0.1:8000/forms/models/${this.category}/${this.fileName}`, {
          headers: {
            Authorization: `Bearer ${this.token}`,
            "Accept": "application/json",
          },
        });

        this.yamlData = response.data;
        this.initializeForm();
      } catch (error) {
        console.error("Error loading YAML file:", error.response?.data || error);
      }
    },
    initializeForm() {
      for (let fieldName in this.yamlData.slots) {
        let field = this.yamlData.slots[fieldName];

        // Initialize values based on type
        if (field.multivalued) {
          this.formData[fieldName] = [];
        } else {
          this.formData[fieldName] = field.range === "integer" ? 0 : "";
        }
      }
    },
    addValue(fieldName) {
      this.formData[fieldName].push("");
    },
    removeValue(fieldName, index) {
      this.formData[fieldName].splice(index, 1);
    },
    saveForm() {
      console.log("Form data:", this.formData);
      alert("Study configuration saved successfully!");
    }
  }
};
</script>

<style scoped>
.yaml-viewer {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  font-family: Arial, sans-serif;
}

h1 {
  text-align: center;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  font-weight: bold;
}

input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

button {
  margin-top: 10px;
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}
</style>
