<template>
  <div class="constraints-edit-modal">
    <div class="head">
      <h3>Field Settings & Constraints</h3>
      <span class="type-chip">{{ currentTypeLabel }}</span>
    </div>

    <div class="dialog-tabs">
      <button
        type="button"
        class="dialog-tab"
        :class="{ active: activeTab === 'basic' }"
        @click="activeTab = 'basic'"
      >
        Basic
      </button>
      <button
        type="button"
        class="dialog-tab"
        :class="{ active: activeTab === 'advanced' }"
        @click="activeTab = 'advanced'"
      >
        Advanced
      </button>
    </div>

    <!-- ========================= BASIC TAB ========================= -->
    <template v-if="activeTab === 'basic'">
      <section class="group">
        <div class="row" v-if="isSlider">
          <label>Control type</label>
          <div class="choice-row">
            <label class="chk">
              <input type="radio" value="slider" v-model="local.mode" />
              Slider
            </label>
            <label class="chk">
              <input type="radio" value="linear" v-model="local.mode" />
              Likert scale
            </label>
          </div>
        </div>

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

        <div class="row" v-if="!isCheckbox && !(isSlider && local.mode === 'slider') && !isFile">
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

        <div class="row" v-if="!isDate && !(isSlider && local.mode === 'slider') && !isFile">
          <label>Default value</label>

          <select v-if="isChoice && !local.allowMultiple" v-model="local.defaultValue">
            <option value="">(none)</option>
            <option v-for="(opt, i) in localOptions" :key="i" :value="opt">{{ opt }}</option>
          </select>

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
              <span
                v-for="(val, i) in (Array.isArray(local.defaultValue) ? local.defaultValue : [])"
                :key="i"
                class="chip"
              >
                {{ val }}
                <button class="chip-x" @click.prevent="removeChip(i)">×</button>
              </span>
            </div>
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

          <small v-if="defaultError && !isDate" class="err">{{ defaultError }}</small>
        </div>
      </section>

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

      <section class="group" v-if="isNumber">
        <div class="row two">
          <div>
            <label>Min value</label>
            <input type="number" :value="num(local.min)" @input="setNum('min', $event)" />
          </div>
          <div>
            <label>Max value</label>
            <input type="number" :value="num(local.max)" @input="setNum('max', $event)" />
          </div>
        </div>

        <div class="row">
          <label>Step</label>
          <input
            type="number"
            :value="num(local.step)"
            @input="setNum('step', $event)"
            placeholder="Leave empty if not applicable"
          />
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
            For values that need leading zeros, consider a <b>Text</b> field with a pattern.
          </span>
        </div>
      </section>

      <section class="group" v-if="isTime">
        <div class="row two">
          <div>
            <label>Min time</label>
            <FieldTime
              v-model="local.minTime"
              :hourCycle="local.hourCycle || '24'"
              :readonly="false"
              :disabled="false"
              :placeholder="(local.hourCycle === '12' ? 'hh:mm AM/PM' : 'HH:mm')"
            />
          </div>
          <div>
            <label>Max time</label>
            <FieldTime
              v-model="local.maxTime"
              :hourCycle="local.hourCycle || '24'"
              :readonly="false"
              :disabled="false"
              :placeholder="(local.hourCycle === '12' ? 'hh:mm AM/PM' : 'HH:mm')"
            />
          </div>
        </div>
      </section>

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
          <small v-if="defaultError && isDate" class="err">{{ defaultError }}</small>
        </div>
      </section>

      <section class="group" v-if="isFile">
        <div class="row">
          <label>Allowed formats</label>
          <input
            type="text"
            v-model="allowedFormatsText"
            placeholder="Examples: .pdf, .csv, .tsv, image/*, application/zip"
          />
          <small class="note">
            Comma-separated list. Client validates on upload; re-validate server-side if needed.
          </small>
        </div>

        <div class="row two">
          <div>
            <label>Max size (MB)</label>
            <input type="number" min="1" step="1" v-model.number="local.maxSizeMB" />
          </div>
          <div>
            <label>Storage behavior</label>
            <select v-model="local.storagePreference">
              <option value="local">Local storage (upload)</option>
              <option value="url">Link via URL</option>
            </select>
            <small class="note">This decides which input appears in the form.</small>
          </div>
        </div>

        <div class="row">
          <label class="chk">
            <input type="checkbox" v-model="local.allowMultipleFiles" />
            Allow multiple files
          </label>
        </div>

        <div class="row">
          <label>Modalities (BIDS)</label>
          <div class="chips">
            <div class="chip-group">
              <label
                v-for="mod in allModalities"
                :key="mod"
                class="chip selectable"
              >
                <input type="checkbox" :value="mod" v-model="local.modalities" />
                {{ mod }}
                <button
                  v-if="!builtInSet.has(mod)"
                  class="chip-x"
                  @click.prevent="removeCustomModByName(mod)"
                  title="Remove custom modality"
                >×</button>
              </label>
            </div>

            <div class="chip-input-row add-mod-row">
              <input
                type="text"
                v-model="customMod"
                placeholder="Custom modality (Enter or +)"
                @keydown.enter.prevent="addCustomMod"
              />
              <button type="button" class="btn-option add-mod-btn" @click="addCustomMod">+</button>
            </div>

            <small class="note">Used to help organize and name files in BIDS folders.</small>
          </div>
        </div>
      </section>

      <section class="group" v-if="isSlider && local.mode === 'slider'">
        <div class="row two">
          <div>
            <label>Min</label>
            <input type="number" :value="num(local.min)" @input="setNum('min', $event)" :disabled="local.percent" />
          </div>
          <div>
            <label>Max</label>
            <input type="number" :value="num(local.max)" @input="setNum('max', $event)" :disabled="local.percent" />
          </div>
        </div>

        <div class="row two">
          <div>
            <label>Step</label>
            <input
              type="number"
              min="0.000001"
              step="0.000001"
              :value="num(local.step)"
              @input="setNum('step', $event)"
            />
          </div>
          <div>
            <label class="chk">
              <input type="checkbox" v-model="local.percent" />
              Show as percentage (1–100)
            </label>
          </div>
        </div>

        <div class="row note">
          <span>No default selection for sliders. Clicking the track jumps to the nearest step.</span>
        </div>

        <div class="row">
          <label>Step labels</label>
          <div class="options-scroll">
            <div class="opt-row">
              <span class="opt-index">#</span>
              <input
                type="number"
                v-model.number="markEditValue"
                :min="useMin"
                :max="useMax"
                :step="useStep"
                placeholder="Step value"
              />
            </div>
            <div class="opt-row">
              <span class="opt-index">↳</span>
              <input
                type="text"
                v-model="markEditLabel"
                placeholder="Label"
                @keydown.enter.prevent="addOrUpdateMark('slider')"
              />
              <button class="icon-btn" title="Add/Update" @click.prevent="addOrUpdateMark('slider')">✓</button>
            </div>

            <div class="opt-row" v-for="(m, i) in marksSorted" :key="'s' + i">
              <span class="opt-index">{{ m.value }}</span>
              <input type="text" :value="m.label" disabled />
              <button class="icon-btn" title="Delete" @click.prevent="removeMark(m.value)">✕</button>
            </div>
          </div>
          <small class="note">We only store labels you add; no snap behavior.</small>
        </div>
      </section>

      <section class="group" v-if="isSlider && local.mode === 'linear'">
        <div class="row two">
          <div>
            <label>Min</label>
            <input type="number" :value="num(local.min)" @input="setNum('min', $event)" />
          </div>
          <div>
            <label>Max</label>
            <input type="number" :value="num(local.max)" @input="setNum('max', $event)" />
          </div>
        </div>
        <div class="row two">
          <div>
            <label>Left label</label>
            <input type="text" v-model="local.leftLabel" placeholder="e.g., Not happy" />
          </div>
          <div>
            <label>Right label</label>
            <input type="text" v-model="local.rightLabel" placeholder="e.g., Very happy" />
          </div>
        </div>
        <div class="row note" v-if="linearCount > LINEAR_MAX">
          <span class="err">Too many points ({{ linearCount }}). Limit is {{ LINEAR_MAX }} to avoid clutter.</span>
        </div>
        <div class="row note">
          <span>Likert scale shows only endpoints (left/right). No step labels.</span>
        </div>
      </section>

      <section class="group" v-if="isChoice">
        <div class="row">
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
              <button type="button" class="btn-option" @click="removeLastOption()" :disabled="localOptions.length <= 1">− Remove</button>
            </div>
          </div>
        </div>

        <div class="options-scroll">
          <div class="opt-row" v-for="(opt, idx) in localOptions" :key="idx">
            <span class="opt-index">{{ idx + 1 }}.</span>
            <input type="text" v-model="localOptions[idx]" placeholder="Option label" />
            <button class="icon-btn" title="Delete" @click.prevent="deleteOption(idx)" :disabled="localOptions.length <= 1">✕</button>
          </div>
        </div>
        <div class="row note" v-if="isSelect">
          <span>Dropdowns are single-select in this builder.</span>
        </div>
      </section>

      <section class="group" v-if="isCheckbox">
        <div class="row note">
          <span>Checkbox has no placeholder. Use help text for guidance.</span>
        </div>
      </section>
    </template>

    <!-- ========================= ADVANCED TAB ========================= -->
    <template v-else>
      <section class="group">
        <div class="row two">
          <div>
            <label>When conditions match</label>
            <select v-model="local.visibilityLogic.action">
              <option value="show">Show this field</option>
              <option value="hide">Hide this field</option>
            </select>
          </div>
          <div>
            <label>Condition mode</label>
            <select v-model="local.visibilityLogic.match">
              <option value="all">All conditions must match (AND)</option>
              <option value="any">Any one condition may match (OR)</option>
            </select>
          </div>
        </div>

        <div class="row note">
          <span>Configure this field’s visibility based on other fields.</span>
        </div>

        <div class="logic-rules">
          <div
            class="logic-rule-card"
            v-for="(rule, idx) in local.visibilityLogic.rules"
            :key="rule.id"
          >
            <div class="logic-rule-top">
              <strong>Condition {{ idx + 1 }}</strong>
              <div class="logic-rule-top-actions">
                <button class="btn-mini" @click.prevent="clearLogicRule(rule)">Clear</button>
                <button class="icon-btn" @click.prevent="removeLogicRule(idx)">✕</button>
              </div>
            </div>

            <div class="row">
              <label>Source field</label>
              <select v-model="rule.sourceFieldKey" @change="onSourceFieldChanged(rule)">
                <option value="">Select source field…</option>
                <option
                  v-for="f in availableSourceFields"
                  :key="f.key"
                  :value="f.key"
                >
                  {{ f.pathLabel }}
                </option>
              </select>
            </div>

            <div class="row" v-if="rule.sourceFieldKey">
              <label>Operator</label>
              <select v-model="rule.operator" @change="onOperatorChanged(rule)">
                <option
                  v-for="op in availableOperatorsForRule(rule)"
                  :key="op.value"
                  :value="op.value"
                >
                  {{ op.label }}
                </option>
              </select>
            </div>

            <template v-if="needsNoValue(rule.operator)">
              <div class="row note">
                <span>No compare value needed for this operator.</span>
              </div>
            </template>

            <template v-else-if="rule.operator === 'between'">
              <div class="row two">
                <div>
                  <label>From</label>

                  <input
                    v-if="ruleSourceType(rule) === 'number' || ruleSourceType(rule) === 'slider'"
                    type="number"
                    v-model.number="rule.value"
                  />

                  <FieldTime
                    v-else-if="ruleSourceType(rule) === 'time'"
                    v-model="rule.value"
                    :hourCycle="sourceHourCycle(rule)"
                    :readonly="false"
                    :disabled="false"
                  />

                  <DateFormatPicker
                    v-else-if="ruleSourceType(rule) === 'date'"
                    v-model="rule.value"
                    :format="sourceDateFormat(rule)"
                    :placeholder="sourceDateFormat(rule)"
                  />

                  <input
                    v-else
                    type="text"
                    v-model="rule.value"
                  />
                </div>

                <div>
                  <label>To</label>

                  <input
                    v-if="ruleSourceType(rule) === 'number' || ruleSourceType(rule) === 'slider'"
                    type="number"
                    v-model.number="rule.valueTo"
                  />

                  <FieldTime
                    v-else-if="ruleSourceType(rule) === 'time'"
                    v-model="rule.valueTo"
                    :hourCycle="sourceHourCycle(rule)"
                    :readonly="false"
                    :disabled="false"
                  />

                  <DateFormatPicker
                    v-else-if="ruleSourceType(rule) === 'date'"
                    v-model="rule.valueTo"
                    :format="sourceDateFormat(rule)"
                    :placeholder="sourceDateFormat(rule)"
                  />

                  <input
                    v-else
                    type="text"
                    v-model="rule.valueTo"
                  />
                </div>
              </div>
            </template>

            <template v-else-if="ruleSourceIsChoiceSingle(rule)">
              <div class="row">
                <label>Compare value</label>
                <select v-model="rule.value">
                  <option value="">Select…</option>
                  <option
                    v-for="opt in sourceOptions(rule)"
                    :key="opt"
                    :value="opt"
                  >
                    {{ opt }}
                  </option>
                </select>
                <small class="note">Options from selected source field.</small>
              </div>
            </template>

            <template v-else-if="ruleSourceIsChoiceMulti(rule)">
              <div class="row">
                <label>Compare value(s)</label>
                <div class="chips">
                  <div class="chip-input-row">
                    <input
                      type="text"
                      v-model="rule._chipInput"
                      placeholder="Type option and press Enter"
                      @keydown.enter.prevent="addRuleChip(rule)"
                      :list="`logic-options-${rule.id}`"
                    />
                    <datalist :id="`logic-options-${rule.id}`">
                      <option v-for="opt in sourceOptions(rule)" :key="opt" :value="opt" />
                    </datalist>
                  </div>
                  <div class="chip-group">
                    <span
                      v-for="(val, i) in (Array.isArray(rule.value) ? rule.value : [])"
                      :key="i"
                      class="chip"
                    >
                      {{ val }}
                      <button class="chip-x" @click.prevent="removeRuleChip(rule, i)">×</button>
                    </span>
                  </div>
                </div>
              </div>
            </template>

            <template v-else-if="ruleSourceType(rule) === 'checkbox'">
              <div class="row">
                <label>Compare value</label>
                <select v-model="rule.value">
                  <option :value="true">Checked</option>
                  <option :value="false">Unchecked</option>
                </select>
              </div>
            </template>

            <template v-else>
              <div class="row">
                <label>Compare value</label>

                <input
                  v-if="ruleSourceType(rule) === 'number' || ruleSourceType(rule) === 'slider'"
                  type="number"
                  v-model.number="rule.value"
                />

                <FieldTime
                  v-else-if="ruleSourceType(rule) === 'time'"
                  v-model="rule.value"
                  :hourCycle="sourceHourCycle(rule)"
                  :readonly="false"
                  :disabled="false"
                />

                <DateFormatPicker
                  v-else-if="ruleSourceType(rule) === 'date'"
                  v-model="rule.value"
                  :format="sourceDateFormat(rule)"
                  :placeholder="sourceDateFormat(rule)"
                />

                <input
                  v-else
                  type="text"
                  v-model="rule.value"
                  placeholder="Enter compare value"
                />
              </div>
            </template>

            <div class="row note">
              <span>{{ logicSummary(rule) }}</span>
            </div>
          </div>
        </div>

        <div class="row">
          <button type="button" class="btn-option" @click="addLogicRule">
            + Add condition
          </button>
        </div>
      </section>
    </template>

    <div class="modal-actions">
      <button class="btn-primary" @click="save" :disabled="isSaveDisabled">Save</button>
      <button class="btn-option" @click="clearToInitial">Clear</button>
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
  "yyyy",
];

