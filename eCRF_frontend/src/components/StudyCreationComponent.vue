<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>

    <!-- STEP 1: Study -->
    <div v-if="step === 1" class="new-study-form">
      <h2>Step 1: Create a New Study</h2>

      <div
        v-for="(f, i) in studySchema.filter(f => f.display)"
        :key="i"
        class="schema-field-row"
      >
        <!-- textarea -->
        <BaseTextarea
          v-if="f.type === 'textarea'"
          v-model="studyData[f.field]"
          :id="f.field"
          :label="f.label"
          :placeholder="f.placeholder"
          :required="f.required"
          :disabled="f.disabled"
          :error="fieldError(f, studyData[f.field])"
        />

        <!-- select / dropdown -->
        <BaseSelectField
          v-else-if="f.type === 'select'"
          v-model="studyData[f.field]"
          :id="f.field"
          :label="f.label"
          :options="f.options"
          :placeholder="f.placeholder"
          :required="f.required"
          :disabled="f.disabled"
          :error="fieldError(f, studyData[f.field])"
        />

        <!-- number -->
        <BaseNumberField
          v-else-if="f.type === 'number'"
          v-model="studyData[f.field]"
          :id="f.field"
          :label="f.label"
          :placeholder="f.placeholder"
          :required="f.required"
          :disabled="f.disabled"
          :error="fieldError(f, studyData[f.field])"
        />

        <!-- date -->
        <BaseDateField
          v-else-if="f.type === 'date'"
          v-model="studyData[f.field]"
          :id="f.field"
          :label="f.label"
          :required="f.required"
          :disabled="f.disabled"
          :error="fieldError(f, studyData[f.field])"
          :min="f.min"
          :max="f.max"
        />

        <!-- fallback to text -->
        <BaseTextField
          v-else
          v-model="studyData[f.field]"
          :id="f.field"
          :label="f.label"
          :placeholder="f.placeholder"
          :required="f.required"
          :disabled="f.disabled"
          :error="fieldError(f, studyData[f.field])"
        />
      </div>

      <div class="form-actions">
        <button @click="validateStudy" class="btn-option">
          Next →
        </button>
      </div>
    </div>

    <!-- STEP 2: Groups/Cohorts -->
    <div v-if="step === 2" class="new-study-form">
      <h2>Step 2: Define Groups/Cohorts</h2>

      <!-- number of groups -->
      <BaseNumberField
        v-model="numberOfGroups"
        id="numGroups"
        label="Number of Groups"
        placeholder="Enter number of groups"
        :required="true"
        :error="showGroupErrors && !numberOfGroups ? 'Number of Groups is required.' : ''"
        :min="1"
      />

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
            v-for="(f, k) in groupSchema.filter(f => f.display)"
            :key="k"
            class="schema-field-row"
          >
            <BaseTextarea
              v-if="f.type === 'textarea'"
              v-model="groupData[groupIndex][f.field]"
              :id="`group-${groupIndex}-${f.field}`"
              :label="f.label"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, groupData[groupIndex][f.field])"
            />

            <BaseSelectField
              v-else-if="f.type === 'select'"
              v-model="groupData[groupIndex][f.field]"
              :id="`group-${groupIndex}-${f.field}`"
              :label="f.label"
              :options="f.options"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, groupData[groupIndex][f.field])"
            />

            <BaseNumberField
              v-else-if="f.type === 'number'"
              v-model="groupData[groupIndex][f.field]"
              :id="`group-${groupIndex}-${f.field}`"
              :label="f.label"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, groupData[groupIndex][f.field])"
            />

            <BaseDateField
              v-else-if="f.type === 'date'"
              v-model="groupData[groupIndex][f.field]"
              :id="`group-${groupIndex}-${f.field}`"
              :label="f.label"
              :required="f.required"
              :error="fieldError(f, groupData[groupIndex][f.field])"
            />

            <BaseTextField
              v-else
              v-model="groupData[groupIndex][f.field]"
              :id="`group-${groupIndex}-${f.field}`"
              :label="f.label"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, groupData[groupIndex][f.field])"
            />
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button @click="step = 1" class="btn-option">← Back</button>
        <button @click="validateGroups" class="btn-option">
          Next →
        </button>
      </div>
    </div>

    <!-- STEP 3: Visits -->
    <div v-if="step === 3" class="new-study-form">
      <h2>Step 3: Define Visits</h2>

      <!-- number of visits -->
      <BaseNumberField
        v-model="numberOfVisits"
        id="numVisits"
        label="Number of Visits"
        placeholder="Enter number of visits"
        :required="true"
        :error="showVisitErrors && !numberOfVisits ? 'Number of Visits is required.' : ''"
        :min="1"
      />

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
            v-for="(f, j) in visitSchema.filter(f => f.display)"
            :key="j"
            class="schema-field-row"
          >
            <BaseTextarea
              v-if="f.type === 'textarea'"
              v-model="visitData[visitIndex][f.field]"
              :id="`visit-${visitIndex}-${f.field}`"
              :label="f.label"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, visitData[visitIndex][f.field])"
            />

            <BaseSelectField
              v-else-if="f.type === 'select'"
              v-model="visitData[visitIndex][f.field]"
              :id="`visit-${visitIndex}-${f.field}`"
              :label="f.label"
              :options="f.options"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, visitData[visitIndex][f.field])"
            />

            <BaseNumberField
              v-else-if="f.type === 'number'"
              v-model="visitData[visitIndex][f.field]"
              :id="`visit-${visitIndex}-${f.field}`"
              :label="f.label"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, visitData[visitIndex][f.field])"
            />

            <BaseDateField
              v-else-if="f.type === 'date'"
              v-model="visitData[visitIndex][f.field]"
              :id="`visit-${visitIndex}-${f.field}`"
              :label="f.label"
              :required="f.required"
              :error="fieldError(f, visitData[visitIndex][f.field])"
            />

            <BaseTextField
              v-else
              v-model="visitData[visitIndex][f.field]"
              :id="`visit-${visitIndex}-${f.field}`"
              :label="f.label"
              :placeholder="f.placeholder"
              :required="f.required"
              :error="fieldError(f, visitData[visitIndex][f.field])"
            />
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button @click="step = 2" class="btn-option">← Back</button>
        <button @click="validateVisits" class="btn-option">
          Finish
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, inject } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import yaml from "js-yaml";

