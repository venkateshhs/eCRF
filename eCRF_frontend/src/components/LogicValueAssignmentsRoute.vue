<template>
  <div class="assignment-page">
    <div class="assignment-topbar">
      <button type="button" class="btn-back" @click="goBack">Back</button>
      <div>
        <h2>Value Assignments</h2>
        <p>Automatically set a field value when one or more clinical conditions match.</p>
      </div>
      <div class="topbar-actions">
        <button type="button" class="btn-secondary" @click="resetEditor">Reset</button>
        <button type="button" class="btn-primary" :disabled="!canSaveRule" @click="saveRule">
          {{ editingRuleId ? "Update Assignment" : "Add Assignment" }}
        </button>
      </div>
    </div>

    <div class="assignment-workspace">
      <section class="panel editor-panel">
        <h3>Assignment rule</h3>

        <label class="field-block">
          <span>Rule name</span>
          <input v-model.trim="draft.name" placeholder="e.g. Set dose action for severe toxicity" />
        </label>

        <div class="grid-two">
          <label class="field-block">
            <span>Target field</span>
            <select v-model="draft.targetFieldKey" @change="onTargetChanged">
              <option value="">Select target field…</option>
              <optgroup
                v-for="section in targetFieldTree"
                :key="section.key"
                :label="section.title"
              >
                <option
                  v-for="field in section.fields"
                  :key="field.key"
                  :value="field.key"
                >
                  {{ field.label }}
                </option>
              </optgroup>
            </select>
          </label>

          <label class="field-block">
            <span>Set target value to</span>
            <select
              v-if="targetIsChoice"
              v-model="draft.outputValue"
              :disabled="!draft.targetFieldKey"
            >
              <option value="">Select output…</option>
              <option v-for="option in targetOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>

            <select
              v-else-if="targetType === 'checkbox'"
              v-model="draft.outputValue"
              :disabled="!draft.targetFieldKey"
            >
              <option :value="true">Checked</option>
              <option :value="false">Unchecked</option>
            </select>

            <DateFormatPicker
              v-else-if="targetType === 'date'"
              v-model="draft.outputValue"
              :format="selectedTarget?.field?.constraints?.dateFormat || 'dd.MM.yyyy'"
              :placeholder="selectedTarget?.field?.constraints?.dateFormat || 'dd.MM.yyyy'"
              :readonly="false"
            />

            <FieldTime
              v-else-if="targetType === 'time'"
              v-model="draft.outputValue"
              v-bind="selectedTarget?.field?.constraints || {}"
              :readonly="false"
            />

            <input
              v-else
              v-model="draft.outputValue"
              :type="targetInputType"
              :disabled="!draft.targetFieldKey"
              placeholder="Output value"
            />
          </label>
        </div>

        <div class="policy-card">
          <label class="check-row">
            <input type="checkbox" v-model="draft.overwriteManualInputs" />
            <span>
              <strong>Overwrite existing values</strong>
              <small>When enabled, a matching rule replaces any value already stored in the target.</small>
            </span>
          </label>

          <label v-if="draft.overwriteManualInputs" class="check-row nested">
            <input type="checkbox" v-model="draft.clearWhenNoMatch" />
            <span>
              <strong>Clear the target when no rule matches</strong>
              <small>Keeps the target synchronized with the currently matching rule.</small>
            </span>
          </label>

          <p class="policy-note">
            Assignment targets are read-only during data entry. Without overwrite enabled,
            the rule fills the target only when it is empty.
          </p>
        </div>

        <div class="condition-head">
          <div>
            <h3>Conditions</h3>
            <p>The first matching assignment for a target field wins.</p>
          </div>
          <select v-model="draft.match">
            <option value="all">All conditions (AND)</option>
            <option value="any">Any condition (OR)</option>
          </select>
        </div>

        <div class="conditions">
          <div
            v-for="(condition, index) in draft.conditions"
            :key="condition.id"
            class="condition-card"
          >
            <div class="condition-title">
              <strong>Condition {{ index + 1 }}</strong>
              <button
                type="button"
                class="icon-btn"
                :disabled="draft.conditions.length === 1"
                @click="removeCondition(index)"
              >
                ×
              </button>
            </div>

            <div class="condition-grid">
              <label class="field-block">
                <span>Source field</span>
                <select v-model="condition.sourceFieldKey" @change="onSourceChanged(condition)">
                  <option value="">Select source field…</option>
                  <optgroup
                    v-for="section in sourceFieldTree"
                    :key="section.key"
                    :label="section.title"
                  >
                    <option
                      v-for="field in section.fields"
                      :key="field.key"
                      :value="field.key"
                    >
                      {{ field.label }}
                    </option>
                  </optgroup>
                </select>
              </label>

              <label class="field-block">
                <span>Operator</span>
                <select v-model="condition.operator" @change="onOperatorChanged(condition)">
                  <option
                    v-for="operator in operatorsForCondition(condition)"
                    :key="operator.value"
                    :value="operator.value"
                  >
                    {{ operator.label }}
                  </option>
                </select>
              </label>

              <template v-if="!operatorNeedsNoValue(condition.operator)">
                <label class="field-block">
                  <span>{{ condition.operator === "between" ? "From" : "Compare value" }}</span>
                  <select
                    v-if="sourceIsChoice(condition)"
                    v-model="condition.value"
                  >
                    <option value="">Select…</option>
                    <option
                      v-for="option in sourceOptions(condition)"
                      :key="option"
                      :value="option"
                    >
                      {{ option }}
                    </option>
                  </select>
                  <select
                    v-else-if="sourceType(condition) === 'checkbox'"
                    v-model="condition.value"
                  >
                    <option :value="true">Checked</option>
                    <option :value="false">Unchecked</option>
                  </select>
                  <DateFormatPicker
                    v-else-if="sourceType(condition) === 'date'"
                    v-model="condition.value"
                    :format="sourceMeta(condition)?.field?.constraints?.dateFormat || 'dd.MM.yyyy'"
                    :placeholder="sourceMeta(condition)?.field?.constraints?.dateFormat || 'dd.MM.yyyy'"
                    :readonly="false"
                  />
                  <FieldTime
                    v-else-if="sourceType(condition) === 'time'"
                    v-model="condition.value"
                    v-bind="sourceMeta(condition)?.field?.constraints || {}"
                    :readonly="false"
                  />
                  <input
                    v-else
                    v-model="condition.value"
                    :type="inputTypeForSource(condition)"
                  />
                </label>

                <label v-if="condition.operator === 'between'" class="field-block">
                  <span>To</span>
                  <DateFormatPicker
                    v-if="sourceType(condition) === 'date'"
                    v-model="condition.valueTo"
                    :format="sourceMeta(condition)?.field?.constraints?.dateFormat || 'dd.MM.yyyy'"
                    :placeholder="sourceMeta(condition)?.field?.constraints?.dateFormat || 'dd.MM.yyyy'"
                    :readonly="false"
                  />
                  <FieldTime
                    v-else-if="sourceType(condition) === 'time'"
                    v-model="condition.valueTo"
                    v-bind="sourceMeta(condition)?.field?.constraints || {}"
                    :readonly="false"
                  />
                  <input
                    v-else
                    v-model="condition.valueTo"
                    :type="inputTypeForSource(condition)"
                  />
                </label>
              </template>
            </div>
          </div>
        </div>

        <button type="button" class="btn-secondary add-condition" @click="addCondition">
          + Add condition
        </button>

        <div v-if="validationMessages.length" class="validation-box">
          <strong>Please review</strong>
          <ul>
            <li v-for="message in validationMessages" :key="message">{{ message }}</li>
          </ul>
        </div>
      </section>

      <section class="panel saved-panel">
        <div class="saved-head">
          <div>
            <h3>Saved assignments</h3>
            <p>Rules are evaluated from top to bottom for each target field.</p>
          </div>
          <span class="count-chip">{{ rules.length }}</span>
        </div>

        <div v-if="!rules.length" class="empty-state">
          No value assignments configured.
        </div>

        <div v-else class="saved-rules">
          <article v-for="(rule, index) in rules" :key="rule.id" class="saved-rule">
            <div class="saved-rule-head">
              <div>
                <strong>{{ rule.name || `Assignment ${index + 1}` }}</strong>
                <p>{{ ruleSummary(rule) }}</p>
              </div>
              <div class="rule-actions">
                <button type="button" class="btn-mini" :disabled="index === 0" @click="moveRule(index, -1)">↑</button>
                <button type="button" class="btn-mini" :disabled="index === rules.length - 1" @click="moveRule(index, 1)">↓</button>
                <button type="button" class="btn-mini" @click="editRule(rule)">Edit</button>
                <button type="button" class="btn-mini danger" @click="deleteRule(rule.id)">Delete</button>
              </div>
            </div>
            <div class="rule-badges">
              <span>{{ rule.match === "any" ? "OR" : "AND" }}</span>
              <span>{{ rule.overwriteManualInputs ? "Overwrite" : "Fill when empty" }}</span>
              <span>{{ rule.enabled === false ? "Disabled" : "Enabled" }}</span>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import DateFormatPicker from "@/components/DateFormatPicker.vue";
