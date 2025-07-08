<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>

    <!-- STEP 1 -->
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

    <!-- STEP 2 -->
    <div v-if="step === 2" class="new-study-form">
      <GroupForm :schema="groupSchema" v-model="groupData" />
      <div class="form-actions">
        <button @click="step = 1" class="btn-option">← Back</button>
        <button @click="checkGroups" class="btn-option">Next →</button>
      </div>
    </div>

    <!-- STEP 3 -->
    <div v-if="step === 3" class="new-study-form">
      <SubjectForm
        v-model:subjectCount="subjectCount"
        v-model:assignmentMethod="assignmentMethod"
      />
      <div class="form-actions">
        <button @click="step = 2" class="btn-option">← Back</button>
        <button @click="checkSubjectsSetup" class="btn-option">Next →</button>
      </div>
    </div>

    <!-- STEP 4 -->
    <div v-if="step === 4 && assignmentMethod !== 'Skip'" class="new-study-form">
      <SubjectAssignmentForm
        :subjects="subjectData"
        :groupData="groupData"
        v-model:subjects="subjectData"
      />
      <div class="form-actions">
        <button @click="step = 3" class="btn-option">← Back</button>
        <button @click="checkSubjectsAssigned" class="btn-option">Next →</button>
      </div>
    </div>

    <!-- STEP 5 -->
    <div v-if="step === 5" class="new-study-form">
      <VisitForm :schema="visitSchema" v-model="visitData" />
      <div class="form-actions">
        <button
          @click="step = (assignmentMethod === 'Skip' ? 3 : 4)"
          class="btn-option"
        >
          ← Back
        </button>
        <button @click="checkVisits" class="btn-option">Finish</button>
      </div>
    </div>
  </div>

  <div v-if="showDialog" class="dialog-backdrop">
    <div class="dialog-box">
      <p>{{ dialogMessage }}</p>
      <button @click="showDialog = false" class="btn-option">OK</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, inject } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import yaml from "js-yaml";

import BaseTextField from "@/components/forms/BaseTextField.vue";
import BaseTextarea from "@/components/forms/BaseTextarea.vue";
import BaseNumberField from "@/components/forms/BaseNumberField.vue";
import BaseDateField from "@/components/forms/BaseDateField.vue";
import BaseSelectField from "@/components/forms/BaseSelectField.vue";

