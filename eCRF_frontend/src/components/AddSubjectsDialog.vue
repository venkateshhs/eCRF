<template>
  <div class="dialog-overlay">
    <div class="dialog dialog-subjects">
      <h3>Add subjects</h3>
      <p class="dialog-subtitle">
        Enter how many new subjects to create, then assign each subject to a group.
        Existing subjects are not changed.
      </p>

      <!-- Subject count + assignment method -->
      <!-- IMPORTANT: no "Skip" here => assignmentOptions only Random + Manual -->
      <SubjectForm
        :subjectCount="subjectCount"
        :assignmentMethod="assignmentMethod"
        :assignmentOptions="['Random', 'Manual']"
        @update:subjectCount="$emit('update:subjectCount', $event)"
        @update:assignmentMethod="$emit('update:assignmentMethod', $event)"
      />

      <!-- Subjects table (scrolls when there are many subjects) -->
      <div
        v-if="subjects && subjects.length"
        class="subject-table-wrapper"
      >
        <SubjectAssignmentForm
          :subjects="subjects"
          :groupData="groupData"
          @update:subjects="$emit('update:subjects', $event)"
        />
      </div>

      <p v-if="error" class="dialog-error">
        {{ error }}
      </p>

      <div class="dialog-actions">
        <button type="button" class="btn-option" @click="$emit('close')">
          Cancel
        </button>
        <button
          type="button"
          class="btn-primary"
          @click="$emit('save')"
          :disabled="saving || !subjects || !subjects.length"
        >
          {{ saving ? 'Saving…' : 'Save subjects' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import SubjectForm from "@/components/SubjectForm.vue";
import SubjectAssignmentForm from "@/components/SubjectAssignmentForm.vue";

export default {
  name: "AddSubjectsDialog",
  components: {
    SubjectForm,
    SubjectAssignmentForm,
  },
  props: {
    subjectCount: { type: Number, required: true },
    assignmentMethod: { type: String, required: true },
    subjects: { type: Array, default: () => [] },
    groupData: { type: Array, default: () => [] },
    saving: { type: Boolean, default: false },
    error: { type: String, default: "" },
  },
  emits: [
    "update:subjectCount",
    "update:assignmentMethod",
    "update:subjects",
    "close",
    "save",
  ],
};
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* Main dialog */
.dialog {
  background: #ffffff;
  padding: 1.5rem;
  border-radius: 8px;
  width: 320px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.dialog h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.dialog-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}

.dialog-actions button:hover {
  background: #d1d5db;
}

/* Specific to add-subjects (wider + scroll-safe) */
.dialog-subjects {
  width: 640px;
  max-width: 95%;
  max-height: 80vh;      /* prevent dialog from going off screen */
  overflow-y: auto;      /* dialog scrolls if content too tall */
}

.dialog-subtitle {
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 12px;
}

/* Table area scroll: keeps header+buttons visible */
.subject-table-wrapper {
  margin-top: 16px;
  max-height: 50vh;      /* only the table area scrolls when many subjects */
  overflow-y: auto;
}

.dialog-error {
  margin-top: 8px;
  color: #dc2626;
  font-size: 13px;
}

/* Buttons */
.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-option {
  background: #e5e7eb;
  color: #111827;
}
</style>
