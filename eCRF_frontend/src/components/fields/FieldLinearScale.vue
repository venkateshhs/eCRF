<template>
  <div class="fls-wrap" :class="{ readonly }">
    <div class="fls-row">
      <span class="edge">{{ leftLabel }}</span>

      <div class="fls-scale" role="radiogroup" :aria-readonly="readonly ? 'true' : 'false'">
        <button
          v-for="n in points"
          :key="n"
          class="fls-point"
          :class="{ active: modelValue === n }"
          type="button"
          :tabindex="readonly ? -1 : 0"
          :aria-checked="modelValue === n ? 'true' : 'false'"
          role="radio"
          @click="onPick(n)"
          @keydown="onKey($event, n)"
        >
          {{ n }}
        </button>
      </div>

      <span class="edge">{{ rightLabel }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: "FieldLinearScale",
  emits: ["update:modelValue"],
  props: {
    modelValue: { type: [Number, null], default: null }, // no default selection
    min: { type: Number, default: 1 },
    max: { type: Number, default: 5 },
    leftLabel: { type: String, default: "" },
    rightLabel: { type: String, default: "" },
    readonly: { type: Boolean, default: false }
  },
  computed: {
    safeMin() {
      const m = Number.isFinite(this.min) ? this.min : 1;
      return Math.max(1, Math.round(m));
    },
    safeMax() {
      const M = Number.isFinite(this.max) ? this.max : 5;
      // cap to prevent clutter (2..10)
      const capped = Math.min(10, Math.round(M));
      return Math.max(this.safeMin + 1, capped);
    },
    points() {
      const arr = [];
      for (let n = this.safeMin; n <= this.safeMax; n++) arr.push(n);
      return arr;
    }
  },
  methods: {
    onPick(n) {
      if (this.readonly) return;
      this.$emit("update:modelValue", n);
    },
    onKey(e, n) {
      if (this.readonly) return;
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        this.onPick(n);
        return;
      }
      let delta = 0;
      if (e.key === "ArrowLeft" || e.key === "ArrowDown") delta = -1;
      else if (e.key === "ArrowRight" || e.key === "ArrowUp") delta = 1;
      if (delta !== 0) {
        e.preventDefault();
        const cur = Number.isFinite(this.modelValue) ? this.modelValue : this.safeMin;
        const next = Math.min(this.safeMax, Math.max(this.safeMin, cur + delta));
        this.$emit("update:modelValue", next);
      }
    }
  }
};
</script>

<style scoped>
.fls-wrap { width: 100%; }
.fls-row { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; }
.edge { font-size: 12px; color: #6b7280; text-align: center; }

.fls-scale {
  display: grid;
  grid-auto-flow: column;
  gap: 8px;
  align-items: center;
}
.fls-point {
  min-width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  cursor: pointer;
  font-size: 14px;
  transition: box-shadow .12s ease, border-color .12s ease, background .12s ease;
}
.fls-point:hover { border-color: #9ca3af; }
.fls-point.active {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}
.fls-wrap.readonly .fls-point { cursor: default; opacity: .75; }
.fls-point:focus-visible { box-shadow: 0 0 0 4px rgba(37,99,235,.25); outline: none; }
</style>
