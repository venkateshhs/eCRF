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

      <div class="import-body">
        <div class="import-main">
          <!-- STEP 1 -->
          <section class="panel">
            <h3>1. Choose import mode</h3>

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
          <section class="panel">
            <h3>2. Target context</h3>

            <div v-if="importMode === 'single'" class="target-grid">
              <div class="control">
                <label for="targetSubject">Subject</label>
                <select id="targetSubject" v-model.number="selectedSubjectIndex">
                  <option v-for="s in subjects" :key="`sub-${s.index}`" :value="s.index">
                    {{ s.label }}
                  </option>
                </select>
              </div>

              <div class="target-card">
                <div class="target-label">Visit</div>
                <div class="target-value">{{ visitLabel || "—" }}</div>
              </div>

              <div class="target-card">
                <div class="target-label">Group</div>
                <div class="target-value">{{ selectedSubjectGroupLabel || "—" }}</div>
              </div>
            </div>

            <div v-else class="target-grid">
              <div class="target-card">
                <div class="target-label">Mode</div>
                <div class="target-value">All subjects</div>
              </div>
              <div class="target-card">
                <div class="target-label">Validation</div>
                <div class="target-value">Uses Study Data Entry rules</div>
              </div>
              <div class="target-card">
                <div class="target-label">Commit behavior</div>
                <div class="target-value">Only valid rows are committed</div>
              </div>
            </div>
          </section>

          <!-- STEP 3 -->
          <section class="panel">
            <h3>3. Upload file</h3>

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
                </select>
              </div>
            </div>

            <div v-if="workbookError" class="error-box">
              {{ workbookError }}
            </div>
          </section>

          <!-- STEP 4 -->
          <section v-if="columns.length && dataRows.length" class="panel">
            <h3>4. Match metadata columns</h3>

            <div class="meta-grid">
              <div class="control">
                <label>Subject column</label>
                <select v-model="metadataMapping.subject">
                  <option value="">Not present</option>
                  <option v-for="col in columns" :key="`sub-col-${col.columnIndex}`" :value="String(col.columnIndex)">
                    {{ col.displayName }}
                  </option>
                </select>
              </div>

              <div class="control">
                <label>Visit column</label>
                <select v-model="metadataMapping.visit">
                  <option value="">Not present</option>
                  <option v-for="col in columns" :key="`vis-col-${col.columnIndex}`" :value="String(col.columnIndex)">
                    {{ col.displayName }}
                  </option>
                </select>
              </div>

              <div class="control">
                <label>Group column</label>
                <select v-model="metadataMapping.group">
                  <option value="">Not present</option>
                  <option v-for="col in columns" :key="`grp-col-${col.columnIndex}`" :value="String(col.columnIndex)">
                    {{ col.displayName }}
                  </option>
                </select>
              </div>
            </div>

            <div class="meta-hint">
              These values are used to match spreadsheet rows to Case-e subjects, visits, and groups.
            </div>
          </section>

          <!-- STEP 5 -->
          <section v-if="columns.length" class="panel">
            <h3>5. Map spreadsheet columns to form fields</h3>

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
          <section v-if="columns.length && dataRows.length" class="panel">
            <h3>6. Spreadsheet preview</h3>

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
          <section v-if="columns.length && dataRows.length" class="panel">
            <h3>7. Validate import rows</h3>

            <div class="analyze-actions">
              <button
                type="button"
                class="btn-primary"
                :disabled="analyzing"
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
          <section v-if="hasPreview" class="panel">
            <h3>8. Import preview result</h3>

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
        <button
          v-if="hasPreview"
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

