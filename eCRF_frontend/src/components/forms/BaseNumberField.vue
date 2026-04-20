<template>
  <div class="form-field">
    <label :for="id" class="form-label">
      {{ label }}<span v-if="required" class="required">*</span>
    </label>
    <input
      :id="id"
      type="number"
      :class="['form-input', { 'input-error': error }]"
      :value="inputValue"
      @input="onInput"
      @blur="onBlur"
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
    id: { type: String, required: true },
    label: { type: String, required: true },
    placeholder: { type: String, default: "" },
    min: { type: Number, default: null },
    max: { type: Number, default: null },
    step: { type: [Number, String], default: 1 },
    required: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    error: { type: [String, Boolean], default: false },
  },

  data() {
    return {
      inputValue: this.modelValue ?? "",
    };
  },

  watch: {
    modelValue: {
      immediate: true,
      handler(val) {
        const normalized = val ?? "";
        if (String(normalized) !== String(this.inputValue)) {
          this.inputValue = normalized;
        }
      }
    }
  },

  methods: {
    onInput(e) {
      const raw = e.target.value;
      this.inputValue = raw;

      // allow empty during typing
      if (raw === "") {
        this.$emit("update:modelValue", null);
        return;
      }

      const num = Number(raw);
      this.$emit("update:modelValue", Number.isNaN(num) ? null : num);
    },

    onBlur() {
      // if left empty, enforce min if present, otherwise leave empty
      if (this.inputValue === "" || this.inputValue == null) {
        if (this.min != null) {
          this.inputValue = this.min;
          this.$emit("update:modelValue", this.min);
        } else {
          this.$emit("update:modelValue", null);
        }
        return;
      }

      let num = Number(this.inputValue);

      if (Number.isNaN(num)) {
        if (this.min != null) {
          num = this.min;
        } else {
          this.inputValue = "";
          this.$emit("update:modelValue", null);
          return;
        }
      }

      if (this.min != null && num < this.min) num = this.min;
      if (this.max != null && num > this.max) num = this.max;

      this.inputValue = num;
      this.$emit("update:modelValue", num);
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
  width: 99%;
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
