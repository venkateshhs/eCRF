<template>
  <div class="subject-form">
    <BaseNumberField
      :modelValue="subjectCount"
      @update:modelValue="updateCount"
      id="subject-count"
      label="Number of Subjects"
      placeholder="e.g. 20"
      :required="true"
      :disabled="!subjectSetupEditable"
    />

    <BaseSelectField
      :modelValue="assignmentMethod"
      @update:modelValue="updateMethod"
      id="assignment-method"
      label="Assignment Method"
      :options="assignmentOptions"
      placeholder="Select assignment method"
      :required="true"
      :disabled="!subjectSetupEditable"
    />

    <div class="subject-id-card">
      <div class="subject-id-header">
        <div>
          <h3>Subject ID Format</h3>
          <p>
            Choose a format for generating subject IDs. Existing saved subject IDs are never regenerated.
          </p>
        </div>

        <span v-if="isFormatLocked" class="locked-pill">
          {{ isPublished ? "Locked after publish" : "Format locked" }}
        </span>
        <span v-else class="editable-pill">Editable</span>
      </div>

      <div v-if="isFormatLocked" class="locked-note">
        Subject ID format is locked after publishing. Existing subject IDs will not be changed.
      </div>

      <div class="subject-id-grid">
        <label class="field-block full-width">
          <span>Available Patterns</span>
          <select
            :value="localConfig.preset"
            :disabled="isFormatLocked"
            @change="applyPreset($event.target.value)"
          >
            <option
              v-for="preset in presetOptions"
              :key="preset.key"
              :value="preset.key"
            >
              {{ preset.label }}
            </option>
          </select>
        </label>

        <label v-if="isCustomPattern" class="field-block full-width">
          <span>Custom Pattern</span>
          <input
            :value="localConfig.pattern"
            :disabled="isFormatLocked"
            placeholder="e.g. SUBJ-{PREFIX}-{NUMBER}"
            @input="updateConfigField('pattern', $event.target.value)"
          />
        </label>

        <label class="field-block">
          <span>Prefix</span>
          <input
            :value="localConfig.prefix"
            :disabled="isFormatLocked || !usesPrefix"
            placeholder="e.g. HFS"
            @input="updateConfigField('prefix', $event.target.value)"
          />
        </label>

        <label class="field-block">
          <span>Start Number</span>
          <input
            type="number"
            min="1"
            :value="localConfig.startNumber"
            :disabled="isFormatLocked || !usesNumber"
            @input="updateConfigField('startNumber', $event.target.value)"
          />
        </label>

        <label class="field-block">
          <span>Number Padding</span>
          <input
            type="number"
            min="1"
            max="8"
            :value="localConfig.padding"
            :disabled="isFormatLocked || !usesNumber"
            @input="updateConfigField('padding', $event.target.value)"
          />
        </label>

        <label class="field-block full-width">
          <span>Example</span>
          <input
            :value="exampleId"
            disabled
            readonly
          />
        </label>
      </div>

      <div class="helper-row">
        <strong>Available tokens:</strong>
        <code>{PREFIX}</code>
        <code>{NUMBER}</code>
        <code>{UUID}</code>
        <code>{UUID8}</code>
        <code>{RAND6}</code>
      </div>

      <div v-if="validationError" class="format-error">
        {{ validationError }}
      </div>

      <div class="preview-box">
        <div class="preview-title">Preview</div>
        <div class="preview-list">
          <span v-for="id in previewIds" :key="id" class="preview-id">
            {{ id }}
          </span>
        </div>
      </div>

      <div v-if="hasExistingSubjects && !isFormatLocked" class="existing-note">
        Existing saved IDs are preserved. If you continue from Step 3, draft subject IDs are regenerated using the selected pattern.
      </div>
    </div>
  </div>
</template>

