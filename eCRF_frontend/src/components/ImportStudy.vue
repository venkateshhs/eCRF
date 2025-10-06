<template>
  <div class="import-study">
    <h1>Import Study</h1>
    <p class="sub">Upload a CSV or Excel file and map columns to create a study and import entries (template first, then data).</p>

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

    <!-- STEP 2: Mapping -->
    <section v-if="headers.length" class="card">
      <h2>2) Map columns</h2>

      <div class="grid">
        <div class="form-row">
          <label>Subject ID column</label>
          <select v-model="mapping.subjectCol">
            <option value="">— Select —</option>
            <option v-for="h in headers" :key="h" :value="h">{{ h }}</option>
          </select>
        </div>

        <div class="form-row">
          <label>Visit column (optional)</label>
          <select v-model="mapping.visitCol">
            <option value="">— None (single visit) —</option>
            <option v-for="h in headers" :key="h" :value="h">{{ h }}</option>
          </select>
        </div>

        <div class="form-row">
          <label>Group column (optional)</label>
          <select v-model="mapping.groupCol">
            <option value="">— None (single group) —</option>
            <option v-for="h in headers" :key="h" :value="h">{{ h }}</option>
          </select>
        </div>

        <div class="form-row">
          <label>Date column (optional)</label>
          <select v-model="mapping.dateCol">
            <option value="">— None —</option>
            <option v-for="h in headers" :key="h" :value="h">{{ h }}</option>
          </select>
        </div>

        <div class="form-row full">
          <label>Other fields to import as eCRF fields</label>
          <div class="pillbox">
            <label v-for="h in otherFieldCandidates" :key="h" class="pill">
              <input type="checkbox" :value="h" v-model="mapping.otherCols" />
              <span>{{ h }}</span>
            </label>
          </div>

          <label class="select-all">
            <input type="checkbox" v-model="otherAllSelected" @change="toggleSelectAllOther" />
            <span>{{ otherAllSelected ? 'Deselect all' : 'Select all' }}</span>
          </label>
        </div>

        <div class="form-row full">
          <label>Study title</label>
          <input v-model="studyMeta.name" placeholder="e.g., ADNI Baseline Import" />
        </div>
        <div class="form-row full">
          <label>Study description</label>
          <input v-model="studyMeta.description" placeholder="Optional" />
        </div>
      </div>

      <button class="btn" @click="inferStructure" :disabled="!mapping.subjectCol">Infer structure</button>

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
              <ul><li v-for="s in subjects.slice(0,20)" :key="s.id">{{ s.id }} <span class="muted">/ {{ s.group }}</span></li></ul>
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

    <!-- STEP 3: Save -->
    <section v-if="structureReady" class="card">
      <h2>3) Import</h2>
      <p class="muted">
        This will ① create the study template, then ② import {{ normalizedRows.length }} row(s) of data.
      </p>

      <button class="btn primary" @click="performSave" :disabled="saving">
        {{ saving ? 'Importing…' : 'Save Study & Data' }}
      </button>

      <div v-if="progress.total" class="progress">
        <div>Posted {{ progress.done }} / {{ progress.total }}</div>
        <div class="bar"><div class="fill" :style="{ width: (progress.done/progress.total*100)+'%' }"></div></div>
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
        ✅ Imported!&nbsp;
        <button class="link" @click="$router.push({ name: 'StudyView', params: { id: successStudyId } })">
          Open Study
        </button>
      </div>
    </section>
  </div>
</template>

<script>
import { read, utils } from "xlsx";
import Papa from "papaparse";
import axios from "axios";
import { useStore } from "vuex";
import { useRouter } from "vue-router";

