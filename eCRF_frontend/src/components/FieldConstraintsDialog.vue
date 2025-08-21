<template>
  <div class="constraints-edit-modal">
    <div class="head">
      <h3>Field Settings & Constraints</h3>
      <span class="type-chip">{{ currentTypeLabel }}</span>
    </div>

    <!-- COMMON -->
    <section class="group">
      <div class="row">
        <label class="chk">
          <input type="checkbox" v-model="local.required" />
          Required
        </label>
        <label class="chk">
          <input type="checkbox" v-model="local.readonly" />
          Readonly
        </label>
      </div>

      <!-- Placeholder (not for checkbox) -->
      <div class="row" v-if="!isCheckbox">
        <label>Placeholder</label>
        <input type="text" v-model="local.placeholder" placeholder="Shown when empty" />
      </div>

      <div class="row">
        <label>Help text</label>
        <input type="text" v-model="local.helpText" placeholder="Shown below the control" />
      </div>
      <div class="row" v-if="isTime">
          <label>Hour format</label>
          <select v-model="local.hourCycle">
            <option value="24">24-hour</option>
            <option value="12">12-hour (AM/PM)</option>
          </select>
        </div>

      <!-- Default value (type-aware) -->
      <div class="row" v-if="!isDate">
        <label>Default value</label>

        <!-- Choice types: pick from options to avoid typos -->
        <select v-if="isChoice && !local.allowMultiple"
                v-model="local.defaultValue">
          <option value="">(none)</option>
          <option v-for="(opt, i) in localOptions" :key="i" :value="opt">{{ opt }}</option>
        </select>

        <!-- Multi radio: default can be multiple (array), we let user set via tags-like input -->
        <div v-else-if="isRadio && local.allowMultiple" class="chips">
          <div class="chip-input-row">
            <input
              type="text"
              v-model="chipInput"
              placeholder="Type option and press Enter"
              @keydown.enter.prevent="addChip"
              list="radio-options"
            />
            <datalist id="radio-options">
              <option v-for="(opt, i) in localOptions" :key="i" :value="opt" />
            </datalist>
          </div>
          <div class="chip-group">
            <span v-for="(val, i) in (Array.isArray(local.defaultValue) ? local.defaultValue : [])"
                  :key="i"
                  class="chip">
              {{ val }}
              <button class="chip-x" @click.prevent="removeChip(i)">×</button>
            </span>
          </div>
          <small class="note">Press Enter to add; duplicates are ignored.</small>
        </div>

        <input
          v-else-if="isTextLike"
          type="text"
          v-model="local.defaultValue"
          placeholder="Default value"
        />

        <input
          v-else-if="isNumber"
          type="number"
          v-model.number="local.defaultValue"
          placeholder="Default number"
        />

        <!-- ADD this -->
        <FieldTime
          v-else-if="isTime"
          v-model="local.defaultValue"
          :hourCycle="local.hourCycle || '24'"
          :readonly="false"
          :disabled="false"
        />


        <label class="chk" v-else-if="isCheckbox">
          <input type="checkbox" v-model="local.defaultValue" />
          Checked by default
        </label>

        <input
          v-else
          type="text"
          v-model="local.defaultValue"
          placeholder="Default value"
        />
      </div>
    </section>

    <!-- TEXT / TEXTAREA -->
    <section class="group" v-if="isTextLike">
      <div class="row two">
        <div>
          <label>Min length</label>
          <input type="number" v-model.number="local.minLength" min="0" />
        </div>
        <div>
          <label>Max length</label>
          <input type="number" v-model.number="local.maxLength" min="0" />
        </div>
      </div>
      <div class="row">
        <label>Regex pattern</label>
        <input type="text" v-model="local.pattern" placeholder="e.g. ^[A-Za-z]+$" />
      </div>
      <div class="row">
        <label>Transform</label>
        <select v-model="local.transform">
          <option value="none">None</option>
          <option value="uppercase">Uppercase</option>
          <option value="lowercase">Lowercase</option>
          <option value="capitalize">Capitalize</option>
        </select>
      </div>
    </section>

    <!-- NUMBER -->
    <section class="group" v-if="isNumber">
      <div class="row two">
        <div>
          <label>Min value</label>
          <input type="number" v-model.number="local.min" />
        </div>
        <div>
          <label>Max value</label>
          <input type="number" v-model.number="local.max" />
        </div>
      </div>

      <div class="row">
        <label>Step</label>
        <input type="number" v-model.number="local.step" placeholder="Leave empty if not applicable" />
      </div>

      <div class="row">
        <label class="chk">
          <input type="checkbox" v-model="local.integerOnly" />
          Integer only
        </label>
      </div>

      <div class="row two">
        <div>
          <label>Min digits (integer part)</label>
          <input type="number" v-model.number="local.minDigits" min="0" />
        </div>
        <div>
          <label>Max digits (integer part)</label>
          <input type="number" v-model.number="local.maxDigits" min="0" />
        </div>
      </div>
      <div class="row note">
        <span>
          Digit limits apply to the integer part. In preview we enforce these when <b>Integer only</b> is checked.
          For values that need leading zeros (e.g., phone numbers), consider using a <b>Text</b> field with a pattern.
        </span>
      </div>
    </section>


    <!-- TIME -->
    <section class="group" v-if="isTime">
      <div class="row two">
        <div>
          <label>Min time</label>
          <FieldTime
           v-model="local.minTime"
           :hourCycle="local.hourCycle || '24'"
           :readonly="false"
           :disabled="false"
           :placeholder="(local.hourCycle==='12' ? 'hh:mm AM/PM' : 'HH:mm')"
         />
        </div>
        <div>
          <label>Max time</label>
          <FieldTime
           v-model="local.maxTime"
           :hourCycle="local.hourCycle || '24'"
           :readonly="false"
           :disabled="false"
           :placeholder="(local.hourCycle==='12' ? 'hh:mm AM/PM' : 'HH:mm')"
         />
        </div>
      </div>
    </section>

    <!-- DATE (format + min/max/default using DateFormatPicker) -->
    <section class="group" v-if="isDate">
      <div class="row">
        <label>Date format</label>
        <select v-model="local.dateFormat">
          <option v-for="fmt in DATE_FORMATS" :key="fmt" :value="fmt">{{ fmt }}</option>
        </select>
      </div>

      <div class="row two">
        <div>
          <label>Min date</label>
          <DateFormatPicker
            v-model="local.minDate"
            :format="local.dateFormat"
            :placeholder="local.dateFormat"
          />
        </div>
        <div>
          <label>Max date</label>
          <DateFormatPicker
            v-model="local.maxDate"
            :format="local.dateFormat"
            :placeholder="local.dateFormat"
          />
        </div>
      </div>

      <div class="row">
        <label>Default date</label>
        <DateFormatPicker
          v-model="local.defaultValue"
          :format="local.dateFormat"
          :placeholder="local.dateFormat"
          :min-date="local.minDate || null"
          :max-date="local.maxDate || null"
        />
      </div>
    </section>

    <!-- RADIO / SELECT OPTIONS -->
    <section class="group" v-if="isChoice">
      <div class="row">
        <!-- NOTE: allowMultiple is for RADIO (multi-check behavior); SELECT is single only -->
        <label class="chk" v-if="isRadio">
          <input type="checkbox" v-model="local.allowMultiple" />
          Allow multiple selections
        </label>
      </div>

      <div class="row two">
        <div>
          <label>Number of options</label>
          <input type="number" min="1" v-model.number="optionsCount" @input="syncOptionsCount" />
        </div>
        <div>
          <label>Quick add</label>
          <div class="quick">
            <button type="button" class="btn-option" @click="addOption()">+ Add</button>
            <button type="button" class="btn-option" @click="removeLastOption()" :disabled="localOptions.length<=1">− Remove</button>
          </div>
        </div>
      </div>

      <div class="options-scroll">
        <div class="opt-row" v-for="(opt, idx) in localOptions" :key="idx">
          <span class="opt-index">{{ idx + 1 }}.</span>
          <input type="text" v-model="localOptions[idx]" placeholder="Option label" />
          <button class="icon-btn" title="Delete" @click.prevent="deleteOption(idx)" :disabled="localOptions.length<=1">
            ✕
          </button>
        </div>
      </div>
      <div class="row note" v-if="isSelect">
        <span>Dropdowns are single-select in this builder.</span>
      </div>
    </section>

    <!-- CHECKBOX -->
    <section class="group" v-if="isCheckbox">
      <div class="row note">
        <span>Checkbox has no placeholder. Use help text for guidance.</span>
      </div>
    </section>

    <div class="modal-actions">
      <button class="btn-primary" @click="save">Save</button>
      <button class="btn-option" @click="$emit('closeConstraintsDialog')">Cancel</button>
    </div>
  </div>
