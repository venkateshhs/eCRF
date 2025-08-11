<template>
  <div class="frg">
    <label
      v-for="(opt, i) in options"
      :key="i"
      class="radio-label"
    >
      <input
        type="radio"
        :name="name"
        :value="opt"
        v-model="proxy"
      />
      {{ opt }}
    </label>
  </div>
</template>

<script>
export default {
  name: "FieldRadioGroup",
  props: {
    modelValue: { type: [String, Number], default: "" },
    options: { type: Array, default: () => [] },
    name: { type: String, default: "radio" }
  },
  emits: ["update:modelValue"],
  computed: {
    proxy: {
      get() { return this.modelValue; },
      set(v) { this.$emit("update:modelValue", v); }
    }
  }
};
</script>

<style scoped>
.frg {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
}
.radio-label input[type="radio"] {
  display: inline-block !important;
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
  border: 2px solid #ccc;
  border-radius: 50%;
  background-color: #fff;
  appearance: none;
  position: relative;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}
.radio-label input[type="radio"]:checked {
  background-color: #444;
  border-color: #444;
}
.radio-label input[type="radio"]:checked::after {
  content: '';
  position: absolute;
  top: 4px;
  left: 4px;
  width: 8px;
  height: 8px;
  background: #fff;
  border-radius: 50%;
}
</style>
