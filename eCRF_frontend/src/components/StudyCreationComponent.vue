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
        <button
          type="button"
          @click="validateStudy"
          class="btn-option"
        >
          Next →
        </button>
      </div>
    </div>

    <!-- STEP 2: Groups/Cohorts -->
    <div v-if="step === 2" class="new-study-form">
      <GroupForm
        :schema="groupSchema"
        v-model="groupData"
        @validate="checkGroups"
      />
      <div class="form-actions">
        <button
          type="button"
          @click="step = 1"
          class="btn-option"
        >
          ← Back
        </button>
        <button
          type="button"
          @click="checkGroups"
          class="btn-option"
        >
          Next →
        </button>
      </div>
    </div>

    <!-- STEP 3: Visits -->
    <div v-if="step === 3" class="new-study-form">
      <VisitForm
        :schema="visitSchema"
        v-model="visitData"
        @validate="checkVisits"
      />
      <div class="form-actions">
        <button
          type="button"
          @click="step = 2"
          class="btn-option"
        >
          ← Back
        </button>
        <button
          type="button"
          @click="checkVisits"
          class="btn-option"
        >
          Finish
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, inject } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import yaml from "js-yaml";

import BaseTextField   from "@/components/forms/BaseTextField.vue";
import BaseTextarea    from "@/components/forms/BaseTextarea.vue";
import BaseNumberField from "@/components/forms/BaseNumberField.vue";
import BaseDateField   from "@/components/forms/BaseDateField.vue";
import BaseSelectField from "@/components/forms/BaseSelectField.vue";

import GroupForm from "./GroupForm.vue";
import VisitForm from "./VisitForm.vue";

export default {
  name: "StudyCreationComponent",
  components: {
    BaseTextField,
    BaseTextarea,
    BaseNumberField,
    BaseDateField,
    BaseSelectField,
    GroupForm,
    VisitForm,
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
    const visitData     = ref([]);
    const groupData     = ref([]);

    const showStudyErrors = ref(false);

    function fieldError(f, value) {
      return f.required && showStudyErrors.value && !value
        ? `${f.label} is required.`
        : "";
    }

    async function loadYaml(path, schemaRef) {
      const res = await fetch(path);
      const doc = yaml.load(await res.text());
      const cls = Object.keys(doc.classes)[0];
      const attrs = doc.classes[cls].attributes;
      schemaRef.value = Object.entries(attrs).map(([n, d]) => {
        let type = d.widget === 'textarea' ? 'textarea' : 'text';
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
          options:     d.enum || [],
          skip:        d.skip || {}
        };
      });
    }

    function validateStudy() {
      showStudyErrors.value = true;
      const hasMissing = studySchema.value.some(f =>
        f.required && !studyData.value[f.field]
      );

      if (!hasMissing) {
        showStudyErrors.value = false;
        const typeField  = studySchema.value.find(f => f.field === 'type');
        const skipConfig = typeField?.skip || {};
        const selected   = studyData.value.type;
        const skips      = skipConfig[selected] || [];
        const payload = {
          study: studyData.value,
          groups: [],
          visits: []
        };

        if (skips.includes('groups') && skips.includes('visits')) {
          store.commit('setStudyDetails', payload);
          router.push({ name: 'CreateFormScratch' });
        } else {
          store.commit('setStudyDetails', payload);
          step.value = 2;
        }
      }
    }

    function checkGroups() {
      const hasErrors = groupData.value.some(g =>
        groupSchema.value.some(f => f.required && !g[f.field])
      );
      if (hasErrors) return;
      store.commit("setStudyDetails", {
        study: studyData.value,
        groups: groupData.value,
        visits: []
      });
      step.value = 3;
    }

    function checkVisits() {
      const hasErrors = visitData.value.some(v =>
        visitSchema.value.some(f => f.required && !v[f.field])
      );
      if (hasErrors) return;
      store.commit("setStudyDetails", {
        study: studyData.value,
        groups: groupData.value,
        visits: visitData.value
      });
      router.push({ name: "CreateFormScratch" });
    }

    onMounted(async () => {
      await loadYaml("/study_schema.yaml", studySchema);
      await loadYaml("/group_schema.yaml", groupSchema);
      await loadYaml("/visit_schema.yaml", visitSchema);

      studySchema.value.forEach(f => studyData.value[f.field] = "");
      groupData.value = [];
      visitData.value = [];
    });

    return {
      step,
      studySchema, studyData, showStudyErrors, validateStudy, fieldError,
      groupSchema, groupData, checkGroups,
      visitSchema, visitData, checkVisits,
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
