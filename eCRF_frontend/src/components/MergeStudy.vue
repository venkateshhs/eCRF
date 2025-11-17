<template>
  <div class="merge-page">
    <!-- Header -->
    <div class="back-header-row">
      <div class="back-button-container">
        <button class="btn-minimal" @click="goBack">
          <i :class="icons.back" aria-hidden="true"></i>
          <span>Back</span>
        </button>
      </div>
      <h2 class="existing-studies-title">Merge Study Bundle</h2>
    </div>

    <!-- Study meta -->
    <div class="top-bar card-surface">
      <div class="meta">
        <div class="meta-title">
          Study: <strong>{{ meta.study_name || '—' }}</strong>
        </div>
        <div class="meta-sub" v-if="meta.study_description">
          {{ meta.study_description }}
        </div>
        <div class="meta-stats">
          Subjects: {{ subjects.length }} · Visits: {{ visits.length }} · Groups: {{ groups.length }}
        </div>
      </div>

      <div class="actions">
        <input
          ref="fileInput"
          type="file"
          accept=".zip"
          class="file-hidden"
          @change="onBundleFile"
        />
        <button class="btn-primary" @click="triggerFile">
          Choose bundle (.zip)
        </button>
        <button
          class="btn-option"
          :disabled="!hasBundle"
          @click="clearBundle"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- Parsing / validation banner -->
    <div
      v-if="parseInfo.message"
      class="parse-banner"
      :class="parseInfo.ok ? 'ok' : 'warn'"
    >
      {{ parseInfo.message }}
    </div>

    <!-- Nothing loaded yet -->
    <div v-if="!hasBundle" class="empty-state card-surface">
      <p class="empty-title">Import a study bundle</p>
      <p class="empty-text">
        Select the ZIP file created by <code>downloadStudyBundle</code>. It
        should contain <code>template_vX.json</code> and
        <code>data_vX.csv</code>.
      </p>
      <ul class="empty-list">
        <li>Default: merge data for all subjects.</li>
        <li>Advanced: restrict import to specific subjects.</li>
        <li>If there are conflicts, you’ll get a simple left/right resolution UI.</li>
      </ul>
    </div>

    <!-- Main layout once bundle is parsed -->
    <div v-else class="main-layout">
      <!-- Left column: bundle + template info -->
      <section class="card-surface left-column">
        <!-- Bundle summary -->
        <div class="section-header">
          <h3>Bundle summary</h3>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="label">Bundle file</div>
            <div class="value">{{ bundleFileName }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Imported version</div>
            <div class="value">
              v{{ bundleVersion || '—' }}
            </div>
          </div>
          <div class="summary-item">
            <div class="label">Rows in CSV</div>
            <div class="value">
              {{ bundleRowCount }}
            </div>
          </div>
          <div class="summary-item">
            <div class="label">Subjects in bundle</div>
            <div class="value">
              {{ bundleSubjectIds.length }}
            </div>
          </div>
          <div class="summary-item">
            <div class="label">Visits in bundle</div>
            <div class="value">
              {{ bundleVisitNames.length }}
            </div>
          </div>
        </div>

        <!-- Template comparison -->
        <div class="section-header mt">
          <h3>Template comparison</h3>
        </div>
        <div class="template-compare">
          <div class="compare-row">
            <div class="label">Current template sections</div>
            <div class="value">{{ currentTemplateSummary.sections }}</div>
          </div>
          <div class="compare-row">
            <div class="label">Imported template sections</div>
            <div class="value">{{ importedTemplateSummary.sections }}</div>
          </div>
          <div class="compare-row">
            <div class="label">Current template fields</div>
            <div class="value">{{ currentTemplateSummary.fields }}</div>
          </div>
          <div class="compare-row">
            <div class="label">Imported template fields</div>
            <div class="value">{{ importedTemplateSummary.fields }}</div>
          </div>
          <div
            v-if="templateMismatch"
            class="template-warning"
          >
            Template structure does not match. Merge is disabled to avoid data
            loss. Please align template versions before importing this bundle.
          </div>
        </div>

        <!-- Scope selection (whole study vs per subject) -->
        <div class="section-header mt">
          <h3>Scope</h3>
        </div>
        <div class="scope-card">
          <label class="radio-row">
            <input
              type="radio"
              value="all"
              v-model="scopeMode"
            />
            <span>Merge whole study (all subjects in bundle)</span>
          </label>
          <label class="radio-row">
            <input
              type="radio"
              value="subset"
              v-model="scopeMode"
            />
            <span>Merge specific subjects</span>
          </label>

          <div
            v-if="scopeMode === 'subset'"
            class="subject-select"
          >
            <p class="helper">
              Select subjects from the bundle to include in this merge.
            </p>
            <div class="subject-list">
              <label
                v-for="sid in bundleSubjectIds"
                :key="sid"
                class="subject-pill"
              >
                <input
                  type="checkbox"
                  :value="sid"
                  v-model="selectedSubjectIds"
                />
                <span>{{ sid }}</span>
              </label>
            </div>
            <button
              class="btn-minimal sm"
              @click="selectAllSubjects"
            >
              Select all
            </button>
            <button
              class="btn-minimal sm"
              @click="clearSelectedSubjects"
            >
              Clear
            </button>
          </div>
        </div>

        <!-- Merge summary -->
        <div class="section-header mt">
          <h3>Merge summary</h3>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="label">Entries to import</div>
            <div class="value">{{ importEntryCount }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Conflicting fields</div>
            <div class="value">
              <span
                :class="{
                  'badge-pill': true,
                  conflict: conflicts.length > 0,
                  ok: conflicts.length === 0
                }"
              >
                {{ conflicts.length }}
              </span>
            </div>
          </div>
          <div class="summary-item">
            <div class="label">Auto-merge possible</div>
            <div class="value">
              {{ autoMergePossible ? 'Yes (no conflicts)' : 'No (review needed)' }}
            </div>
          </div>
        </div>
      </section>

      <!-- Right column: conflicts table (only if conflicts) -->
      <section class="card-surface right-column" v-if="conflicts.length">
        <div class="section-header">
          <h3>Resolve conflicts</h3>
          <div class="section-actions">
            <!-- NEW: Subject filter dropdown -->
            <div class="subject-filter">
              <label for="conflict-subject-filter">Subject:</label>
              <select
                id="conflict-subject-filter"
                v-model="selectedConflictSubject"
              >
                <option value="ALL">All</option>
                <option
                  v-for="sid in conflictSubjectOptions"
                  :key="sid"
                  :value="sid"
                >
                  {{ sid }}
                </option>
              </select>
            </div>

            <button
              class="btn-option sm"
              @click="applyDecisionToAll('incoming')"
            >
              Use incoming (right) for all
            </button>
            <button
              class="btn-option sm"
              @click="applyDecisionToAll('existing')"
            >
              Keep existing (left) for all
            </button>
          </div>
        </div>

        <p class="helper">
          These fields have different values in the current study and in the imported
          bundle. Choose whether to keep the existing value (left) or use the incoming
          value (right). Default decisions are based on the higher
          <code>form_version</code>.
        </p>

        <div class="conflict-table-wrapper">
          <table class="conflict-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Visit</th>
                <th>Section</th>
                <th>Field</th>
                <th>Existing (left)</th>
                <th>Incoming (right)</th>
                <th>Choice</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in visibleConflicts"
                :key="c.key"
              >
                <td>{{ c.subjectId }}</td>
                <td>{{ c.visitName }}</td>
                <td>{{ c.sectionTitle }}</td>
                <td>{{ c.fieldLabel }}</td>
                <td>
                  <div class="val-cell">
                    <div class="val-main">
                      {{ displayVal(c.existingValue) }}
                    </div>
                    <div class="val-meta">
                      v{{ c.existingVersion || '—' }}
                    </div>
                  </div>
                </td>
                <td>
                  <div class="val-cell">
                    <div class="val-main">
                      {{ displayVal(c.incomingValue) }}
                    </div>
                    <div class="val-meta">
                      v{{ c.incomingVersion || '—' }}
                    </div>
                  </div>
                </td>
                <td>
                  <div class="choice-row">
                    <label class="radio-inline">
                      <input
                        type="radio"
                        :name="c.key"
                        value="existing"
                        :checked="decisions[c.key] === 'existing'"
                        @change="setDecision(c.key, 'existing')"
                      />
                      Left
                    </label>
                    <label class="radio-inline">
                      <input
                        type="radio"
                        :name="c.key"
                        value="incoming"
                        :checked="decisions[c.key] === 'incoming'"
                        @change="setDecision(c.key, 'incoming')"
                      />
                      Right
                    </label>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- No conflicts: small notice on right -->
      <section
        v-else
        class="card-surface right-column"
      >
        <div class="section-header">
          <h3>No conflicts</h3>
        </div>
        <p class="helper">
          All incoming values are either identical to existing data or filling empty
          fields. Clicking <strong>Merge</strong> will safely update or create
          entries without overwriting conflicting data.
        </p>
      </section>
    </div>

    <!-- Sticky footer -->
    <div class="global-commit" v-if="hasBundle">
      <div class="gc-left">
        <div class="sel-summary">
          <span>Subjects in scope:</span>
          <strong>
            {{
              scopeMode === 'all'
                ? bundleSubjectIds.length
                : selectedSubjectIds.length
            }}
          </strong>
          <span class="dot">·</span>
          <span>Conflicts:</span>
          <strong>{{ conflicts.length }}</strong>
        </div>
        <div class="sel-sub" v-if="!autoMergePossible">
          Decisions made:
          <strong>{{ decidedConflictCount }}</strong> /
          <strong>{{ conflicts.length }}</strong>
        </div>
      </div>
      <div class="gc-right">
        <button
          class="btn-primary"
          :disabled="!canMerge"
          @click="performMerge"
        >
          {{ isMerging ? 'Merging…' : (autoMergePossible ? 'Merge' : 'Merge with decisions') }}
        </button>
      </div>
    </div>

    <CustomDialog
      :message="dialogMessage"
      :isVisible="showDialog"
      @close="closeDialog"
    />
  </div>
</template>

<script>
/* eslint-disable */
import axios from "axios";
import JSZip from "jszip";
import * as Papa from "papaparse";
import CustomDialog from "@/components/CustomDialog.vue";
import icons from "@/assets/styles/icons";

export default {
  name: "MergeStudyBundle",
  components: { CustomDialog },
  data() {
    return {
      icons,
      studyId: null,
      study: null,
      meta: {},
      subjects: [],
      visits: [],
      groups: [],
      subjectToGroupIdx: [],

      // template index (from current study)
      sectionIndex: new Map(),       // title -> { displayByCanon, fieldNameByCanon, fieldTypeByCanon }
      sectionTitleByCanon: new Map(),// canon(sectionTitle) -> sectionTitle

      // existing entries (server)
      entries: [],
      entriesIndex: new Map(),       // svgKey -> latest entry

      // imported bundle
      hasBundle: false,
      bundleFileName: "",
      bundleVersion: null,
      bundleRowCount: 0,
      bundleSubjectIds: [],
      bundleVisitNames: [],
      importedSchema: null,          // schema from template_vX.json
      incomingEntries: {},           // svgKey -> { subject_index, visit_index, group_index, data, form_version }

      // scope
      scopeMode: "all",              // 'all' | 'subset'
      selectedSubjectIds: [],

      // conflicts
      conflicts: [],                 // [{ key, svgKey, subjectId, visitName, sectionTitle, fieldCanon, fieldLabel, existingValue, incomingValue, existingVersion, incomingVersion }]
      decisions: {},                 // conflictKey -> 'existing' | 'incoming'

      // NEW: subject filter for conflicts table
      selectedConflictSubject: "ALL",

      parseInfo: { ok: false, message: "" },
      isMerging: false,

      showDialog: false,
      dialogMessage: "",
    };
  },
  computed: {
    importEntryCount() {
      return Object.keys(this.incomingEntries || {}).length;
    },
    autoMergePossible() {
      return this.conflicts.length === 0;
    },
    decidedConflictCount() {
      return this.conflicts.filter((c) => !!this.decisions[c.key]).length;
    },
    canMerge() {
      if (!this.hasBundle) return false;
      if (this.templateMismatch) return false;
      if (this.scopeMode === "subset" && this.selectedSubjectIds.length === 0) return false;
      if (!this.autoMergePossible && this.decidedConflictCount < this.conflicts.length) {
        return false;
      }
      return !this.isMerging;
    },
    // simple summaries for template comparison
    currentTemplateSummary() {
      const sd = this.study?.content?.study_data || {};
      const sections = sd.selectedModels || [];
      let fieldCount = 0;
      sections.forEach((sec) => {
        fieldCount += (sec.fields || []).length;
      });
      return {
        sections: sections.length,
        fields: fieldCount,
      };
    },
    importedTemplateSummary() {
      const schema = this.importedSchema || {};
      const sections = Array.isArray(schema.selectedModels) ? schema.selectedModels : [];
      let fieldCount = 0;
      sections.forEach((sec) => {
        fieldCount += (sec.fields || []).length;
      });
      return {
        sections: sections.length,
        fields: fieldCount,
      };
    },
    templateMismatch() {
      // very conservative: require same number of sections and fields
      return (
        this.currentTemplateSummary.sections !== this.importedTemplateSummary.sections ||
        this.currentTemplateSummary.fields !== this.importedTemplateSummary.fields
      );
    },
    // NEW: distinct subject IDs present in conflicts
    conflictSubjectOptions() {
      const set = new Set(this.conflicts.map((c) => String(c.subjectId)));
      return Array.from(set).sort();
    },
    // NEW: conflicts filtered by selected subject for the table only
    visibleConflicts() {
      if (!this.selectedConflictSubject || this.selectedConflictSubject === "ALL") {
        return this.conflicts;
      }
      return this.conflicts.filter(
        (c) => String(c.subjectId) === String(this.selectedConflictSubject)
      );
    },
  },
  async created() {
    this.studyId = this.$route.params.id;
    await this.loadStudy();
    await this.loadEntries();
    this.indexEntries();
    this.buildSectionIndex();
  },
  methods: {
    // ---------- Navigation & dialog ----------
    goBack() {
      this.$router.push({ name: "Dashboard", query: { openStudies: "true" } });
    },
    showDialogMessage(msg) {
      this.dialogMessage = msg;
      this.showDialog = true;
    },
    closeDialog() {
      this.showDialog = false;
      this.dialogMessage = "";
    },

    // ---------- Load existing study ----------
    async loadStudy() {
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}`, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        });
        this.study = data;
        this.meta = data?.metadata || {};
        const sd = data?.content?.study_data || {};
        this.subjects = sd.subjects || [];
        this.visits = sd.visits || [];
        this.groups = sd.groups || [];
        this.subjectToGroupIdx = (this.subjects || []).map((s) => {
          const gn = (s.group || "").toLowerCase().trim();
          const gi = (this.groups || []).findIndex(
            (g) => (g.name || "").toLowerCase().trim() === gn
          );
          return gi >= 0 ? gi : 0;
        });
      } catch (e) {
        console.error("[Merge] Failed to load study:", e);
        this.showDialogMessage("Failed to load study.");
      }
    },
    async loadEntries() {
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}/data_entries`, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        });
        this.entries = Array.isArray(data) ? data : data?.entries || [];
      } catch (e) {
        console.error("[Merge] Failed to load entries:", e);
        this.entries = [];
      }
    },
    indexEntries() {
      const m = new Map();
      for (const e of this.entries) {
        const key = `${e.subject_index}|${e.visit_index}|${e.group_index}`;
        const cur = m.get(key);
        if (!cur || Number(e.form_version) >= Number(cur?.form_version || 0)) {
          m.set(key, e);
        }
      }
      this.entriesIndex = m;
    },

    // ---------- Template index & helpers ----------
    buildSectionIndex() {
      this.sectionIndex = new Map();
      this.sectionTitleByCanon = new Map();

      const models = this.study?.content?.study_data?.selectedModels || [];
      models.forEach((sec) => {
        const title = sec?.title || "";
        if (!title) return;

        const displayByCanon = {};
        const fieldNameByCanon = {};
        const fieldTypeByCanon = {};

        this.sectionTitleByCanon.set(this.canonKey(title), title);

        (sec.fields || []).forEach((f, idx) => {
          const label = f?.label || f?.title || f?.name || `Field ${idx + 1}`;
          const name = f?.name || label;
          const type = (f?.type || "").toLowerCase();

          const candidates = new Set(
            [
              name,
              label,
              f?.title || "",
              this.humanizeCamel(name),
              this.humanizeCamel(label),
            ].filter(Boolean)
          );

          for (const c of candidates) {
            const canon = this.canonKey(c);
            fieldNameByCanon[canon] = name;
            fieldTypeByCanon[this.canonKey(name)] = type;
          }

          displayByCanon[this.canonKey(name)] = label;
        });

        this.sectionIndex.set(title, { displayByCanon, fieldNameByCanon, fieldTypeByCanon });
      });
    },
    mapSectionTitle(raw) {
      const mapped = this.sectionTitleByCanon.get(this.canonKey(raw));
      return mapped || raw;
    },
    displayFor(sectionTitle, canon) {
      const m = this.sectionIndex.get(sectionTitle);
      return (m?.displayByCanon?.[canon]) || this.prettyFromCanon(canon);
    },

    canonKey(s) {
      return String(s ?? "")
        .toLowerCase()
        .replace(/[\W_]+/g, "");
    },
    humanizeCamel(s) {
      if (!s) return "";
      const w = String(s)
        .replace(/[_\-]+/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .toLowerCase();
      return w.replace(/\b\w/g, (c) => c.toUpperCase());
    },
    prettyFromCanon(canon) {
      return this.humanizeCamel(canon);
    },
    hasValue(v) {
      return v !== null && v !== undefined && String(v).trim() !== "";
    },
    displayVal(v) {
      return this.hasValue(v) ? String(v) : "";
    },

    normalizeCheckbox(val) {
      if (val === true) return true;
      if (val === false) return false;
      if (val == null || String(val).trim() === "") return "";
      const s = String(val).trim().toLowerCase();
      if (["true", "yes", "1", "y", "on", "checked"].includes(s)) return true;
      if (["false", "no", "0", "n", "off", "unchecked"].includes(s)) return false;
      return "";
    },

    normalizeSectionDict(sectionTitle, rawSectionDict) {
      const out = {};
      if (!rawSectionDict || typeof rawSectionDict !== "object") return out;
      const idx = this.sectionIndex.get(sectionTitle);
      if (!idx) return out;

      for (const rawKey of Object.keys(rawSectionDict)) {
        const cRaw = this.canonKey(rawKey);
        const fieldName = idx.fieldNameByCanon?.[cRaw];
        if (!fieldName) continue;
        const canonName = this.canonKey(fieldName);
        const val = rawSectionDict[rawKey];
        if (!(canonName in out) || this.hasValue(val)) out[canonName] = val;
      }
      return out;
    },

    entryToDictNormalized(entry) {
      const models = this.study?.content?.study_data?.selectedModels || [];
      const out = {};
      if (!entry) {
        for (const sec of models) out[sec.title] = {};
        return out;
      }

      if (entry.data && !Array.isArray(entry.data) && typeof entry.data === "object") {
        for (const sec of models) {
          const secTitle = sec.title;
          const secObj = entry.data?.[secTitle] || {};
          const byName = {};
          (sec.fields || []).forEach((f) => {
            const name = f?.name || "";
            const label = f?.label || f?.title || "";
            if (!name) return;
            let v = secObj[name];
            if (v === undefined) v = secObj[label];
            if (v !== undefined) byName[name] = v;
          });
          out[secTitle] = this.normalizeSectionDict(secTitle, byName);
        }
        return out;
      }

      // array-shape fallback
      const arr = Array.isArray(entry.data) ? entry.data : [];
      models.forEach((sec, sIdx) => {
        const secTitle = sec.title;
        const row = Array.isArray(arr[sIdx]) ? arr[sIdx] : [];
        const byName = {};
        (sec.fields || []).forEach((f, fIdx) => {
          const name = f?.name || f?.label || f?.title || `Field ${fIdx + 1}`;
          byName[name] = row[fIdx] != null ? row[fIdx] : "";
        });
        out[secTitle] = this.normalizeSectionDict(secTitle, byName);
      });
      return out;
    },

    makeSkipSkeleton() {
      const models = this.study?.content?.study_data?.selectedModels || [];
      return models.map((sec) => (sec.fields || []).map(() => false));
    },

    denormalizeForSave(normBySection) {
      const out = {};
      for (const rawSecName of Object.keys(normBySection || {})) {
        const secTitle = this.mapSectionTitle(rawSecName);
        const secDictCanon = normBySection[rawSecName] || {};
        const map = this.sectionIndex.get(secTitle);
        if (!map) continue;
        const row = {};
        for (const canon of Object.keys(secDictCanon)) {
          const fieldKey = map.fieldNameByCanon?.[canon];
          if (!fieldKey) continue;
          const fType = map.fieldTypeByCanon?.[canon];
          let val = secDictCanon[canon];
          if (fType === "checkbox") val = this.normalizeCheckbox(val);
          row[fieldKey] = val;
        }
        if (Object.keys(row).length > 0) {
          out[secTitle] = row;
        }
      }
      return out;
    },

    valuesEqual(a, b) {
      const hv = (v) => v !== null && v !== undefined && String(v).trim() !== "";
      if (!hv(a) && !hv(b)) return true;
      const aa = String(a ?? "").trim();
      const bb = String(b ?? "").trim();
      const na = Number(aa);
      const nb = Number(bb);
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na === nb;
      return aa === bb;
    },

    // ---------- Scope helpers ----------
    selectAllSubjects() {
      this.selectedSubjectIds = [...this.bundleSubjectIds];
      this.computeConflicts();
    },
    clearSelectedSubjects() {
      this.selectedSubjectIds = [];
      this.computeConflicts();
    },

    // ---------- File handling / parsing ----------
    triggerFile() {
      this.$refs.fileInput && this.$refs.fileInput.click();
    },
    clearBundle() {
      this.hasBundle = false;
      this.bundleFileName = "";
      this.bundleVersion = null;
      this.bundleRowCount = 0;
      this.bundleSubjectIds = [];
      this.bundleVisitNames = [];
      this.importedSchema = null;
      this.incomingEntries = {};
      this.conflicts = [];
      this.decisions = {};
      this.parseInfo = { ok: false, message: "" };
      this.scopeMode = "all";
      this.selectedSubjectIds = [];
      this.selectedConflictSubject = "ALL";
    },
    async onBundleFile(ev) {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      try {
        await this.parseBundle(f);
      } catch (e) {
        console.error("[Merge] Failed to parse bundle:", e);
        this.parseInfo = { ok: false, message: "Failed to read bundle. See console." };
        this.hasBundle = false;
      }
    },
    async parseBundle(file) {
      this.clearBundle();
      this.bundleFileName = file.name;

      const zip = await JSZip.loadAsync(file);
      let templateFile = null;
      let dataFile = null;

      zip.forEach((path, zf) => {
        if (zf.dir) return;
        const lower = path.toLowerCase();
        if (!templateFile && lower.includes("template_v") && lower.endsWith(".json")) {
          templateFile = zf;
        } else if (!dataFile && lower.includes("data_v") && lower.endsWith(".csv")) {
          dataFile = zf;
        }
      });

      if (!templateFile || !dataFile) {
        this.parseInfo = {
          ok: false,
          message: "Bundle must contain template_vX.json and data_vX.csv.",
        };
        return;
      }

      const templateText = await templateFile.async("string");
      const csvText = await dataFile.async("string");

      let schema = {};
      try {
        const parsed = JSON.parse(templateText);
        schema = parsed?.schema || parsed || {};
      } catch (e) {
        console.error("[Merge] Failed to parse template JSON:", e);
        this.parseInfo = { ok: false, message: "Failed to parse template JSON." };
        return;
      }

      const csvRes = Papa.parse(csvText, {
        skipEmptyLines: "greedy",
      });
      const rows = csvRes.data || [];
      if (rows.length < 3) {
        this.parseInfo = {
          ok: false,
          message: "CSV in bundle must have 2 header rows + data.",
        };
        return;
      }

      // Version from filename or schema
      const tmplMatch = templateFile.name.match(/template_v(\d+)/i);
      const dataMatch = dataFile.name.match(/data_v(\d+)/i);
      const versionFromName =
        (tmplMatch && Number(tmplMatch[1])) ||
        (dataMatch && Number(dataMatch[1])) ||
        Number(schema.version || 1);

      this.bundleVersion = versionFromName || 1;
      this.bundleRowCount = rows.length - 2;
      this.importedSchema = schema;

      // Build incoming entries from rows
      const { incomingEntries, subjectIds, visitNames, warnings } =
        this.buildIncomingEntriesFromRows(rows, schema, this.bundleVersion);

      if (warnings.length) {
        this.parseInfo = {
          ok: false,
          message: `Bundle contains unknown subjects/visits: ${warnings.join(
            "; "
          )}. Merge is disabled to avoid data loss.`,
        };
        return;
      }

      this.incomingEntries = incomingEntries;
      this.bundleSubjectIds = subjectIds;
      this.bundleVisitNames = visitNames;
      this.selectedSubjectIds = [...subjectIds];

      this.hasBundle = true;
      this.parseInfo = {
        ok: true,
        message: `Bundle parsed. Rows: ${this.bundleRowCount}. Subjects: ${subjectIds.length}. Visits: ${visitNames.length}.`,
      };

      // Recompute conflicts based on full scope
      this.computeConflicts();
    },

    buildIncomingEntriesFromRows(rows, schema, bundleVersion) {
      const studyData = this.study?.content?.study_data || {};
      const sections = Array.isArray(schema.selectedModels) ? schema.selectedModels : [];
      const incomingEntries = {};
      const subjectIdsSet = new Set();
      const visitNamesSet = new Set();
      const warnings = [];

      // maps for current study
      const subjMap = {};
      this.subjects.forEach((s, idx) => {
        subjMap[String(s.id)] = idx;
      });
      const visitMap = {};
      this.visits.forEach((v, idx) => {
        visitMap[String(v.name).trim().toLowerCase()] = idx;
      });

      for (let r = 2; r < rows.length; r++) {
        const row = rows[r] || [];
        const subjectId = String(row[0] || "").trim();
        const visitName = String(row[1] || "").trim();
        if (!subjectId || !visitName) continue;

        subjectIdsSet.add(subjectId);
        visitNamesSet.add(visitName);

        const sIdx = subjMap[subjectId];
        const vIdx = visitMap[visitName.trim().toLowerCase()];

        if (sIdx == null || sIdx < 0) {
          if (!warnings.includes("unknown subject(s)")) warnings.push("unknown subject(s)");
          continue;
        }
        if (vIdx == null || vIdx < 0) {
          if (!warnings.includes("unknown visit(s)")) warnings.push("unknown visit(s)");
          continue;
        }

        const groupIdx = this.resolveGroup(studyData, sIdx);

        const key = `${sIdx}|${vIdx}|${groupIdx}`;
        if (!incomingEntries[key]) {
          incomingEntries[key] = {
            study_id: this.studyId,
            subject_index: sIdx,
            visit_index: vIdx,
            group_index: groupIdx,
            form_version: bundleVersion,
            data: {},
          };
        }
        const entry = incomingEntries[key];

        let col = 2;
        sections.forEach((section, sIndex) => {
          const secTitle = section.title || section.name || `Section ${sIndex + 1}`;
          const fields = section.fields || [];
          if (!entry.data[secTitle]) entry.data[secTitle] = {};
          fields.forEach((field, fIdx) => {
            const val = row[col++] ?? "";
            const name =
              field.name ||
              field.key ||
              field.id ||
              field.label ||
              field.title ||
              `f${fIdx}`;
            const trimmed = String(val).trim();
            if (trimmed !== "") {
              entry.data[secTitle][name] = trimmed;
            }
          });
        });
      }

      return {
        incomingEntries,
        subjectIds: Array.from(subjectIdsSet),
        visitNames: Array.from(visitNamesSet),
        warnings,
      };
    },

    resolveGroup(studyData, subjIdx) {
      const subjects = studyData.subjects || [];
      const groups = studyData.groups || [];
      const subjGroup = (subjects[subjIdx]?.group || "").trim().toLowerCase();
      const idx = groups.findIndex(
        (g) => (g.name || "").trim().toLowerCase() === subjGroup
      );
      return idx >= 0 ? idx : 0;
    },

    // ---------- Conflict detection ----------
    computeConflicts() {
      const conflicts = [];
      const scopeAll = this.scopeMode === "all";
      const scopeSet = new Set(this.selectedSubjectIds || []);
      const conflictSeen = new Set();

      for (const svgKey of Object.keys(this.incomingEntries || {})) {
        const incoming = this.incomingEntries[svgKey];
        const sIdx = incoming.subject_index;
        const vIdx = incoming.visit_index;
        const gIdx = incoming.group_index;

        const subject = this.subjects[sIdx];
        const visit = this.visits[vIdx];
        const subjectId = subject?.id;
        const visitName = visit?.name;

        if (!subjectId || !visitName) continue;
        if (!scopeAll && !scopeSet.has(String(subjectId))) continue;

        const existing = this.entriesIndex.get(svgKey);
        if (!existing) continue; // new entry, no conflicts

        const exDict = this.entryToDictNormalized(existing);
        const inDict = this.entryToDictNormalized(incoming);

        const allSections = new Set([
          ...Object.keys(exDict || {}),
          ...Object.keys(inDict || {}),
        ]);

        for (const secTitle of allSections) {
          const exSec = exDict[secTitle] || {};
          const inSec = inDict[secTitle] || {};
          const canons = new Set([
            ...Object.keys(exSec),
            ...Object.keys(inSec),
          ]);

          for (const canon of canons) {
            const exVal = exSec[canon];
            const inVal = inSec[canon];
            if (!this.hasValue(exVal) && !this.hasValue(inVal)) continue;

            if (
              this.hasValue(exVal) &&
              this.hasValue(inVal) &&
              !this.valuesEqual(exVal, inVal)
            ) {
              const key = `${svgKey}|${secTitle}|${canon}`;
              if (conflictSeen.has(key)) continue;
              conflictSeen.add(key);

              conflicts.push({
                key,
                svgKey,
                subjectId,
                visitName,
                sectionTitle: secTitle,
                fieldCanon: canon,
                fieldLabel: this.displayFor(secTitle, canon),
                existingValue: exVal,
                incomingValue: inVal,
                existingVersion: existing.form_version,
                incomingVersion: incoming.form_version,
              });
            }
          }
        }
      }

      this.conflicts = conflicts;
      this.decisions = {};
      this.selectedConflictSubject = "ALL";
      // Auto decisions based on version (higher version wins by default)
      for (const c of conflicts) {
        const eV = Number(c.existingVersion || 0);
        const iV = Number(c.incomingVersion || 0);
        this.decisions[c.key] = iV >= eV ? "incoming" : "existing";
      }
    },

    setDecision(key, choice) {
      this.decisions = { ...this.decisions, [key]: choice };
    },
    applyDecisionToAll(choice) {
      const next = { ...this.decisions };
      this.conflicts.forEach((c) => {
        next[c.key] = choice;
      });
      this.decisions = next;
    },

    // ---------- Merge ----------
    async performMerge() {
      if (!this.canMerge) return;

      const scopeAll = this.scopeMode === "all";
      const scopeSet = new Set(this.selectedSubjectIds || []);
      const conflictKeySet = new Set(this.conflicts.map((c) => c.key));

      this.isMerging = true;
      try {
        const headers = {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        };

        for (const svgKey of Object.keys(this.incomingEntries || {})) {
          const incoming = this.incomingEntries[svgKey];
          const sIdx = incoming.subject_index;
          const vIdx = incoming.visit_index;
          const gIdx = incoming.group_index;

          const subject = this.subjects[sIdx];
          const subjectId = subject?.id;
          if (!subjectId) continue;
          if (!scopeAll && !scopeSet.has(String(subjectId))) continue;

          const existing = this.entriesIndex.get(svgKey) || null;
          const baseDict = this.entryToDictNormalized(existing);
          const inDict = this.entryToDictNormalized(incoming);

          const allSections = new Set([
            ...Object.keys(baseDict || {}),
            ...Object.keys(inDict || {}),
          ]);

          for (const secTitle of allSections) {
            if (!baseDict[secTitle]) baseDict[secTitle] = {};
            const exSec = baseDict[secTitle];
            const inSec = inDict[secTitle] || {};
            const canons = new Set([
              ...Object.keys(exSec),
              ...Object.keys(inSec),
            ]);

            for (const canon of canons) {
              const exVal = exSec[canon];
              const inVal = inSec[canon];
              const hasEx = this.hasValue(exVal);
              const hasIn = this.hasValue(inVal);
              const cKey = `${svgKey}|${secTitle}|${canon}`;

              if (
                hasEx &&
                hasIn &&
                !this.valuesEqual(exVal, inVal) &&
                conflictKeySet.has(cKey)
              ) {
                const choice = this.decisions[cKey] || "existing";
                if (choice === "incoming") {
                  exSec[canon] = inVal;
                } else {
                  exSec[canon] = hasEx ? exVal : inVal;
                }
              } else {
                // Non-conflict: never drop non-empty data
                if (hasIn && !hasEx) exSec[canon] = inVal;
                else if (!hasIn && hasEx) exSec[canon] = exVal;
                else if (hasIn && hasEx) exSec[canon] = inVal; // equal or compatible
                else exSec[canon] = "";
              }
            }
          }

          const payload = {
            study_id: this.studyId,
            subject_index: sIdx,
            visit_index: vIdx,
            group_index: gIdx,
            data: this.denormalizeForSave(baseDict),
            skipped_required_flags: this.makeSkipSkeleton(),
          };

          if (existing?.id) {
            await axios.put(
              `/forms/studies/${this.studyId}/data_entries/${existing.id}`,
              payload,
              headers
            );
          } else {
            await axios.post(
              `/forms/studies/${this.studyId}/data`,
              payload,
              headers
            );
          }
        }

        // reload entries and indexes
        await this.loadEntries();
        this.indexEntries();
        this.showDialogMessage("Merge completed successfully.");
      } catch (e) {
        console.error("[Merge] Merge failed:", e?.response?.data || e);
        this.showDialogMessage("Merge failed. See console for details.");
      } finally {
        this.isMerging = false;
      }
    },
  },
};
</script>

