<template>
  <div class="saved-study-container">
    <h1>Saved Study Preview</h1>

    <div v-if="!matrix">
      <p>No saved protocol found. Please save one first.</p>
    </div>

    <div v-else>
      <!-- Visit Navigator -->
      <div v-if="matrix.visits.length > 1" class="nav-bar">
        <button
          type="button"
          @click="prevVisit"
          :disabled="currentVisitIndex === 0"
        >&lt;</button>
        <span class="nav-label">
          Visit: {{ currentVisitIndex + 1 }} / {{ matrix.visits.length }}
        </span>
        <button
          type="button"
          @click="nextVisit"
          :disabled="currentVisitIndex === matrix.visits.length - 1"
        >&gt;</button>
      </div>

      <!-- Current Visit Name -->
      <h2 class="visit-name">
        Visit: {{ matrix.visits[currentVisitIndex].name }}
      </h2>

      <!-- Group Navigator -->
      <div v-if="matrix.groups.length > 1" class="nav-bar group-nav">
        <button
          type="button"
          @click="prevGroup"
          :disabled="currentGroupIndex === 0"
        >&lt;</button>
        <span class="nav-label">
          Group: {{ currentGroupIndex + 1 }} / {{ matrix.groups.length }}
        </span>
        <button
          type="button"
          @click="nextGroup"
          :disabled="currentGroupIndex === matrix.groups.length - 1"
        >&gt;</button>
      </div>

      <!-- Current Group Name -->
      <h3 class="group-name">
        Group: {{ matrix.groups[currentGroupIndex].name }}
      </h3>

      <!-- Assigned Sections or None -->
      <div class="content-block">
        <div v-if="assignedModels(currentVisitIndex, currentGroupIndex).length">
          <FormPreview :form="buildForm(currentVisitIndex, currentGroupIndex)" />
        </div>
        <div v-else class="no-sections">
          <em>No sections assigned to this visit/group.</em>
        </div>
      </div>
    </div>

    <div class="actions">
      <button type="button" class="btn-option" @click="goBack">
        Back
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import FormPreview from "@/components/FormPreview.vue";

export default {
  name: "SavedStudyView",
  components: { FormPreview },
  setup() {
    const router = useRouter();
    const matrix = ref(null);

    const currentVisitIndex = ref(0);
    const currentGroupIndex = ref(0);

    onMounted(() => {
      const json = localStorage.getItem("protocolStudy");
      if (json) matrix.value = JSON.parse(json);
    });

    function assignedModels(vIdx, gIdx) {
      if (!matrix.value) return [];
      return matrix.value.selectedModels.filter(
        (_, mIdx) => matrix.value.assignments[mIdx][vIdx][gIdx]
      );
    }

    function buildForm(vIdx, gIdx) {
      const visitName = matrix.value.visits[vIdx].name;
      const groupName = matrix.value.groups[gIdx].name;
      const sections = assignedModels(vIdx, gIdx).map(model => ({
        title:  model.title,
        fields: model.fields
      }));
      return {
        formName: `Preview: ${visitName} / ${groupName}`,
        sections
      };
    }

    function prevVisit() {
      if (currentVisitIndex.value > 0) {
        currentVisitIndex.value--;
        currentGroupIndex.value = 0;
      }
    }
    function nextVisit() {
      if (currentVisitIndex.value < matrix.value.visits.length - 1) {
        currentVisitIndex.value++;
        currentGroupIndex.value = 0;
      }
    }
    function prevGroup() {
      if (currentGroupIndex.value > 0) currentGroupIndex.value--;
    }
    function nextGroup() {
      if (currentGroupIndex.value < matrix.value.groups.length - 1)
        currentGroupIndex.value++;
    }

    function goBack() {
      router.back();
    }

    return {
      matrix,
      currentVisitIndex,
      currentGroupIndex,
      assignedModels,
      buildForm,
      prevVisit,
      nextVisit,
      prevGroup,
      nextGroup,
      goBack
    };
  }
};
</script>

<style scoped>
.saved-study-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
  font-family: Arial, sans-serif;
}

.nav-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 1rem 0;
}
.group-nav {
  margin-top: 0.5rem;
}
.nav-bar button {
  background: #ddd;
  border: none;
  padding: 0.5rem 1rem;
  font-size: 1rem;
  cursor: pointer;
}
.nav-bar button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.nav-label {
  margin: 0 1rem;
  font-weight: bold;
}

.visit-name {
  text-align: center;
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.group-name {
  text-align: center;
  margin-bottom: 1rem;
  font-size: 1.25rem;
}

.content-block {
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 6px;
  min-height: 200px;
}

.no-sections {
  color: #777;
  text-align: center;
  margin-top: 2rem;
}

.actions {
  margin-top: 2rem;
  text-align: right;
}

.btn-option {
  padding: 8px 16px;
  background: #eee;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}
</style>
