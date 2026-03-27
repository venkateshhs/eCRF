<template>
  <div class="import-dialog-shell">
    <div class="modal import-csv-modal">
      <div class="import-header">
        <h3>Import Fields from CSV / Excel</h3>
        <button class="icon-button" @click="$emit('close')" title="Close">✕</button>
      </div>

      <!-- STEP 1 -->
      <div v-if="step === 1" class="import-step">
        <div class="field-grid single">
          <div class="field-block">
            <label class="label">Choose file</label>
            <input
              ref="fileInput"
              type="file"
              class="input"
              accept=".csv,.xlsx,.xls"
              @change="onFilePicked"
            />
            <small class="help">Supported: CSV, XLSX, XLS</small>
          </div>

          <div v-if="fileName" class="file-chip">
            Selected: <strong>{{ fileName }}</strong>
          </div>

          <div v-if="parseError" class="error-box">{{ parseError }}</div>
        </div>

        <div v-if="workbookReady" class="field-grid two">
          <div class="field-block" v-if="sheetNames.length > 1">
            <label class="label">Sheet</label>
            <select v-model="selectedSheetName" class="input" @change="rebuildRows">
              <option v-for="s in sheetNames" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>

          <div class="field-block">
            <label class="label">Header row</label>
            <select v-model.number="headerRowIndex" class="input" @change="rebuildRows">
              <option v-for="n in headerRowOptions" :key="n" :value="n - 1">
                Row {{ n }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="previewHeaders.length" class="preview-wrap">
          <div class="preview-title">Detected columns</div>
          <div class="header-pills">
            <span v-for="h in previewHeaders" :key="h" class="header-pill">{{ h }}</span>
          </div>
        </div>

        <div v-if="previewRows.length" class="preview-wrap">
          <div class="preview-title">File preview</div>
          <div class="table-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th v-for="h in previewHeaders" :key="h">{{ h }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in previewRows" :key="ri">
                  <td v-for="h in previewHeaders" :key="h">{{ row[h] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-option" @click="$emit('close')">Cancel</button>
          <button class="btn-primary" :disabled="!workbookReady || !previewHeaders.length" @click="goToStep2">
            Next
          </button>
        </div>
      </div>

      <!-- STEP 2 -->
      <div v-else-if="step === 2" class="import-step">
        <div class="section-box">
          <div class="section-title">Core mapping</div>

          <div class="field-grid two">
            <div class="field-block">
              <label class="label">Field label column</label>
              <select v-model="mapping.labelColumn" class="input">
                <option value="">Select column…</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Field name column</label>
              <select v-model="mapping.nameColumn" class="input">
                <option value="">Auto-generate from label</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Type source</label>
              <select v-model="mapping.typeMode" class="input">
                <option value="single">Use one type for all rows</option>
                <option value="column">Use a column from file</option>
              </select>
            </div>

            <div class="field-block" v-if="mapping.typeMode === 'single'">
              <label class="label">Default type</label>
              <select v-model="mapping.globalType" class="input">
                <option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>

            <div class="field-block" v-else>
              <label class="label">Type column</label>
              <select v-model="mapping.typeColumn" class="input">
                <option value="">Select column…</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="section-box">
          <div class="section-title">Help text mapping</div>

          <div class="field-grid two">
            <div class="field-block">
              <label class="label">Mode</label>
              <select v-model="mapping.helpTextMode" class="input">
                <option value="none">No help text</option>
                <option value="singleColumn">Use one column</option>
                <option value="concat">Concatenate multiple parts</option>
              </select>
            </div>

            <div v-if="mapping.helpTextMode === 'singleColumn'" class="field-block">
              <label class="label">Help text column</label>
              <select v-model="mapping.helpTextColumn" class="input">
                <option value="">Select column…</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>
          </div>

          <div v-if="mapping.helpTextMode === 'concat'" class="concat-builder">
            <div class="concat-toolbar">
              <button class="btn-option small" @click="addConcatPart('column')">+ Column</button>
              <button class="btn-option small" @click="addConcatPart('text')">+ Text</button>
            </div>

            <div v-if="!mapping.helpTextParts.length" class="muted">No parts added yet.</div>

            <div v-for="(part, idx) in mapping.helpTextParts" :key="idx" class="concat-row">
              <select v-model="part.kind" class="input narrow">
                <option value="column">Column</option>
                <option value="text">Text</option>
              </select>

              <select v-if="part.kind === 'column'" v-model="part.value" class="input">
                <option value="">Select column…</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>

              <input
                v-else
                v-model="part.value"
                type="text"
                class="input"
                placeholder='Example: " - " or "Reference High: "'
              />

              <button class="icon-button danger" @click="removeConcatPart(idx)">✕</button>
            </div>

            <small class="help">
              Example: SwissLab Code + " - " + Unit + " - " + Result text + " - " + Reference Low + " - Reference High: " + Reference High
            </small>
          </div>
        </div>

        <div class="section-box">
          <div class="section-title">Constraint column mapping</div>

          <div class="field-grid three">
            <div class="field-block"><label class="label">Placeholder</label>
              <select v-model="mapping.placeholderColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Default value</label>
              <select v-model="mapping.defaultValueColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Required</label>
              <select v-model="mapping.requiredColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Readonly</label>
              <select v-model="mapping.readonlyColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Min length</label>
              <select v-model="mapping.minLengthColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Max length</label>
              <select v-model="mapping.maxLengthColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Pattern</label>
              <select v-model="mapping.patternColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Transform</label>
              <select v-model="mapping.transformColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Min</label>
              <select v-model="mapping.minColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Max</label>
              <select v-model="mapping.maxColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Step</label>
              <select v-model="mapping.stepColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Integer only</label>
              <select v-model="mapping.integerOnlyColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Min digits</label>
              <select v-model="mapping.minDigitsColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Max digits</label>
              <select v-model="mapping.maxDigitsColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Min time</label>
              <select v-model="mapping.minTimeColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Max time</label>
              <select v-model="mapping.maxTimeColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Hour cycle</label>
              <select v-model="mapping.hourCycleColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Date format</label>
              <select v-model="mapping.dateFormatColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Min date</label>
              <select v-model="mapping.minDateColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Max date</label>
              <select v-model="mapping.maxDateColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Allow multiple</label>
              <select v-model="mapping.allowMultipleColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Options</label>
              <select v-model="mapping.optionsColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Rows</label>
              <select v-model="mapping.rowsColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Slider mode</label>
              <select v-model="mapping.sliderModeColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Percent</label>
              <select v-model="mapping.percentColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Left label</label>
              <select v-model="mapping.leftLabelColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Right label</label>
              <select v-model="mapping.rightLabelColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Allowed formats</label>
              <select v-model="mapping.allowedFormatsColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Max size MB</label>
              <select v-model="mapping.maxSizeMBColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Storage preference</label>
              <select v-model="mapping.storagePreferenceColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Allow multiple files</label>
              <select v-model="mapping.allowMultipleFilesColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>

            <div class="field-block"><label class="label">Modalities</label>
              <select v-model="mapping.modalitiesColumn" class="input">
                <option value="">None</option>
                <option v-for="h in previewHeaders" :key="h" :value="h">{{ h }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-option" @click="step = 1">Back</button>
          <button class="btn-primary" :disabled="!mapping.labelColumn" @click="goToStep3">
            Next
          </button>
        </div>
      </div>

      <!-- STEP 3 -->
      <div v-else-if="step === 3" class="import-step">
        <div class="section-box">
          <div class="section-title">Global defaults</div>

          <div class="field-grid three">
            <div class="field-block">
              <label class="label">Required</label>
              <select v-model="defaults.required" class="input">
                <option :value="false">No</option>
                <option :value="true">Yes</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Readonly</label>
              <select v-model="defaults.readonly" class="input">
                <option :value="false">No</option>
                <option :value="true">Yes</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Date format</label>
              <select v-model="defaults.dateFormat" class="input">
                <option value="dd.MM.yyyy">dd.MM.yyyy</option>
                <option value="MM-dd-yyyy">MM-dd-yyyy</option>
                <option value="dd-MM-yyyy">dd-MM-yyyy</option>
                <option value="yyyy-MM-dd">yyyy-MM-dd</option>
                <option value="MM/yyyy">MM/yyyy</option>
                <option value="MM-yyyy">MM-yyyy</option>
                <option value="yyyy/MM">yyyy/MM</option>
                <option value="yyyy-MM">yyyy-MM</option>
                <option value="yyyy">yyyy</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Hour cycle</label>
              <select v-model="defaults.hourCycle" class="input">
                <option value="24">24</option>
                <option value="12">12</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Transform</label>
              <select v-model="defaults.transform" class="input">
                <option value="none">None</option>
                <option value="uppercase">Uppercase</option>
                <option value="lowercase">Lowercase</option>
                <option value="capitalize">Capitalize</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Textarea rows</label>
              <input v-model.number="defaults.rows" type="number" class="input" min="1" />
            </div>

            <div class="field-block">
              <label class="label">Number min</label>
              <input v-model="defaults.min" type="text" class="input" />
            </div>

            <div class="field-block">
              <label class="label">Number max</label>
              <input v-model="defaults.max" type="text" class="input" />
            </div>

            <div class="field-block">
              <label class="label">Number step</label>
              <input v-model="defaults.step" type="text" class="input" />
            </div>

            <div class="field-block">
              <label class="label">Slider mode</label>
              <select v-model="defaults.sliderMode" class="input">
                <option value="slider">Slider</option>
                <option value="linear">Likert scale</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Slider percent</label>
              <select v-model="defaults.percent" class="input">
                <option :value="false">No</option>
                <option :value="true">Yes</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Allow multiple choice</label>
              <select v-model="defaults.allowMultiple" class="input">
                <option :value="false">No</option>
                <option :value="true">Yes</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Storage preference</label>
              <select v-model="defaults.storagePreference" class="input">
                <option value="local">local</option>
                <option value="url">url</option>
              </select>
            </div>

            <div class="field-block">
              <label class="label">Allow multiple files</label>
              <select v-model="defaults.allowMultipleFiles" class="input">
                <option :value="true">Yes</option>
                <option :value="false">No</option>
              </select>
            </div>
          </div>
        </div>

        <div class="section-box">
          <div class="section-title">Preview and adjust</div>

          <div class="table-wrap large">
            <table class="preview-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Label</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Help text</th>
                  <th>Default</th>
                  <th>Required</th>
                  <th>Readonly</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in importRows" :key="idx">
                  <td>{{ idx + 1 }}</td>
                  <td><input v-model="row.label" class="input cell" type="text" /></td>
                  <td><input v-model="row.name" class="input cell" type="text" /></td>
                  <td>
                    <select v-model="row.type" class="input cell">
                      <option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
                    </select>
                  </td>
                  <td><input v-model="row.helpText" class="input cell" type="text" /></td>
                  <td><input v-model="row.defaultValue" class="input cell" type="text" /></td>
                  <td>
                    <select v-model="row.required" class="input cell">
                      <option :value="false">No</option>
                      <option :value="true">Yes</option>
                    </select>
                  </td>
                  <td>
                    <select v-model="row.readonly" class="input cell">
                      <option :value="false">No</option>
                      <option :value="true">Yes</option>
                    </select>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-option" @click="step = 2">Back</button>
          <button class="btn-primary" :disabled="!canImport" @click="confirmImport">
            Import Fields
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ImportCsvTemplateDialog",
  emits: ["close", "import-fields"],
  data() {
    return {
      step: 1,
      fileName: "",
      parseError: "",
      workbookReady: false,
      workbook: null,
      sheetNames: [],
      selectedSheetName: "",
      headerRowIndex: 0,
      rawSheetRows: [],
      previewHeaders: [],
      previewRows: [],
      importRows: [],

      typeOptions: [
        { value: "text", label: "Text" },
        { value: "textarea", label: "Textarea" },
        { value: "number", label: "Number" },
        { value: "date", label: "Date" },
        { value: "time", label: "Time" },
        { value: "select", label: "Select" },
        { value: "radio", label: "Radio" },
        { value: "slider", label: "Slider" },
        { value: "checkbox", label: "Checkbox" },
        { value: "file", label: "File" },
      ],

      mapping: {
        labelColumn: "",
        nameColumn: "",
        typeMode: "single",
        globalType: "text",
        typeColumn: "",

        helpTextMode: "none",
        helpTextColumn: "",
        helpTextParts: [],

        placeholderColumn: "",
        defaultValueColumn: "",
        requiredColumn: "",
        readonlyColumn: "",

        minLengthColumn: "",
        maxLengthColumn: "",
        patternColumn: "",
        transformColumn: "",

        minColumn: "",
        maxColumn: "",
        stepColumn: "",
        integerOnlyColumn: "",
        minDigitsColumn: "",
        maxDigitsColumn: "",

        minTimeColumn: "",
        maxTimeColumn: "",
        hourCycleColumn: "",

        dateFormatColumn: "",
        minDateColumn: "",
        maxDateColumn: "",

        allowMultipleColumn: "",
        optionsColumn: "",
        rowsColumn: "",

        sliderModeColumn: "",
        percentColumn: "",
        leftLabelColumn: "",
        rightLabelColumn: "",

        allowedFormatsColumn: "",
        maxSizeMBColumn: "",
        storagePreferenceColumn: "",
        allowMultipleFilesColumn: "",
        modalitiesColumn: "",
      },

      defaults: {
        required: false,
        readonly: false,
        dateFormat: "dd.MM.yyyy",
        hourCycle: "24",
        transform: "none",
        rows: 4,
        min: "",
        max: "",
        step: "",
        sliderMode: "slider",
        percent: false,
        allowMultiple: false,
        storagePreference: "local",
        allowMultipleFiles: true,
      },
    };
  },

  computed: {
    headerRowOptions() {
      return Array.from({ length: Math.min(this.rawSheetRows.length || 1, 10) }, (_, i) => i + 1);
    },
    canImport() {
      return this.importRows.length > 0 && this.importRows.every(r => String(r.label || "").trim());
    },
  },

  methods: {
    async onFilePicked(e) {
      const file = e?.target?.files?.[0];
      if (!file) return;

      this.resetFileState();
      this.fileName = file.name;

      try {
        const lower = String(file.name || "").toLowerCase();

        if (lower.endsWith(".csv")) {
          const text = await file.text();
          const rows = this.parseCsvText(text);
          this.loadWorkbookLikeData({ CSV: rows });
          return;
        }

        const buf = await file.arrayBuffer();
        const XLSX = await import("xlsx");
        const wb = XLSX.read(buf, { type: "array" });
        const sheetData = {};

        wb.SheetNames.forEach((sheetName) => {
          const ws = wb.Sheets[sheetName];
          sheetData[sheetName] = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });
        });

        this.loadWorkbookLikeData(sheetData);
      } catch (err) {
        console.error(err);
        this.parseError = "Failed to read file. Please check the file format.";
      }
    },

    resetFileState() {
      this.parseError = "";
      this.workbookReady = false;
      this.workbook = null;
      this.sheetNames = [];
      this.selectedSheetName = "";
      this.headerRowIndex = 0;
      this.rawSheetRows = [];
      this.previewHeaders = [];
      this.previewRows = [];
      this.importRows = [];
      this.step = 1;
    },

    loadWorkbookLikeData(workbookObj) {
      this.workbook = workbookObj || {};
      this.sheetNames = Object.keys(this.workbook);
      this.selectedSheetName = this.sheetNames[0] || "";
      this.workbookReady = !!this.selectedSheetName;
      this.rebuildRows();
    },

    rebuildRows() {
      const rows = Array.isArray(this.workbook?.[this.selectedSheetName])
        ? this.workbook[this.selectedSheetName]
        : [];

      this.rawSheetRows = rows;

      if (!rows.length) {
        this.previewHeaders = [];
        this.previewRows = [];
        return;
      }

      const headerRow = rows[this.headerRowIndex] || [];
      const headers = headerRow.map((h, idx) => {
        const val = String(h ?? "").trim();
        return val || `Column ${idx + 1}`;
      });

      const bodyRows = rows.slice(this.headerRowIndex + 1)
        .filter(r => Array.isArray(r) && r.some(cell => String(cell ?? "").trim() !== ""))
        .map(r => {
          const out = {};
          headers.forEach((h, idx) => {
            out[h] = r[idx] ?? "";
          });
          return out;
        });

      this.previewHeaders = headers;
      this.previewRows = bodyRows.slice(0, 5);

      if (!this.mapping.labelColumn && headers.length) {
        const displayMatch = headers.find(h => String(h).trim().toLowerCase() === "display");
        this.mapping.labelColumn = displayMatch || headers[0];
      }

      this.bootstrapSuggestedMappings(headers);
    },

    bootstrapSuggestedMappings(headers) {
      const byName = (name) => headers.find(h => String(h).trim().toLowerCase() === name.toLowerCase()) || "";

      this.mapping.defaultValueColumn ||= byName("Value");
      this.mapping.minColumn ||= byName("Reference Low");
      this.mapping.maxColumn ||= byName("Reference High");
    },

    goToStep2() {
      this.step = 2;
    },

    goToStep3() {
      this.importRows = this.buildImportRowsFromPreview();
      this.step = 3;
    },

    addConcatPart(kind) {
      this.mapping.helpTextParts.push({ kind, value: "" });
    },

    removeConcatPart(idx) {
      this.mapping.helpTextParts.splice(idx, 1);
    },

    rawDataRows() {
      const rows = Array.isArray(this.workbook?.[this.selectedSheetName])
        ? this.workbook[this.selectedSheetName]
        : [];
      const headers = this.previewHeaders || [];
      return rows.slice(this.headerRowIndex + 1)
        .filter(r => Array.isArray(r) && r.some(cell => String(cell ?? "").trim() !== ""))
        .map(r => {
          const out = {};
          headers.forEach((h, idx) => {
            out[h] = r[idx] ?? "";
          });
          return out;
        });
    },

    buildImportRowsFromPreview() {
      return this.rawDataRows().map((src, idx) => {
        const label = this.cell(src, this.mapping.labelColumn);

        return {
          sourceIndex: idx,
          source: src,
          label,
          name: this.resolveNameForRow(src, idx, label),
          type: this.resolveTypeForRow(src),
          helpText: this.resolveHelpTextForRow(src),
          defaultValue: this.cell(src, this.mapping.defaultValueColumn),

          required: this.resolveBooleanForRow(src, this.mapping.requiredColumn, this.defaults.required),
          readonly: this.resolveBooleanForRow(src, this.mapping.readonlyColumn, this.defaults.readonly),

          placeholder: this.cell(src, this.mapping.placeholderColumn),

          minLength: this.cell(src, this.mapping.minLengthColumn),
          maxLength: this.cell(src, this.mapping.maxLengthColumn),
          pattern: this.cell(src, this.mapping.patternColumn),
          transform: this.resolveTextForRow(src, this.mapping.transformColumn, this.defaults.transform),

          min: this.cell(src, this.mapping.minColumn),
          max: this.cell(src, this.mapping.maxColumn),
          step: this.cell(src, this.mapping.stepColumn),
          integerOnly: this.resolveBooleanForRow(src, this.mapping.integerOnlyColumn, false),
          minDigits: this.cell(src, this.mapping.minDigitsColumn),
          maxDigits: this.cell(src, this.mapping.maxDigitsColumn),

          minTime: this.cell(src, this.mapping.minTimeColumn),
          maxTime: this.cell(src, this.mapping.maxTimeColumn),
          hourCycle: this.resolveTextForRow(src, this.mapping.hourCycleColumn, this.defaults.hourCycle),

          dateFormat: this.resolveTextForRow(src, this.mapping.dateFormatColumn, this.defaults.dateFormat),
          minDate: this.cell(src, this.mapping.minDateColumn),
          maxDate: this.cell(src, this.mapping.maxDateColumn),

          allowMultiple: this.resolveBooleanForRow(src, this.mapping.allowMultipleColumn, this.defaults.allowMultiple),
          optionsRaw: this.cell(src, this.mapping.optionsColumn),
          rows: this.cell(src, this.mapping.rowsColumn),

          sliderMode: this.resolveSliderModeForRow(src),
          percent: this.resolveBooleanForRow(src, this.mapping.percentColumn, this.defaults.percent),
          leftLabel: this.cell(src, this.mapping.leftLabelColumn),
          rightLabel: this.cell(src, this.mapping.rightLabelColumn),

          allowedFormatsRaw: this.cell(src, this.mapping.allowedFormatsColumn),
          maxSizeMB: this.cell(src, this.mapping.maxSizeMBColumn),
          storagePreference: this.resolveStoragePreferenceForRow(src),
          allowMultipleFiles: this.resolveBooleanForRow(src, this.mapping.allowMultipleFilesColumn, this.defaults.allowMultipleFiles),
          modalitiesRaw: this.cell(src, this.mapping.modalitiesColumn),
        };
      }).filter(r => String(r.label || "").trim());
    },

    cell(row, columnName) {
      if (!row || !columnName) return "";
      return row[columnName] ?? "";
    },

    resolveNameForRow(row, idx, label) {
      const explicit = String(this.cell(row, this.mapping.nameColumn) || "").trim();
      if (explicit) return this.slugify(explicit);
      return `${this.slugify(label || `field_${idx + 1}`)}_${idx + 1}`;
    },

    resolveTypeForRow(row) {
      if (this.mapping.typeMode === "single") return this.mapping.globalType || "text";

      const raw = String(this.cell(row, this.mapping.typeColumn) || "").trim().toLowerCase();
      if (!raw) return "text";

      if (["int", "integer", "number", "decimal", "float"].includes(raw)) return "number";
      if (["text", "string", "shorttext"].includes(raw)) return "text";
      if (["textarea", "longtext", "multiline"].includes(raw)) return "textarea";
      if (["date"].includes(raw)) return "date";
      if (["time"].includes(raw)) return "time";
      if (["select", "dropdown"].includes(raw)) return "select";
      if (["radio"].includes(raw)) return "radio";
      if (["slider", "linear", "linearscale", "likert"].includes(raw)) return "slider";
      if (["checkbox", "bool", "boolean"].includes(raw)) return "checkbox";
      if (["file", "upload"].includes(raw)) return "file";

      return "text";
    },

    resolveHelpTextForRow(row) {
      if (this.mapping.helpTextMode === "none") return "";

      if (this.mapping.helpTextMode === "singleColumn") {
        return String(this.cell(row, this.mapping.helpTextColumn) || "").trim();
      }

      return this.mapping.helpTextParts
        .map(part => part.kind === "text" ? String(part.value || "") : String(this.cell(row, part.value) || ""))
        .join("")
        .trim();
    },

    resolveBooleanForRow(row, column, fallback) {
      if (!column) return !!fallback;
      const s = String(this.cell(row, column) ?? "").trim().toLowerCase();
      if (!s) return !!fallback;
      return ["true", "1", "yes", "y", "required", "readonly", "checked"].includes(s);
    },

    resolveTextForRow(row, column, fallback = "") {
      const v = String(this.cell(row, column) ?? "").trim();
      return v || fallback || "";
    },

    resolveSliderModeForRow(row) {
      const raw = String(this.cell(row, this.mapping.sliderModeColumn) || "").trim().toLowerCase();
      if (!raw) return this.defaults.sliderMode || "slider";
      return ["linear", "likert", "linearscale"].includes(raw) ? "linear" : "slider";
    },

    resolveStoragePreferenceForRow(row) {
      const raw = String(this.cell(row, this.mapping.storagePreferenceColumn) || "").trim().toLowerCase();
      if (!raw) return this.defaults.storagePreference || "local";
      return raw === "url" ? "url" : "local";
    },

    confirmImport() {
      const fields = this.importRows.map((row, idx) => this.toCaseEField(row, idx));
      this.$emit("import-fields", fields);
    },

    toCaseEField(row, idx) {
      const type = row.type || "text";
      const constraints = {
        required: !!row.required,
        readonly: !!row.readonly,
        visibilityLogic: {
          action: "show",
          match: "all",
          rules: [],
        },
      };

      if (row.helpText) constraints.helpText = row.helpText;

      if (type === "text" || type === "textarea") {
        if (row.placeholder) constraints.placeholder = row.placeholder;
        if (this.isNumberLike(row.minLength)) constraints.minLength = Number(row.minLength);
        if (this.isNumberLike(row.maxLength)) constraints.maxLength = Number(row.maxLength);
        if (String(row.pattern || "").trim()) constraints.pattern = String(row.pattern).trim();
        if (["none", "uppercase", "lowercase", "capitalize"].includes(String(row.transform || ""))) {
          constraints.transform = row.transform;
        }
      }

      if (type === "number") {
        if (this.isNumberLike(row.min)) constraints.min = Number(row.min);
        else if (this.isNumberLike(this.defaults.min)) constraints.min = Number(this.defaults.min);

        if (this.isNumberLike(row.max)) constraints.max = Number(row.max);
        else if (this.isNumberLike(this.defaults.max)) constraints.max = Number(this.defaults.max);

        if (this.isNumberLike(row.step)) constraints.step = Number(row.step);
        else if (this.isNumberLike(this.defaults.step)) constraints.step = Number(this.defaults.step);

        if (row.integerOnly) constraints.integerOnly = true;
        if (this.isNumberLike(row.minDigits)) constraints.minDigits = Number(row.minDigits);
        if (this.isNumberLike(row.maxDigits)) constraints.maxDigits = Number(row.maxDigits);
      }

      if (type === "date") {
        constraints.dateFormat = row.dateFormat || this.defaults.dateFormat || "dd.MM.yyyy";
        if (String(row.minDate || "").trim()) constraints.minDate = String(row.minDate).trim();
        if (String(row.maxDate || "").trim()) constraints.maxDate = String(row.maxDate).trim();
      }

      if (type === "time") {
        constraints.hourCycle = row.hourCycle || this.defaults.hourCycle || "24";
        if (String(row.minTime || "").trim()) constraints.minTime = String(row.minTime).trim();
        if (String(row.maxTime || "").trim()) constraints.maxTime = String(row.maxTime).trim();
      }

      if (type === "textarea") {
        const rows = this.toNumber(row.rows);
        if (Number.isFinite(rows)) {
          // kept on field as builder already uses field.rows
        }
      }

      if (type === "select" || type === "radio") {
        const options = this.parseOptions(row.optionsRaw);
        if (type === "radio") {
          constraints.allowMultiple = !!row.allowMultiple;
        }
        if (!options.length) {
          // safe fallback
        }
      }

      if (type === "slider") {
        constraints.mode = row.sliderMode || "slider";
        constraints.percent = !!row.percent;

        if (constraints.mode === "linear") {
          constraints.min = this.isNumberLike(row.min) ? Number(row.min) : 1;
          constraints.max = this.isNumberLike(row.max) ? Number(row.max) : 5;
          constraints.leftLabel = String(row.leftLabel || "").trim();
          constraints.rightLabel = String(row.rightLabel || "").trim();
        } else {
          constraints.min = this.isNumberLike(row.min) ? Number(row.min) : (constraints.percent ? 1 : 1);
          constraints.max = this.isNumberLike(row.max) ? Number(row.max) : (constraints.percent ? 100 : 5);
          constraints.step = this.isNumberLike(row.step) ? Number(row.step) : 1;
          constraints.marks = [];
        }
      }

      if (type === "file") {
        const allowedFormats = this.parseOptions(row.allowedFormatsRaw);
        if (allowedFormats.length) constraints.allowedFormats = allowedFormats;
        if (this.isNumberLike(row.maxSizeMB)) constraints.maxSizeMB = Number(row.maxSizeMB);
        constraints.storagePreference = row.storagePreference || "local";
        constraints.allowMultipleFiles = row.allowMultipleFiles !== false;
        constraints.modalities = this.parseOptions(row.modalitiesRaw).length
          ? this.parseOptions(row.modalitiesRaw)
          : [String(row.label || row.name || `file_${idx + 1}`).trim()];
      }

      const field = {
        _id: this.uuidForImport(),
        name: this.slugify(row.name || `field_${idx + 1}`),
        label: String(row.label || "").trim(),
        type,
        value: this.defaultValueForType(type, row.defaultValue, row.allowMultiple),
        placeholder: row.placeholder || "",
        constraints,
      };

      if (type === "textarea") {
        const rows = this.toNumber(row.rows);
        field.rows = Number.isFinite(rows) ? rows : Number(this.defaults.rows || 4);
      }

      if (type === "select" || type === "radio") {
        const options = this.parseOptions(row.optionsRaw);
        field.options = options.length ? options : ["Option 1"];
      }

      if (type === "checkbox") {
        field.value = this.toBoolean(row.defaultValue);
      }

      if (type === "file") {
        field.value = null;
      }

      return field;
    },

    defaultValueForType(type, raw, allowMultiple = false) {
      if (type === "number") {
        const n = this.toNumber(raw);
        return Number.isFinite(n) ? n : "";
      }
      if (type === "checkbox") {
        return this.toBoolean(raw);
      }
      if (type === "slider") {
        const n = this.toNumber(raw);
        return Number.isFinite(n) ? n : null;
      }
      if (type === "radio" && allowMultiple) {
        return this.parseOptions(raw);
      }
      if (type === "file") return null;
      return raw ?? "";
    },

    parseOptions(raw) {
      const txt = String(raw || "").trim();
      if (!txt) return [];
      return txt
        .split(/[,;|]/g)
        .map(v => String(v || "").trim())
        .filter(Boolean);
    },

    toNumber(v) {
      if (v === "" || v == null) return NaN;
      const n = Number(v);
      return Number.isFinite(n) ? n : NaN;
    },

    isNumberLike(v) {
      return v !== "" && v != null && Number.isFinite(Number(v));
    },

    toBoolean(v) {
      const s = String(v ?? "").trim().toLowerCase();
      return ["true", "1", "yes", "y", "checked"].includes(s);
    },

    slugify(s) {
      return String(s || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
    },

    uuidForImport() {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
      return `import_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    },

    parseCsvText(text) {
      const rows = [];
      let row = [];
      let value = "";
      let inQuotes = false;

      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        const next = text[i + 1];

        if (ch === '"') {
          if (inQuotes && next === '"') {
            value += '"';
            i++;
          } else {
            inQuotes = !inQuotes;
          }
        } else if (ch === "," && !inQuotes) {
          row.push(value);
          value = "";
        } else if ((ch === "\n" || ch === "\r") && !inQuotes) {
          if (ch === "\r" && next === "\n") i++;
          row.push(value);
          rows.push(row);
          row = [];
          value = "";
        } else {
          value += ch;
        }
      }

      if (value.length || row.length) {
        row.push(value);
        rows.push(row);
      }

      return rows;
    },
  },
};
</script>

<style scoped>
.import-csv-modal {
  width: min(1320px, 96vw);
  max-height: 92vh;
  overflow-y: auto;
}
.import-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.import-step {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field-grid {
  display: grid;
  gap: 12px;
}
.field-grid.single { grid-template-columns: 1fr; }
.field-grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.field-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.field-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label {
  font-size: 12px;
  font-weight: 700;
  color: #4b5563;
  text-transform: uppercase;
}
.input {
  width: 100%;
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-sizing: border-box;
}
.input.cell {
  min-height: 34px;
  padding: 6px 8px;
  font-size: 13px;
}
.input.narrow {
  max-width: 140px;
}
.help {
  color: #6b7280;
  font-size: 12px;
}
.section-box {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  background: #fafafa;
}
.section-title {
  font-weight: 700;
  margin-bottom: 10px;
}
.preview-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.preview-title {
  font-weight: 700;
}
.header-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.header-pill,
.file-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 13px;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: white;
}
.table-wrap.large {
  max-height: 420px;
}
.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.preview-table th,
.preview-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: top;
}
.preview-table th {
  background: #f8fafc;
  font-weight: 700;
}
.concat-builder {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.concat-toolbar {
  display: flex;
  gap: 8px;
}
.concat-row {
  display: grid;
  grid-template-columns: 140px 1fr auto;
  gap: 8px;
  align-items: center;
}
.error-box {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px;
  border-radius: 8px;
}
.muted {
  color: #6b7280;
}
.icon-button {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
}
.icon-button.danger {
  color: #b91c1c;
}
.btn-primary,
.btn-option {
  min-height: 40px;
}
.btn-option.small {
  min-height: 32px;
  padding: 6px 10px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}
@media (max-width: 900px) {
  .field-grid.two,
  .field-grid.three {
    grid-template-columns: 1fr;
  }
  .concat-row {
    grid-template-columns: 1fr;
  }
}
.modal.import-csv-modal {
  background: #ffffff;
  border-radius: 12px;
  padding: 16px;

  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);

  border: 1px solid #e5e7eb;
}
</style>