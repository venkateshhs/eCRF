<template>
  <div class="protocol-matrix-container">
    <!-- 1. Visit Navigator (when >3 visits) -->
    <div v-if="visitList.length > 3" class="visit-nav">
      <button @click="prevVisit" :disabled="currentVisitIndex === 0" class="nav-btn">&lt;</button>
      <span class="visit-counter">
        Visit {{ currentVisitIndex + 1 }} / {{ visitList.length }}
      </span>
      <button @click="nextVisit" :disabled="currentVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
    </div>

    <!-- 2. Protocol Matrix -->
    <div class="table-container">
      <table class="protocol-table">
        <!-- Full matrix if ≤3 visits -->
        <thead v-if="visitList.length <= 3">
          <tr>
            <th rowspan="2">Data Models</th>
            <th v-for="(visit, vIdx) in visitList" :key="vIdx" :colspan="groupList.length">
              Visit: {{ visit.name }}
            </th>
          </tr>
          <tr>
            <template v-for="(_, vIdx) in visitList" :key="vIdx">
              <th v-for="(group, gIdx) in groupList" :key="gIdx">Group/Cohort: {{ group.name }}</th>
            </template>
          </tr>
        </thead>

        <!-- Single-visit view if >3 visits -->
        <thead v-else>
          <tr>
            <th>Data Models</th>
            <th v-for="(group, gIdx) in groupList" :key="gIdx">Group/Cohort: {{ group.name }}</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(model, mIdx) in selectedModels" :key="mIdx">
            <td>{{ model.title }}</td>

            <!-- Full-matrix cells -->
            <template v-if="visitList.length <= 3">
              <template v-for="(_, vIdx) in visitList" :key="vIdx">
                <td v-for="(_, gIdx) in groupList" :key="gIdx">
                  <input
                    type="checkbox"
                    :checked="assignments[mIdx][vIdx][gIdx]"
                    @change="onToggle(mIdx, vIdx, gIdx, $event.target.checked)"
                  />
                </td>
              </template>
            </template>

            <!-- Single-visit cells -->
            <template v-else>
              <td v-for="(_, gIdx) in groupList" :key="gIdx">
                <input
                  type="checkbox"
                  :checked="assignments[mIdx][currentVisitIndex][gIdx]"
                  @change="onToggle(mIdx, currentVisitIndex, gIdx, $event.target.checked)"
                />
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 3. Preview Modal -->
    <div v-if="showPreviewModal" class="modal-overlay">
      <div class="modal protocol-preview-modal">
        <div class="preview-header">
          <!-- Visit nav -->
          <button @click="prevPreviewVisit" :disabled="previewVisitIndex === 0" class="nav-btn">&lt;</button>
          <span>Visit: {{ visitList[previewVisitIndex].name }}</span>
          <button @click="nextPreviewVisit" :disabled="previewVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
          <span class="spacer"></span>
          <!-- Group nav -->
          <button @click="prevPreviewGroup" :disabled="previewGroupPos === 0" class="nav-btn">&lt;</button>
          <span>Group/Cohort: {{ groupList[assignedGroups[previewGroupPos]].name }}</span>
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
          <button @click="closePreview" class="btn-action">Close</button>
        </div>
      </div>
    </div>

    <!-- 4. Custom Dialog for Notifications -->
    <CustomDialog
      :message="dialogMessage"
      :isVisible="showDialog"
      @close="closeDialog"
    />

    <!-- 5. Footer Actions -->
    <div class="matrix-actions">
      <button @click="$emit('edit-template')" class="btn-option">Edit Template</button>
      <button @click="saveStudy" class="btn-primary">Save</button>
      <button
        @click="openPreview"
        :disabled="!hasAssignment(currentVisitIndex)"
        class="btn-option"
      >
        Preview
      </button>
      <button @click="goToSaved" class="btn-option">View Saved Study</button>
    </div>
  </div>
</template>

<script>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import axios from "axios";
import FormPreview from "@/components/FormPreview.vue";
import CustomDialog from "@/components/CustomDialog.vue";

