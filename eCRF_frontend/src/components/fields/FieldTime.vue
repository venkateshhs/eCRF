<template>
  <div class="ftm-wrap" :class="{ readonly: isReadonly }">
    <!-- Display input -->
    <div
      class="ftm-input"
      :tabindex="isReadonly ? -1 : 0"
      @click="toggleOpen"
      @keydown.enter.prevent="toggleOpen"
      @keydown.space.prevent="toggleOpen"
      :aria-readonly="isReadonly ? 'true' : 'false'"
    >
      <i :class="icons.clock" class="ftm-clock-icon" aria-hidden="true"></i>
      <span
        class="ftm-text"
        :class="{ placeholder: !displayValue }"
      >{{ displayValue || placeholderText }}</span>
    </div>

    <!-- Popover (no long lists; stepper controls) -->
    <div v-if="menuOpen" class="ftm-pop" @mousedown.stop>
      <div class="ftm-row">
        <!-- HOURS -->
        <div class="ftm-step">
          <button class="ftm-step-btn" @click="stepHour( +1 )" :disabled="isReadonly"> <i :class="icons.toggleUp"></i></button>
          <input
            class="ftm-step-input"
            type="number"
            :min="is12h ? 1 : 0"
            :max="is12h ? 12 : 23"
            v-model.number="uiHour"
            :disabled="isReadonly"
          />
          <button class="ftm-step-btn" @click="stepHour( -1 )" :disabled="isReadonly"><i :class="icons.toggleDown"></i></button>
        </div>

        <span class="ftm-colon">:</span>

        <!-- MINUTES -->
        <div class="ftm-step">
          <button class="ftm-step-btn" @click="stepMinute( +1 )" :disabled="isReadonly"> <i :class="icons.toggleUp"></i></button>
          <input
            class="ftm-step-input"
            type="number"
            min="0"
            max="59"
            v-model.number="uiMinute"
            :disabled="isReadonly"
          />
          <button class="ftm-step-btn" @click="stepMinute( -1 )" :disabled="isReadonly"><i :class="icons.toggleDown"></i></button>
        </div>

        <!-- AM/PM -->
        <div v-if="is12h" class="ftm-ap-toggle">
          <button
            class="ftm-ap-btn"
            :class="{ active: ap==='AM' }"
            @click="ap='AM'"
            :disabled="isReadonly"
          >AM</button>
          <button
            class="ftm-ap-btn"
            :class="{ active: ap==='PM' }"
            @click="ap='PM'"
            :disabled="isReadonly"
          >PM</button>
        </div>
      </div>

      <div class="ftm-actions">
        <button class="ftm-btn" @click="apply" :disabled="isReadonly">OK</button>
        <button class="ftm-btn ghost" @click="close">Cancel</button>
        <button class="ftm-btn ghost" v-if="!isReadonly" @click="setNow">Now</button>
        <small v-if="boundText" class="ftm-bounds">{{ boundText }}</small>
      </div>
    </div>

    <!-- Readonly shield -->
    <div v-if="isReadonly" class="ftm-overlay" aria-hidden="true"></div>
  </div>
</template>

