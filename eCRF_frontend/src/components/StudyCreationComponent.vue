<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>

    <!-- STEP 1: STUDY -->
    <div v-if="step === 1" class="new-study-form">
      <h2>Step 1: Create a New Study</h2>
      <div
        v-for="(field, idx) in studySchema"
        :key="idx"
        class="schema-field-row"
      >
        <label :for="field.field">
          {{ field.label }}
          <span v-if="field.required" class="required">*</span>
        </label>

        <!-- textarea -->
        <template v-if="field.type === 'textarea'">
          <textarea
            :id="field.field"
            v-model="studyData[field.field]"
            :placeholder="field.placeholder"
          ></textarea>
        </template>

        <!-- select -->
        <template v-else-if="field.type === 'select'">
          <select
            :id="field.field"
            v-model="studyData[field.field]"
          >
            <option value="">{{ field.placeholder }}</option>
            <option
              v-for="opt in field.options"
              :key="opt"
              :value="opt"
            >{{ opt }}</option>
          </select>
        </template>

        <!-- date or number or text -->
        <template v-else>
          <input
            :type="field.type"
            :id="field.field"
            v-model="studyData[field.field]"
            :placeholder="field.placeholder"
          />
        </template>

        <small
          v-if="showStudyErrors && field.required && !studyData[field.field]"
          class="error-text"
        >
          {{ field.placeholder }} is required.
        </small>
      </div>

      <div class="form-actions">
        <button @click="validateStudy" class="btn-option">
          Next → Visits
        </button>
      </div>
    </div>

    <!-- STEP 2: VISITS -->
    <div v-if="step === 2" class="new-study-form">
      <h2>Step 2: Define Visits</h2>

      <div class="schema-field-row">
        <label for="numVisits">
          Number of Visits
          <span class="required">*</span>
        </label>
        <input
          id="numVisits"
          type="number"
          min="1"
          v-model.number="numberOfVisits"
        />
      </div>

      <div
        v-for="(visit, vi) in visitData"
        :key="vi"
        class="visit-block"
      >
        <h3>Visit {{ vi + 1 }}</h3>
        <div
          v-for="(field, fi) in visitSchema"
          :key="fi"
          class="schema-field-row"
        >
          <label :for="`visit-${vi}-${field.field}`">
            {{ field.label }}
            <span v-if="field.required" class="required">*</span>
          </label>

          <template v-if="field.type === 'textarea'">
            <textarea
              :id="`visit-${vi}-${field.field}`"
              v-model="visit[field.field]"
              :placeholder="field.placeholder"
            ></textarea>
          </template>

          <template v-else-if="field.type === 'select'">
            <select
              :id="`visit-${vi}-${field.field}`"
              v-model="visit[field.field]"
            >
              <option value="">{{ field.placeholder }}</option>
              <option
                v-for="opt in field.options"
                :key="opt"
                :value="opt"
              >{{ opt }}</option>
            </select>
          </template>

          <template v-else>
            <input
              :type="field.type"
              :id="`visit-${vi}-${field.field}`"
              v-model="visit[field.field]"
              :placeholder="field.placeholder"
            />
          </template>

          <small
            v-if="showVisitErrors && field.required && !visit[field.field]"
            class="error-text"
          >
            {{ field.placeholder }} is required.
          </small>
        </div>
      </div>

      <div class="form-actions">
        <button @click="step = 1" class="btn-option">← Back</button>
        <button @click="validateVisits" class="btn-option">
          Next → Groups
        </button>
      </div>
    </div>

    <!-- STEP 3: GROUPS -->
    <div v-if="step === 3" class="new-study-form">
      <h2>Step 3: Define Groups/Cohorts</h2>

      <div class="schema-field-row">
        <label for="numGroups">
          Number of Groups
          <span class="required">*</span>
        </label>
        <input
          id="numGroups"
          type="number"
          min="1"
          v-model.number="numberOfGroups"
        />
      </div>

      <div
        v-for="(group, gi) in groupData"
        :key="gi"
        class="visit-block"
      >
        <h3>Group {{ gi + 1 }}</h3>
        <div
          v-for="(field, fi) in groupSchema"
          :key="fi"
          class="schema-field-row"
        >
          <label :for="`group-${gi}-${field.field}`">
            {{ field.label }}
            <span v-if="field.required" class="required">*</span>
          </label>

          <template v-if="field.type === 'textarea'">
            <textarea
              :id="`group-${gi}-${field.field}`"
              v-model="group[field.field]"
              :placeholder="field.placeholder"
            ></textarea>
          </template>

          <template v-else-if="field.type === 'select'">
            <select
              :id="`group-${gi}-${field.field}`"
              v-model="group[field.field]"
            >
              <option value="">{{ field.placeholder }}</option>
              <option
                v-for="opt in field.options"
                :key="opt"
                :value="opt"
              >{{ opt }}</option>
            </select>
          </template>

          <template v-else>
            <input
              :type="field.type"
              :id="`group-${gi}-${field.field}`"
              v-model="group[field.field]"
              :placeholder="field.placeholder"
            />
          </template>

          <small
            v-if="showGroupErrors && field.required && !group[field.field]"
            class="error-text"
          >
            {{ field.placeholder }} is required.
          </small>
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

    // schema definitions
    const studySchema = ref([]);
    const visitSchema = ref([]);
    const groupSchema = ref([]);

    // form data
    const studyData = ref({});
    const numberOfVisits = ref(1);
    const visitData = ref([]);
    const numberOfGroups = ref(1);
    const groupData = ref([]);

    // error flags
    const showStudyErrors = ref(false);
    const showVisitErrors = ref(false);
    const showGroupErrors = ref(false);

    // load a single-class YAML into schemaRef
    async function loadYaml(path, schemaRef) {
      const res = await fetch(path);
      const doc = yaml.load(await res.text());
      const cls = Object.keys(doc.classes)[0];
      const attrs = doc.classes[cls].attributes;
      schemaRef.value = Object.entries(attrs).map(([name, def]) => {
        let type = "text";
        const r = (def.range || "").toLowerCase();
        if (r === "date" || r === "datetime") type = "date";
        if (r === "integer" || r === "decimal") type = "number";
        if (def.enum) type = "select";
        return {
          field: name,
          label: name,
          placeholder: def.description || name,
          type,
          required: !!def.required,
          options: def.enum || [],
        };
      });
    }

    // whenever numberOfVisits changes, reinitialize visitData
    watch(
      numberOfVisits,
      (n) => {
        visitData.value = Array.from({ length: n }, () => {
          const obj = {};
          visitSchema.value.forEach((f) => (obj[f.field] = ""));
          return obj;
        });
      },
      { immediate: true }
    );

    // whenever numberOfGroups changes, reinitialize groupData
    watch(
      numberOfGroups,
      (n) => {
        groupData.value = Array.from({ length: n }, () => {
          const obj = {};
          groupSchema.value.forEach((f) => (obj[f.field] = ""));
          return obj;
        });
      },
      { immediate: true }
    );

    function validateStudy() {
      showStudyErrors.value = true;
      const missing = studySchema.value.some(
        (f) => f.required && !studyData.value[f.field]
      );
      if (!missing) {
        showStudyErrors.value = false;
        step.value = 2;
      }
    }

    function validateVisits() {
      showVisitErrors.value = true;
      const missing = visitData.value.some((visit) =>
        visitSchema.value.some((f) => f.required && !visit[f.field])
      );
      if (!missing) {
        showVisitErrors.value = false;
        step.value = 3;
      }
    }

    function validateGroups() {
      showGroupErrors.value = true;
      const missing = groupData.value.some((grp) =>
        groupSchema.value.some((f) => f.required && !grp[f.field])
      );
      if (!missing) {
        showGroupErrors.value = false;
        // here you can assemble your payload:
        // { study: studyData.value, visits: visitData.value, groups: groupData.value }
        router.push({ name: "CreateFormScratch" });
      }
    }

    onMounted(async () => {
      await loadYaml("/study_schema.yaml", studySchema);
      await loadYaml("/visit_schema.yaml", visitSchema);
      await loadYaml("/group_schema.yaml", groupSchema);

      // init studyData keys
      studySchema.value.forEach((f) => {
        studyData.value[f.field] = "";
      });
    });

    return {
      step,
      studySchema,
      studyData,
      visitSchema,
      numberOfVisits,
      visitData,
      groupSchema,
      numberOfGroups,
      groupData,
      showStudyErrors,
      showVisitErrors,
      showGroupErrors,
      validateStudy,
      validateVisits,
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
}
.btn-option {
  flex: 1;
  padding: 10px;
  background: #eee;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  text-align: center;
}
</style>
