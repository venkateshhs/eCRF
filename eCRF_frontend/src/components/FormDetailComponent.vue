<template>
  <div class="study-detail-container" v-if="study">
    <!-- Main Heading: Study Name -->
    <h1 class="study-name">{{ study.metadata?.study_name }}</h1>

    <!-- Details Header with Toggle Button -->
    <div class="details-header">
      <span class="header-text">Study Details</span>
      <button class="toggle-btn" @click="toggleDetails">
        <i :class="detailsCollapsed ? icons.toggleDown : icons.toggleUp"></i>
      </button>
    </div>

    <!-- Details Section (Collapsible) -->
    <div class="details-section" v-show="!detailsCollapsed">
      <p><strong>Study ID:</strong> {{ study.metadata?.id }}</p>
      <p><strong>Description:</strong> {{ study.metadata?.study_description }}</p>
      <p>
        <strong>Number of Forms:</strong>
        {{ study.metadata?.numberOfForms || study.content?.study_data?.meta_info?.numberOfForms || 1 }}
      </p>
      <p>
        <strong>Study Type:</strong>
        {{ study.content?.study_data?.meta_info?.studyType || 'Custom' }}
      </p>
      <p>
        <strong>Number of Subjects:</strong>
        {{ study.content?.study_data?.meta_info?.numberOfSubjects || 'N/A' }}
      </p>
      <p>
        <strong>Number of Visits per Subject:</strong>
        {{ study.content?.study_data?.meta_info?.numberOfVisits || 'N/A' }}
      </p>
      <p>
        <strong>Study Meta Description:</strong>
        {{ study.content?.study_data?.meta_info?.studyMetaDescription || 'N/A' }}
      </p>
      <!-- Custom Fields -->
      <div v-if="study.content?.study_data?.meta_info?.customFields?.length">
        <h4>Custom Fields</h4>
        <ul>
          <li v-for="(field, index) in study.content.study_data.meta_info.customFields" :key="'cf-' + index">
            <strong>{{ field.fieldName }}</strong>: {{ field.fieldValue }}
          </li>
        </ul>
      </div>
      <!-- Meta Custom Fields -->
      <div v-if="study.content?.study_data?.meta_info?.metaCustomFields?.length">
        <h4>Meta Custom Fields</h4>
        <ul>
          <li v-for="(field, index) in study.content.study_data.meta_info.metaCustomFields" :key="'mcf-' + index">
            <strong>{{ field.fieldName }}</strong>: {{ field.fieldValue }}
          </li>
        </ul>
      </div>
    </div>

    <!-- Forms Section -->
    <div class="forms-section" v-if="(study.content?.study_data?.forms || []).length">
      <h2>Forms ({{ study.metadata?.numberOfForms || study.content?.study_data?.meta_info?.numberOfForms || 1 }})</h2>
      <div v-for="(form, formIndex) in study.content.study_data.forms || []" :key="formIndex" class="form">
        <h3>{{ form.form_name }}</h3>
        <div v-for="(section, sectionIndex) in form.sections" :key="sectionIndex" class="form-section">
          <h4>{{ section.title }}</h4>
          <div v-for="(field, fieldIndex) in section.fields" :key="fieldIndex" class="form-field">
            <label v-if="field.type !== 'button'">{{ field.label }}</label>
            <template v-if="field.type === 'text'">
              <input type="text" v-model="field.value" :placeholder="field.placeholder" />
            </template>
            <template v-else-if="field.type === 'textarea'">
              <textarea v-model="field.value" :placeholder="field.placeholder"></textarea>
            </template>
            <template v-else-if="field.type === 'number'">
              <input type="number" v-model="field.value" :placeholder="field.placeholder" />
            </template>
            <template v-else-if="field.type === 'date'">
              <input type="date" v-model="field.value" :placeholder="field.placeholder" />
            </template>
            <template v-else-if="field.type === 'select'">
              <select v-model="field.value">
                <option v-for="option in field.options" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
            </template>
          </div>
        </div>
      </div>
    </div>

    <button @click="goBack" class="btn-back">Back</button>
  </div>
  <div v-else>
    <p>Loading study details...</p>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons"; // Ensure icons.toggleUp and icons.toggleDown are defined

export default {
  name: "StudyDetailComponent",
  data() {
    return {
      study: null,
      detailsCollapsed: false,
      icons,
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
  },
  async created() {
    const studyId = this.$route.params.id;
    await this.loadStudy(studyId);
  },
  methods: {
    async loadStudy(studyId) {
      try {
        const response = await axios.get(`http://127.0.0.1:8000/forms/studies/${studyId}`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.study = response.data;
        console.log("Loaded study:", this.study);
      } catch (error) {
        console.error("Error loading study:", error.response?.data || error.message);
        alert("Failed to load study details. Please try again.");
      }
    },
    toggleDetails() {
      this.detailsCollapsed = !this.detailsCollapsed;
    },
    goBack() {
      this.$router.push("/saved-forms");
    },
  },
};
</script>

<style scoped>
.study-detail-container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  font-family: Arial, sans-serif;
}
.study-name {
  text-align: center;
  margin-bottom: 10px;
  font-size: 28px;
  color: #333;
}
.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  margin-bottom: 10px;
}
.header-text {
  font-size: 16px;
  color: #333;
}
.toggle-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 20px;
  color: #007bff;
}
.details-section {
  background: #fff; /* Matches the main container */
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  margin-bottom: 20px;
}
.details-section p {
  margin: 5px 0;
  font-size: 14px;
  color: #555;
}
.forms-section {
  margin-top: 20px;
}
.form {
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 15px;
  margin-bottom: 15px;
  background: #fefefe;
}
.form h3 {
  margin-top: 0;
}
.form-section {
  margin-top: 10px;
  padding: 10px;
  border-top: 1px solid #ccc;
}
.form-field {
  margin-bottom: 10px;
}
.form-field label {
  font-weight: bold;
  display: block;
  margin-bottom: 5px;
}
input[type="text"],
textarea,
input[type="number"],
input[type="date"],
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}
.btn-back {
  display: block;
  margin: 20px auto 0;
  padding: 10px 20px;
  background: #007bff;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}
.btn-back:hover {
  background: #0056b3;
}
</style>
