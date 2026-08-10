<template>
  <div class="import-study">
    <!-- STEP 1: Upload -->
    <section class="card">
      <h2>1) Upload file</h2>
      <div class="upload-inputs">
        <div class="upload-input-group">
          <label class="upload-label">Study data</label>
          <input type="file" accept=".csv,.tsv,.xlsx,.xls" @change="onFile" />
          <div v-if="fileName" class="hint">Loaded: {{ fileName }} ({{ rowCount }} rows)</div>
        </div>

        <div class="upload-input-group">
          <div class="schema-upload-heading">
            <label class="upload-label">Field schema JSON <span class="muted">(optional)</span></label>
            <button
              type="button"
              class="schema-info-button"
              title="Field schema JSON example"
              aria-label="Show field schema JSON example"
              @click="showFieldSchemaInfo = true"
            >
              <i :class="icons.info"></i>
            </button>
          </div>
          <input type="file" accept=".json,application/json" @change="onFieldSchemaFile" />
          <div v-if="fieldSchemaFileName" class="schema-file-status">
            <span>Loaded: {{ fieldSchemaFileName }}</span>
            <button type="button" class="link schema-clear-button" @click="clearFieldSchema">Remove</button>
          </div>
          <div v-if="fieldSchemaAppliedCount" class="hint">
            Schema matched {{ fieldSchemaAppliedCount }} column(s). Unlisted fields will be inferred.
          </div>
          <div v-if="fieldSchemaError" class="schema-error-row error">
            <span>{{ fieldSchemaError }}</span>
            <button type="button" class="link schema-clear-button" @click="clearFieldSchema">Ignore JSON</button>
          </div>
        </div>
      </div>

      <div v-if="previewRows.length" class="table-scroll">
        <table class="preview">
          <thead>
            <tr>
              <th v-for="h in headers" :key="h">{{ h }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in previewRows" :key="i">
              <td v-for="h in headers" :key="h">{{ r[h] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- STEP 2: Map Study Metadata -->
    <section class="card">
      <h2>2) Map Study Metadata</h2>
      <p class="muted">Map CSV columns or set fixed values to populate your study's metadata.</p>

      <div class="schema-grid" v-if="studySchema.length">
        <div
          v-for="f in studySchema"
          :key="'study-' + f.field"
          class="schema-map-row"
          v-show="f.display !== false"
        >
          <div class="schema-map-label">
            <div class="lbl">{{ f.label }}</div>
            <div class="req" v-if="f.required">*</div>
          </div>

          <div class="schema-map-ctrls">
            <div class="schema-map-ctrl">
              <label class="small">From column</label>
              <select v-model="mapping.study.cols[f.field]">
                <option value="">— None —</option>
                <option v-for="h in headers" :key="'scol-' + f.field + '-' + h" :value="h">{{ h }}</option>
              </select>
            </div>
            <div class="schema-map-ctrl">
              <label class="small">Fixed value</label>
              <input
                v-if="f.type !== 'select'"
                v-model="mapping.study.fixed[f.field]"
                :placeholder="f.placeholder || f.label"
              />
              <select v-else v-model="mapping.study.fixed[f.field]">
                <option value="">— None —</option>
                <option v-for="opt in f.options || []" :key="'sfx-' + f.field + '-' + opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <details v-if="studySchema.length">
        <summary>Detected study schema fields</summary>
        <ul class="muted">
          <li v-for="f in studySchema" :key="'studypeek-' + f.field">
            {{ f.field }} ({{ f.type }}){{ f.required ? ' *' : '' }}
          </li>
        </ul>
      </details>
    </section>

    <!-- STEP 3: Subject (ID & optional date) -->
    <section v-if="headers.length" class="card">
      <h2>3) Subject</h2>
      <div class="grid">
        <div class="form-row">
          <label>Subject ID column <span class="muted">(required)</span></label>
          <select v-model="mapping.subject.idCol">
            <option value="">— Select —</option>
            <option v-for="h in headers" :key="'sid-' + h" :value="h">{{ h }}</option>
          </select>
        </div>

        <div class="form-row">
          <label>Date column (optional)</label>
          <select v-model="mapping.subject.dateCol">
            <option value="">— None —</option>
            <option v-for="h in headers" :key="'dt-' + h" :value="h">{{ h }}</option>
          </select>
        </div>
      </div>

      <div class="muted smalltop">
        Visit and Group are mapped below in their own sections.
      </div>
    </section>

    <!-- STEP 4: Map Group Metadata (and group name column) -->
    <section class="card">
      <h2>4) Map Group Metadata</h2>
      <p class="muted">Choose the column that contains the group name for each row, then map optional metadata fields.</p>

      <div class="form-row" style="margin-bottom:10px;">
        <label>Group name column</label>
        <select v-model="mapping.group.nameCol">
          <option value="">— None (single group: Group A) —</option>
          <option v-for="h in headers" :key="'grpname-' + h" :value="h">{{ h }}</option>
        </select>
      </div>

      <div class="schema-grid" v-if="groupSchema.length">
        <div
          v-for="f in groupSchema"
          :key="'group-' + f.field"
          class="schema-map-row"
          v-show="f.display !== false"
        >
          <div class="schema-map-label">
            <div class="lbl">{{ f.label }}</div>
          </div>

          <div class="schema-map-ctrls">
            <div class="schema-map-ctrl">
              <label class="small">From column</label>
              <select v-model="mapping.group.cols[f.field]">
                <option value="">— None —</option>
                <option v-for="h in headers" :key="'gcol-' + f.field + '-' + h" :value="h">{{ h }}</option>
              </select>
            </div>
            <div class="schema-map-ctrl">
              <label class="small">Fixed value</label>
              <input
                v-if="f.type !== 'select'"
                v-model="mapping.group.fixed[f.field]"
                :placeholder="f.placeholder || f.label"
              />
              <select v-else v-model="mapping.group.fixed[f.field]">
                <option value="">— None —</option>
                <option v-for="opt in f.options || []" :key="'gfx-' + f.field + '-' + opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <details v-if="groupSchema.length">
        <summary>Detected group schema fields</summary>
        <ul class="muted">
          <li v-for="f in groupSchema" :key="'grouppeek-' + f.field">
            {{ f.field }} ({{ f.type }})
          </li>
        </ul>
      </details>
    </section>

    <!-- STEP 5: Map Visit Metadata (and visit name column) -->
    <section class="card">
      <h2>5) Map Visit Metadata</h2>
      <p class="muted">Choose the column that contains the visit name for each row, then map optional metadata fields.</p>

      <div class="form-row" style="margin-bottom:10px;">
        <label>Visit name column</label>
        <select v-model="mapping.visit.nameCol">
          <option value="">— None (single visit: Baseline) —</option>
          <option v-for="h in headers" :key="'visname-' + h" :value="h">{{ h }}</option>
        </select>
      </div>

      <div class="schema-grid" v-if="visitSchema.length">
        <div
          v-for="f in visitSchema"
          :key="'visit-' + f.field"
          class="schema-map-row"
          v-show="f.display !== false"
        >
          <div class="schema-map-label">
            <div class="lbl">{{ f.label }}</div>
          </div>

          <div class="schema-map-ctrls">
            <div class="schema-map-ctrl">
              <label class="small">From column</label>
              <select v-model="mapping.visit.cols[f.field]">
                <option value="">— None —</option>
                <option v-for="h in headers" :key="'vcol-' + f.field + '-' + h" :value="h">{{ h }}</option>
              </select>
            </div>
            <div class="schema-map-ctrl">
              <label class="small">Fixed value</label>
              <input
                v-if="f.type !== 'select'"
                v-model="mapping.visit.fixed[f.field]"
                :placeholder="f.placeholder || f.label"
              />
              <select v-else v-model="mapping.visit.fixed[f.field]">
                <option value="">— None —</option>
                <option v-for="opt in f.options || []" :key="'vfx-' + f.field + '-' + opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <details v-if="visitSchema.length">
        <summary>Detected visit schema fields</summary>
        <ul class="muted">
          <li v-for="f in visitSchema" :key="'visitpeek-' + f.field">
            {{ f.field }} ({{ f.type }})
          </li>
        </ul>
      </details>
    </section>

    <!-- STEP 6: eCRF Fields (Sections & Fields) -->
    <section v-if="headers.length" class="card">
      <h2>6) eCRF Fields (Sections & Fields)</h2>

      <!-- Auto-filled study title/description (editable) -->
      <div class="form-row full">
        <label>Study title <span class="muted">(auto-filled from metadata mapping when available)</span></label>
        <input
          v-model="studyMeta.name"
          @input="studyMetaEdited.name = true"
          placeholder="e.g., ADNI Baseline Import"
        />
      </div>
      <div class="form-row full">
        <label>Study description <span class="muted">(auto-filled from metadata mapping when available)</span></label>
        <input
          v-model="studyMeta.description"
          @input="studyMetaEdited.description = true"
          placeholder="Optional"
        />
      </div>

      <div class="form-row full">
        <label>Other fields to import as section fields</label>
        <div class="pillbox">
          <label
            v-for="h in otherFieldCandidates"
            :key="'oth-' + h"
            class="pill"
          >
            <input type="checkbox" :value="h" v-model="mapping.otherCols" />
            <span>{{ h }}</span>
          </label>
        </div>

        <label class="select-all">
          <input type="checkbox" v-model="otherAllSelected" @change="toggleSelectAllOther" />
          <span>{{ otherAllSelected ? 'Deselect all' : 'Select all' }}</span>
        </label>
      </div>
    </section>

    <!-- STEP 7: Infer + Preview -->
    <section class="card">
      <h2>7) Infer structure</h2>

      <div class="infer-controls">
        <button class="btn" @click="inferStructure" :disabled="!mapping.subject.idCol">
          Infer structure
        </button>

        <div class="bids-toggle" :class="{ disabled: saving }">
          <button
          type="button"
          class="toggle-btn"
          :class="{ on: createBidsOnImport }"
          :disabled="saving"
          @click="createBidsOnImport = !createBidsOnImport"
          :title="createBidsOnImport ? 'BIDS folder creation enabled' : 'BIDS folder creation disabled'"
        >
          <i :class="createBidsOnImport ? icons.toggleOn : icons.toggleOff"></i>
        </button>


          <div class="bids-toggle-text">
            <div class="bids-question">
              Do you want to create BIDS data folder for imported study data?
            </div>

            <div class="bids-warning">
              <i :class="icons.info"></i>
              <span>Creating folder structure for larger data files may take lot of time.</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="structureReady" class="structure">
        <div class="chips">
          <div class="chip"><strong>Subjects:</strong> {{ subjects.length }}</div>
          <div class="chip"><strong>Visits:</strong> {{ visits.length }}</div>
          <div class="chip"><strong>Groups:</strong> {{ groups.length }}</div>
          <div class="chip"><strong>Fields:</strong> {{ mapping.otherCols.length }}</div>
        </div>

        <details>
          <summary>Preview lists</summary>
          <div class="cols">
            <div>
              <h4>Subjects (first 20)</h4>
              <ul>
                <li v-for="s in subjects.slice(0, 20)" :key="s.id">
                  {{ s.id }} <span class="muted">/ {{ s.group }}</span>
                </li>
              </ul>
            </div>
            <div>
              <h4>Visits</h4>
              <ul><li v-for="v in visits" :key="v.name">{{ v.name }}</li></ul>
            </div>
            <div>
              <h4>Groups</h4>
              <ul><li v-for="g in groups" :key="g.name">{{ g.name }}</li></ul>
            </div>
          </div>
        </details>
      </div>
    </section>

    <!-- STEP 8: Save -->
    <section v-if="structureReady" class="card">
      <h2>8) Import</h2>
      <p class="muted">
        This will ① create the study template, then ② import {{ normalizedRows.length }} row(s) of data.
      </p>

      <button class="btn primary" @click="performSave" :disabled="saving">
        {{ saving ? 'Importing…' : 'Save Study & Data' }}
      </button>

      <div v-if="progress.total" class="progress">
        <div>Posted {{ progress.done }} / {{ progress.total }}</div>
        <div class="bar"><div class="fill" :style="{ width: (progress.done / progress.total * 100) + '%' }"></div></div>
      </div>

      <div v-if="saveError" class="error">{{ saveError }}</div>

      <div v-if="failures.length">
        <h3>Failures ({{ failures.length }})</h3>
        <table class="preview">
          <thead>
            <tr>
              <th>#</th><th>Subject</th><th>Visit</th><th>Group</th><th>Reason</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in failures" :key="f._ix">
              <td>{{ f._ix + 1 }}</td>
              <td>{{ f.subject }}</td>
              <td>{{ f.visit }}</td>
              <td>{{ f.group }}</td>
              <td><code>{{ f.reason }}</code></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="successStudyId && !saving" class="success">
        Imported!
        <button class="link" @click="$router.push({ name: 'StudyView', params: { id: successStudyId } })">
          Open Study
        </button>
      </div>
    </section>

    <div v-if="showFieldSchemaInfo" class="schema-modal-overlay" @click.self="showFieldSchemaInfo = false">
      <div class="schema-modal" role="dialog" aria-modal="true" aria-labelledby="field-schema-title">
        <div class="schema-modal-header">
          <div>
            <h3 id="field-schema-title">Field schema JSON example</h3>
            <p class="muted">
              Column names must exactly match the uploaded data headers. Fields omitted from this file use automatic inference.
            </p>
          </div>
          <button type="button" class="schema-modal-close" aria-label="Close" @click="showFieldSchemaInfo = false">×</button>
        </div>

        <pre class="schema-example"><code>{{ fieldSchemaExampleText }}</code></pre>

        <div class="schema-example-notes muted">
          Supported types: text, textarea, number, checkbox, radio, date, time, select, and slider.
          Use constraints for required fields, numeric ranges, steps, defaults, and date formats.
        </div>

        <div class="schema-modal-actions">
          <button type="button" class="btn" @click="copyFieldSchemaExample">
            {{ schemaCopyStatus || 'Copy JSON' }}
          </button>
          <button type="button" class="btn" @click="downloadFieldSchemaExample">Download example JSON</button>
          <button type="button" class="btn primary" @click="showFieldSchemaInfo = false">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
