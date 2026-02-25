<template>
  <div class="form-field">
    <label :for="id" class="form-label">
      {{ label }}<span v-if="required" class="required">*</span>
    </label>
    <select
      :id="id"
      :class="['form-input', { 'input-error': error }]"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
      :required="required"
      :disabled="disabled"
    >
      <option value="" disabled>{{ placeholder || 'Select…' }}</option>
      <option
        v-for="opt in options"
        :key="opt.value ?? opt"
        :value="opt.value ?? opt"
      >
        {{ opt.label ?? opt }}
      </option>
    </select>
    <div v-if="error" class="form-error">
      <slot name="error">{{ error }}</slot>
    </div>
  </div>
</template>

<script>
export default {
  name: "BaseSelectField",
  props: {
    modelValue: [String,Number],
    id:         { type: String,    required: true },
    label:      { type: String,    required: true },
    options:    { type: Array,     default: () => [] },
    placeholder:String,
    required:   { type: Boolean,   default: false },
    disabled:   { type: Boolean,   default: false },
    error:      { type: [String,Boolean], default: false },
  }
};
</script>

<style scoped>
.form-field { margin-bottom: 1rem; }
.form-label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 400;
}
.form-input {
  width: 99%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font: inherit;
  font-weight: 400 !important;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-input option {
  font-weight: 400;
}

.input-error {
  border-color: #c00 !important;
}
.required {
  color: red;
  margin-left: 0.25rem;
  font-weight: 400;
}
.form-error {
  color: #c00;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  font-weight: 400;
}
</style>
