<template>
  <div v-if="loading" class="loading">
    <p>Loading shared data…</p>
  </div>
  <div v-else-if="error" class="error">
    <p>{{ error }}</p>
  </div>
  <div v-else-if="info && info.study && info.study.metadata" class="share-link-viewer">
    <h2>Shared Data Entry View</h2>
    <div class="bread-crumb">
      <strong>Study:</strong> {{ info.study.metadata.study_name }} &nbsp;|&nbsp;
      <strong>Subject:</strong> {{ info.subject_index + 1 }} &nbsp;|&nbsp;
      <strong>Visit:</strong> {{ info.study.content.study_data.visits[info.visit_index]?.name || 'Unknown Visit' }} &nbsp;|&nbsp;
      <strong>Group:</strong> {{ info.study.content.study_data.groups[info.group_index]?.name || 'Unknown Group' }}
    </div>
    <div v-if="modelIndices.length">
      <div v-for="mIdx in modelIndices" :key="mIdx" class="section-block">
        <h3>{{ models[mIdx].title }}</h3>
        <div v-for="(field, fIdx) in models[mIdx].fields" :key="fIdx" class="form-field">
          <label>{{ field.label }}</label>
          <input
            v-if="field.type === 'text'"
            :value="entryData[mIdx]?.[fIdx] || ''"
            readonly
            type="text"
          />
          <textarea
            v-else-if="field.type === 'textarea'"
            :value="entryData[mIdx]?.[fIdx] || ''"
            readonly
            rows="4"
          ></textarea>
          <input
            v-else-if="field.type === 'number'"
            :value="entryData[mIdx]?.[fIdx] || ''"
            readonly
            type="number"
          />
          <input
            v-else-if="field.type === 'date'"
            :value="entryData[mIdx]?.[fIdx] || ''"
            readonly
            type="date"
          />
          <select
            v-else-if="field.type === 'select'"
            :value="entryData[mIdx]?.[fIdx] || ''"
            disabled
          >
            <option value="" disabled>Select…</option>
            <option
              v-for="opt in field.options"
              :key="opt"
              :value="opt"
            >{{ opt }}</option>
          </select>
          <p v-else>Unsupported field type: {{ field.type }}</p>
        </div>
      </div>
    </div>
    <div v-else>
      <p>No data available for this share link.</p>
    </div>
  </div>
  <div v-else class="error">
    <p>Invalid or missing study data. Please check the shared link.</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';

const route = useRoute();
const loading = ref(true);
const error = ref(null);
const info = ref(null);

const token = computed(() => route.params.token);

const models = computed(() => info.value?.study?.content?.study_data?.selectedModels || []);

const modelIndices = computed(() => {
  if (!info.value || info.value.visit_index === null || info.value.group_index === null) return [];
  const assignments = info.value?.study?.content?.study_data?.assignments;
  if (!Array.isArray(assignments)) {
    console.warn("[WARN] Assignments array is missing or invalid in study_data");
    return [];
  }
  return models.value
    .map((_, i) => i)
    .filter(i => {
      const visitArray = assignments[i];
      if (!Array.isArray(visitArray)) return false;
      const groupArray = visitArray[info.value.visit_index];
      if (!Array.isArray(groupArray)) return false;
      return groupArray[info.value.group_index] === true;
    });
});

const entryData = computed(() => {
  if (
    !info.value ||
    info.value.subject_index === null ||
    info.value.visit_index === null ||
    info.value.group_index === null ||
    !info.value.study?.content?.study_data?.entryData
  ) {
    console.warn("[WARN] entryData is missing or invalid in study_data");
    return [];
  }
  const entryData = info.value.study.content.study_data.entryData;
  if (
    !Array.isArray(entryData) ||
    !Array.isArray(entryData[info.value.subject_index]) ||
    !Array.isArray(entryData[info.value.subject_index][info.value.visit_index]) ||
    !Array.isArray(entryData[info.value.subject_index][info.value.visit_index][info.value.group_index])
  ) {
    console.warn("[WARN] entryData structure is invalid for indices", {
      subjectIndex: info.value.subject_index,
      visitIndex: info.value.visit_index,
      groupIndex: info.value.group_index
    });
    return [];
  }
  return entryData[info.value.subject_index][info.value.visit_index][info.value.group_index] || [];
});

onMounted(async () => {
  console.log("[DEBUG] DataEntryComponent mounted with token:", token.value);
  try {
    const resp = await axios.get(
      `http://localhost:8000/forms/shared/${token.value}/`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
    );
    info.value = resp.data;
    console.log("[DEBUG] Shared data loaded:", {
      study: info.value.study,
      indices: {
        subjectIndex: info.value.subject_index,
        visitIndex: info.value.visit_index,
        groupIndex: info.value.group_index
      },
    });
    if (!info.value.study || !info.value.study.metadata) {
      throw new Error("Study metadata is missing in the response.");
    }
    if (!info.value.study.content?.study_data?.assignments) {
      console.warn("[WARN] No assignments array in study_data");
    }
    if (!info.value.study.content?.study_data?.entryData) {
      console.warn("[WARN] No entryData array in study_data");
    }
  } catch (err) {
    console.error("[ERROR] loading shared data", {
      message: err.message,
      response: err.response?.data,
      status: err.response?.status
    });
    error.value = err.response?.data?.detail || "Failed to load shared data. Please check the link or contact the administrator.";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.share-link-viewer {
  max-width: 960px;
  margin: 24px auto;
  padding: 24px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.bread-crumb {
  background: #f9fafb;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 24px;
  font-size: 14px;
  color: #374151;
}
.section-block {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}
.form-field {
  margin-bottom: 12px;
}
.form-field label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
}
input[readonly], textarea[readonly], select[disabled] {
  background: #f9fafb;
  border: 1px solid #d1d5db;
  padding: 8px;
  border-radius: 6px;
  width: 100%;
  box-sizing: border-box;
}
.loading, .error {
  text-align: center;
  padding: 50px;
  color: #6b7280;
}
</style>