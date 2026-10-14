               <template>
  <div v-if="visible" class="import-overlay" @click.self="$emit('close')">
    <div class="import-dialog">
      <div class="import-header">
        <div>
          <h2>Import Data</h2>
          <p class="subtitle">
            Upload a CSV or Excel file, map its columns, preview the rows, and import only the valid ones.
          </p>
        </div>
        <button type="button" class="icon-btn" @click="$emit('close')" title="Close">✕</button>
      </div>

      <div class="wizard-steps" aria-label="Import progress">
        <button v-for="item in wizardSteps" :key="item.step" type="button" :class="{ active: wizardStep === item.step, complete: wizardStep > item.step }" :disabled="item.step > furthestWizardStep" @click="goToWizardStep(item.step)">
          <span>{{ item.step }}</span>{{ item.label }}
        </button>
      </div>

      <div class="import-body">
        <div class="import-main">
          <!-- STEP 1 -->
          <section v-show="wizardStep === 1" class="panel">
            <h3>Choose who and where to import</h3>

            <div class="mode-grid">
              <label class="mode-card" :class="{ active: importMode === 'single' }">
                <input type="radio" value="single" v-model="importMode" />
                <div class="mode-title">One selected subject</div>
                <div class="mode-sub">Import one row into one selected subject and visit.</div>
              </label>

              <label class="mode-card" :class="{ active: importMode === 'all' }">
                <input type="radio" value="all" v-model="importMode" />
                <div class="mode-title">All subjects</div>
                <div class="mode-sub">Stage many rows, validate them, and commit only valid rows.</div>
              </label>
            </div>
          </section>

          <!-- STEP 2 -->
          <section v-show="wizardStep === 1" class="panel">
            <h3>Destination</h3>

            <div v-if="importMode === 'single'" class="target-grid">
              <div class="control">
                <label for="targetSubject">Subject</label>
                <select id="targetSubject" v-model.number="selectedSubjectIndex">
                  <option v-for="s in subjects" :key="`sub-${s.index}`" :value="s.index">
                    {{ s.label }}
                  </option>
                </select>
              </div>
              <div class="control">
                <label for="singleVisit">Visit</label>
                <select id="singleVisit" v-model.number="singleVisitIndex">
                  <option v-for="visit in normalizedVisits" :key="`single-visit-${visit.index}`" :value="visit.index">{{ visit.name }}</option>
                </select>
              </div>

              <div class="target-card">
                <div class="target-label">Group</div>
                <div class="target-value">{{ selectedSubjectGroupLabel || "—" }}</div>
              </div>
            </div>

            <div v-else class="info-box">
              Each spreadsheet row is matched to a subject. Visit and group can come from columns or use one selection for every row.
            </div>
          </section>

          <!-- STEP 3 -->
          <section v-show="wizardStep === 2" class="panel">
            <h3>Upload and identify the layout</h3>

            <div class="upload-row">
              <input
                ref="fileInput"
                type="file"
                accept=".csv,.xlsx,.xls"
                @change="onFileChange"
              />
            </div>

            <div v-if="fileName" class="file-meta">
              <strong>File:</strong> {{ fileName }}
            </div>

            <div v-if="sheetNames.length" class="sheet-row">
              <div class="control">
                <label for="sheetSelect">Sheet</label>
                <select id="sheetSelect" v-model="selectedSheetName" @change="rebuildFromSheet">
                  <option v-for="sheet in sheetNames" :key="sheet" :value="sheet">
                    {{ sheet }}
                  </option>
                </select>
              </div>

              <div class="control">
                <label for="headerMode">Header mode</label>
                <select id="headerMode" v-model="headerMode" @change="buildColumnsAndRows">
                  <option value="auto">Auto detect</option>
                  <option value="single">Single header row</option>
                  <option value="two-row">Two header rows (Section + Field)</option>
                  <option value="three-row">Three header rows (Section + Field + Stable key)</option>
                  <option value="legacy-sections">Header-only columns mark sections</option>
                </select>
              </div>
              <div class="control">
                <label for="headerRow">First header row</label>
                <select id="headerRow" v-model.number="headerRowIndex" @change="buildColumnsAndRows">
                  <option v-for="number in headerRowOptions" :key="`header-row-${number}`" :value="number - 1">Row {{ number }}</option>
                </select>
              </div>
            </div>

            <div v-if="workbookError" class="error-box">
              {{ workbookError }}
            </div>
            <div v-if="structureInfo" class="info-box">{{ structureInfo }}</div>
          </section>

          <!-- STEP 4 -->
          <section v-show="wizardStep === 2" v-if="columns.length && dataRows.length" class="panel">
            <h3>Subject, visit and group</h3>

            <div class="meta-grid">
              <div v-if="importMode === 'single'" class="control">
                <label>Spreadsheet row</label>
                <select v-model.number="singleDataRowIndex">
                  <option v-for="row in importableRowOptions" :key="`single-row-${row.index}`" :value="row.index">
                    Row {{ displayRowNumber(row.index) }}{{ row.example ? ` — ${row.example}` : "" }}
                  </option>
                </select>
              </div>
              <div v-if="importMode === 'all'" class="control">
                <label>Subject column</label>
                <select v-model="metadataMapping.subject">
                  <option value="">Not present</option>
                  <option v-for="col in columns" :key="`sub-col-${col.columnIndex}`" :value="String(col.columnIndex)">
                    {{ col.displayName }}
                  </option>
                </select>
              </div>

              <div v-if="importMode === 'all'" class="control source-control"><label>Visit source</label><select v-model="visitSource"><option value="fixed">Use one visit for all rows</option><option value="column">Read visit from a column</option></select><select v-if="visitSource === 'column'" v-model="metadataMapping.visit"><option value="">Select visit column…</option><option v-for="col in columns" :key="`vis-col-${col.columnIndex}`" :value="String(col.columnIndex)">{{ col.displayName }}</option></select><select v-else v-model.number="bulkVisitIndex"><option v-for="visit in normalizedVisits" :key="`bulk-visit-${visit.index}`" :value="visit.index">{{ visit.name }}</option></select></div>
              <div v-if="importMode === 'all'" class="control source-control"><label>Group source</label><select v-model="groupSource"><option value="subject">Use each subject's assigned group</option><option value="column">Validate against a file column</option><option value="fixed">Validate one group for all rows</option></select><select v-if="groupSource === 'column'" v-model="metadataMapping.group"><option value="">Select group column…</option><option v-for="col in columns" :key="`grp-col-${col.columnIndex}`" :value="String(col.columnIndex)">{{ col.displayName }}</option></select><select v-else-if="groupSource === 'fixed'" v-model.number="bulkGroupIndex"><option v-for="group in normalizedGroups" :key="`bulk-group-${group.index}`" :value="group.index">{{ group.name }}</option></select></div>
            </div>

            <div class="meta-hint">
              Missing visit or group columns are supported. Select one visit for all rows and use each subject's assigned group.
            </div>
          </section>

          <!-- STEP 5 -->
          <section v-show="wizardStep === 3" v-if="columns.length" class="panel">
            <h3>Match fields</h3>

            <div class="mapping-tools">
              <label class="check-inline">
                <input type="checkbox" v-model="showUnmappedOnly" />
                Show only unmatched
              </label>

              <input
                v-model.trim="mappingSearch"
                type="text"
                placeholder="Search mapping..."
                class="search-input"
              />

              <button type="button" class="btn-secondary" @click="applyAutoMapping">
                Auto match
              </button>

              <button type="button" class="btn-secondary" @click="clearMappings">
                Clear
              </button>
            </div>

            <div v-if="!mappableColumns.length" class="info-box">
              No non-metadata columns are available for field mapping.
            </div>
            <div v-if="autoMappingIssues.length" class="warning-box soft">
              <div v-for="(issue, index) in autoMappingIssues" :key="`auto-map-issue-${index}`">{{ issue }}</div>
            </div>
            <div v-if="mappingCollisions.length" class="error-box">
              <div v-for="issue in mappingCollisions" :key="issue">{{ issue }}</div>
            </div>

            <div v-else class="mapping-table-wrap">
              <table class="mapping-table">
                <thead>
                  <tr>
                    <th>Spreadsheet column</th>
                    <th>Map to Case-e field</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="col in filteredColumnsForMapping" :key="`map-${col.columnIndex}`">
                    <td>
                      <div class="col-title">{{ col.displayName }}</div>
                      <div class="col-sub">Example: {{ firstNonEmptyValueForColumn(col.columnIndex) || "—" }}</div>
                    </td>
                    <td>
                      <select v-model="mappings[col.columnIndex]" class="mapping-select">
                        <option value="">Do not import</option>
                        <option
                          v-for="field in availableFields"
                          :key="field.key"
                          :value="field.key"
                        >
                          {{ field.sectionTitle }} → {{ field.fieldLabel }}
                        </option>
                      </select>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- STEP 6 -->
          <section v-show="wizardStep === 3" v-if="columns.length && dataRows.length" class="panel">
            <h3>Check sample rows</h3>

            <div class="mapping-tools">
              <label class="check-inline">
                <input type="checkbox" v-model="showOnlyRowsWithData" />
                Show only rows with at least one value
              </label>

              <input
                v-model.trim="csvSearch"
                type="text"
                placeholder="Search spreadsheet rows..."
                class="search-input"
              />
            </div>

            <div class="csv-preview-wrap">
              <table class="csv-preview-table">
                <thead>
                  <tr>
                    <th class="sticky-col">Row</th>
                    <th
                      v-for="col in columns"
                      :key="`csv-head-${col.columnIndex}`"
                    >
                      {{ col.displayName }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="rowItem in filteredCsvRows"
                    :key="`csv-row-${rowItem.rowIndex}`"
                  >
                    <td class="sticky-col">{{ displayRowNumber(rowItem.rowIndex) }}</td>
                    <td
                      v-for="col in columns"
                      :key="`csv-cell-${rowItem.rowIndex}-${col.columnIndex}`"
                    >
                      {{ rowItem.values[col.columnIndex] || "—" }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- STEP 7 -->
          <section v-show="wizardStep === 4" v-if="columns.length && dataRows.length" class="panel">
            <h3>Validate before importing</h3>

            <div class="analyze-actions">
              <button
                type="button"
                class="btn-primary"
                :disabled="analyzing || mappingCollisions.length > 0"
                @click="emitAnalyze"
              >
                {{ analyzing ? "Validating..." : "Build Import Preview" }}
              </button>
            </div>

            <div class="meta-hint">
              This will run the same visibility, calculation, and validation pipeline as Study Data Entry before anything is committed.
            </div>
          </section>

          <!-- STEP 8 -->
          <section v-show="wizardStep === 4" v-if="hasPreview" class="panel">
            <h3>Import preview</h3>

            <div class="all-summary-grid">
              <div class="summary-card">
                <div class="summary-label">Rows analysed</div>
                <div class="summary-value">{{ previewSummary.totalRows }}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">Ready</div>
                <div class="summary-value">{{ previewSummary.readyRows }}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">Warnings</div>
                <div class="summary-value">{{ previewSummary.warningRows }}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">Errors</div>
                <div class="summary-value">{{ previewSummary.errorRows }}</div>
              </div>
            </div>

            <div class="mapping-tools">
              <label class="check-inline">
                <input type="checkbox" v-model="showOnlyInvalidPreviewRows" />
                Show only rows with issues
              </label>

              <input
                v-model.trim="previewSearch"
                type="text"
                placeholder="Search preview rows..."
                class="search-input"
              />
            </div>

            <div class="all-preview-wrap">
              <table class="all-preview-table">
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Subject</th>
                    <th>Visit</th>
                    <th>Group</th>
                    <th>Mapped Values</th>
                    <th>Status</th>
                    <th>Issues</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in filteredPreviewRows"
                    :key="`preview-row-${row.rowIndex}`"
                  >
                    <td>{{ displayRowNumber(row.rowIndex) }}</td>
                    <td>{{ row.subjectLabel || "—" }}</td>
                    <td>{{ row.visitLabel || "—" }}</td>
                    <td>{{ row.groupLabel || "—" }}</td>
                    <td>{{ row.mappedValueCount }}</td>
                    <td>
                      <span class="status-pill" :class="statusClass(row.status)">
                        {{ row.status }}
                      </span>
                    </td>
                    <td>
                      <div v-if="row.issues && row.issues.length" class="issue-list">
                        <div v-for="(issue, idx) in row.issues" :key="`issue-${row.rowIndex}-${idx}`">
                          {{ issue }}
                        </div>
                      </div>
                      <span v-else>—</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="previewSummary.errorRows || previewSummary.warningRows" class="warning-box soft">
              Rows with issues are not committed. Please correct the spreadsheet and upload again, or commit only the valid rows.
            </div>
          </section>
        </div>
      </div>

      <div class="import-footer">
        <button type="button" class="btn-secondary" @click="$emit('close')">
          Cancel
        </button>
        <div class="footer-spacer"></div>
        <button v-if="wizardStep > 1" type="button" class="btn-secondary" @click="wizardStep -= 1">Back</button>
        <button v-if="wizardStep < 4" type="button" class="btn-primary" :disabled="!canContinueWizard" @click="advanceWizard">Continue</button>
        <button
          v-if="wizardStep === 4 && hasPreview"
          type="button"
          class="btn-primary"
          :disabled="committing || !previewSummary.readyRows"
          @click="$emit('commit')"
        >
          {{ committing ? "Committing..." : `Commit Valid Rows (${previewSummary.readyRows})` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
/* eslint-disable */
import * as XLSX from "xlsx";
import { compositeImportKey, normalizeImportText, parseSpreadsheetStructure, stripLegacyColumnSuffix } from "@/utils/spreadsheetStructure";

export default {
  name: "StudyDataImportDialog",
  props: {
    visible: { type: Boolean, default: false },
    availableFields: { type: Array, default: () => [] },
    subjects: { type: Array, default: () => [] },
    visits: { type: Array, default: () => [] },
    groups: { type: Array, default: () => [] },
    initialVisitIndex: { type: Number, default: 0 },
    visitLabel: { type: String, default: "" },

    previewRows: { type: Array, default: () => [] },
    previewSummary: {
      type: Object,
      default: () => ({
        totalRows: 0,
        readyRows: 0,
        warningRows: 0,
        errorRows: 0,
      }),
    },
    analyzing: { type: Boolean, default: false },
    committing: { type: Boolean, default: false },
  },
  emits: ["close", "analyze", "commit"],
  data() {
    return {
      importMode: "single",
      selectedSubjectIndex: 0,
      wizardStep: 1,
      furthestWizardStep: 1,
      singleVisitIndex: 0,
      singleDataRowIndex: 0,
      visitSource: "fixed",
      bulkVisitIndex: 0,
      groupSource: "subject",
      bulkGroupIndex: 0,

      workbook: null,
      workbookError: "",
      fileName: "",
      sheetNames: [],
      selectedSheetName: "",
      headerMode: "auto",
      headerRowIndex: 0,

      rawAoA: [],
      rawValueAoA: [],
      columns: [],
      dataRows: [],
      rawDataRows: [],
      dataStartIndex: 1,
      detectedLayout: "single",
      structureInfo: "",
      autoMappingIssues: [],

      mappings: {},
      metadataMapping: {
        subject: "",
        visit: "",
        group: "",
      },

      mappingSearch: "",
      previewSearch: "",
      csvSearch: "",
      showUnmappedOnly: false,
      showOnlyInvalidPreviewRows: false,
      showOnlyRowsWithData: false,
    };
  },
  computed: {
    wizardSteps() {
      return [
        { step: 1, label: "Destination" },
        { step: 2, label: "File & context" },
        { step: 3, label: "Field mapping" },
        { step: 4, label: "Review & import" },
      ];
    },
    normalizedVisits() {
      return (this.visits || []).map((visit, index) => ({
        index,
        name: String(visit?.name || `Visit ${index + 1}`),
      }));
    },
    normalizedGroups() {
      return (this.groups || []).map((group, index) => ({
        index,
        name: String(group?.name || `Group ${index + 1}`),
      }));
    },
    headerRowOptions() {
      return Array.from({ length: Math.min(this.rawAoA.length, 25) }, (_, index) => index + 1);
    },
    importableRowOptions() {
      return this.dataRows
        .map((row, index) => ({
          index,
          example: (row || []).map((value) => String(value ?? "").trim()).find(Boolean) || "",
          hasData: (row || []).some((value) => String(value ?? "").trim()),
        }))
        .filter((row) => row.hasData);
    },
    canContinueWizard() {
      if (this.wizardStep === 1) {
        if (this.importMode === "single") {
          return !!this.selectedSubject && this.normalizedVisits.some((visit) => visit.index === Number(this.singleVisitIndex));
        }
        return this.subjects.length > 0 && this.normalizedVisits.length > 0;
      }
      if (this.wizardStep === 2) {
        if (!this.columns.length || !this.dataRows.length) return false;
        if (this.importMode === "single" && !this.importableRowOptions.some((row) => row.index === Number(this.singleDataRowIndex))) return false;
        if (this.importMode === "all" && this.metadataMapping.subject === "") return false;
        if (this.importMode === "all" && this.visitSource === "column" && this.metadataMapping.visit === "") return false;
        if (this.importMode === "all" && this.visitSource === "fixed" && !this.normalizedVisits.some((visit) => visit.index === Number(this.bulkVisitIndex))) return false;
        if (this.importMode === "all" && this.groupSource === "column" && this.metadataMapping.group === "") return false;
        if (this.importMode === "all" && this.groupSource === "fixed" && !this.normalizedGroups.some((group) => group.index === Number(this.bulkGroupIndex))) return false;
        return true;
      }
      if (this.wizardStep === 3) {
        return Object.values(this.effectiveMappings).some(Boolean) && this.mappingCollisions.length === 0;
      }
      return true;
    },
    selectedSubject() {
      return this.subjects.find((s) => Number(s.index) === Number(this.selectedSubjectIndex)) || null;
    },
    selectedSubjectGroupLabel() {
      return this.selectedSubject?.groupLabel || "";
    },

    hasPreview() {
      return Array.isArray(this.previewRows) && this.previewRows.length > 0;
    },

    metadataColumnIndexSet() {
      const out = new Set();
      const metadataColumns = [this.metadataMapping.subject];
      if (this.importMode === "all" && this.visitSource === "column") metadataColumns.push(this.metadataMapping.visit);
      if (this.importMode === "all" && this.groupSource === "column") metadataColumns.push(this.metadataMapping.group);
      metadataColumns
        .filter((x) => x !== "" && x != null)
        .forEach((x) => {
          const n = Number(x);
          if (Number.isInteger(n) && n >= 0) out.add(n);
        });
      return out;
    },

    mappableColumns() {
      return this.columns.filter((col) => !this.metadataColumnIndexSet.has(col.columnIndex));
    },
    effectiveMappings() {
      const allowed = new Set(this.mappableColumns.map((column) => String(column.columnIndex)));
      return Object.fromEntries(
        Object.entries(this.mappings || {}).filter(([columnIndex, targetKey]) => allowed.has(String(columnIndex)) && targetKey)
      );
    },

    filteredColumnsForMapping() {
      let cols = [...this.mappableColumns];

      if (this.showUnmappedOnly) {
        cols = cols.filter((c) => !this.mappings[c.columnIndex]);
      }

      const q = String(this.mappingSearch || "").trim().toLowerCase();
      if (!q) return cols;

      return cols.filter((c) => {
        const mappedField = this.availableFields.find((f) => f.key === this.mappings[c.columnIndex]);
        const hay = [
          c.displayName,
          c.sectionName,
          c.fieldName,
          mappedField?.sectionTitle,
          mappedField?.fieldLabel,
        ].filter(Boolean).join(" ").toLowerCase();
        return hay.includes(q);
      });
    },

    filteredCsvRows() {
      const q = String(this.csvSearch || "").trim().toLowerCase();

      let rows = this.dataRows.map((row, idx) => ({
        rowIndex: idx,
        values: row,
      }));

      if (this.showOnlyRowsWithData) {
        rows = rows.filter((r) =>
          (r.values || []).some((v) => !(v == null || String(v).trim() === ""))
        );
      }

      if (!q) return rows;

      return rows.filter((r) =>
        (r.values || []).some((v) => String(v || "").toLowerCase().includes(q))
      );
    },

    filteredPreviewRows() {
      let rows = Array.isArray(this.previewRows) ? [...this.previewRows] : [];

      if (this.showOnlyInvalidPreviewRows) {
        rows = rows.filter((r) => r.status !== "Ready");
      }

      const q = String(this.previewSearch || "").trim().toLowerCase();
      if (!q) return rows;

      return rows.filter((r) => {
        const hay = [
          r.subjectLabel,
          r.visitLabel,
          r.groupLabel,
          r.status,
          ...(Array.isArray(r.issues) ? r.issues : []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return hay.includes(q);
      });
    },
    mappingCollisions() {
      const targets = new Map();
      Object.entries(this.effectiveMappings).forEach(([columnIndex, targetKey]) => {
        if (!targetKey) return;
        if (!targets.has(targetKey)) targets.set(targetKey, []);
        targets.get(targetKey).push(Number(columnIndex));
      });
      return [...targets.entries()].filter(([, indexes]) => indexes.length > 1).map(([targetKey, indexes]) => {
        const field = this.availableFields.find(item => item.key === targetKey);
        const sourceNames = indexes.map(index => this.columns.find(column => column.columnIndex === index)?.displayName || `Column ${index + 1}`);
        return `${sourceNames.join(", ")} all map to ${field?.sectionTitle || "section"} → ${field?.fieldLabel || targetKey}. Each target field can be mapped only once.`;
      });
    },
  },
  watch: {
    visible(v) {
      if (!v) this.resetState();
    },
    subjects: {
      immediate: true,
      handler(list) {
        if (Array.isArray(list) && list.length) {
          this.selectedSubjectIndex = list[0].index;
        }
      },
    },
    visits: {
      immediate: true,
      handler() {
        const preferred = Number.isInteger(this.initialVisitIndex) && this.initialVisitIndex >= 0
          ? this.initialVisitIndex
          : 0;
        this.singleVisitIndex = this.normalizedVisits.some((visit) => visit.index === preferred) ? preferred : 0;
        this.bulkVisitIndex = this.singleVisitIndex;
      },
    },
    groups: {
      immediate: true,
      handler() {
        if (!this.normalizedGroups.some((group) => group.index === Number(this.bulkGroupIndex))) {
          this.bulkGroupIndex = this.normalizedGroups[0]?.index ?? 0;
        }
      },
    },
  },
  methods: {
    statusClass(status) {
      if (status === "Ready") return "good";
      if (status === "Warning") return "partial";
      return "bad";
    },

    resetState() {
      this.importMode = "single";
      this.selectedSubjectIndex = Array.isArray(this.subjects) && this.subjects.length ? this.subjects[0].index : 0;
      this.wizardStep = 1;
      this.furthestWizardStep = 1;
      this.singleVisitIndex = this.normalizedVisits.some((visit) => visit.index === this.initialVisitIndex) ? this.initialVisitIndex : 0;
      this.singleDataRowIndex = 0;
      this.bulkVisitIndex = this.singleVisitIndex;
      this.visitSource = "fixed";
      this.groupSource = "subject";
      this.bulkGroupIndex = this.normalizedGroups[0]?.index ?? 0;
      this.workbook = null;
      this.workbookError = "";
      this.fileName = "";
      this.sheetNames = [];
      this.selectedSheetName = "";
      this.headerMode = "auto";
      this.headerRowIndex = 0;
      this.rawAoA = [];
      this.rawValueAoA = [];
      this.columns = [];
      this.dataRows = [];
      this.rawDataRows = [];
      this.dataStartIndex = 1;
      this.detectedLayout = "single";
      this.structureInfo = "";
      this.autoMappingIssues = [];
      this.mappings = {};
      this.metadataMapping = { subject: "", visit: "", group: "" };
      this.mappingSearch = "";
      this.previewSearch = "";
      this.csvSearch = "";
      this.showUnmappedOnly = false;
      this.showOnlyInvalidPreviewRows = false;
      this.showOnlyRowsWithData = false;

      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = "";
      }
    },

    async onFileChange(event) {
      const file = event?.target?.files?.[0];
      if (!file) return;

      this.workbookError = "";
      this.fileName = file.name;

      try {
        const buffer = await file.arrayBuffer();
        const wb = XLSX.read(buffer, { type: "array", cellDates: true, cellNF: true });

        this.workbook = wb;
        this.sheetNames = wb.SheetNames || [];
        this.selectedSheetName = this.sheetNames[0] || "";

        if (!this.selectedSheetName) {
          this.workbookError = "No sheet was found in the uploaded file.";
          return;
        }

        this.rebuildFromSheet();
      } catch (e) {
        console.error("Failed to read file", e);
        this.workbookError = "The selected file could not be read. Please upload a valid CSV or Excel file.";
      }
    },

    rebuildFromSheet() {
      if (!this.workbook || !this.selectedSheetName) return;

      const sheet = this.workbook.Sheets[this.selectedSheetName];
      const aoa = XLSX.utils.sheet_to_json(sheet, {
        header: 1,
        defval: "",
        raw: false,
        blankrows: false,
      });
      const rawValueAoA = XLSX.utils.sheet_to_json(sheet, {
        header: 1,
        defval: "",
        raw: true,
        blankrows: false,
      });

      this.rawAoA = Array.isArray(aoa) ? aoa : [];
      this.rawValueAoA = Array.isArray(rawValueAoA) ? rawValueAoA : [];
      if (this.headerRowIndex >= this.rawAoA.length) this.headerRowIndex = 0;
      this.buildColumnsAndRows();
    },

    buildColumnsAndRows() {
      this.columns = [];
      this.dataRows = [];
      this.rawDataRows = [];
      this.mappings = {};
      this.metadataMapping = { subject: "", visit: "", group: "" };

      if (!Array.isArray(this.rawAoA) || !this.rawAoA.length) {
        this.workbookError = "The selected sheet is empty.";
        return;
      }

      const rows = this.rawAoA.map((r) => (Array.isArray(r) ? r : []));
      const parsed = parseSpreadsheetStructure(rows, {
        layout: this.headerMode,
        headerRowIndex: this.headerRowIndex,
      });
      this.detectedLayout = parsed.layout;
      this.columns = parsed.columns;
      this.dataRows = parsed.dataRows;
      this.rawDataRows = this.rawValueAoA.slice(parsed.dataStartIndex);
      this.singleDataRowIndex = this.importableRowOptions[0]?.index ?? 0;
      this.dataStartIndex = parsed.dataStartIndex;
      this.structureInfo = parsed.layout === "legacy-sections"
        ? `${parsed.markerIndexes.length} header-only section column(s) were recognized and excluded from participant data. Confirm the Header mode; choose Single header row if any of these are unanswered fields instead.`
        : `Using ${parsed.layout === "three-row" ? "three" : parsed.layout === "two-row" ? "two" : "one"} header row(s).`;

      this.prefillMetadataMappings();
      this.applyAutoMapping();
    },

    detectHeaderMode() {
      return this.detectedLayout || "single";
    },

    cellText(v) {
      return String(v == null ? "" : v).trim();
    },

    normalizeText(v) {
      return normalizeImportText(v);
    },

    applyAutoMapping() {
      const next = {};
      const usedTargets = new Set();
      const issues = [];
      for (const col of this.mappableColumns) {
        const stableKey = this.normalizeText(col.stableKey);
        const compositeKey = compositeImportKey(col.sectionName, col.fieldName);
        const sourceAliases = [col.sourceAlias, col.rawHeader].map(this.normalizeText).filter(Boolean);
        let matches = this.availableFields.filter(field => stableKey && [field.stableFieldKey, field.fieldName].map(this.normalizeText).includes(stableKey));
        if (!matches.length && col.sectionName) matches = this.availableFields.filter(field => compositeImportKey(field.sectionTitle, field.fieldLabel) === compositeKey);
        if (!matches.length) matches = this.availableFields.filter(field => (field.importAliases || []).map(this.normalizeText).some(alias => sourceAliases.includes(alias)));
        if (!matches.length) {
          const cleanLabel = this.normalizeText(stripLegacyColumnSuffix(col.fieldName));
          const labelMatches = this.availableFields.filter(field => this.normalizeText(field.fieldLabel) === cleanLabel);
          if (labelMatches.length === 1) matches = labelMatches;
        }
        if (matches.length > 1) {
          issues.push(`${col.displayName} matches more than one Case-e field and must be mapped manually.`);
          next[col.columnIndex] = "";
        } else if (matches.length === 1 && usedTargets.has(matches[0].key)) {
          issues.push(`${col.displayName} resolves to a field already used by another column and was left unmapped.`);
          next[col.columnIndex] = "";
        } else {
          next[col.columnIndex] = matches[0]?.key || "";
          if (matches[0]) usedTargets.add(matches[0].key);
        }
      }
      this.autoMappingIssues = issues;
      this.mappings = next;
    },

    clearMappings() {
      const next = {};
      this.mappableColumns.forEach((col) => {
        next[col.columnIndex] = "";
      });
      this.mappings = next;
    },

    prefillMetadataMappings() {
      const findFirst = (patterns) => {
        for (const pattern of patterns) {
          const found = this.columns.find(col => this.normalizeText(col.displayName).includes(pattern));
          if (found) return String(found.columnIndex);
        }
        return "";
      };

      this.metadataMapping.subject = findFirst([
        "subject id",
        "probanden code",
        "participant id",
        "subject",
        "participant",
        "teilnehmer",
      ]);

      this.metadataMapping.visit = findFirst([
        "visit",
        "visit name",
        "timepoint",
        "session",
      ]);

      this.metadataMapping.group = findFirst([
        "group",
        "arm",
        "cohort",
      ]);

      this.visitSource = this.metadataMapping.visit ? "column" : "fixed";
      this.groupSource = this.metadataMapping.group ? "column" : "subject";
    },

    firstNonEmptyValueForColumn(columnIndex) {
      for (const row of this.dataRows) {
        const v = row?.[columnIndex];
        if (!(v == null || String(v).trim() === "")) return String(v);
      }
      return "";
    },

    displayRowNumber(dataRowIndex) {
      return dataRowIndex + this.dataStartIndex + 1;
    },

    emitAnalyze() {
      if (this.mappingCollisions.length) return;
      this.$emit("analyze", {
        mode: this.importMode,
        selectedSubjectIndex: Number(this.selectedSubjectIndex),
        singleDataRowIndex: Number(this.singleDataRowIndex),
        selectedSubjectLabel: this.selectedSubject?.label || "",
        singleVisitIndex: Number(this.singleVisitIndex),
        visitSource: this.visitSource,
        bulkVisitIndex: Number(this.bulkVisitIndex),
        groupSource: this.groupSource,
        bulkGroupIndex: Number(this.bulkGroupIndex),
        visitLabel: this.normalizedVisits.find((visit) => visit.index === Number(this.singleVisitIndex))?.name || this.visitLabel || "",
        selectedSubjectGroupLabel: this.selectedSubjectGroupLabel || "",
        metadataMapping: { ...this.metadataMapping },
        mappings: { ...this.effectiveMappings },
        columns: this.columns,
        dataRows: this.dataRows,
        rawDataRows: this.rawDataRows,
      });
    },
    advanceWizard() {
      if (!this.canContinueWizard || this.wizardStep >= 4) return;
      this.wizardStep += 1;
      this.furthestWizardStep = Math.max(this.furthestWizardStep, this.wizardStep);
      if (this.wizardStep === 4) this.emitAnalyze();
    },
    goToWizardStep(step) {
      const nextStep = Number(step);
      if (!Number.isInteger(nextStep) || nextStep < 1 || nextStep > this.furthestWizardStep) return;
      this.wizardStep = nextStep;
      if (nextStep === 4) this.emitAnalyze();
    },
  },
};
</script>

<style scoped>
.import-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.import-dialog {
  width: min(1500px, 98vw);
  max-height: 94vh;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.import-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 18px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.import-header h2 {
  margin: 0;
  font-size: 22px;
  color: #111827;
}

.wizard-steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.wizard-steps button {
  border: 0;
  background: #fff;
  color: #6b7280;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.wizard-steps button span {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  margin-right: 8px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #374151;
}

.wizard-steps button.active {
  color: #1d4ed8;
  background: #eff6ff;
}

.wizard-steps button.active span,
.wizard-steps button.complete span {
  background: #2563eb;
  color: #fff;
}

.wizard-steps button:disabled {
  cursor: default;
  color: #9ca3af;
}

.subtitle {
  margin: 6px 0 0 0;
  font-size: 14px;
  color: #6b7280;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  color: #6b7280;
  padding: 6px 8px;
}

.import-body {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  background: #f9fafb;
  overflow: hidden;
}

.import-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 18px;
}

.panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.panel h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #111827;
}

.mode-grid,
.target-grid,
.meta-grid,
.sheet-row,
.mapping-tools,
.toolbar,
.analyze-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: stretch;
}

.mode-card {
  flex: 1 1 280px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  background: #fff;
}

.mode-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.mode-card input {
  margin-right: 8px;
}

.mode-title {
  font-weight: 600;
  color: #111827;
  margin-top: 6px;
}

.mode-sub {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 220px;
  margin-bottom: 12px;
}

.control label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.source-control {
  flex: 1 1 280px;
}

.target-card,
.summary-card {
  flex: 1 1 220px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 10px;
  padding: 12px;
}

.target-label,
.summary-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

.target-value,
.summary-value {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.file-meta {
  margin-top: 10px;
  font-size: 14px;
  color: #374151;
}

.meta-hint {
  margin-top: 10px;
  font-size: 13px;
  color: #6b7280;
}

.mapping-table-wrap,
.csv-preview-wrap,
.all-preview-wrap,
.meta-table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.mapping-table,
.csv-preview-table,
.all-preview-table,
.meta-table {
  width: 100%;
  min-width: 1100px;
  border-collapse: collapse;
}

.mapping-table th,
.mapping-table td,
.csv-preview-table th,
.csv-preview-table td,
.all-preview-table th,
.all-preview-table td,
.meta-table th,
.meta-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

.mapping-table th,
.csv-preview-table th,
.all-preview-table th,
.meta-table th {
  background: #f3f4f6;
  color: #111827;
  position: sticky;
  top: 0;
}

.sticky-col {
  position: sticky;
  left: 0;
  z-index: 1;
  background: #f9fafb;
  min-width: 70px;
}

.csv-preview-table thead .sticky-col {
  background: #f3f4f6;
  z-index: 2;
}

.col-title {
  font-weight: 600;
  color: #111827;
}

.col-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.mapping-select,
select,
.search-input {
  min-height: 38px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  background: #fff;
}

.mapping-select {
  width: 100%;
}

.check-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #374151;
  font-size: 14px;
}

.info-box {
  margin-top: 12px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}

.warning-box {
  margin-top: 12px;
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}

.warning-box.soft {
  background: #fffbeb;
  color: #92400e;
  border-color: #fde68a;
}

.error-box {
  margin-top: 12px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}

.status-pill {
  display: inline-block;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-pill.good {
  background: #dcfce7;
  color: #166534;
}

.status-pill.partial {
  background: #fef3c7;
  color: #92400e;
}

.status-pill.bad {
  background: #fee2e2;
  color: #991b1b;
}

.issue-list {
  display: grid;
  gap: 4px;
}

.all-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.import-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.footer-spacer {
  flex: 1;
}

.btn-primary,
.btn-secondary {
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #e5e7eb;
  color: #111827;
}

@media (max-width: 980px) {
  .wizard-steps {
    grid-template-columns: 1fr 1fr;
  }

  .all-summary-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
