<template>
  <div class="fs">
    <!-- SINGLE VALUE -->
    <div v-if="!isRange" class="fs-row">
      <input
        class="fs-input"
        type="range"
        :min="min"
        :max="max"
        :step="step"
        :value="singleValueSafe"
        :disabled="isReadonly"
        :aria-readonly="isReadonly ? 'true' : 'false'"
        @input="onSingleInput($event)"
        @change="onSingleChange($event)"
      />
      <span v-if="showValue" class="fs-value" :aria-live="'polite'">
        {{ format(singleValueSafe) }}
      </span>
    </div>

    <!-- RANGE VALUE -->
    <div v-else class="fs-row fs-range">
      <!-- Track with fill -->
      <div class="fs-track">
        <div
          class="fs-fill"
          :style="fillStyle"
          aria-hidden="true"
        ></div>
        <input
          class="fs-input fs-lower"
          type="range"
          :min="min"
          :max="max"
          :step="step"
          :value="lower"
          :disabled="isReadonly"
          @input="onLowerInput($event)"
          @change="onRangeCommit"
        />
        <input
          class="fs-input fs-upper"
          type="range"
          :min="min"
          :max="max"
          :step="step"
          :value="upper"
          :disabled="isReadonly"
          @input="onUpperInput($event)"
          @change="onRangeCommit"
        />
      </div>

      <span v-if="showValue" class="fs-value" :aria-live="'polite'">
        {{ format(lower) }} — {{ format(upper) }}
      </span>
    </div>

    <!-- Helper / placeholder hint -->
    <small v-if="placeholder" class="fs-help">{{ placeholder }}</small>
  </div>
</template>

