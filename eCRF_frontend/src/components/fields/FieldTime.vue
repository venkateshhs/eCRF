<template>
  <input
    class="ftm-input"
    :id="id"
    type="time"
    v-model="proxy"
    :step="computedStep"
    :placeholder="placeholder"
  />
</template>

<script>
export default {
  name: "FieldTime",
  props: {
    modelValue: { type: String, default: "" }, // "HH:mm" or "HH:mm:ss"
    format: { type: String, default: "HH:mm" }, // used to infer seconds if no step provided
    step: { type: [Number, String, null], default: null }, // seconds
    placeholder: { type: String, default: "HH:mm" },
    id: { type: String, default: null }
  },
  emits: ["update:modelValue"],
  computed: {
    proxy: {
      get() { return this.modelValue || ""; },
      set(v) { this.$emit("update:modelValue", v || ""); }
    },
    computedStep() {
      if (this.step != null && this.step !== "") return this.step;
      // if format includes seconds, step 1 sec; else browser default (usually 60)
      return /s/.test(this.format) ? 1 : undefined;
    }
  }
};
</script>

<style scoped>
.ftm-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 14px;
  color: #1f2937;
}
</style>
