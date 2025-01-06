<template>
  <div>
    <h1>Manage Study Types</h1>
    <form @submit.prevent="saveStudyType">
      <input v-model="studyType.name" placeholder="Study Type Name" required />
      <textarea v-model="studyType.description" placeholder="Description"></textarea>
      <button type="submit">Save</button>
    </form>

    <h2>Existing Study Types</h2>
    <ul>
      <li v-for="type in studyTypes" :key="type.id">
        {{ type.name }}
        <button @click="editStudyType(type)">Edit</button>
        <button @click="deleteStudyType(type.id)">Delete</button>
      </li>
    </ul>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      studyTypes: [],
      studyType: { name: "", description: "" },
    };
  },
  async created() {
    await this.loadStudyTypes();
  },
  methods: {
    async loadStudyTypes() {
      const response = await axios.get("/study-types");
      this.studyTypes = response.data;
    },
    async saveStudyType() {
      await axios.post("/study-types", this.studyType);
      this.studyType = { name: "", description: "" };
      await this.loadStudyTypes();
    },
    editStudyType(type) {
      this.studyType = { ...type };
    },
    async deleteStudyType(id) {
      await axios.delete(`/study-types/${id}`);
      await this.loadStudyTypes();
    },
  },
};
</script>
