<template>
  <div class="frg">
    <!-- MULTI (checkboxes) -->
    <template v-if="allowMultiple">
      <label
        v-for="(opt, i) in stringOptions"
        :key="'m-' + i"
        class="radio-label"
      >
        <input
          type="checkbox"
          :name="name + '[]'"
          :value="opt"
          :checked="proxyArray.includes(opt)"
          :disabled="isReadonly"
          :aria-readonly="isReadonly ? 'true' : 'false'"
          @mousedown.prevent="isReadonly && $event.preventDefault()"
          @change="onToggleMulti(opt, $event.target.checked)"
        />
        {{ opt }}
      </label>
    </template>

    <!-- SINGLE (radios) -->
    <template v-else>
      <label
        v-for="(opt, i) in stringOptions"
        :key="'s-' + i"
        class="radio-label"
      >
        <input
          type="radio"
          :name="name"
          :value="opt"
          :checked="proxySingle === opt"
          :disabled="isReadonly"
          :aria-readonly="isReadonly ? 'true' : 'false'"
          @mousedown.prevent="isReadonly && $event.preventDefault()"
          @change="onSelectSingle(opt)"
        />
        {{ opt }}
      </label>
    </template>
  </div>
</template>

<script>
export default {
  name: "FieldRadioGroup",
  inheritAttrs: false,
  props: {
    modelValue: { type: [String, Number, Array], default: "" },
    options: { type: Array, default: () => [] },
    name: { type: String, default: "radio" },

    // constraints
    readonly: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    defaultValue: { type: [String, Number, Array], default: "" },
    allowMultiple: { type: Boolean, default: false },
  },
  emits: ["update:modelValue", "change"],
  computed: {
    isReadonly() {
      const attrReadonly =
        this.$attrs.readonly === "" ||
        this.$attrs.readonly === true ||
        this.$attrs.readonly === "true";
      return this.readonly || attrReadonly || this.disabled;
    },
    stringOptions() {
      return this.options.map((o) => (o == null ? "" : String(o)));
    },
    // single
    proxySingle() {
      return this.modelValue == null ? "" : String(this.modelValue);
    },
    // multi
    proxyArray() {
      const v = this.modelValue;
      if (Array.isArray(v)) return v.map((x) => (x == null ? "" : String(x)));
      // if parent gave scalar while we are in multi mode, coerce to []
      return [];
    },
  },
  mounted() {
    this.initFromDefaults();
  },
  watch: {
    options() {
      // keep current value(s) valid when options change
      const opts = this.stringOptions;

      if (this.allowMultiple) {
        const cur = this.proxyArray.filter((v) => opts.includes(v));
        this.$emit("update:modelValue", cur);
        this.$emit("change", cur);
      } else {
        const cur = this.proxySingle;
        if (!opts.includes(cur)) {
          const dv = this.pickSingleDefault();
          const next = dv && opts.includes(dv) ? dv : "";
          this.$emit("update:modelValue", next);
          this.$emit("change", next);
        }
      }
    },
    allowMultiple() {
      // when the mode flips, coerce the model shape and apply defaults if needed
      this.initFromDefaults(true);
    },
  },
  methods: {
    // ----- defaults / init -----
    pickSingleDefault() {
      // defaultValue may be scalar or array; for single, pick first valid
      const opts = this.stringOptions;
      const dv = this.defaultValue;

      if (Array.isArray(dv)) {
        const first = dv.map((x) => String(x)).find((x) => opts.includes(x));
        return first || "";
      }
      const s = dv == null ? "" : String(dv);
      return opts.includes(s) ? s : "";
    },
    pickMultiDefault() {
      // intersect defaults array with options
      const opts = this.stringOptions;
      const dv = this.defaultValue;

      if (Array.isArray(dv)) {
        return dv.map((x) => String(x)).filter((x) => opts.includes(x));
      }
      const s = dv == null ? "" : String(dv);
      return opts.includes(s) ? [s] : [];
    },
    initFromDefaults(force = false) {
      const hasValue = (v) =>
        (Array.isArray(v) ? v.length > 0 : v !== null && String(v).trim() !== "");

      if (this.allowMultiple) {
        const cur = this.proxyArray;
        if (!hasValue(cur) || force) {
          const next = this.pickMultiDefault();
          this.$emit("update:modelValue", next);
          this.$emit("change", next);
        }
      } else {
        const cur = this.proxySingle;
        if (!hasValue(cur) || force) {
          const next = this.pickSingleDefault();
          this.$emit("update:modelValue", next);
          this.$emit("change", next);
        }
      }
    },

    // ----- interactions -----
    onSelectSingle(val) {
      if (this.isReadonly) return;
      this.$emit("update:modelValue", val);
      this.$emit("change", val);
    },
    onToggleMulti(opt, checked) {
      if (this.isReadonly) return;
      const set = new Set(this.proxyArray);
      if (checked) set.add(opt);
      else set.delete(opt);
      const next = Array.from(set);
      this.$emit("update:modelValue", next);
      this.$emit("change", next); //
    },
  },
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
  line-height: 1.2;
}

/* Make radios & checkboxes look identical (circular dot) */
.radio-label input[type="radio"],
.radio-label input[type="checkbox"] {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;

  width: 18px;
  height: 18px;
  margin: 0;

  border: 2px solid #9ca3af;          /* gray-400 */
  border-radius: 50%;                  /* always circle */
  background: #ffffff;
  position: relative;
  cursor: pointer;
  display: inline-block;

  transition: border-color .2s ease, background-color .2s ease, box-shadow .2s ease;
}

.radio-label input[type="radio"]:hover,
.radio-label input[type="checkbox"]:hover {
  border-color: #6b7280;               /* gray-500 */
}

.radio-label input[type="radio"]:focus,
.radio-label input[type="checkbox"]:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.25); /* gray focus ring */
}

/* Checked state: dark circle with white inner dot */
.radio-label input[type="radio"]:checked,
.radio-label input[type="checkbox"]:checked {
  background-color: #111827;           /* gray-900 */
  border-color: #111827;
}
.radio-label input[type="radio"]:checked::after,
.radio-label input[type="checkbox"]:checked::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 8px;
  height: 8px;
  margin-top: -4px;
  margin-left: -4px;
  background: #ffffff;
  border-radius: 50%;
}

/* Disabled / readonly visual */
.radio-label input[type="radio"]:disabled,
.radio-label input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
