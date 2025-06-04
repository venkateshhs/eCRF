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
            <th rowspan="2">Section</th>
            <th v-for="(visit, vIdx) in visitList" :key="vIdx" :colspan="groupList.length">
              {{ visit.name }}
            </th>
          </tr>
          <tr>
            <template v-for="(_, vIdx) in visitList" :key="vIdx">
              <th v-for="(group, gIdx) in groupList" :key="gIdx">{{ group.name }}</th>
            </template>
          </tr>
        </thead>

        <!-- Single-visit view if >3 visits -->
        <thead v-else>
          <tr>
            <th>Section</th>
            <th v-for="(group, gIdx) in groupList" :key="gIdx">{{ group.name }}</th>
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

          &nbsp;&nbsp;

          <!-- Group nav -->
          <button @click="prevPreviewGroup" :disabled="previewGroupPos === 0" class="nav-btn">&lt;</button>
          <span>Group: {{ groupList[assignedGroups[previewGroupPos]].name }}</span>
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

    <!-- 4. Footer Actions -->
    <div class="matrix-actions">
      <button @click="$emit('edit-template')" class="btn-action">Edit Template</button>
      <button @click="saveStudy" class="btn-action">Save</button>
      <button
        @click="openPreview"
        :disabled="!hasAssignment(currentVisitIndex)"
        class="btn-action"
      >
        Preview
      </button>
      <button @click="goToSaved" class="btn-action">View Saved Study</button>
    </div>
  </div>
</template>

<script>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import axios from "axios";
import FormPreview from "@/components/FormPreview.vue";

export default {
  name: "ProtocolMatrix",
  components: { FormPreview },
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

    // Save the entire study into the database using POST /studies/
    async function saveStudy() {
      console.log("saveStudy() called");
      const studyDetails = store.state.studyDetails || {};
      const userId = store.state.user?.id;
      console.log("Retrieved userId from store:", userId);

      if (!userId) {
        console.error("saveStudy aborted: no authenticated user found in store");
        return;
      }

      // Build metadata
      const metadata = {
        created_by: userId,
        study_name: studyDetails.name || "",
        study_description: studyDetails.description || ""
      };
      console.log("Built metadata:", metadata);

      // Combine everything into a single JSON object for study_data
      const studyData = {
        ...studyDetails,
        visits: props.visits,
        groups: props.groups,
        selectedModels: props.selectedModels,
        assignments: props.assignments
      };
      console.log("Built studyData (full JSON):", studyData);

      // Final payload
      const payload = {
        study_metadata: metadata,
        study_content: { study_data: studyData }
      };
      console.log("Final payload to send:", payload);

      // Send request to POST /studies/
      try {
        console.log("Sending axios POST to /studies/ …");
        const response = await axios.post(
          "http://localhost:8000/forms/studies/",
          payload,
          {
            headers: {
              Authorization: `Bearer ${store.state.token}`
            }
          }
        );
        console.log("API response received:", response.data);
        alert("Study successfully saved to database!");
      } catch (error) {
        console.error("Error saving study to database:", error);
        alert("Failed to save study. Check console for details.");
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
  padding: 16px;
  background: #fafafa;
  border: 1px solid $border-color;
  border-radius: 6px;
}

/* Visit Pagination */
.visit-nav {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 12px;
}
.nav-btn {
  @include button-reset;
  background: $secondary-color;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
}
.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.visit-counter {
  margin: 0 8px;
  font-weight: bold;
}

/* Matrix */
.table-container {
  overflow-x: auto;
  margin-bottom: 16px;
}
.protocol-table {
  width: 100%;
  border-collapse: collapse;
}
.protocol-table th,
.protocol-table td {
  border: 1px solid $border-color;
  padding: 8px;
  text-align: center;
}

/* Preview Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.protocol-preview-modal {
  background: #fff;
  border-radius: 6px;
  width: 80%;
  max-width: 800px;
  padding: 16px;
}
.preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 1.1em;
}
.preview-content {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 4px;
  max-height: 60vh;
  overflow-y: auto;
}
.modal-actions {
  text-align: right;
  margin-top: 12px;
}

/* Footer */
.matrix-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}
.btn-action {
  @include button-reset;
  background: $primary-color;
  color: #fff;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
}
.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
