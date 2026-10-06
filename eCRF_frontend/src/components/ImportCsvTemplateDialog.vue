<template>
  <div class="import-dialog-shell">
    <div class="modal import-csv-modal">
      <header class="import-header">
        <div><h3>Import fields from CSV / Excel</h3><p>Choose the file layout, select the fields, then confirm every field type.</p></div>
        <button class="icon-button" type="button" title="Close" @click="$emit('close')">✕</button>
      </header>
      <nav class="steps"><span :class="stepClass(1)">1. File &amp; layout</span><span :class="stepClass(2)">2. Select fields</span><span :class="stepClass(3)">3. Review types</span></nav>

      <section v-if="step === 1" class="stack">
        <div class="grid two">
          <label class="field"><b>Choose file</b><input type="file" class="input" accept=".csv,.xlsx,.xls" @change="onFilePicked"><small>CSV, XLSX and XLS are supported.</small></label>
          <label v-if="sheetNames.length > 1" class="field"><b>Sheet</b><select v-model="selectedSheetName" class="input" @change="rebuildSheet"><option v-for="name in sheetNames" :key="name">{{ name }}</option></select></label>
          <label v-if="workbookReady" class="field"><b>Header row</b><select v-model.number="headerRowIndex" class="input" @change="rebuildSheet"><option v-for="n in headerRowOptions" :key="n" :value="n - 1">Row {{ n }}</option></select><small>Choose the row containing column headings.</small></label>
        </div>
        <div v-if="fileName" class="file-chip">Selected: <strong>{{ fileName }}</strong></div>
        <div v-if="parseError" class="message error">{{ parseError }}</div>
        <div v-if="workbookReady" class="panel">
          <strong>How are fields arranged?</strong>
          <div class="orientation-grid">
            <label class="orientation" :class="{ selected: orientation === 'columns' }"><input v-model="orientation" type="radio" value="columns" @change="prepareCandidates"><span><b>Fields are columns</b><small>For response/data exports. Each selected column heading becomes a field.</small><em v-if="suggestedOrientation === 'columns'">Recommended</em></span></label>
            <label class="orientation" :class="{ selected: orientation === 'rows' }"><input v-model="orientation" type="radio" value="rows" @change="prepareCandidates"><span><b>Fields are rows</b><small>For definition lists with field-name and optional type columns.</small><em v-if="suggestedOrientation === 'rows'">Recommended</em></span></label>
          </div>
        </div>
        <div v-if="previewColumns.length" class="stack tight"><strong>File preview</strong><div class="table-wrap preview"><table><thead><tr><th v-for="c in previewColumns" :key="c.id">{{ c.displayLabel }}</th></tr></thead><tbody><tr v-for="(row, i) in previewRows" :key="i"><td v-for="c in previewColumns" :key="c.id">{{ displayCell(row[c.index]) }}</td></tr></tbody></table></div><small>Showing up to 5 rows and 12 columns.</small></div>
        <footer class="actions"><button class="btn-option" @click="$emit('close')">Cancel</button><button class="btn-primary" :disabled="!workbookReady || !previewColumns.length" @click="goToSelection">Select fields</button></footer>
      </section>

      <section v-else-if="step === 2" class="stack">
        <div v-if="orientation === 'rows'" class="panel">
          <strong>Definition columns</strong><p>Choose which columns describe each field. Types can be changed on the next step.</p>
          <div class="grid three">
            <label class="field"><b>Field label</b><select v-model.number="rowMapping.labelIndex" class="input" @change="refreshDefinitionCandidates"><option :value="-1">Select column…</option><option v-for="c in allColumns" :key="c.id" :value="c.index">{{ c.displayLabel }}</option></select></label>
            <label class="field"><b>Field name (optional)</b><select v-model.number="rowMapping.nameIndex" class="input" @change="refreshDefinitionCandidates"><option :value="-1">Generate from label</option><option v-for="c in allColumns" :key="c.id" :value="c.index">{{ c.displayLabel }}</option></select></label>
            <label class="field"><b>Field type (optional)</b><select v-model.number="rowMapping.typeIndex" class="input" @change="refreshDefinitionCandidates"><option :value="-1">Choose during review</option><option v-for="c in allColumns" :key="c.id" :value="c.index">{{ c.displayLabel }}</option></select></label>
          </div>
          <details><summary>Optional settings from other columns</summary><div class="grid three optional"><label v-for="item in optionalMappings" :key="item.key" class="field"><b>{{ item.label }}</b><select v-model.number="rowMapping[item.key]" class="input"><option :value="-1">Not imported</option><option v-for="c in allColumns" :key="c.id" :value="c.index">{{ c.displayLabel }}</option></select></label></div></details>
        </div>
        <div class="toolbar"><div><strong>{{ selectedCount }} of {{ candidates.length }} selected</strong><small>{{ orientation === 'columns' ? 'Each selected column becomes one field.' : 'Each selected row becomes one field.' }}</small></div><div class="toolbar-actions"><input v-model="search" type="search" class="input search" placeholder="Search fields"><button class="btn-option small" @click="selectShown(true)">Select shown</button><button class="btn-option small" @click="selectShown(false)">Clear shown</button></div></div>
        <div v-if="orientation === 'rows' && rowMapping.labelIndex < 0" class="message info">Select the field label column to continue.</div>
        <div v-else class="candidate-list"><label v-for="item in filteredCandidates" :key="item.id" class="candidate"><input v-model="item.selected" type="checkbox"><span><b>{{ candidateTitle(item) }}</b><small>{{ candidateSubtitle(item) }}</small></span><em>{{ typeLabel(item.inferredType || normalizeImportedType(item.rawType)) }}</em></label><div v-if="!filteredCandidates.length" class="empty">No matching fields.</div></div>
        <footer class="actions"><button class="btn-option" @click="step = 1">Back</button><button class="btn-primary" :disabled="!canReview" @click="goToReview">Review selected fields</button></footer>
      </section>

      <section v-else class="stack">
        <div class="review-head"><div><strong>{{ importRows.length }} fields ready to review</strong><small>Source values are used only for suggestions; participant records are not imported.</small></div><div v-if="validationMessage" class="message error">{{ validationMessage }}</div></div>
        <div class="table-wrap review"><table><thead><tr><th>#</th><th>Field label</th><th>Field name</th><th>Type</th><th>Examples / choice options</th><th></th></tr></thead><tbody><tr v-for="(row, i) in importRows" :key="row.sourceId"><td>{{ i + 1 }}</td><td><input v-model="row.label" class="input cell label-cell" @input="validateReview"></td><td><input v-model="row.name" class="input cell name-cell" @input="validateReview"></td><td><select v-model="row.type" class="input cell type-cell"><option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option></select></td><td><input v-if="['select','radio'].includes(row.type)" v-model="row.optionsRaw" class="input cell options-cell" placeholder="Option 1 | Option 2"><span v-else class="samples">{{ row.sampleText || 'No example values' }}</span></td><td><button class="icon-button danger" title="Remove field" @click="removeReviewRow(i)">✕</button></td></tr></tbody></table></div>
        <small>Choice options can be separated with |, comma or semicolon. Labels and letter case are preserved.</small>
        <footer class="actions"><button class="btn-option" @click="step = 2">Back</button><button class="btn-primary" :disabled="!canImport" @click="confirmImport">Import {{ importRows.length }} fields</button></footer>
      </section>
    </div>
  </div>
