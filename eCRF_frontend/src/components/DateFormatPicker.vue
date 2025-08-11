<template>
  <div class="dfp-wrapper">
    <VueDatePicker
      v-model="innerValue"
      :model-type="'format'"
      :format="resolvedFormat"
      :placeholder="placeholder || resolvedFormat"
      :min-date="mode === 'date' ? (minDate || undefined) : undefined"
      :max-date="mode === 'date' ? (maxDate || undefined) : undefined"
      :teleport="false"
      :enable-time-picker="mode === 'time'"
      :time-picker="mode === 'time'"
      :month-picker="mode === 'date' && isMonthPicker"
      :year-picker="mode === 'date' && isYearPicker"
      :auto-apply="true"
      :clearable="true"
      input-class="dfp-input"
      class="dfp-picker"
      @update:model-value="emitChange"
    />
  </div>
</template>

<script>
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css';

/**
 * A small wrapper around @vuepic/vue-datepicker:
 * - mode="date" (default) supports formats like 'MM-dd-yyyy', 'dd-MM-yyyy', 'yyyy', 'MM-yyyy', etc.
 * - mode="time" uses time-only picker with formats like 'HH:mm', 'HH:mm:ss'
 * - v-model is the *formatted string* (model-type="format") so it plugs into your field.value
 */
export default {
  name: 'DateFormatPicker',
  components: { VueDatePicker },
  props: {
    modelValue: { type: [String, Date, null], default: '' },
    format: { type: String, default: 'dd.MM.yyyy' },
    placeholder: { type: String, default: '' },
    minDate: { type: [String, Date], default: null },
    maxDate: { type: [String, Date], default: null },
    mode: { type: String, default: 'date' } // 'date' | 'time'
  },
  emits: ['update:modelValue'],
  computed: {
    isYearPicker() {
      return this.mode === 'date' && this.format.toLowerCase() === 'yyyy';
    },
    isMonthPicker() {
      if (this.mode !== 'date') return false;
      const f = this.format.toLowerCase();
      return f === 'mm-yyyy' || f === 'yyyy-mm' || f === 'mm.yyyy' || f === 'yyyy.mm';
    },
    resolvedFormat() {
      // Normalize common lowercase tokens to date-fns tokens used by vue-datepicker
      return this.format
        .replace(/yyyy/gi, 'yyyy')
        .replace(/dd/gi, 'dd')
        .replace(/mm/gi, 'MM') // month
        .replace(/hh/gi, 'HH'); // 24h time (if time mode)
    },
    innerValue: {
      get() {
        return this.modelValue || '';
      },
      set(v) {
        this.$emit('update:modelValue', v || '');
      }
    }
  },
  methods: {
    emitChange(v) {
      this.$emit('update:modelValue', v || '');
    }
  }
};
</script>

<style scoped>
.dfp-wrapper {
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
</style>
