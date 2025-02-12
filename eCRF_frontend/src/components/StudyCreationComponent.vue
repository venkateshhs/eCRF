<template>
  <div class="study-creation-container">
    <h1>Create a New Study</h1>

    <div v-if="studyModels">
      <div v-for="(category, categoryName) in studyModels" :key="categoryName" class="category-section">
        <div class="category-header">
          <h2>{{ categoryName }}</h2>
          <button @click="toggleCategory(categoryName)" class="icon-button collapse-button">
            <i :class="expandedCategories[categoryName] ? 'fas fa-chevron-up' : 'fas fa-chevron-down'"></i>
          </button>
        </div>

        <table v-if="expandedCategories[categoryName]" class="yaml-table">
          <thead>
            <tr>
              <th>Model Name</th>
              <th>Description</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(model, modelName) in category" :key="modelName">
              <td><strong>{{ model.name }}</strong></td>
              <td>{{ getModelDescription(model) }}</td>
              <td>
                <button @click="viewYamlFile(categoryName, modelName)" class="icon-button view-button">
                  <i class="fas fa-eye"></i> View Details
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
      studyModels: null,
      expandedCategories: {}, // Track expanded state for each category
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
        this.initializeExpandedCategories();
      } catch (error) {
        console.error("Error loading study models:", error.response?.data || error);
      }
    },
    initializeExpandedCategories() {
      for (const category in this.studyModels) {
        this.$set(this.expandedCategories, category, false);
      }
    },
    toggleCategory(categoryName) {
      this.expandedCategories[categoryName] = !this.expandedCategories[categoryName];
    },
    getModelDescription(model) {
      if (model.classes) {
        const classKeys = Object.keys(model.classes);
        if (classKeys.length > 0) {
          return model.classes[classKeys[0]].description || "No description available.";
        }
      }
      return "No description available.";
    },
    viewYamlFile(category, fileName) {
      this.$router.push(`/dashboard/view-yaml/${category}/${fileName}`);
    }
  }
};
</script>

<style scoped>
/* General Layout */
.study-creation-container {
  max-width: 900px;
  margin: auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
}

/* Category Section */
.category-section {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 5px;
}

.category-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Table Styling */
.yaml-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.yaml-table th, .yaml-table td {
  border: 1px solid #ccc;
  padding: 10px;
  text-align: left;
}

.yaml-table th {
  background-color: #007bff;
  color: white;
}

.yaml-table tr:nth-child(even) {
  background-color: #f2f2f2;
}

/* Buttons */
.icon-button {
  background: none;
  border: none;
  padding: 8px 12px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  border-radius: 5px;
  transition: background-color 0.3s ease;
}

.icon-button i {
  font-size: 18px;
}

/* Collapse Button */
.collapse-button {
  background-color: transparent;
  color: #007bff;
  font-size: 20px;
  transition: transform 0.3s ease;
}

.collapse-button:hover {
  background-color: transparent;
  color: #0056b3;
}

/* View Details Button */
.view-button {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 8px 12px;
  font-size: 14px;
}

.view-button:hover {
  background-color: #0056b3;
}
</style>