</template>

<script>
/* eslint-disable */
import { normalizeConstraints, coerceDefaultForType } from "@/utils/constraints";
import DateFormatPicker from "@/components/DateFormatPicker.vue";
import FieldTime from "@/components/fields/FieldTime.vue";

const DATE_FORMATS = [
  "dd.MM.yyyy",
  "MM-dd-yyyy",
  "dd-MM-yyyy",
  "yyyy-MM-dd",
  "MM/yyyy",
  "MM-yyyy",
  "yyyy/MM",
  "yyyy-MM",
  "yyyy"
];

export default {
  name: "FieldConstraintsDialog",
  components: { DateFormatPicker,  FieldTime  },
  props: {
    currentFieldType: { type: String, default: "text" },
    constraintsForm:  { type: Object, default: () => ({}) }
  },
  data() {
    const base = this.constraintsForm || {};
    const type = (this.currentFieldType || "text").toLowerCase();
    const initialOptions =
      (Array.isArray(base.options) ? base.options : []).filter(Boolean).map(String);

    // For radio multi-select, defaultValue should be an array; for others keep scalar
    const defaultValue =
      base.defaultValue !== undefined
        ? base.defaultValue
        : (type === "checkbox" ? false : type === "radio" && base.allowMultiple ? [] : "");

    return {
      DATE_FORMATS,
      local: {
        // common
        required: !!base.required,
        readonly: !!base.readonly,
        helpText: base.helpText || "",
        placeholder: base.placeholder || "",
        defaultValue,

        // text-like
        minLength: isFinite(base.minLength) ? Number(base.minLength) : undefined,
        maxLength: isFinite(base.maxLength) ? Number(base.maxLength) : undefined,
        pattern: base.pattern || "",
        transform: base.transform || "none",

        // number
        min: isFinite(base.min) ? Number(base.min) : undefined,
        max: isFinite(base.max) ? Number(base.max) : undefined,
        step: isFinite(base.step) ? Number(base.step) : undefined,
        integerOnly: !!base.integerOnly,
        maxLengthDigits: isFinite(base.maxLengthDigits) ? Number(base.maxLengthDigits) : undefined,

        // time
        minTime: base.minTime || "",
        maxTime: base.maxTime || "",
        hourCycle: base.hourCycle || "24",

        // date
        minDate: base.minDate || "",
        maxDate: base.maxDate || "",
        dateFormat: base.dateFormat || "dd.MM.yyyy",

        // radio-specific (multi)
        allowMultiple: !!base.allowMultiple
      },

      // choice options (radio/select)
      localOptions: initialOptions.length ? initialOptions : ["Option 1"],
      optionsCount: Math.max(1, initialOptions.length || 1),

      chipInput: ""
    };
  },
  computed: {
    type() { return (this.currentFieldType || "text").toLowerCase(); },
    isTextLike() { return this.type === "text" || this.type === "textarea"; },
    isNumber()   { return this.type === "number"; },
    isTime()     { return this.type === "time"; },
    isDate()     { return this.type === "date"; },
    isCheckbox() { return this.type === "checkbox"; },
    isRadio()    { return this.type === "radio"; },
    isSelect()   { return this.type === "select"; },
    isChoice()   { return this.isRadio || this.isSelect; },
    currentTypeLabel() {
      return this.type.charAt(0).toUpperCase() + this.type.slice(1);
    }
  },
  watch: {
    constraintsForm: {
      deep: true,
      handler(nv) {
        const base = nv || {};
        this.local = {
          ...this.local,
          required: !!base.required,
          readonly: !!base.readonly,
          helpText: base.helpText || "",
          placeholder: base.placeholder || "",
          defaultValue:
            base.defaultValue !== undefined ? base.defaultValue : this.local.defaultValue,

          minLength: isFinite(base.minLength) ? Number(base.minLength) : undefined,
          maxLength: isFinite(base.maxLength) ? Number(base.maxLength) : undefined,
          pattern: base.pattern || "",
          transform: base.transform || "none",

          min: isFinite(base.min) ? Number(base.min) : undefined,
          max: isFinite(base.max) ? Number(base.max) : undefined,
          step: isFinite(base.step) ? Number(base.step) : undefined,
          integerOnly: !!base.integerOnly,
          maxLengthDigits: isFinite(base.maxLengthDigits) ? Number(base.maxLengthDigits) : undefined,

          minTime: base.minTime || "",
          maxTime: base.maxTime || "",
          hourCycle: base.hourCycle || this.local.hourCycle,

          minDate: base.minDate || "",
          maxDate: base.maxDate || "",
          dateFormat: base.dateFormat || this.local.dateFormat,

          allowMultiple: !!base.allowMultiple
        };

        if (Array.isArray(base.options)) {
          const cleaned = base.options.filter(Boolean).map(String);
          this.localOptions = cleaned.length ? cleaned : ["Option 1"];
          this.optionsCount = this.localOptions.length;
        }
      }
    },
    currentFieldType(val) {
      const t = (val || "").toLowerCase();
      if (t === "checkbox") {
        this.local.defaultValue = !!this.local.defaultValue;
        this.local.placeholder = "";
      }
    },
    // when toggling radio allowMultiple, coerce defaultValue shape
    "local.allowMultiple"(nv) {
      if (!this.isRadio) return;
      if (nv) {
        // become array
        this.local.defaultValue = Array.isArray(this.local.defaultValue)
          ? this.local.defaultValue.filter((v) => this.localOptions.includes(v))
          : (this.local.defaultValue && this.localOptions.includes(this.local.defaultValue)
              ? [this.local.defaultValue]
              : []);
      } else {
        // become scalar
        if (Array.isArray(this.local.defaultValue)) {
          this.local.defaultValue = this.local.defaultValue[0] || "";
        }
      }
    },
    // keep defaultValue coherent with options if choice
    localOptions: {
      deep: true,
      handler() {
        if (!this.isChoice) return;
        if (this.isRadio && this.local.allowMultiple) {
          // prune removed values
          if (Array.isArray(this.local.defaultValue)) {
            this.local.defaultValue = this.local.defaultValue.filter((v) =>
              this.localOptions.includes(v)
            );
          }
        } else {
          if (!this.localOptions.includes(this.local.defaultValue)) {
            this.local.defaultValue = "";
          }
        }
        this.optionsCount = this.localOptions.length;
      }
    }
  },
  methods: {
    // chips helpers for multi-radio default
    addChip() {
      const v = (this.chipInput || "").trim();
      if (!v) return;
      if (!this.localOptions.includes(v)) return; // must be from options
      if (!Array.isArray(this.local.defaultValue)) this.local.defaultValue = [];
      if (!this.local.defaultValue.includes(v)) this.local.defaultValue.push(v);
      this.chipInput = "";
    },
    removeChip(i) {
      if (!Array.isArray(this.local.defaultValue)) return;
      this.local.defaultValue.splice(i, 1);
    },

    // options list helpers
    syncOptionsCount() {
      const count = Math.max(1, Number(this.optionsCount || 1));
      if (count > this.localOptions.length) {
        const add = count - this.localOptions.length;
        for (let i = 0; i < add; i++) {
          this.localOptions.push(`Option ${this.localOptions.length + 1}`);
        }
      } else if (count < this.localOptions.length) {
        this.localOptions.splice(count);
      }
      this.optionsCount = this.localOptions.length;
    },
    addOption() {
      this.localOptions.push(`Option ${this.localOptions.length + 1}`);
      this.optionsCount = this.localOptions.length;
    },
    removeLastOption() {
      if (this.localOptions.length > 1) {
        const removed = this.localOptions.pop();
        // fix defaultValue membership
        if (Array.isArray(this.local.defaultValue)) {
          this.local.defaultValue = this.local.defaultValue.filter((v) => v !== removed);
        } else if (this.local.defaultValue === removed) {
          this.local.defaultValue = "";
        }
        this.optionsCount = this.localOptions.length;
      }
    },
    deleteOption(idx) {
      if (this.localOptions.length <= 1) return;
      const removed = this.localOptions.splice(idx, 1)[0];
      if (Array.isArray(this.local.defaultValue)) {
        this.local.defaultValue = this.local.defaultValue.filter((v) => v !== removed);
      } else if (this.local.defaultValue === removed) {
        this.local.defaultValue = "";
      }
      this.optionsCount = this.localOptions.length;
    },

    save() {
      // 1) normalize base constraints
      const cleaned = normalizeConstraints(this.type, { ...this.local });

      // 2) attach options for choice types (trim + dedupe empties)
      if (this.isChoice) {
        const opts = this.localOptions
          .map((o) => String(o || "").trim())
          .filter((o) => !!o);

        const finalOpts = opts.length ? Array.from(new Set(opts)) : ["Option 1"];

        // keep defaultValue valid
        if (this.isRadio && this.local.allowMultiple) {
          const arr = Array.isArray(cleaned.defaultValue) ? cleaned.defaultValue : [];
          cleaned.defaultValue = arr.filter((v) => finalOpts.includes(v));
        } else {
          if (!finalOpts.includes(cleaned.defaultValue)) cleaned.defaultValue = "";
        }

        cleaned.options = finalOpts;

        // IMPORTANT: dropdown is single-select => no allowMultiple on select
        if (this.isSelect) delete cleaned.allowMultiple;
      }

      // 3) final coerce of defaultValue just in case
      cleaned.defaultValue = coerceDefaultForType(
        this.isRadio && this.local.allowMultiple ? "radio" : this.type,
        cleaned.defaultValue
      );
      cleaned.hourCycle = this.local.hourCycle || "24";
      this.$emit("updateConstraints", cleaned);
    }
  },

};
</script>

