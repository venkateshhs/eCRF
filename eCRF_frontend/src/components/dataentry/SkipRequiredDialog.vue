<template>
  <div v-if="visible" class="dialog-overlay">
    <div class="dialog dialog-wide">
      <h3>Fix validation before saving</h3>
      <p>
        The fields below are required but empty. You can fill them now or choose to
        <em>Skip for now</em> to save the rest.
      </p>

      <div class="skip-list">
        <div class="skip-row" v-for="item in skipCandidates" :key="item.key">
          <div class="skip-left">
            <div class="skip-title">
              <strong>{{ item.sectionTitle }}</strong> / {{ item.fieldLabel }}
            </div>
          </div>
          <div class="skip-right">
            <label class="skip-chk">
              <input
                type="checkbox"
                :checked="!!localSelections[item.key]"
                @change="onSelectionChange(item.key, $event.target.checked)"
              />
              Skip for now
            </label>
            <button class="btn-jump" @click="$emit('jump', item)">Go to field</button>
          </div>
        </div>
      </div>

      <div class="dialog-actions">
        <button @click="$emit('confirm', localSelections)" class="btn-primary" :disabled="!canEdit">
          Skip selected & Save
        </button>
        <button @click="$emit('cancel')" class="btn-option">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "SkipRequiredDialog",
  props: {
    visible: { type: Boolean, default: false },
    skipCandidates: { type: Array, default: () => [] },
    skipSelections: { type: Object, default: () => ({}) },
    canEdit: { type: Boolean, default: true },
  },
  emits: ["confirm", "cancel", "jump"],
  data() {
    return {
      localSelections: {},
    };
  },
  watch: {
    skipSelections: {
      immediate: true,
      deep: true,
      handler(val) {
        this.localSelections = { ...(val || {}) };
      },
    },
  },
  methods: {
    onSelectionChange(key, checked) {
      this.localSelections = {
        ...this.localSelections,
        [key]: checked,
      };
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
.dialog-wide {
  width: 680px;
  max-width: 95%;
}
.skip-list {
  max-height: 360px;
  overflow: auto;
  border: 1px dashed #e5e7eb;
  padding: 8px;
  border-radius: 8px;
  margin: 10px 0;
}
.skip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px;
  border-bottom: 1px solid #f3f4f6;
  gap: 12px;
}
.skip-row:last-child {
  border-bottom: none;
}
.skip-left {
  min-width: 0;
}
.skip-title {
  font-size: 14px;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.skip-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.skip-chk {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn-jump {
  background: #e5e7eb;
  color: #111827;
  border: none;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.btn-jump:hover {
  background: #d1d5db;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}
.btn-option {
  background: #e5e7eb;
  color: #111827;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}
</style>