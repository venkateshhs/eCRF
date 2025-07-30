<template>
  <div v-if="loading" class="loading">
    <p>Loading shared data…</p>
  </div>
  <div v-else-if="error" class="error">
    <p>{{ error }}</p>
  </div>

  <div v-else class="share-link-viewer">
    <h2>Shared Data Entry</h2>
    <div class="bread-crumb">
      <strong>Study:</strong> {{ info.study.metadata.study_name }} |
      <strong>Subject:</strong> {{ info.subject_index + 1 }} |
      <strong>Visit:</strong>
        {{ visits[info.visit_index]?.name || '–' }} |
      <strong>Group:</strong>
        {{ groups[info.group_index]?.name || '–' }}
    </div>

    <div v-if="modelIndices.length">
      <div
        v-for="mIdx in modelIndices"
        :key="mIdx"
        class="section-block"
      >
        <h3>{{ models[mIdx].title }}</h3>

        <div
          v-for="(field, fIdx) in models[mIdx].fields"
          :key="fIdx"
          class="form-field"
        >
          <label :for="fieldId(mIdx,fIdx)">
            {{ field.label }}
            <span v-if="field.constraints?.required" class="required">*</span>
          </label>

          <!-- TEXT -->
          <input
            v-if="field.type==='text'"
            :id="fieldId(mIdx,fIdx)"
            type="text"
            v-model="entryData[mIdx][fIdx]"
            :readonly="isViewOnly"
            :placeholder="field.placeholder"
          />

          <!-- TEXTAREA -->
          <textarea
            v-else-if="field.type==='textarea'"
            :id="fieldId(mIdx,fIdx)"
            v-model="entryData[mIdx][fIdx]"
            :readonly="isViewOnly"
            :rows="4"
            :placeholder="field.placeholder"
          ></textarea>

          <!-- NUMBER -->
          <input
            v-else-if="field.type==='number'"
            :id="fieldId(mIdx,fIdx)"
            type="number"
            v-model.number="entryData[mIdx][fIdx]"
            :readonly="isViewOnly"
            :min="field.constraints?.min"
            :max="field.constraints?.max"
            :step="field.constraints?.step||'any'"
          />

          <!-- DATE -->
          <input
            v-else-if="field.type==='date'"
            :id="fieldId(mIdx,fIdx)"
            type="date"
            v-model="entryData[mIdx][fIdx]"
            :readonly="isViewOnly"
            :min="field.constraints?.minDate"
            :max="field.constraints?.maxDate"
          />

          <!-- SELECT -->
          <select
            v-else-if="field.type==='select'"
            :id="fieldId(mIdx,fIdx)"
            v-model="entryData[mIdx][fIdx]"
            :disabled="isViewOnly"
          >
            <option value="" disabled>Select…</option>
            <option
              v-for="opt in field.options"
              :key="opt"
              :value="opt"
            >{{ opt }}</option>
          </select>

          <!-- FALLBACK -->
          <div v-else>Unsupported field type: {{ field.type }}</div>
        </div>
      </div>

      <div class="form-actions" v-if="!isViewOnly">
        <button @click="submitData" class="btn-primary">
          Save
        </button>
      </div>
    </div>

    <div v-else class="no-assigned">
      <p>No sections assigned for this visit & group.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

// ----- state -----
const route   = useRoute()
const loading = ref(true)
const error   = ref(null)
const info    = ref(null)

// extract token & permission
const token      = computed(() => route.params.token)
const permission = computed(() => info.value?.permission || 'view')
const isViewOnly = computed(() => permission.value === 'view')

// models, visits, groups
const models = computed(() =>
  info.value?.study?.content?.study_data?.selectedModels || []
)
const visits = computed(() =>
  info.value?.study?.content?.study_data?.visits || []
)
const groups = computed(() =>
  info.value?.study?.content?.study_data?.groups || []
)

// which models apply to this visit&group?
const modelIndices = computed(() => {
  if (!info.value) return []
  const a = info.value.study.content.study_data.assignments
  const v = info.value.visit_index
  const g = info.value.group_index
  if (!Array.isArray(a)) return []
  return models.value
    .map((_, i) => i)
    .filter(i => !!a[i]?.[v]?.[g])
})

// entryData: editable copy of the shared entryData slice
const entryData = ref([])

function initEntryData() {
  const subj = info.value.subject_index
  const v    = info.value.visit_index
  const g    = info.value.group_index
  const raw  = info.value.study.content.study_data.entryData

  if (
    raw?.[subj]?.[v]?.[g] &&
    Array.isArray(raw[subj][v][g])
  ) {
    // deep‑clone so we can v-model
    entryData.value = JSON.parse(
      JSON.stringify(raw[subj][v][g])
    )
  } else {
    // fallback: one empty row per section
    entryData.value = models.value.map(()=>[])
  }
}

// update whenever we load or permission changes
watch(info, val => {
  if (val) initEntryData()
})

// fetch on mount
onMounted(async () => {
  try {
    const resp = await axios.get(
      `http://localhost:8000/forms/shared/${token.value}/`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
    )
    info.value = resp.data
  } catch (e) {
    console.error(e)
    error.value = e.response?.data?.detail
      || 'Failed to load shared data.'
  } finally {
    loading.value = false
  }
})

// generate unique IDs for labels
function fieldId(mIdx,fIdx){
  return `s${info.value.subject_index}` +
         `v${info.value.visit_index}` +
         `g${info.value.group_index}` +
         `m${mIdx}` +
         `f${fIdx}`
}

// save back to server
async function submitData() {
  try {
    await axios.post(
      `http://localhost:8000/forms/studies/` +
        `${info.value.study.metadata.id}/data`,
      {
        study_id:      info.value.study.metadata.id,
        subject_index: info.value.subject_index,
        visit_index:   info.value.visit_index,
        group_index:   info.value.group_index,
        data:          entryData.value
      },
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
    )
    alert('Data saved successfully.')
  } catch (e) {
    console.error(e)
    alert('Failed to save data.')
  }
}
</script>

<style scoped>
.loading, .error {
  text-align: center;
  padding: 2rem;
  color: #666;
}
.share-link-viewer {
  max-width: 900px;
  margin: 2rem auto;
  padding: 1rem;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.bread-crumb {
  font-size: 0.9rem;
  margin-bottom: 1rem;
  color: #333;
}
.section-block {
  margin-bottom: 1.5rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.form-field {
  margin-bottom: 0.75rem;
}
.form-field label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
}
input, textarea, select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}
input[readonly], textarea[readonly], select[disabled] {
  background: #f9f9f9;
  color: #555;
}
.required {
  color: #c00;
  margin-left: 4px;
}
.form-actions {
  text-align: right;
}
.btn-primary {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary:hover {
  background: #0069d9;
}
.no-assigned {
  font-style: italic;
  color: #666;
  text-align: center;
  padding: 1rem;
}
</style>