const BIDS_MODALITIES = Object.freeze([
  "MRI",
  "T1w",
  "T2w",
  "bold",
  "dwi",
  "FLAIR",
  "PD",
  "inplaneT2",
  "fmap",
  "fieldmap",
  "epi",
  "phasediff",
  "magnitude",
  "MEG",
  "EEG",
  "iEEG",
  "NIRS",
  "PET",
  "ASL",
  "beh",
  "events",
  "physio",
  "scans",
  "func",
  "anat",
  "fmap",
  "swi",
]);

function buildInitialLocal(vm, constraintsForm, currentFieldType) {
  const base = constraintsForm || {};
  const type = (currentFieldType || "text").toLowerCase();

  const initialOptions = (Array.isArray(base.options) ? base.options : [])
    .filter(Boolean)
    .map(String);

  const defaultValue =
    base.defaultValue !== undefined
      ? base.defaultValue
      : type === "checkbox"
      ? false
      : type === "radio" && base.allowMultiple
      ? []
      : "";

  const allowedFormats = Array.isArray(base.allowedFormats)
    ? base.allowedFormats.map(String).map((s) => s.trim()).filter(Boolean)
    : [];

  return {
    required: !!base.required,
    readonly: !!base.readonly,
    helpText: base.helpText || "",
    placeholder: base.placeholder || "",
    defaultValue,

    minLength: isFinite(base.minLength) ? Number(base.minLength) : undefined,
    maxLength: isFinite(base.maxLength) ? Number(base.maxLength) : undefined,
    pattern: base.pattern || "",
    transform: base.transform || "none",

    min: isFinite(base.min) ? Number(base.min) : type === "slider" ? 1 : undefined,
    max: isFinite(base.max) ? Number(base.max) : type === "slider" ? 5 : undefined,
    step: isFinite(base.step) ? Number(base.step) : type === "slider" ? 1 : undefined,
    integerOnly: !!base.integerOnly,
    minDigits: isFinite(base.minDigits) ? Number(base.minDigits) : undefined,
    maxDigits: isFinite(base.maxDigits) ? Number(base.maxDigits) : undefined,

    minTime: base.minTime || "",
    maxTime: base.maxTime || "",
    hourCycle: base.hourCycle || "24",

    minDate: base.minDate || "",
    maxDate: base.maxDate || "",
    dateFormat: base.dateFormat || "dd.MM.yyyy",

    allowMultiple: !!base.allowMultiple,

    mode: base.mode === "linear" ? "linear" : "slider",
    percent: !!base.percent,

    leftLabel: base.leftLabel || "",
    rightLabel: base.rightLabel || "",

    marks: Array.isArray(base.marks)
      ? base.marks
          .map((m) => ({ value: Number(m?.value), label: String(m?.label ?? "") }))
          .filter((m) => Number.isFinite(m.value) && m.label)
      : base.marks && typeof base.marks === "object"
      ? Object.keys(base.marks)
          .map((k) => ({ value: Number(k), label: String(base.marks[k]) }))
          .filter((m) => Number.isFinite(m.value) && m.label)
      : [],

    allowedFormats,
    maxSizeMB:
      isFinite(base.maxSizeMB) && Number(base.maxSizeMB) > 0
        ? Number(base.maxSizeMB)
        : undefined,
    storagePreference: base.storagePreference === "url" ? "url" : "local",
    allowMultipleFiles: base.allowMultipleFiles === undefined ? true : !!base.allowMultipleFiles,
    modalities: Array.isArray(base.modalities)
      ? base.modalities.filter(Boolean).map(String)
      : [],

    visibilityLogic: vm.normalizeVisibilityLogic(base.visibilityLogic),
  };
}

