<template>
  <div>
    <h2>Define Groups/Cohorts</h2>

    <BaseNumberField
      v-model="count"
      id="numGroups"
      label="Number of Groups"
      :min="1"
      :error="errors.count"
    />

    <div
      v-for="(group, idx) in groups"
      :key="idx"
      class="panel"
    >
      <div class="panel-header" @click="togglePanel(idx)">
        <span>Group {{ idx + 1 }}</span>
        <span v-if="panelErrors[idx]" class="error-badge">
          {{ panelErrors[idx] }} error(s)
        </span>
        <span class="toggle-icon">
          {{ activePanels.includes(idx) ? '▼' : '▶' }}
        </span>
      </div>
      <div v-show="activePanels.includes(idx)" class="panel-body">
        <div
          v-for="f in schema"
          :key="f.field"
          class="schema-field-row"
        >
          <component
            :is="fieldComponent(f)"
            v-model="group[f.field]"
            :id="`group-${idx}-${f.field}`"
            :label="f.label"
            :placeholder="f.placeholder"
            :required="f.required"
            :options="f.options"
            :error="fieldError(f, group[f.field])"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, computed } from "vue";
import BaseTextarea    from "@/components/forms/BaseTextarea.vue";
import BaseSelectField from "@/components/forms/BaseSelectField.vue";
import BaseNumberField from "@/components/forms/BaseNumberField.vue";
import BaseDateField   from "@/components/forms/BaseDateField.vue";
import BaseTextField   from "@/components/forms/BaseTextField.vue";

export default {
  name: "GroupForm",
  components: {
    BaseTextarea,
    BaseSelectField,
    BaseNumberField,
    BaseDateField,
    BaseTextField,
  },
  props: {
    schema:     { type: Array, default: () => [] },
    modelValue: { type: Array, default: () => [] },
  },
  emits: ["update:modelValue", "validate"],
  setup(props, { emit }) {
    const count        = ref(props.modelValue.length || 1);
    const activePanels = ref([]);
    const groups       = ref([...props.modelValue]);

    // sync parent→local
    watch(
      () => props.modelValue,
      v => {
        groups.value = [...v];
        count.value  = v.length;
      },
      { deep: true }
    );

    // build panels immediately & on count change
    watch(
      count,
      () => resizeGroups(),
      { immediate: true }
    );

    function resizeGroups() {
      const n = Math.max(1, count.value);
      const arr = Array.from({ length: n }, (_, i) =>
        groups.value[i] != null
          ? groups.value[i]
          : Object.fromEntries(props.schema.map(f => [f.field, ""]))
      );
      groups.value = arr;
      emit("update:modelValue", arr);
      // open them all:
      activePanels.value = arr.map((_, i) => i);
      emit("validate");
    }

    function togglePanel(idx) {
      const i = activePanels.value.indexOf(idx);
      if (i >= 0) activePanels.value.splice(i, 1);
      else         activePanels.value.push(idx);
    }

    const panelErrors = computed(() =>
      groups.value.map(g =>
        props.schema.reduce(
          (sum, f) => sum + (f.required && !g[f.field] ? 1 : 0),
          0
        )
      )
    );
    const errors = computed(() => ({
      count: count.value < 1 ? "Must have at least one group." : ""
    }));

    function fieldComponent(f) {
      switch (f.type) {
        case "textarea": return BaseTextarea;
        case "select":   return BaseSelectField;
        case "number":   return BaseNumberField;
        case "date":     return BaseDateField;
        default:         return BaseTextField;
      }
    }
    function fieldError(f, val) {
      return f.required && !val ? `${f.label} is required.` : "";
    }

    return {
      count, groups, activePanels,
      panelErrors, errors,
      togglePanel, fieldComponent, fieldError
    };
  }
};
</script>

<style scoped>
.panel {
  border: 1px solid #ddd;
  border-radius: 4px;
  margin: 1rem 0;
}
.panel-header {
  background: #f1f1f1;
  padding: 0.75rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-body {
  padding: 1rem;
  border-top: 1px solid #ddd;
}
.error-badge {
  background: #fdd;
  color: #a00;
  border-radius: 12px;
  padding: 2px 6px;
  font-size: 0.8em;
}
.toggle-icon {
  margin-left: 1rem;
}
.schema-field-row {
  margin-bottom: 1rem;
}
</style>
