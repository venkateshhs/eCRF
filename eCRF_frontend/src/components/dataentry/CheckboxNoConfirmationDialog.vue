<template>
  <div v-if="visible" class="dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="checkbox-no-title">
    <div class="dialog">
      <h3 id="checkbox-no-title">Confirm unchecked answers</h3>
      <p class="dialog-intro">
        The checkbox questions below are unanswered. Review them before saving.
        Any question left unchecked will be recorded as <strong>No</strong> and counted as answered.
      </p>

      <div class="section-list">
        <section v-for="group in groupedCandidates" :key="group.sectionIndex" class="section-group">
          <h4>{{ group.sectionTitle }}</h4>
          <button
            v-for="item in group.items"
            :key="item.key"
            type="button"
            class="question-link"
            @click="$emit('jump', item)"
          >
            <span>{{ item.fieldLabel }}</span>
            <span class="change-label">Go to question</span>
          </button>
        </section>
      </div>

      <label class="confirmation-check">
        <input v-model="confirmed" type="checkbox" />
        <span>
          I have reviewed these questions and confirm that the unchecked answers
          should be recorded as “No”.
        </span>
      </label>

      <div class="dialog-actions">
        <button
          type="button"
          class="btn-confirm"
          :disabled="!confirmed"
          @click="$emit('confirm')"
        >
          Confirm and Save
        </button>
        <button type="button" class="btn-cancel" @click="$emit('cancel')">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CheckboxNoConfirmationDialog",
  props: {
    visible: { type: Boolean, default: false },
    candidates: { type: Array, default: () => [] },
  },
  emits: ["confirm", "cancel", "jump"],
  data() {
    return {
      confirmed: false,
    };
  },
  computed: {
    groupedCandidates() {
      const groups = [];
      const bySection = new Map();

      (this.candidates || []).forEach((item) => {
        if (!bySection.has(item.sectionIndex)) {
          const group = {
            sectionIndex: item.sectionIndex,
            sectionTitle: item.sectionTitle,
            items: [],
          };
          bySection.set(item.sectionIndex, group);
          groups.push(group);
        }
        bySection.get(item.sectionIndex).items.push(item);
      });

      return groups;
    },
  },
  watch: {
    visible(next) {
      if (next) this.confirmed = false;
    },
  },
};
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
}

.dialog {
  width: min(680px, 100%);
  max-height: min(760px, calc(100vh - 40px));
  overflow: auto;
  padding: 24px;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.2);
}

h3,
h4,
p {
  margin-top: 0;
}

h3 {
  margin-bottom: 8px;
  color: #111827;
}

.dialog-intro {
  margin-bottom: 18px;
  color: #4b5563;
  line-height: 1.5;
}

.section-list {
  max-height: 340px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.section-group + .section-group {
  border-top: 1px solid #e5e7eb;
}

.section-group h4 {
  margin: 0;
  padding: 10px 12px;
  background: #f3f4f6;
  color: #374151;
  font-size: 14px;
}

.question-link {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 12px;
  border: 0;
  border-top: 1px solid #f3f4f6;
  background: #ffffff;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.question-link:hover,
.question-link:focus-visible {
  background: #f9fafb;
}

.change-label {
  flex: 0 0 auto;
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
}

.confirmation-check {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 18px;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  color: #1f2937;
  line-height: 1.45;
  cursor: pointer;
}

.confirmation-check input {
  width: 17px;
  height: 17px;
  margin-top: 2px;
  flex: 0 0 auto;
  cursor: pointer;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-confirm,
.btn-cancel {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-confirm {
  border: 0;
  background: #16a34a;
  color: #ffffff;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
}
</style>