export default {
  name: "FieldConstraintsDialog",
  components: { DateFormatPicker, FieldTime },
  props: {
    currentFieldType: { type: String, default: "text" },
    constraintsForm: { type: Object, default: () => ({}) },
    form: { type: Object, default: () => ({ sections: [] }) },
    currentFieldKey: { type: String, default: "" },
    currentFieldLabel: { type: String, default: "" },
  },

  data() {
    const local = buildInitialLocal(this, this.constraintsForm, this.currentFieldType);
    const initialOptions = (Array.isArray(this.constraintsForm?.options) ? this.constraintsForm.options : [])
      .filter(Boolean)
      .map(String);
    const allowedFormats = Array.isArray(this.constraintsForm?.allowedFormats)
      ? this.constraintsForm.allowedFormats.map(String).map((s) => s.trim()).filter(Boolean)
      : [];

    return {
      activeTab: "basic",
      DATE_FORMATS,
      LINEAR_MAX: 10,
      BIDS_MODALITIES,
      customMod: "",
      allowedFormatsText: allowedFormats.join(", "),

      local,
      localOptions: initialOptions.length ? initialOptions : ["Option 1"],
      optionsCount: Math.max(1, initialOptions.length || 1),

      chipInput: "",
      markEditValue: null,
      markEditLabel: "",
    };
  },

  computed: {
    type() {
      return (this.currentFieldType || "text").toLowerCase();
    },
    isTextLike() {
      return this.type === "text" || this.type === "textarea";
    },
    isNumber() {
      return this.type === "number";
    },
    isTime() {
      return this.type === "time";
    },
    isDate() {
      return this.type === "date";
    },
    isCheckbox() {
      return this.type === "checkbox";
    },
    isRadio() {
      return this.type === "radio";
    },
    isSelect() {
      return this.type === "select";
    },
    isChoice() {
      return this.isRadio || this.isSelect;
    },
    isSlider() {
      return this.type === "slider";
    },
    isFile() {
      return this.type === "file";
    },
    currentTypeLabel() {
      return this.type.charAt(0).toUpperCase() + this.type.slice(1);
    },

    useMin() {
      return Number.isFinite(this.local.min) ? this.local.min : 1;
    },
    useMax() {
      return Number.isFinite(this.local.max) ? this.local.max : 5;
    },
    useStep() {
      return Number.isFinite(this.local.step) && this.local.step > 0 ? this.local.step : 1;
    },

    linearCount() {
      const min = Number.isFinite(+this.local.min) ? +this.local.min : 1;
      const max = Number.isFinite(+this.local.max) ? +this.local.max : 5;
      return Math.max(0, max - min + 1);
    },

    marksSorted() {
      return [...(this.local.marks || [])]
        .sort((a, b) => a.value - b.value)
        .filter((m, idx, arr) => idx === 0 || m.value !== arr[idx - 1].value);
    },

    defaultError() {
      if (!(this.local.required && this.local.readonly)) return "";

      const t = this.type;
      const dv = this.local.defaultValue;

      if (t === "radio") {
        const ok = this.local.allowMultiple
          ? Array.isArray(dv) && dv.length > 0
          : typeof dv === "string" && dv !== "";
        return ok ? "" : "Default value is required when the field is both Required and Readonly.";
      }

      if (t === "select") {
        const ok = typeof dv === "string" && dv !== "";
        return ok ? "" : "Default value is required when the field is both Required and Readonly.";
      }

      if (t === "checkbox") {
        const ok = !!dv;
        return ok ? "" : "Default value (Checked) is required when the field is both Required and Readonly.";
      }

      if (t === "number") {
        const ok = dv !== "" && dv !== null && dv !== undefined && !Number.isNaN(Number(dv));
        return ok ? "" : "Default value is required when the field is both Required and Readonly.";
      }

      return dv !== "" && dv !== null && dv !== undefined
        ? ""
        : "Default value is required when the field is both Required and Readonly.";
    },

    isSaveDisabled() {
      if (this.isSlider && this.local.mode === "linear") {
        return this.linearCount < 2 || this.linearCount > this.LINEAR_MAX;
      }
      if (!this.isDate && !(this.isSlider && this.local.mode === "slider") && this.local.required && this.local.readonly) {
        return !!this.defaultError;
      }
      return false;
    },

    builtInSet() {
      return new Set(BIDS_MODALITIES);
    },
    allModalities() {
      const extras = (this.local.modalities || []).filter(
        (m) => !!m && !this.builtInSet.has(m)
      );
      return [...BIDS_MODALITIES, ...Array.from(new Set(extras))];
    },

    availableSourceFields() {
      const currentKey = String(this.currentFieldKey || "");
      const out = [];

      (this.form?.sections || []).forEach((section, si) => {
        (section.fields || []).forEach((field, fi) => {
          const key = field._id || field.name || `section_${si}_field_${fi}`;
          if (String(key) === currentKey) return;

          const constraints = field.constraints || {};

          out.push({
            key: String(key),
            label: field.label || field.name || `Field ${fi + 1}`,
            sectionTitle: section.title || `Section ${si + 1}`,
            pathLabel: `${section.title || `Section ${si + 1}`}.${field.label || field.name || `Field ${fi + 1}`}`,
            type: field.type || "text",
            options: Array.isArray(field.options) ? [...field.options] : [],
            allowMultiple: !!constraints.allowMultiple,
            dateFormat: constraints.dateFormat || "dd.MM.yyyy",
            hourCycle: constraints.hourCycle || "24",
          });
        });
      });

      return out;
    },
  },

  watch: {
    constraintsForm: {
      deep: true,
      handler(nv) {
        const nextLocal = buildInitialLocal(this, nv, this.currentFieldType);
        const allowedFormats = Array.isArray(nv?.allowedFormats)
          ? nv.allowedFormats.map(String).map((s) => s.trim()).filter(Boolean)
          : [];

        this.allowedFormatsText = allowedFormats.join(", ");
        this.local = nextLocal;

        if (Array.isArray(nv?.options)) {
          const cleaned = nv.options.filter(Boolean).map(String);
          this.localOptions = cleaned.length ? cleaned : ["Option 1"];
          this.optionsCount = this.localOptions.length;
        }
      },
    },

    "local.percent"(on) {
      if (this.isSlider && this.local.mode === "slider" && on) {
        this.local.min = 1;
        this.local.max = 100;
        if (!Number.isFinite(this.local.step) || this.local.step <= 0) this.local.step = 1;
        this.local.marks = (this.local.marks || []).filter((m) => m.value >= 1 && m.value <= 100);
      }
    },

    currentFieldType(val) {
      const t = (val || "").toLowerCase();
      if (t === "checkbox") {
        this.local.defaultValue = !!this.local.defaultValue;
        this.local.placeholder = "";
      }
    },

    "local.allowMultiple"(nv) {
      if (!this.isRadio) return;
      if (nv) {
        this.local.defaultValue = Array.isArray(this.local.defaultValue)
          ? this.local.defaultValue.filter((v) => this.localOptions.includes(v))
          : this.local.defaultValue && this.localOptions.includes(this.local.defaultValue)
          ? [this.local.defaultValue]
          : [];
      } else {
        if (Array.isArray(this.local.defaultValue)) {
          this.local.defaultValue = this.local.defaultValue[0] || "";
        }
      }
    },

    localOptions: {
      deep: true,
      handler() {
        if (!this.isChoice) return;

        if (this.isRadio && this.local.allowMultiple) {
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
      },
    },
  },

  methods: {
    num(v) {
      return v === undefined || v === null || Number.isNaN(v) ? "" : v;
    },

    setNum(key, evt) {
      const raw = evt?.target?.value;
      if (raw === "" || raw === null || raw === undefined) {
        this.local[key] = undefined;
        return;
      }
      const n = Number(raw);
      this.local[key] = Number.isFinite(n) ? n : undefined;
    },

    uuidForRule() {
      return `rule_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    },

    makeLogicRule() {
      return {
        id: this.uuidForRule(),
        sourceFieldKey: "",
        operator: "eq",
        value: "",
        valueTo: "",
        _chipInput: "",
      };
    },

    normalizeSingleLogicRule(rule) {
      if (!rule || typeof rule !== "object") return this.makeLogicRule();

      return {
        id: rule.id || this.uuidForRule(),
        sourceFieldKey: String(rule.sourceFieldKey || ""),
        operator: String(rule.operator || "eq"),
        value: Array.isArray(rule.value) ? [...rule.value] : rule.value ?? "",
        valueTo: rule.valueTo ?? "",
        _chipInput: "",
      };
    },

    normalizeVisibilityLogic(raw) {
      const src = raw && typeof raw === "object" ? raw : {};
      const rules =
        Array.isArray(src.rules) && src.rules.length
          ? src.rules.map((rule) => this.normalizeSingleLogicRule(rule)).filter(Boolean)
          : [this.makeLogicRule()];

      return {
        action: src.action === "hide" ? "hide" : "show",
        match: src.match === "any" ? "any" : "all",
        rules,
      };
    },

    cleanedVisibilityLogic() {
      const src = this.local.visibilityLogic || {};
      const cleanedRules = (Array.isArray(src.rules) ? src.rules : [])
        .map((rule) => {
          const r = {
            sourceFieldKey: String(rule.sourceFieldKey || ""),
            operator: String(rule.operator || "eq"),
          };

          if (!r.sourceFieldKey) return null;

          if (this.needsNoValue(r.operator)) return r;

          if (r.operator === "between") {
            r.value = rule.value;
            r.valueTo = rule.valueTo;
            return r;
          }

          r.value = rule.value;
          return r;
        })
        .filter(Boolean);

      return {
        action: src.action === "hide" ? "hide" : "show",
        match: src.match === "any" ? "any" : "all",
        rules: cleanedRules,
      };
    },

    addLogicRule() {
      if (!Array.isArray(this.local.visibilityLogic.rules)) {
        this.local.visibilityLogic.rules = [];
      }
      this.local.visibilityLogic.rules.push(this.makeLogicRule());
    },

    removeLogicRule(idx) {
      if (!Array.isArray(this.local.visibilityLogic.rules)) {
        this.local.visibilityLogic.rules = [this.makeLogicRule()];
        return;
      }

      this.local.visibilityLogic.rules.splice(idx, 1);

      if (!this.local.visibilityLogic.rules.length) {
        this.local.visibilityLogic.rules.push(this.makeLogicRule());
      }
    },

    clearLogicRule(rule) {
      if (!rule) return;
      rule.sourceFieldKey = "";
      rule.operator = "eq";
      rule.value = "";
      rule.valueTo = "";
      rule._chipInput = "";
    },

    findSourceField(rule) {
      const key = String(rule?.sourceFieldKey || "");
      if (!key) return null;
      return this.availableSourceFields.find((f) => String(f.key) === key) || null;
    },

    ruleSourceType(rule) {
      return this.findSourceField(rule)?.type || "text";
    },

    ruleSourceIsChoiceSingle(rule) {
      const f = this.findSourceField(rule);
      return !!f && (f.type === "select" || f.type === "radio") && !f.allowMultiple;
    },

    ruleSourceIsChoiceMulti(rule) {
      const f = this.findSourceField(rule);
      return !!f && f.type === "radio" && !!f.allowMultiple;
    },

    sourceOptions(rule) {
      const f = this.findSourceField(rule);
      return Array.isArray(f?.options) ? f.options : [];
    },

    sourceDateFormat(rule) {
      return this.findSourceField(rule)?.dateFormat || "dd.MM.yyyy";
    },

    sourceHourCycle(rule) {
      return this.findSourceField(rule)?.hourCycle || "24";
    },

    needsNoValue(operator) {
      return ["is_empty", "is_not_empty"].includes(String(operator || ""));
    },

    availableOperatorsForRule(rule) {
      const type = this.ruleSourceType(rule);

      if (type === "number" || type === "slider") {
        return [
          { value: "eq", label: "Equals" },
          { value: "neq", label: "Does not equal" },
          { value: "gt", label: "Greater than" },
          { value: "gte", label: "Greater than or equal" },
          { value: "lt", label: "Less than" },
          { value: "lte", label: "Less than or equal" },
          { value: "between", label: "Between" },
          { value: "is_empty", label: "Is empty" },
          { value: "is_not_empty", label: "Is not empty" },
        ];
      }

      if (type === "date" || type === "time") {
        return [
          { value: "eq", label: "Equals" },
          { value: "neq", label: "Does not equal" },
          { value: "gt", label: "After / Greater than" },
          { value: "gte", label: "On or after / Greater than or equal" },
          { value: "lt", label: "Before / Less than" },
          { value: "lte", label: "On or before / Less than or equal" },
          { value: "between", label: "Between" },
          { value: "is_empty", label: "Is empty" },
          { value: "is_not_empty", label: "Is not empty" },
        ];
      }

      if (type === "checkbox") {
        return [
          { value: "eq", label: "Equals" },
          { value: "neq", label: "Does not equal" },
        ];
      }

      return [
        { value: "eq", label: "Equals" },
        { value: "neq", label: "Does not equal" },
        { value: "contains", label: "Contains" },
        { value: "not_contains", label: "Does not contain" },
        { value: "is_empty", label: "Is empty" },
        { value: "is_not_empty", label: "Is not empty" },
      ];
    },

    onSourceFieldChanged(rule) {
      const ops = this.availableOperatorsForRule(rule).map((o) => o.value);
      if (!ops.includes(rule.operator)) {
        rule.operator = ops[0] || "eq";
      }

      if (this.ruleSourceIsChoiceMulti(rule)) {
        rule.value = Array.isArray(rule.value) ? rule.value : [];
      } else if (this.ruleSourceType(rule) === "checkbox") {
        rule.value = true;
      } else {
        rule.value = "";
      }

      rule.valueTo = "";
      rule._chipInput = "";
    },

    onOperatorChanged(rule) {
      if (this.needsNoValue(rule.operator)) {
        rule.value = "";
        rule.valueTo = "";
        return;
      }

      if (rule.operator === "between") {
        rule.value = "";
        rule.valueTo = "";
        return;
      }

      if (this.ruleSourceIsChoiceMulti(rule)) {
        rule.value = Array.isArray(rule.value) ? rule.value : [];
      } else if (this.ruleSourceType(rule) === "checkbox") {
        rule.value = true;
      } else {
        rule.valueTo = "";
      }
    },

    addRuleChip(rule) {
      const val = String(rule?._chipInput || "").trim();
      if (!val) return;

      const allowed = this.sourceOptions(rule);
      if (allowed.length && !allowed.includes(val)) return;

      if (!Array.isArray(rule.value)) rule.value = [];
      if (!rule.value.includes(val)) rule.value.push(val);

      rule._chipInput = "";
    },

    removeRuleChip(rule, idx) {
      if (!Array.isArray(rule?.value)) return;
      rule.value.splice(idx, 1);
    },

    logicSummary(rule) {
      const src = this.findSourceField(rule);
      if (!src || !rule?.sourceFieldKey) return "Select a source field.";

      const fieldName = src.pathLabel || src.label || src.key;
      const op = rule.operator || "eq";

      if (this.needsNoValue(op)) {
        return `${fieldName} ${op.replaceAll("_", " ")}`;
      }

      if (op === "between") {
        return `${fieldName} between ${rule.value ?? ""} and ${rule.valueTo ?? ""}`;
      }

      if (Array.isArray(rule.value)) {
        return `${fieldName} ${op} [${rule.value.join(", ")}]`;
      }

      return `${fieldName} ${op} ${rule.value ?? ""}`;
    },

    addOrUpdateMark(kind) {
      if (kind !== "slider") return;
      let v = Number(this.markEditValue);
      const lbl = String(this.markEditLabel || "").trim();
      if (!Number.isFinite(v) || !lbl) return;

      const min = this.useMin;
      const max = this.useMax;
      const step = this.useStep;

      v = Math.max(min, Math.min(max, v));
      v = Math.round((v - min) / step) * step + min;
      v = Math.max(min, Math.min(max, v));

      const i = (this.local.marks || []).findIndex((m) => m.value === v);
      if (i >= 0) this.local.marks.splice(i, 1, { value: v, label: lbl });
      else (this.local.marks || (this.local.marks = [])).push({ value: v, label: lbl });

      this.markEditLabel = "";
      this.markEditValue = null;
    },

    removeMark(v) {
      const i = (this.local.marks || []).findIndex((m) => m.value === v);
      if (i >= 0) this.local.marks.splice(i, 1);
    },

    addChip() {
      const v = (this.chipInput || "").trim();
      if (!v) return;
      if (!this.localOptions.includes(v)) return;
      if (!Array.isArray(this.local.defaultValue)) this.local.defaultValue = [];
      if (!this.local.defaultValue.includes(v)) this.local.defaultValue.push(v);
      this.chipInput = "";
    },

    removeChip(i) {
      if (!Array.isArray(this.local.defaultValue)) return;
      this.local.defaultValue.splice(i, 1);
    },

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

    addCustomMod() {
      const v = (this.customMod || "").trim();
      if (!v) return;
      const exists = (this.local.modalities || []).some(
        (m) => (m || "").toLowerCase() === v.toLowerCase()
      );
      if (!exists) {
        if (!Array.isArray(this.local.modalities)) this.local.modalities = [];
        this.local.modalities.push(v);
      }
      this.customMod = "";
    },

    removeCustomModByName(name) {
      this.local.modalities = (this.local.modalities || []).filter((m) => m !== name);
    },

    save() {
      if (this.isSaveDisabled) return;

      const visibilityLogic = this.cleanedVisibilityLogic();

      if (this.isFile) {
        const parsedFormats = String(this.allowedFormatsText || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);

        const cleaned = {
          required: !!this.local.required,
          readonly: !!this.local.readonly,
          helpText: this.local.helpText || "",
          allowedFormats: parsedFormats,
          maxSizeMB:
            Number.isFinite(this.local.maxSizeMB) && this.local.maxSizeMB > 0
              ? Number(this.local.maxSizeMB)
              : undefined,
          storagePreference: this.local.storagePreference === "url" ? "url" : "local",
          allowMultipleFiles: this.local.allowMultipleFiles !== false,
          modalities: Array.isArray(this.local.modalities)
            ? Array.from(new Set(this.local.modalities.filter(Boolean).map(String)))
            : [],
          visibilityLogic,
        };

        this.$emit("updateConstraints", cleaned);
        return;
      }

      if (!this.isSlider) {
        const cleaned = normalizeConstraints(this.type, { ...this.local });

        if (this.isChoice) {
          const opts = this.localOptions.map((o) => String(o || "").trim()).filter(Boolean);
          const finalOpts = opts.length ? Array.from(new Set(opts)) : ["Option 1"];

          if (this.isRadio && this.local.allowMultiple) {
            const arr = Array.isArray(cleaned.defaultValue) ? cleaned.defaultValue : [];
            cleaned.defaultValue = arr.filter((v) => finalOpts.includes(v));
          } else {
            if (!finalOpts.includes(cleaned.defaultValue)) cleaned.defaultValue = "";
          }

          cleaned.options = finalOpts;
          if (this.isSelect) delete cleaned.allowMultiple;
        }

        cleaned.defaultValue = coerceDefaultForType(
          this.isRadio && this.local.allowMultiple ? "radio" : this.type,
          cleaned.defaultValue
        );
        cleaned.hourCycle = this.local.hourCycle || "24";
        cleaned.visibilityLogic = visibilityLogic;

        this.$emit("updateConstraints", cleaned);
        return;
      }

      if (this.local.mode === "slider") {
        const min = this.local.percent ? 1 : this.useMin;
        const max = this.local.percent ? 100 : this.useMax;
        const step = this.local.percent ? 1 : this.useStep;

        const marks = (this.local.marks || [])
          .map((m) => {
            let v = Number(m.value);
            if (!Number.isFinite(v)) return null;
            v = Math.round((v - min) / step) * step + min;
            v = Math.max(min, Math.min(max, v));
            return { value: v, label: String(m.label || "") };
          })
          .filter((m) => m && m.label)
          .filter((m, idx, arr) => arr.findIndex((x) => x.value === m.value) === idx)
          .sort((a, b) => a.value - b.value);

        const cleaned = {
          mode: "slider",
          required: !!this.local.required,
          readonly: !!this.local.readonly,
          helpText: this.local.helpText || "",
          percent: !!this.local.percent,
          min,
          max,
          step,
          marks,
          visibilityLogic,
        };

        this.$emit("updateConstraints", cleaned);
        return;
      }

      const LIM = this.LINEAR_MAX;
      let linMin = this.useMin;
      let linMax = this.useMax;
      if (linMax - linMin + 1 > LIM) linMax = linMin + (LIM - 1);
      if (linMax < linMin) linMax = linMin + 1;

      const cleaned = {
        mode: "linear",
        required: !!this.local.required,
        readonly: !!this.local.readonly,
        helpText: this.local.helpText || "",
        min: linMin,
        max: linMax,
        leftLabel: this.local.leftLabel || "",
        rightLabel: this.local.rightLabel || "",
        visibilityLogic,
      };

      this.$emit("updateConstraints", cleaned);
    },

    clearToInitial() {
      const t = this.type;

      this.local.required = false;
      this.local.readonly = false;
      this.local.helpText = "";
      if (!this.isCheckbox && !(this.isSlider && this.local.mode === "slider") && !this.isFile) {
        this.local.placeholder = "";
      }

      if (t === "checkbox") this.local.defaultValue = false;
      else if (t === "radio" && this.local.allowMultiple) this.local.defaultValue = [];
      else this.local.defaultValue = "";

      if (t === "number") {
        this.local.min = undefined;
        this.local.max = undefined;
        this.local.step = undefined;
        this.local.integerOnly = false;
        this.local.minDigits = undefined;
        this.local.maxDigits = undefined;
      } else if (t === "text" || t === "textarea") {
        this.local.minLength = undefined;
        this.local.maxLength = undefined;
        this.local.pattern = "";
        this.local.transform = "none";
      } else if (t === "time") {
        this.local.minTime = "";
        this.local.maxTime = "";
      } else if (t === "date") {
        this.local.minDate = "";
        this.local.maxDate = "";
        this.local.defaultValue = "";
      } else if (t === "slider") {
        this.local.percent = false;
        this.local.marks = [];
        if (this.local.mode === "linear") {
          this.local.min = 1;
          this.local.max = 5;
          this.local.leftLabel = "";
          this.local.rightLabel = "";
        } else {
          this.local.min = 1;
          this.local.max = 5;
          this.local.step = 1;
        }
      } else if (t === "file") {
        this.allowedFormatsText = "";
        this.local.allowedFormats = [];
        this.local.maxSizeMB = undefined;
        this.local.storagePreference = "local";
        this.local.allowMultipleFiles = true;
        this.local.modalities = [];
      } else if (t === "radio" || t === "select") {
        this.local.defaultValue = this.local.allowMultiple ? [] : "";
      }

      this.local.visibilityLogic = {
        action: "show",
        match: "all",
        rules: [this.makeLogicRule()],
      };

      this.activeTab = "basic";
      this.chipInput = "";
      this.markEditValue = null;
      this.markEditLabel = "";
      this.customMod = "";
    },
  },
};
</script>

<style scoped>
.constraints-edit-modal {
  width: 560px;
  background: #fff;
  padding: 16px 16px 12px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  max-height: 80vh;
  overflow-y: auto;
  box-sizing: border-box;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.type-chip {
  background: #eef2ff;
  color: #3730a3;
  border: 1px solid #c7d2fe;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.dialog-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.dialog-tab {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #f9fafb;
  cursor: pointer;
  font-size: 13px;
}
.dialog-tab.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.group {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
}
.row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}
.row.two {
  display: grid;
  gap: 10px;
  grid-template-columns: 1fr 1fr;
}
.choice-row {
  display: flex;
  gap: 16px;
}
label {
  font-size: 12px;
  color: #374151;
}
input[type="text"],
input[type="number"],
input[type="time"],
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}
.chk {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.note {
  color: #6b7280;
  font-size: 12px;
}
.options-scroll {
  max-height: 220px;
  overflow: auto;
  border: 1px dashed #e5e7eb;
  border-radius: 8px;
  padding: 8px;
}
.opt-row {
  display: grid;
  grid-template-columns: 24px 1fr 32px;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.opt-index {
  text-align: right;
  color: #6b7280;
  font-size: 12px;
}
.icon-btn {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  cursor: pointer;
  padding: 4px 8px;
}
.quick {
  display: flex;
  gap: 6px;
}
.chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chip-input-row input {
  width: 100%;
}
.add-mod-row {
  display: grid;
  grid-template-columns: 1fr 40px;
  gap: 6px;
}
.add-mod-btn {
  padding: 8px;
  border-radius: 6px;
}
.chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}
.chip {
  background: #eef2ff;
  color: #111827;
  border: 1px solid #c7d2fe;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.chip.selectable input {
  margin-right: 6px;
}
.chip-x {
  background: transparent;
  border: none;
  cursor: pointer;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease, opacity 0.2s ease;
}
.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-primary:disabled {
  background: #93c5fd;
  cursor: not-allowed;
  opacity: 0.7;
}
.btn-option {
  background: #e5e7eb;
  color: #111827;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
}
.btn-mini {
  background: #eef2ff;
  color: #1f2937;
  border: 1px solid #c7d2fe;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}
.err {
  color: #dc2626;
  font-size: 12px;
  margin-top: 4px;
}

.logic-rules {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}
.logic-rule-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  background: #fafafa;
}
.logic-rule-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.logic-rule-top-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>