/* eslint-disable */
import { read, utils } from "xlsx";
import Papa from "papaparse";
import axios from "axios";
import yaml from "js-yaml";
import { useStore } from "vuex";
import icons from "@/assets/styles/icons";

export default {
  name: "ImportStudy",
  setup() {
    const store = useStore();
    return { store };
  },
  data() {
    return {
      icons,

      // BIDS folder creation toggle (default OFF)
      createBidsOnImport: false,

      // file/preview
      fileName: "",
      fieldSchemaFileName: "",
      fieldSchema: null,
      fieldSchemaError: "",
      fieldSchemaAppliedCount: 0,
      showFieldSchemaInfo: false,
      schemaCopyStatus: "",
      headers: [],
      rows: [],
      previewRows: [],
      rowCount: 0,

      // columns meta
      columns: [],
      columnMeta: new Map(),     // Map<label, {section, field, name}]
      resolvedImportFields: new Map(),

      // mapping (metadata + subject + eCRF)
      mapping: {
        study: { cols: {}, fixed: {} },
        group: { nameCol: "", cols: {}, fixed: {} },  // <-- name column here
        visit: { nameCol: "", cols: {}, fixed: {} },  // <-- name column here
        subject: { idCol: "", dateCol: "" },          // <-- removed visit/group here
        otherCols: []
      },
      otherAllSelected: false,

      // YAML schemas
      studySchema: [],
      groupSchema: [],
      visitSchema: [],

      // eCRF title/description (editable in step 6)
      studyMeta: { name: "", description: "" },
      studyMetaEdited: { name: false, description: false },

      // inferred structure
      subjects: [],
      visits: [],
      groups: [],
      normalizedRows: [],
      structureReady: false,

      // saving
      saving: false,
      progress: { total: 0, done: 0 },
      failures: [],
      saveError: "",
      successStudyId: null,

      // known keys to mirror (robust to schema names)
      TITLE_KEYS: ["study_name", "title", "study_title", "name", "short_name"],
      DESC_KEYS: ["study_description", "description", "study_desc", "desc"],
    };
  },
  computed: {
    token() {
      return this.store.state.token;
    },
    currentUserId() {
      return this.store.state.user?.id || null;
    },
    otherFieldCandidates() {
      const explicitFieldColumns = new Set(
        (this.fieldSchema?.fields || []).map(field => field.column)
      );
      const exclude = new Set(
        [
          this.mapping.subject.idCol,
          this.mapping.group.nameCol,
          this.mapping.visit.nameCol,
          explicitFieldColumns.has(this.mapping.subject.dateCol)
            ? ""
            : this.mapping.subject.dateCol,
        ].filter(Boolean)
      );
      return this.headers.filter(h => !exclude.has(h));
    },
    fieldSchemaExampleText() {
      return JSON.stringify(this.fieldSchemaExampleObject(), null, 2);
    },
  },
  watch: {
    // Mirror study metadata → eCRF fields whenever mapping changes
    "mapping.study": {
      handler() {
        this.autofillStudyMetaFromMapping(false);
      },
      deep: true
    }
  },
  async mounted() {
    await Promise.all([
      this.loadYaml("/study_schema.yaml", "studySchema"),
      this.loadYaml("/group_schema.yaml", "groupSchema"),
      this.loadYaml("/visit_schema.yaml", "visitSchema"),
    ]);
    // initial auto-fill if user sets fixed values before upload
    this.autofillStudyMetaFromMapping(true);
  },
  methods: {
    // ---------- YAML ----------
    async loadYaml(path, targetKey) {
      try {
        const res = await fetch(path);
        const doc = yaml.load(await res.text());
        const cls = Object.keys(doc.classes || {})[0];
        const attrs = (doc.classes?.[cls]?.attributes) || {};
        const fmt = (s) => String(s || "")
          .replace(/_/g, " ")
          .replace(/\b\w/g, ch => ch.toUpperCase());

        this[targetKey] = Object.entries(attrs).map(([n, d]) => {
          let type = d.widget === "textarea" ? "textarea" : "text";
          const r = (d.range || "").toLowerCase();
          if (r === "date" || r === "datetime") type = "date";
          if (r === "integer" || r === "decimal") type = "number";
          if (d.enum) type = "select";
          return {
            field: n,
            label: fmt(n),
            placeholder: d.description || fmt(n),
            type,
            required: !!d.required,
            disabled: !!d.disabled,
            display: d.display !== false,
            options: d.enum || []
          };
        });
      } catch {
        this[targetKey] = [];
      }
    },

    // ---------- File ingest ----------
    onFile(e) {
      const file = e.target.files?.[0];
      if (!file) return;

      this.resetAfterFile();
      this.fileName = file.name;
      const ext = (file.name.split(".").pop() || "").toLowerCase();

      if (["xlsx", "xls"].includes(ext)) {
        const reader = new FileReader();
        reader.onload = (evt) => {
          try {
            const wb = read(evt.target.result, { type: "array" });
            const ws = wb.Sheets[wb.SheetNames[0]];
            const matrix = utils.sheet_to_json(ws, { header: 1, defval: null });
            this.ingestFromMatrix(matrix);
          } catch (err) {
            console.error("[Import] XLSX parse error:", err);
            this.saveError = "Could not parse Excel file.";
          }
        };
        reader.readAsArrayBuffer(file);
      } else {
        Papa.parse(file, {
          header: false,
          skipEmptyLines: "greedy",
          complete: (res) => this.ingestFromMatrix(res.data || []),
          error: (err) => {
            console.error("[Import] CSV parse error:", err);
            this.saveError = "Could not parse CSV file.";
          }
        });
      }
    },

    onFieldSchemaFile(e) {
      const file = e.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const parsed = JSON.parse(String(event.target?.result || ""));
          this.fieldSchema = this.normalizeFieldSchemaDocument(parsed);
          this.fieldSchemaFileName = file.name;
          this.fieldSchemaError = "";
          this.structureReady = false;
          this.applyFieldSchemaToCurrentHeaders();
        } catch (error) {
          this.fieldSchema = null;
          this.fieldSchemaFileName = "";
          this.fieldSchemaAppliedCount = 0;
          this.fieldSchemaError = error?.message || "Could not parse field schema JSON.";
        } finally {
          e.target.value = "";
        }
      };
      reader.onerror = () => {
        this.fieldSchemaError = "Could not read field schema JSON.";
        e.target.value = "";
      };
      reader.readAsText(file);
    },

    normalizeFieldSchemaDocument(document) {
      if (!document || typeof document !== "object" || Array.isArray(document)) {
        throw new Error("Field schema JSON must contain an object.");
      }
      if (!Array.isArray(document.fields) || !document.fields.length) {
        throw new Error('Field schema JSON must contain a non-empty "fields" array.');
      }

      const typeAliases = {
        string: "text",
        integer: "number",
        decimal: "number",
        boolean: "checkbox",
        dropdown: "select",
      };
      const supportedTypes = new Set([
        "text", "textarea", "number", "checkbox", "radio",
        "date", "time", "select", "slider",
      ]);
      const seenColumns = new Set();
      const shorthandConstraints = [
        "required", "readonly", "min", "max", "step", "minLength", "maxLength",
        "dateFormat", "minDate", "maxDate", "defaultValue", "allowMultiple",
      ];

      const fields = document.fields.map((rawField, index) => {
        if (!rawField || typeof rawField !== "object" || Array.isArray(rawField)) {
          throw new Error(`Field schema item ${index + 1} must be an object.`);
        }

        const column = String(rawField.column || "").trim();
        if (!column) throw new Error(`Field schema item ${index + 1} is missing "column".`);
        if (seenColumns.has(column)) throw new Error(`Field schema contains duplicate column "${column}".`);
        seenColumns.add(column);

        const requestedType = String(rawField.type || "").trim().toLowerCase();
        const type = typeAliases[requestedType] || requestedType;
        if (!supportedTypes.has(type)) {
          throw new Error(`Unsupported type "${rawField.type || ""}" for column "${column}".`);
        }

        if (rawField.options != null && !Array.isArray(rawField.options)) {
          throw new Error(`Options for column "${column}" must be an array.`);
        }
        if (
          rawField.constraints != null &&
          (typeof rawField.constraints !== "object" || Array.isArray(rawField.constraints))
        ) {
          throw new Error(`Constraints for column "${column}" must be an object.`);
        }

        const constraints = { ...(rawField.constraints || {}) };
        shorthandConstraints.forEach((key) => {
          if (rawField[key] !== undefined && constraints[key] === undefined) {
            constraints[key] = rawField[key];
          }
        });

        return {
          column,
          type,
          section: String(rawField.section || "").trim(),
          name: String(rawField.name || "").trim(),
          label: String(rawField.label || "").trim(),
          description: String(rawField.description || ""),
          placeholder: String(rawField.placeholder || ""),
          options: Array.isArray(rawField.options) ? rawField.options : [],
          constraints,
        };
      });

      return { version: document.version || 1, fields };
    },

    applyFieldSchemaToCurrentHeaders() {
      this.fieldSchemaAppliedCount = 0;
      if (!this.fieldSchema) {
        this.fieldSchemaError = "";
        return;
      }
      if (!this.headers.length) return;

      const headerSet = new Set(this.headers);
      const unknownColumns = this.fieldSchema.fields
        .map(field => field.column)
        .filter(column => !headerSet.has(column));
      if (unknownColumns.length) {
        this.fieldSchemaError = `Schema column(s) not found in the data file: ${unknownColumns.join(", ")}`;
        return;
      }

      this.fieldSchemaError = "";
      const structuralColumns = new Set([
        this.mapping.subject.idCol,
        this.mapping.group.nameCol,
        this.mapping.visit.nameCol,
      ].filter(Boolean));
      const explicitColumns = this.fieldSchema.fields
        .map(field => field.column)
        .filter(column => !structuralColumns.has(column));
      this.mapping.otherCols = Array.from(new Set([
        ...this.mapping.otherCols,
        ...explicitColumns,
      ]));
      this.fieldSchemaAppliedCount = this.fieldSchema.fields.length;
      this.otherAllSelected = this.otherFieldCandidates.length > 0 &&
        this.otherFieldCandidates.every(column => this.mapping.otherCols.includes(column));
    },

    clearFieldSchema() {
      const mappedDateColumn = this.mapping.subject.dateCol;
      this.fieldSchema = null;
      this.fieldSchemaFileName = "";
      this.fieldSchemaError = "";
      this.fieldSchemaAppliedCount = 0;
      this.schemaCopyStatus = "";
      if (mappedDateColumn) {
        this.mapping.otherCols = this.mapping.otherCols.filter(column => column !== mappedDateColumn);
      }
      this.otherAllSelected = false;
      this.structureReady = false;
    },

    fieldSchemaExampleObject() {
      return {
        version: 1,
        fields: [
          {
            column: "Site Code",
            name: "site_code",
            label: "Site Code",
            section: "Visit Information",
            description: "Identifier of the study site.",
            placeholder: "SITE-01",
            type: "text",
            constraints: {
              required: true,
              readonly: false,
              helpText: "Use the assigned site code.",
              placeholder: "SITE-01",
              defaultValue: "",
              minLength: 7,
              maxLength: 12,
              pattern: "^SITE-[0-9]+$",
              transform: "uppercase",
            },
          },
          {
            column: "Clinical Notes",
            name: "clinical_notes",
            label: "Clinical Notes",
            section: "Visit Information",
            description: "Free-text clinical observations.",
            placeholder: "Enter relevant observations",
            type: "textarea",
            constraints: {
              required: false,
              readonly: false,
              helpText: "Do not enter directly identifying information.",
              placeholder: "Enter relevant observations",
              defaultValue: "",
              minLength: 0,
              maxLength: 2000,
              pattern: ".*",
              transform: "none",
            },
          },
          {
            column: "Age (years)",
            name: "age_years",
            label: "Age (years)",
            section: "Demographics",
            description: "Age at assessment in completed years.",
            placeholder: "18",
            type: "number",
            constraints: {
              required: true,
              readonly: false,
              helpText: "Enter whole years.",
              placeholder: "18",
              defaultValue: "",
              min: 0,
              max: 120,
              step: 1,
              integerOnly: true,
              minDigits: 1,
              maxDigits: 3,
            },
          },
          {
            column: "Informed Consent",
            name: "informed_consent",
            label: "Informed Consent",
            section: "Eligibility",
            description: "Whether informed consent was obtained.",
            type: "checkbox",
            constraints: {
              required: true,
              readonly: false,
              helpText: "Checked means consent was obtained.",
              defaultValue: false,
            },
          },
          {
            column: "Symptoms",
            name: "symptoms",
            label: "Symptoms",
            section: "Assessment",
            description: "Select all symptoms reported by the subject.",
            placeholder: "Select one or more symptoms",
            type: "radio",
            options: ["None", "Mild", "Moderate", "Severe"],
            constraints: {
              required: false,
              readonly: false,
              helpText: "The dominant option None clears other selections.",
              placeholder: "Select one or more symptoms",
              defaultValue: ["None"],
              allowMultiple: true,
              dominantOptions: ["None"],
            },
          },
          {
            column: "Assessment Date",
            name: "assessment_date",
            label: "Assessment Date",
            section: "Visit Information",
            description: "Date on which the assessment occurred.",
            placeholder: "yyyy-MM-dd",
            type: "date",
            constraints: {
              required: true,
              readonly: false,
              helpText: "Use ISO date format.",
              placeholder: "yyyy-MM-dd",
              defaultValue: "2025-01-01",
              dateFormat: "yyyy-MM-dd",
              minDate: "2020-01-01",
              maxDate: "2030-12-31",
            },
          },
          {
            column: "Assessment Time",
            name: "assessment_time",
            label: "Assessment Time",
            section: "Visit Information",
            description: "Time at which the assessment occurred.",
            placeholder: "HH:mm",
            type: "time",
            constraints: {
              required: false,
              readonly: false,
              helpText: "Use 24-hour time.",
              placeholder: "HH:mm",
              defaultValue: "09:00",
              hourCycle: "24",
              minTime: "00:00",
              maxTime: "23:59",
              step: 60,
            },
          },
          {
            column: "Sex",
            name: "sex",
            label: "Sex",
            section: "Demographics",
            description: "Recorded sex category.",
            placeholder: "Select a value",
            type: "select",
            options: ["Female", "Male", "Other"],
            constraints: {
              required: true,
              readonly: false,
              helpText: "Choose one option.",
              placeholder: "Select a value",
              defaultValue: "Other",
            },
          },
          {
            column: "Pain Score",
            name: "pain_score",
            label: "Pain Score",
            section: "Assessment",
            description: "Pain intensity from 0 to 10.",
            type: "slider",
            constraints: {
              required: false,
              readonly: false,
              helpText: "0 means no pain and 10 means worst pain.",
              mode: "slider",
              percent: false,
              min: 0,
              max: 10,
              step: 1,
              showTicks: true,
              marks: [
                { value: 0, label: "No pain" },
                { value: 5, label: "Moderate" },
                { value: 10, label: "Worst pain" },
              ],
            },
          },
          {
            column: "Quality Rating",
            name: "quality_rating",
            label: "Quality Rating",
            section: "Assessment",
            description: "Example of the Likert variant of a slider field.",
            type: "slider",
            constraints: {
              required: false,
              readonly: false,
              helpText: "Choose one point on the scale.",
              mode: "linear",
              min: 1,
              max: 5,
              leftLabel: "Very poor",
              rightLabel: "Excellent",
            },
          },
        ],
      };
    },

    async copyFieldSchemaExample() {
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(this.fieldSchemaExampleText);
        } else {
          const textarea = document.createElement("textarea");
          textarea.value = this.fieldSchemaExampleText;
          textarea.style.position = "fixed";
          textarea.style.opacity = "0";
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand("copy");
          textarea.remove();
        }
        this.schemaCopyStatus = "Copied";
      } catch {
        this.schemaCopyStatus = "Copy failed";
      }
      window.setTimeout(() => { this.schemaCopyStatus = ""; }, 1600);
    },

    downloadFieldSchemaExample() {
      const blob = new Blob([`${this.fieldSchemaExampleText}\n`], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "field-schema.example.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },

    ingestFromMatrix(matrix) {
      if (!Array.isArray(matrix) || !matrix.length) {
        this.saveError = "No rows found.";
        return;
      }

      const trim = v => (v == null ? null : String(v).trim());
      const rows = matrix.map(r => (Array.isArray(r) ? r.map(trim) : []));

      // two-row header detection
      const r0 = rows[0] || [];
      const r1 = rows[1] || [];
      const nonEmpty0 = r0.filter(x => x).length;
      const nonEmpty1 = r1.filter(x => x).length;
      const uniq0 = new Set(r0.filter(x => x)).size;
      const uniq1 = new Set(r1.filter(x => x)).size;

      const looksTwoHeader =
        rows.length >= 3 &&
        nonEmpty0 > 0 && nonEmpty1 > 0 &&
        uniq1 / Math.max(1, nonEmpty1) >= 0.6 &&
        (uniq0 / Math.max(1, nonEmpty0)) <= 0.8 &&
        nonEmpty1 >= 3;

      // build columns meta
      const cols = [];
      const labelJoin = (a, b) => (a && b) ? `${a} — ${b}` : (a || b || "");
      const DEFAULT_SECTION = "Imported Fields";

      if (looksTwoHeader) {
        const top = r0;
        const second = r1;
        const width = Math.max(top.length, second.length);
        for (let i = 0; i < width; i++) {
          const section = (top[i] || DEFAULT_SECTION);
          const field = (second[i] || `Field_${i + 1}`);
          const label = labelJoin(section, field);
          cols.push({ idx: i, section, field, label, name: this.toName(field) });
        }
        const dataRows = rows.slice(2);
        this.rows = this.buildRowObjects(dataRows, cols);
      } else {
        const head = r0;
        const width = head.length;
        for (let i = 0; i < width; i++) {
          const field = head[i] || `Field_${i + 1}`;
          const section = DEFAULT_SECTION;
          const label = field;
          cols.push({ idx: i, section, field, label, name: this.toName(field) });
        }
        const dataRows = rows.slice(1);
        this.rows = this.buildRowObjects(dataRows, cols);
      }

      this.columns = cols;
      this.columnMeta = new Map(cols.map(c => [c.label, { section: c.section, field: c.field, name: c.name }]));
      this.headers = cols.map(c => c.label);

      this.rowCount = this.rows.length;
      this.previewRows = this.rows.slice(0, 20);

      // suggestions
      this.suggestColumnHints();

      // copy metadata mapping → eCRF fields
      this.autofillStudyMetaFromMapping(false);

      if (!this.studyMeta.name) {
        this.studyMeta.name = (this.fileName || "Imported Study").replace(/\.(csv|tsv|xlsx|xls)$/i, "");
      }

      this.applyFieldSchemaToCurrentHeaders();
    },

    buildRowObjects(dataRows, cols) {
      const out = [];
      for (const r of dataRows) {
        if (!Array.isArray(r)) continue;
        const obj = {};
        for (const c of cols) obj[c.label] = r[c.idx] ?? null;
        const hasAny = Object.values(obj).some(v => v != null && String(v).trim() !== "");
        if (hasAny) out.push(obj);
      }
      return out;
    },

    suggestColumnHints() {
      const H = this.headers;
      const findCol = (reList) => {
        const rx = new RegExp(reList.join("|"), "i");
        return H.find(h => rx.test(h)) || "";
      };
      this.mapping.subject.idCol    = findCol(["^subject$", "subject.?id", "^rid$", "^ptid$", "^participant", "^id$"]);
      this.mapping.group.nameCol    = findCol(["^group", "arm", "cohort", "treatment", "^site$", "center"]);
      this.mapping.visit.nameCol    = findCol(["^visit", "time.?point", "session", "wave", "phase", "viscode"]);
      this.mapping.subject.dateCol  = findCol(["date", "exam.?date", "visit.?date", "acq.?date"]);
    },

    // ---------- Metadata → eCRF mirroring ----------
    toName(s) {
      return String(s || "")
        .normalize("NFKD")
        .replace(/[^\w\s-]/g, "")
        .trim()
        .replace(/\s+/g, "_")
        .toLowerCase();
    },
    safeStr(v) { return v == null ? "" : String(v).trim(); },

    async postImportedEntry(studyId, item) {
      const headers = { Authorization: `Bearer ${this.token}` };
      let expectedRevisionToken = null;

      try {
        const { data: slot } = await axios.get(
          `/forms/studies/${studyId}/slot-data`,
          {
            headers,
            params: {
              subject_index: item.subject_index,
              visit_index: item.visit_index,
              group_index: item.group_index,
            },
          }
        );
        expectedRevisionToken = String(slot?.revision_token ?? "");
      } catch (error) {
        // The legacy database backend has no slot-data endpoint and does not
        // require revision tokens. Preserve compatibility with that backend.
        if (error?.response?.status !== 404 && error?.response?.status !== 405) {
          throw error;
        }
      }

      const params = { audit_label: "Study Data Import" };
      if (expectedRevisionToken !== null) {
        params.expected_revision_token = expectedRevisionToken;
      }

      await axios.post(
        `/forms/studies/${studyId}/data`,
        item,
        { headers, params }
      );
    },

    firstNonEmptyFromColumn(col) {
      if (!col) return "";
      for (const r of this.rows) {
        const v = this.safeStr(r[col]);
        if (v) return v;
      }
      return "";
    },

    getMappedValueFromKeys(keys) {
      // Prefer fixed values from mapping, else first non-empty value from mapped column
      for (const k of keys) {
        const fx = this.safeStr(this.mapping.study.fixed?.[k]);
        if (fx) return fx;
      }
      for (const k of keys) {
        const col = this.mapping.study.cols?.[k];
        if (col) {
          const v = this.firstNonEmptyFromColumn(col);
          if (v) return v;
        }
      }
      return "";
    },

    // fallback using schema if custom key names used in YAML
    findSchemaField(schemaArr, candidates) {
      if (!Array.isArray(schemaArr)) return null;
      const lc = new Set(candidates.map(s => s.toLowerCase()));
      const hit = schemaArr.find(f => lc.has(String(f.field).toLowerCase()));
      return hit ? hit.field : null;
    },
    getStudyMappedValueBySchema(fieldName) {
      const fx = this.safeStr(this.mapping.study.fixed?.[fieldName]);
      if (fx) return fx;
      const col = this.mapping.study.cols?.[fieldName];
      if (col) return this.firstNonEmptyFromColumn(col);
      return "";
    },

    autofillStudyMetaFromMapping(force = false) {
      // primary: look for common key aliases in mapping
      const titleVal = this.getMappedValueFromKeys(this.TITLE_KEYS);
      const descVal  = this.getMappedValueFromKeys(this.DESC_KEYS);

      if (titleVal && (force || !this.studyMetaEdited.name)) {
        this.studyMeta.name = titleVal;
      }
      if (descVal && (force || !this.studyMetaEdited.description)) {
        this.studyMeta.description = descVal;
      }

      // secondary: if still empty, try schema-derived names
      if (!this.studyMeta.name) {
        const titleField = this.findSchemaField(this.studySchema, this.TITLE_KEYS);
        if (titleField) {
          const v = this.getStudyMappedValueBySchema(titleField);
          if (v && (force || !this.studyMetaEdited.name)) this.studyMeta.name = v;
        }
      }
      if (!this.studyMeta.description) {
        const descField = this.findSchemaField(this.studySchema, this.DESC_KEYS);
        if (descField) {
          const v = this.getStudyMappedValueBySchema(descField);
          if (v && (force || !this.studyMetaEdited.description)) this.studyMeta.description = v;
        }
      }
    },

    // ---------- eCRF model building ----------
    isStrictDateValue(value) {
      const text = String(value ?? "").trim();
      let match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      let year, month, day;
      if (match) {
        year = Number(match[1]);
        month = Number(match[2]);
        day = Number(match[3]);
      } else {
        match = text.match(/^(\d{2})[.-](\d{2})[.-](\d{4})$/);
        if (!match) return false;
        day = Number(match[1]);
        month = Number(match[2]);
        year = Number(match[3]);
      }

      const date = new Date(Date.UTC(year, month - 1, day));
      return date.getUTCFullYear() === year &&
        date.getUTCMonth() === month - 1 &&
        date.getUTCDate() === day;
    },

    inferFieldType(samples) {
      let nums = 0, dates = 0, bools = 0, total = 0;
      for (const v of samples) {
        if (v == null || v === "") continue;
        total++;
        if (!isNaN(Number(v))) { nums++; continue; }
        if (["true","false","yes","no","y","n","0","1"].includes(String(v).toLowerCase())) { bools++; continue; }
        if (this.isStrictDateValue(v)) { dates++; continue; }
      }
      if (total && nums === total) return "number";
      if (total && dates === total) return "date";
      if (total && bools === total) return "checkbox";
      return "text";
    },

    fieldSchemaDefinitionForColumn(column) {
      return (this.fieldSchema?.fields || []).find(field => field.column === column) || null;
    },

    buildSelectedModels() {
      this.resolvedImportFields = new Map();
      const samplesByLabel = {};
      for (const k of this.mapping.otherCols) samplesByLabel[k] = [];
      for (const r of this.rows.slice(0, 200)) {
        for (const k of this.mapping.otherCols) samplesByLabel[k].push(r[k]);
      }

      const bySection = new Map();
      for (const label of this.mapping.otherCols) {
        const meta = this.columnMeta.get(label);
        if (!meta) continue;
        const definition = this.fieldSchemaDefinitionForColumn(label);
        const section = definition?.section || meta.section;
        const type = definition?.type || this.inferFieldType(samplesByLabel[label] || []);
        const arr = bySection.get(section) || [];
        const field = {
          name: definition?.name || meta.name,
          label: definition?.label || meta.field,
          description: definition?.description || "",
          type,
          options: definition?.options || [],
          constraints: { required: false, ...(definition?.constraints || {}) },
          placeholder: definition?.placeholder || ""
        };
        arr.push(field);
        this.resolvedImportFields.set(label, { section, field });
        bySection.set(section, arr);
      }

      const models = [];
      for (const [section, fields] of bySection.entries()) {
        models.push({ title: section, fields, source: "import" });
      }
      if (!models.length) {
        models.push({ title: "Imported Fields", fields: [], source: "import" });
      }
      return models;
    },

    buildAssignmentsMatrix(modelCount) {
      const visitCount = this.visits.length || 1;
      const groupCount = this.groups.length || 1;
      return Array.from({ length: modelCount }, () =>
        Array.from({ length: visitCount }, () => Array.from({ length: groupCount }, () => true))
      );
    },

    buildBidsBlock(selectedModels) {
      const pad = (n, w) => String(n).padStart(w, "0");
      const pretty = (s) => String(s || "").replace(/\s+/g, "_");

      const catalog = [];
      selectedModels.forEach((sec, sIdx) => {
        (sec.fields || []).forEach((f, fIdx) => {
          catalog.push({ sIdx, fIdx, name: `${pretty(sec.title)}.${pretty(f.label)}` });
        });
      });

      return {
        subject_label_map: Object.fromEntries(this.subjects.map((s, i) => [s.id, pad(i + 1, 3)])),
        session_label_map: Object.fromEntries(this.visits.map((v, i) => [v.name, pad(i + 1, 2)])),
        column_catalog: catalog
      };
    },

    packRowDataToDict(flatData) {
      const out = {};
      for (const [label, val] of Object.entries(flatData || {})) {
        const meta = this.columnMeta.get(label);
        if (!meta) continue;
        const resolved = this.resolvedImportFields.get(label);
        const section = resolved?.section || meta.section;
        const field = resolved?.field || { name: meta.name, type: "text", constraints: {} };
        if (!out[section]) out[section] = {};
        out[section][field.name || meta.name] = this.normalizeImportedFieldValue(val, field);
      }
      return out;
    },

    normalizeImportedFieldValue(value, field) {
      if (value == null || value === "") return value;
      const type = String(field?.type || "text").toLowerCase();
      const text = String(value).trim();

      if (type === "number" || type === "slider") {
        const number = Number(text.replace(/,/g, "."));
        return Number.isFinite(number) ? number : value;
      }

      if (type === "checkbox") {
        const normalized = text.toLowerCase();
        if (["true", "yes", "y", "1", "checked"].includes(normalized)) return true;
        if (["false", "no", "n", "0", "unchecked"].includes(normalized)) return false;
        return value;
      }

      if (
        (type === "select" || type === "radio") &&
        field?.constraints?.allowMultiple &&
        typeof value === "string"
      ) {
        return value.split(",").map(item => item.trim()).filter(Boolean);
      }

      return value;
    },

    // ---------- Structure inference ----------
    inferStructure() {
      this.saveError = "";
      this.failures = [];
      this.successStudyId = null;
      this.structureReady = false;

      if (this.fieldSchemaError) {
        this.saveError = "Please fix or remove the field schema JSON before inferring the study structure.";
        return;
      }

      if (!this.mapping.subject.idCol) {
        this.saveError = "Please map Subject ID column.";
        return;
      }

      const DEFAULT_VISIT = "Baseline";
      const DEFAULT_GROUP = "Group A";

      const subjSet = new Map();
      const visitSet = new Map();
      const groupSet = new Map();

      const normalized = [];

      const idCol     = this.mapping.subject.idCol;
      const visitCol  = this.mapping.visit.nameCol;   // moved here
      const groupCol  = this.mapping.group.nameCol;   // moved here
      const dateCol   = this.mapping.subject.dateCol;

      for (let i = 0; i < this.rows.length; i++) {
        const r = this.rows[i];

        const subjRaw = this.safeStr(r[idCol]);
        if (!subjRaw) continue;

        const visit = visitCol ? (this.safeStr(r[visitCol]) || DEFAULT_VISIT) : DEFAULT_VISIT;
        const group = groupCol ? (this.safeStr(r[groupCol]) || DEFAULT_GROUP) : DEFAULT_GROUP;

        const extra = {};
        for (const k of this.mapping.otherCols) extra[k] = r[k] ?? null;
        if (dateCol) extra.__date__ = r[dateCol] ?? null;

        normalized.push({ _ix: i, subject: subjRaw, visit, group, data: extra });

        if (!subjSet.has(subjRaw)) subjSet.set(subjRaw, subjSet.size);
        if (!visitSet.has(visit))  visitSet.set(visit, visitSet.size);
        if (!groupSet.has(group))  groupSet.set(group, groupSet.size);
      }

      const groupNames = Array.from(groupSet.keys());
      const visitNames = Array.from(visitSet.keys());

      // map group metadata
      const groupObjs = groupNames.map(name => {
        const obj = { name };
        for (const f of this.groupSchema) {
          if (f.display === false) continue;
          const fx = this.safeStr(this.mapping.group.fixed?.[f.field]);
          const col = this.mapping.group.cols?.[f.field];
          if (fx) obj[f.field] = fx;
          else if (col && groupCol) obj[f.field] = this.rows
            .map(r => ({ grp: this.safeStr(r[groupCol]), v: this.safeStr(r[col]) }))
            .find(x => x.grp === name && x.v)?.v || "";
          else if (col) obj[f.field] = this.firstNonEmptyFromColumn(col);
        }
        return obj;
      });

      // map visit metadata
      const visitObjs = visitNames.map(name => {
        const obj = { name };
        for (const f of this.visitSchema) {
          if (f.display === false) continue;
          const fx = this.safeStr(this.mapping.visit.fixed?.[f.field]);
          const col = this.mapping.visit.cols?.[f.field];
          if (fx) obj[f.field] = fx;
          else if (col && visitCol) obj[f.field] = this.rows
            .map(r => ({ vis: this.safeStr(r[visitCol]), v: this.safeStr(r[col]) }))
            .find(x => x.vis === name && x.v)?.v || "";
          else if (col) obj[f.field] = this.firstNonEmptyFromColumn(col);
        }
        return obj;
      });

      const subjFirstGroup = {};
      for (const row of normalized) if (!(row.subject in subjFirstGroup)) subjFirstGroup[row.subject] = row.group;
      const subjectObjs = Array.from(subjSet.keys()).map(id => ({ id, group: subjFirstGroup[id] || groupNames[0] || DEFAULT_GROUP }));

      this.groups = groupObjs;
      this.visits = visitObjs;
      this.subjects = subjectObjs;
      this.normalizedRows = normalized;
      this.structureReady = true;
    },

    // ---------- Save ----------
    async performSave() {
      this.saveError = "";
      this.failures = [];
      this.successStudyId = null;

      // Final sync safety: if eCRF fields empty, fill from mapping once more
      if (!this.studyMeta.name) {
        const t = this.getMappedValueFromKeys(this.TITLE_KEYS);
        if (t) this.studyMeta.name = t;
      }
      if (!this.studyMeta.description) {
        const d = this.getMappedValueFromKeys(this.DESC_KEYS);
        if (d) this.studyMeta.description = d;
      }

      if (!this.structureReady) { this.saveError = "Please infer structure first."; return; }
      if (!this.studyMeta.name.trim()) { this.saveError = "Please enter a study title."; return; }
      if (!this.currentUserId) {
        alert("Please log in again.");
        this.$router.push("/login");
        return;
      }

      const createBids = !!this.createBidsOnImport;
      const createBidsQS = `create_bids=${createBids ? 1 : 0}`;

      try {
        this.saving = true;

        const selectedModels = this.buildSelectedModels();
        const assignments = this.buildAssignmentsMatrix(selectedModels.length);

        const studyShell = {
          id: "",
          title: this.studyMeta.name,
          short_name: "",
          description: this.studyMeta.description || "",
          type: "",
          status: "",
          creator: "",
          publisher: "",
          "start time": "",
          "End time": "",
          "Location": ""
        };

        const study_data = {
          study: studyShell,
          groups: this.groups,
          visits: this.visits,
          subjects: this.subjects,
          subjectCount: this.subjects.length,
          assignmentMethod: "import",
          assignments,
          selectedModels,
          bids: this.buildBidsBlock(selectedModels)
        };

        const createPayload = {
          study_metadata: {
            created_by: this.currentUserId,
            study_name: this.studyMeta.name,
            study_description: this.studyMeta.description || "",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          study_content: { study_data }
        };

        // pass create_bids flag to study creation
        const { data: created } = await axios.post(
          `/forms/studies/?${createBidsQS}`,
          createPayload,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const studyId = created?.metadata?.id || created?.study_metadata?.id;
        if (!studyId) throw new Error("Failed to create study (no id returned).");

        this.progress.total = this.normalizedRows.length;
        this.progress.done = 0;

        const vMap = new Map(this.visits.map((v, i) => [v.name, i]));
        const gMap = new Map(this.groups.map((g, i) => [g.name, i]));
        const sMap = new Map(this.subjects.map((s, i) => [s.id, i]));

        const entries = this.normalizedRows.map((row) => {
          const nested = this.packRowDataToDict(row.data);
          return {
            subject_index: sMap.get(row.subject),
            visit_index: vMap.get(row.visit),
            group_index: gMap.get(row.group),
            data: nested,
            skipped_required_flags: [],
          };
        });

        const postBulk = async (chunk) => {
          const resp = await axios.post(
            `/forms/studies/${studyId}/data/bulk?${createBidsQS}`,   // gate BIDS mirroring here
            { entries: chunk },
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          return resp.data;
        };
        const postOne = async (item) => this.postImportedEntry(studyId, item);

        const CHUNK_SIZE = 1000;

        for (let i = 0; i < entries.length; i += CHUNK_SIZE) {
          const chunk = entries.slice(i, i + CHUNK_SIZE);
          try {
            await postBulk(chunk);
            this.progress.done += chunk.length;
          } catch (err) {
            if (err?.response?.status === 404 || err?.response?.status === 405) {
              const CONC = 6;
              let idx = 0;
              const workers = Array.from({ length: CONC }, () => (async () => {
                while (idx < chunk.length) {
                  const k = idx++;
                  try {
                    await postOne(chunk[k]);
                  } catch (e) {
                    const reason = e?.response?.data?.detail || e?.message || "Unknown error";
                    const original = this.normalizedRows[i + k] || {};
                    this.failures.push({ _ix: i + k, subject: original.subject, visit: original.visit, group: original.group, reason });
                  } finally {
                    this.progress.done += 1;
                  }
                }
              })());
              await Promise.all(workers);
            } else {
              const reason = err?.response?.data?.detail || err?.message || "Bulk insert failed";
              this.failures.push({ _ix: i, subject: "—", visit: "—", group: "—", reason });
              this.progress.done += chunk.length;
            }
          }
        }

        this.successStudyId = studyId;
      } catch (e) {
        console.error("[Import] Import failed:", e);
        this.saveError = e?.message || "Import failed.";
      } finally {
        this.saving = false;
      }
    },

    // ---------- Reset ----------
    resetAfterFile() {
      this.headers = [];
      this.rows = [];
      this.previewRows = [];
      this.rowCount = 0;
      this.columns = [];
      this.columnMeta = new Map();
      this.resolvedImportFields = new Map();
      this.mapping.subject = { idCol: "", dateCol: "" };
      this.mapping.group = { nameCol: "", cols: {}, fixed: {} };
      this.mapping.visit = { nameCol: "", cols: {}, fixed: {} };
      this.mapping.otherCols = [];
      this.otherAllSelected = false;
      this.subjects = [];
      this.visits = [];
      this.groups = [];
      this.normalizedRows = [];
      this.structureReady = false;
      this.saving = false;
      this.progress = { total: 0, done: 0 };
      this.failures = [];
      this.saveError = "";
      this.successStudyId = null;
      this.fieldSchemaError = "";
      this.fieldSchemaAppliedCount = 0;

      // keep default OFF on new file
      this.createBidsOnImport = false;
      // DO NOT clear studyMeta so user-typed values persist
    },

    toggleSelectAllOther() {
      if (this.otherAllSelected) {
        const exclude = new Set(
          [
            this.mapping.subject.idCol,
            this.mapping.group.nameCol,
            this.mapping.visit.nameCol,
            this.mapping.subject.dateCol
          ].filter(Boolean)
        );
        this.mapping.otherCols = this.headers.filter(h => !exclude.has(h));
      } else {
        this.mapping.otherCols = [];
      }
    },
  }
};
</script>

<style scoped>
/* keep layout from ever widening its parent */
.import-study {
  width: 100%;
  min-width: 0;
  max-width: 1100px;
  margin: 0 auto;
}

.sub { color:#666; margin-bottom: 12px; }

.card {
  border:1px solid #e7e7e7;
  border-radius:12px;
  padding:16px 18px;
  margin:14px 0;
  background:#fafafa;
  min-width: 0;
  max-width: 100%;
}

.upload-inputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 16px;
  align-items: start;
}

.upload-input-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
}

.upload-label {
  font-weight: 600;
  color: #333;
}

.schema-upload-heading,
.schema-file-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.schema-info-button,
.schema-modal-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: #2f6fed;
  cursor: pointer;
}

.schema-info-button {
  width: 30px;
  height: 30px;
  border-radius: 50%;
}

.schema-info-button:hover {
  background: #eff6ff;
}

.schema-clear-button {
  padding: 0;
}

.schema-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.55);
}

