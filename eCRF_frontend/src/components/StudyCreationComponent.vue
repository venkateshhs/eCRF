<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>

    <!-- STEP 1: Study -->
    <div v-if="step === 1" class="new-study-form">
      <h2>Step 1: Create a New Study</h2>
      <div
        v-for="(f, i) in studySchema"
        :key="i"
        class="schema-field-row"
      >
        <label :for="f.field">
          {{ f.label }}<span v-if="f.required" class="required">*</span>
        </label>

        <!-- textarea -->
        <textarea
          v-if="f.type==='textarea'"
          :id="f.field"
          v-model="studyData[f.field]"
          :placeholder="f.placeholder"
        />

        <!-- select -->
        <select
          v-else-if="f.type==='select'"
          :id="f.field"
          v-model="studyData[f.field]"
        >
          <option value="">{{ f.placeholder }}</option>
          <option v-for="opt in f.options" :key="opt" :value="opt">
            {{ opt }}
          </option>
        </select>

        <!-- date/number/text -->
        <input
          v-else
          :type="f.type"
          :id="f.field"
          v-model="studyData[f.field]"
          :placeholder="f.placeholder"
        />

        <small
          v-if="showStudyErrors && f.required && !studyData[f.field]"
          class="error-text"
        >
          {{ f.placeholder }} is required.
        </small>
      </div>

      <div class="form-actions">
        <button @click="validateStudy" class="btn-option">
          Next → Visits
        </button>
      </div>
    </div>

    <!-- STEP 2: Visits -->
    <div v-if="step === 2" class="new-study-form">
      <h2>Step 2: Define Visits</h2>

      <div class="schema-field-row">
        <label for="numVisits">
          Number of Visits<span class="required">*</span>
        </label>
        <input
          id="numVisits"
          type="number"
          min="1"
          v-model.number="numberOfVisits"
        />
      </div>

      <!-- only show nav + form if we have a valid array entry -->
      <div v-if="visitData[visitIndex]">
        <div class="navigation">
          <button @click="prevVisit" :disabled="visitIndex === 0">←</button>
          <span>{{ visitIndex + 1 }} / {{ numberOfVisits }}</span>
          <button
            @click="nextVisit"
            :disabled="visitIndex === numberOfVisits - 1"
          >→</button>
        </div>

        <div class="visit-block">
          <h3>Visit {{ visitIndex + 1 }}</h3>
          <div
            v-for="(f, j) in visitSchema"
            :key="j"
            class="schema-field-row"
          >
            <label :for="`visit-${visitIndex}-${f.field}`">
              {{ f.label }}<span v-if="f.required" class="required">*</span>
            </label>

            <textarea
              v-if="f.type==='textarea'"
              :id="`visit-${visitIndex}-${f.field}`"
              v-model="visitData[visitIndex][f.field]"
              :placeholder="f.placeholder"
            />

            <select
              v-else-if="f.type==='select'"
              :id="`visit-${visitIndex}-${f.field}`"
              v-model="visitData[visitIndex][f.field]"
            >
              <option value="">{{ f.placeholder }}</option>
              <option v-for="opt in f.options" :key="opt" :value="opt">
                {{ opt }}
              </option>
            </select>

            <input
              v-else
              :type="f.type"
              :id="`visit-${visitIndex}-${f.field}`"
              v-model="visitData[visitIndex][f.field]"
              :placeholder="f.placeholder"
            />

            <small
              v-if="showVisitErrors
                && f.required
                && !visitData[visitIndex][f.field]"
              class="error-text"
            >
              {{ f.placeholder }} is required.
            </small>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button @click="step = 1" class="btn-option">← Back</button>
        <button @click="validateVisits" class="btn-option">
          Next → Groups
        </button>
      </div>
    </div>

    <!-- STEP 3: Groups -->
    <div v-if="step === 3" class="new-study-form">
      <h2>Step 3: Define Groups/Cohorts</h2>

      <div class="schema-field-row">
        <label for="numGroups">
          Number of Groups<span class="required">*</span>
        </label>
        <input
          id="numGroups"
          type="number"
          min="1"
          v-model.number="numberOfGroups"
        />
      </div>

      <div v-if="groupData[groupIndex]">
        <div class="navigation">
          <button @click="prevGroup" :disabled="groupIndex === 0">←</button>
          <span>{{ groupIndex + 1 }} / {{ numberOfGroups }}</span>
          <button
            @click="nextGroup"
            :disabled="groupIndex === numberOfGroups - 1"
          >→</button>
        </div>

        <div class="visit-block">
          <h3>Group {{ groupIndex + 1 }}</h3>
          <div
            v-for="(f, k) in groupSchema"
            :key="k"
            class="schema-field-row"
          >
            <label :for="`group-${groupIndex}-${f.field}`">
              {{ f.label }}<span v-if="f.required" class="required">*</span>
            </label>

            <textarea
              v-if="f.type==='textarea'"
              :id="`group-${groupIndex}-${f.field}`"
              v-model="groupData[groupIndex][f.field]"
              :placeholder="f.placeholder"
            />

            <select
              v-else-if="f.type==='select'"
              :id="`group-${groupIndex}-${f.field}`"
              v-model="groupData[groupIndex][f.field]"
            >
              <option value="">{{ f.placeholder }}</option>
              <option v-for="opt in f.options" :key="opt" :value="opt">
                {{ opt }}
              </option>
            </select>

            <input
              v-else
              :type="f.type"
              :id="`group-${groupIndex}-${f.field}`"
              v-model="groupData[groupIndex][f.field]"
              :placeholder="f.placeholder"
            />

            <small
              v-if="showGroupErrors
                && f.required
                && !groupData[groupIndex][f.field]"
              class="error-text"
            >
              {{ f.placeholder }} is required.
            </small>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button @click="step = 2" class="btn-option">← Back</button>
        <button @click="validateGroups" class="btn-option">Finish</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import yaml from "js-yaml";

