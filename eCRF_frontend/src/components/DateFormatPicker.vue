<template>
  <div class="dfp-wrapper" :class="{ readonly: isReadonly }">
    <VueDatePicker
      v-model="innerValue"
      :model-type="'format'"
      :format="resolvedFormat"
      :placeholder="placeholder || resolvedFormat"
      :min-date="dateMinResolved"
      :max-date="dateMaxResolved"
      :teleport="true"
      :enable-time-picker="mode === 'time'"
      :time-picker="mode === 'time'"
      :month-picker="mode === 'date' && isMonthPicker"
      :year-picker="mode === 'date' && isYearPicker"
      :auto-apply="true"
      :clearable="!isReadonly"
      :disabled="isReadonly"
      :config="pickerConfig"
      input-class="dfp-input"
      class="dfp-picker"
      v-bind="$attrs"
    />
    <!-- overlay to guarantee no edits when readonly -->
    <div v-if="isReadonly" class="dfp-overlay" aria-hidden="true"></div>
  </div>
</template>

<script>
import VueDatePicker from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";

export default {
  name: "DateFormatPicker",
  components: { VueDatePicker },
  inheritAttrs: false,

  props: {
    modelValue: { type: [String, Number, Date, null], default: "" },
    format: { type: String, default: "dd.MM.yyyy" },
    placeholder: { type: String, default: "" },
    minDate: { type: [String, Date], default: null },
    maxDate: { type: [String, Date], default: null },
    mode: { type: String, default: "date" }, // supported runtime use here is date
    readonly: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    mobileBreakpoint: { type: Number, default: 0 },
  },

  emits: ["update:modelValue"],

  computed: {
    pickerConfig() {
      return {
        mobileBreakpoint: Number.isFinite(this.mobileBreakpoint)
          ? this.mobileBreakpoint
          : 0,
        allowPreventDefault: true,
        closeOnScroll: false,
        closeOnAutoApply: true,
        tabOutClosesMenu: true,
      };
    },

    isYearPicker() {
      return this.mode === "date" && this.format.toLowerCase() === "yyyy";
    },

    isMonthPicker() {
      if (this.mode !== "date") return false;
      const f = this.format.toLowerCase();
      return (
        f === "mm-yyyy" ||
        f === "yyyy-mm" ||
        f === "mm/yyyy" ||
        f === "yyyy/mm"
      );
    },

    resolvedFormat() {
      return this.format
        .replace(/yyyy/gi, "yyyy")
        .replace(/dd/gi, "dd")
        .replace(/mm/gi, "MM")
        .replace(/hh/gi, "HH");
    },

    isReadonly() {
      const isTrue = (v) => v === true || v === "true" || v === "";
      return !!(
        this.readonly ||
        this.disabled ||
        isTrue(this.$attrs.readonly) ||
        isTrue(this.$attrs.disabled) ||
        isTrue(this.$attrs["aria-readonly"]) ||
        isTrue(this.$attrs["data-readonly"])
      );
    },

    innerValue: {
      get() {
        return this.normalizeIncomingModelValue(this.modelValue);
      },
      set(v) {
        if (this.isReadonly) return;
        this.$emit("update:modelValue", this.normalizeOutputValue(v));
      },
    },

    dateMinResolved() {
      const d = this.resolveDate(this.minDate, "min");
      return d || undefined;
    },

    dateMaxResolved() {
      const d = this.resolveDate(this.maxDate, "max");
      return d || undefined;
    },
  },

  methods: {
    normalizeIncomingModelValue(v) {
      if (v == null || v === "") return "";
      if (typeof v === "number") return String(v);
      return v;
    },

    normalizeOutputValue(v) {
      if (v == null || v === "") return "";

      if (typeof v === "string") return v;

      if (this.isYearPicker && typeof v === "number") {
        return String(v);
      }

      if (v instanceof Date && !Number.isNaN(v.getTime())) {
        return this.formatDateByFormat(v, this.format);
      }

      if (this.isYearPicker && typeof v === "object" && v !== null) {
        if (typeof v.year === "number" || typeof v.year === "string") {
          return String(v.year);
        }
      }

      if (this.isMonthPicker && typeof v === "object" && v !== null) {
        const year = Number(v.year);
        const month = Number(v.month);
        if (Number.isFinite(year) && Number.isFinite(month)) {
          const d = new Date(year, month - 1, 1);
          return this.formatDateByFormat(d, this.format);
        }
      }

      if (typeof v === "number" || typeof v === "boolean") {
        return String(v);
      }

      return "";
    },

    formatDateByFormat(dateObj, fmt) {
      const y = dateObj.getFullYear();
      const m = String(dateObj.getMonth() + 1).padStart(2, "0");
      const d = String(dateObj.getDate()).padStart(2, "0");

      const f = String(fmt || "").toLowerCase();

      if (f === "yyyy") return String(y);
      if (f === "mm-yyyy") return `${m}-${y}`;
      if (f === "yyyy-mm") return `${y}-${m}`;
      if (f === "mm/yyyy") return `${m}/${y}`;
      if (f === "yyyy/mm") return `${y}/${m}`;
      if (f === "dd.mm.yyyy") return `${d}.${m}.${y}`;
      if (f === "dd-mm-yyyy") return `${d}-${m}-${y}`;
      if (f === "mm-dd-yyyy") return `${m}-${d}-${y}`;
      if (f === "yyyy-mm-dd") return `${y}-${m}-${d}`;

      return `${d}.${m}.${y}`;
    },

    resolveDate(input, kind) {
      if (!input) return null;

      if (input instanceof Date) {
        return this.normalizeBoundary(input, kind);
      }

      const s = String(input).trim();
      const d =
        this.parseByFormat(s, this.format) ||
        this.parseByFormat(s, this.resolvedFormat);

      return d ? this.normalizeBoundary(d, kind) : null;
    },

    normalizeBoundary(dateObj, kind) {
      const y = dateObj.getFullYear();
      const m = dateObj.getMonth();

      if (this.isYearPicker) {
        return new Date(y, kind === "min" ? 0 : 11, kind === "min" ? 1 : 31);
      }

      if (this.isMonthPicker) {
        if (kind === "min") return new Date(y, m, 1);
        return new Date(y, m + 1, 0);
      }

      return dateObj;
    },

    parseByFormat(str, fmt) {
      if (!str || !fmt) return null;

      const f = String(fmt).toLowerCase();
      const s = String(str).trim();

      if (f === "yyyy") {
        const m = /^(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[1], 0, 1);
      }

      if (f === "mm-yyyy" || f === "mm/yyyy") {
        const m = /^(\d{2})[-/](\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[2], +m[1] - 1, 1);
      }

      if (f === "yyyy-mm" || f === "yyyy/mm") {
        const m = /^(\d{4})[-/](\d{2})$/.exec(s);
        if (!m) return null;
        return new Date(+m[1], +m[2] - 1, 1);
      }

      if (f === "dd.mm.yyyy") {
        const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[3], +m[2] - 1, +m[1]);
      }

      if (f === "dd-mm-yyyy") {
        const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[3], +m[2] - 1, +m[1]);
      }

      if (f === "mm-dd-yyyy") {
        const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s);
        if (!m) return null;
        return new Date(+m[3], +m[1] - 1, +m[2]);
      }

      if (f === "yyyy-mm-dd") {
        const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
        if (!m) return null;
        return new Date(+m[1], +m[2] - 1, +m[3]);
      }

      return null;
    },
  },
};
</script>

