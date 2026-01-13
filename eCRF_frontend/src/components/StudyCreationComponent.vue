<template>
  <div class="study-creation-container">
    <!-- STEPPER HEADER -->
    <div class="stepper" v-if="steps && steps.length">
      <div v-for="(s, idx) in steps" :key="s.id" class="stepper-item">
        <button
          type="button"
          class="stepper-circle"
          :class="{
            'is-active': s.id === step,
            'is-completed': s.isCompleted,
            'is-error': s.hasError,
            'is-disabled': s.disabled
          }"
          :disabled="s.disabled"
          @click="onStepClick(s.id)"
        >
          <span>{{ s.id }}</span>
        </button>
        <div class="stepper-label">{{ s.label }}</div>

        <div
          v-if="idx < steps.length - 1"
          class="stepper-connector"
          :class="{ 'connector-completed': s.id < step }"
        ></div>
      </div>
    </div>

    <!-- STEP 1 -->
    <div v-if="step === 1" class="new-study-form">
      <div class="step1-header">
        <h2 class="step-title">{{ panelTitle }}</h2>

        <!-- Import Study Template (ONLY for new study creation) -->
        <div v-if="!isEditing" class="import-template-actions">
          <button
            type="button"
            class="btn-option"
            :disabled="importingTemplate"
            @click.prevent="triggerTemplatePick"
            title="Import a template-only JSON exported from another device"
          >
            {{ importingTemplate ? "Importing…" : "Import Study Template" }}
          </button>

          <input
            ref="templateFileInput"
            class="hidden-file"
            type="file"
            accept=".json,application/json"
            @change="onTemplatePicked"
          />

          <div v-if="templateFileName" class="import-file-name" :title="templateFileName">
            {{ templateFileName }}
          </div>

          <p v-if="templateImportError" class="import-error">{{ templateImportError }}</p>
        </div>
      </div>

      <div v-for="(f, i) in studySchema.filter((f) => f.display)" :key="i" class="schema-field-row">
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
        <button type="button" @click="backFromStep1" class="btn-option">Back</button>

        <button v-if="isEditing" type="button" class="btn-option" @click="saveThisStepAndBackToStudy">
          Save
        </button>

        <button type="button" @click="validateStudy()" class="btn-option">
          {{ stepLabelById[2] }}
        </button>
      </div>
    </div>

    <!-- STEP 2 -->
    <div v-if="step === 2" class="new-study-form">
      <h2>{{ panelTitle }}</h2>

      <GroupForm :schema="groupSchema" v-model="groupData" />

      <div class="form-actions">
        <button @click="step = 1" class="btn-option">{{ stepLabelById[1] }}</button>

        <button v-if="isEditing" type="button" class="btn-option" @click="saveThisStepAndBackToStudy">
          Save
        </button>

        <button @click="checkGroups()" class="btn-option">{{ stepLabelById[3] }}</button>
      </div>
    </div>

    <!-- STEP 3 -->
    <div v-if="step === 3" class="new-study-form">
      <h2>{{ panelTitle }}</h2>

      <div class="step-header">
        <label class="skip-toggle">
          <span class="skip-label">Skip subject creation for now</span>
          <button
            type="button"
            class="toggle-button"
            :class="{ 'toggle-on': skipSubjectCreationNow }"
            @click="skipSubjectCreationNow = !skipSubjectCreationNow"
          >
            <span class="toggle-knob" />
          </button>
        </label>
      </div>

      <SubjectForm v-model:subjectCount="subjectCount" v-model:assignmentMethod="assignmentMethod" />

      <div class="form-actions">
        <button @click="step = 2" class="btn-option">{{ stepLabelById[2] }}</button>

        <button v-if="isEditing" type="button" class="btn-option" @click="saveThisStepAndBackToStudy">
          Save
        </button>

        <button @click="checkSubjectsSetup()" class="btn-option">
          {{ nextLabelFromStep3 }}
        </button>
      </div>
    </div>

    <!-- STEP 4 -->
    <div v-if="step === 4 && assignmentMethod !== 'Skip' && !skipSubjectCreationNow" class="new-study-form">
      <h2>{{ panelTitle }}</h2>

      <SubjectAssignmentForm :subjects="subjectData" :groupData="groupData" v-model:subjects="subjectData" />

      <div class="form-actions">
        <button @click="step = 3" class="btn-option">{{ stepLabelById[3] }}</button>

        <button v-if="isEditing" type="button" class="btn-option" @click="saveThisStepAndBackToStudy">
          Save
        </button>

        <button @click="checkSubjectsAssigned()" class="btn-option">{{ stepLabelById[5] }}</button>
      </div>
    </div>

    <!-- STEP 5 -->
    <div v-if="step === 5" class="new-study-form">
      <h2>{{ panelTitle }}</h2>

      <VisitForm :schema="visitSchema" v-model="visitData" />

      <div class="form-actions">
        <button @click="goBackFromVisits" class="btn-option">{{ prevLabelForVisits }}</button>

        <button v-if="isEditing" type="button" class="btn-option" @click="saveThisStepAndBackToStudy">
          Save
        </button>

        <button @click="goToFinish()" class="btn-option">{{ stepLabelById[6] }}</button>
      </div>
    </div>
  </div>

  <!-- Dialog -->
  <div v-if="showDialog" class="dialog-backdrop">
    <div class="dialog-box">
      <p>{{ dialogMessage }}</p>

      <!-- Import success dialog actions -->
      <div v-if="dialogMode === 'importSuccess'" class="dialog-actions">
        <button class="btn-option" @click="goDashboardAfterImport">Go to Dashboard</button>
        <button class="btn-option" @click="viewImportedStudy">View Study</button>
        <button class="btn-option" @click="editImportedStudy">Edit Study</button>
        <button class="btn-option" @click="closeDialog">Close</button>
      </div>

      <button v-else @click="closeDialog" class="btn-option">OK</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, inject, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useStore } from "vuex";