.schema-modal {
  width: min(820px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  padding: 20px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
}

.schema-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.schema-modal-header h3 {
  margin: 0 0 6px;
}

.schema-modal-close {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  color: #4b5563;
  font-size: 26px;
}

.schema-example {
  max-height: 420px;
  overflow: auto;
  margin: 16px 0 10px;
  padding: 14px;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #f8fafc;
  color: #172033;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre;
}

.schema-example-notes {
  line-height: 1.5;
}

.schema-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.grid { display:grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap:14px; min-width:0; }
.form-row { display:flex; flex-direction:column; gap:6px; min-width:0; }
.form-row.full { grid-column: 1 / -1; }
label { font-size: 13px; color:#444; }
input, select { padding:10px; border:1px solid #ddd; border-radius:8px; }
.muted { color:#777; font-size: 12px; }
.smalltop { margin-top: 6px; }

/* this is where horizontal scrolling must happen */
.table-scroll {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: auto;
  max-height: 280px;
  margin-top:10px;
  border:1px solid #eee;
  border-radius:8px;
  -webkit-overflow-scrolling: touch;
}

/* Keep default tables normal everywhere else */
.preview { border-collapse: collapse; width: 100%; }

/* only the preview table inside the scroll box should be allowed to be wider */
.table-scroll .preview {
  width: max-content;   /* force wide table -> horizontal scroll in .table-scroll */
  min-width: 100%;
}

.preview th, .preview td {
  border-bottom:1px solid #eee;
  padding:6px 8px;
  text-align:left;
  font-size:12px;
  white-space: nowrap;
}

.structure .chips { display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }
.chip { background:#fff; border:1px solid #e1e1e1; border-radius:999px; padding:6px 10px; font-size:12px; }
.cols { display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; margin-top:10px; min-width:0; }

.btn { border:1px solid #ddd; padding:10px 14px; border-radius:8px; cursor:pointer; background:#fff; }
.btn.primary { background:#2f6fed; color:#fff; border-color:#245fe0; }
.btn:disabled { opacity:.6; cursor:not-allowed; }

.progress { margin-top: 12px; }
.bar { height: 10px; background:#eee; border-radius: 999px; overflow:hidden; }
.fill { height: 100%; background:#2f6fed; }

.error { color:#b00020; margin-top: 10px; }
.success { margin-top: 12px; }
.link { background:none; border:none; color:#2f6fed; cursor:pointer; text-decoration: underline; }
.hint { color:#555; margin-top:6px; }

@media (max-width: 760px) {
  .upload-inputs {
    grid-template-columns: 1fr;
  }
}

/* schema mapping grid */
.schema-grid { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 8px; min-width:0; }
.schema-map-row { display: grid; grid-template-columns: 220px 1fr; gap: 12px; align-items: center; background:#fff; border:1px solid #eee; border-radius:10px; padding:10px; min-width:0; }
.schema-map-label { display:flex; align-items:center; gap:6px; min-width:0; }
.schema-map-label .lbl { font-weight:600; color:#333; font-size: 13px; }
.schema-map-label .req { color:#b00020; font-size: 12px; }
.schema-map-ctrls { display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 10px; min-width:0; }
.schema-map-ctrl { display:flex; flex-direction:column; gap:6px; min-width:0; }
.schema-map-ctrl .small { font-size: 11px; color:#777; }

.pillbox { display:flex; flex-wrap:wrap; gap:8px; margin-top: 6px; min-width:0; }
.pill { border:1px solid #ddd; padding:6px 8px; border-radius:999px; background:#fff; font-size:12px; }
.select-all { display:flex; gap:8px; align-items:center; margin-top:8px; }

/* NEW: Infer row controls */
.infer-controls {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex-wrap: wrap;
}

.bids-toggle {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 10px;
  min-width: 260px;
  max-width: 560px;
}

.bids-toggle.disabled {
  opacity: .6;
}

/* BIDS toggle button */
.toggle-btn {
  border: none;
  background: transparent;
  padding: 6px 10px;
  border-radius: 999px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

/* BIGGER toggle icon */
.toggle-btn i {
  font-size: 26px;   /* increased size */
  line-height: 1;
}

/* ON state: blue background */
.toggle-btn.on {
  background-color: #2f6fed;      /* project primary blue */
  box-shadow: 0 0 0 2px rgba(47, 111, 237, 0.25);
}

/* ON state icon color */
.toggle-btn.on i {
  color: #ffffff;
}

/* OFF state icon color */
.toggle-btn:not(.on) i {
  color: #9ca3af; /* subtle gray */
}

/* Disabled state */
.toggle-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}


.bids-toggle-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.bids-question {
  font-size: 12px;
  color: #333;
}

.bids-warning {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #777;
}

.bids-warning i {
  font-size: 14px;
}
</style>