<script>
import { computed, reactive, watch } from "vue";
import BaseNumberField from "@/components/forms/BaseNumberField.vue";
import BaseSelectField from "@/components/forms/BaseSelectField.vue";
import {
  DEFAULT_SUBJECT_ID_CONFIG,
  SUBJECT_ID_PRESET_DEFINITIONS,
  deepClone,
  normalizeSubjectPrefix,
  normalizeSubjectIdConfig,
  presetFromSubjectIdConfig,
  buildPreviewSubjectId,
  subjectIdPatternValidationMessage,
} from "@/utils/subjectIdUtils";

export default {
  name: "SubjectForm",
  components: { BaseNumberField, BaseSelectField },
  props: {
    subjectCount: Number,
    assignmentMethod: String,

    subjectIdConfig: {
      type: Object,
      default: () => ({ ...DEFAULT_SUBJECT_ID_CONFIG }),
    },

    subjectSetupEditable: {
      type: Boolean,
      default: true,
    },

    subjectIdFormatEditable: {
      type: Boolean,
      default: true,
    },

    hasExistingSubjects: {
      type: Boolean,
      default: false,
    },

    isPublished: {
      type: Boolean,
      default: false,
    },

    assignmentOptions: {
      type: Array,
      default: () => ["Random", "Manual", "Skip"],
    },
  },
  emits: [
    "update:subjectCount",
    "update:assignmentMethod",
    "update:subjectIdConfig",
    "changed",
  ],
  setup(props, { emit }) {
    const localConfig = reactive(normalizeSubjectIdConfig(props.subjectIdConfig));

    const selectedPreset = computed(() => {
      return presetFromSubjectIdConfig(localConfig);
    });

    const isCustomPattern = computed(() => {
      return localConfig.preset === "custom";
    });

    const effectivePattern = computed(() => {
      if (isCustomPattern.value) {
        return String(localConfig.pattern || "").trim() || DEFAULT_SUBJECT_ID_CONFIG.pattern;
      }

      return selectedPreset.value?.pattern || DEFAULT_SUBJECT_ID_CONFIG.pattern;
    });

    const presetOptions = computed(() => {
      const prefix = normalizeSubjectPrefix(localConfig.prefix);

      return SUBJECT_ID_PRESET_DEFINITIONS.map((item) => ({
        ...item,
        label: item.label(prefix),
      }));
    });

    const isFormatLocked = computed(() => {
      return props.isPublished || !!localConfig.locked || !props.subjectIdFormatEditable;
    });

    const usesPrefix = computed(() => {
      return String(effectivePattern.value || "").includes("{PREFIX}");
    });

    const usesNumber = computed(() => {
      return String(effectivePattern.value || "").includes("{NUMBER}");
    });

    const validationError = computed(() => {
      return subjectIdPatternValidationMessage({
        ...deepClone(localConfig),
        pattern: effectivePattern.value,
      });
    });

    const exampleId = computed(() => {
      return buildPreviewSubjectId(
        {
          ...deepClone(localConfig),
          pattern: effectivePattern.value,
        },
        Number(localConfig.startNumber || 1),
        0
      );
    });

    const previewIds = computed(() => {
      const start = Number(localConfig.startNumber || 1);

      return [0, 1, 2].map((offset) =>
        buildPreviewSubjectId(
          {
            ...deepClone(localConfig),
            pattern: effectivePattern.value,
          },
          start + offset,
          offset
        )
      );
    });

    function emitConfig(kind = "subjectIdConfig") {
      const normalized = normalizeSubjectIdConfig({
        ...deepClone(localConfig),
        preset: selectedPreset.value.key,
        mode: selectedPreset.value.mode,
        pattern: effectivePattern.value,
        locked: props.isPublished || !props.subjectIdFormatEditable,
      });

      Object.assign(localConfig, normalized);

      emit("update:subjectIdConfig", normalized);
      emit("changed", { kind, value: normalized });
    }

    watch(
      () => props.subjectCount,
      (val) => {
        if (val == null && props.subjectSetupEditable) {
          emit("update:subjectCount", 1);
        }
      },
      { immediate: true }
    );

    watch(
      () => props.assignmentMethod,
      (val) => {
        if (!val && props.subjectSetupEditable) {
          emit("update:assignmentMethod", "Random");
        }
      },
      { immediate: true }
    );

    watch(
      () => props.subjectIdConfig,
      (next) => {
        const normalized = normalizeSubjectIdConfig(next);

        Object.assign(localConfig, {
          ...normalized,
          locked: props.isPublished || !!normalized.locked || !props.subjectIdFormatEditable,
        });
      },
      { deep: true, immediate: true }
    );

    function updateCount(val) {
      if (!props.subjectSetupEditable) return;

      emit("update:subjectCount", val);
      emit("changed", { kind: "subjectCount", value: val });
    }

    function updateMethod(val) {
      if (!props.subjectSetupEditable) return;

      emit("update:assignmentMethod", val);
      emit("changed", { kind: "assignmentMethod", value: val });
    }

    function updateConfigField(field, value) {
      if (isFormatLocked.value) return;

      if (field === "prefix") {
        localConfig.prefix = normalizeSubjectPrefix(value);
      } else if (field === "padding") {
        const n = Number(value);
        localConfig.padding = Number.isFinite(n) ? Math.min(Math.max(n, 1), 8) : 3;
      } else if (field === "startNumber") {
        const n = Number(value);
        localConfig.startNumber = Number.isFinite(n) ? Math.max(n, 1) : 1;
      } else if (field === "pattern") {
        localConfig.preset = "custom";
        localConfig.mode = "custom";
        localConfig.pattern = String(value || "").trim();
      }

      if (!isCustomPattern.value) {
        localConfig.pattern = effectivePattern.value;
      }

      emitConfig();
    }

    function applyPreset(key) {
      if (isFormatLocked.value) return;

      const selected =
        SUBJECT_ID_PRESET_DEFINITIONS.find((p) => p.key === key) ||
        SUBJECT_ID_PRESET_DEFINITIONS[0];

      localConfig.preset = selected.key;
      localConfig.mode = selected.mode;

      if (selected.key === "custom") {
        localConfig.pattern = localConfig.pattern || DEFAULT_SUBJECT_ID_CONFIG.pattern;
      } else {
        localConfig.pattern = selected.pattern;
      }

      emitConfig("subjectIdPreset");
    }

    return {
      localConfig,
      presetOptions,
      isFormatLocked,
      isCustomPattern,
      usesPrefix,
      usesNumber,
      validationError,
      previewIds,
      exampleId,
      effectivePattern,
      updateCount,
      updateMethod,
      updateConfigField,
      applyPreset,
    };
  },
};
</script>