import GroupForm from "./GroupForm.vue";
import VisitForm from "./VisitForm.vue";
import SubjectForm from "./SubjectForm.vue";
import SubjectAssignmentForm from "./SubjectAssignmentForm.vue";

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
    SubjectForm,
    SubjectAssignmentForm,
  },
  setup() {
    const router = useRouter();
    const store = useStore();
    const formatLabel = inject("formatLabel");

    const step = ref(1);
    const studyData = ref({});
    const groupData = ref([]);
    const subjectData = ref([]);
    const visitData = ref([]);
    const subjectCount = ref(1);
    const assignmentMethod = ref("Random");

    const studySchema = ref([]);
    const groupSchema = ref([]);
    const visitSchema = ref([]);

    const showStudyErrors = ref(false);
    const showDialog = ref(false);
    const dialogMessage = ref("");

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
        let type = d.widget === "textarea" ? "textarea" : "text";
        const r = (d.range || "").toLowerCase();
        if (r === "date" || r === "datetime") type = "date";
        if (r === "integer" || r === "decimal") type = "number";
        if (d.enum) type = "select";
        return {
          field: n,
          label: formatLabel(n),
          placeholder: d.description || formatLabel(n),
          type,
          required: !!d.required,
          disabled: !!d.disabled,
          display: d.display !== false,
          options: d.enum || [],
          skip: d.skip || {}
        };
      });
    }

    function validateStudy() {
      showStudyErrors.value = true;
      const hasMissing = studySchema.value.some(f =>
        f.required && !studyData.value[f.field]
      );
      if (hasMissing) return;

      showStudyErrors.value = false;
      const typeField = studySchema.value.find(f => f.field === "type");
      const skipConfig = typeField?.skip || {};
      const selected = studyData.value.type;
      const skips = skipConfig[selected] || [];

      const payload = {
        study: studyData.value,
        groups: [],
        visits: []
      };

      if (skips.includes("groups") && skips.includes("visits")) {
        store.commit("setStudyDetails", payload);
        router.push({ name: "CreateFormScratch" });
      } else {
        store.commit("setStudyDetails", payload);
        step.value = 2;
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

    function checkSubjectsSetup() {
      if (!subjectCount.value || !assignmentMethod.value) {
        console.warn("Provide subject count and assignment method.");
        return;
      }

      const N = subjectCount.value;
      const prefix = (studyData.value.title || "ST")
        .replace(/[^A-Za-z\s]/g, "")
        .trim()
        .split(/\s+/)
        .map(w => w[0]?.toUpperCase() || "")
        .join("") || "ST";
      const groupNames = groupData.value.map(g => g.name || g.label || "Unnamed");

      let assignments = [];
      if (assignmentMethod.value === "Random" && groupNames.length > 0) {
        const G = groupNames.length;
        const base = Math.floor(N / G), rem = N % G;
        const idx = Array.from({ length: G }, (_, i) => i);
        for (let i = G - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [idx[i], idx[j]] = [idx[j], idx[i]];
        }
        const extra = new Set(idx.slice(0, rem));
        for (let gi = 0; gi < G; gi++) {
          const cnt = base + (extra.has(gi) ? 1 : 0);
          for (let k = 0; k < cnt; k++) {
            assignments.push(groupNames[gi]);
          }
        }
        for (let i = assignments.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [assignments[i], assignments[j]] = [assignments[j], assignments[i]];
        }
      } else {
        assignments = Array(N).fill("");
      }

      subjectData.value = assignments.map((grp, idx) => ({
        id: `SUBJ-${prefix}-${String(idx + 1).padStart(3, "0")}`,
        group: grp
      }));

      console.log("subjects", subjectData.value);
      step.value = assignmentMethod.value === "Skip" ? 5 : 4;
    }

    function checkSubjectsAssigned() {
      if (subjectData.value.some(s => !s.group)) {
        dialogMessage.value = "All subjects must have a group.";
        showDialog.value = true;
        return;
      }
      step.value = 5;
    }

    function checkVisits() {
      const hasErrors = visitData.value.some(v =>
        visitSchema.value.some(f => f.required && !v[f.field])
      );
      if (hasErrors) return;

      // *** commit everything to Vuex instead of saving to DB ***
      store.commit("setStudyDetails", {
        study: studyData.value,
        groups: groupData.value,
        subjectCount: subjectCount.value,
        assignmentMethod: assignmentMethod.value,
        subjects: subjectData.value,
        visits: visitData.value
      });

      // navigate to your scratch‐form editor
      router.push({ name: "CreateFormScratch" });
    }

    onMounted(async () => {
      await loadYaml("/study_schema.yaml", studySchema);
      await loadYaml("/group_schema.yaml", groupSchema);
      await loadYaml("/visit_schema.yaml", visitSchema);

      studySchema.value.forEach(f => (studyData.value[f.field] = ""));
      groupData.value = [];
      visitData.value = [];
    });

    return {
      step,
      studyData,
      groupData,
      subjectData,
      visitData,
      subjectCount,
      assignmentMethod,
      studySchema,
      groupSchema,
      visitSchema,
      showDialog,
      dialogMessage,
      fieldError,
      validateStudy,
      checkGroups,
      checkSubjectsSetup,
      checkSubjectsAssigned,
      checkVisits
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
.dialog-backdrop {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.dialog-box {
  background: white;
  padding: 20px 30px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.25);
  text-align: center;
}
</style>
