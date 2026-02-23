<template>
  <div class="protocol-matrix-container">
    <div class="screen-header">
      <h2 class="screen-title">Schedule of Assessments</h2>
      <button class="icon-btn header-info-btn" @click="showInfo = true" aria-label="What is Protocol Matrix?">
        <i :class="icons.info"></i>
      </button>
    </div>

    <!-- 1. Visit Navigator (when >3 visits) -->
    <div v-if="visitList.length > 3" class="visit-nav">
      <button @click="prevVisit" :disabled="currentVisitIndex === 0" class="nav-btn">&lt;</button>

      <div class="visit-nav-center">
        <span class="visit-counter">
          Visit {{ currentVisitIndex + 1 }} / {{ visitList.length }}
        </span>
        <!-- show current visit name directly below -->
        <span class="visit-name">{{ visitList[currentVisitIndex]?.name || 'Visit' }}</span>
      </div>

      <button @click="nextVisit" :disabled="currentVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
    </div>

    <!-- Bulk controls for current visit (only when many visits) -->
    <div
      v-if="visitList.length > 3 && groupList.length && selectedModels.length"
      class="visit-bulk-bar"
    >
      <label class="bulk-toggle">
        <input
          type="checkbox"
          :checked="isVisitFullySelected(currentVisitIndex)"
          @change="onToggleVisitAll(currentVisitIndex, $event.target.checked)"
        />
        <span>Assign all forms to this visit</span>
      </label>
    </div>

    <!-- 2. Protocol Matrix -->
    <div class="table-container card-surface">
      <table class="protocol-table">
        <!-- Full matrix if ≤3 visits -->
        <thead v-if="visitList.length <= 3">
          <tr>
            <th rowspan="2" class="model-header-col">
              Data Models
            </th>
            <th
              v-for="(visit, vIdx) in visitList"
              :key="`vh-${vIdx}`"
              :colspan="groupList.length"
            >
              <div class="visit-header-cell">
                <div class="visit-header-main">
                  <span class="th-title">Visit:</span>
                  <span class="th-chip">{{ visit.name }}</span>
                </div>
                <label
                  v-if="groupList.length && selectedModels.length"
                  class="bulk-toggle small"
                >
                  <input
                    type="checkbox"
                    :checked="isVisitFullySelected(vIdx)"
                    @change="onToggleVisitAll(vIdx, $event.target.checked)"
                  />
                  <span>All forms</span>
                </label>
              </div>
            </th>
          </tr>
          <tr>
            <template v-for="(_, vIdx) in visitList" :key="`vg-${vIdx}`">
              <th v-for="(group, gIdx) in groupList" :key="`vg-${vIdx}-${gIdx}`">
                <span class="group-name">Group: {{ group.name }}</span>
              </th>
            </template>
          </tr>
        </thead>

        <!-- Single-visit view if >3 visits -->
        <thead v-else>
          <tr>
            <th class="model-header-col">
              Data Models
            </th>
            <th v-for="(group, gIdx) in groupList" :key="`g-${gIdx}`">
              <span class="group-name">{{ group.name }}</span>
            </th>
          </tr>
        </thead>

        <tbody>
          <!-- hide models with no fields -->
          <tr
            v-for="(model, mIdx) in selectedModels"
            :key="`m-${mIdx}`"
            v-show="model.fields && model.fields.length"
          >
            <td class="model-cell">
              <div class="model-header-row">
                <span class="model-title">{{ model.title }}</span>
                <label
                  v-if="visitList.length && groupList.length"
                  class="bulk-toggle small"
                >
                  <input
                    type="checkbox"
                    :checked="isModelFullySelected(mIdx)"
                    @change="onToggleModelAll(mIdx, $event.target.checked)"
                  />
                  <span>All visits</span>
                </label>
              </div>
            </td>

            <!-- Full-matrix cells -->
            <template v-if="visitList.length <= 3">
              <template v-for="(_, vIdx) in visitList" :key="`row-${mIdx}-v-${vIdx}`">
                <td v-for="(_, gIdx) in groupList" :key="`cell-${mIdx}-${vIdx}-${gIdx}`">
                  <label class="chk-wrap" :title="`Toggle ${model.title} @ ${visitList[vIdx]?.name} / ${groupList[gIdx]?.name}`">
                    <input
                      type="checkbox"
                      :checked="assignments[mIdx][vIdx][gIdx]"
                      @change="onToggle(mIdx, vIdx, gIdx, $event.target.checked)"
                    />
                    <!-- Unchecked: outline square; Checked: check-square -->
                    <i class="fa-chk" :class="[assignments[mIdx][vIdx][gIdx] ? 'fas fa-check-square' : 'far fa-square']"></i>
                  </label>
                </td>
              </template>
            </template>

            <!-- Single-visit cells -->
            <template v-else>
              <td v-for="(_, gIdx) in groupList" :key="`celln-${mIdx}-${gIdx}`">
                <label class="chk-wrap" :title="`Toggle ${model.title} @ ${visitList[currentVisitIndex]?.name} / ${groupList[gIdx]?.name}`">
                  <input
                    type="checkbox"
                    :checked="assignments[mIdx][currentVisitIndex][gIdx]"
                    @change="onToggle(mIdx, currentVisitIndex, gIdx, $event.target.checked)"
                  />
                  <i class="fa-chk" :class="[assignments[mIdx][currentVisitIndex][gIdx] ? 'fas fa-check-square' : 'far fa-square']"></i>
                </label>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Global bulk control: everything -->
    <div
      v-if="visitList.length && groupList.length && selectedModels.length"
      class="global-bulk-bar"
    >
      <label class="bulk-toggle">
        <input
          type="checkbox"
          :checked="isEverythingSelected"
          @change="onToggleAll($event.target.checked)"
        />
        <span>Assign all models to all visits</span>
      </label>
    </div>

    <!-- 3. Preview Modal -->
    <div v-if="showPreviewModal" class="modal-overlay">
      <div class="modal protocol-preview-modal">
        <div class="preview-header">
          <!-- Visit nav -->
          <button @click="prevPreviewVisit" :disabled="previewVisitIndex === 0" class="nav-btn">&lt;</button>
          <span class="preview-label">
            Visit:
            <span class="th-chip">{{ visitList[previewVisitIndex].name }}</span>
          </span>
          <button @click="nextPreviewVisit" :disabled="previewVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
          <span class="spacer"></span>
          <!-- Group nav -->
          <button @click="prevPreviewGroup" :disabled="previewGroupPos === 0" class="nav-btn">&lt;</button>
          <span class="preview-label">
            Group:
            <span class="th-chip">{{ groupList[assignedGroups[previewGroupPos]]?.name }}</span>
          </span>
          <button
            @click="nextPreviewGroup"
            :disabled="previewGroupPos === assignedGroups.length - 1"
            class="nav-btn"
          >&gt;</button>
        </div>

        <div class="preview-content">
          <FormPreview :form="previewForm" />
        </div>
        <div class="modal-actions">
          <button @click="closePreview" class="btn-option">
            <i :class="icons.times" class="mr-6"></i> Close
          </button>
        </div>
      </div>
    </div>

    <!-- 4. Custom Dialog for Notifications (errors/general) -->
    <CustomDialog :message="dialogMessage" :isVisible="showDialog" @close="closeDialog" />

    <!-- 4a. Success dialog with View Saved Study CTA -->
    <div v-if="showSaveSuccessDialog" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">
          <i :class="icons.check" class="li-icon"></i> Save successful
        </h3>
        <p class="validation-text">{{ saveSuccessMessage }}</p>
        <div class="modal-actions">
          <button class="btn-option" @click="closeSaveSuccessDialog">
            <i :class="icons.times" class="mr-6"></i> Close
          </button>
          <button class="btn-primary" @click="onSuccessViewSavedStudy">
            <i :class="icons.check" class="mr-6"></i> View Saved Study
          </button>
        </div>
      </div>
    </div>

    <!-- 4b. Info dialog for ProtocolMatrix -->
    <div v-if="showInfo" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">
          <i :class="icons.infoCircle" class="li-icon"></i> What is this screen?
        </h3>
        <p class="validation-text">
          This matrix helps you decide which <strong>forms/data models</strong> are collected for each
          study <strong>Visit</strong> and <strong>Group</strong>. Click a checkbox to assign a form
          to that visit and group. Use the arrows to move between visits when there are many.
        </p>
        <ul class="empty-visits-list">
          <li>Checked = that form will appear for participants in that group at that visit.</li>
          <li>Use <strong>Preview</strong> to see what participants will fill out.</li>
          <li><strong>Save</strong> stores your setup. We’ll warn you if a visit has nothing assigned.</li>
        </ul>
        <div class="modal-actions">
          <button class="btn-primary" @click="showInfo = false">
            <i :class="icons.check" class="mr-6"></i> Got it
          </button>
        </div>
      </div>
    </div>

    <!-- 4b. Empty-visit warning modal -->
    <div v-if="showEmptyVisitsModal" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">
          <i :class="icons.infoCircle" class="li-icon"></i> Some visits have no assigned models
        </h3>
        <p class="validation-text">
          We found visits without any model assigned. You can go fix them, or save anyway.
        </p>
        <ul class="empty-visits-list">
          <li v-for="vIdx in emptyVisitIndices" :key="`empty-v-${vIdx}`">
            <span class="visit-item-title">Visit {{ vIdx + 1 }} — {{ visitList[vIdx]?.name || 'Visit' }}</span>
          </li>
        </ul>
        <div class="modal-actions">
          <button class="btn-option" @click="goToFirstEmptyVisit">
            <i :class="icons.exchangeAlt" class="mr-6"></i> Go to first empty visit
          </button>
          <button class="btn-primary" :disabled="isSavingInProgress" @click="saveAnyway">
            <i :class="icons.check" class="mr-6"></i> {{ isSavingInProgress ? 'Saving…' : 'Save anyway' }}
          </button>
          <button class="btn-option" @click="closeEmptyVisitsModal">
            <i :class="icons.times" class="mr-6"></i> Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- 4c. Confirm Template Changes (scrollable) -->
    <div v-if="showConfirmChanges" class="modal-overlay">
      <div class="modal validation-modal confirm-scroll">
        <h3 class="validation-title">
          <i :class="icons.infoCircle" class="li-icon"></i> Confirm Template Changes
        </h3>
        <p class="validation-text">
          You made structural changes. Saving will create a <strong>new template version</strong>.
          Existing data remains attached to its original versions and is not lost.
        </p>

        <!-- Scrolling area -->
        <div class="diff-scroll">
          <TemplateDiffView v-if="snapshotFrom && snapshotTo" :from="snapshotFrom" :to="snapshotTo" />
        </div>

        <div class="modal-actions sticky-actions">
          <button class="btn-option" @click="cancelConfirm">
            <i :class="icons.times" class="mr-6"></i> Cancel
          </button>
          <button class="btn-primary" @click="confirmAndSave">
            <i :class="icons.check" class="mr-6"></i> Confirm &amp; Save
          </button>
        </div>
      </div>
    </div>

    <!-- Unsaved changes dialog -->
    <div v-if="showUnsavedDialog" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">
          <i :class="icons.infoCircle" class="li-icon"></i> Unsaved changes
        </h3>
        <p class="validation-text">
          You have unsaved changes in the Visit Schedule. You can keep editing, exit without saving,
          or save as draft and exit.
        </p>
        <div class="modal-actions unsaved-actions">
          <button class="btn-option" @click="onUnsavedKeepEditing" :disabled="unsavedBusy">
            Keep editing
          </button>
          <button class="btn-option" @click="onUnsavedExitWithoutSaving" :disabled="unsavedBusy">
            Exit without saving
          </button>
          <button class="btn-primary" @click="onUnsavedSaveAndExit" :disabled="unsavedBusy">
            {{ unsavedBusy ? "Saving…" : "Save as Draft & Exit" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="matrix-actions card-surface">
      <button @click="$emit('edit-template')" class="btn-option">Back to Edit Template</button>
      <button @click="openPreview" :disabled="!hasAssignment(currentVisitIndex)" class="btn-option">Preview</button>

      <!-- FIX: explicit publish mode -->
      <button @click="saveStudy('publish')" class="btn-primary">
        Publish Study
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, onBeforeUnmount, nextTick } from "vue";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { useStore } from "vuex";
import axios from "axios";
import FormPreview from "@/components/FormPreview.vue";
import CustomDialog from "@/components/CustomDialog.vue";
import TemplateDiffView, { deepClone, computeTemplateDiff } from "@/components/TemplateDiffView.vue";
import icons from "@/assets/styles/icons";

export default {
  name: "ProtocolMatrix",
  components: { FormPreview, CustomDialog, TemplateDiffView },
  props: {
    visits: { type: Array, required: true },
    groups: { type: Array, required: true },
    selectedModels: { type: Array, required: true },
    assignments: { type: Array, required: true },
  },
  emits: ["assignment-updated", "edit-template"],
  setup(props, { emit }) {
    const router = useRouter();
    const store = useStore();

    const isEditing = computed(() => !!(store.state.studyDetails?.study_metadata?.id));

    // Matrix indices
    const currentVisitIndex = ref(0);

    // Preview indices + modal control
    const showPreviewModal = ref(false);
    const previewVisitIndex = ref(0);
    const previewGroupIndex = ref(0);

    // Dialog state
    const showInfo = ref(false);
    const showDialog = ref(false);
    const dialogMessage = ref("");

    // Success dialog state (with CTA)
    const showSaveSuccessDialog = ref(false);
    const saveSuccessMessage = ref("");

    // Empty-visit modal state
    const showEmptyVisitsModal = ref(false);
    const emptyVisitIndices = ref([]);
    const isSavingInProgress = ref(false);

    // Confirm changes
    const showConfirmChanges = ref(false);
    const snapshotFrom = ref(null);
    const snapshotTo = ref(null);

    // Baseline (server)
    const baseline = ref(null);

    // Has any data already been saved for this study?
    const hasAnyData = ref(false);

    // ---------- UNSAVED GUARD STATE ----------
    const showUnsavedDialog = ref(false);
    const unsavedBusy = ref(false);
    const allowInternalNav = ref(false);

    // Prevent duplicate unsaved dialogs (route guard + parent guard/logo nav race)
    const unsavedDialogOpenOrPending = ref(false);

    // Local dirty tracking
    const isDirty = ref(false);
    const lastSavedSnapshot = ref(null);

    const globalDirty = computed(() => !!store.state.studyCreationDirty);

    // Display lists
    const visitList = computed(() =>
      props.visits.length ? props.visits : [{ name: "All Visits" }]
    );
    const groupList = computed(() =>
      props.groups.length ? props.groups : [{ name: "All Groups" }]
    );
    const totalModels = computed(() => props.selectedModels.length);
    const totalVisits = computed(() => props.visits.length);
    const totalGroups = computed(() => props.groups.length);

    // ---------- DIRTY SNAPSHOT HELPERS ----------
    function buildDirtySnapshot() {
      const sd = store.state.studyDetails || {};
      const meta = sd.study_metadata || {};
      return deepClone({
        // Matrix props
        visits: props.visits || [],
        groups: props.groups || [],
        selectedModels: props.selectedModels || [],
        assignments: props.assignments || [],

        // Upstream study data that affects final payload and can change before matrix
        study: sd.study || {},
        subjects: sd.subjects || [],
        subjectCount: sd.subjectCount ?? 0,
        assignmentMethod: sd.assignmentMethod ?? "random",
        skipSubjectCreationNow: !!sd.skipSubjectCreationNow,

        // Metadata fields relevant to publish/draft transitions
        studyId: meta.id ?? null,
        status: meta.status ?? null,
        study_name: meta.study_name ?? meta.name ?? "",
        study_description: meta.study_description ?? meta.description ?? "",
      });
    }

    function markSavedSnapshot() {
      lastSavedSnapshot.value = buildDirtySnapshot();
      isDirty.value = false;
      if (store?._mutations?.setStudyCreationDirty) {
        store.commit("setStudyCreationDirty", false);
      }
    }

    function computeDirty() {
      try {
        const a = JSON.stringify(buildDirtySnapshot());
        const b = JSON.stringify(lastSavedSnapshot.value || {});
        isDirty.value = a !== b;
      } catch {
        isDirty.value = true;
      }

      // only set global dirty to true here; clearing happens only on successful save
      if (isDirty.value && store?._mutations?.setStudyCreationDirty) {
        store.commit("setStudyCreationDirty", true);
      }
    }

    function hasUnsavedChanges() {
      computeDirty();
      return isDirty.value || globalDirty.value;
    }

    function openUnsavedDialog() {
      if (unsavedDialogOpenOrPending.value || showUnsavedDialog.value) return;
      unsavedDialogOpenOrPending.value = true;
      showUnsavedDialog.value = true;
    }

    function closeUnsavedDialog() {
      showUnsavedDialog.value = false;
      unsavedBusy.value = false;
      unsavedDialogOpenOrPending.value = false;
    }

    // ---------- MATRIX TOGGLES ----------
    function onToggle(mIdx, vIdx, gIdx, checked) {
      emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
    }

    // --------- BULK HELPERS ---------
    function isModelFullySelected(mIdx) {
      if (!totalVisits.value || !totalGroups.value) return false;
      for (let vIdx = 0; vIdx < totalVisits.value; vIdx++) {
        for (let gIdx = 0; gIdx < totalGroups.value; gIdx++) {
          if (!props.assignments?.[mIdx]?.[vIdx]?.[gIdx]) return false;
        }
      }
      return true;
    }

    function isVisitFullySelected(vIdx) {
      if (!totalModels.value || !totalGroups.value) return false;
      for (let mIdx = 0; mIdx < totalModels.value; mIdx++) {
        for (let gIdx = 0; gIdx < totalGroups.value; gIdx++) {
          if (!props.assignments?.[mIdx]?.[vIdx]?.[gIdx]) return false;
        }
      }
      return true;
    }

    const isEverythingSelected = computed(() => {
      if (!totalModels.value || !totalVisits.value || !totalGroups.value) return false;
      for (let mIdx = 0; mIdx < totalModels.value; mIdx++) {
        if (!isModelFullySelected(mIdx)) return false;
      }
      return true;
    });

    function onToggleModelAll(mIdx, checked) {
      if (!totalVisits.value || !totalGroups.value) return;
      for (let vIdx = 0; vIdx < totalVisits.value; vIdx++) {
        for (let gIdx = 0; gIdx < totalGroups.value; gIdx++) {
          const current = !!props.assignments?.[mIdx]?.[vIdx]?.[gIdx];
          if (current !== checked) {
            emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
          }
        }
      }
    }

    function onToggleVisitAll(vIdx, checked) {
      if (!totalModels.value || !totalGroups.value) return;
      for (let mIdx = 0; mIdx < totalModels.value; mIdx++) {
        for (let gIdx = 0; gIdx < totalGroups.value; gIdx++) {
          const current = !!props.assignments?.[mIdx]?.[vIdx]?.[gIdx];
          if (current !== checked) {
            emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
          }
        }
      }
    }

    function onToggleAll(checked) {
      if (!totalModels.value || !totalVisits.value || !totalGroups.value) return;
      for (let mIdx = 0; mIdx < totalModels.value; mIdx++) {
        for (let vIdx = 0; vIdx < totalVisits.value; vIdx++) {
          for (let gIdx = 0; gIdx < totalGroups.value; gIdx++) {
            const current = !!props.assignments?.[mIdx]?.[vIdx]?.[gIdx];
            if (current !== checked) {
              emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
            }
          }
        }
      }
    }

    // Matrix nav
    function prevVisit() { if (currentVisitIndex.value > 0) currentVisitIndex.value--; }
    function nextVisit() { if (currentVisitIndex.value < visitList.value.length - 1) currentVisitIndex.value++; }

    // Preview helpers
    function groupsForVisit(vIdx) {
      return groupList.value
        .map((_, idx) => idx)
        .filter(gIdx =>
          props.selectedModels.some((_, mIdx) =>
            props.assignments[mIdx][vIdx]?.[gIdx]
          )
        );
    }
    const assignedGroups = computed(() => groupsForVisit(previewVisitIndex.value));
    const previewGroupPos = computed(() => assignedGroups.value.indexOf(previewGroupIndex.value));
    function setFirstGroup(vIdx) {
      const arr = groupsForVisit(vIdx);
      previewGroupIndex.value = arr.length ? arr[0] : 0;
    }

    // Preview nav
    function prevPreviewVisit() {
      if (previewVisitIndex.value > 0) { previewVisitIndex.value--; setFirstGroup(previewVisitIndex.value); }
    }
    function nextPreviewVisit() {
      if (previewVisitIndex.value < visitList.value.length - 1) { previewVisitIndex.value++; setFirstGroup(previewVisitIndex.value); }
    }
    function prevPreviewGroup() {
      if (previewGroupPos.value > 0) { previewGroupIndex.value = assignedGroups.value[previewGroupPos.value - 1]; }
    }
    function nextPreviewGroup() {
      if (previewGroupPos.value < assignedGroups.value.length - 1) { previewGroupIndex.value = assignedGroups.value[previewGroupPos.value + 1]; }
    }

    // Build preview form
    const previewForm = computed(() => {
      const visitName = visitList.value[previewVisitIndex.value].name;
      const groupName = groupList.value[previewGroupIndex.value].name;
      const sections = props.selectedModels
        .filter((m, mIdx) =>
          m.fields && m.fields.length &&
          props.assignments[mIdx][previewVisitIndex.value]?.[previewGroupIndex.value]
        )
        .map(m => ({ title: m.title, fields: m.fields }));
      return { formName: `Preview: ${visitName} / ${groupName}`, sections };
    });

    // At least one assignment in a visit?
    function hasAssignment(vIdx) {
      return groupList.value.some((_, gIdx) =>
        props.selectedModels.some((_, mIdx) =>
          props.assignments[mIdx]?.[vIdx]?.[gIdx] === true
        )
      );
    }

    // STRICT check against real visits (for Save)
    function hasAssignmentInVisit(vIdx) {
      return props.groups.some((_, gIdx) =>
        props.selectedModels.some((_, mIdx) =>
          props.assignments?.[mIdx]?.[vIdx]?.[gIdx] === true
        )
      );
    }
    function computeEmptyVisits() {
      const empties = [];
      const realVisitsCount = props.visits.length;
      for (let v = 0; v < realVisitsCount; v++) if (!hasAssignmentInVisit(v)) empties.push(v);
      return empties;
    }

    // ---------- SNAPSHOT BUILDERS ----------
    function buildSnapshotFromBaseline(b) {
      const base = b || {};
      return {
        study: base.study || {},
        groups: base.groups || [],
        visits: base.visits || [],
        subjects: base.subjects || [],
        selectedModels: base.selectedModels || [],
        assignments: base.assignments || []
      };
    }
    function buildSnapshotFromCurrent() {
      const sd = store.state.studyDetails || {};
      return {
        study: sd.study || {},
        groups: deepClone(props.groups || []),
        visits: deepClone(props.visits || []),
        subjects: sd.subjects || [],
        selectedModels: deepClone(props.selectedModels || []),
        assignments: deepClone(props.assignments || [])
      };
    }

    // ---------- BASELINE & DATA PRESENCE ----------
    async function loadBaselineFromServer() {
      const studyId = store.state.studyDetails?.study_metadata?.id;
      if (!studyId) {
        baseline.value = buildSnapshotFromCurrent();
        return;
      }
      try {
        const resp = await axios.get(`/forms/studies/${studyId}`, { headers: { Authorization: `Bearer ${store.state.token}` } });
        const payload = resp.data || {};
        const metadata = payload.metadata || payload.study_metadata || {};
        const studyData = payload.content?.study_data || {};

        baseline.value = {
          study: {
            id: metadata.id,
            title: (studyData.study?.title ?? metadata.study_name) || "",
            description: (studyData.study?.description ?? metadata.study_description) || ""
          },
          groups: studyData.groups || [],
          visits: studyData.visits || [],
          subjects: studyData.subjects || [],
          selectedModels: studyData.selectedModels || [],
          assignments: studyData.assignments || []
        };
      } catch (e) {
        // fall back to current snapshot
        baseline.value = buildSnapshotFromCurrent();
      }
    }

    async function loadHasAnyData() {
      const studyId = store.state.studyDetails?.study_metadata?.id;
      if (!studyId) {
        hasAnyData.value = false;
        return;
      }

      try {
        const resp = await axios.get(`/forms/studies/${studyId}/data_entries`, {
          headers: { Authorization: `Bearer ${store.state.token}` },
        });
        const list = Array.isArray(resp.data) ? resp.data : resp.data?.entries || [];
        hasAnyData.value = list.length > 0;
      } catch (e) {
        // If check fails, avoid false structural prompts
        hasAnyData.value = false;
      }
    }

    // ---------- SAVE ----------
    // mode:
    // - "publish" => actual Save button
    // - "draft"   => unsaved dialog Save as Draft & Exit
    async function saveStudy(mode = "publish") {
      const isDraftMode = mode === "draft";

      // Publish path only: empty-visit warning
      if (!isDraftMode) {
        const empties = computeEmptyVisits();
        if (empties.length > 0) {
          emptyVisitIndices.value = empties;
          showEmptyVisitsModal.value = true;
          return;
        }
      }

      // Publish path only: structural confirm for editing with existing data
      if (!isDraftMode && isEditing.value) {
        const fromSnap = buildSnapshotFromBaseline(baseline.value);
        const toSnap = buildSnapshotFromCurrent();
        const diff = computeTemplateDiff(fromSnap, toSnap);

        const shouldPrompt = hasAnyData.value && diff.anyStructural;
        if (shouldPrompt) {
          snapshotFrom.value = fromSnap;
          snapshotTo.value = toSnap;
          showConfirmChanges.value = true;
          return;
        }
      }

      await saveStudyImpl({ mode });
    }

    function showDialogMessage(message) {
      dialogMessage.value = message;
      showDialog.value = true;
    }

    function closeDialog() {
      showDialog.value = false;
      dialogMessage.value = "";
    }

    function openSaveSuccessDialog(message) {
      saveSuccessMessage.value = message;
      showSaveSuccessDialog.value = true;
    }

    function closeSaveSuccessDialog() {
      showSaveSuccessDialog.value = false;
      saveSuccessMessage.value = "";
    }

    function onSuccessViewSavedStudy() {
      closeSaveSuccessDialog();
      goToSaved();
    }

    function cancelConfirm() {
      showConfirmChanges.value = false;
    }

    async function confirmAndSave() {
      showConfirmChanges.value = false;
      await saveStudyImpl({ mode: "publish" });
    }

    function closeEmptyVisitsModal() {
      showEmptyVisitsModal.value = false;
    }

    function goToFirstEmptyVisit() {
      if (emptyVisitIndices.value.length) currentVisitIndex.value = emptyVisitIndices.value[0];
      showEmptyVisitsModal.value = false;
    }

    async function saveAnyway() {
      isSavingInProgress.value = true;
      try {
        await saveStudyImpl({ mode: "publish" });
      } finally {
        isSavingInProgress.value = false;
        showEmptyVisitsModal.value = false;
      }
    }

    // --- Save impl ---
    // mode = "publish" | "draft"
    async function saveStudyImpl({ mode = "publish" } = {}) {
      const studyDetails = store.state.studyDetails || {};
      const userId = store.state.user?.id;
      const studyId = studyDetails.study_metadata?.id;

      if (!userId) {
        showDialogMessage("Please log in again.");
        return false;
      }

      const existingMeta = studyDetails.study_metadata || {};
      const targetStatus = mode === "draft" ? "DRAFT" : "PUBLISHED";

      // IMPORTANT: explicit status is sent so backend PUT can transition DRAFT -> PUBLISHED
      const metadata = studyId
        ? {
            created_by: existingMeta.created_by ?? userId,
            study_name:
              studyDetails.study?.title ??
              existingMeta.study_name ??
              existingMeta.name ??
              "",
            study_description:
              studyDetails.study?.description ??
              existingMeta.study_description ??
              existingMeta.description ??
              "",
            status: targetStatus,
            last_completed_step: 6,
          }
        : {
            created_by: userId,
            study_name: studyDetails.study?.title ?? "",
            study_description: studyDetails.study?.description ?? "",
            status: targetStatus,
            last_completed_step: 6,
          };

      const studyData = {
        study: {
          ...(studyDetails.study || {}),
          title: studyDetails.study?.title ?? metadata.study_name ?? "",
          description: studyDetails.study?.description ?? metadata.study_description ?? "",
        },
        groups: props.groups,
        visits: props.visits,
        subjects: Array.isArray(studyDetails.subjects) ? studyDetails.subjects : [],
        selectedModels: props.selectedModels,
        assignments: props.assignments,
        subjectCount: studyDetails.subjectCount ?? 0,
        assignmentMethod: studyDetails.assignmentMethod ?? "random",
        skipSubjectCreationNow: !!studyDetails.skipSubjectCreationNow,
      };

      const payload = { study_metadata: metadata, study_content: { study_data: studyData } };

      // Keep your backend's existing "draft create via query param" behavior for POST,
      // but use explicit metadata.status for PUT/transition logic.
      let url;
      let method;

      if (studyId) {
        method = "put";
        // PUT uses explicit study_metadata.status; query params are optional/noise.
        url = `/forms/studies/${studyId}`;
      } else {
        method = "post";
        if (mode === "draft") {
          url = `/forms/studies/?status=DRAFT&last_completed_step=6`;
        } else {
          url = `/forms/studies/`;
        }
      }

      // Debug logs (you asked for visibility)
      console.log("[ProtocolMatrix saveStudyImpl] mode=", mode);
      console.log("[ProtocolMatrix saveStudyImpl] studyId=", studyId);
      console.log("[ProtocolMatrix saveStudyImpl] URL=", url, "method=", method);
      console.log("[ProtocolMatrix saveStudyImpl] existingMeta.status=", existingMeta.status);
      console.log("[ProtocolMatrix saveStudyImpl] payload.study_metadata=", payload.study_metadata);

      try {
        const headers = { headers: { Authorization: `Bearer ${store.state.token}` } };
        const response = await axios[method](url, payload, headers);

        console.log(
          "[ProtocolMatrix saveStudyImpl] response metadata=",
          response.data?.metadata || response.data?.study_metadata
        );

        const updatedMetadata = response.data?.study_metadata || response.data?.metadata || metadata;
        const updatedStudyData = response.data?.content?.study_data || studyData;

        store.commit("setStudyDetails", {
          study_metadata: {
            id: studyId || updatedMetadata?.id,
            study_name: updatedMetadata.study_name,
            name: updatedMetadata.study_name,
            description: updatedMetadata.study_description,
            study_description: updatedMetadata.study_description,
            created_at: updatedMetadata.created_at,
            updated_at: updatedMetadata.updated_at,
            created_by: updatedMetadata.created_by,
            status: updatedMetadata.status ?? targetStatus,
            draft_of_study_id: updatedMetadata.draft_of_study_id,
            last_completed_step:
              updatedMetadata.last_completed_step ??
              metadata.last_completed_step ??
              existingMeta.last_completed_step,
          },
          study: { id: studyId || updatedMetadata?.id, ...(updatedStudyData.study || {}) },
          groups: updatedStudyData.groups || [],
          visits: updatedStudyData.visits || [],
          subjectCount: updatedStudyData.subjectCount ?? 0,
          assignmentMethod: updatedStudyData.assignmentMethod ?? "random",
          subjects: updatedStudyData.subjects || [],
          assignments: updatedStudyData.assignments || [],
          selectedModels: updatedStudyData.selectedModels || [],
          skipSubjectCreationNow: !!updatedStudyData.skipSubjectCreationNow,
        });

        // Refresh baseline/data and clear dirty markers only after successful save
        await Promise.all([loadBaselineFromServer(), loadHasAnyData()]);
        await nextTick();
        markSavedSnapshot();

        // Publish save => success dialog with CTA
        if (mode === "publish") {
          openSaveSuccessDialog(
            studyId
              ? "Study successfully updated and published!"
              : "Study successfully saved and published!"
          );
        }

        return true;
      } catch (error) {
        console.error(`[ProtocolMatrix saveStudyImpl] Error ${studyId ? "updating" : "saving"} study:`, error);
        showDialogMessage(`Failed to ${studyId ? "update" : "save"} study. Check console for details.`);
        return false;
      }
    }

    function openPreview() {
      if (!hasAssignment(currentVisitIndex.value)) return;
      previewVisitIndex.value = currentVisitIndex.value;
      setFirstGroup(currentVisitIndex.value);
      showPreviewModal.value = true;
    }

    function closePreview() {
      showPreviewModal.value = false;
    }

    function goToSaved() {
      allowInternalNav.value = true;
      router
        .push({ name: "Dashboard", query: { openStudies: "true" } })
        .finally(() => {
          allowInternalNav.value = false;
        });
    }

    // ---------- UNSAVED DIALOG ACTIONS ----------
    function onUnsavedKeepEditing() {
      closeUnsavedDialog();
    }

    function onUnsavedExitWithoutSaving() {
      closeUnsavedDialog();
      allowInternalNav.value = true;
      router
        .push({ name: "Dashboard", query: { openStudies: "true" } })
        .finally(() => {
          allowInternalNav.value = false;
        });
    }

    async function onUnsavedSaveAndExit() {
      if (unsavedBusy.value) return;
      unsavedBusy.value = true;

      try {
        const ok = await saveStudyImpl({ mode: "draft" });
        if (!ok) return;

        closeUnsavedDialog();

        allowInternalNav.value = true;
        router
          .push({ name: "Dashboard", query: { openStudies: "true" } })
          .finally(() => {
            allowInternalNav.value = false;
          });
      } finally {
        unsavedBusy.value = false;
      }
    }

    // ---------- NAVIGATION / UNLOAD GUARDS ----------
    function beforeUnloadHandler(e) {
      if (!hasUnsavedChanges()) return;
      e.preventDefault();
      e.returnValue = "";
    }

    onBeforeRouteLeave((to, from, next) => {
      if (allowInternalNav.value) return next();

      // Do not stack dialogs if one is already open/pending
      if (showUnsavedDialog.value || unsavedDialogOpenOrPending.value) {
        return next(false);
      }

      if (!hasUnsavedChanges()) return next();

      openUnsavedDialog();
      next(false);
    });

    // ---------- DIRTY WATCHERS ----------
    // Watch matrix props + upstream study state so unsaved dialog also triggers
    // when user changed earlier steps / scratch form and reaches protocol matrix.
    watch(
      () => [
        props.visits,
        props.groups,
        props.selectedModels,
        props.assignments,
        store.state.studyDetails?.study,
        store.state.studyDetails?.subjects,
        store.state.studyDetails?.subjectCount,
        store.state.studyDetails?.assignmentMethod,
        store.state.studyDetails?.skipSubjectCreationNow,
        store.state.studyDetails?.study_metadata?.status,
        store.state.studyDetails?.study_metadata?.id,
      ],
      () => computeDirty(),
      { deep: true }
    );

    onMounted(async () => {
      await Promise.all([loadBaselineFromServer(), loadHasAnyData()]);

      // Baseline is current snapshot when entering screen, but keep global dirty alive.
      // If upstream steps/scratchform were dirty before entering matrix, route guard must still prompt.
      lastSavedSnapshot.value = buildDirtySnapshot();
      isDirty.value = false;

      window.addEventListener("beforeunload", beforeUnloadHandler);
    });

    onBeforeUnmount(() => {
      window.removeEventListener("beforeunload", beforeUnloadHandler);
    });



    return {
      icons,

      // state
      visitList,
      groupList,
      isEditing,

      // matrix nav
      currentVisitIndex,
      prevVisit,
      nextVisit,

      // preview
      showPreviewModal,
      previewVisitIndex,
      previewGroupIndex,
      assignedGroups,
      previewGroupPos,
      prevPreviewVisit,
      nextPreviewVisit,
      prevPreviewGroup,
      nextPreviewGroup,
      openPreview,
      closePreview,
      previewForm,

      // toggles
      onToggle,
      hasAssignment,

      // bulk helpers
      isModelFullySelected,
      isVisitFullySelected,
      isEverythingSelected,
      onToggleModelAll,
      onToggleVisitAll,
      onToggleAll,

      // dialogs
      showInfo,
      showDialog,
      dialogMessage,
      closeDialog,

      // success dialog
      showSaveSuccessDialog,
      saveSuccessMessage,
      closeSaveSuccessDialog,
      onSuccessViewSavedStudy,

      // unsaved dialog
      showUnsavedDialog,
      unsavedBusy,
      onUnsavedKeepEditing,
      onUnsavedExitWithoutSaving,
      onUnsavedSaveAndExit,

      // empty-visit modal
      showEmptyVisitsModal,
      emptyVisitIndices,
      isSavingInProgress,
      closeEmptyVisitsModal,
      goToFirstEmptyVisit,
      saveAnyway,

      // confirm changes
      showConfirmChanges,
      cancelConfirm,
      confirmAndSave,
      snapshotFrom,
      snapshotTo,

      // save + route
      saveStudy,
      goToSaved,

    };
  },
};
</script>

<style scoped lang="scss">
@import "@/assets/styles/_base.scss";

/* Subtle app-like surface and spacing */
.protocol-matrix-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 100%);
  border-radius: 12px;
}