<style scoped>
.subject-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.subject-id-card {
  margin-top: 4px;
  padding: 16px;
  border: 1px solid #dbe3ef;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}

.subject-id-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.subject-id-header h3 {
  margin: 0;
  font-size: 16px;
  color: #111827;
}

.subject-id-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.4;
}

.locked-pill,
.editable-pill {
  flex: 0 0 auto;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.locked-pill {
  background: #fee2e2;
  color: #991b1b;
}

.editable-pill {
  background: #dcfce7;
  color: #166534;
}

.locked-note,
.existing-note {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.4;
}

.locked-note {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
}

.existing-note {
  margin-top: 12px;
  margin-bottom: 0;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}

.subject-id-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-block.full-width {
  grid-column: 1 / -1;
}

.field-block span {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}

.field-block input,
.field-block select {
  width: 100%;
  min-height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  box-sizing: border-box;
  background: #ffffff;
}

.field-block input:disabled,
.field-block select:disabled {
  background: #f3f4f6;
  color: #6b7280;
  cursor: not-allowed;
}

.helper-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
  font-size: 13px;
  color: #475569;
}

.helper-row code {
  padding: 2px 6px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #0f172a;
}

.format-error {
  margin-top: 10px;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 600;
}

.preview-box {
  margin-top: 14px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
}

.preview-title {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 8px;
}

.preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preview-id {
  padding: 6px 9px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #111827;
  font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

@media (max-width: 720px) {
  .subject-id-grid {
    grid-template-columns: 1fr;
  }

  .subject-id-header {
    flex-direction: column;
  }
}
</style>