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
          Choose source fields, select an operation, and store the result in an existing field
          or create a new read-only calculated field.
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
          <h3>1) Source fields</h3>
          <div class="sub">Pick 2 or more fields</div>
        </div>

        <div class="toolbar">
          <input
            v-model="fieldSearch"
            class="search"
            placeholder="Search source fields…"
            aria-label="Search source fields"
          />
          <button class="btn-mini" @click="clearSelection" :disabled="selectedSourceIds.length === 0">
            Clear
          </button>
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
              <label
                v-for="f in sec.fields"
                :key="f.id"
                class="field-row"
                :title="f.path"
              >
                <input
                  type="checkbox"
                  :checked="selectedSourceIds.includes(f.id)"
                  @change="toggleSource(f.id, $event)"
                />
                <div class="field-meta">
                  <div class="field-label">{{ f.label }}</div>
                  <div class="field-sub">{{ f.typeLabel }}</div>
                </div>
              </label>
            </div>
          </details>

          <div v-if="!filteredFieldTree.length" class="empty">No fields found.</div>
        </div>

        <div class="selection-summary">
          <div class="summary-title">Selected</div>
          <div v-if="selectedSourceIds.length" class="chips">
            <span v-for="id in selectedSourceIds" :key="id" class="chip">
              {{ shortLabel(id) }}
            </span>
          </div>
          <div v-else class="empty-small">No source fields selected yet.</div>
        </div>
      </section>

      <!-- MIDDLE -->
      <section class="panel panel-middle">
        <div class="panel-head">
          <h3>2) Operation</h3>
          <div class="sub">How should the result be calculated?</div>
        </div>

        <div class="op-select-wrap">
          <label class="field-block">
            <span class="field-block-label">Operation</span>
            <select v-model="operation" class="select">
              <option v-for="op in operations" :key="op.value" :value="op.value">
                {{ op.label }}
              </option>
            </select>
          </label>

          <div class="selected-op-card">
            <div class="op-name">{{ selectedOperationLabel }}</div>
            <div class="op-desc">{{ selectedOperationDesc }}</div>
          </div>
        </div>

        <div class="preview-card">
          <div class="preview-title">Formula preview</div>
          <div class="formula" v-if="selectedSourceIds.length">
            {{ formulaPreview }}
          </div>
          <div v-else class="empty-small">Choose source fields to see preview.</div>
        </div>

        <div class="preview-card">
          <div class="preview-title">Notes</div>
          <ul class="notes">
            <li>For subtraction and division, the first selected field is used as the base.</li>
            <li>Statistical operations work best with number fields.</li>
            <li>Calculated result fields created here are read-only in the form.</li>
          </ul>
        </div>
      </section>

      <!-- RIGHT -->
      <section class="panel panel-right">
        <div class="panel-head">
          <h3>3) Result field</h3>
          <div class="sub">Store result in an existing field or create a new one</div>
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

        <!-- EXISTING -->
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

        <!-- NEW -->
        <div v-else class="target-block">
          <div class="form-block">
            <label class="field-block">
              <span class="field-block-label">Section</span>
              <select v-model="newTargetSectionId" class="select">
                <option disabled value="">Select section…</option>
                <option
                  v-for="sec in sectionOptions"
                  :key="sec.id"
                  :value="sec.id"
                >
                  {{ sec.title }}
                </option>
              </select>
            </label>

            <label class="field-block">
              <span class="field-block-label">New field name</span>
              <input
                v-model="newTargetLabel"
                class="search"
                placeholder="e.g. Total Score"
              />
            </label>

            <div class="new-field-note">
              A new <strong>read-only number field</strong> will be created in the selected section.
            </div>
          </div>
        </div>

        <div class="preview-card">
          <div class="preview-title">Result summary</div>

          <div class="preview-row">
            <div class="preview-k">Sources</div>
            <div class="preview-v">{{ selectedSourceLabels || "—" }}</div>
          </div>

          <div class="preview-row">
            <div class="preview-k">Operation</div>
            <div class="preview-v">{{ prettyOperation(operation) }}</div>
          </div>

          <div class="preview-row">
            <div class="preview-k">Result</div>
            <div class="preview-v">
              <template v-if="targetMode === 'existing'">
                {{ targetLabel || "—" }}
              </template>
              <template v-else>
                {{ newTargetPreview || "—" }}
              </template>
            </div>
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
/**
 * SIMPLE CALCULATIONS ONLY
 * - full-width 3-column UX
 * - result target can be:
 *    1) existing field
 *    2) newly created read-only calculated field
 *
 * IMPORTANT:
 * - never mutates the incoming form prop
 * - maintains an internal working copy
 * - emits both updated form structure and logic payload back to parent
 */
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

      selectedSourceIds: [],
      operation: "sum",

      targetMode: "existing",
      targetFieldId: "",

      newTargetSectionId: "",
      newTargetLabel: "",

      calcRules: [],
      editingRuleId: null,

      operations: [
        { value: "sum", label: "Sum", desc: "Add all selected values" },
        { value: "subtract", label: "Subtract", desc: "First - second - third…" },
        { value: "multiply", label: "Multiply", desc: "Multiply all selected values" },
        { value: "divide", label: "Divide", desc: "First ÷ second ÷ third…" },
        { value: "mean", label: "Mean", desc: "Average of selected values" },
        { value: "median", label: "Median", desc: "Middle value after sorting" },
        { value: "mode", label: "Mode", desc: "Most frequent value" },
        { value: "min", label: "Minimum", desc: "Smallest value" },
        { value: "max", label: "Maximum", desc: "Largest value" },
        { value: "range", label: "Range", desc: "Maximum - Minimum" },
        { value: "count", label: "Count (non-empty)", desc: "Count only filled values" },
        { value: "count_all", label: "Count (all)", desc: "Count all selected fields" },
        { value: "stddev_pop", label: "Std Dev (Population)", desc: "Population standard deviation" },
        { value: "stddev_samp", label: "Std Dev (Sample)", desc: "Sample standard deviation" },
        { value: "variance_pop", label: "Variance (Population)", desc: "Population variance" },
        { value: "variance_samp", label: "Variance (Sample)", desc: "Sample variance" }
      ]
    };
  },

  computed: {
    currentForm() {
      return this.forms[this.formIndex] || { sections: [], logic: { version: 1, calculations: [], conditions: [] } };
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

    selectedSourceLabels() {
      const m = new Map(this.allFields.map(f => [f.id, f]));
      return this.selectedSourceIds
        .map(id => m.get(id)?.label)
        .filter(Boolean)
        .join(", ");
    },

    targetLabel() {
      const f = this.allFields.find(x => x.id === this.targetFieldId);
      return f ? `${f.label} — ${f.sectionTitle}` : "";
    },

    newTargetPreview() {
      const sec = this.sectionOptions.find(s => s.id === this.newTargetSectionId);
      if (!sec && !this.newTargetLabel.trim()) return "";
      return `${this.newTargetLabel || "New Calculated Field"}${sec ? ` — ${sec.title}` : ""}`;
    },

    canSave() {
      if (this.selectedSourceIds.length < 2 || !this.operation) return false;

      if (this.targetMode === "existing") {
        return !!this.targetFieldId;
      }

      return !!this.newTargetSectionId && !!String(this.newTargetLabel || "").trim();
    },

    selectedOperation() {
      return this.operations.find(op => op.value === this.operation) || this.operations[0];
    },

    selectedOperationLabel() {
      return this.selectedOperation?.label || "";
    },

    selectedOperationDesc() {
      return this.selectedOperation?.desc || "";
    },

    formulaPreview() {
      const src = this.selectedSourceIds.map(id => this.shortLabel(id)).filter(Boolean);
      if (!src.length) return "Select source fields";

      const resultName =
        this.targetMode === "existing"
          ? (this.shortLabel(this.targetFieldId) || "Result")
          : (this.newTargetLabel || "New Calculated Field");

      const A = src[0];
      const rest = src.slice(1);

      if (this.operation === "sum") return `${resultName} = ${src.join(" + ")}`;
      if (this.operation === "subtract") return `${resultName} = ${A}${rest.length ? " - " + rest.join(" - ") : ""}`;
      if (this.operation === "multiply") return `${resultName} = ${src.join(" × ")}`;
      if (this.operation === "divide") return `${resultName} = ${A}${rest.length ? " ÷ " + rest.join(" ÷ ") : ""}`;

      if (this.operation === "mean") return `${resultName} = MEAN(${src.join(", ")})`;
      if (this.operation === "median") return `${resultName} = MEDIAN(${src.join(", ")})`;
      if (this.operation === "mode") return `${resultName} = MODE(${src.join(", ")})`;
      if (this.operation === "min") return `${resultName} = MIN(${src.join(", ")})`;
      if (this.operation === "max") return `${resultName} = MAX(${src.join(", ")})`;
      if (this.operation === "range") return `${resultName} = RANGE(${src.join(", ")})`;
      if (this.operation === "count") return `${resultName} = COUNT_NON_EMPTY(${src.join(", ")})`;
      if (this.operation === "count_all") return `${resultName} = COUNT_ALL(${src.join(", ")})`;
      if (this.operation === "stddev_pop") return `${resultName} = STDDEV_POP(${src.join(", ")})`;
      if (this.operation === "stddev_samp") return `${resultName} = STDDEV_SAMP(${src.join(", ")})`;
      if (this.operation === "variance_pop") return `${resultName} = VAR_POP(${src.join(", ")})`;
      if (this.operation === "variance_samp") return `${resultName} = VAR_SAMP(${src.join(", ")})`;

      return `${resultName} = ${String(this.operation).toUpperCase()}(${src.join(", ")})`;
    },

    warnings() {
      const out = [];

      const sourceNonNumber = this.selectedSourceIds
        .map(id => this.allFields.find(f => f.id === id))
        .filter(f => f && f.type && f.type !== "number");

      if (sourceNonNumber.length) {
        out.push("Some selected source fields are not number fields.");
      }

      if (this.targetMode === "existing") {
        if (this.targetFieldId && this.selectedSourceIds.includes(this.targetFieldId)) {
          out.push("Result field is also included in source fields.");
        }

        const t = this.allFields.find(f => f.id === this.targetFieldId);
        if (t && t.type && t.type !== "number") {
          out.push(`Existing result field type is "${t.type}". Number field is recommended.`);
        }
      }

      if (this.targetMode === "new" && this.newTargetLabel.trim()) {
        const duplicate = this.allFields.some(
          f =>
            String(f.label || "").trim().toLowerCase() ===
            String(this.newTargetLabel || "").trim().toLowerCase()
        );
        if (duplicate) {
          out.push("A field with the same label already exists.");
        }
      }

      if (this.operation === "divide" && this.selectedSourceIds.length >= 2) {
        out.push("Division can fail at runtime if a divisor becomes zero or empty.");
      }

      return out;
    }
  },

  watch: {
    form: {
      deep: true,
      handler(newForm) {
        if (!newForm || typeof newForm !== "object") return;

        console.log("[Logic] prop form changed", JSON.parse(JSON.stringify(newForm)));

        const next = JSON.parse(JSON.stringify(newForm));
        if (!next.logic || typeof next.logic !== "object") {
          next.logic = { version: 1, calculations: [], conditions: [] };
        }
        if (!Array.isArray(next.logic.calculations)) next.logic.calculations = [];
        if (!Array.isArray(next.logic.conditions)) next.logic.conditions = [];

        this.forms[this.formIndex] = next;
        this.ensurePersistentIds();
        this.buildFieldIndex();
        this.loadCalcRules();
      }
    }
  },

  mounted() {
    const idx = parseInt(this.$route?.query?.formIndex ?? "0", 10);
    this.formIndex = Number.isFinite(idx) && idx >= 0 ? idx : 0;

    this.loadFormsFromStorage();
    this.ensurePersistentIds();
    this.buildFieldIndex();
    this.loadCalcRules();
  },

  methods: {
    goBack() {
      this.persistRules();

      console.log("[Logic] goBack() after persistRules", {
        fullForm: JSON.parse(JSON.stringify(this.currentForm || {})),
        logic: JSON.parse(JSON.stringify(this.currentForm?.logic || {}))
      });

      this.emitCurrentFormToParent("goBack");
      this.$emit("back-to-builder");
    },

    loadFormsFromStorage() {
      try {
        const parsed = JSON.parse(localStorage.getItem("scratchForms") || "[]");
        this.forms = Array.isArray(parsed) ? parsed : [];
      } catch {
        this.forms = [];
      }

      if (!this.forms.length) this.forms = [{ sections: [] }];
      while (this.forms.length <= this.formIndex) this.forms.push({ sections: [] });

      if (this.form && typeof this.form === "object") {
        this.forms[this.formIndex] = JSON.parse(JSON.stringify(this.form));
      } else if (!this.forms[this.formIndex]) {
        this.forms[this.formIndex] = { sections: [] };
      }

      if (!Array.isArray(this.forms[this.formIndex].sections)) {
        this.forms[this.formIndex].sections = [];
      }

      if (!this.forms[this.formIndex].logic || typeof this.forms[this.formIndex].logic !== "object") {
        this.forms[this.formIndex].logic = { version: 1, calculations: [], conditions: [] };
      }
      if (!Array.isArray(this.forms[this.formIndex].logic.calculations)) {
        this.forms[this.formIndex].logic.calculations = [];
      }
      if (!Array.isArray(this.forms[this.formIndex].logic.conditions)) {
        this.forms[this.formIndex].logic.conditions = [];
      }

      console.log("[Logic] loadFormsFromStorage()", {
        formIndex: this.formIndex,
        propForm: JSON.parse(JSON.stringify(this.form || {})),
        workingForm: JSON.parse(JSON.stringify(this.forms[this.formIndex] || {}))
      });
    },

    saveFormsToStorage() {
      localStorage.setItem("scratchForms", JSON.stringify(this.forms));
    },

    emitCurrentFormToParent(reason = "unknown") {
      const currentForm = JSON.parse(JSON.stringify(this.currentForm || {}));
      const currentLogic = JSON.parse(JSON.stringify(currentForm.logic || {
        version: 1,
        calculations: [],
        conditions: []
      }));

      console.log(`[Logic] emitCurrentFormToParent() reason=${reason}`, {
        currentForm,
        currentLogic
      });

      this.$emit("update-form-structure", currentForm);
      this.$emit("update-logic", currentLogic);
    },

    uuid() {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
      return `id_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    },

    ensurePersistentIds() {
      const form = this.currentForm;

      (form.sections || []).forEach(sec => {
        if (!sec._id) sec._id = this.uuid();
        if (!Array.isArray(sec.fields)) sec.fields = [];
        sec.fields.forEach(f => {
          if (!f._id) f._id = this.uuid();
          if (!f.constraints || typeof f.constraints !== "object") {
            f.constraints = {};
          }
        });
      });

      if (!form.logic) form.logic = { version: 1, calculations: [], conditions: [] };
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];
      if (!Array.isArray(form.logic.conditions)) form.logic.conditions = [];
      if (!form.logic.version) form.logic.version = 1;

      this.forms[this.formIndex] = form;
      this.saveFormsToStorage();
    },

    buildFieldIndex() {
      const form = this.currentForm;
      const out = [];

      (form.sections || []).forEach((sec, si) => {
        const sectionTitle = sec.title || `Section ${si + 1}`;

        (sec.fields || []).forEach((f, fi) => {
          const id = f._id || f.id || `sec${si}_fld${fi}_${String(f.name || "")}`;

          out.push({
            id: String(id),
            label: String(f.label || f.name || `Field ${fi + 1}`),
            name: String(f.name || ""),
            type: String(f.type || "text"),
            typeLabel: this.prettyTypeLabel(String(f.type || "text")),
            sectionTitle,
            path: `${sectionTitle} / ${String(f.label || f.name || `Field ${fi + 1}`)}`
          });
        });
      });

      this.allFields = out.filter(f => f.type !== "button");

      console.log("[Logic] buildFieldIndex()", JSON.parse(JSON.stringify(this.allFields)));
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
        : fields.filter(f => {
            const hay = `${f.label} ${f.sectionTitle} ${f.path} ${f.typeLabel}`.toLowerCase();
            return hay.includes(q);
          });

      const bySection = new Map();
      filtered.forEach(f => {
        const key = String(f.sectionTitle || "Other");
        if (!bySection.has(key)) bySection.set(key, []);
        bySection.get(key).push(f);
      });

      const sectionOrder = [];
      (this.currentForm?.sections || []).forEach(sec => {
        const st = String(sec?.title || "");
        if (st) sectionOrder.push(st);
      });

      const out = [];
      const used = new Set();

      sectionOrder.forEach(st => {
        if (!bySection.has(st)) return;
        used.add(st);
        out.push({
          key: `sec_${st}`,
          sectionTitle: st,
          fields: bySection.get(st),
          openByDefault: !!q
        });
      });

      Array.from(bySection.keys()).forEach(st => {
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

    loadCalcRules() {
      const form = this.currentForm;
      if (!form.logic) form.logic = { version: 1, calculations: [], conditions: [] };
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];

      this.calcRules = JSON.parse(
        JSON.stringify((form.logic.calculations || []).filter(r => r && r.kind === "calc"))
      );

      console.log("[Logic] loadCalcRules()", JSON.parse(JSON.stringify(this.calcRules)));
    },

    persistRules() {
      const form = this.currentForm;

      if (!form.logic) form.logic = { version: 1, calculations: [], conditions: [] };
      if (!Array.isArray(form.logic.calculations)) form.logic.calculations = [];
      if (!Array.isArray(form.logic.conditions)) form.logic.conditions = [];

      form.logic.calculations = JSON.parse(JSON.stringify(this.calcRules));
      form.logic.version = 1;

      this.forms[this.formIndex] = form;
      this.saveFormsToStorage();

      console.log("[Logic] persistRules()", {
        calcRules: JSON.parse(JSON.stringify(this.calcRules || [])),
        logicOnForm: JSON.parse(JSON.stringify(form.logic || {})),
        fullForm: JSON.parse(JSON.stringify(form || {}))
      });

      this.emitCurrentFormToParent("persistRules");

      if (this.$store) this.$store.commit("setStudyCreationDirty", true);
    },

    toggleSource(id, evt) {
      const checked = !!evt?.target?.checked;
      const next = new Set(this.selectedSourceIds);

      if (checked) next.add(id);
      else next.delete(id);

      const order = new Map(this.allFields.map((f, i) => [f.id, i]));
      this.selectedSourceIds = Array.from(next).sort((a, b) => (order.get(a) ?? 0) - (order.get(b) ?? 0));
    },

    clearSelection() {
      this.selectedSourceIds = [];
    },

    resetBuilder() {
      this.selectedSourceIds = [];
      this.operation = "sum";

      this.targetMode = "existing";
      this.targetFieldId = "";

      this.newTargetSectionId = "";
      this.newTargetLabel = "";

      this.fieldSearch = "";
      this.targetSearch = "";
      this.editingRuleId = null;
    },

    shortLabel(id) {
      const f = this.allFields.find(x => x.id === id);
      return f ? f.label : id;
    },

    prettyOperation(op) {
      const map = {
        sum: "Sum",
        subtract: "Subtract",
        multiply: "Multiply",
        divide: "Divide",
        mean: "Mean",
        median: "Median",
        mode: "Mode",
        min: "Minimum",
        max: "Maximum",
        range: "Range",
        count: "Count (non-empty)",
        count_all: "Count (all)",
        stddev_pop: "Std Dev (Population)",
        stddev_samp: "Std Dev (Sample)",
        variance_pop: "Variance (Population)",
        variance_samp: "Variance (Sample)"
      };
      return map[op] || op;
    },

    createNewCalculatedField() {
      const form = this.currentForm;
      const secIndex = (form.sections || []).findIndex(sec => sec._id === this.newTargetSectionId);
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

      console.log("[Logic] createNewCalculatedField()", {
        secIndex,
        newField,
        formAfterCreate: JSON.parse(JSON.stringify(form))
      });

      return {
        fieldId,
        field: newField
      };
    },

    saveCalculation() {
      if (!this.canSave) return;

      let finalTargetFieldId = this.targetFieldId;

      if (this.targetMode === "new") {
        const created = this.createNewCalculatedField();
        if (!created?.fieldId) return;
        finalTargetFieldId = created.fieldId;

        this.buildFieldIndex();
      }

      const rule = {
        id: this.editingRuleId || this.uuid(),
        kind: "calc",
        version: 1,
        op: this.operation,
        sources: [...this.selectedSourceIds],
        target: finalTargetFieldId,
        targetMode: this.targetMode,
        enabled: true,
        updatedAt: new Date().toISOString()
      };

      if (this.editingRuleId) {
        const idx = this.calcRules.findIndex(r => r.id === this.editingRuleId);
        if (idx >= 0) this.calcRules.splice(idx, 1, rule);
        else this.calcRules.unshift(rule);
      } else {
        this.calcRules.unshift(rule);
      }

      this.persistRules();

      console.log("[Logic] saveCalculation() completed", {
        finalTargetFieldId,
        calcRules: JSON.parse(JSON.stringify(this.calcRules || [])),
        formAfterSave: JSON.parse(JSON.stringify(this.currentForm || {}))
      });

      this.selectedSourceIds = [];
      this.fieldSearch = "";
      this.targetSearch = "";

      this.targetMode = "existing";
      this.targetFieldId = finalTargetFieldId;
      this.newTargetSectionId = "";
      this.newTargetLabel = "";
      this.editingRuleId = null;

      this.saveFormsToStorage();
    },

    deleteRule(id) {
      this.calcRules = this.calcRules.filter(r => r.id !== id);
      this.persistRules();
    },

    loadRuleToEditor(rule) {
      this.editingRuleId = rule.id;
      this.selectedSourceIds = Array.isArray(rule.sources) ? [...rule.sources] : [];
      this.operation = rule.op || "sum";

      if (rule.targetMode === "new") {
        this.targetMode = "new";
        this.targetFieldId = "";
      } else {
        this.targetMode = "existing";
        this.targetFieldId = rule.target || "";
      }

      this.newTargetSectionId = "";
      this.newTargetLabel = "";

      this.fieldSearch = "";
      this.targetSearch = "";
    },

    ruleSummary(rule) {
      const tgt = this.shortLabel(rule.target);
      return `${tgt} ← ${this.prettyOperation(rule.op)}`;
    },

    ruleFormula(rule) {
      const sources = (rule.sources || []).map(id => this.shortLabel(id)).join(", ");
      return `${this.shortLabel(rule.target)} = ${this.prettyOperation(rule.op)}(${sources})`;
    }
  }
};
</script>

<style scoped>
.logic-calc-page {
  width: 100%;
  min-height: 100%;
  padding: 18px;
  background: #f5f6f8;
  box-sizing: border-box;
}

.topbar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.logic-back-btn {
  justify-self: start;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
  color: #111827;
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
}

.title-wrap h2 {
  margin: 0;
}

.title-wrap p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.topbar-actions {
  display: flex;
  gap: 10px;
}

.workspace {
  display: grid;
  grid-template-columns: 1.15fr 0.95fr 1.15fr;
  gap: 16px;
  align-items: start;
}

.panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  min-height: calc(100vh - 260px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-head {
  padding: 16px 16px 10px;
  border-bottom: 1px solid #eef2f7;
}

.panel-head h3 {
  margin: 0;
}

.sub {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.toolbar {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
}

.search,
.select {
  width: 100%;
  border: 1px solid #dfe3ea;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  box-sizing: border-box;
}

.btn-mini {
  border: 1px solid #dfe3ea;
  background: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-mini:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-mini.danger {
  border-color: #fecaca;
}

.btn-secondary {
  border: 1px solid #dfe3ea;
  background: #fff;
  border-radius: 12px;
  padding: 11px 14px;
  cursor: pointer;
}

.btn-primary {
  border: none;
  background: #2563eb;
  color: #fff;
  border-radius: 12px;
  padding: 11px 16px;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker-list {
  flex: 1;
  overflow: auto;
  padding: 0 16px 16px;
}

.group {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  margin-bottom: 10px;
  background: #fff;
}

.group-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 12px;
  cursor: pointer;
  user-select: none;
}

.group-title {
  font-weight: 700;
  color: #111827;
}

.group-count {
  font-size: 12px;
  color: #6b7280;
  padding: 2px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f9fafb;
}

.field-list {
  padding: 0 8px 10px;
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
  border-radius: 12px;
  cursor: pointer;
}

.field-row:hover {
  background: #f9fafb;
  border-color: #e5e7eb;
}

.field-row input[type="checkbox"],
.field-row input[type="radio"] {
  margin-top: 3px;
}

.field-meta {
  min-width: 0;
}

.field-label {
  font-weight: 600;
  color: #111827;
}

.field-sub {
  font-size: 12px;
  color: #6b7280;
}

.selection-summary {
  border-top: 1px solid #eef2f7;
  padding: 12px 16px 16px;
}

.summary-title {
  font-weight: 700;
  margin-bottom: 8px;
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
}

.op-select-wrap {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.selected-op-card {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 14px;
  padding: 12px;
}

.op-name {
  font-weight: 700;
  color: #111827;
}

.op-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.preview-card {
  margin: 0 16px 16px;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 14px;
  padding: 12px;
}

.preview-title {
  font-weight: 700;
  margin-bottom: 8px;
}

.formula {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 12px;
  padding: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 13px;
  line-height: 1.5;
}

.notes {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 13px;
}

.target-mode {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
}

.mode-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #dfe3ea;
  background: #fff;
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
}

.mode-pill.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.mode-pill input {
  margin: 0;
}

.target-block {
  flex: 1;
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
}

.new-field-note {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
}

.preview-row {
  display: grid;
  grid-template-columns: 88px 1fr;
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
  border-radius: 12px;
  padding: 10px;
}

.warn-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.saved-block {
  margin-top: 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 16px;
}

.saved-head h3 {
  margin: 0 0 12px;
}

.rules {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
}

.rule-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.rule-title {
  font-weight: 700;
}

.rule-actions {
  display: flex;
  gap: 8px;
}

.rule-sub {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
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
</style>