<style scoped>
.constraints-edit-modal{width:480px;background:#fff;padding:16px 16px 12px;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.18);max-height:80vh;overflow-y:auto;box-sizing:border-box}
.head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.type-chip{background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;padding:2px 8px;border-radius:999px;font-size:12px}
.group{border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin-top:10px}
.row{display:flex;flex-direction:column;gap:6px;margin-bottom:10px}
.row.two{display:grid;gap:10px;grid-template-columns:1fr 1fr}
label{font-size:12px;color:#374151}
input[type="text"],input[type="number"],input[type="time"],select{width:100%;padding:8px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;box-sizing:border-box}
.chk{display:inline-flex;align-items:center;gap:8px}
.note{color:#6b7280;font-size:12px}
.options-scroll{max-height:220px;overflow:auto;border:1px dashed #e5e7eb;border-radius:8px;padding:8px}
.opt-row{display:grid;grid-template-columns:24px 1fr 32px;gap:8px;align-items:center;margin-bottom:8px}
.opt-index{text-align:right;color:#6b7280;font-size:12px}
.icon-btn{border:1px solid #e5e7eb;border-radius:6px;background:#f9fafb;cursor:pointer;padding:4px 0}
.quick{display:flex;gap:6px}
.chips{display:flex;flex-direction:column;gap:6px}
.chip-input-row input{width:100%}
.chip-group{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:#eef2ff;color:#111827;border:1px solid #c7d2fe;border-radius:999px;padding:2px 8px;font-size:12px}
.chip-x{margin-left:6px;background:transparent;border:none;cursor:pointer}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
.btn-primary{background:#2563eb;color:#fff;border:none;padding:8px 14px;border-radius:6px;cursor:pointer}
.btn-option{background:#e5e7eb;color:#111827;border:none;padding:8px 14px;border-radius:6px;cursor:pointer}
</style>