export default {
  name: "ImportStudy",
  setup() {
    const store = useStore();
    const router = useRouter();
    return { store, router };
  },
  data() {
    return {
      // file/preview
      fileName: "",
      headers: [],
      rows: [],             // array of row objects keyed by headers[]
      previewRows: [],
      rowCount: 0,

      // detected columns meta (drives headers)
      // [{ idx, section, field, label, name }]
      columns: [],
      // Map<label, {section, field, name}>
      columnMeta: new Map(),

      // mapping
      mapping: { subjectCol: "", visitCol: "", groupCol: "", dateCol: "", otherCols: [] },
      otherAllSelected: false,

      // study meta
      studyMeta: { name: "", description: "" },

      // inferred structure
      subjects: [],
      visits: [],
      groups: [],
      normalizedRows: [],
      structureReady: false,

      // saving state
      saving: false,
      progress: { total: 0, done: 0 },
      failures: [],
      saveError: "",
      successStudyId: null,
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
        [this.mapping.subjectCol, this.mapping.visitCol, this.mapping.groupCol, this.mapping.dateCol].filter(Boolean)
      );
      return this.headers.filter(h => !exclude.has(h));
    },
  },
  methods: {
    // ---------- File ingest ----------
    onFile(e) {
      const file = e.target.files?.[0];
      if (!file) return;

      this.resetAll();
      this.fileName = file.name;
      const ext = (file.name.split(".").pop() || "").toLowerCase();

      console.log("[Import] Selected file:", file.name);

      if (["xlsx", "xls"].includes(ext)) {
        const reader = new FileReader();
        reader.onload = (evt) => {
          try {
            const wb = read(evt.target.result, { type: "array" });
            const ws = wb.Sheets[wb.SheetNames[0]];
            // 2D array (including header rows)
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
          header: false,                 // read as matrix so we can detect 1 vs 2 header rows
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

      // Trim all cells to strings (or null)
      const trim = v => (v == null ? null : String(v).trim());
      const rows = matrix.map(r => (Array.isArray(r) ? r.map(trim) : []));

      // Detect two header rows
      const r0 = rows[0] || [];
      const r1 = rows[1] || [];
      const nonEmpty0 = r0.filter(x => x).length;
      const nonEmpty1 = r1.filter(x => x).length;
      const uniq0 = new Set(r0.filter(x => x)).size;
      const uniq1 = new Set(r1.filter(x => x)).size;

      // Heuristic: second row looks like distinct field names,
      // first row has fewer unique values (repeating sections)
      const looksTwoHeader =
        rows.length >= 3 &&
        nonEmpty0 > 0 && nonEmpty1 > 0 &&
        uniq1 / Math.max(1, nonEmpty1) >= 0.6 &&
        (uniq0 / Math.max(1, nonEmpty0)) <= 0.8 &&
        nonEmpty1 >= 3;

      console.log("[Import] Header detection → two-row =", looksTwoHeader, { nonEmpty0, nonEmpty1, uniq0, uniq1 });

      // Build columns meta
      const cols = [];
      const labelJoin = (a, b) => (a && b) ? `${a} — ${b}` : (a || b || "");
      const DEFAULT_SECTION = "Imported Fields";

      if (looksTwoHeader) {
        const top = r0;
        const second = r1;
        const width = Math.max(top.length, second.length);
        for (let i = 0; i < width; i++) {
          const section = (top[i] || DEFAULT_SECTION);
          const field = (second[i] || `Field_${i+1}`);
          const label = labelJoin(section, field);
          cols.push({ idx: i, section, field, label, name: this.toName(field) });
        }
        // Data rows start at row 2
        const dataRows = rows.slice(2);
        this.rows = this.buildRowObjects(dataRows, cols);
      } else {
        const head = r0;
        const width = head.length;
        for (let i = 0; i < width; i++) {
          const field = head[i] || `Field_${i+1}`;
          const section = DEFAULT_SECTION;
          const label = field;
          cols.push({ idx: i, section, field, label, name: this.toName(field) });
        }
        // Data rows start at row 1
        const dataRows = rows.slice(1);
        this.rows = this.buildRowObjects(dataRows, cols);
      }

      // Store columns + meta
      this.columns = cols;
      this.columnMeta = new Map(cols.map(c => [c.label, { section: c.section, field: c.field, name: c.name }]));
      this.headers = cols.map(c => c.label);

      // Basic stats/preview
      this.rowCount = this.rows.length;
      this.previewRows = this.rows.slice(0, 20);

      // Auto-detect mapping suggestions from headers
      this.suggestMapping();

      if (!this.studyMeta.name) {
        this.studyMeta.name = (this.fileName || "Imported Study").replace(/\.(csv|tsv|xlsx|xls)$/i, "");
      }

      console.log("[Import] Detected columns:", this.columns);
      console.log("[Import] Headers:", this.headers);
      console.log("[Import] Preview row 1:", this.previewRows[0] || {});
    },

    buildRowObjects(dataRows, cols) {
      const out = [];
      for (const r of dataRows) {
        if (!Array.isArray(r)) continue;
        const obj = {};
        for (const c of cols) {
          obj[c.label] = r[c.idx] ?? null;
        }
        // skip completely empty rows
        const hasAny = Object.values(obj).some(v => v != null && String(v).trim() !== "");
        if (hasAny) out.push(obj);
      }
      return out;
    },

    suggestMapping() {
      const H = this.headers;
      const findCol = (reList) => {
        const rx = new RegExp(reList.join("|"), "i");
        return H.find(h => rx.test(h)) || "";
      };
      this.mapping.subjectCol = findCol(["^subject$", "subject.?id", "^rid$", "^ptid$", "^participant", "^id$"]);
      this.mapping.visitCol   = findCol(["^visit", "time.?point", "session", "wave", "phase", "viscode"]);
      this.mapping.groupCol   = findCol(["^group", "arm", "cohort", "treatment", "^site$", "center"]);
      this.mapping.dateCol    = findCol(["date", "exam.?date", "visit.?date", "acq.?date"]);
      this.mapping.otherCols  = [];
      this.otherAllSelected = false;

      console.log("[Import] Mapping suggestion:", this.mapping);
    },

    toggleSelectAllOther() {
      if (this.otherAllSelected) {
        const exclude = new Set(
          [this.mapping.subjectCol, this.mapping.visitCol, this.mapping.groupCol, this.mapping.dateCol].filter(Boolean)
        );
        this.mapping.otherCols = this.headers.filter(h => !exclude.has(h));
      } else {
        this.mapping.otherCols = [];
      }
    },

    // ---------- Structure inference ----------
    inferStructure() {
      if (!this.mapping.subjectCol) {
        alert("Please map Subject ID column.");
        return;
      }

      const DEFAULT_VISIT = "Baseline";
      const DEFAULT_GROUP = "Group A";

      const subjSet = new Map();  // id -> index
      const visitSet = new Map(); // name -> index
      const groupSet = new Map(); // name -> index

      const normalized = [];

      for (let i = 0; i < this.rows.length; i++) {
        const r = this.rows[i];

        const subjRaw = this.safeStr(r[this.mapping.subjectCol]);
        if (!subjRaw) continue;

        const visit = this.mapping.visitCol ? (this.safeStr(r[this.mapping.visitCol]) || DEFAULT_VISIT) : DEFAULT_VISIT;
        const group = this.mapping.groupCol ? (this.safeStr(r[this.mapping.groupCol]) || DEFAULT_GROUP) : DEFAULT_GROUP;

        const extra = {};
        for (const k of this.mapping.otherCols) extra[k] = r[k] ?? null;
        if (this.mapping.dateCol) extra.__date__ = r[this.mapping.dateCol] ?? null;

        normalized.push({ _ix: i, subject: subjRaw, visit, group, data: extra });

        if (!subjSet.has(subjRaw)) subjSet.set(subjRaw, subjSet.size);
        if (!visitSet.has(visit))  visitSet.set(visit, visitSet.size);
        if (!groupSet.has(group))  groupSet.set(group, groupSet.size);
      }

      // Build UI-compatible arrays
      const groupNames = Array.from(groupSet.keys());
      this.groups = groupNames.map(name => ({ name }));

      const visitNames = Array.from(visitSet.keys());
      this.visits = visitNames.map(name => ({ name }));

      // Subject objects: { id, group } ; keep first-seen group
      const subjFirstGroup = {};
      for (const row of normalized) if (!(row.subject in subjFirstGroup)) subjFirstGroup[row.subject] = row.group;
      this.subjects = Array.from(subjSet.keys()).map(id => ({ id, group: subjFirstGroup[id] || groupNames[0] || DEFAULT_GROUP }));

      this.normalizedRows = normalized;
      this.structureReady = true;

      console.log("[Import] Inferred subjects:", this.subjects.length);
      console.log("[Import] Inferred visits:", this.visits.map(v => v.name));
      console.log("[Import] Inferred groups:", this.groups.map(g => g.name));
    },

    safeStr(v) { return v == null ? "" : String(v).trim(); },
    toName(s) {
      return String(s || "")
        .normalize("NFKD")
        .replace(/[^\w\s-]/g, "")
        .trim()
        .replace(/\s+/g, "_")
        .toLowerCase();
    },

    // ---------- Field/type helpers ----------
    inferFieldType(samples) {
      let nums=0, dates=0, bools=0, total=0;
      for (const v of samples) {
        if (v == null || v === "") continue;
        total++;
        if (!isNaN(Number(v))) { nums++; continue; }
        const d = new Date(v); if (!isNaN(d.getTime())) { dates++; continue; }
        if (["true","false","yes","no","y","n","0","1"].includes(String(v).toLowerCase())) { bools++; continue; }
      }
      if (total && nums===total) return "number";
      if (total && dates===total) return "date";
      if (total && bools===total) return "boolean";
      return "text";
    },

    // Build selectedModels from mapping.otherCols, grouped by section
    buildSelectedModels() {
      // sample values by header label
      const samplesByLabel = {};
      for (const k of this.mapping.otherCols) samplesByLabel[k] = [];
      for (const r of this.normalizedRows.slice(0, 200)) {
        for (const k of this.mapping.otherCols) samplesByLabel[k].push(r.data[k]);
      }

      // Group fields by section using columnMeta
      const bySection = new Map(); // section -> [{name,label}]
      for (const label of this.mapping.otherCols) {
        const meta = this.columnMeta.get(label);
        if (!meta) continue;
        const type = this.inferFieldType(samplesByLabel[label] || []);
        const arr = bySection.get(meta.section) || [];
        arr.push({
          name: meta.name,             // machine key (must match what we save in nested dict)
          label: meta.field,           // human label
          description: "",
          type, options: [],
          constraints: { required: false },
          placeholder: ""
        });
        bySection.set(meta.section, arr);
      }

      // Create one model per section (title = section)
      const models = [];
      for (const [section, fields] of bySection.entries()) {
        models.push({ title: section, fields, source: "import" });
      }
      // If nothing selected (edge), put an empty Imported Fields section
      if (!models.length) {
        models.push({ title: "Imported Fields", fields: [], source: "import" });
      }
      return models;
    },

    // assignments: [model][visit][group] -> set all true so sections are assigned everywhere
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
        subject_label_map: Object.fromEntries(this.subjects.map((s, i) => [s.id, pad(i+1, 3)])),
        session_label_map: Object.fromEntries(this.visits.map((v, i) => [v.name, pad(i+1, 2)])),
        column_catalog: catalog
      };
    },

    // Turn a flat { headerLabel: value } map into nested { Section: { field_name: value } }
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

    // ---------- Save sequence ----------
    async performSave() {
      this.saveError = "";
      this.failures = [];
      this.successStudyId = null;

      if (!this.structureReady) { this.saveError = "Please infer structure first."; return; }
      if (!this.studyMeta.name.trim()) { this.saveError = "Please enter a study title."; return; }
      if (!this.currentUserId) {
        alert("Please log in again.");
        this.$router.push("/login");
        return;
      }

      try {
        this.saving = true;

        // 1) Build study_data to match UI expectations
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
          subjects: this.subjects,               // [{ id, group }]
          subjectCount: this.subjects.length,
          assignmentMethod: "import",
          assignments,
          selectedModels,
          bids: this.buildBidsBlock(selectedModels)
        };

        // 2) Create study (TEMPLATE FIRST)
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

        console.log("[Import] Creating study with payload:", createPayload);

        const { data: created } = await axios.post(
          "/forms/studies/",
          createPayload,
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const studyId = created?.metadata?.id || created?.study_metadata?.id;
        if (!studyId) throw new Error("Failed to create study (no id returned).");

        console.log("[Import] Study created. ID =", studyId);

        // 3) Post entries (DATA SECOND) — bulk with fallback
        this.progress.total = this.normalizedRows.length;
        this.progress.done = 0;

        const vMap = new Map(this.visits.map((v, i) => [v.name, i]));
        const gMap = new Map(this.groups.map((g, i) => [g.name, i]));
        const sMap = new Map(this.subjects.map((s, i) => [s.id, i]));

        // Build all entries for bulk: convert flat extra -> nested dict now
        const entries = this.normalizedRows.map((row) => {
          const nested = this.packRowDataToDict(row.data);
          return {
            subject_index: sMap.get(row.subject),
            visit_index: vMap.get(row.visit),
            group_index: gMap.get(row.group),
            data: nested,
            skipped_required_flags: [], // IMPORTANT: array (never {})
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

        const CHUNK_SIZE = 1000; // tune 500–2000
        let usedBulk = true;

        console.log(`[Import] Posting ${entries.length} entries…`);

        for (let i = 0; i < entries.length; i += CHUNK_SIZE) {
          const chunk = entries.slice(i, i + CHUNK_SIZE);
          try {
            await postBulk(chunk);
            this.progress.done += chunk.length;
            console.log(`[Import] Bulk posted ${this.progress.done}/${this.progress.total}`);
          } catch (err) {
            if (err?.response?.status === 404 || err?.response?.status === 405) {
              usedBulk = false;
              console.warn("[Import] Bulk endpoint not available. Falling back to per-row…");
              // per-row fallback with modest concurrency
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
              console.log(`[Import] Per-row posted ${this.progress.done}/${this.progress.total}`);
            } else {
              const reason = err?.response?.data?.detail || err?.message || "Bulk insert failed";
              console.error("[Import] Bulk chunk failed:", reason);
              // mark attempted; record one failure summary
              this.failures.push({ _ix: i, subject: "—", visit: "—", group: "—", reason });
              this.progress.done += chunk.length;
            }
          }
        }

        this.successStudyId = studyId;
        console.log("[Import] Finished. Used bulk:", usedBulk, "Failures:", this.failures.length);
      } catch (e) {
        console.error("[Import] Import failed:", e);
        this.saveError = e?.message || "Import failed.";
      } finally {
        this.saving = false;
      }
    },

    // ---------- Reset ----------
    resetAll() {
      this.headers = [];
      this.rows = [];
      this.previewRows = [];
      this.rowCount = 0;
      this.columns = [];
      this.columnMeta = new Map();
      this.mapping = { subjectCol: "", visitCol: "", groupCol: "", dateCol: "", otherCols: [] };
      this.otherAllSelected = false;
      this.studyMeta = { name: "", description: "" };
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
.pillbox { display:flex; flex-wrap:wrap; gap:8px; }
.pill { border:1px solid #ddd; padding:6px 8px; border-radius:999px; background:#fff; font-size:12px; }
.select-all { display:flex; gap:8px; align-items:center; margin-top:8px; }
.muted { color:#777; font-size: 12px; }
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
</style>
