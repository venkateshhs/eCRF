<template>
  <div class="import-study">
    <!-- STEP 1: Upload -->
    <section class="card">
      <h2>1) Upload file</h2>
      <input type="file" accept=".csv,.tsv,.xlsx,.xls" @change="onFile" />
      <div v-if="fileName" class="hint">Loaded: {{ fileName }} ({{ rowCount }} rows)</div>

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
      <button class="btn" @click="inferStructure" :disabled="!mapping.subject.idCol">
        Infer structure
      </button>

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
  </div>
</template>

<script>
/* eslint-disable */
import { read, utils } from "xlsx";
import Papa from "papaparse";
import axios from "axios";
import yaml from "js-yaml";
import { useStore } from "vuex";

export default {
  name: "ImportStudy",
  setup() {
    const store = useStore();
    return { store };
  },
  data() {
    return {
      // file/preview
      fileName: "",
      headers: [],
      rows: [],
      previewRows: [],
      rowCount: 0,

      // columns meta
      columns: [],
      columnMeta: new Map(),     // Map<label, {section, field, name}]

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
      const exclude = new Set(
        [
          this.mapping.subject.idCol,
          this.mapping.group.nameCol,
          this.mapping.visit.nameCol,
          this.mapping.subject.dateCol,
        ].filter(Boolean)
      );
      return this.headers.filter(h => !exclude.has(h));
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
    inferFieldType(samples) {
      let nums = 0, dates = 0, bools = 0, total = 0;
      for (const v of samples) {
        if (v == null || v === "") continue;
        total++;
        if (!isNaN(Number(v))) { nums++; continue; }
        const d = new Date(v); if (!isNaN(d.getTime())) { dates++; continue; }
        if (["true","false","yes","no","y","n","0","1"].includes(String(v).toLowerCase())) { bools++; continue; }
      }
      if (total && nums === total) return "number";
      if (total && dates === total) return "date";
      if (total && bools === total) return "boolean";
      return "text";
    },

    buildSelectedModels() {
      const samplesByLabel = {};
      for (const k of this.mapping.otherCols) samplesByLabel[k] = [];
      for (const r of this.rows.slice(0, 200)) {
        for (const k of this.mapping.otherCols) samplesByLabel[k].push(r[k]);
      }

      const bySection = new Map();
      for (const label of this.mapping.otherCols) {
        const meta = this.columnMeta.get(label);
        if (!meta) continue;
        const type = this.inferFieldType(samplesByLabel[label] || []);
        const arr = bySection.get(meta.section) || [];
        arr.push({
          name: meta.name,
          label: meta.field,
          description: "",
          type, options: [],
          constraints: { required: false },
          placeholder: ""
        });
        bySection.set(meta.section, arr);
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
        if (!out[meta.section]) out[meta.section] = {};
        out[meta.section][meta.name] = val;
      }
      return out;
    },

    // ---------- Structure inference ----------
    inferStructure() {
      this.saveError = "";
      this.failures = [];
      this.successStudyId = null;
      this.structureReady = false;

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

        const { data: created } = await axios.post(
          "/forms/studies/",
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
            `/forms/studies/${studyId}/data/bulk`,
            { entries: chunk },
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          return resp.data;
        };
        const postOne = async (item) => {
          await axios.post(
            `/forms/studies/${studyId}/data`,
            item,
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
        };

        const CHUNK_SIZE = 1000;
        let usedBulk = true;

        for (let i = 0; i < entries.length; i += CHUNK_SIZE) {
          const chunk = entries.slice(i, i + CHUNK_SIZE);
          try {
            await postBulk(chunk);
            this.progress.done += chunk.length;
          } catch (err) {
            if (err?.response?.status === 404 || err?.response?.status === 405) {
              usedBulk = false;
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
.import-study { max-width: 1100px; margin: 0 auto; }
.sub { color:#666; margin-bottom: 12px; }

.card { border:1px solid #e7e7e7; border-radius:12px; padding:16px 18px; margin:14px 0; background:#fafafa; }
.grid { display:grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap:14px; }
.form-row { display:flex; flex-direction:column; gap:6px; }
.form-row.full { grid-column: 1 / -1; }
label { font-size: 13px; color:#444; }
input, select { padding:10px; border:1px solid #ddd; border-radius:8px; }
.muted { color:#777; font-size: 12px; }
.smalltop { margin-top: 6px; }
.table-scroll { overflow:auto; max-height: 280px; margin-top:10px; border:1px solid #eee; border-radius:8px; }

.preview { border-collapse: collapse; width: 100%; }
.preview th, .preview td { border-bottom:1px solid #eee; padding:6px 8px; text-align:left; font-size:12px; }

.structure .chips { display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }
.chip { background:#fff; border:1px solid #e1e1e1; border-radius:999px; padding:6px 10px; font-size:12px; }
.cols { display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; margin-top:10px; }

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

/* schema mapping grid */
.schema-grid { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 8px; }
.schema-map-row { display: grid; grid-template-columns: 220px 1fr; gap: 12px; align-items: center; background:#fff; border:1px solid #eee; border-radius:10px; padding:10px; }
.schema-map-label { display:flex; align-items:center; gap:6px; }
.schema-map-label .lbl { font-weight:600; color:#333; font-size: 13px; }
.schema-map-label .req { color:#b00020; font-size: 12px; }
.schema-map-ctrls { display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 10px; }
.schema-map-ctrl { display:flex; flex-direction:column; gap:6px; }
.schema-map-ctrl .small { font-size: 11px; color:#777; }

.pillbox { display:flex; flex-wrap:wrap; gap:8px; margin-top: 6px; }
.pill { border:1px solid #ddd; padding:6px 8px; border-radius:999px; background:#fff; font-size:12px; }
.select-all { display:flex; gap:8px; align-items:center; margin-top:8px; }
</style>
