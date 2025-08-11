<template>
  <label class="fcx-wrapper">
    <input type="checkbox" :id="id" v-model="proxy" />
  </label>
</template>

<script>
export default {
  name: "FieldCheckbox",
  props: {
    modelValue: { type: Boolean, default: false },
    id: { type: String, default: null },
  },
  emits: ["update:modelValue"],
  computed: {
    proxy: {
      get() { return !!this.modelValue; },
      set(v) { this.$emit("update:modelValue", !!v); }
    }
  }
};
</script>

<style scoped>
.fcx-wrapper input[type="checkbox"] {
  display: inline-block !important;
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
  border: 2px solid #ccc;
  border-radius: 4px;
  background-color: #fff;
  appearance: none;
  position: relative;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}
.fcx-wrapper input[type="checkbox"]:checked {
  background-color: #444;
  border-color: #444;
}
.fcx-wrapper input[type="checkbox"]:checked::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 5px;
  width: 4px;
  height: 8px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
</style>