<style scoped>
.dfp-wrapper {
  position: relative;
  width: 100%;
  min-width: 0;
  min-height: 44px;
  display: block !important;
  visibility: visible !important;
  overflow: visible !important;
}

.dfp-picker {
  width: 100%;
  min-width: 0;
  display: block !important;
  overflow: visible !important;
}

/* Let the datepicker root fill available width */
:deep(.dp__main) {
  width: 100% !important;
  min-width: 0 !important;
  min-height: 44px !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  overflow: visible !important;
  font-family: inherit;
}

/* Input wrapper */
:deep(.dp__input_wrap) {
  position: relative;
  width: 100% !important;
  min-width: 0 !important;
  min-height: 44px !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  overflow: visible !important;
}

/* Main input */
:deep(.dp__input),
:deep(.dfp-input) {
  display: block !important;
  width: 100% !important;
  min-width: 0 !important;
  min-height: 44px !important;
  height: 44px !important;
  box-sizing: border-box !important;
  padding-top: 8px !important;
  padding-right: 12px !important;
  padding-bottom: 8px !important;
  padding-left: 42px !important;
  border: 1px solid #d1d5db !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  color: #1f2937 !important;
  font-family: inherit !important;
  font-size: 14px !important;
  line-height: 1.4 !important;
  outline: none !important;
  box-shadow: none !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
  visibility: visible !important;
  opacity: 1 !important;
}

