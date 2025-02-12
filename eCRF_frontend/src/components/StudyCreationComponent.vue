<template>
  <div class="study-creation-container">
    <h1>Create a New Study</h1>

    <div v-if="studyModels">
      <div v-for="(category, categoryName) in studyModels" :key="categoryName" class="category-section">
        <h2>{{ categoryName }}</h2>
        <ul>
          <li v-for="(model, modelName) in category" :key="modelName">
            <strong>{{ model.name }}</strong> - {{ model.description }}
            <button @click="viewYamlFile(categoryName, modelName)">View Details</button>
          </li>
        </ul>
      </div>
    </div>

    <p v-else>Loading study models...</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StudyCreationComponent",
  data() {
    return {
      studyModels: null
    };
  },
  async created() {
    await this.loadStudyModels();
  },
  computed: {
    token() {
      return this.$store.state.token;
    }
  },
  methods: {
    async loadStudyModels() {
      if (!this.token) {
        alert("Authentication error: No token found. Please log in again.");
        this.$router.push("/login");
        return;
      }

      try {
        const response = await axios.get("http://127.0.0.1:8000/forms/models", {
          headers: {
            Authorization: `Bearer ${this.token}`,
            "Accept": "application/json",
          },
        });

        this.studyModels = response.data;
      } catch (error) {
        console.error("Error loading study models:", error.response?.data || error);
      }
    },
    viewYamlFile(category, fileName) {
      this.$router.push(`/dashboard/view-yaml/${category}/${fileName}`);
    }
  }
};
</script>

<style scoped>
.study-creation-container {
  max-width: 900px;
  margin: auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1, h2 {
  text-align: center;
}

.category-section {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 5px;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  padding: 10px;
  cursor: pointer;
  background-color: #e9e9e9;
  border-radius: 5px;
  margin-bottom: 5px;
}

li:hover {
  background-color: #d1d1d1;
}

.form-group {
  margin-bottom: 10px;
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