</template>

<script>
import Papa from "papaparse";
import { analyzeColumnFields, analyzeDefinitionRows, detectOrientation, distinctValues, makeColumns, normalizeType, slugifyFieldName, suggestDefinitionMappings, uniqueFieldNames } from "@/utils/templateFieldImport";

export default {
  name: "ImportCsvTemplateDialog",
  emits: ["close", "import-fields"],
  data() {
    return {
      step: 1, fileName: "", parseError: "", workbookReady: false, workbook: {}, sheetNames: [], selectedSheetName: "", headerRowIndex: 0,
      orientation: "columns", suggestedOrientation: "columns", rawSheetRows: [], allColumns: [], previewColumns: [], previewRows: [], candidates: [], search: "", importRows: [], validationMessage: "",
      rowMapping: this.emptyRowMapping(),
      typeOptions: [{value:"text",label:"Text"},{value:"textarea",label:"Textarea"},{value:"number",label:"Number"},{value:"date",label:"Date"},{value:"time",label:"Time"},{value:"select",label:"Dropdown Select"},{value:"radio",label:"Radio Group"},{value:"slider",label:"Slider / Likert"},{value:"checkbox",label:"Checkbox"},{value:"file",label:"File Upload"}],
      optionalMappings: [
        {key:"helpTextIndex",label:"Help text"},{key:"optionsIndex",label:"Choice options"},{key:"defaultValueIndex",label:"Default value"},{key:"requiredIndex",label:"Required"},{key:"readonlyIndex",label:"Readonly"},{key:"placeholderIndex",label:"Placeholder"},
        {key:"minLengthIndex",label:"Minimum length"},{key:"maxLengthIndex",label:"Maximum length"},{key:"patternIndex",label:"Validation pattern"},{key:"transformIndex",label:"Text transform"},
        {key:"minIndex",label:"Minimum"},{key:"maxIndex",label:"Maximum"},{key:"stepIndex",label:"Number step"},{key:"integerOnlyIndex",label:"Integer only"},{key:"minDigitsIndex",label:"Minimum digits"},{key:"maxDigitsIndex",label:"Maximum digits"},
        {key:"minTimeIndex",label:"Minimum time"},{key:"maxTimeIndex",label:"Maximum time"},{key:"hourCycleIndex",label:"Hour cycle"},{key:"dateFormatIndex",label:"Date format"},{key:"minDateIndex",label:"Minimum date"},{key:"maxDateIndex",label:"Maximum date"},
        {key:"allowMultipleIndex",label:"Allow multiple choices"},{key:"rowsIndex",label:"Textarea rows"},{key:"sliderModeIndex",label:"Slider mode"},{key:"percentIndex",label:"Slider percent"},{key:"leftLabelIndex",label:"Left label"},{key:"rightLabelIndex",label:"Right label"},
        {key:"allowedFormatsIndex",label:"Allowed file formats"},{key:"maxSizeMBIndex",label:"Maximum file size (MB)"},{key:"storagePreferenceIndex",label:"File storage"},{key:"allowMultipleFilesIndex",label:"Allow multiple files"},{key:"modalitiesIndex",label:"Modalities"},
      ],
    };
  },
  computed: {
    headerRowOptions() { return Array.from({length: Math.min(this.rawSheetRows.length || 1, 25)}, (_, i) => i + 1); },
    filteredCandidates() { const q = this.search.trim().toLowerCase(); return q ? this.candidates.filter(x => `${this.candidateTitle(x)} ${this.candidateSubtitle(x)}`.toLowerCase().includes(q)) : this.candidates; },
    selectedCount() { return this.candidates.filter(x => x.selected).length; },
    canReview() { return this.selectedCount > 0 && (this.orientation === "columns" || this.rowMapping.labelIndex >= 0); },
    canImport() { return this.importRows.length > 0 && !this.validationMessage; },
  },
  methods: {
    emptyRowMapping() {
      const mapping = {labelIndex:-1,nameIndex:-1,typeIndex:-1};
      ["helpText","options","defaultValue","required","readonly","placeholder","minLength","maxLength","pattern","transform","min","max","step","integerOnly","minDigits","maxDigits","minTime","maxTime","hourCycle","dateFormat","minDate","maxDate","allowMultiple","rows","sliderMode","percent","leftLabel","rightLabel","allowedFormats","maxSizeMB","storagePreference","allowMultipleFiles","modalities"].forEach(key => { mapping[`${key}Index`] = -1; });
      return mapping;
    },
    stepClass(n) { return {active: this.step === n, complete: this.step > n}; },
    async onFilePicked(event) {
      const file = event?.target?.files?.[0]; if (!file) return;
      this.resetFileState(); this.fileName = file.name;
      try {
        if (file.name.toLowerCase().endsWith(".csv")) {
          const result = Papa.parse(await file.text(), {skipEmptyLines:false});
          if (result.errors?.length && !result.data?.length) throw new Error(result.errors[0].message);
          this.loadWorkbookData({CSV: result.data || []}); return;
        }
        const XLSX = await import("xlsx");
        const wb = XLSX.read(await file.arrayBuffer(), {type:"array",cellDates:true}); const sheets = {};
        wb.SheetNames.forEach(name => { sheets[name] = XLSX.utils.sheet_to_json(wb.Sheets[name], {header:1,defval:"",raw:false}); });
        this.loadWorkbookData(sheets);
      } catch (error) { console.error(error); this.parseError = `Could not read this file${error?.message ? `: ${error.message}` : "."}`; }
    },
    resetFileState() { Object.assign(this, {parseError:"",workbookReady:false,workbook:{},sheetNames:[],selectedSheetName:"",headerRowIndex:0,rawSheetRows:[],allColumns:[],previewColumns:[],previewRows:[],candidates:[],importRows:[],step:1}); this.rowMapping = this.emptyRowMapping(); },
    loadWorkbookData(workbook) { this.workbook = workbook || {}; this.sheetNames = Object.keys(this.workbook); this.selectedSheetName = this.sheetNames[0] || ""; this.workbookReady = !!this.selectedSheetName; this.rebuildSheet(); },
    rebuildSheet() {
      this.rawSheetRows = Array.isArray(this.workbook?.[this.selectedSheetName]) ? this.workbook[this.selectedSheetName] : [];
      if (this.headerRowIndex >= this.rawSheetRows.length) this.headerRowIndex = 0;
      this.allColumns = makeColumns(this.rawSheetRows[this.headerRowIndex] || []); this.previewColumns = this.allColumns.slice(0, 12);
      this.previewRows = this.rawSheetRows.slice(this.headerRowIndex + 1).filter(row => row.some(v => String(v ?? "").trim())).slice(0, 5);
      this.suggestedOrientation = detectOrientation(this.rawSheetRows, this.headerRowIndex); this.orientation = this.suggestedOrientation;
      this.rowMapping = {...this.emptyRowMapping(), ...suggestDefinitionMappings(this.allColumns)}; this.prepareCandidates();
    },
    prepareCandidates() { this.search = ""; this.candidates = this.orientation === "columns" ? analyzeColumnFields(this.rawSheetRows, this.headerRowIndex) : []; if (this.orientation === "rows") this.refreshDefinitionCandidates(); },
    refreshDefinitionCandidates() { this.candidates = analyzeDefinitionRows(this.rawSheetRows, this.headerRowIndex, this.rowMapping.labelIndex, this.rowMapping.typeIndex, this.rowMapping.nameIndex); },
    goToSelection() { this.prepareCandidates(); this.step = 2; },
    selectShown(value) { this.filteredCandidates.forEach(x => { x.selected = value; }); },
    candidateTitle(x) { return this.orientation === "columns" ? x.displayLabel : (x.label || `Row ${x.rowIndex + 1}`); },
    candidateSubtitle(x) { return this.orientation === "columns" ? `${x.nonBlankCount} non-empty value(s) — ${x.samples.length ? x.samples.join(" · ") : "No data"}` : (x.rawType ? `Type in file: ${x.rawType}` : `Spreadsheet row ${x.rowIndex + 1}`); },
    normalizeImportedType(value) { return normalizeType(value, "text"); },
    typeLabel(type) { return this.typeOptions.find(x => x.value === type)?.label || "Text"; },
    goToReview() {
      const selected = this.candidates.filter(x => x.selected);
      this.importRows = this.orientation === "columns" ? this.buildColumnRows(selected) : this.buildDefinitionRows(selected);
      const names = uniqueFieldNames(this.importRows); this.importRows.forEach((row, i) => { row.name = names[i]; }); this.validateReview(); this.step = 3;
    },
    baseRow(id, label, name, type) { return {sourceId:id,label,name,type,sampleText:"",optionsRaw:"",helpText:"",defaultValue:"",required:false,readonly:false,placeholder:"",min:"",max:"",step:"",rows:""}; },
    buildColumnRows(selected) { return selected.map(x => ({...this.baseRow(x.id,x.label,slugifyFieldName(x.label),x.inferredType),sampleText:x.samples.join(" · "),optionsRaw:x.inferredType === "select" ? x.distinct.join(" | ") : ""})); },
    buildDefinitionRows(selected) {
      return selected.filter(x => x.label).map(x => {
        const get = key => this.rowMapping[`${key}Index`] >= 0 ? x.values[this.rowMapping[`${key}Index`]] ?? "" : "";
        const row = {...this.baseRow(x.id,x.label,x.name || slugifyFieldName(x.label),normalizeType(x.rawType,"text")),sampleText:x.rawType ? `Type in file: ${x.rawType}` : ""};
        ["helpText","defaultValue","placeholder","minLength","maxLength","pattern","transform","min","max","step","minDigits","maxDigits","minTime","maxTime","hourCycle","dateFormat","minDate","maxDate","rows","sliderMode","leftLabel","rightLabel","maxSizeMB","storagePreference"].forEach(key => { row[key] = get(key); });
        ["required","readonly","integerOnly","allowMultiple","percent","allowMultipleFiles"].forEach(key => { row[key] = this.toBoolean(get(key)); });
        if (this.rowMapping.allowMultipleFilesIndex < 0) row.allowMultipleFiles = true;
        ["options","allowedFormats","modalities"].forEach(key => { row[`${key}Raw`] = String(get(key)); });
        return row;
      });
    },
    validateReview() {
      const missing = this.importRows.findIndex(x => !String(x.label || "").trim()); if (missing >= 0) { this.validationMessage = `Field ${missing + 1} needs a label.`; return; }
      const names = this.importRows.map(x => slugifyFieldName(x.name)); const duplicate = names.find((x,i) => names.indexOf(x) !== i); this.validationMessage = duplicate ? `Field name “${duplicate}” is used more than once.` : "";
    },
    removeReviewRow(i) { this.importRows.splice(i,1); this.validateReview(); },
    confirmImport() { this.validateReview(); if (this.canImport) this.$emit("import-fields", this.importRows.map((row,i) => this.toField(row,i))); },
    toField(row, i) {
      const type = row.type || "text"; const constraints = {required:!!row.required,readonly:!!row.readonly,visibilityLogic:{action:"show",match:"all",rules:[]}};
      if (row.helpText) constraints.helpText = String(row.helpText); if (row.placeholder) constraints.placeholder = String(row.placeholder);
      if (["text","textarea"].includes(type)) {
        if (this.numberLike(row.minLength)) constraints.minLength=Number(row.minLength); if (this.numberLike(row.maxLength)) constraints.maxLength=Number(row.maxLength);
        if (row.pattern) constraints.pattern=String(row.pattern); if (["none","uppercase","lowercase","capitalize"].includes(String(row.transform))) constraints.transform=row.transform;
      }
      if (["number","slider"].includes(type)) { if (this.numberLike(row.min)) constraints.min=Number(row.min); if (this.numberLike(row.max)) constraints.max=Number(row.max); if (this.numberLike(row.step)) constraints.step=Number(row.step); }
      if (type === "number") { if (row.integerOnly) constraints.integerOnly=true; if (this.numberLike(row.minDigits)) constraints.minDigits=Number(row.minDigits); if (this.numberLike(row.maxDigits)) constraints.maxDigits=Number(row.maxDigits); }
      if (type === "date") { constraints.dateFormat=row.dateFormat || "dd.MM.yyyy"; if (row.minDate) constraints.minDate=String(row.minDate); if (row.maxDate) constraints.maxDate=String(row.maxDate); }
      if (type === "time") { constraints.hourCycle=row.hourCycle || "24"; if (row.minTime) constraints.minTime=String(row.minTime); if (row.maxTime) constraints.maxTime=String(row.maxTime); }
      if (type === "radio") constraints.allowMultiple=!!row.allowMultiple;
      if (type === "slider") Object.assign(constraints,{mode:["linear","likert","linearscale"].includes(String(row.sliderMode).toLowerCase()) ? "linear" : "slider",percent:!!row.percent,min:constraints.min ?? 1,max:constraints.max ?? 5,step:constraints.step ?? 1,marks:[]});
      if (constraints.mode === "linear") { constraints.leftLabel=String(row.leftLabel || ""); constraints.rightLabel=String(row.rightLabel || ""); }
      if (type === "file") Object.assign(constraints,{allowedFormats:this.parseOptions(row.allowedFormatsRaw),maxSizeMB:this.numberLike(row.maxSizeMB) ? Number(row.maxSizeMB) : undefined,storagePreference:row.storagePreference === "url" ? "url" : "local",allowMultipleFiles:row.allowMultipleFiles !== false,modalities:this.parseOptions(row.modalitiesRaw).length ? this.parseOptions(row.modalitiesRaw) : [String(row.label || `File ${i+1}`)]});
      const field = {_id:this.uuid(),name:slugifyFieldName(row.name),label:String(row.label).trim(),type,value:this.defaultValue(type,row.defaultValue),placeholder:String(row.placeholder || ""),constraints};
      if (type === "textarea") field.rows=this.numberLike(row.rows) ? Number(row.rows) : 4;
      if (["select","radio"].includes(type)) { const options=this.parseOptions(row.optionsRaw); field.options=options.length ? options : ["Option 1"]; }
      if (type === "file") field.value=null; return field;
    },
    defaultValue(type,value) { if (type === "number") return this.numberLike(value) ? Number(value) : ""; if (type === "checkbox") return this.toBoolean(value); if (type === "slider") return this.numberLike(value) ? Number(value) : null; return type === "file" ? null : (value ?? ""); },
    parseOptions(value) { return distinctValues(String(value || "").split(/[|,;]/).map(x => x.trim()).filter(Boolean)); },
    toBoolean(value) { return ["true","1","yes","y","ja","required","readonly","checked"].includes(String(value ?? "").trim().toLowerCase()); },
    numberLike(value) { return value !== "" && value != null && Number.isFinite(Number(value)); },
    displayCell(value) { const s = value instanceof Date ? value.toLocaleDateString() : String(value ?? ""); return s.length > 100 ? `${s.slice(0,97)}…` : s; },
    uuid() { return typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `import_${Date.now()}_${Math.random().toString(16).slice(2)}`; },
  },
};
</script>