/* Header */
.screen-header { position: relative; text-align: center; padding: 4px 4px 0; }
.screen-title { margin: 0 0 4px; font-weight: 800; font-size: 18px; color: #101828; }
.icon-btn { background: transparent; cursor: pointer; border: none; padding: 0; }
.header-info-btn { position: absolute; right: 6px; top: 50%; transform: translateY(-50%); font-size: 18px; color: #667085; }
.header-info-btn:hover { color: #111827; }

/* Reusable surface */
.card-surface { border: 1px solid $border-color; border-radius: 12px; background: #fff; box-shadow: 0 10px 25px rgba(16, 24, 40, 0.06); }

/* Visit Pagination */
.visit-nav {
  display: grid; grid-template-columns: 1fr auto 1fr;
  position: relative; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 12px; background: #f5f6fa; border: 1px solid $border-color;
}
.visit-nav .nav-btn { justify-self: start; }
.visit-nav .nav-btn:last-child { justify-self: end; }

.visit-nav-center { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.visit-counter { font-weight: 700; letter-spacing: 0.2px; color: $text-color; }

.th-chip, .visit-name {
  display: inline-block; white-space: normal; overflow-wrap: anywhere; word-break: break-word; hyphens: auto; line-height: 1.25;
  max-width: clamp(30ch, 36vw, 64ch); text-align: center;
}

.nav-btn {
  background: #ffffff; padding: 8px 12px; border: 1px solid $border-color; border-radius: $button-border-radius; cursor: pointer; font-size: 16px;
  transition: transform .05s ease, box-shadow .2s ease, background .2s ease;
}
.nav-btn:hover:not(:disabled) { background: #f8fafc; box-shadow: 0 4px 10px rgba(16,24,40,.08); }
.nav-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* Matrix */
.table-container { overflow: auto; }
.protocol-table { width: 100%; border-collapse: separate; border-spacing: 0; background: white; border-radius: 12px; overflow: hidden; }
.protocol-table thead th { position: sticky; top: 0; z-index: 1; background: #f8fafc; border-bottom: 1px solid $border-color; white-space: normal; vertical-align: middle; }
.protocol-table th, .protocol-table td { border-right: 1px solid $border-color; border-bottom: 1px solid $border-color; padding: 12px; text-align: center; font-size: 14px; }
.protocol-table th:first-child, .protocol-table td:first-child { border-left: 1px solid $border-color; }
.protocol-table tr:nth-child(even) td { background: #fbfdff; }
.protocol-table tbody tr:hover td { background: #eef6ff; }
.th-title { color: #667085; font-size: 12px; margin-right: 6px; }
.group-name { font-weight: 600; color: #101828; white-space: normal; overflow-wrap: anywhere; word-break: break-word; }
.th-chip { display: inline-block; font-size: 12px; background: #eef2ff; color: #3538cd; border: 1px solid #e0e7ff; padding: 1px 8px; border-radius: 999px; }
.model-cell { text-align: left; background: #fff; }
.model-title { font-weight: 600; color: #101828; }

/* Checkbox using Font Awesome */
.chk-wrap { --size: 18px; display: inline-flex; align-items: center; justify-content: center; width: var(--size); height: var(--size); position: relative; cursor: pointer; background: transparent; }
.chk-wrap input { opacity: 0; width: var(--size); height: var(--size); position: absolute; margin: 0; }
.fa-chk { font-size: 18px; line-height: 1; pointer-events: none; color: #98a2b3; }
.chk-wrap input:checked + .fa-chk { color: $primary-color; }
.chk-wrap:focus-within .fa-chk { outline: 2px solid rgba(52, 96, 255, .25); outline-offset: 2px; }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 12, 34, 0.45); display: flex; justify-content: center; align-items: center; z-index: 1000; padding: 12px; }
.protocol-preview-modal, .validation-modal { background: white; border-radius: 12px; width: 96%; max-width: 900px; padding: 20px; box-shadow: 0 20px 50px rgba(16,24,40,.18); }
.validation-title { margin: 0 0 6px; font-size: 18px; font-weight: 800; color: #101828; display: flex; align-items: center; gap: 8px; }
.validation-text { margin: 0 0 10px; color: #475467; }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 16px; }

/* Unsaved dialog actions */
.unsaved-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
}
@media (max-width: 760px) {
  .unsaved-actions {
    grid-template-columns: 1fr;
  }
}

/* Confirm changes scroll handling */
.confirm-scroll { max-width: 1100px; }
.diff-scroll {
  max-height: 60vh;
  overflow-y: auto;
  overflow-x: auto;
  border: 1px solid $border-color;
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}

/* Sticky footer inside confirm dialog */
.sticky-actions { position: sticky; bottom: 0; background: #fff; padding-top: 12px; margin-top: 12px; border-top: 1px solid $border-color; }

/* Footer */
.matrix-actions { position: sticky; bottom: 0; padding: 14px; display: flex; justify-content: flex-end; gap: 12px; z-index: 10; background: #fff; border: 1px solid $border-color; border-radius: 12px; }
.btn-option, .btn-primary { padding: $button-padding; border-radius: $button-border-radius; cursor: pointer; font-size: 14px; border: 1px solid transparent; transition: transform .05s ease, box-shadow .2s ease, background .2s ease, color .2s ease, border-color .2s ease; }
.btn-option { background: #ffffff; border: 1px solid $border-color; color: #111827; }
.btn-option:hover { background: #f8fafc; box-shadow: 0 6px 14px rgba(16,24,40,.08); }
.btn-primary { background: $primary-color; color: #fff; }
.btn-primary:hover { background: darken($primary-color, 6%); box-shadow: 0 8px 18px rgba(52, 96, 255, .25); }

/* Empty-visit list */
.empty-visits-list { margin: 0 0 8px 18px; padding: 0; list-style: disc; color: #344054; max-height: 40vh; overflow-y: auto; }
.empty-visits-list .visit-item-title { display: inline-block; white-space: normal; overflow-wrap: anywhere; word-break: break-word; line-height: 1.3; }

/* Small utility */
.li-icon { margin-right: 6px; }
.mr-6 { margin-right: 6px; }
.bulk-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #111827;
  cursor: pointer;
}
.bulk-toggle.small { font-size: 11px; }
.visit-bulk-bar,
.global-bulk-bar {
  display: flex;
  justify-content: flex-end;
  padding: 4px 0;
  margin-top: 4px;
}
.model-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.bulk-toggle input {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid $border-color;
  background: #ffffff;
  display: inline-block;
  position: relative;
  margin: 0;
  cursor: pointer;
}
.bulk-toggle input:checked {
  background: $primary-color;
  border-color: $primary-color;
}
.bulk-toggle input:checked::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 5px;
  width: 4px;
  height: 8px;
  border: 2px solid #ffffff;
  border-top: none;
  border-left: none;
  transform: rotate(45deg);
}
.bulk-toggle span { line-height: 1.2; }
</style>