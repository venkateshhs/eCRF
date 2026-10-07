<template>
  <div class="fsel">
    <select
      class="fsel-input"
      :id="id"
      v-model="proxy"
      :multiple="multiple"
      :disabled="isReadonly"
      :aria-readonly="isReadonly ? 'true' : 'false'"
      v-bind="$attrs"
    >
      <option v-if="!multiple && placeholder" disabled value="">{{ placeholder }}</option>
      <option v-for="(opt, i) in stringOptions" :key="i" :value="opt">{{ opt }}</option>
      <option v-if="allowOther" :value="otherToken">Other</option>
    </select>
    <input
      v-if="allowOther && otherActive"
      ref="otherInput"
      class="fsel-input other-input"
      type="text"
      :value="otherText"
      :disabled="isReadonly"
      placeholder="Please specify"
      aria-label="Other answer"
      @input="updateOther($event.target.value)"
      @blur="finishOther"
    />

    <button
      v-if="multiple && allowClear && !isReadonly && hasAnySelection"
      class="fsel-clear"
      type="button"
      @click="clearSelection"
      title="Clear selection"
    >
      ×
    </button>
  </div>
</template>

<script>
export default {
  name: "FieldSelect",
  inheritAttrs: false,
  props: {
    modelValue: { type: [String, Array], default: "" },
    options: { type: Array, default: () => [] },
    multiple: { type: Boolean, default: false },
    readonly: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    placeholder: { type: String, default: "Select…" },
    id: { type: String, default: null },
    defaultValue: { type: [String, Array], default: "" },
    allowClear: { type: Boolean, default: true },
    allowOther: { type: Boolean, default: false }
  },
  emits: ["update:modelValue"],
  data() {
    return { otherActive: false, otherText: "" };
  },
  computed: {
    otherToken() {
      let token = "__other__";
      while (this.stringOptions.includes(token)) token += "_";
      return token;
    },
    isReadonly() {
      const attrReadonly =
        this.$attrs.readonly === "" || this.$attrs.readonly === true || this.$attrs.readonly === "true";
      return this.readonly || attrReadonly || this.disabled;
    },
    stringOptions() {
      return this.options.map(o => (o == null ? "" : String(o)))
        .filter(o => !this.allowOther || o.trim().toLowerCase() !== 'other');
    },
    optionSet() {
      return new Set(this.stringOptions);
    },
    hasAnySelection() {
      return this.multiple ? this.asArray(this.modelValue).length > 0 : !!this.modelValue;
    },
    proxy: {
      get() {
        if (this.allowOther && this.otherActive) {
          return this.multiple
            ? [...this.asArray(this.modelValue).filter(v => this.optionSet.has(v)), this.otherToken]
            : this.otherToken;
        }
        if (this.multiple) {
          return this.asArray(this.modelValue).map(String).filter(v => this.optionSet.has(v));
        }
        const s = this.modelValue == null ? "" : String(this.modelValue);
        return this.optionSet.has(s) ? s : "";
      },
      set(v) {
        if (this.isReadonly) return;
        const selected = this.multiple ? this.asArray(v) : [v];
        this.otherActive = this.allowOther && selected.includes(this.otherToken);
        if (this.otherActive) {
          this.updateOther(this.otherText);
          this.$nextTick(() => this.$refs.otherInput?.focus());
          return;
        }
        this.otherText = "";
        if (this.multiple) {
          const arr = this.asArray(v).map(String).filter(x => this.optionSet.has(x));
          this.$emit("update:modelValue", arr);
        } else {
          const s = v == null ? "" : String(v);
          this.$emit("update:modelValue", this.optionSet.has(s) ? s : "");
        }
      }
    }
  },
  mounted() {
    this.syncOther();
    if (this.allowOther && this.otherActive) return;
    const opts = this.stringOptions;
    if (this.multiple) {
      const cur = this.asArray(this.modelValue).map(String).filter(v => opts.includes(v));
      if (cur.length === 0) {
        const dv = this.asArray(this.defaultValue).map(String).filter(v => opts.includes(v));
        if (dv.length) this.$emit("update:modelValue", dv);
      }
    } else {
      const cur = this.modelValue == null ? "" : String(this.modelValue);
      if (!cur || !opts.includes(cur)) {
        const dv = this.defaultValue == null ? "" : String(this.defaultValue);
        if (dv && opts.includes(dv)) this.$emit("update:modelValue", dv);
      }
    }
  },
  watch: {
    allowOther(enabled) {
      if (enabled) { this.syncOther(); return; }
      this.otherActive = false;
      this.otherText = "";
      const next = this.multiple
        ? this.asArray(this.modelValue).filter(v => this.optionSet.has(v))
        : this.optionSet.has(this.modelValue) ? this.modelValue : "";
      this.$emit("update:modelValue", next);
    },
    modelValue: {
      deep: true,
      handler() { this.syncOther(); },
    },
    options() {
      if (this.allowOther) { this.syncOther(); return; }
      const opts = this.stringOptions;
      if (this.multiple) {
        const cur = this.asArray(this.modelValue).map(String).filter(v => opts.includes(v));
        this.$emit("update:modelValue", cur);
      } else {
        const cur = this.modelValue == null ? "" : String(this.modelValue);
        if (!opts.includes(cur)) {
          const dv = this.defaultValue == null ? "" : String(this.defaultValue);
          this.$emit("update:modelValue", dv && opts.includes(dv) ? dv : "");
        }
      }
    }
  },
  methods: {
    syncOther() {
      if (!this.allowOther) return;
      const values = this.asArray(this.modelValue).map(String);
      const custom = values.find(v => v && !this.optionSet.has(v));
      if (custom) {
        this.otherActive = true;
        this.otherText = custom;
      } else if (this.otherText && !values.includes(this.otherText)) {
        this.otherActive = false;
        this.otherText = "";
      }
    },
    updateOther(value) {
      if (this.isReadonly) return;
      this.otherText = value;
      const next = this.multiple
        ? [...this.asArray(this.modelValue).filter(v => this.optionSet.has(v)), ...(value ? [value] : [])]
        : value;
      this.$emit("update:modelValue", next);
    },
    finishOther() {
      if (this.isReadonly) return;
      const value = this.otherText.trim();
      this.updateOther(value);
      if (this.optionSet.has(value)) {
        this.otherActive = false;
        this.otherText = "";
      }
    },
    asArray(v) { return Array.isArray(v) ? v : (v ? [v] : []); },
    clearSelection() {
      this.otherActive = false;
      this.otherText = "";
      this.$emit("update:modelValue", []);
    }
  }
};
</script>

<style scoped>
.fsel {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.fsel-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 14px;
  color: #1f2937;
  font-weight: 400; /* force normal */
  min-height: 44px;
}
.fsel-input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.fsel-clear {
  position: absolute;
  right: 6px;
  top: 6px;
  height: 28px;
  width: 28px;
  border: none;
  background: #f3f4f6;
  border-radius: 6px;
  cursor: pointer;
  line-height: 1;
}
.fsel-clear:hover {
  background: #e5e7eb;
}
</style>
