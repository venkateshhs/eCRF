<template>
  <div class="field-slider" :class="{ readonly }">
    <div class="slider-header">
      <span v-if="displayValue !== null" class="slider-value">
        {{ displayValueText }}
      </span>
    </div>

    <div class="slider-track-wrap" ref="wrap" @click="onTrackClick">
      <input
        ref="range"
        type="range"
        class="slider-range"
        :min="useMin"
        :max="useMax"
        :step="useStep"
        :value="rangeValue"
        :disabled="readonly"
        @input="onInput"
        @change="onChange"
        @mousedown="dragging = true"
        @mouseup="dragging = false"
        @touchstart="dragging = true"
        @touchend="dragging = false"
      />

      <!-- Step labels (marks) -->
      <div class="marks" v-if="hasMarks">
        <div
          v-for="(m, i) in normalizedMarks"
          :key="i"
          class="mark"
          :style="{ left: markPercent(m.value) + '%' }"
        >
          <span class="mark-tick"></span>
          <span class="mark-label">{{ m.label }}</span>
        </div>
      </div>
    </div>

    <div class="slider-footer">
      <span class="min-label">{{ useMin }}</span>
      <span class="max-label">{{ useMax }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: "FieldSlider",
  props: {
    modelValue: { type: [Number, String, null], default: null }, // v-model
    min: { type: Number, default: 1 },
    max: { type: Number, default: 5 },
    step: { type: Number, default: 1 },
    readonly: { type: Boolean, default: false },
    percent: { type: Boolean, default: false },
    marks: { type: Array, default: () => [] } // [{ value: number, label: string }]
  },
  emits: ["update:modelValue"],
  data() {
    return {
      internalValue: this.toNumberOrNull(this.modelValue),
      dragging: false
    };
  },
  computed: {
    useMin() {
      return this.percent ? 1 : this.min;
    },
    useMax() {
      return this.percent ? 100 : this.max;
    },
    useStep() {
      return this.percent ? 1 : (this.step > 0 ? this.step : 1);
    },
    hasMarks() {
      return this.normalizedMarks.length > 0;
    },
    normalizedMarks() {
      const min = this.useMin, max = this.useMax, step = this.useStep;
      const seen = new Set();
      const out = [];
      (this.marks || []).forEach(m => {
        let v = Number(m?.value);
        const label = (m?.label ?? "").toString();
        if (!Number.isFinite(v) || !label) return;
        // snap to step & clamp
        v = Math.round((v - min) / step) * step + min;
        v = Math.max(min, Math.min(max, v));
        const key = `${v}`;
        if (!seen.has(key)) {
          seen.add(key);
          out.push({ value: v, label });
        }
      });
      out.sort((a, b) => a.value - b.value);
      return out;
    },
    displayValue() {
      return this.internalValue !== null && Number.isFinite(+this.internalValue)
        ? Number(this.internalValue)
        : null;
    },
    displayValueText() {
      if (this.displayValue === null) return "";
      return this.percent ? `${this.displayValue}%` : this.displayValue;
    },
    rangeValue() {
      // the native input needs a number even if we haven't picked yet
      return this.internalValue === null ? this.useMin : this.internalValue;
    }
  },
  watch: {
    modelValue(nv) {
      const n = this.toNumberOrNull(nv);
      if (n !== this.internalValue) this.internalValue = n;
    },
    min() { this.snapWithinBounds(); },
    max() { this.snapWithinBounds(); },
    step() { this.snapWithinBounds(); },
    percent() { this.snapWithinBounds(); },
    marks() {
      console.log("[FieldSlider] marks updated:", this.marks);
    }
  },
  mounted() {
    console.log("[FieldSlider] mounted props:", {
      percent: this.percent, min: this.min, max: this.max, step: this.step, marks: this.marks
    });
  },
  methods: {
    toNumberOrNull(v) {
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    },
    clampSnap(n) {
      const min = this.useMin, max = this.useMax, step = this.useStep;
      if (!Number.isFinite(n)) return null;
      let v = Math.max(min, Math.min(max, n));
      v = Math.round((v - min) / step) * step + min;
      v = Math.max(min, Math.min(max, v));
      return v;
    },
    snapWithinBounds() {
      // if we haven't chosen a value yet, keep it null; otherwise snap/clamp
      if (this.internalValue === null) return;
      const snapped = this.clampSnap(this.internalValue);
      if (snapped !== this.internalValue) {
        this.internalValue = snapped;
        this.$emit("update:modelValue", snapped);
      }
    },
    onInput(e) {
      const raw = Number(e && e.target ? e.target.value : this.internalValue);
      const v = this.clampSnap(raw);
      this.internalValue = v;
      this.$emit("update:modelValue", v); // continuous update while sliding
    },
    onChange(e) {
      const raw = Number(e && e.target ? e.target.value : this.internalValue);
      const v = this.clampSnap(raw);
      this.internalValue = v;
      this.$emit("update:modelValue", v);
    },
    onTrackClick(evt) {
      if (this.readonly) return;
      const wrap = this.$refs.wrap;
      const range = this.$refs.range;
      if (!wrap || !range) return;

      const rect = wrap.getBoundingClientRect();
      const x = (evt.clientX ?? (evt.touches && evt.touches[0]?.clientX)) || 0;
      const rel = (x - rect.left) / rect.width;
      const min = this.useMin, max = this.useMax;
      const guess = min + rel * (max - min);
      const v = this.clampSnap(guess);

      this.internalValue = v;
      this.$emit("update:modelValue", v);

      // also sync native input UI
      range.value = v;
    },
    markPercent(value) {
      const min = this.useMin, max = this.useMax;
      if (max === min) return 0;
      return ((value - min) / (max - min)) * 100;
    }
  }
};
</script>

<style scoped>
.field-slider {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slider-header {
  display: flex;
  justify-content: flex-end;
  min-height: 18px;
}

.slider-value {
  font-size: 12px;
  color: #111827;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  padding: 2px 6px;
  border-radius: 999px;
}

.slider-track-wrap {
  position: relative;
  padding: 12px 0 22px; /* bottom space for labels */
}

.slider-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: #e5e7eb;
  border-radius: 999px;
  outline: none;
  cursor: pointer;
}

/* thumb */
.slider-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #2563eb;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
  cursor: pointer;
}
.slider-range::-moz-range-thumb {
  width: 16px; height: 16px; border-radius: 50%;
  background: #2563eb; border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,.2);
  cursor: pointer;
}

/* track (Firefox) */
.slider-range::-moz-range-track {
  height: 4px;
  background: #e5e7eb;
  border: none;
  border-radius: 999px;
}

/* marks */
.marks {
  position: absolute;
  left: 0; right: 0;
  bottom: 0; /* sit closer to the track to avoid "too low" issue */
  height: 18px;
}

.mark {
  position: absolute;
  transform: translateX(-50%);
  text-align: center;
  white-space: nowrap;
}

.mark-tick {
  display: block;
  width: 2px;
  height: 8px;
  margin: 0 auto 2px;
  background: #9ca3af;
  border-radius: 2px;
}

.mark-label {
  font-size: 11px;
  color: #374151;
  line-height: 1;
}

.slider-footer {
  display: flex;
  justify-content: space-between;
  color: #6b7280;
  font-size: 12px;
}

.readonly .slider-range {
  cursor: not-allowed;
  opacity: .7;
}
</style>