:deep(.dp__input::placeholder),
:deep(.dfp-input::placeholder) {
  color: #9ca3af !important;
  opacity: 1 !important;
}

:deep(.dp__input:hover),
:deep(.dfp-input:hover) {
  border-color: #cbd5e1 !important;
}

:deep(.dp__input:focus),
:deep(.dfp-input:focus) {
  border-color: #93c5fd !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12) !important;
}

:deep(.dp__input_icon) {
  left: 12px !important;
  color: #6b7280 !important;
  width: 18px !important;
  height: 18px !important;
}

:deep(.dp__clear_icon) {
  right: 12px !important;
  color: #6b7280 !important;
}

:deep(.dp__input_icon_pad) {
  padding-inline-start: 42px !important;
}

:deep(.dp__main[data-dp-mobile="true"]) {
  display: block !important;
  width: 100% !important;
  min-width: 0 !important;
  min-height: 44px !important;
  visibility: visible !important;
  opacity: 1 !important;
}

:deep(.dp__main[data-dp-mobile="true"] .dp__input_wrap) {
  display: block !important;
  width: 100% !important;
  min-width: 0 !important;
  min-height: 44px !important;
  visibility: visible !important;
  opacity: 1 !important;
}

:deep(.dp__main[data-dp-mobile="true"] .dp__input),
:deep(.dp__main[data-dp-mobile="true"] .dfp-input) {
  display: block !important;
  width: 100% !important;
  min-width: 0 !important;
  min-height: 44px !important;
  height: 44px !important;
  padding-left: 42px !important;
  visibility: visible !important;
  opacity: 1 !important;
}

:deep(.dp__menu) {
  font-family: inherit;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
  z-index: 99999 !important;
}

:deep(.dp__calendar) {
  padding: 6px;
}

:deep(.dp__month_year_row) {
  padding: 8px 10px;
}

:deep(.dp__calendar_header_item) {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
}

:deep(.dp__cell_inner) {
  border-radius: 8px;
}

:deep(.dp__today) {
  border-color: #93c5fd;
}

:deep(.dp__active_date),
:deep(.dp__range_start),
:deep(.dp__range_end) {
  background: #2563eb !important;
  color: #ffffff !important;
}

:deep(.dp__disabled),
:deep(.dp__input:disabled),
:deep(.dfp-input:disabled) {
  background: #f9fafb !important;
  color: #9ca3af !important;
  cursor: not-allowed !important;
}

.dfp-overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: transparent;
  pointer-events: all;
  cursor: not-allowed;
}

.dfp-wrapper.readonly :deep(.dp__input),
.dfp-wrapper.readonly :deep(.dfp-input) {
  background: #f9fafb !important;
  color: #6b7280 !important;
  opacity: 1 !important;
  cursor: not-allowed !important;
}

:deep(.dp__menu_wrapper),
:deep(.dp__outer_menu_wrap) {
  z-index: 99999 !important;
  overflow: visible !important;
}
</style>