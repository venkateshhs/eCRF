<template>
  <div class="logic-calc-page">
    <div class="topbar">
      <button
        class="btn-back logic-back-btn"
        @click="goBack"
        title="Go Back"
      >
        Back
      </button>

      <div class="title-wrap">
        <h2>Calculations</h2>
        <p>
          Build expressions by clicking fields, operators, functions, and parentheses.
          Supports numeric fields and scored non-numeric fields.
        </p>
      </div>

      <div class="topbar-actions">
        <button class="btn-secondary" @click="resetBuilder">Reset</button>
        <button class="btn-primary" :disabled="!canSave" @click="saveCalculation">
          {{ editingRuleId ? "Update Calculation" : "Save Calculation" }}
        </button>
      </div>
    </div>

    <div class="workspace">
      <!-- LEFT -->
      <section class="panel panel-left">
        <div class="panel-head">
          <h3>1) Inputs</h3>
          <div class="sub">Click a field to insert it into the expression</div>
        </div>

        <div class="toolbar">
          <input
            v-model="fieldSearch"
            class="search"
            placeholder="Search fields…"
            aria-label="Search fields"
          />
          <button class="btn-mini" @click="refreshSymbolUsages">Refresh</button>
        </div>

        <div class="picker-list">
          <details
            v-for="sec in filteredFieldTree"
            :key="sec.key"
            class="group"
            :open="sec.openByDefault"
          >
            <summary class="group-summary">
              <span class="group-title">{{ sec.sectionTitle }}</span>
              <span class="group-count">{{ sec.fields.length }}</span>
            </summary>

            <div class="field-list">
              <button
                v-for="f in sec.fields"
                :key="f.id"
                type="button"
                class="field-row field-row-btn"
                :title="f.path"
                @click="insertFieldIntoExpression(f)"
              >
                <div class="field-meta">
                  <div class="field-label">{{ f.label }}</div>
                  <div class="field-sub">
                    {{ f.typeLabel }}
                    <span v-if="isScorableField(f)" class="score-badge">scoreable</span>
                  </div>
                </div>

                <div class="field-insert-name">{{ suggestedSymbolForField(f) }}</div>
              </button>
            </div>
          </details>

          <div v-if="!filteredFieldTree.length" class="empty">No fields found.</div>
        </div>
      </section>

      <!-- MIDDLE -->
      <section class="panel panel-middle">
        <div class="panel-head">
          <h3>2) Expression</h3>
          <div class="sub">Click fields/operators or type directly</div>
        </div>

        <div class="expr-builder">
          <div class="token-toolbar">
            <div class="toolbar-group">
              <button v-for="op in operatorButtons" :key="op" class="btn-token" @click="insertToken(op)">
                {{ op }}
              </button>
            </div>

            <div class="toolbar-group">
              <button v-for="fn in functionButtons" :key="fn.token" class="btn-token fn" @click="insertToken(fn.token)">
                {{ fn.label }}
              </button>
            </div>

            <div class="toolbar-group">
              <button class="btn-token" @click="insertToken(' 0 ')">0</button>
              <button class="btn-token" @click="insertToken(' 1 ')">1</button>
              <button class="btn-token" @click="insertToken(' 100 ')">100</button>
              <button class="btn-token" @click="insertToken(' pi ')">π</button>
            </div>
          </div>

          <div class="expr-editor-wrap">
            <textarea
              ref="expressionInput"
              v-model="expression"
              class="expr-editor"
              placeholder="Example: weight_kg / ((height_cm / 100)^2)"
              @click="captureCursor"
              @keyup="captureCursor"
              @focus="captureCursor"
            />
          </div>

          <div class="expr-actions">
            <button class="btn-mini" @click="removeLastToken">Backspace</button>
            <button class="btn-mini" @click="clearExpression" :disabled="!expression.trim()">Clear</button>
            <button class="btn-mini" @click="formatExpression">Format</button>
            <button class="btn-mini" @click="validateExpressionNow">Validate</button>
          </div>

          <div class="preview-card">
            <div class="preview-title">Expression preview</div>
            <div v-if="expression.trim()" class="formula">{{ expression }}</div>
            <div v-else class="empty-small">Build an expression.</div>
          </div>

          <div class="preview-card">
            <div class="preview-title">Validation</div>
            <div v-if="expressionValidation.ok" class="valid-box">
              Expression looks valid.
            </div>
            <div v-else class="warn-box">
              <div class="warn-title">Issues</div>
              <ul>
                <li v-for="(m, i) in expressionValidation.messages" :key="i">{{ m }}</li>
              </ul>
            </div>
          </div>

          <div class="preview-card">
            <div class="preview-title">Detected symbols</div>
            <div v-if="usedSymbols.length" class="chips">
              <span v-for="sym in usedSymbols" :key="sym" class="chip">{{ sym }}</span>
            </div>
            <div v-else class="empty-small">No field symbols detected yet.</div>
          </div>
        </div>
      </section>

      <!-- RIGHT -->
      <section class="panel panel-right">
        <div class="panel-head">
          <h3>3) Result + scoring</h3>
          <div class="sub">Choose result field and define scoring for non-numeric inputs</div>
        </div>

        <div class="target-mode">
          <label class="mode-pill" :class="{ active: targetMode === 'existing' }">
            <input type="radio" value="existing" v-model="targetMode" />
            <span>Use existing field</span>
          </label>

          <label class="mode-pill" :class="{ active: targetMode === 'new' }">
            <input type="radio" value="new" v-model="targetMode" />
            <span>Create new field</span>
          </label>
        </div>

        <div v-if="targetMode === 'existing'" class="target-block">
          <div class="toolbar">
            <input
              v-model="targetSearch"
              class="search"
              placeholder="Search target fields…"
              aria-label="Search target fields"
            />
            <button class="btn-mini" @click="targetFieldId = ''" :disabled="!targetFieldId">
              Clear
            </button>
          </div>

          <div class="picker-list">
            <details
              v-for="sec in filteredTargetTree"
              :key="sec.key"
              class="group"
              :open="sec.openByDefault"
            >
              <summary class="group-summary">
                <span class="group-title">{{ sec.sectionTitle }}</span>
                <span class="group-count">{{ sec.fields.length }}</span>
              </summary>

              <div class="field-list">
                <label
                  v-for="f in sec.fields"
                  :key="f.id"
                  class="field-row"
                  :title="f.path"
                >
                  <input
                    type="radio"
                    name="targetField"
                    :value="f.id"
                    v-model="targetFieldId"
                  />
                  <div class="field-meta">
                    <div class="field-label">{{ f.label }}</div>
                    <div class="field-sub">{{ f.typeLabel }}</div>
                  </div>
                </label>
              </div>
            </details>

            <div v-if="!filteredTargetTree.length" class="empty">No target fields found.</div>
          </div>
        </div>

        <div v-else class="target-block">
          <div class="form-block">
            <label class="field-block">
              <span class="field-block-label">Section</span>
              <select v-model="newTargetSectionId" class="select">
                <option disabled value="">Select section…</option>
                <option v-for="sec in sectionOptions" :key="sec.id" :value="sec.id">
                  {{ sec.title }}
                </option>
              </select>
            </label>

            <label class="field-block">
              <span class="field-block-label">New field name</span>
              <input
                v-model="newTargetLabel"
                class="search"
                placeholder="e.g. BMI or Total Score"
              />
            </label>

            <label class="field-block">
              <span class="field-block-label">Decimals</span>
              <input
                v-model.number="resultDecimals"
                type="number"
                min="0"
                max="10"
                class="search"
                placeholder="2"
              />
            </label>

            <div class="new-field-note">
              A new <strong>read-only calculated number field</strong> will be created.
            </div>
          </div>
        </div>

        <div class="form-block">
          <label class="field-block">
            <span class="field-block-label">Blank handling</span>
            <select v-model="blankPolicy" class="select">
              <option value="strict">Strict (missing input => no result)</option>
              <option value="zero">Zero (missing numeric/scored => 0)</option>
            </select>
          </label>
        </div>

        <div class="preview-card">
          <div class="preview-title">Scoring for non-numeric symbols</div>

          <div v-if="!scoringSymbols.length" class="empty-small">
            No scored non-numeric symbols used in the expression.
          </div>

          <div v-for="sym in scoringSymbols" :key="sym.symbol" class="score-card">
            <div class="score-head">
              <div class="score-title">{{ sym.field.label }}</div>
              <div class="score-sub">{{ sym.symbol }} · {{ sym.field.typeLabel }}</div>
            </div>

            <div v-if="sym.field.type === 'checkbox'" class="checkbox-score-grid">
              <label class="field-block">
                <span class="field-block-label">Unchecked</span>
                <input
                  v-model.number="symbolMapDraft[sym.symbol].mappings.__unchecked"
                  type="number"
                  class="search"
                />
              </label>

              <label class="field-block">
                <span class="field-block-label">Checked</span>
                <input
                  v-model.number="symbolMapDraft[sym.symbol].mappings.__checked"
                  type="number"
                  class="search"
                />
              </label>
            </div>

            <div v-else class="score-options">
              <div
                v-for="opt in getFieldOptions(sym.field)"
                :key="String(opt)"
                class="score-row"
              >
                <div class="score-opt">{{ opt }}</div>
                <input
                  type="number"
                  class="score-input"
                  :value="getMappingValue(sym.symbol, opt)"
                  @input="setMappingValue(sym.symbol, opt, $event.target.value)"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="preview-card">
          <div class="preview-title">Result summary</div>

          <div class="preview-row">
            <div class="preview-k">Target</div>
            <div class="preview-v">
              <template v-if="targetMode === 'existing'">
                {{ targetLabel || "—" }}
              </template>
              <template v-else>
                {{ newTargetPreview || "—" }}
              </template>
            </div>
          </div>

          <div class="preview-row">
            <div class="preview-k">Output</div>
            <div class="preview-v">Number</div>
          </div>

          <div class="preview-row">
            <div class="preview-k">Blank rule</div>
            <div class="preview-v">{{ blankPolicy }}</div>
          </div>

          <div class="preview-row">
            <div class="preview-k">Decimals</div>
            <div class="preview-v">{{ resultDecimals }}</div>
          </div>

          <div v-if="warnings.length" class="warn-box">
            <div class="warn-title">Warnings</div>
            <ul>
              <li v-for="(w, i) in warnings" :key="i">{{ w }}</li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <div class="saved-block">
      <div class="saved-head">
        <h3>Saved calculations</h3>
      </div>

      <div v-if="!calcRules.length" class="empty">
        No calculations saved yet.
      </div>

      <div v-else class="rules">
        <div v-for="r in calcRules" :key="r.id" class="rule">
          <div class="rule-top">
            <div class="rule-title">{{ ruleSummary(r) }}</div>
            <div class="rule-actions">
              <button class="btn-mini" @click="loadRuleToEditor(r)">Edit</button>
              <button class="btn-mini danger" @click="deleteRule(r.id)">Delete</button>
            </div>
          </div>
          <div class="rule-sub">{{ ruleFormula(r) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
/* eslint-disable */
import { create, all } from "mathjs";

const math = create(all, {});

try {
  math.import({
    ifElse: (cond, a, b) => (cond ? a : b),
    nz: (v, fallback = 0) => (v === null || v === undefined || v === "" ? fallback : v),
    mean: (...args) => {
      const arr = Array.isArray(args[0]) && args.length === 1 ? args[0] : args;
      const nums = arr.map(Number).filter(Number.isFinite);
      if (!nums.length) return 0;
      return nums.reduce((a, b) => a + b, 0) / nums.length;
    }
  }, { override: true });
} catch {}

const RESERVED_SYMBOLS = new Set([
  "e", "E", "pi", "PI", "true", "false", "null", "undefined",
  "abs", "ceil", "floor", "round", "sqrt", "pow", "min", "max",
  "mean", "ifElse", "nz", "mod"
]);

export default {
  name: "LogicCalculationsRoute",
  props: {
    form: {
      type: Object,
      required: true
    }
  },
  emits: ["back-to-builder", "update-logic", "update-form-structure"],

  data() {
    return {
      forms: [],
      formIndex: 0,

      allFields: [],
      fieldSearch: "",
      targetSearch: "",

      expression: "",
      symbolMapDraft: {},
      targetMode: "existing",
      targetFieldId: "",
      newTargetSectionId: "",
      newTargetLabel: "",
      resultDecimals: 2,
      blankPolicy: "strict",

      calcRules: [],
      editingRuleId: null,

      cursorStart: 0,
      cursorEnd: 0,

      expressionValidation: {
        ok: false,
        messages: ["Expression is empty."]
      },

      operatorButtons: [" + ", " - ", " * ", " / ", " ^ ", " % ", " ( ", " ) ", " , "],
      functionButtons: [
        { label: "mean()", token: "mean()" },
        { label: "min()", token: "min()" },
        { label: "max()", token: "max()" },
        { label: "round()", token: "round()" },
        { label: "abs()", token: "abs()" },
        { label: "sqrt()", token: "sqrt()" },
        { label: "ifElse()", token: "ifElse()" },
        { label: "nz()", token: "nz()" }
      ]
    };
  },

  computed: {
    currentForm() {
      return this.forms[this.formIndex] || { sections: [], logic: { version: 2, calculations: [], conditions: [] } };
    },

    sectionOptions() {
      const form = this.currentForm;
      return (form.sections || []).map((sec, idx) => ({
        id: sec._id || `section_${idx}`,
        title: sec.title || `Section ${idx + 1}`
      }));
    },

    filteredFieldTree() {
      return this.buildTreeFromFields(this.allFields, this.fieldSearch);
    },

    filteredTargetTree() {
      return this.buildTreeFromFields(this.allFields, this.targetSearch);
    },

    usedSymbols() {
      return this.extractSymbolsFromExpression(this.expression);
    },

    scoringSymbols() {
      return this.usedSymbols
        .map((symbol) => {
          const def = this.symbolMapDraft[symbol];
          if (!def) return null;
          const field = this.allFields.find((f) => f.id === def.fieldId);
          if (!field) return null;
          if (def.valueType !== "mapped_choice" && def.valueType !== "boolean_score") return null;
          return { symbol, def, field };
        })
        .filter(Boolean);
    },

    targetLabel() {
      const f = this.allFields.find((x) => x.id === this.targetFieldId);
      return f ? `${f.label} — ${f.sectionTitle}` : "";
    },

    newTargetPreview() {
      const sec = this.sectionOptions.find((s) => s.id === this.newTargetSectionId);
      if (!sec && !this.newTargetLabel.trim()) return "";
      return `${this.newTargetLabel || "New Calculated Field"}${sec ? ` — ${sec.title}` : ""}`;
    },

    warnings() {
      const out = [];

      if (!this.expression.trim()) out.push("Expression is empty.");

      const undefinedSymbols = this.usedSymbols.filter((sym) => !this.symbolMapDraft[sym]);
      if (undefinedSymbols.length) {
        out.push(`Some symbols are not mapped to fields: ${undefinedSymbols.join(", ")}`);
      }

      if (this.targetMode === "existing") {
        if (this.targetFieldId) {
          const targetIsSource = Object.values(this.symbolMapDraft).some(
            (x) => String(x?.fieldId || "") === String(this.targetFieldId)
          );
          if (targetIsSource) out.push("Result field is also used as an input.");
        }

        const t = this.allFields.find((f) => f.id === this.targetFieldId);
        if (t && t.type && t.type !== "number") {
          out.push(`Existing result field type is "${t.type}". Number field is recommended.`);
        }
      }

      this.scoringSymbols.forEach((sym) => {
        if (sym.field.type === "checkbox") {
          const m = sym.def.mappings || {};
          if (typeof m.__checked === "undefined" || typeof m.__unchecked === "undefined") {
            out.push(`Checkbox scoring for "${sym.field.label}" is incomplete.`);
          }
        } else {
          const opts = this.getFieldOptions(sym.field);
          const missing = opts.filter((opt) => {
            const v = sym.def.mappings?.[String(opt)];
            return v === "" || v === null || typeof v === "undefined";
          });
          if (missing.length) {
            out.push(`Scoring for "${sym.field.label}" is incomplete.`);
          }
        }
      });

      return out;
    },

    canSave() {
      if (!this.expression.trim()) return false;
      if (!this.expressionValidation.ok) return false;

      if (this.targetMode === "existing") {
        return !!this.targetFieldId;
      }

      return !!this.newTargetSectionId && !!String(this.newTargetLabel || "").trim();
    }
  },

  watch: {
    form: {
      deep: true,
      handler(newForm) {
        if (!newForm || typeof newForm !== "object") return;

        console.log("[LogicCalc] prop form changed =", JSON.parse(JSON.stringify(newForm || {})));
        console.log("[LogicCalc] prop logic changed =", JSON.parse(JSON.stringify(newForm?.logic || {})));

        const next = JSON.parse(JSON.stringify(newForm));
        if (!next.logic || typeof next.logic !== "object") {
          next.logic = { version: 2, calculations: [], conditions: [] };
        }
        if (!Array.isArray(next.logic.calculations)) next.logic.calculations = [];
        if (!Array.isArray(next.logic.conditions)) next.logic.conditions = [];

        this.forms[this.formIndex] = next;
        this.ensurePersistentIds();
        this.buildFieldIndex();
        this.loadCalcRules();
        this.refreshSymbolUsages();
      }
    },

    expression() {
      this.refreshSymbolUsages();
      this.validateExpressionNow();
    }
  },

  mounted() {
      const idx = parseInt(this.$route?.query?.formIndex ?? "0", 10);
      this.formIndex = Number.isFinite(idx) && idx >= 0 ? idx : 0;

      console.log("[LogicCalc] mounted formIndex =", this.formIndex);
      console.log("[LogicCalc] mounted incoming prop form =", JSON.parse(JSON.stringify(this.form || {})));
      console.log("[LogicCalc] mounted incoming prop logic =", JSON.parse(JSON.stringify(this.form?.logic || {})));

      this.loadFormsFromSource();
      this.ensurePersistentIds();
      this.buildFieldIndex();
      this.loadCalcRules();
      this.refreshSymbolUsages();
    },
  methods: {
    goBack() {
      this.persistRules();
      this.emitCurrentFormToParent("goBack");
      this.$emit("back-to-builder");
    },

    loadFormsFromSource() {
      // Always prefer parent prop form as source of truth for the currently open form.
      // Local storage is only fallback support.
      try {
        const parsed = JSON.parse(localStorage.getItem("scratchForms") || "[]");
        this.forms = Array.isArray(parsed) ? parsed : [];
      } catch {
        this.forms = [];
      }

      if (!this.forms.length) this.forms = [{ sections: [], logic: { version: 2, calculations: [], conditions: [] } }];
      while (this.forms.length <= this.formIndex) {
        this.forms.push({ sections: [], logic: { version: 2, calculations: [], conditions: [] } });
      }

      if (this.form && typeof this.form === "object") {
        this.forms[this.formIndex] = JSON.parse(JSON.stringify(this.form));
      } else if (!this.forms[this.formIndex]) {
        this.forms[this.formIndex] = { sections: [], logic: { version: 2, calculations: [], conditions: [] } };
      }

      if (!Array.isArray(this.forms[this.formIndex].sections)) {
        this.forms[this.formIndex].sections = [];
      }

      if (!this.forms[this.formIndex].logic || typeof this.forms[this.formIndex].logic !== "object") {
        this.forms[this.formIndex].logic = { version: 2, calculations: [], conditions: [] };
      }
      if (!Array.isArray(this.forms[this.formIndex].logic.calculations)) {
        this.forms[this.formIndex].logic.calculations = [];
      }
      if (!Array.isArray(this.forms[this.formIndex].logic.conditions)) {
        this.forms[this.formIndex].logic.conditions = [];
      }

      console.log("[LogicCalc] loadFormsFromSource current form =", JSON.parse(JSON.stringify(this.forms[this.formIndex] || {})));
      console.log("[LogicCalc] loadFormsFromSource current logic =", JSON.parse(JSON.stringify(this.forms[this.formIndex]?.logic || {})));
    },

    saveFormsToStorage() {
      localStorage.setItem("scratchForms", JSON.stringify(this.forms));
    },

    emitCurrentFormToParent(reason = "unknown") {
      const currentForm = JSON.parse(JSON.stringify(this.currentForm || {}));
      const currentLogic = JSON.parse(JSON.stringify(currentForm.logic || {
        version: 2,
        calculations: [],
        conditions: []
      }));

      this.$emit("update-form-structure", currentForm);
      this.$emit("update-logic", currentLogic);
    },

    uuid() {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
      return `id_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    },

    ensurePersistentIds() {
      const form = this.currentForm;

      (form.sections || []).forEach((sec) => {
        if (!sec._id) sec._id = this.uuid();
        if (!Array.isArray(sec.fields)) sec.fields = [];

        sec.fields.forEach((f) => {
          if (!f._id) f._id = this.uuid();
          if (!f.constraints || typeof f.constraints !== "object") {
            f.constraints = {};
          }
        });
      });

      if (!form.logic) form.logic = { version: 2, calculations: [], conditions: [] };
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];
      if (!Array.isArray(form.logic.conditions)) form.logic.conditions = [];
      if (!form.logic.version) form.logic.version = 2;

      this.forms[this.formIndex] = form;
      this.saveFormsToStorage();
    },

    buildFieldIndex() {
      const form = this.currentForm;
      const out = [];

      (form.sections || []).forEach((sec, si) => {
        const sectionTitle = sec.title || `Section ${si + 1}`;

        (sec.fields || []).forEach((f, fi) => {
          const id = f._id || f.id || f.field_id || f.uid || f.key || `sec${si}_fld${fi}`;

          out.push({
            id: String(id),
            label: String(f.label || f.name || `Field ${fi + 1}`),
            name: String(f.name || ""),
            type: String(f.type || "text").toLowerCase(),
            typeLabel: this.prettyTypeLabel(String(f.type || "text")),
            sectionTitle,
            path: `${sectionTitle} / ${String(f.label || f.name || `Field ${fi + 1}`)}`,
            field: f
          });
        });
      });

      this.allFields = out.filter((f) => f.type !== "button");
    },

    prettyTypeLabel(t) {
      const map = {
        number: "Number",
        text: "Text",
        textarea: "Text",
        select: "Select",
        radio: "Radio",
        checkbox: "Checkbox",
        date: "Date",
        time: "Time",
        slider: "Slider",
        file: "File"
      };
      return map[String(t || "").toLowerCase()] || String(t || "Field");
    },

    buildTreeFromFields(fields, query) {
      const q = (query || "").trim().toLowerCase();

      const filtered = !q
        ? fields
        : fields.filter((f) => {
            const hay = `${f.label} ${f.sectionTitle} ${f.path} ${f.typeLabel}`.toLowerCase();
            return hay.includes(q);
          });

      const bySection = new Map();
      filtered.forEach((f) => {
        const key = String(f.sectionTitle || "Other");
        if (!bySection.has(key)) bySection.set(key, []);
        bySection.get(key).push(f);
      });

      const sectionOrder = [];
      (this.currentForm?.sections || []).forEach((sec) => {
        const st = String(sec?.title || "");
        if (st) sectionOrder.push(st);
      });

      const out = [];
      const used = new Set();

      sectionOrder.forEach((st) => {
        if (!bySection.has(st)) return;
        used.add(st);
        out.push({
          key: `sec_${st}`,
          sectionTitle: st,
          fields: bySection.get(st),
          openByDefault: !!q
        });
      });

      Array.from(bySection.keys()).forEach((st) => {
        if (used.has(st)) return;
        out.push({
          key: `sec_${st}`,
          sectionTitle: st,
          fields: bySection.get(st),
          openByDefault: !!q
        });
      });

      return out;
    },

    suggestedSymbolForField(f) {
      const raw = String(f.label || f.name || "field")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");

      let base = raw || "field";
      if (/^\d/.test(base)) base = `f_${base}`;

      let next = base;
      let n = 2;
      const used = new Set(Object.keys(this.symbolMapDraft || {}));

      while (used.has(next) && this.symbolMapDraft[next]?.fieldId !== f.id) {
        next = `${base}_${n++}`;
      }

      return next;
    },

    isNumericField(f) {
      return ["number", "slider"].includes(String(f?.type || "").toLowerCase());
    },

    isScorableField(f) {
      return ["select", "radio", "checkbox"].includes(String(f?.type || "").toLowerCase());
    },

    getFieldOptions(fieldMeta) {
      const field = fieldMeta?.field || fieldMeta;
      const opts = field?.options || field?.constraints?.options || [];
      if (Array.isArray(opts)) {
        return opts
          .map((o) => {
            if (typeof o === "string") return o;
            if (o && typeof o === "object") return o.label || o.value || o.name || "";
            return "";
          })
          .filter(Boolean);
      }
      return [];
    },

    captureCursor() {
      const el = this.$refs.expressionInput;
      if (!el) return;
      this.cursorStart = el.selectionStart ?? 0;
      this.cursorEnd = el.selectionEnd ?? 0;
    },

    setCursor(pos) {
      this.$nextTick(() => {
        const el = this.$refs.expressionInput;
        if (!el) return;
        el.focus();
        el.setSelectionRange(pos, pos);
        this.cursorStart = pos;
        this.cursorEnd = pos;
      });
    },

    insertToken(token) {
      const el = this.$refs.expressionInput;
      const current = this.expression || "";
      const start = el ? (el.selectionStart ?? this.cursorStart ?? current.length) : current.length;
      const end = el ? (el.selectionEnd ?? this.cursorEnd ?? current.length) : current.length;

      let insertion = token;
      let moveBack = 0;

      if (token.endsWith("()")) {
        insertion = token.replace("()", "( )");
        moveBack = 2;
      }

      const next = current.slice(0, start) + insertion + current.slice(end);
      this.expression = next;

      const newPos = start + insertion.length - moveBack;
      this.setCursor(newPos);
    },

    removeLastToken() {
      if (!this.expression) return;
      this.expression = this.expression.slice(0, -1);
      this.setCursor(this.expression.length);
    },

    clearExpression() {
      this.expression = "";
      this.refreshSymbolUsages();
      this.validateExpressionNow();
    },

    formatExpression() {
      this.expression = String(this.expression || "")
        .replace(/\s+/g, " ")
        .replace(/\(\s+/g, "(")
        .replace(/\s+\)/g, ")")
        .trim();
      this.refreshSymbolUsages();
      this.validateExpressionNow();
    },

    insertFieldIntoExpression(fieldMeta) {
      const symbol = this.ensureSymbolForField(fieldMeta);
      this.insertToken(symbol);
    },

    ensureSymbolForField(fieldMeta) {
      const existing = Object.entries(this.symbolMapDraft).find(
        ([, def]) => String(def?.fieldId || "") === String(fieldMeta.id)
      );
      if (existing) return existing[0];

      const symbol = this.suggestedSymbolForField(fieldMeta);
      const isNumeric = this.isNumericField(fieldMeta);
      const isCheckbox = String(fieldMeta.type || "").toLowerCase() === "checkbox";

      this.symbolMapDraft = {
        ...this.symbolMapDraft,
        [symbol]: {
          fieldId: fieldMeta.id,
          fieldLabel: fieldMeta.label,
          sourceType: fieldMeta.type,
          valueType: isNumeric
            ? "number"
            : isCheckbox
              ? "boolean_score"
              : "mapped_choice",
          mappings: isCheckbox
            ? { __unchecked: 0, __checked: 1 }
            : {}
        }
      };

      return symbol;
    },

    extractSymbolsFromExpression(expr) {
      if (!String(expr || "").trim()) return [];

      try {
        const node = math.parse(expr);
        const out = new Set();

        node.traverse((n) => {
          if (n?.isSymbolNode) {
            const name = String(n.name || "");
            if (!name) return;
            if (RESERVED_SYMBOLS.has(name)) return;
            out.add(name);
          }
        });

        return Array.from(out);
      } catch {
        const matches = String(expr || "").match(/[A-Za-z_][A-Za-z0-9_]*/g) || [];
        return [...new Set(matches.filter((x) => !RESERVED_SYMBOLS.has(x)))];
      }
    },

    refreshSymbolUsages() {
      const used = this.extractSymbolsFromExpression(this.expression);
      const next = { ...this.symbolMapDraft };

      used.forEach((sym) => {
        if (!next[sym]) {
          next[sym] = {
            fieldId: "",
            fieldLabel: sym,
            sourceType: "number",
            valueType: "number",
            mappings: {}
          };
        }
      });

      this.symbolMapDraft = next;
    },

    validateExpressionNow() {
      const messages = [];
      const expr = String(this.expression || "").trim();

      if (!expr) {
        this.expressionValidation = { ok: false, messages: ["Expression is empty."] };
        return;
      }

      try {
        math.parse(expr);
      } catch (err) {
        messages.push(err?.message || "Expression syntax is invalid.");
      }

      const symbols = this.extractSymbolsFromExpression(expr);

      if (!symbols.length) {
        messages.push("Expression should reference at least one field symbol.");
      }

      symbols.forEach((sym) => {
        const def = this.symbolMapDraft[sym];
        if (!def || !def.fieldId) {
          messages.push(`Symbol "${sym}" is not mapped to a field.`);
          return;
        }

        const field = this.allFields.find((f) => f.id === def.fieldId);
        if (!field) {
          messages.push(`Symbol "${sym}" points to a missing field.`);
          return;
        }

        if (def.valueType === "mapped_choice") {
          const opts = this.getFieldOptions(field);
          const missing = opts.filter((opt) => {
            const v = def.mappings?.[String(opt)];
            return v === "" || v === null || typeof v === "undefined";
          });
          if (missing.length) {
            messages.push(`Scoring for "${sym}" is incomplete.`);
          }
        }

        if (def.valueType === "boolean_score") {
          const m = def.mappings || {};
          if (typeof m.__checked === "undefined" || typeof m.__unchecked === "undefined") {
            messages.push(`Checkbox scoring for "${sym}" is incomplete.`);
          }
        }
      });

      this.expressionValidation = {
        ok: messages.length === 0,
        messages: messages.length ? messages : ["Looks good."]
      };
    },

    loadCalcRules() {
      const form = this.currentForm;
      if (!form.logic) form.logic = { version: 2, calculations: [], conditions: [] };
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];

      this.calcRules = JSON.parse(
        JSON.stringify(
          (form.logic.calculations || []).filter(
            (r) => r && (r.kind === "calc_expr" || r.kind === "calc")
          )
        )
      );
    },

    persistRules() {
      const form = this.currentForm;

      if (!form.logic) form.logic = { version: 2, calculations: [], conditions: [] };
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];
      if (!Array.isArray(form.logic.conditions)) form.logic.conditions = [];

      form.logic.calculations = JSON.parse(JSON.stringify(this.calcRules));
      form.logic.version = 2;

      this.forms[this.formIndex] = form;
      this.saveFormsToStorage();
      this.emitCurrentFormToParent("persistRules");

      if (this.$store) this.$store.commit("setStudyCreationDirty", true);
    },

    createNewCalculatedField() {
      const form = this.currentForm;
      const secIndex = (form.sections || []).findIndex((sec) => sec._id === this.newTargetSectionId);
      if (secIndex < 0) return null;

      const section = form.sections[secIndex];
      const label = String(this.newTargetLabel || "").trim();
      const safeBase =
        label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "calculated_result";

      const fieldId = this.uuid();

      const newField = {
        _id: fieldId,
        name: `${safeBase}_${Date.now()}`,
        label,
        type: "number",
        value: null,
        placeholder: "",
        computed: true,
        isCalculatedField: true,
        constraints: {
          readonly: true,
          required: false,
          helpText: "Calculated field"
        }
      };

      if (!Array.isArray(section.fields)) section.fields = [];
      section.fields.push(newField);

      this.forms[this.formIndex] = form;
      return { fieldId, field: newField };
    },

    buildRulePayload(finalTargetFieldId) {
      const used = this.extractSymbolsFromExpression(this.expression);
      const symbolMap = {};

      used.forEach((sym) => {
        const def = this.symbolMapDraft[sym];
        if (!def) return;
        symbolMap[sym] = {
          fieldId: def.fieldId,
          fieldLabel: def.fieldLabel,
          sourceType: def.sourceType,
          valueType: def.valueType,
          mappings: JSON.parse(JSON.stringify(def.mappings || {}))
        };
      });

      return {
        id: this.editingRuleId || this.uuid(),
        kind: "calc_expr",
        version: 2,
        expression: String(this.expression || "").trim(),
        symbolOrder: used,
        symbolMap,
        target: finalTargetFieldId,
        targetMode: this.targetMode,
        outputType: "number",
        decimals: Number.isFinite(Number(this.resultDecimals)) ? Number(this.resultDecimals) : 2,
        blankPolicy: this.blankPolicy || "strict",
        enabled: true,
        updatedAt: new Date().toISOString()
      };
    },

    saveCalculation() {
      this.validateExpressionNow();
      if (!this.canSave) return;

      let finalTargetFieldId = this.targetFieldId;

      if (this.targetMode === "new") {
        const created = this.createNewCalculatedField();
        if (!created?.fieldId) return;
        finalTargetFieldId = created.fieldId;
        this.buildFieldIndex();
      }

      const rule = this.buildRulePayload(finalTargetFieldId);

      if (this.editingRuleId) {
        const idx = this.calcRules.findIndex((r) => r.id === this.editingRuleId);
        if (idx >= 0) this.calcRules.splice(idx, 1, rule);
        else this.calcRules.unshift(rule);
      } else {
        this.calcRules.unshift(rule);
      }

      this.persistRules();

      this.targetMode = "existing";
      this.targetFieldId = finalTargetFieldId;
      this.newTargetSectionId = "";
      this.newTargetLabel = "";
      this.editingRuleId = null;

      this.expression = "";
      this.symbolMapDraft = {};
      this.fieldSearch = "";
      this.targetSearch = "";
      this.resultDecimals = 2;
      this.blankPolicy = "strict";

      this.saveFormsToStorage();
    },

    deleteRule(id) {
      this.calcRules = this.calcRules.filter((r) => r.id !== id);
      this.persistRules();
    },

    loadRuleToEditor(rule) {
      this.editingRuleId = rule.id;

      if (rule.kind === "calc_expr") {
        this.expression = rule.expression || "";
        this.symbolMapDraft = JSON.parse(JSON.stringify(rule.symbolMap || {}));
        this.targetMode = rule.targetMode || "existing";
        this.targetFieldId = rule.target || "";
        this.resultDecimals = Number.isFinite(Number(rule.decimals)) ? Number(rule.decimals) : 2;
        this.blankPolicy = rule.blankPolicy || "strict";
      } else {
        const migrated = this.migrateLegacyRuleToExpression(rule);
        this.expression = migrated.expression || "";
        this.symbolMapDraft = JSON.parse(JSON.stringify(migrated.symbolMap || {}));
        this.targetMode = migrated.targetMode || "existing";
        this.targetFieldId = migrated.target || "";
        this.resultDecimals = Number.isFinite(Number(migrated.decimals)) ? Number(migrated.decimals) : 2;
        this.blankPolicy = migrated.blankPolicy || "strict";
      }

      this.newTargetSectionId = "";
      this.newTargetLabel = "";

      this.fieldSearch = "";
      this.targetSearch = "";
      this.refreshSymbolUsages();
      this.validateExpressionNow();
    },

    migrateLegacyRuleToExpression(rule) {
      const sources = Array.isArray(rule.sources) ? rule.sources : [];
      const symMap = {};
      const symbols = sources.map((srcId) => {
        const field = this.allFields.find((f) => f.id === String(srcId));
        const symbol = this.suggestedSymbolForField(field || { id: srcId, label: `field_${srcId}` });
        symMap[symbol] = {
          fieldId: String(srcId),
          fieldLabel: field?.label || symbol,
          sourceType: field?.type || "number",
          valueType: this.isNumericField(field) ? "number" : "mapped_choice",
          mappings: {}
        };
        return symbol;
      });

      const expr = this.legacyRuleToExpression(rule.op, symbols);

      return {
        ...rule,
        kind: "calc_expr",
        version: 2,
        expression: expr,
        symbolOrder: symbols,
        symbolMap: symMap,
        decimals: 2,
        blankPolicy: "strict"
      };
    },

    legacyRuleToExpression(op, symbols) {
      const A = symbols[0] || "a";
      const rest = symbols.slice(1);

      if (op === "sum") return symbols.join(" + ");
      if (op === "subtract") return `${A}${rest.length ? " - " + rest.join(" - ") : ""}`;
      if (op === "multiply") return symbols.join(" * ");
      if (op === "divide") return `${A}${rest.length ? " / " + rest.join(" / ") : ""}`;
      if (op === "mean") return `mean(${symbols.join(", ")})`;
      if (op === "min") return `min(${symbols.join(", ")})`;
      if (op === "max") return `max(${symbols.join(", ")})`;
      if (op === "count_all") return String(symbols.length || 0);

      return symbols.join(" + ");
    },

    ruleSummary(rule) {
      const tgt = this.shortLabel(rule.target);
      return `${tgt} ← Expression`;
    },

    ruleFormula(rule) {
      if (rule.kind === "calc_expr") {
        return `${this.shortLabel(rule.target)} = ${rule.expression || ""}`;
      }

      const migrated = this.migrateLegacyRuleToExpression(rule);
      return `${this.shortLabel(rule.target)} = ${migrated.expression || ""}`;
    },

    shortLabel(id) {
      const f = this.allFields.find((x) => x.id === id);
      return f ? f.label : id;
    },

    getMappingValue(symbol, option) {
      const def = this.symbolMapDraft[symbol] || {};
      const val = def.mappings?.[String(option)];
      return typeof val === "undefined" ? "" : val;
    },

    setMappingValue(symbol, option, rawValue) {
      const n = rawValue === "" ? "" : Number(rawValue);
      if (!this.symbolMapDraft[symbol]) return;

      this.symbolMapDraft = {
        ...this.symbolMapDraft,
        [symbol]: {
          ...this.symbolMapDraft[symbol],
          mappings: {
            ...(this.symbolMapDraft[symbol].mappings || {}),
            [String(option)]: n
          }
        }
      };

      this.validateExpressionNow();
    },

    resetBuilder() {
      this.expression = "";
      this.symbolMapDraft = {};
      this.targetMode = "existing";
      this.targetFieldId = "";
      this.newTargetSectionId = "";
      this.newTargetLabel = "";
      this.resultDecimals = 2;
      this.blankPolicy = "strict";
      this.fieldSearch = "";
      this.targetSearch = "";
      this.editingRuleId = null;
      this.expressionValidation = {
        ok: false,
        messages: ["Expression is empty."]
      };
    }
  }
};
</script>

<style scoped>
.logic-calc-page {
  width: 100%;
  height: calc(100vh - 40px);
  min-height: 0;
  padding: 18px;
  background: #f5f6f8;
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Keep main calculation header visible */
.topbar {
  position: sticky;
  top: 0;
  z-index: 250;

  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;

  margin-bottom: 16px;
  padding: 14px 16px;

  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
}

.logic-back-btn {
  justify-self: start;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #dddddd;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
  color: #374151;
  font-size: 14px;
  line-height: 1;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.02s ease;
}

.btn-back:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.btn-back:active {
  transform: scale(0.98);
}

.title-wrap {
  text-align: center;
  min-width: 0;
}

.title-wrap h2 {
  margin: 0;
  color: #111827;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
}

.title-wrap p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.4;
}

.topbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.1fr) minmax(0, 1.1fr);
  gap: 16px;
  align-items: start;
  min-width: 0;
}

/* Panels should not hide their own headers */
.panel {
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
  min-height: 0;
  max-height: calc(100vh - 190px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

/* Keep panel headers visible while inner list/content scrolls */
.panel-head {
  position: sticky;
  top: 0;
  z-index: 30;

  flex: 0 0 auto;
  padding: 16px 16px 10px;
  border-bottom: 1px solid #dbe4ee;
  background: #eef4f9;
  box-shadow: 0 3px 8px rgba(15, 23, 42, 0.08);
}
/* RIGHT PANEL FIX:
   Result + scoring has many stacked blocks, so the whole right panel must scroll.
   Left and middle panels keep their existing internal scrolling behavior. */
.panel-right {
  overflow-y: auto;
  overflow-x: hidden;
}

/* Keep the right panel header visible while right panel content scrolls */
.panel-right .panel-head {
  position: sticky;
  top: 0;
  z-index: 40;
}

/* Do not let existing/new target block consume all height and hide blocks below */
.panel-right .target-block {
  flex: 0 0 auto;
  min-height: auto;
}

/* Existing target field list gets its own comfortable scroll area */
.panel-right .target-block .picker-list {
  flex: 0 0 auto;
  max-height: 260px;
  min-height: 120px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Give right-panel cards proper spacing because the panel itself now scrolls */
.panel-right > .preview-card {
  margin: 0 16px 16px;
}

.panel-right > .form-block {
  flex: 0 0 auto;
}

/* Keep the scoring/summary sections reachable at the bottom */
.panel-right::after {
  content: "";
  display: block;
  height: 16px;
  flex: 0 0 auto;
}
.panel-head h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.25;
}

.sub {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
}

.toolbar {
  flex: 0 0 auto;
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
}

.search,
.select,
.score-input,
.expr-editor {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  color: #1f2937;
  box-sizing: border-box;
  font-size: 14px;
}

.search:focus,
.select:focus,
.score-input:focus,
.expr-editor:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

.expr-builder {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.token-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toolbar-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn-token {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.12s ease;
}

.btn-token:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

.btn-token.fn {
  font-family: inherit;
}

.expr-editor-wrap {
  display: flex;
  min-width: 0;
}

.expr-editor {
  min-height: 120px;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  line-height: 1.45;
}

.expr-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn-mini {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 700;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.12s ease;
}

.btn-mini:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

.btn-mini:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-mini.danger {
  border-color: #fecaca;
  color: #b91c1c;
}

.btn-secondary {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.12s ease;
}

.btn-secondary:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

.btn-primary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #ffffff;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.12s ease, box-shadow 0.18s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px 16px;
}

.group {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  margin-bottom: 10px;
  background: #ffffff;
  overflow: hidden;
}

.group-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  cursor: pointer;
  user-select: none;
  background: #f8fafc;
}

.group-title {
  font-weight: 700;
  color: #111827;
  min-width: 0;
  word-break: break-word;
}

.group-count {
  font-size: 12px;
  color: #6b7280;
  padding: 2px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #ffffff;
  flex-shrink: 0;
}

.field-list {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  min-width: 0;
}

.field-row:hover {
  background: #f9fafb;
  border-color: #e5e7eb;
}

.field-row-btn {
  width: 100%;
  background: #ffffff;
  text-align: left;
  justify-content: space-between;
}

.field-row input[type="checkbox"],
.field-row input[type="radio"] {
  margin-top: 3px;
  flex-shrink: 0;
}

.field-meta {
  min-width: 0;
}

.field-label {
  font-weight: 600;
  color: #111827;
  word-break: break-word;
}

.field-sub {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
}

.field-insert-name {
  margin-left: auto;
  font-size: 12px;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  border-radius: 999px;
  padding: 4px 8px;
  flex-shrink: 0;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.score-badge {
  margin-left: 6px;
  color: #7c3aed;
  font-weight: 700;
}

.preview-card {
  border: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 12px;
  padding: 12px;
}

.preview-title {
  font-weight: 700;
  margin-bottom: 8px;
  color: #111827;
}

.formula {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 10px;
  padding: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.target-mode {
  flex: 0 0 auto;
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
}

.mode-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.mode-pill.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.mode-pill input {
  margin: 0;
}

.target-block {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.form-block {
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-block-label {
  font-weight: 700;
  font-size: 13px;
  color: #111827;
}

.new-field-note,
.valid-box {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
}

.preview-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 8px;
}

.preview-k {
  color: #6b7280;
  font-size: 13px;
}

.preview-v {
  color: #111827;
  font-size: 13px;
  word-break: break-word;
}

.warn-box {
  margin-top: 10px;
  border: 1px solid #fde68a;
  background: #fffbeb;
  border-radius: 10px;
  padding: 10px;
  color: #92400e;
}

.warn-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.warn-box ul {
  margin: 0;
  padding-left: 18px;
}

.score-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  background: #ffffff;
  margin-bottom: 10px;
}

.score-head {
  margin-bottom: 10px;
}

.score-title {
  font-weight: 700;
  color: #111827;
}

.score-sub {
  font-size: 12px;
  color: #6b7280;
}

.score-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px;
  gap: 8px;
  align-items: center;
}

.score-opt {
  font-size: 13px;
  color: #111827;
  word-break: break-word;
}

.checkbox-score-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
}

.saved-block {
  margin-top: 16px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.saved-head h3 {
  margin: 0 0 12px;
  color: #111827;
  font-size: 18px;
  font-weight: 800;
}

.rules {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  background: #ffffff;
}

.rule-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.rule-title {
  font-weight: 700;
  color: #111827;
}

.rule-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.rule-sub {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
  word-break: break-word;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  background: #eef2ff;
  color: #3730a3;
  border: 1px solid #c7d2fe;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
}

.empty {
  color: #6b7280;
  font-size: 13px;
  padding: 8px 0;
}

.empty-small {
  color: #6b7280;
  font-size: 12px;
}

/* Responsive */
@media (max-width: 1200px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .panel {
  max-height: none;
  overflow: visible;
}

.panel-left,
.panel-middle,
.panel-right {
  overflow: visible;
}

.panel-right .target-block .picker-list {
  max-height: 280px;
  overflow-y: auto;
}

  .logic-calc-page {
    height: calc(100vh - 40px);
  }
}

@media (max-width: 768px) {
  .logic-calc-page {
    padding: 12px;
  }

  .topbar {
    grid-template-columns: 1fr;
    align-items: stretch;
    top: 0;
  }

  .title-wrap {
    text-align: left;
  }

  .topbar-actions {
    flex-direction: column;
  }

  .btn-secondary,
  .btn-primary,
  .btn-back {
    width: 100%;
    justify-content: center;
  }

  .target-mode {
    flex-direction: column;
  }

  .checkbox-score-grid,
  .score-row,
  .preview-row {
    grid-template-columns: 1fr;
  }

  .rule-top {
    flex-direction: column;
    align-items: stretch;
  }

  .rule-actions {
    justify-content: flex-start;
  }
}
</style>