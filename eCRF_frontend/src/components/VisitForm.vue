<template>
  <div>
    <h2>Step 5: Define Visits</h2>

    <!-- Number of Visits -->
    <BaseNumberField
      v-model="count"
      id="numVisits"
      label="Number of Visits"
      :min="1"
      :error="errors.count"
    />

    <!-- Custom Accordion Panels -->
    <div
      v-for="(visit, idx) in visits"
      :key="idx"
      class="panel"
    >
      <div class="panel-header" @click="togglePanel(idx)">
        <span>Visit {{ idx + 1 }}</span>
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
            v-model="visit[f.field]"
            :id="`visit-${idx}-${f.field}`"
            :label="f.label"
            :placeholder="f.placeholder"
            :required="f.required"
            :options="f.options"
            :error="fieldError(f, visit[f.field])"
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
  name: "VisitForm",
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
    // how many visits
    const count = ref(props.modelValue.length || 1);

    // which panels are open
    const activePanels = ref([]);

    // local mirror of modelValue
    const visits = ref([...props.modelValue]);

    // sync if parent overwrites modelValue
    watch(
      () => props.modelValue,
      v => {
        visits.value = [...v];
        count.value = v.length;
      },
      { deep: true }
    );

    // rebuild panels whenever `count` changes, and on init
    watch(
      count,
      () => resizeVisits(),
      { immediate: true }
    );

    function resizeVisits() {
      const n = Math.max(1, count.value);
      const arr = Array.from({ length: n }, (_, i) =>
        visits.value[i] != null
          ? visits.value[i]
          : Object.fromEntries(props.schema.map(f => [f.field, ""]))
      );
      visits.value = arr;
      emit("update:modelValue", arr);

      // open all panels by default
      activePanels.value = arr.map((_, i) => i);

      // notify parent to re-validate
      emit("validate");
    }

    function togglePanel(idx) {
      const i = activePanels.value.indexOf(idx);
      if (i >= 0) activePanels.value.splice(i, 1);
      else activePanels.value.push(idx);
    }

    // count missing fields per panel
    const panelErrors = computed(() =>
      visits.value.map(v =>
        props.schema.reduce(
          (sum, f) => sum + (f.required && !v[f.field] ? 1 : 0),
          0
        )
      )
    );

    // error on the count field
    const errors = computed(() => ({
      count: count.value < 1 ? "Must have at least one visit." : ""
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
      count,
      visits,
      activePanels,
      panelErrors,
      errors,
      togglePanel,
      fieldComponent,
      fieldError,
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
  margin-left: 8px;
}
.toggle-icon {
  font-size: 0.9em;
  margin-left: 1rem;
}
.schema-field-row {
  margin-bottom: 1rem;
}
</style>
