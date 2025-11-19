<template>
  <div>
    <BaseNumberField
      :modelValue="subjectCount"
      @update:modelValue="updateCount"
      id="subject-count"
      label="Number of Subjects"
      placeholder="e.g. 20"
      :required="true"
    />

    <BaseSelectField
      :modelValue="assignmentMethod"
      @update:modelValue="updateMethod"
      id="assignment-method"
      label="Assignment Method"
      :options="['Random', 'Manual', 'Skip']"
      placeholder="Select assignment method"
      :required="true"
    />
  </div>
</template>

<script>
import { watch } from "vue";
import BaseNumberField from "@/components/forms/BaseNumberField.vue";
import BaseSelectField from "@/components/forms/BaseSelectField.vue";

export default {
  name: "SubjectForm",
  components: { BaseNumberField, BaseSelectField },
  props: {
    subjectCount: Number,
    assignmentMethod: String,
  },
  emits: ["update:subjectCount", "update:assignmentMethod"],
  setup(props, { emit }) {
    watch(
      () => props.subjectCount,
      (val) => {
        if (val == null) emit("update:subjectCount", 1);
      },
      { immediate: true }
    );

    watch(
      () => props.assignmentMethod,
      (val) => {
        if (!val) emit("update:assignmentMethod", "random");
      },
      { immediate: true }
    );

    const updateCount = (val) => emit("update:subjectCount", val);
    const updateMethod = (val) => emit("update:assignmentMethod", val);

    return { updateCount, updateMethod };
  }
};
</script>


<style scoped>
.form-actions {
  margin-top: 1.5rem;
  text-align: right;
}
.btn-option {
  padding: 10px 20px;
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-option:hover {
  background: #4338ca;
}
</style>