export default {
  name: "ProtocolMatrix",
  components: { FormPreview, CustomDialog },
  props: {
    visits:         { type: Array, required: true },
    groups:         { type: Array, required: true },
    selectedModels: { type: Array, required: true },
    assignments:    { type: Array, required: true }
  },
  emits: ["assignment-updated", "edit-template"],
  setup(props, { emit }) {
    const router = useRouter();
    const store = useStore();

    // Matrix indices
    const currentVisitIndex = ref(0);

    // Preview indices + modal control
    const showPreviewModal  = ref(false);
    const previewVisitIndex = ref(0);
    const previewGroupIndex = ref(0);

    // Dialog state
    const showDialog = ref(false);
    const dialogMessage = ref("");

    // Lists with fallback
    const visitList = computed(() => props.visits.length ? props.visits : [{ name: "All Visits" }]);
    const groupList = computed(() => props.groups.length ? props.groups : [{ name: "All Groups" }]);

    // Toggle a checkbox
    function onToggle(mIdx, vIdx, gIdx, checked) {
      console.log("onToggle called:", { mIdx, vIdx, gIdx, checked });
      emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
    }

    // Matrix nav
    function prevVisit() {
      if (currentVisitIndex.value > 0) {
        currentVisitIndex.value--;
        console.log("Switched to matrix visit index:", currentVisitIndex.value);
      }
    }
    function nextVisit() {
      if (currentVisitIndex.value < visitList.value.length - 1) {
        currentVisitIndex.value++;
        console.log("Switched to matrix visit index:", currentVisitIndex.value);
      }
    }

    // Determine which groups are assigned in a given visit
    function groupsForVisit(vIdx) {
      const arr = groupList.value
        .map((_, idx) => idx)
        .filter(gIdx =>
          props.selectedModels.some((_, mIdx) =>
            props.assignments[mIdx][vIdx]?.[gIdx]
          )
        );
      console.log(`groupsForVisit(${vIdx}) =>`, arr);
      return arr;
    }
    const assignedGroups = computed(() => groupsForVisit(previewVisitIndex.value));
    const previewGroupPos = computed(() => assignedGroups.value.indexOf(previewGroupIndex.value));

    function setFirstGroup(vIdx) {
      const arr = groupsForVisit(vIdx);
      previewGroupIndex.value = arr.length ? arr[0] : 0;
      console.log("setFirstGroup(): previewGroupIndex set to", previewGroupIndex.value);
    }

    // Preview nav
    function prevPreviewVisit() {
      if (previewVisitIndex.value > 0) {
        previewVisitIndex.value--;
        console.log("Preview visit changed to:", previewVisitIndex.value);
        setFirstGroup(previewVisitIndex.value);
      }
    }
    function nextPreviewVisit() {
      if (previewVisitIndex.value < visitList.value.length - 1) {
        previewVisitIndex.value++;
        console.log("Preview visit changed to:", previewVisitIndex.value);
        setFirstGroup(previewVisitIndex.value);
      }
    }
    function prevPreviewGroup() {
      if (previewGroupPos.value > 0) {
        previewGroupIndex.value = assignedGroups.value[previewGroupPos.value - 1];
        console.log("Preview group changed to:", previewGroupIndex.value);
      }
    }
    function nextPreviewGroup() {
      if (previewGroupPos.value < assignedGroups.value.length - 1) {
        previewGroupIndex.value = assignedGroups.value[previewGroupPos.value + 1];
        console.log("Preview group changed to:", previewGroupIndex.value);
      }
    }

    // Build preview form for current visit & group
    const previewForm = computed(() => {
      const visitName = visitList.value[previewVisitIndex.value].name;
      const groupName = groupList.value[previewGroupIndex.value].name;
      const sections = props.selectedModels
        .filter((_, mIdx) =>
          props.assignments[mIdx][previewVisitIndex.value]?.[previewGroupIndex.value]
        )
        .map(m => ({ title: m.title, fields: m.fields }));
      console.log("Building previewForm with:", { visitName, groupName, sections });
      return { formName: `Preview: ${visitName} / ${groupName}`, sections };
    });

    // Only open preview if the current visit has at least one assignment
    function hasAssignment(vIdx) {
      const result = groupList.value.some((_, gIdx) =>
        props.selectedModels.some((_, mIdx) =>
          props.assignments[mIdx][vIdx]?.[gIdx]
        )
      );
      console.log(`hasAssignment(${vIdx}) =>`, result);
      return result;
    }
    function openPreview() {
      console.log("openPreview() called for visit:", currentVisitIndex.value);
      if (!hasAssignment(currentVisitIndex.value)) {
        console.log("openPreview aborted: no assignments in visit", currentVisitIndex.value);
        return;
      }
      previewVisitIndex.value = currentVisitIndex.value;
      setFirstGroup(currentVisitIndex.value);
      showPreviewModal.value = true;
      console.log("Preview modal opened at:", { previewVisitIndex: previewVisitIndex.value, previewGroupIndex: previewGroupIndex.value });
    }
    function closePreview() {
      showPreviewModal.value = false;
      console.log("Preview modal closed");
    }

    // Dialog control
    function showDialogMessage(message) {
      console.log("Showing dialog with message:", message);
      dialogMessage.value = message;
      showDialog.value = true;
    }
    function closeDialog() {
      showDialog.value = false;
      dialogMessage.value = "";
      console.log("Dialog closed");
    }

    // Save or update the study in the database
    async function saveStudy() {
      console.log("saveStudy() called");
      const studyDetails = store.state.studyDetails || {};
      console.log("studyDetails", studyDetails);
      const userId = store.state.user?.id;
      const studyId = studyDetails.study_metadata?.id;
      console.log("Retrieved userId:", userId, "studyId:", studyId);

      if (!userId) {
        console.error("saveStudy aborted: no authenticated user found in store");
        showDialogMessage("Please log in again.");
        return;
      }

      // Prepare study data
      const studyData = {
        ...studyDetails,
        visits: props.visits,
        groups: props.groups,
        selectedModels: props.selectedModels,
        assignments: props.assignments
      };
      console.log("Built studyData:", studyData);

      // Prepare metadata
      let metadata;
      if (studyId) {
        // Update existing study
        const existingMetadata = studyDetails.study_metadata || {};
        metadata = {
          created_by: existingMetadata.created_by === userId ? existingMetadata.created_by : userId,
          study_name: studyDetails.study?.title || existingMetadata.name || "",
          study_description: existingMetadata.description || studyDetails.study?.description || "",
          created_at: existingMetadata.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        console.log("Updated metadata for existing study:", metadata);
      } else {
        // Create new study
        metadata = {
          created_by: userId,
          study_name: studyDetails.study?.title || "",
          study_description: studyDetails.study?.description || "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        console.log("New metadata for new study:", metadata);
      }

      // Final payload
      const payload = {
        study_metadata: metadata,
        study_content: { study_data: studyData }
      };
      console.log("Final payload to send:", payload);

      // Send request
      const url = studyId ? `http://localhost:8000/forms/studies/${studyId}` : "http://localhost:8000/forms/studies/";
      const method = studyId ? "put" : "post";
      try {
        console.log(`Sending ${method.toUpperCase()} to ${url} …`);
        const response = await axios[method](
          url,
          payload,
          {
            headers: {
              Authorization: `Bearer ${store.state.token}`
            }
          }
        );
        console.log("API response received:", response.data);

        // Update Vuex store with the response data
        const updatedMetadata = response.data.study_metadata || metadata;
        const updatedStudyData = response.data.content?.study_data || studyData;
        store.commit("setStudyDetails", {
          study_metadata: {
            id: studyId || response.data.study_metadata?.id,
            name: updatedMetadata.study_name,
            description: updatedMetadata.study_description,
            created_at: updatedMetadata.created_at,
            updated_at: updatedMetadata.updated_at,
            created_by: updatedMetadata.created_by
          },
          study: { id: studyId || response.data.study_metadata?.id, ...updatedStudyData.study },
          groups: updatedStudyData.groups,
          visits: updatedStudyData.visits,
          subjectCount: updatedStudyData.subjectCount,
          assignmentMethod: updatedStudyData.assignmentMethod,
          subjects: updatedStudyData.subjects
        });

        showDialogMessage(studyId ? "Study successfully updated!" : "Study successfully saved!");
      } catch (error) {
        console.error(`Error ${studyId ? "updating" : "saving"} study:`, error);
        showDialogMessage(`Failed to ${studyId ? "update" : "save"} study. Check console for details.`);
      }
    }

    function goToSaved() {
      console.log("goToSaved(): navigating to /saved-study");
      router.push("/saved-study");
    }

    return {
      // matrix
      visitList,
      groupList,
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
      // dialog
      showDialog,
      dialogMessage,
      closeDialog,
      // save
      saveStudy,
      goToSaved
    };
  }
};
</script>

<style scoped lang="scss">
@import "@/assets/styles/_base.scss";

.protocol-matrix-container {
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: white;
  border: 1px solid $border-color;
  border-radius: 8px;
  min-height: calc(100vh - 100px);
}

/* Visit Pagination */
.visit-nav {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 20px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
}

.nav-btn {
  @include button-reset;
  background: $secondary-color;
  padding: 8px 12px;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  font-size: 16px;
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.visit-counter {
  margin: 0 12px;
  font-weight: 600;
  color: $text-color;
}

/* Matrix */
.table-container {
  flex: 1;
  overflow-x: auto;
  margin-bottom: 20px;
}

.protocol-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.protocol-table th,
.protocol-table td {
  border: 1px solid $border-color;
  padding: 12px;
  text-align: center;
  font-size: 14px;
}

.protocol-table th {
  background: #f5f5f5;
  color: $text-color;
  font-weight: 600;
  text-align: left;
  padding: 12px 16px;
}

.protocol-table td {
  background: #f9f9f9;
  text-align: center;
}

.protocol-table tr:nth-child(even) td {
  background: #f0f4f8;
}

.protocol-table tr:hover td {
  background: #e3effd;
}

.protocol-table input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* Preview Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.protocol-preview-modal {
  background: white;
  border-radius: 8px;
  width: 80%;
  max-width: 800px;
  padding: 20px;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  background: #f2f3f4;
  padding: 12px;
  border-radius: 4px;
}

.spacer {
  flex: 1;
}

.preview-content {
  background: white;
  padding: 16px;
  border: 1px solid $border-color;
  border-radius: 4px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

/* Footer */
.matrix-actions {
  position: sticky;
  bottom: 0;
  background: white;
  padding: 15px 0;
  border-top: 1px solid $border-color;
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  z-index: 10;
}

.btn-option {
  background: $secondary-color;
  padding: $button-padding;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 0 1 auto;
  font-size: 14px;
}

.btn-primary {
  background: $primary-color;
  color: white;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 0 1 auto;
  font-size: 14px;
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>