<style scoped>
/* Shared surface + buttons */
.card-surface {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 25px rgba(16, 24, 40, 0.06);
}
.btn-primary {
  background: #2f6fed;
  border: 1px solid #245fe0;
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease, box-shadow 0.2s ease, transform 0.02s ease;
}
.btn-primary:hover {
  background: #285fce;
  box-shadow: 0 2px 10px rgba(47, 111, 237, 0.25);
}
.btn-option {
  background: #fff;
  border: 1px solid #e0e0e0;
  color: #111827;
  padding: 8px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
  font-size: 14px;
}
.btn-option:hover {
  background: #f8fafc;
}
.btn-option.sm {
  padding: 6px 10px;
  font-size: 13px;
}
.btn-minimal {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-minimal.sm {
  padding: 4px 8px;
  font-size: 12px;
}
.btn-minimal:hover {
  background: #e8e8e8;
  color: #000;
  border-color: #d6d6d6;
}
.file-hidden {
  display: none;
}

/* Page shell */
.merge-page {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 16px 72px;
}
.back-header-row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  margin-bottom: 12px;
}
.back-button-container {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
}
.existing-studies-title {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

/* Top bar */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.meta-title {
  font-size: 16px;
  color: #111827;
}
.meta-sub {
  color: #4b5563;
  margin-top: 4px;
}
.meta-stats {
  color: #6b7280;
  font-size: 13px;
  margin-top: 2px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.parse-banner {
  margin: 10px 0;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
}
.parse-banner.ok {
  background: #f0fdf4;
  color: #065f46;
  border: 1px solid #bbf7d0;
}
.parse-banner.warn {
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
}

/* Empty state */
.empty-state {
  margin-top: 16px;
  padding: 18px 20px;
}
.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: #111827;
}
.empty-text {
  margin-top: 6px;
  color: #4b5563;
}
.empty-list {
  margin-top: 10px;
  padding-left: 20px;
  color: #4b5563;
}
.empty-list li {
  margin-bottom: 4px;
}

/* Main layout */
.main-layout {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 0.55fr) minmax(0, 0.45fr);
  gap: 12px;
  align-items: flex-start;
}
.left-column {
  padding: 14px 14px 16px;
}
.right-column {
  padding: 14px 14px 16px;
}

