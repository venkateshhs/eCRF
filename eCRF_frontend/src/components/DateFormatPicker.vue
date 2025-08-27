<template>
  <div class="dfp-wrapper" :class="{ readonly: isReadonly }">
    <VueDatePicker
      v-model="innerValue"
      :model-type="'format'"
      :format="resolvedFormat"
      :placeholder="placeholder || resolvedFormat"
      :min-date="dateMinResolved"
      :max-date="dateMaxResolved"
      :teleport="false"
      :enable-time-picker="mode === 'time'"
      :time-picker="mode === 'time'"
      :month-picker="mode === 'date' && isMonthPicker"
      :year-picker="mode === 'date' && isYearPicker"
      :auto-apply="true"
      :clearable="!isReadonly"
      :disabled="isReadonly"
      input-class="dfp-input"
      class="dfp-picker"
      @update:model-value="emitChange"
      v-bind="$attrs"
    />
    <!-- overlay to guarantee no edits when readonly -->
    <div v-if="isReadonly" class="dfp-overlay" aria-hidden="true"></div>
  </div>
</template>

<script>
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css';

export default {
  name: 'DateFormatPicker',
  components: { VueDatePicker },
  inheritAttrs: false,
  props: {
    modelValue: { type: [String, Date, null], default: '' },
    format: { type: String, default: 'dd.MM.yyyy' },
    placeholder: { type: String, default: '' },
    minDate: { type: [String, Date], default: null },
    maxDate: { type: [String, Date], default: null },
    mode: { type: String, default: 'date' }, // 'date' | 'time'
    readonly: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:modelValue'],
  computed: {
    isYearPicker() {
      return this.mode === 'date' && this.format.toLowerCase() === 'yyyy';
    },
    isMonthPicker() {
      if (this.mode !== 'date') return false;
      const f = this.format.toLowerCase();
      // support common month-year patterns
      return (
        f === 'mm-yyyy' || f === 'yyyy-mm' ||
        f === 'mm/yyyy' || f === 'yyyy/mm' ||
        f === 'mm.yyyy' || f === 'yyyy.mm'
      );
    },
    resolvedFormat() {
      // normalize to datepicker tokens
      return this.format
        .replace(/yyyy/gi, 'yyyy')
        .replace(/dd/gi, 'dd')
        .replace(/mm/gi, 'MM')  // month
        .replace(/hh/gi, 'HH'); // 24h
    },
    // block edits when explicit readonly/disabled attrs are true
    isReadonly() {
      const isTrue = (v) => v === true || v === 'true' || v === '';
      return !!(
        this.readonly ||
        this.disabled ||
        isTrue(this.$attrs.readonly) ||
        isTrue(this.$attrs.disabled) ||
        isTrue(this.$attrs['aria-readonly']) ||
        isTrue(this.$attrs['data-readonly'])
      );
    },
    innerValue: {
      get() {
        return this.modelValue || '';
      },
      set(v) {
        if (!this.isReadonly) this.$emit('update:modelValue', v || '');
      }
    },
    // Proper min/max handling for month/year formats
    dateMinResolved() {
      const d = this.resolveDate(this.minDate, 'min');
      return d || undefined;
    },
    dateMaxResolved() {
      const d = this.resolveDate(this.maxDate, 'max');
      return d || undefined;
    },
  },
  methods: {
    emitChange(v) {
      if (!this.isReadonly) this.$emit('update:modelValue', v || '');
    },
    // turn string/date into Date object respecting current format
    resolveDate(input, kind /* 'min' | 'max' */) {
      if (!input) return null;
      if (input instanceof Date) return this.normalizeBoundary(input, kind);

      const s = String(input).trim();
      const d =
        this.parseByFormat(s, this.format) ||
        this.parseByFormat(s, this.resolvedFormat);
      return d ? this.normalizeBoundary(d, kind) : null;
    },
    // For month/year pickers, bound to first/last day of month/year
    normalizeBoundary(dateObj, kind) {
      const y = dateObj.getFullYear();
      const m = dateObj.getMonth();
      if (this.isYearPicker) {
        return new Date(kind === 'min' ? y : y, kind === 'min' ? 0 : 11, kind === 'min' ? 1 : 31);
      }
      if (this.isMonthPicker) {
        if (kind === 'min') return new Date(y, m, 1);
        return new Date(y, m + 1, 0); // last day of month
      }
      return dateObj; // day-level date as-is
    },
    // small parser for common patterns supported in constraints
    parseByFormat(str, fmt) {
      if (!str || !fmt) return null;
      const f = fmt.toLowerCase();
      const s = String(str).trim();

      // yyyy
      if (f === 'yyyy') {
        const m = /^(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[1], 0, 1);
      }

      // MM-yyyy / MM/yyyy / MM.yyyy
      if (f === 'mm-yyyy' || f === 'mm/yyyy' || f === 'mm.yyyy') {
        const m = /^(\d{2})[-/.](\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[2], +m[1] - 1, 1);
      }

      // yyyy-MM / yyyy/MM / yyyy.MM
      if (f === 'yyyy-mm' || f === 'yyyy/mm' || f === 'yyyy.mm') {
        const m = /^(\d{4})[-/.](\d{2})$/.exec(s);
        if (!m) return null;
        return new Date(+m[1], +m[2] - 1, 1);
      }

      // dd.MM.yyyy
      if (f === 'dd.mm.yyyy') {
        const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[3], +m[2] - 1, +m[1]);
      }

      // dd-MM-yyyy
      if (f === 'dd-mm-yyyy') {
        const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[3], +m[2] - 1, +m[1]);
      }

      // MM-dd-yyyy
      if (f === 'mm-dd-yyyy') {
        const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[3], +m[1] - 1, +m[2]);
      }

      // yyyy-MM-dd
      if (f === 'yyyy-mm-dd') {
        const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
        if (!m) return null;
        return new Date(+m[1], +m[2] - 1, +m[3]);
      }

      return null;
    },
  }
};
</script>

<style scoped>
.dfp-wrapper {
  position: relative;
  width: 100%;
}
.dfp-picker {
  width: 100%;
}
.dfp-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 14px;
  color: #1f2937;
}
/* overlay to fully block interaction when readonly */
.dfp-overlay {
  position: absolute;
  inset: 0;
  background: transparent;
  pointer-events: all;
  z-index: 3;
  cursor: not-allowed;
}
.dfp-wrapper.readonly .dfp-input {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