import BaseTextField   from "@/components/forms/BaseTextField.vue";
import BaseTextarea    from "@/components/forms/BaseTextarea.vue";
import BaseNumberField from "@/components/forms/BaseNumberField.vue";
import BaseDateField   from "@/components/forms/BaseDateField.vue";
import BaseSelectField from "@/components/forms/BaseSelectField.vue";

export default {
  name: "StudyCreationComponent",
  components: {
    BaseTextField,
    BaseTextarea,
    BaseNumberField,
    BaseDateField,
    BaseSelectField
  },
  setup() {
    const router = useRouter();
    const store = useStore();
    const formatLabel = inject("formatLabel");
    const step = ref(1);

    const studySchema   = ref([]);
    const visitSchema   = ref([]);
    const groupSchema   = ref([]);

    const studyData     = ref({});
    const numberOfVisits= ref(1);
    const visitData     = ref([]);
    const visitIndex    = ref(0);

    const numberOfGroups= ref(1);
    const groupData     = ref([]);
    const groupIndex    = ref(0);

    const showStudyErrors = ref(false);
    const showVisitErrors = ref(false);
    const showGroupErrors = ref(false);
    /* eslint-disable-next-line no-unused-vars */
    function fieldError(f, value) {
      return (f.required && (showStudyErrors.value || showVisitErrors.value || showGroupErrors.value) && !value)
        ? `${f.label} is required.`
        : "";
    }

    async function loadYaml(path, schemaRef) {
      const res = await fetch(path);
      const doc = yaml.load(await res.text());
      const cls = Object.keys(doc.classes)[0];
      const attrs = doc.classes[cls].attributes;
      schemaRef.value = Object.entries(attrs).map(([n, d]) => {
        let type = d.widget === 'textarea'
      ? 'textarea'
      : 'text';

        const r = (d.range || "").toLowerCase();
        if (r === "date" || r === "datetime") type = "date";
        if (r === "integer" || r === "decimal") type = "number";
        if (d.enum) type = "select";
        return {
          field:       n,
          label:       formatLabel(n),
          placeholder: d.description || formatLabel(n),
          type,
          required:    !!d.required,
          disabled:    !!d.disabled,
          display:     d.display !== false,
          options:     d.enum || []
        };
      });
    }

    watch(studySchema, s => s.forEach(f => studyData.value[f.field] = ""));
    watch([numberOfVisits, visitSchema], ([n]) => {
      visitIndex.value = 0;
      visitData.value = n >= 1 && visitSchema.value.length
        ? Array.from({ length: n }, () => Object.fromEntries(visitSchema.value.map(f => [f.field, ""])))
        : [];
    }, { immediate: true });
    watch([numberOfGroups, groupSchema], ([n]) => {
      groupIndex.value = 0;
      groupData.value = n >= 1 && groupSchema.value.length
        ? Array.from({ length: n }, () => Object.fromEntries(groupSchema.value.map(f => [f.field, ""])))
        : [];
    }, { immediate: true });

    function validateStudy() {
      showStudyErrors.value = true;
      if (!studySchema.value.some(f => f.required && !studyData.value[f.field])) {
        showStudyErrors.value = false;
        step.value = 2;
      }
    }

    function prevVisit()  { if (visitIndex.value > 0) visitIndex.value--; }
    function nextVisit()  { if (visitIndex.value < numberOfVisits.value - 1) visitIndex.value++; }

    function validateGroups() {
      showGroupErrors.value = true;
      if (!groupData.value.some(g =>
        groupSchema.value.some(f => f.required && !g[f.field])
      )) {
        showGroupErrors.value = false;
        // store study + groups, then advance to Visits
        const payload = { study: studyData.value, visits: [], groups: groupData.value };
        store.commit("setStudyDetails", payload);
        step.value = 3;
      }
    }

    function prevGroup()  { if (groupIndex.value > 0) groupIndex.value--; }
    function nextGroup()  { if (groupIndex.value < numberOfGroups.value - 1) groupIndex.value++; }

    function validateVisits() {
      showVisitErrors.value = true;
      if (!visitData.value.some(v =>
        visitSchema.value.some(f => f.required && !v[f.field])
      )) {
        showVisitErrors.value = false;
        // finally store visits and navigate on
        const payload = {
          study: studyData.value,
          visits: visitData.value,
          groups: groupData.value
        };
        store.commit("setStudyDetails", payload);
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
      studySchema, studyData, showStudyErrors, validateStudy,
      numberOfVisits, visitSchema, visitData, visitIndex, showVisitErrors,
      prevVisit, nextVisit, validateVisits,
      numberOfGroups, groupSchema, groupData, groupIndex, showGroupErrors,
      prevGroup, nextGroup, validateGroups, fieldError
    };
  }
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
.visit-block {
  padding: 10px 0;
  border-top: 1px solid #ddd;
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