<script>
import icons from "@/assets/styles/icons";
export default {
  name: "FieldTime",
  inheritAttrs: false,
  props: {
    modelValue:   { type: String, default: "" },       // stored "HH:mm"
    placeholder:  { type: String, default: "" },
    id:           { type: String, default: null },

    // constraints (may come via v-bind="constraints")
    minTime:      { type: String, default: "" },       // "HH:mm" or "hh:mm AM/PM"
    maxTime:      { type: String, default: "" },
    readonly:     { type: Boolean, default: false },
    disabled:     { type: Boolean, default: false },
    required:     { type: Boolean, default: false },
    defaultValue: { type: String,  default: undefined },
    hourCycle:    { type: String,  default: "24" }     // "24" | "12"
  },
  emits: ["update:modelValue"],
  data() {
    return {
      menuOpen: false,
      uiHour: 12,        // 1..12 in 12h mode; 0..23 in 24h mode
      uiMinute: 0,
      ap: "AM",
      icons,
    };
  },
  computed: {
    isReadonly() {
      const a = this.$attrs, isTrue = (v) => v === true || v === "true" || v === "";
      return !!(this.readonly || this.disabled || isTrue(a.readonly) || isTrue(a.disabled) || isTrue(a["aria-readonly"]) || isTrue(a["data-readonly"]));
    },
    isRequired() {
      const a = this.$attrs, isTrue = (v) => v === true || v === "true" || v === "";
      return !!(this.required || isTrue(a.required));
    },
    is12h() {
      const raw = this.hourCycle || this.$attrs.hourCycle || "24";
      return String(raw) === "12";
    },
    displayValue() {
      const d = this.parseToDate(this.modelValue);
      if (!d) return "";
      return this.is12h ? this.to12(d) : this.to24(d);
    },
    placeholderText() { return this.placeholder || (this.is12h ? "hh:mm AM/PM" : "HH:mm"); },
    minDate() { return this.parseToDate(this.minTime); },
    maxDate() { return this.parseToDate(this.maxTime); },
    boundText() {
      const s = [];
      if (this.minDate) s.push(`min ${this.is12h ? this.to12(this.minDate) : this.to24(this.minDate)}`);
      if (this.maxDate) s.push(`max ${this.is12h ? this.to12(this.maxDate) : this.to24(this.maxDate)}`);
      return s.join(" · ");
    }
  },
  watch: {
    hourCycle() { this.syncPanelFromValue(); }
  },
  mounted() {
    if (!this.hasValue(this.modelValue)) {
      const eff = this.effectiveDefault();
      if (eff) this.$emit("update:modelValue", eff);
    } else {
      const norm = this.normalizeHHMM(this.modelValue);
      if (norm !== this.modelValue) this.$emit("update:modelValue", norm);
    }
    this.syncPanelFromValue();
    document.addEventListener("mousedown", this.onDocDown);
  },
  beforeUnmount() { document.removeEventListener("mousedown", this.onDocDown); },
  methods: {
    // open/close
    toggleOpen() { if (!this.isReadonly) { this.menuOpen = !this.menuOpen; if (this.menuOpen) this.syncPanelFromValue(); } },
    close() { this.menuOpen = false; },
    onDocDown(e) { if (!this.$el.contains(e.target)) this.close(); },

    // utils
    pad2(n) { return String(n).padStart(2, "0"); },
    hasValue(v) { return typeof v === "string" && v.trim() !== ""; },
    nowHHMM() {
      const d = new Date();
      return `${this.pad2(d.getHours())}:${this.pad2(d.getMinutes())}`;
    },
    effectiveDefault() {
      const hasProp = Object.prototype.hasOwnProperty.call(this.$props, "defaultValue");
      if (hasProp && this.hasValue(this.defaultValue)) {
        const d = this.parseToDate(this.defaultValue);
        return d ? this.to24(d) : "";
      }
      const hasAttr = Object.prototype.hasOwnProperty.call(this.$attrs, "defaultValue");
      if (hasAttr && this.hasValue(this.$attrs.defaultValue)) {
        const d = this.parseToDate(String(this.$attrs.defaultValue));
        return d ? this.to24(d) : "";
      }
      if (this.isReadonly && this.isRequired) return this.nowHHMM();
      return "";
    },

    // parsing / formatting
    parseToDate(v) {
      const s = String(v || "").trim();
      let m = /^(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec(s);
      if (m) {
        let hh = +m[1], mm = +m[2];
        if (hh < 1 || hh > 12 || mm < 0 || mm > 59) return null;
        const ap = m[3].toUpperCase();
        if (ap === "PM" && hh < 12) hh += 12;
        if (ap === "AM" && hh === 12) hh = 0;
        const d = new Date();
        d.setHours(hh, mm, 0, 0);
        return d;
      }
      m = /^(\d{1,2}):(\d{2})$/.exec(s);
      if (m) {
        let hh = +m[1], mm = +m[2];
        if (hh < 0 || hh > 23 || mm < 0 || mm > 59) return null;
        const d = new Date();
        d.setHours(hh, mm, 0, 0);
        return d;
      }
      return null;
    },
    normalizeHHMM(v) { const d = this.parseToDate(v); return d ? this.to24(d) : ""; },
    to24(d) { return `${this.pad2(d.getHours())}:${this.pad2(d.getMinutes())}`; },
    to12(d) {
      let h = d.getHours(), ap = h >= 12 ? "PM" : "AM";
      h = h % 12; if (h === 0) h = 12;
      return `${this.pad2(h)}:${this.pad2(d.getMinutes())} ${ap}`;
    },

    // panel sync
    syncPanelFromValue() {
      const d = this.parseToDate(this.modelValue) || this.parseToDate(this.effectiveDefault()) || new Date();
      let h = d.getHours();
      this.uiMinute = d.getMinutes();
      if (this.is12h) {
        this.ap = h >= 12 ? "PM" : "AM";
        h = h % 12; if (h === 0) h = 12;
        this.uiHour = h; // 1..12
      } else {
        this.uiHour = h; // 0..23
      }
    },
    currentSelectionToDate() {
      let h = Number(this.uiHour) || 0;
      const m = Number(this.uiMinute) || 0;
      if (this.is12h) {
        if (this.ap === "PM" && h < 12) h += 12;
        if (this.ap === "AM" && h === 12) h = 0;
      }
      const d = new Date();
      d.setHours(Math.min(23, Math.max(0, h)), Math.min(59, Math.max(0, m)), 0, 0);
      return d;
    },
    clampToBounds(d) {
      const min = this.minDate, max = this.maxDate;
      if (min && d < min) return new Date(min);
      if (max && d > max) return new Date(max);
      return d;
    },

    // actions
    apply() {
      if (this.isReadonly) return;
      let d = this.currentSelectionToDate();
      d = this.clampToBounds(d);
      this.$emit("update:modelValue", this.to24(d)); // store HH:mm
      this.close();
    },
    setNow() {
      if (this.isReadonly) return;
      let d = new Date();
      d = this.clampToBounds(d);
      this.$emit("update:modelValue", this.to24(d));
      this.syncPanelFromValue();
    },

    // steppers
    stepHour(delta) {
      if (this.is12h) {
        let h = (Number(this.uiHour) || 12) + delta;
        if (h > 12) h = 1;
        if (h < 1) h = 12;
        this.uiHour = h;
      } else {
        let h = (Number(this.uiHour) || 0) + delta;
        if (h > 23) h = 0;
        if (h < 0) h = 23;
        this.uiHour = h;
      }
    },
    stepMinute(delta) {
      let m = (Number(this.uiMinute) || 0) + delta;
      if (m > 59) m = 0;
      if (m < 0) m = 59;
      this.uiMinute = m;
    }
  }
};
</script>

<style scoped>
/* container */
.ftm-wrap {
  position: relative;
  width: 100%;
  min-width: 0; /* allow children to shrink inside narrow columns */
}

/* faux input (always same UI for 12h/24h) */
.ftm-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: text;
  background: #fff;
  box-sizing: border-box;
}
.ftm-input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(107,114,128,.15);
}
.ftm-clock-icon { font-size: 14px; opacity: .85; }
.ftm-text { flex: 1; user-select: none; }
.ftm-text.placeholder { color: #9ca3af; /* gray-400 */ }
.readonly .ftm-input { opacity: .6; cursor: not-allowed; }

/* popover */
.ftm-pop {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  right: 0;               /* stretch within the column */
  margin-top: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 10px 25px rgba(0,0,0,.12);
  width: 100%;
  max-width: 100%;
  min-width: 0;           /* remove rigid minimum */
  box-sizing: border-box; /* include padding in width */
}

/* row with steppers */
.ftm-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;        /* wrap controls instead of overflowing */
}
.ftm-colon { font-weight: 600; color: #374151; }

/* hour/minute steppers */
.ftm-step {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.ftm-step-btn {
  padding: 4px 6px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
}
.ftm-step-input {
  width: 64px;
  min-width: 60px;
  max-width: 100%;
  text-align: center;
  padding: 6px 8px;
  margin: 4px 0;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

/* AM/PM toggle */
.ftm-ap-toggle {
  display: inline-flex;
  gap: 6px;
  margin-left: auto; /* push nicely when space allows */
}
.ftm-ap-btn {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}
.ftm-ap-btn.active {
  background: #111827;
  color: #fff;
  border-color: #111827;
}

/* actions */
.ftm-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.ftm-btn {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #f9fafb;
  cursor: pointer;
  font-size: 13px;
}
.ftm-btn.ghost { background: #fff; }
.ftm-btn:disabled { cursor: not-allowed; opacity: .5; }
.ftm-bounds { margin-left: auto; color: #6b7280; font-size: 12px; }

/* readonly shield */
.ftm-overlay {
  position: absolute;
  inset: 0;
  background: transparent;
  pointer-events: all;
  z-index: 3;
  cursor: not-allowed;
}
</style>
