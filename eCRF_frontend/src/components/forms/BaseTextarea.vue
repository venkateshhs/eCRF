<template>
  <div class="form-field">
    <label :for="id" class="form-label">
      {{ label }}<span v-if="required" class="required">*</span>
    </label>
    <textarea
      :id="id"
      :class="['form-textarea', { 'input-error': error }]"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      :placeholder="placeholder"
      :rows="rows"
      :maxlength="maxlength"
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
  name: "BaseTextarea",
  props: {
    modelValue: { type: String, default: "" },
    id:         { type: String,   required: true },
    label:      { type: String,   required: true },
    placeholder:{ type: String,   default: "" },
    rows:       { type: Number,   default: 4 },
    maxlength:  { type: [Number,String], default: null },
    required:   { type: Boolean,  default: false },
    disabled:   { type: Boolean,  default: false },
    error:      { type: [String,Boolean], default: false },
  }
};
</script>

<style scoped>
.form-textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font: inherit;
  box-sizing: border-box;
  resize: vertical;
  transition: border-color 0.2s;
}
.input-error {
  border-color: #c00 !important;
}
</style>
