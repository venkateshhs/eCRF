<template>
  <div v-if="visible" class="conflict-backdrop" role="dialog" aria-modal="true">
    <div class="conflict-dialog">
      <header class="conflict-header">
        <div>
          <h3>Review simultaneous changes</h3>
          <p>
            Another person saved while this form was open. Unrelated changes
            have already been combined. Choose a value for the fields below.
          </p>
        </div>
      </header>

      <div class="conflict-bulk-actions">
        <span>{{ resolvedCount }} of {{ conflicts.length }} selected</span>
        <button type="button" @click="chooseAll('local')">Use all my values</button>
        <button type="button" @click="chooseAll('latest')">Use all latest values</button>
      </div>

      <div class="conflict-table-wrapper">
        <table class="conflict-table">
          <thead>
            <tr>
              <th>Section</th>
              <th>Field</th>
              <th>What you entered</th>
              <th>What was saved by the other user</th>
              <th>Use value</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="conflict in conflicts" :key="conflict.key">
              <td class="section-cell">{{ conflict.sectionLabel || conflict.sectionKey }}</td>
              <td class="field-cell">{{ conflict.fieldLabel || conflict.fieldKey }}</td>
              <td class="value-cell">
                <ConflictValueDisplay
                  :value="conflict.localValue"
                  :other-value="conflict.latestValue"
                  :field="conflict.field || {}"
                />
              </td>
              <td class="value-cell">
                <ConflictValueDisplay
                  :value="conflict.latestValue"
                  :other-value="conflict.localValue"
                  :field="conflict.field || {}"
                />
              </td>
              <td class="choice-cell">
                <label>
                  <input
                    type="radio"
                    :name="`entry-conflict-${conflict.key}`"
                    value="local"
                    :checked="decisions[conflict.key] === 'local'"
                    @change="choose(conflict.key, 'local')"
                  />
                  Mine
                </label>
                <label>
                  <input
                    type="radio"
                    :name="`entry-conflict-${conflict.key}`"
                    value="latest"
                    :checked="decisions[conflict.key] === 'latest'"
                    @change="choose(conflict.key, 'latest')"
                  />
                  Other user
                </label>
                <label v-if="conflict.allowKeepBoth">
                  <input
                    type="radio"
                    :name="`entry-conflict-${conflict.key}`"
                    value="both"
                    :checked="decisions[conflict.key] === 'both'"
                    @change="choose(conflict.key, 'both')"
                  />
                  Keep both rows
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="conflict-footer">
        <button type="button" class="secondary" @click="$emit('cancel')">
          Keep editing
        </button>
        <button
          type="button"
          class="primary"
          :disabled="!allResolved"
          @click="$emit('confirm', { ...decisions })"
        >
          Apply choices and save
        </button>
      </footer>
    </div>
  </div>
</template>

<script>
import ConflictValueDisplay from "@/components/dataentry/ConflictValueDisplay.vue";

export default {
  name: "DataEntryConflictDialog",
  components: { ConflictValueDisplay },
  emits: ["confirm", "cancel"],
  props: {
    visible: { type: Boolean, default: false },
    conflicts: { type: Array, default: () => [] },
  },
  data() {
    return {
      decisions: {},
    };
  },
  computed: {
    resolvedCount() {
      return this.conflicts.filter((item) => !!this.decisions[item.key]).length;
    },
    allResolved() {
      return this.conflicts.length > 0 && this.resolvedCount === this.conflicts.length;
    },
  },
  watch: {
    visible(next) {
      if (next) this.decisions = {};
    },
  },
  methods: {
    choose(key, choice) {
      this.decisions = { ...this.decisions, [key]: choice };
    },
    chooseAll(choice) {
      const next = {};
      this.conflicts.forEach((item) => {
        next[item.key] = choice;
      });
      this.decisions = next;
    },
  },
};
</script>

<style scoped>
.conflict-backdrop {
  position: fixed;
  inset: 0;
  z-index: 11000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.58);
}

.conflict-dialog {
  width: min(980px, 100%);
  max-height: min(820px, 92vh);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.3);
}

.conflict-header,
.conflict-bulk-actions,
.conflict-footer {
  padding: 18px 22px;
}

.conflict-header {
  border-bottom: 1px solid #e2e8f0;
}

.conflict-header h3,
.conflict-header p {
  margin: 0;
}

.conflict-header p {
  margin-top: 7px;
  color: #475569;
  line-height: 1.45;
}

.conflict-bulk-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  background: #f8fafc;
}

.conflict-bulk-actions span {
  margin-right: auto;
  color: #475569;
  font-size: 0.9rem;
}

.conflict-bulk-actions button,
.conflict-footer button {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 13px;
  background: #fff;
  cursor: pointer;
}

.conflict-table-wrapper {
  overflow-y: auto;
  padding: 0 22px 18px;
}

.conflict-table {
  width: 100%;
  margin-top: 18px;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid #dbe3ee;
  border-radius: 10px;
  overflow: hidden;
  font-size: 0.92rem;
}

.conflict-table th,
.conflict-table td {
  padding: 12px;
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  vertical-align: top;
}

.conflict-table th:last-child,
.conflict-table td:last-child {
  border-right: 0;
}

.conflict-table tbody tr:last-child td {
  border-bottom: 0;
}

.conflict-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
}

.section-cell,
.field-cell {
  font-weight: 600;
}

.value-cell {
  min-width: 220px;
  max-width: 380px;
  overflow-wrap: anywhere;
}

.choice-cell {
  min-width: 130px;
}

.choice-cell label {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  cursor: pointer;
}

.choice-cell label:last-child {
  margin-bottom: 0;
}

.conflict-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #e2e8f0;
}

.conflict-footer .primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.conflict-footer .primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .conflict-backdrop {
    padding: 10px;
  }

  .conflict-table-wrapper {
    overflow-x: auto;
  }

  .conflict-table {
    min-width: 760px;
  }
}
</style>