export default {
  name: "StudyDataImportDialog",
  props: {
    visible: { type: Boolean, default: false },
    availableFields: { type: Array, default: () => [] },
    subjects: { type: Array, default: () => [] },
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

      workbook: null,
      workbookError: "",
      fileName: "",
      sheetNames: [],
      selectedSheetName: "",
      headerMode: "auto",

      rawAoA: [],
      columns: [],
      dataRows: [],

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
      [this.metadataMapping.subject, this.metadataMapping.visit, this.metadataMapping.group]
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
      this.workbook = null;
      this.workbookError = "";
      this.fileName = "";
      this.sheetNames = [];
      this.selectedSheetName = "";
      this.headerMode = "auto";
      this.rawAoA = [];
      this.columns = [];
      this.dataRows = [];
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
        const wb = XLSX.read(buffer, { type: "array" });

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

      this.rawAoA = Array.isArray(aoa) ? aoa : [];
      this.buildColumnsAndRows();
    },

    buildColumnsAndRows() {
      this.columns = [];
      this.dataRows = [];
      this.mappings = {};
      this.metadataMapping = { subject: "", visit: "", group: "" };

      if (!Array.isArray(this.rawAoA) || !this.rawAoA.length) {
        this.workbookError = "The selected sheet is empty.";
        return;
      }

      const mode = this.detectHeaderMode();
      const rows = this.rawAoA.map((r) => (Array.isArray(r) ? r : []));

      let columns = [];
      let dataStartIndex = 1;

      if (mode === "two-row" && rows.length >= 2) {
        const row1 = rows[0];
        const row2 = rows[1];
        const width = Math.max(row1.length, row2.length);

        columns = Array.from({ length: width }, (_, i) => {
          const sectionName = this.cellText(row1[i]);
          const fieldName = this.cellText(row2[i]);
          const displayName = [sectionName, fieldName].filter(Boolean).join(" / ") || `Column ${i + 1}`;

          return {
            columnIndex: i,
            sectionName,
            fieldName,
            rawHeader: displayName,
            displayName,
          };
        });

        dataStartIndex = 2;
      } else {
        const headerRow = rows[0];
        const width = headerRow.length;

        columns = Array.from({ length: width }, (_, i) => {
          const rawHeader = this.cellText(headerRow[i]);
          const split = this.splitSingleHeader(rawHeader);

          return {
            columnIndex: i,
            sectionName: split.sectionName,
            fieldName: split.fieldName,
            rawHeader,
            displayName: rawHeader || `Column ${i + 1}`,
          };
        });

        dataStartIndex = 1;
      }

      this.columns = columns;
      this.dataRows = rows.slice(dataStartIndex);

      this.prefillMetadataMappings();
      this.applyAutoMapping();
    },

    detectHeaderMode() {
      if (this.headerMode !== "auto") return this.headerMode;

      const row1 = this.rawAoA?.[0] || [];
      const row2 = this.rawAoA?.[1] || [];

      if (!row1.length || !row2.length) return "single";

      let compoundCount = 0;
      for (let i = 0; i < row1.length; i++) {
        const a = this.cellText(row1[i]);
        if (a.includes(".") || a.includes("/") || a.includes("|") || a.includes("->")) {
          compoundCount += 1;
        }
      }

      if (compoundCount > 0) return "single";
      return "two-row";
    },

    splitSingleHeader(header) {
      const h = String(header || "").trim();
      if (!h) return { sectionName: "", fieldName: "" };

      const separators = [".", "/", "->", "::", "|", " - "];
      for (const sep of separators) {
        if (h.includes(sep)) {
          const parts = h.split(sep).map((x) => String(x || "").trim()).filter(Boolean);
          if (parts.length >= 2) {
            return {
              sectionName: parts[0],
              fieldName: parts.slice(1).join(" "),
            };
          }
        }
      }

      return { sectionName: "", fieldName: h };
    },

    cellText(v) {
      return String(v == null ? "" : v).trim();
    },

    normalizeText(v) {
      return String(v || "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ")
        .replace(/[._/\\|:-]+/g, " ")
        .replace(/[()]/g, "")
        .trim();
    },

    buildSourceCandidates(col) {
      const candidates = new Set();

      const raw = this.normalizeText(col.rawHeader);
      const section = this.normalizeText(col.sectionName);
      const field = this.normalizeText(col.fieldName);
      const display = this.normalizeText(col.displayName);

      if (raw) candidates.add(raw);
      if (display) candidates.add(display);
      if (field) candidates.add(field);
      if (section && field) {
        candidates.add(`${section} ${field}`);
        candidates.add(`${section}.${field}`);
      }

      return [...candidates].filter(Boolean);
    },

    buildFieldCandidates(field) {
      const candidates = new Set();

      [
        field.sectionTitle,
        field.fieldLabel,
        field.fieldName,
        `${field.sectionTitle} ${field.fieldLabel}`,
        `${field.sectionTitle}.${field.fieldLabel}`,
      ]
        .filter(Boolean)
        .forEach((x) => candidates.add(this.normalizeText(x)));

      return [...candidates].filter(Boolean);
    },

    applyAutoMapping() {
      const next = {};

      for (const col of this.mappableColumns) {
        const sourceCandidates = this.buildSourceCandidates(col);

        let exact = this.availableFields.find((field) => {
          const fieldCandidates = this.buildFieldCandidates(field);
          return sourceCandidates.some((src) => fieldCandidates.includes(src));
        });

        if (!exact) {
          exact = this.availableFields.find((field) => {
            const fieldCandidates = this.buildFieldCandidates(field);
            return sourceCandidates.some((src) =>
              fieldCandidates.some((fc) => fc.includes(src) || src.includes(fc))
            );
          });
        }

        next[col.columnIndex] = exact?.key || "";
      }

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
        const found = this.columns.find((col) => {
          const txt = this.normalizeText(col.displayName);
          return patterns.some((p) => txt.includes(p));
        });
        return found ? String(found.columnIndex) : "";
      };

      this.metadataMapping.subject = findFirst([
        "subject id",
        "subject",
        "participant",
        "participant id",
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
    },

    firstNonEmptyValueForColumn(columnIndex) {
      for (const row of this.dataRows) {
        const v = row?.[columnIndex];
        if (!(v == null || String(v).trim() === "")) return String(v);
      }
      return "";
    },

    displayRowNumber(dataRowIndex) {
      const mode = this.detectHeaderMode();
      const headerRows = mode === "two-row" ? 2 : 1;
      return dataRowIndex + headerRows + 1;
    },

    emitAnalyze() {
      this.$emit("analyze", {
        mode: this.importMode,
        selectedSubjectIndex: Number(this.selectedSubjectIndex),
        selectedSubjectLabel: this.selectedSubject?.label || "",
        visitLabel: this.visitLabel || "",
        selectedSubjectGroupLabel: this.selectedSubjectGroupLabel || "",
        metadataMapping: { ...this.metadataMapping },
        mappings: { ...this.mappings },
        columns: this.columns,
        dataRows: this.dataRows,
      });
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
  .all-summary-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>