import axios from "axios";
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
  props: {
    id: { type: [String, Number], required: false },
  },
  setup(props) {
    const router = useRouter();
    const route = useRoute();
    const store = useStore();
    const formatLabel = inject("formatLabel");

    const step = ref(1);
    const studyData = ref({});
    const groupData = ref([]);
    const subjectData = ref([]);
    const visitData = ref([]);
    const subjectCount = ref(1);
    const assignmentMethod = ref("Random");
    const assignments = ref([]);

    const studySchema = ref([]);
    const groupSchema = ref([]);
    const visitSchema = ref([]);

    const showStudyErrors = ref(false);
    const showDialog = ref(false);
    const dialogMessage = ref("");
    const dialogMode = ref("default"); // 'default' | 'importSuccess'

    const skipSubjectCreationNow = ref(false);

    // --- import template state ---
    const templateFileInput = ref(null);
    const importingTemplate = ref(false);
    const templateFileName = ref("");
    const templateImportError = ref("");

    // store created study info (for dialog actions)
    const importedStudyId = ref(null);
    const importedStudyName = ref("");

    const stepErrors = ref({
      1: false,
      2: false,
      3: false,
      4: false,
      5: false,
      6: false,
    });

    const editId = computed(() => props.id || route.params.id || null);
    const isEditing = computed(() => !!editId.value);

    const stepLabelById = {
      1: "Create a New Study",
      2: "Groups",
      3: "Subject Setup",
      4: "Group Assignment",
      5: "Visits",
      6: "Finish",
    };

    // keep previous titles in create mode
    const createTitleById = {
      1: "Step 1: Create a New Study",
      2: "Step 2: Groups",
      3: "Step 3: Subject Setup",
      4: "Step 4: Group Assignment",
      5: "Step 5: Visits",
      6: "Step 6: Finish",
    };

    const currentStepLabel = computed(() => stepLabelById[step.value] || "");

    const headerStudyName = computed(() => {
      const s = studyData.value || {};
      return (
        s.title ||
        s.study_name ||
        s.name ||
        (store.state.studyDetails?.study_metadata?.name ?? "") ||
        "Study"
      );
    });

    const panelTitle = computed(() => {
      if (isEditing.value) return `Editing ${headerStudyName.value}, Step ${currentStepLabel.value}`;
      return createTitleById[step.value] || "";
    });

    const nextLabelFromStep3 = computed(() => {
      const disableAssign = skipSubjectCreationNow.value || assignmentMethod.value === "Skip";
      return disableAssign ? stepLabelById[5] : stepLabelById[4];
    });

    const prevLabelForVisits = computed(() => {
      const disableAssign = skipSubjectCreationNow.value || assignmentMethod.value === "Skip";
      return disableAssign ? stepLabelById[3] : stepLabelById[4];
    });

    const token = computed(() => store.state.token);
    const authHeader = computed(() => ({ Authorization: `Bearer ${token.value}` }));
    const currentUserId = computed(() => store.state.user?.id || null);

    function closeDialog() {
      showDialog.value = false;
      dialogMode.value = "default";
    }

    function fieldError(f, value) {
      return f.required && showStudyErrors.value && !value ? `${f.label} is required.` : "";
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
          skip: d.skip || {},
        };
      });
    }

    function initializeAssignments(models, visits, groups) {
      return Array(models.length)
        .fill()
        .map(() =>
          Array(visits.length)
            .fill()
            .map(() => Array(groups.length).fill(false))
        );
    }

    function _deepClone(x) {
      try {
        return JSON.parse(JSON.stringify(x));
      } catch (err) {
        return x;
      }
    }

    //  Centralized: populate component refs from store.state.studyDetails
    function populateRefsFromStore() {
      const details = store.state.studyDetails || {};

      if (details && details.study && Object.keys(details.study).length) {
        studyData.value = { ...details.study };
      } else {
        // keep keys to avoid undefined bindings
        const base = {};
        (studySchema.value || []).forEach((f) => (base[f.field] = ""));
        studyData.value = base;
      }

      groupData.value = Array.isArray(details.groups) ? [...details.groups] : [];
      subjectCount.value = details.subjectCount ?? subjectCount.value;
      assignmentMethod.value = details.assignmentMethod ?? assignmentMethod.value;
      subjectData.value = Array.isArray(details.subjects) ? [...details.subjects] : [];
      visitData.value = Array.isArray(details.visits) ? [...details.visits] : [];
      skipSubjectCreationNow.value = !!details.skipSubjectCreationNow;

      assignments.value = Array.isArray(details.assignments)
        ? JSON.parse(JSON.stringify(details.assignments))
        : initializeAssignments(details.selectedModels || [], details.visits || [], details.groups || []);
    }

    async function saveCurrentStepToBackend() {
      if (!isEditing.value) return true;
      if (!token.value) {
        router.push("/login");
        return false;
      }

      const s = studyData.value || {};
      const payload = {
        study_metadata: {
          study_name: s.title || s.study_name || s.name,
          study_description: s.description || s.study_description,
        },
        study_content: {
          study_data: {
            study: _deepClone(studyData.value || {}),
            groups: _deepClone(groupData.value || []),
            visits: _deepClone(visitData.value || []),
            subjectCount: Number(subjectCount.value || 0),
            assignmentMethod: assignmentMethod.value || "Random",
            subjects: _deepClone(subjectData.value || []),
            assignments: _deepClone(assignments.value || []),
            skipSubjectCreationNow: !!skipSubjectCreationNow.value,
          },
        },
      };

      try {
        await axios.put(`/forms/studies/${editId.value}`, payload, {
          headers: authHeader.value,
        });
        return true;
      } catch (e) {
        const msg =
          e?.response?.data?.detail ||
          e?.response?.data?.message ||
          e?.message ||
          "Failed to save study changes.";
        dialogMessage.value = String(msg);
        dialogMode.value = "default";
        showDialog.value = true;
        return false;
      }
    }

    function validateStepOnly(stepId) {
      if (stepId === 1) return validateStudy({ advance: false });
      if (stepId === 2) return checkGroups({ advance: false });
      if (stepId === 3) return checkSubjectsSetup({ advance: false });
      if (stepId === 4) return checkSubjectsAssigned({ advance: false });
      if (stepId === 5) return checkVisits({ advance: false });
      return true;
    }

    function resolveReturnRoute() {
      const returnTo = route.query.returnTo ? String(route.query.returnTo) : "StudyView";
      const returnId =
        route.query.returnId != null
          ? String(route.query.returnId)
          : editId.value != null
          ? String(editId.value)
          : "";
      const returnTab = route.query.returnTab ? String(route.query.returnTab) : null;

      const nav = { name: returnTo };
      if (returnId) nav.params = { id: returnId };
      if (returnTab) nav.query = { tab: returnTab };
      return nav;
    }

    async function saveThisStepAndBackToStudy() {
      const ok = validateStepOnly(step.value);
      if (!ok) return;

      const saved = await saveCurrentStepToBackend();
      if (!saved) return;

      router.push(resolveReturnRoute());
    }

    function openFinishRoute() {
      const q = { ...route.query };
      if (isEditing.value) {
        q.mode = q.mode || "edit";
        q.single = q.single || "true";
        q.returnTo = q.returnTo || "StudyView";
        q.returnId = q.returnId || (editId.value != null ? String(editId.value) : "");
        q.returnTab = q.returnTab || "edit";
      }

      router.push({
        name: "CreateFormScratch",
        params: { assignments: assignments.value },
        query: q,
      });
    }

    // -----------------------
    // Import Study Template (Step 1, create mode)
    // -----------------------
    function triggerTemplatePick() {
      templateImportError.value = "";
      templateFileName.value = "";
      const el = templateFileInput.value;
      if (el) el.click();
    }

    async function onTemplatePicked(e) {
      const f = e?.target?.files && e.target.files[0];
      if (e?.target) e.target.value = "";
      if (!f) return;
      await importStudyTemplateFile(f);
    }

    function normalizeImportedStudyData(rawJson) {
      const candidate =
        rawJson?.study_data && typeof rawJson.study_data === "object" ? rawJson.study_data : rawJson;
      const sd = typeof candidate === "object" && candidate ? candidate : null;
      if (!sd || !Array.isArray(sd.selectedModels)) {
        throw new Error("Invalid template format. Missing selectedModels.");
      }
      return sd;
    }

    function buildAssignmentsIfMissing(sd) {
      const existing = Array.isArray(sd.assignments) ? sd.assignments : [];
      if (existing.length) return existing;

      const models = Array.isArray(sd.selectedModels) ? sd.selectedModels : [];
      const visits = Array.isArray(sd.visits) ? sd.visits : [];
      const groups = Array.isArray(sd.groups) ? sd.groups : [];
      return initializeAssignments(models, visits, groups);
    }

    function setScratchFormsFromSelectedModels(selectedModels) {
      if (!Array.isArray(selectedModels)) return;
      const scratchForms = [
        {
          sections: selectedModels.map((model) => ({
            title: model.title,
            fields: model.fields,
            source: "template",
          })),
        },
      ];
      localStorage.setItem("scratchForms", JSON.stringify(scratchForms));
    }

    function mergeMetaIntoStudyNode(studyNode, meta) {
      const base = _deepClone(studyNode || {});
      const metaName = meta?.study_name || meta?.name || "";
      const metaDesc = meta?.study_description || meta?.description || "";

      const titleVal = base.title || base.study_name || base.name || metaName;
      const descVal = base.description || base.study_description || metaDesc;

      return {
        ...base,
        title: titleVal,
        name: titleVal,
        study_name: titleVal,
        description: descVal,
        study_description: descVal,
      };
    }

    async function hydrateStoreFromStudyId(id) {
      const resp = await axios.get(`/forms/studies/${id}`, { headers: authHeader.value });

      const sd = resp.data?.content?.study_data || {};
      const meta = resp.data?.metadata || resp.data?.study_metadata || {};

      let assignmentsLocal = Array.isArray(sd.assignments) ? sd.assignments : [];
      if (!assignmentsLocal.length && sd.selectedModels?.length) {
        assignmentsLocal = buildAssignmentsIfMissing(sd);
      }

      const studyInfo = {
        id: meta.id ?? id,
        name: meta.study_name,
        description: meta.study_description,
        created_at: meta.created_at,
        updated_at: meta.updated_at,
        created_by: meta.created_by,
      };

      const mergedStudy = mergeMetaIntoStudyNode(sd.study, meta);

      store.commit("setStudyDetails", {
        study_metadata: studyInfo,
        study: { id: meta.id ?? id, ...mergedStudy },
        groups: sd.groups || [],
        visits: sd.visits || [],
        subjectCount: sd.subjectCount || 0,
        assignmentMethod: sd.assignmentMethod || "random",
        subjects: sd.subjects || [],
        assignments: assignmentsLocal,
        skipSubjectCreationNow: !!sd.skipSubjectCreationNow,
        forms: sd.selectedModels
          ? [
              {
                sections: sd.selectedModels.map((model) => ({
                  title: model.title,
                  fields: model.fields,
                  source: "template",
                })),
              },
            ]
          : [],
      });

      if (sd.selectedModels) setScratchFormsFromSelectedModels(sd.selectedModels);
    }

    async function importStudyTemplateFile(file) {
      templateImportError.value = "";
      templateFileName.value = file?.name || "";

      if (!token.value) {
        templateImportError.value = "Please log in again.";
        router.push("/login");
        return;
      }

      importingTemplate.value = true;
      try {
        const text = await file.text();
        const raw = JSON.parse(text);
        const sd = normalizeImportedStudyData(raw);

        const studyObj = sd.study || {};
        const studyName = studyObj.title || studyObj.study_name || raw.study_name || "Imported Study";
        const studyDescription =
          studyObj.description || studyObj.study_description || raw.study_description || "";

        const study_metadata = {
          created_by: currentUserId.value,
          study_name: studyName,
          study_description: studyDescription,
        };

        const original = _deepClone(sd);
        const studyNode = {
          ...(original.study || {}),
          title: studyName,
          name: studyName,
          study_name: studyName,
          description: studyDescription,
          study_description: studyDescription,
        };

        const study_data = {
          ...original,
          study: studyNode,
          assignments: buildAssignmentsIfMissing(original),
        };

        const payload = {
          study_metadata,
          study_content: { study_data },
        };

        const created = await axios.post("/forms/studies/", payload, { headers: authHeader.value });
        const meta = created.data?.study_metadata || created.data?.metadata || {};
        const createdId = meta.id ?? created.data?.id;

        if (createdId == null) {
          throw new Error("Study created but ID was not returned.");
        }

        // hydrate store (so Edit action works immediately)
        await hydrateStoreFromStudyId(createdId);

        importedStudyId.value = String(createdId);
        importedStudyName.value = String(meta.study_name || studyName || "Imported Study");

        dialogMode.value = "importSuccess";
        dialogMessage.value = `Imported study “${importedStudyName.value}” is saved successfully. What would you like to do next?`;
        showDialog.value = true;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(err);
        templateImportError.value =
          err?.message || "Failed to import JSON. Please select a valid template file.";
      } finally {
        importingTemplate.value = false;
      }
    }

    // Dialog actions for import-success
    function goDashboardAfterImport() {
      closeDialog();
      router.push({ name: "Dashboard", query: { openStudies: "true" } });
    }

    function viewImportedStudy() {
      if (!importedStudyId.value) {
        closeDialog();
        return;
      }
      closeDialog();
      router.push({ name: "StudyView", params: { id: importedStudyId.value } });
    }

    function editImportedStudy() {
      if (!importedStudyId.value) {
        closeDialog();
        return;
      }
      closeDialog();
      // IMPORTANT: navigating create -> edit reuses the same component instance
      // The watch(editId) below will re-hydrate and repopulate all refs.
      router.push({
        name: "CreateStudy",
        params: { id: importedStudyId.value },
        query: {
          mode: "edit",
          single: "true",
          returnTo: "Dashboard",
          returnId: "",
          returnTab: "edit",
          step: "1",
        },
      });
    }

    // ============ STEP 1 ============
    function validateStudy(opts = { advance: true }) {
      showStudyErrors.value = true;
      const hasMissing = studySchema.value.some((f) => f.required && !studyData.value[f.field]);
      stepErrors.value[1] = hasMissing;

      if (hasMissing) return false;

      showStudyErrors.value = false;
      stepErrors.value[1] = false;

      const typeField = studySchema.value.find((f) => f.field === "type");
      const skipConfig = typeField?.skip || {};
      const selected = studyData.value.type;
      const skips = skipConfig[selected] || [];

      const payload = {
        study: studyData.value,
        groups: [],
        visits: [],
        assignments: assignments.value,
        skipSubjectCreationNow: skipSubjectCreationNow.value,
      };

      store.commit("setStudyDetails", payload);

      if (!isEditing.value && opts.advance) {
        if (skips.includes("groups") && skips.includes("visits")) {
          router.push({
            name: "CreateFormScratch",
            params: { assignments: assignments.value },
          });
          return false;
        }
      }

      if (opts.advance) step.value = 2;
      return true;
    }

    // ============ STEP 2 ============
    function checkGroups(opts = { advance: true }) {
      if (!groupData.value || groupData.value.length === 0) {
        stepErrors.value[2] = true;
        dialogMessage.value = "Please add at least one group.";
        dialogMode.value = "default";
        showDialog.value = true;
        return false;
      }

      const hasErrors = groupData.value.some((g) =>
        groupSchema.value.some((f) => f.required && !g[f.field])
      );
      stepErrors.value[2] = hasErrors;
      if (hasErrors) return false;

      if (assignments.value.length > 0 && assignments.value[0]?.[0]?.length !== groupData.value.length) {
        assignments.value = initializeAssignments(studyData.value.selectedModels || [], visitData.value, groupData.value);
      }

      store.commit("setStudyDetails", {
        study: studyData.value,
        groups: groupData.value,
        visits: [],
        assignments: assignments.value,
        skipSubjectCreationNow: skipSubjectCreationNow.value,
      });

      stepErrors.value[2] = false;
      if (opts.advance) step.value = 3;
      return true;
    }

    // ============ STEP 3 ============
    function checkSubjectsSetup(opts = { advance: true }) {
      if (skipSubjectCreationNow.value) {
        stepErrors.value[3] = false;
        if (opts.advance) step.value = 5;
        return true;
      }

      if (!subjectCount.value || !assignmentMethod.value) {
        dialogMessage.value = "Please provide subject count and assignment method.";
        dialogMode.value = "default";
        showDialog.value = true;
        stepErrors.value[3] = true;
        return false;
      }

      const N = subjectCount.value;
      const prefix =
        (studyData.value.title || "ST")
          .replace(/[^A-Za-z\s]/g, "")
          .trim()
          .split(/\s+/)
          .map((w) => w[0]?.toUpperCase() || "")
          .join("") || "ST";
      const groupNames = groupData.value.map((g) => g.name || g.label || "Unnamed");

      if (isEditing.value && subjectData.value.length > 0) {
        const currentCount = subjectData.value.length;
        if (N === currentCount) {
          stepErrors.value[3] = false;
          if (opts.advance) step.value = assignmentMethod.value === "Skip" ? 5 : 4;
          return true;
        } else if (N > currentCount) {
          const additionalSubjects = Array(N - currentCount)
            .fill()
            .map((_, idx) => ({
              id: `SUBJ-${prefix}-${String(currentCount + idx + 1).padStart(3, "0")}`,
              group:
                assignmentMethod.value === "Random" && groupNames.length > 0
                  ? groupNames[Math.floor(Math.random() * groupNames.length)]
                  : "",
            }));
          subjectData.value = [...subjectData.value, ...additionalSubjects];
        } else {
          subjectData.value = subjectData.value.slice(0, N);
        }
      } else {
        let assignedGroups = [];
        if (assignmentMethod.value === "Random" && groupNames.length > 0) {
          const G = groupNames.length;
          const base = Math.floor(N / G);
          const rem = N % G;
          const idx = Array.from({ length: G }, (_, i) => i);
          for (let i = G - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [idx[i], idx[j]] = [idx[j], idx[i]];
          }
          const extra = new Set(idx.slice(0, rem));
          for (let gi = 0; gi < G; gi++) {
            const cnt = base + (extra.has(gi) ? 1 : 0);
            for (let k = 0; k < cnt; k++) assignedGroups.push(groupNames[gi]);
          }
          for (let i = assignedGroups.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [assignedGroups[i], assignedGroups[j]] = [assignedGroups[j], assignedGroups[i]];
          }
        } else {
          assignedGroups = Array(N).fill("");
        }

        subjectData.value = assignedGroups.map((grp, idx) => ({
          id: `SUBJ-${prefix}-${String(idx + 1).padStart(3, "0")}`,
          group: grp,
        }));
      }

      stepErrors.value[3] = false;
      if (opts.advance) step.value = assignmentMethod.value === "Skip" ? 5 : 4;
      return true;
    }

    // ============ STEP 4 ============
    function checkSubjectsAssigned(opts = { advance: true }) {
      if (subjectData.value.some((s) => !s.group)) {
        dialogMessage.value = "All subjects must have a group.";
        dialogMode.value = "default";
        showDialog.value = true;
        stepErrors.value[4] = true;
        return false;
      }
      stepErrors.value[4] = false;
      if (opts.advance) step.value = 5;
      return true;
    }

    // ============ STEP 5 ============
    function checkVisits(opts = { advance: true }) {
      if (!visitData.value || visitData.value.length === 0) {
        stepErrors.value[5] = true;
        dialogMessage.value = "Please add at least one visit.";
        dialogMode.value = "default";
        showDialog.value = true;
        return false;
      }

      const hasErrors = visitData.value.some((v) =>
        visitSchema.value.some((f) => f.required && !v[f.field])
      );
      stepErrors.value[5] = hasErrors;
      if (hasErrors) return false;

      store.commit("setStudyDetails", {
        study: studyData.value,
        groups: groupData.value,
        subjectCount: subjectCount.value,
        assignmentMethod: assignmentMethod.value,
        subjects: subjectData.value,
        visits: visitData.value,
        assignments: assignments.value,
        skipSubjectCreationNow: skipSubjectCreationNow.value,
      });

      stepErrors.value[5] = false;

      if (!isEditing.value && opts.advance) {
        openFinishRoute();
      }
      return true;
    }

    function goToStudyManagement() {
      router.push({ name: "Dashboard", query: { openStudies: "false" } });
    }

    function backFromStep1() {
      if (isEditing.value) router.push(resolveReturnRoute());
      else goToStudyManagement();
    }

    function goBackFromVisits() {
      if (skipSubjectCreationNow.value) step.value = 3;
      else step.value = assignmentMethod.value === "Skip" ? 3 : 4;
    }

    async function goToFinish() {
      const ok = checkVisits({ advance: false });
      if (!ok) return;
      openFinishRoute();
    }

    // ============ STEPPER LOGIC ============
    const steps = computed(() => {
      const disableAssign = skipSubjectCreationNow.value || assignmentMethod.value === "Skip";
      const rawSteps = [
        { id: 1, label: stepLabelById[1], disabled: false },
        { id: 2, label: stepLabelById[2], disabled: false },
        { id: 3, label: stepLabelById[3], disabled: false },
        { id: 4, label: stepLabelById[4], disabled: disableAssign },
        { id: 5, label: stepLabelById[5], disabled: false },
        { id: 6, label: stepLabelById[6], disabled: false },
      ];
      return rawSteps.map((raw) => {
        const disabled = raw.disabled;
        const hasError = !!stepErrors.value[raw.id];
        const isCompleted = raw.id < step.value && !hasError && !disabled;
        return { ...raw, disabled, hasError, isCompleted };
      });
    });

    function onStepClick(targetStep) {
      const disableAssign = skipSubjectCreationNow.value || assignmentMethod.value === "Skip";
      if (targetStep === step.value) return;
      if (targetStep === 4 && disableAssign) return;

      if (isEditing.value) {
        if (targetStep === 6) {
          openFinishRoute();
          return;
        }
        step.value = targetStep;
        return;
      }

      goToStep(targetStep);
    }

    function goToStep(targetStep) {
      if (targetStep < 1 || targetStep > 6) return;

      const disableAssign = skipSubjectCreationNow.value || assignmentMethod.value === "Skip";
      if (targetStep === 4 && disableAssign) return;

      if (targetStep < step.value) {
        step.value = targetStep;
        return;
      }

      const validators = {
        1: () => validateStudy({ advance: true }),
        2: () => checkGroups({ advance: true }),
        3: () => checkSubjectsSetup({ advance: true }),
        4: () => checkSubjectsAssigned({ advance: true }),
        5: () => checkVisits({ advance: true }),
      };

      const maxLogicalStep = targetStep === 6 ? 5 : Math.min(targetStep - 1, 5);
      if (maxLogicalStep <= 0) {
        step.value = 1;
        return;
      }

      const sequence = [1, 2, 3, 4, 5].filter(
        (id) => id <= maxLogicalStep && !(id === 4 && disableAssign)
      );

      for (const id of sequence) {
        if (step.value !== id) step.value = id;
        const fn = validators[id];
        if (!fn) continue;
        const ok = fn();
        if (!ok) return;
      }

      if (targetStep <= 5) step.value = targetStep;
    }

    function normalizeTargetStep(n) {
      let t = Number(n);
      if (!Number.isFinite(t)) return 1;
      if (t < 1) t = 1;
      if (t > 6) t = 6;

      const disableAssign = skipSubjectCreationNow.value || assignmentMethod.value === "Skip";
      if (t === 4 && disableAssign) t = 5;

      return t;
    }

    function applyInitialStepFromQuery() {
      if (!isEditing.value) return;
      const qs = route.query.step;
      if (qs == null) return;

      const target = normalizeTargetStep(qs);
      if (target === 6) {
        openFinishRoute();
        return;
      }
      step.value = target;
    }

    watch(
      () => route.query.step,
      () => applyInitialStepFromQuery()
    );

    async function ensureStoreDetailsLoadedForEdit() {
      if (!isEditing.value) return;

      const details = store.state.studyDetails;
      const hasSomeData = !!(details && details.study && Object.keys(details.study).length);
      if (hasSomeData) return;

      if (!token.value) return;

      try {
        await hydrateStoreFromStudyId(editId.value);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("Failed to fetch study for edit URL load:", err?.response?.data || err?.message || err);
      }
    }

    //  CRITICAL FIX: when route changes create -> edit (same component instance), reload everything
    watch(
      () => editId.value,
      async (newVal, oldVal) => {
        if (newVal === oldVal) return;

        // switching to "create new"
        if (!newVal) {
          store.commit("resetStudyDetails");
          const base = {};
          (studySchema.value || []).forEach((f) => (base[f.field] = ""));
          studyData.value = base;
          groupData.value = [];
          subjectData.value = [];
          visitData.value = [];
          subjectCount.value = 1;
          assignmentMethod.value = "Random";
          assignments.value = [];
          skipSubjectCreationNow.value = false;
          step.value = 1;
          return;
        }

        // switching to edit mode (or switching ids)
        await ensureStoreDetailsLoadedForEdit();
        populateRefsFromStore();
        applyInitialStepFromQuery();
      }
    );

    onMounted(async () => {
      if (!editId.value) store.commit("resetStudyDetails");

      await loadYaml("/study_schema.yaml", studySchema);
      await loadYaml("/group_schema.yaml", groupSchema);
      await loadYaml("/visit_schema.yaml", visitSchema);

      await ensureStoreDetailsLoadedForEdit();
      populateRefsFromStore();
      applyInitialStepFromQuery();
    });

    return {
      step,
      studyData,
      groupData,
      subjectData,
      visitData,
      subjectCount,
      assignmentMethod,
      assignments,
      studySchema,
      groupSchema,
      visitSchema,
      showDialog,
      dialogMessage,
      dialogMode,
      skipSubjectCreationNow,

      steps,
      isEditing,
      headerStudyName,
      panelTitle,

      stepLabelById,
      nextLabelFromStep3,
      prevLabelForVisits,

      fieldError,
      validateStudy,
      checkGroups,
      checkSubjectsSetup,
      checkSubjectsAssigned,
      checkVisits,

      goToStudyManagement,
      goBackFromVisits,
      onStepClick,
      backFromStep1,
      saveThisStepAndBackToStudy,
      goToFinish,

      templateFileInput,
      importingTemplate,
      templateFileName,
      templateImportError,
      triggerTemplatePick,
      onTemplatePicked,

      closeDialog,
      goDashboardAfterImport,
      viewImportedStudy,
      editImportedStudy,
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

/* Step 1 header row (title + import action) */
.step1-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.step-title {
  margin: 0;
}
.import-template-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  min-width: 240px;
}
.hidden-file {
  display: none;
}
.import-file-name {
  max-width: 320px;
  font-size: 12px;
  color: #4b5563;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.import-error {
  margin: 0;
  color: #dc2626;
  font-size: 12px;
}

