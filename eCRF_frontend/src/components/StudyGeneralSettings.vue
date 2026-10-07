<template>
  <div class="study-settings-page">
    <header class="settings-topbar">
      <button type="button" class="btn-option settings-back" @click="$emit('back')">Back to forms</button>
      <div class="settings-heading">
        <h2>General study settings</h2>
        <p>Shared conventions for forms, rules, calculations, imports, and exports.</p>
      </div>
      <span class="scope-chip">Study-wide</span>
    </header>

    <div class="settings-content">
      <section class="settings-card">
        <div class="card-heading">
          <div>
            <h3>Regional number format</h3>
            <p>Numbers remain stored in a locale-independent form.</p>
          </div>
        </div>

        <div class="settings-body">
          <label class="setting-field">
            <span>Format preset</span>
            <select v-model="local.numberFormat.preset" @change="applyPreset">
              <option value="international">International (default)</option>
              <option value="german">German (Germany)</option>
            </select>
          </label>

          <div class="format-preview" aria-live="polite">
            <div>
              <small>Decimal</small>
              <strong>{{ examples.exampleDecimal }}</strong>
            </div>
            <div>
              <small>Large number</small>
              <strong>{{ examples.exampleLarge }}</strong>
            </div>
            <div>
              <small>Separators</small>
              <strong>{{ separatorDescription }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section class="settings-card">
        <div class="card-heading">
          <div>
            <h3>Unexpected number formats</h3>
            <p>Choose what happens when a value uses another number convention.</p>
          </div>
        </div>

        <div class="settings-body policy-list">
          <label class="policy-option">
            <input v-model="local.numberFormat.unexpectedInputPolicy" type="radio" value="confirm" @change="emitChange" />
            <span>
              <strong>Ask when the meaning could change</strong>
              <small>Recommended. Show the possible values and require the user to confirm.</small>
            </span>
          </label>
          <label class="policy-option">
            <input v-model="local.numberFormat.unexpectedInputPolicy" type="radio" value="reject" @change="emitChange" />
            <span>
              <strong>Reject the value</strong>
              <small>Show the study’s expected format without converting the entry.</small>
            </span>
          </label>
          <label class="policy-option">
            <input v-model="local.numberFormat.unexpectedInputPolicy" type="radio" value="auto" @change="emitChange" />
            <span>
              <strong>Convert when unambiguous</strong>
              <small>Automatic conversion is allowed only when there is one safe interpretation.</small>
            </span>
          </label>
        </div>
      </section>

      <section class="settings-card">
        <div class="card-heading measurement-heading">
          <div>
            <h3>Measurement defaults</h3>
            <p>Defaults appear only for numeric fields explicitly classified by an author.</p>
          </div>
          <span class="classification-count">
            {{ classifiedFieldCount }} classified · {{ measurementSummary.unclassified.length }} unclassified
          </span>
        </div>

        <div class="settings-body">
          <div v-if="measurementRows.length" class="measurement-table-wrap">
            <table class="measurement-table">
              <thead>
                <tr>
                  <th>Measurement</th>
                  <th>Study default</th>
                  <th>Used by</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in measurementRows" :key="row.concept">
                  <td>{{ row.definition.label }}</td>
                  <td>
                    <select
                      v-model="local.measurementDefaults[row.concept]"
                      :aria-label="`Default unit for ${row.definition.label}`"
                      @change="emitChange"
                    >
                      <option v-for="unit in row.definition.units" :key="unit" :value="unit">{{ unit }}</option>
                    </select>
                  </td>
                  <td>
                    <span class="usage-count">{{ row.fields.length }} field{{ row.fields.length === 1 ? '' : 's' }}</span>
                    <small>{{ fieldNames(row.fields) }}</small>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="measurement-empty">
            <strong>No measurement fields have been classified yet.</strong>
            <p>Open a numeric field’s settings and choose a measurement concept. Field names are never guessed.</p>
          </div>

          <div v-if="measurementSummary.unclassified.length" class="unclassified-note">
            <strong>{{ measurementSummary.unclassified.length }} numeric field{{ measurementSummary.unclassified.length === 1 ? '' : 's' }} use no measurement.</strong>
            <span>{{ fieldNames(measurementSummary.unclassified) }}</span>
          </div>
        </div>
      </section>

      <aside class="safety-note">
        <strong>Safe by design</strong>
        <span>Changing a display format never reinterprets existing values. Unit changes should require an impact review after data collection begins.</span>
      </aside>
    </div>
  </div>
</template>

<script>
import {
  collectStudyMeasurements,
  measurementConcept,
  normalizeStudySettings,
  studyNumberExamples,
} from "@/utils/studySettings";

export default {
  name: "StudyGeneralSettings",
  props: {
    modelValue: { type: Object, default: () => ({}) },
    forms: { type: Array, default: () => [] },
  },
  emits: ["update:modelValue", "back"],
  data() {
    return {
      local: normalizeStudySettings(this.modelValue),
    };
  },
  computed: {
    examples() {
      return studyNumberExamples(this.local);
    },
    separatorDescription() {
      return `Decimal “${this.local.numberFormat.decimalSeparator}” · grouping “${this.local.numberFormat.groupingSeparator}”`;
    },
    measurementSummary() {
      return collectStudyMeasurements(this.forms);
    },
    classifiedFieldCount() {
      return this.measurementSummary.classified.reduce((total, row) => total + row.fields.length, 0);
    },
    measurementRows() {
      return this.measurementSummary.classified.map((row) => ({
        ...row,
        definition: measurementConcept(row.concept),
      }));
    },
  },
  watch: {
    modelValue: {
      deep: true,
      handler(next) {
        const normalized = normalizeStudySettings(next);
        if (JSON.stringify(normalized) !== JSON.stringify(this.local)) this.local = normalized;
      },
    },
  },
  methods: {
    applyPreset() {
      this.local = normalizeStudySettings(this.local);
      this.emitChange();
    },
    emitChange() {
      this.$emit("update:modelValue", normalizeStudySettings(this.local));
    },
    fieldNames(fields) {
      const labels = fields.map((field) => `${field.section}: ${field.label}`);
      if (labels.length <= 3) return labels.join(", ");
      return `${labels.slice(0, 3).join(", ")} and ${labels.length - 3} more`;
    },
  },
};
</script>

<style lang="scss" scoped>
@import "@/assets/styles/_base.scss";

.study-settings-page {
  min-height: 100%;
  padding: 18px;
  background: #f6f8fb;
  color: #111827;
  box-sizing: border-box;
}

.settings-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.settings-heading h2,
.settings-heading p,
.card-heading h3,
.card-heading p,
.measurement-empty p { margin: 0; }
.settings-heading h2 { margin-bottom: 3px; }
.settings-heading p,
.card-heading p,
.measurement-empty p { color: #6b7280; }

.scope-chip,
.classification-count,
.usage-count {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #f4f4f4;
  color: #374151;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 9px;
}

.settings-back { white-space: nowrap; }

.settings-content {
  width: min(940px, 100%);
  margin: 0 auto;
  padding: 22px 0 42px;
}

.settings-card {
  overflow: hidden;
  margin-bottom: 16px;
  border: 1px solid #dddddd;
  border-radius: 10px;
  background: #fff;
}

.card-heading {
  padding: 17px 18px 14px;
  border-bottom: 1px solid #e5e7eb;
}
.card-heading h3 { margin-bottom: 4px; }
.measurement-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.settings-body { padding: 18px; }

.setting-field { display: grid; gap: 7px; max-width: 440px; font-weight: 700; }
.setting-field select,
.measurement-table select {
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  background: #fff;
  color: #333333;
}

.format-preview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9f9f9;
}
.format-preview div { display: grid; gap: 4px; }
.format-preview small { color: #6b7280; }
.format-preview strong { font-size: 16px; font-variant-numeric: tabular-nums; }

.policy-list { display: grid; gap: 12px; }
.policy-option { display: grid; grid-template-columns: auto 1fr; gap: 10px; align-items: start; cursor: pointer; }
.policy-option input { margin-top: 3px; accent-color: #444444; }
.policy-option span { display: grid; gap: 3px; }
.policy-option small { color: #6b7280; }

.measurement-table-wrap { overflow-x: auto; }
.measurement-table { width: 100%; border-collapse: collapse; }
.measurement-table th,
.measurement-table td { padding: 11px 10px; border-bottom: 1px solid #e5eaf0; text-align: left; vertical-align: top; }
.measurement-table th { color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.measurement-table td:nth-child(2) { width: 180px; }
.measurement-table td:last-child { display: grid; gap: 6px; }
.measurement-table td:last-child small { color: #6b7280; }

.measurement-empty {
  padding: 18px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  background: #f9f9f9;
  text-align: center;
}
.measurement-empty strong { display: block; margin-bottom: 5px; }

.unclassified-note,
.safety-note {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 9px;
}
.unclassified-note { border: 1px solid #fde68a; background: #fffbeb; color: #78350f; }
.safety-note { margin-top: 0; border: 1px solid #d1d5db; background: #f4f4f4; color: #374151; }
.unclassified-note span,
.safety-note span { color: inherit; }

@media (max-width: 720px) {
  .study-settings-page { padding: 10px; }
  .settings-topbar { grid-template-columns: 1fr; }
  .scope-chip { display: none; }
  .format-preview { grid-template-columns: 1fr; }
  .measurement-heading,
  .unclassified-note,
  .safety-note { flex-direction: column; }
}
</style>