import FieldTime from "@/components/fields/FieldTime.vue";

export default {
  name: "LogicValueAssignmentsRoute",
  components: {
    DateFormatPicker,
    FieldTime,
  },
  props: {
    form: { type: Object, required: true },
  },
  emits: ["back-to-builder", "update-form-structure", "update-logic"],

  data() {
    return {
      localForm: this.normalizeForm(this.form),
      rules: [],
      draft: this.emptyRule(),
      editingRuleId: null,
    };
  },

  computed: {
    allFields() {
      const fields = [];
      (this.localForm.sections || []).forEach((section, sectionIndex) => {
        (section.fields || []).forEach((field, fieldIndex) => {
          const type = String(field?.type || "text").toLowerCase();
          if (type === "button") return;
          fields.push({
            key: String(field?._id || field?.id || field?.name || `section_${sectionIndex}_field_${fieldIndex}`),
            label: field?.label || field?.name || `Field ${fieldIndex + 1}`,
            sectionTitle: section?.title || `Section ${sectionIndex + 1}`,
            sectionIndex,
            fieldIndex,
            type,
            field,
          });
        });
      });
      return fields;
    },

    sourceFields() {
      return this.allFields.filter((field) => !["file", "table"].includes(field.type));
    },

    targetFields() {
      return this.allFields.filter((field) =>
        ["text", "textarea", "number", "select", "radio", "checkbox", "date", "time", "slider"].includes(field.type)
      );
    },

    sourceFieldTree() {
      return this.groupFields(this.sourceFields);
    },

    targetFieldTree() {
      return this.groupFields(this.targetFields);
    },

    selectedTarget() {
      return this.targetFields.find((field) => field.key === this.draft.targetFieldKey) || null;
    },

    targetType() {
      return this.selectedTarget?.type || "";
    },

    targetIsChoice() {
      return ["select", "radio"].includes(this.targetType);
    },

    targetOptions() {
      return this.optionsForField(this.selectedTarget?.field);
    },

    targetInputType() {
      if (["number", "slider"].includes(this.targetType)) return "number";
      if (this.targetType === "date") return "date";
      if (this.targetType === "time") return "time";
      return "text";
    },

    validationMessages() {
      const messages = [];
      if (!this.draft.targetFieldKey) messages.push("Select a target field.");
      if (
        this.draft.targetFieldKey &&
        (this.localForm?.logic?.calculations || []).some(
          (rule) => String(rule?.target || "") === String(this.draft.targetFieldKey)
        )
      ) {
        messages.push("The target field is already controlled by a calculation.");
      }
      if (
        this.draft.outputValue === "" ||
        this.draft.outputValue === null ||
        typeof this.draft.outputValue === "undefined"
      ) {
        messages.push("Select or enter an output value.");
      }
      if (!this.draft.conditions.length) messages.push("Add at least one condition.");
      this.draft.conditions.forEach((condition, index) => {
        if (!condition.sourceFieldKey) messages.push(`Condition ${index + 1}: select a source field.`);
        if (
          condition.sourceFieldKey &&
          String(condition.sourceFieldKey) === String(this.draft.targetFieldKey)
        ) {
          messages.push(`Condition ${index + 1}: the target field cannot depend on itself.`);
        }
        if (!condition.operator) messages.push(`Condition ${index + 1}: select an operator.`);
        if (
          !this.operatorNeedsNoValue(condition.operator) &&
          (condition.value === "" || condition.value === null || typeof condition.value === "undefined")
        ) {
          messages.push(`Condition ${index + 1}: enter a compare value.`);
        }
        if (
          condition.operator === "between" &&
          (condition.valueTo === "" || condition.valueTo === null || typeof condition.valueTo === "undefined")
        ) {
          messages.push(`Condition ${index + 1}: enter the upper compare value.`);
        }
      });
      if (this.assignmentGraphHasCycle()) {
        messages.push("The assignment rules contain a circular dependency.");
      }
      return Array.from(new Set(messages));
    },

    canSaveRule() {
      return this.validationMessages.length === 0;
    },
  },

  watch: {
    form: {
      deep: true,
      handler(next) {
        this.localForm = this.normalizeForm(next);
        this.loadRules();
      },
    },
  },

  mounted() {
    this.loadRules();
  },

  methods: {
    uuid() {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
      return `assignment_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    },

    normalizeForm(form) {
      const next = JSON.parse(JSON.stringify(form || {}));
      if (!Array.isArray(next.sections)) next.sections = [];
      if (!next.logic || typeof next.logic !== "object") next.logic = {};
      if (!Array.isArray(next.logic.calculations)) next.logic.calculations = [];
      if (!Array.isArray(next.logic.conditions)) next.logic.conditions = [];
      if (!Array.isArray(next.logic.valueAssignments)) next.logic.valueAssignments = [];
      if (!next.logic.version) next.logic.version = 2;
      return next;
    },

    emptyCondition() {
      return {
        id: this.uuid(),
        sourceFieldKey: "",
        operator: "eq",
        value: "",
        valueTo: "",
      };
    },

    emptyRule() {
      return {
        id: this.uuid(),
        name: "",
        targetFieldKey: "",
        outputValue: "",
        match: "all",
        conditions: [this.emptyCondition()],
        overwriteManualInputs: false,
        clearWhenNoMatch: false,
        enabled: true,
      };
    },

    loadRules() {
      this.rules = JSON.parse(JSON.stringify(this.localForm?.logic?.valueAssignments || []));
      this.rules.forEach((rule, index) => {
        rule.priority = index;
        if (!Array.isArray(rule.conditions) || !rule.conditions.length) {
          rule.conditions = [this.emptyCondition()];
        }
      });
    },

    groupFields(fields) {
      const groups = [];
      const map = new Map();
      fields.forEach((field) => {
        if (!map.has(field.sectionTitle)) {
          const group = {
            key: `${field.sectionIndex}-${field.sectionTitle}`,
            title: field.sectionTitle,
            fields: [],
          };
          map.set(field.sectionTitle, group);
          groups.push(group);
        }
        map.get(field.sectionTitle).fields.push(field);
      });
      return groups;
    },

    optionsForField(field) {
      const options = field?.options || field?.constraints?.options || [];
      return Array.isArray(options)
        ? options
            .map((option) =>
              typeof option === "object"
                ? String(option?.value ?? option?.label ?? option?.name ?? "")
                : String(option)
            )
            .filter(Boolean)
        : [];
    },

    sourceMeta(condition) {
      return this.sourceFields.find((field) => field.key === condition.sourceFieldKey) || null;
    },

    sourceType(condition) {
      return this.sourceMeta(condition)?.type || "";
    },

    sourceIsChoice(condition) {
      return ["select", "radio"].includes(this.sourceType(condition));
    },

    sourceOptions(condition) {
      return this.optionsForField(this.sourceMeta(condition)?.field);
    },

    inputTypeForSource(condition) {
      const type = this.sourceType(condition);
      if (["number", "slider"].includes(type)) return "number";
      if (type === "date") return "date";
      if (type === "time") return "time";
      return "text";
    },

    operatorsForCondition(condition) {
      const type = this.sourceType(condition);
      const common = [
        { value: "eq", label: "Equals" },
        { value: "neq", label: "Does not equal" },
        { value: "empty", label: "Is empty" },
        { value: "not_empty", label: "Is not empty" },
      ];
      if (["number", "slider", "date", "time"].includes(type)) {
        return [
          ...common,
          { value: "gt", label: "Greater than" },
          { value: "gte", label: "Greater than or equal" },
          { value: "lt", label: "Less than" },
          { value: "lte", label: "Less than or equal" },
          { value: "between", label: "Between" },
        ];
      }
      if (["text", "textarea"].includes(type)) {
        return [
          ...common,
          { value: "contains", label: "Contains" },
          { value: "not_contains", label: "Does not contain" },
          { value: "starts_with", label: "Starts with" },
          { value: "ends_with", label: "Ends with" },
        ];
      }
      return common;
    },

    operatorNeedsNoValue(operator) {
      return ["empty", "is_empty", "not_empty", "is_not_empty"].includes(operator);
    },

    onTargetChanged() {
      if (this.targetType === "checkbox") this.draft.outputValue = true;
      else this.draft.outputValue = "";
    },

    onSourceChanged(condition) {
      condition.operator = "eq";
      condition.value = this.sourceType(condition) === "checkbox" ? true : "";
      condition.valueTo = "";
    },

    onOperatorChanged(condition) {
      if (this.operatorNeedsNoValue(condition.operator)) {
        condition.value = "";
        condition.valueTo = "";
      } else if (condition.operator !== "between") {
        condition.valueTo = "";
      }
    },

    addCondition() {
      this.draft.conditions.push(this.emptyCondition());
    },

    removeCondition(index) {
      if (this.draft.conditions.length <= 1) return;
      this.draft.conditions.splice(index, 1);
    },

    saveRule() {
      if (!this.canSaveRule) return;
      const rule = JSON.parse(JSON.stringify(this.draft));
      const existingIndex = this.rules.findIndex((item) => item.id === this.editingRuleId);
      if (existingIndex >= 0) this.rules.splice(existingIndex, 1, rule);
      else this.rules.push(rule);
      this.persistRules();
      this.resetEditor();
    },

    editRule(rule) {
      this.editingRuleId = rule.id;
      this.draft = JSON.parse(JSON.stringify(rule));
      if (!Array.isArray(this.draft.conditions) || !this.draft.conditions.length) {
        this.draft.conditions = [this.emptyCondition()];
      }
    },

    deleteRule(id) {
      this.rules = this.rules.filter((rule) => rule.id !== id);
      this.persistRules();
      if (this.editingRuleId === id) this.resetEditor();
    },

    moveRule(index, direction) {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= this.rules.length) return;
      const moved = this.rules.splice(index, 1)[0];
      this.rules.splice(nextIndex, 0, moved);
      this.persistRules();
    },

    resetEditor() {
      this.editingRuleId = null;
      this.draft = this.emptyRule();
    },

    persistRules() {
      this.rules.forEach((rule, index) => {
        rule.priority = index;
      });
      this.localForm.logic.valueAssignments = JSON.parse(JSON.stringify(this.rules));
      this.$emit("update-form-structure", JSON.parse(JSON.stringify(this.localForm)));
      this.$emit("update-logic", JSON.parse(JSON.stringify(this.localForm.logic)));
    },

    goBack() {
      this.persistRules();
      this.$emit("back-to-builder");
    },

    fieldLabel(key) {
      return this.allFields.find((field) => field.key === String(key))?.label || String(key || "Field");
    },

    displayValue(value) {
      if (typeof value === "boolean") return value ? "Checked" : "Unchecked";
      return String(value ?? "");
    },

    ruleSummary(rule) {
      const target = this.fieldLabel(rule.targetFieldKey);
      const conditions = (rule.conditions || [])
        .map((condition) => {
          const source = this.fieldLabel(condition.sourceFieldKey);
          if (this.operatorNeedsNoValue(condition.operator)) {
            return `${source} ${condition.operator}`;
          }
          if (condition.operator === "between") {
            return `${source} between ${condition.value} and ${condition.valueTo}`;
          }
          return `${source} ${condition.operator} ${this.displayValue(condition.value)}`;
        })
        .join(rule.match === "any" ? " OR " : " AND ");
      return `If ${conditions}, set ${target} to ${this.displayValue(rule.outputValue)}.`;
    },

    assignmentGraphHasCycle() {
      if (!this.draft.targetFieldKey) return false;

      const candidate = JSON.parse(JSON.stringify(this.draft));
      const rules = this.rules
        .filter((rule) => rule.id !== this.editingRuleId)
        .concat(candidate);
      const graph = new Map();

      rules.forEach((rule) => {
        const target = String(rule?.targetFieldKey || "");
        if (!target) return;
        if (!graph.has(target)) graph.set(target, new Set());

        (rule.conditions || []).forEach((condition) => {
          const source = String(condition?.sourceFieldKey || "");
          if (source) graph.get(target).add(source);
        });
      });

      const visiting = new Set();
      const visited = new Set();

      const visit = (node) => {
        if (visiting.has(node)) return true;
        if (visited.has(node)) return false;

        visiting.add(node);
        for (const source of graph.get(node) || []) {
          if (graph.has(source) && visit(source)) return true;
        }
        visiting.delete(node);
        visited.add(node);
        return false;
      };

      return Array.from(graph.keys()).some((node) => visit(node));
    },
  },
};
</script>

<style scoped>
.assignment-page {
  height: 100%;
  min-height: 0;
  padding: 18px;
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
  background: #f6f8fb;
  color: #111827;
}

.assignment-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 16px;
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

h2, h3, p { margin-top: 0; }
.assignment-topbar h2 { margin-bottom: 4px; }
.assignment-topbar p, .saved-head p, .condition-head p { margin-bottom: 0; color: #6b7280; }

.topbar-actions, .rule-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.assignment-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 16px;
  margin-top: 16px;
  min-height: 0;
  align-items: start;
}

.panel {
  padding: 18px;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #fff;
}

.editor-panel {
  align-self: start;
  min-height: 0;
}

.grid-two, .condition-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.condition-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }

.field-block {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
}

.field-block > span {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}

input, select {
  width: 100%;
  min-height: 38px;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
}

.policy-card, .condition-card, .saved-rule {
  margin: 12px 0;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.check-row input { width: auto; min-height: auto; margin-top: 3px; }
.check-row span { display: grid; gap: 3px; }
.check-row small, .policy-note { color: #6b7280; line-height: 1.4; }
.check-row.nested { margin: 12px 0 0 24px; }
.policy-note { margin: 12px 0 0; font-size: 12px; }

.condition-head, .saved-head, .condition-title, .saved-rule-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.condition-head { margin-top: 20px; }
.condition-head select { width: auto; min-width: 190px; }
.condition-title { margin-bottom: 12px; }

.add-condition { margin-top: 4px; }
.validation-box {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff1f2;
  color: #991b1b;
}
.validation-box ul { margin-bottom: 0; }

.saved-panel {
  align-self: start;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 190px);
  min-height: 0;
  overflow: hidden;
}

.saved-rules {
  display: grid;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}
.saved-rule { margin: 0; background: #fff; }
.saved-rule p { margin: 5px 0 0; color: #4b5563; line-height: 1.4; }
.rule-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.rule-badges span, .count-chip {
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 11px;
  font-weight: 700;
}

.empty-state {
  padding: 28px 10px;
  color: #6b7280;
  text-align: center;
}

button {
  border-radius: 8px;
  cursor: pointer;
}
.btn-primary, .btn-secondary, .btn-back, .btn-mini, .icon-btn {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  background: #fff;
}
.btn-primary { border-color: #2563eb; background: #2563eb; color: #fff; }
.btn-primary:disabled, button:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-mini, .icon-btn { padding: 5px 8px; font-size: 12px; }
.danger { color: #b91c1c; }

@media (max-width: 1050px) {
  .assignment-workspace { grid-template-columns: 1fr; }
  .condition-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 700px) {
  .assignment-topbar { grid-template-columns: 1fr; }
  .assignment-workspace, .grid-two, .condition-grid { grid-template-columns: 1fr; }
  .condition-head, .saved-head, .saved-rule-head { flex-direction: column; }
}
</style>