<script>
export default {
  name: "FieldSlider",
  inheritAttrs: false,
  props: {
    modelValue: { type: [Number, String, Array], default: "" },
    // constraints (mirrors number field + slider flags)
    min: { type: [Number, String], default: 0 },
    max: { type: [Number, String], default: 100 },
    step: { type: [Number, String], default: 1 },
    readonly: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    percent: { type: Boolean, default: false },   // display as %
    isRange: { type: Boolean, default: false },   // dual-thumb
    showValue: { type: Boolean, default: true },  // live value bubble
    defaultValue: { type: [Number, Array, String], default: "" },
    placeholder: { type: String, default: "" },   // optional help text
  },
  emits: ["update:modelValue", "change"],
  computed: {
    isReadonly() {
      const attrReadonly =
        this.$attrs.readonly === "" ||
        this.$attrs.readonly === true ||
        this.$attrs.readonly === "true";
      return this.readonly || this.disabled || attrReadonly;
    },
    nmin() { return this.toNum(this.min, 0); },
    nmax() { return this.toNum(this.max, 100); },
    nstep(){
      const s = this.toNum(this.step, 1);
      return s > 0 ? s : 1;
    },
    // SINGLE
    singleValueSafe() {
      const v = Array.isArray(this.modelValue) ? this.modelValue[0] : this.modelValue;
      const n = this.coerceNumberOrEmpty(v);
      if (n === "") return this.clamp(this.defaultScalar());
      return this.clamp(n);
    },
    // RANGE
    lower() { return this.rangeSafe()[0]; },
    upper() { return this.rangeSafe()[1]; },
    fillStyle() {
      const a = ((this.lower - this.nmin) / (this.nmax - this.nmin)) * 100;
      const b = ((this.upper - this.nmin) / (this.nmax - this.nmin)) * 100;
      return { left: `${a}%`, width: `${Math.max(b - a, 0)}%` };
    }
  },
  methods: {
    toNum(v, d=0){ const n = Number(v); return Number.isFinite(n) ? n : d; },
    clamp(n){
      const x = this.toNum(n, this.nmin);
      return Math.min(this.nmax, Math.max(this.nmin, x));
    },
    coerceNumberOrEmpty(v){
      if (v === "" || v == null) return "";
      const n = Number(v);
      return Number.isFinite(n) ? n : "";
    },
    defaultScalar(){
      const dv = this.coerceNumberOrEmpty(this.defaultValue);
      return dv === "" ? this.nmin : this.clamp(dv);
    },
    defaultRange(){
      let a = this.nmin, b = this.nmax;
      if (Array.isArray(this.defaultValue)) {
        const d0 = this.coerceNumberOrEmpty(this.defaultValue[0]);
        const d1 = this.coerceNumberOrEmpty(this.defaultValue[1]);
        if (d0 !== "") a = this.clamp(d0);
        if (d1 !== "") b = this.clamp(d1);
      }
      if (a > b) [a,b] = [b,a];
      return [a,b];
    },
    rangeSafe(){
      if (!this.isRange) return [this.singleValueSafe, this.singleValueSafe];
      if (!Array.isArray(this.modelValue)) return this.defaultRange();
      const a = this.coerceNumberOrEmpty(this.modelValue[0]);
      const b = this.coerceNumberOrEmpty(this.modelValue[1]);
      let lo = a === "" ? this.nmin : this.clamp(a);
      let hi = b === "" ? this.nmax : this.clamp(b);
      if (lo > hi) [lo, hi] = [hi, lo];
      return [lo, hi];
    },
    snapToStep(n) {
      const offset = n - this.nmin;
      const steps = Math.round(offset / this.nstep);
      return this.clamp(this.nmin + steps * this.nstep);
    },
    onSingleInput(e){
      if (this.isReadonly) return;
      const n = this.snapToStep(this.toNum(e.target.value, this.nmin));
      this.$emit("update:modelValue", n);
    },
    onSingleChange(e){
      if (this.isReadonly) return;
      const n = this.snapToStep(this.toNum(e.target.value, this.nmin));
      this.$emit("update:modelValue", n);
      this.$emit("change", n);
    },
    onLowerInput(e){
      if (this.isReadonly) return;
      let lo = this.snapToStep(this.toNum(e.target.value, this.nmin));
      let hi = this.upper;
      if (lo > hi) lo = hi;
      this.$emit("update:modelValue", [lo, hi]);
    },
    onUpperInput(e){
      if (this.isReadonly) return;
      let hi = this.snapToStep(this.toNum(e.target.value, this.nmax));
      let lo = this.lower;
      if (hi < lo) hi = lo;
      this.$emit("update:modelValue", [lo, hi]);
    },
    onRangeCommit(){
      if (this.isReadonly) return;
      this.$emit("change", [this.lower, this.upper]);
    },
    format(n){
      return this.percent ? `${n}%` : String(n);
    }
  }
};
</script>

<style scoped>
.fs { display: flex; flex-direction: column; gap: 6px; }
.fs-row { display: flex; align-items: center; gap: 10px; }
.fs-value {
  min-width: 64px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 12px;
  color: #111827;
  text-align: center;
}
.fs-help { color: #6b7280; font-size: 12px; }

.fs-input {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  background: transparent;
  cursor: pointer;
}
.fs-input:disabled { cursor: not-allowed; opacity: .6; }

/* Track */
.fs-input::-webkit-slider-runnable-track { height: 6px; background: #e5e7eb; border-radius: 999px; }
.fs-input::-moz-range-track { height: 6px; background: #e5e7eb; border-radius: 999px; }

/* Thumb */
.fs-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #111827;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #111827;
  margin-top: -6px;
}
.fs-input::-moz-range-thumb {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #111827;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #111827;
}

/* RANGE mode */
.fs-range { flex-direction: row; align-items: center; }
.fs-track {
  position: relative;
  width: 100%;
  height: 6px;
  background: #e5e7eb;
  border-radius: 999px;
}
.fs-fill {
  position: absolute; top: 0; height: 6px;
  background: #111827;
  border-radius: 999px;
}
.fs-track .fs-input {
  position: absolute; left: 0; right: 0; top: -6px;
}
.fs-track .fs-upper { pointer-events: auto; }
</style>
