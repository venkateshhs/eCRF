<template>
  <div v-if="visible" class="dialog-overlay">
    <div class="dialog">
      <h3>Group assignment required</h3>
      <p>This subject has no group. Choose how you want to assign a group.</p>

      <label>
        Assignment:
        <select :value="groupAssignScope" @change="$emit('update:groupAssignScope', $event.target.value)">
          <option value="one">Assign group to this subject only</option>
          <option value="all">Assign group to all unassigned subjects</option>
        </select>
      </label>

      <label v-if="groupAssignScope === 'one'">
        Group:
        <select :value="groupAssignSelectedGroup" @change="$emit('update:groupAssignSelectedGroup', $event.target.value)">
          <option v-for="g in groupList" :key="g.name" :value="g.name">
            {{ g.name }}
          </option>
        </select>
      </label>

      <div v-else>
        <p style="margin: 0 0 10px 0;">
          Assign a group for each unassigned subject:
        </p>

        <div style="max-height: 260px; overflow: auto; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px;">
          <div
            v-for="row in localDrafts"
            :key="row.index"
            style="display:flex; align-items:center; justify-content:space-between; gap:10px; padding:6px 0; border-bottom:1px solid #f3f4f6;"
          >
            <div style="min-width:0;">
              <strong>{{ row.id || ('Subject ' + (row.index + 1)) }}</strong>
            </div>

            <div style="flex: 0 0 180px;">
              <select v-model="row.group" style="width:100%;" @change="emitDrafts">
                <option v-for="g in groupList" :key="g.name" :value="g.name">
                  {{ g.name }}
                </option>
              </select>
            </div>
          </div>

          <div v-if="!localDrafts || !localDrafts.length" style="font-size: 12px; color: #6b7280; padding: 8px 0;">
            No unassigned subjects found.
          </div>
        </div>
      </div>

      <p v-if="groupAssignError" style="color:#dc2626; font-size:12px; margin-top:6px;">
        {{ groupAssignError }}
      </p>

      <div class="dialog-actions">
        <button @click="$emit('save')" :disabled="savingGroupAssign">
          {{ savingGroupAssign ? "Saving..." : "Save" }}
        </button>
        <button @click="$emit('close')" :disabled="savingGroupAssign">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "GroupAssignDialog",
  props: {
    visible: { type: Boolean, default: false },
    groupAssignScope: { type: String, default: "one" },
    groupAssignSelectedGroup: { type: String, default: "" },
    groupAssignError: { type: String, default: "" },
    savingGroupAssign: { type: Boolean, default: false },
    groupAssignDrafts: { type: Array, default: () => [] },
    groupList: { type: Array, default: () => [] },
  },
  emits: [
    "close",
    "save",
    "update:groupAssignScope",
    "update:groupAssignSelectedGroup",
    "update:groupAssignDrafts",
  ],
  data() {
    return {
      localDrafts: [],
    };
  },
  watch: {
    groupAssignDrafts: {
      immediate: true,
      deep: true,
      handler(val) {
        this.localDrafts = Array.isArray(val) ? JSON.parse(JSON.stringify(val)) : [];
      },
    },
  },
  methods: {
    emitDrafts() {
      this.$emit("update:groupAssignDrafts", JSON.parse(JSON.stringify(this.localDrafts)));
    },
  },
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
.dialog label {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  color: #374151;
}
.dialog label select,
.dialog label input {
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
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
.dialog-actions button:first-child,
.dialog-actions button:last-child {
  background: #e5e7eb;
  color: #1f2937;
}
</style>