/* Sections */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.section-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}
.section-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.mt {
  margin-top: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.summary-item {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f9fafb;
}
.summary-item .label {
  font-size: 12px;
  color: #6b7280;
}
.summary-item .value {
  margin-top: 2px;
  font-size: 14px;
  color: #111827;
  word-break: break-word;
}

.template-compare {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f9fafb;
}
.compare-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;
}
.compare-row .label {
  color: #6b7280;
}
.compare-row .value {
  color: #111827;
}
.template-warning {
  margin-top: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  background: #fef2f2;
  color: #b91c1c;
}

/* Scope */
.scope-card {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f9fafb;
}
.radio-row {
  display: flex;
  align-items: center;
  font-size: 13px;
  gap: 8px;
  margin-bottom: 4px;
}
.subject-select {
  margin-top: 8px;
}
.helper {
  margin: 0 0 6px;
  font-size: 13px;
  color: #6b7280;
}
.subject-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}
.subject-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}

/* Conflicts */
.conflict-table-wrapper {
  margin-top: 10px;
  max-height: 60vh;
  overflow: auto;
}
.conflict-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.conflict-table th,
.conflict-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 6px 8px;
  vertical-align: top;
}
.conflict-table th {
  background: #f9fafb;
  position: sticky;
  top: 0;
  z-index: 1;
}
.val-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.val-main {
  word-break: break-word;
}
.val-meta {
  font-size: 11px;
  color: #6b7280;
}
.choice-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.radio-inline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

/* Subject filter in conflicts header */
.subject-filter {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.subject-filter select {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 12px;
  background: #fff;
}

/* Merge summary badge */
.badge-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
}
.badge-pill.conflict {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}
.badge-pill.ok {
  background: #ecfdf3;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

/* Sticky footer */
.global-commit {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(16, 24, 40, 0.08);
}
.sel-summary {
  display: flex;
  gap: 6px;
  align-items: center;
  color: #374151;
  flex-wrap: wrap;
  font-size: 13px;
}
.sel-sub {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}
.dot {
  margin: 0 4px;
  color: #9ca3af;
}

/* Responsive */
@media (max-width: 980px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
  .global-commit {
    flex-direction: column;
    align-items: flex-start;
  }
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
}
</style>