export default {
  name: "StudyCreationComponent",
  setup() {
    const router = useRouter();
    const step = ref(1);

    // schemas
    const studySchema = ref([]);
    const visitSchema = ref([]);
    const groupSchema = ref([]);

    // data
    const studyData = ref({});
    const numberOfVisits = ref(1);
    const visitData = ref([]);
    const visitIndex = ref(0);

    const numberOfGroups = ref(1);
    const groupData = ref([]);
    const groupIndex = ref(0);

    // errors
    const showStudyErrors = ref(false);
    const showVisitErrors = ref(false);
    const showGroupErrors = ref(false);

    // load YAML into schemaRef
    async function loadYaml(path, schemaRef) {
      const res = await fetch(path);
      const doc = yaml.load(await res.text());
      const cls = Object.keys(doc.classes)[0];
      const attrs = doc.classes[cls].attributes;
      schemaRef.value = Object.entries(attrs).map(([n, d]) => {
        let type = "text";
        const r = (d.range || "").toLowerCase();
        if (r === "date" || r === "datetime") type = "date";
        if (r === "integer" || r === "decimal") type = "number";
        if (d.enum) type = "select";
        return {
          field: n,
          label: n,
          placeholder: d.description || n,
          type,
          required: !!d.required,
          options: d.enum || [],
        };
      });
    }

    // init studyData after schema loads
    watch(studySchema, (s) => {
      s.forEach((f) => (studyData.value[f.field] = ""));
    });

    // init visitData when count or schema changes—and only if count >= 1
    watch([numberOfVisits, visitSchema], ([n]) => {
      if (n >= 1 && visitSchema.value.length) {
        visitIndex.value = 0;
        visitData.value = Array.from({ length: n }, () => {
          const o = {};
          visitSchema.value.forEach((f) => (o[f.field] = ""));
          return o;
        });
      } else {
        visitData.value = [];
      }
    }, { immediate: true });

    // init groupData when count or schema changes—and only if count >= 1
    watch([numberOfGroups, groupSchema], ([n]) => {
      if (n >= 1 && groupSchema.value.length) {
        groupIndex.value = 0;
        groupData.value = Array.from({ length: n }, () => {
          const o = {};
          groupSchema.value.forEach((f) => (o[f.field] = ""));
          return o;
        });
      } else {
        groupData.value = [];
      }
    }, { immediate: true });

    // validation/navigation
    function validateStudy() {
      showStudyErrors.value = true;
      if (!studySchema.value.some(f => f.required && !studyData.value[f.field])) {
        showStudyErrors.value = false;
        step.value = 2;
      }
    }

    function prevVisit() {
      if (visitIndex.value > 0) visitIndex.value--;
    }
    function nextVisit() {
      if (visitIndex.value < numberOfVisits.value - 1) visitIndex.value++;
    }
    function validateVisits() {
      showVisitErrors.value = true;
      if (!visitData.value.some(v =>
        visitSchema.value.some(f => f.required && !v[f.field])
      )) {
        showVisitErrors.value = false;
        step.value = 3;
      }
    }

    function prevGroup() {
      if (groupIndex.value > 0) groupIndex.value--;
    }
    function nextGroup() {
      if (groupIndex.value < numberOfGroups.value - 1) groupIndex.value++;
    }
    function validateGroups() {
      showGroupErrors.value = true;
      if (!groupData.value.some(g =>
        groupSchema.value.some(f => f.required && !g[f.field])
      )) {
        showGroupErrors.value = false;
        // final payload:
        const payload = {
          study: studyData.value,
          visits: visitData.value,
          groups: groupData.value,
        };
        console.log("Final payload:", payload);
        router.push({ name: "CreateFormScratch" });
      }
    }

    onMounted(async () => {
      await loadYaml("/study_schema.yaml", studySchema);
      await loadYaml("/visit_schema.yaml", visitSchema);
      await loadYaml("/group_schema.yaml", groupSchema);
    });

    return {
      step,
      studySchema,
      studyData,
      showStudyErrors,
      validateStudy,

      numberOfVisits,
      visitSchema,
      visitData,
      visitIndex,
      showVisitErrors,
      prevVisit,
      nextVisit,
      validateVisits,

      numberOfGroups,
      groupSchema,
      groupData,
      groupIndex,
      showGroupErrors,
      prevGroup,
      nextGroup,
      validateGroups,
    };
  },
};
</script>

<style scoped>
.study-creation-container {
  max-width: 800px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
}
.new-study-form {
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
  margin-top: 20px;
}
.schema-field-row {
  margin-bottom: 1rem;
}
.navigation {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin: 1rem 0;
}
.navigation button {
  padding: 6px 12px;
}
.visit-block {
  padding: 10px 0;
  border-top: 1px solid #ddd;
}
label {
  display: block;
  font-weight: bold;
}
.required {
  color: red;
  margin-left: 4px;
}
input,
textarea,
select {
  width: 100%;
  padding: 8px;
  margin-top: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}
.error-text {
  color: red;
  font-size: 0.85rem;
  margin-top: 2px;
}
.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.btn-option {
  padding: 10px 20px;
  background: #eee;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}
</style>
