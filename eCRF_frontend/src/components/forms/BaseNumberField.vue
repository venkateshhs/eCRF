<template>
  <div class="form-field">
    <label :for="id" class="form-label">
      {{ label }}<span v-if="required" class="required">*</span>
    </label>
    <input
      :id="id"
      type="number"
      :class="['form-input', { 'input-error': error }]"
      :value="modelValue"
      @input="onInput"
      :min="min"
      :max="max"
      :step="step"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
    />
    <div v-if="error" class="form-error">
      <slot name="error">{{ error }}</slot>
    </div>
  </div>
</template>

<script>
export default {
  name: "BaseNumberField",
  props: {
    modelValue: { type: Number, default: null },
    id:         { type: String, required: true },
    label:      { type: String, required: true },
    placeholder:{ type: String, default: "" },
    min:        { type: Number, default: null },
    max:        { type: Number, default: null },
    step:       { type: [Number,String], default: 1 },
    required:   { type: Boolean, default: false },
    disabled:   { type: Boolean, default: false },
    error:      { type: [String,Boolean], default: false },
  },
  methods: {
    onInput(e) {
      const val = e.target.valueAsNumber
      this.$emit('update:modelValue', isNaN(val) ? null : val)
    }
  }
};
</script>

<style scoped>
.form-field { margin-bottom: 1rem; }
.form-label {
  display: block;
  margin-bottom: 0.25rem;
}
.form-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font: inherit;
  box-sizing: border-box;
  transition: border-color 0.2s;
}
.input-error {
  border-color: #c00 !important;
}
.required {
  color: red;
  margin-left: 0.25rem;
}
.form-error {
  color: #c00;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}
</style>