@media (max-width: 640px) {
  .step1-header {
    flex-direction: column;
    align-items: stretch;
  }
  .import-template-actions {
    align-items: flex-start;
    min-width: 0;
  }
  .import-file-name {
    max-width: 100%;
  }
}

/* STEPPER */
.stepper {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-top: 20px;
}
.stepper::before {
  content: "";
  position: absolute;
  top: 16px;
  left: 0;
  right: 0;
  height: 2px;
  background: #e5e7eb;
  z-index: 0;
}
.stepper-item {
  position: relative;
  flex: 1;
  text-align: center;
}
.stepper-circle {
  position: relative;
  z-index: 2;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 2px solid #d1d5db;
  background: #f9fafb;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
}
.stepper-circle.is-active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}
.stepper-circle.is-completed {
  border-color: #16a34a;
  background: #dcfce7;
  color: #166534;
}
.stepper-circle.is-error {
  border-color: #dc2626;
  background: #fee2e2;
  color: #b91c1c;
}
.stepper-circle.is-disabled {
  cursor: default;
  opacity: 0.5;
}
.stepper-circle:disabled {
  cursor: default;
}
.stepper-label {
  font-size: 12px;
  color: #4b5563;
}
.stepper-connector {
  position: absolute;
  top: 16px;
  left: 50%;
  width: 100%;
  height: 4px;
  transform: translateY(-50%);
  background: transparent;
  border-radius: 999px;
  z-index: 1;
}
.stepper-connector.connector-completed {
  background: #16a34a;
}
@media (max-width: 640px) {
  .stepper-label {
    font-size: 11px;
  }
  .stepper-circle {
    width: 28px;
    height: 28px;
    font-size: 13px;
  }
}

/* FORMS */
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

/* Step 3 toggle row */
.step-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: 1rem;
}
.skip-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #111827;
}
.skip-label {
  white-space: nowrap;
  color: #111827;
  font-weight: 400;
  font-size: 14px;
}
.toggle-button {
  position: relative;
  width: 42px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #e5e7eb;
  padding: 0;
  cursor: pointer;
  outline: none;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.toggle-button .toggle-knob {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: transform 0.15s ease;
}
.toggle-button.toggle-on {
  background: #3b82f6;
  border-color: #2563eb;
}
.toggle-button.toggle-on .toggle-knob {
  transform: translateX(20px);
}

/* Dialog */
.dialog-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.dialog-box {
  background: white;
  padding: 20px 30px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
  text-align: center;
  max-height: 80vh;
  overflow-y: auto;
  width: min(720px, 92vw);
}

/*  Uniform buttons: grid avoids 3+1 wrap */
.dialog-actions {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
@media (max-width: 760px) {
  .dialog-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
