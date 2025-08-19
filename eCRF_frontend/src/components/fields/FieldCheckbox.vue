<template>
  <label class="fcx-wrapper" :class="{ readonly: isReadonly }">
    <input
      type="checkbox"
      :id="id"
      v-model="proxy"
      :disabled="isReadonly"
      :aria-readonly="isReadonly ? 'true' : 'false'"
      @click="onMaybeBlock"
      @keydown.exact="onMaybeBlock"
      @wheel="onMaybeBlock"
    />
  </label>
</template>

<script>
export default {
  name: "FieldCheckbox",
  inheritAttrs: true,
  props: {
    modelValue: { type: Boolean, default: false },
    id: { type: String, default: null },

    // Constraints (may come via v-bind="$field.constraints")
    readonly: { type: Boolean, default: false },
    required: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    defaultValue: { type: [Boolean, String, Number, null], default: undefined },
  },
  emits: ["update:modelValue"],
  computed: {
    isReadonly() {
      const attrRO =
        this.$attrs.readonly === "" ||
        this.$attrs.readonly === "true" ||
        this.$attrs.readonly === true;
      const attrDisabled =
        this.$attrs.disabled === "" ||
        this.$attrs.disabled === "true" ||
        this.$attrs.disabled === true;
      return this.readonly || this.disabled || attrRO || attrDisabled;
    },
    isRequired() {
      const attrReq =
        this.$attrs.required === "" ||
        this.$attrs.required === "true" ||
        this.$attrs.required === true;
      return this.required || attrReq;
    },
    effectiveDefault() {
      // 1) explicit defaultValue (prop or attr) wins
      if (Object.prototype.hasOwnProperty.call(this.$props, "defaultValue")) {
        return !!this.defaultValue;
      }
      if (Object.prototype.hasOwnProperty.call(this.$attrs, "defaultValue")) {
        const v = this.$attrs.defaultValue;
        return v === "" ? true : v === true || v === "true";
      }
      // 2) impossible state: readonly + required => true
      if (this.isReadonly && this.isRequired) return true;
      // 3) otherwise false by default
      return false;
    },
    proxy: {
      get() {
        return !!this.modelValue;
      },
      set(v) {
        if (!this.isReadonly) this.$emit("update:modelValue", !!v);
      },
    },
  },
  mounted() {
    this.enforceRules(true);
  },
  watch: {
    // Re-enforce when constraints or value change
    isReadonly() { this.enforceRules(); },
    isRequired() { this.enforceRules(); },
    defaultValue() { this.enforceRules(); },
    modelValue() { this.enforceRules(); },
  },
  methods: {
    onMaybeBlock(e) {
      if (this.isReadonly) {
        e.preventDefault?.();
        e.stopPropagation?.();
        return false;
      }
      // if editable, do nothing (let v-model toggle)
    },
    enforceRules(initial = false) {
      // If value is "unset" (null/undefined/empty string), apply effective default
      const isUnset = this.modelValue === null || this.modelValue === undefined || this.modelValue === "";
      if (isUnset) {
        this.$emit("update:modelValue", this.effectiveDefault);
        return;
      }

      // If readonly + required but not checked, force true
      if (this.isReadonly && this.isRequired && this.modelValue !== true) {
        this.$emit("update:modelValue", true);
        return;
      }

      // If an explicit defaultValue is provided and this is the first mount with falsy value,
      // initialize to that (without overriding a deliberate false later).
      if (initial && Object.prototype.hasOwnProperty.call(this.$props, "defaultValue")) {
        if (this.modelValue !== !!this.defaultValue) {
          this.$emit("update:modelValue", !!this.defaultValue);
        }
      }
    },
  },
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
.fcx-wrapper.readonly input[type="checkbox"] {
  cursor: not-allowed;
  opacity: 0.6;
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