<style scoped>
.import-csv-modal{width:min(1180px,96vw);max-height:92vh;overflow:auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;box-shadow:0 20px 60px #0004}.import-header,.toolbar,.review-head,.actions{display:flex;justify-content:space-between;align-items:center;gap:12px}.import-header{align-items:flex-start}.import-header h3,.import-header p,.panel p{margin:0}.import-header p,.panel p,small{color:#64748b;font-size:12px}.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:18px 0}.steps span{padding:8px;border-radius:8px;background:#f1f5f9;color:#64748b;font-size:12px;font-weight:700;text-align:center}.steps .active{background:#2563eb;color:#fff}.steps .complete{background:#dbeafe;color:#1d4ed8}.stack{display:flex;flex-direction:column;gap:16px}.stack.tight{gap:7px}.grid{display:grid;gap:12px}.grid.two,.orientation-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.field{display:flex;flex-direction:column;gap:6px}.field>b{color:#475569;font-size:12px;text-transform:uppercase}.input{box-sizing:border-box;width:100%;min-height:40px;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;background:#fff}.input:focus{outline:0;border-color:#2563eb;box-shadow:0 0 0 3px #2563eb1f}.file-chip{align-self:flex-start;padding:6px 10px;border:1px solid #bfdbfe;border-radius:999px;background:#eff6ff;color:#1d4ed8;font-size:13px}.panel{padding:14px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc}.orientation-grid{display:grid;gap:12px;margin-top:12px}.orientation{display:flex;gap:10px;padding:14px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;cursor:pointer}.orientation.selected{border-color:#2563eb;box-shadow:0 0 0 2px #2563eb1f}.orientation span,.toolbar>div,.review-head>div{display:flex;flex-direction:column;gap:4px}.orientation em,.candidate em{color:#1d4ed8;font-size:11px;font-style:normal;font-weight:700;text-transform:uppercase}.table-wrap{overflow:auto;border:1px solid #e2e8f0;border-radius:10px}.table-wrap.preview{max-height:250px}.table-wrap.review{max-height:500px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 10px;border-bottom:1px solid #f1f5f9;text-align:left;vertical-align:top}th{position:sticky;top:0;z-index:1;background:#f8fafc;white-space:nowrap}details{margin-top:14px}summary{color:#1d4ed8;cursor:pointer;font-weight:700}.optional{margin-top:12px}.toolbar-actions{display:flex;gap:8px}.search{width:230px}.candidate-list{max-height:420px;overflow:auto;border:1px solid #e2e8f0;border-radius:10px}.candidate{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:12px;padding:11px 12px;border-bottom:1px solid #f1f5f9;cursor:pointer}.candidate:hover{background:#f8fafc}.candidate>span{display:flex;min-width:0;flex-direction:column;gap:3px}.candidate b,.candidate small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.candidate em{padding:4px 8px;border-radius:999px;background:#eef2ff;color:#4338ca;white-space:nowrap}.empty{padding:30px;color:#64748b;text-align:center}.cell{min-height:34px;padding:6px 8px}.label-cell{min-width:240px}.name-cell{min-width:170px}.type-cell{min-width:145px}.options-cell{min-width:240px}.samples{display:inline-block;max-width:300px;color:#64748b}.message{padding:9px 11px;border-radius:8px;font-size:13px}.message.error{border:1px solid #fecaca;background:#fef2f2;color:#b91c1c}.message.info{border:1px solid #bfdbfe;background:#eff6ff;color:#1d4ed8}.icon-button{border:0;background:transparent;cursor:pointer;font-size:16px}.icon-button.danger{color:#b91c1c}.btn-primary,.btn-option{min-height:40px}.btn-option.small{min-height:36px;padding:6px 10px}.actions{justify-content:flex-end}@media(max-width:850px){.grid.two,.grid.three,.orientation-grid{grid-template-columns:1fr}.toolbar,.review-head{align-items:stretch;flex-direction:column}.toolbar-actions{flex-wrap:wrap}.search{width:100%}}
</style>
