<template>
  <div v-if="open" class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog dialog-export" role="dialog" aria-modal="true" aria-labelledby="study-download-title">
      <div class="dialog-header">
        <div>
          <h3 id="study-download-title">Download study</h3>
          <p class="dialog-subtitle">Download the standard BIDS package or choose custom export options.</p>
        </div>
        <button class="btn-minimal icon-only" type="button" aria-label="Close" @click="$emit('close')">×</button>
      </div>

      <div class="dialog-body">
        <div class="mode-grid">
          <label class="mode-card" :class="{ selected: mode === 'bids' }">
            <input v-model="mode" type="radio" value="bids" />
            <span class="mode-icon"><i class="fas fa-database"></i></span>
            <span class="mode-copy">
              <span class="mode-title">BIDS-compliant study</span>
              <span class="mode-description">Analysis-ready data with human-readable field names in a fully structured BIDS package.</span>
              <span class="mode-meta">Latest version · all subjects · template included</span>
            </span>
            <span class="default-pill">Default</span>
          </label>
          <label class="mode-card" :class="{ selected: mode === 'custom' }">
            <input v-model="mode" type="radio" value="custom" />
            <span class="mode-icon secondary"><i class="fas fa-sliders-h"></i></span>
            <span class="mode-copy">
              <span class="mode-title">Custom export</span>
              <span class="mode-description">Choose versions, subjects, groups, visits, files, templates, and audit history.</span>
              <span class="mode-meta">Focused scope · optional files and audit log</span>
            </span>
          </label>
        </div>

        <div v-if="mode === 'bids'" class="package-preview">
          <strong>Included in this package</strong>
          <div class="preview-grid">
            <span><i class="fas fa-check"></i> Dataset metadata</span>
            <span><i class="fas fa-check"></i> Participants table</span>
            <span><i class="fas fa-check"></i> Human-labelled eCRF data</span>
            <span><i class="fas fa-check"></i> Latest study template</span>
            <span><i class="fas fa-check"></i> Subject and study-level files</span>
          </div>
          <label class="subject-folder-option">
            <input v-model="includeSubjectFolders" type="checkbox" />
            <i class="fas fa-folder-open"></i>
            <span><strong>Individual subject folders</strong><small>Place each subject's visit data in its own folder, with uploaded files grouped under modality folders.</small></span>
          </label>
          <p>UUID field keys are replaced by their actual field names in analysis tables. The original template remains in <code>code/</code> for reproducibility.</p>
        </div>

        <template v-else>
          <div class="form-section">
            <div class="section-heading"><span>1</span><div><h4>Study version</h4><small>Select the data and template version to export.</small></div></div>
            <div class="inline-options section-content">
              <label><input v-model="versionMode" type="radio" value="latest" /> Latest (v{{ latestVersion }})</label>
              <label><input v-model="versionMode" type="radio" value="all" /> All versions</label>
              <label><input v-model="versionMode" type="radio" value="specific" /> Specific version</label>
              <select v-if="versionMode === 'specific'" v-model.number="specificVersion" class="form-select">
                <option v-for="version in normalizedVersions" :key="version" :value="version">Version {{ version }}</option>
              </select>
            </div>
          </div>

          <div class="form-section">
            <div class="section-heading"><span>2</span><div><h4>Export scope</h4><small>Download the entire study or a focused subset.</small></div></div>
            <div class="scope-options section-content">
              <label v-for="item in scopes" :key="item.value" :class="{ selected: scope === item.value }">
                <input v-model="scope" type="radio" :value="item.value" />
                <i :class="item.icon"></i>
                <span><strong>{{ item.label }}</strong><small>{{ item.help }}</small></span>
              </label>
            </div>

            <div v-if="scope === 'subjects'" class="selection-box">
              <div class="selection-head"><strong>Select subjects</strong><button class="text-button" type="button" @click="toggleAll('subjects')">{{ selectedSubjects.length === subjects.length ? 'Clear all' : 'Select all' }}</button></div>
              <div class="selection-grid"><label v-for="(subject, index) in subjects" :key="index"><input v-model="selectedSubjects" type="checkbox" :value="index" /> {{ subject.id || `Subject ${index + 1}` }}</label></div>
            </div>
            <div v-if="scope === 'groups'" class="selection-box">
              <div class="selection-head"><strong>Select groups</strong><button class="text-button" type="button" @click="toggleAll('groups')">{{ selectedGroups.length === groups.length ? 'Clear all' : 'Select all' }}</button></div>
              <div class="selection-grid"><label v-for="(group, index) in groups" :key="index"><input v-model="selectedGroups" type="checkbox" :value="index" /> {{ group.name || group.label || `Group ${index + 1}` }}</label></div>
            </div>
            <div v-if="scope === 'visits'" class="selection-box">
              <div class="selection-head"><strong>Select visits</strong><button class="text-button" type="button" @click="toggleAll('visits')">{{ selectedVisits.length === visits.length ? 'Clear all' : 'Select all' }}</button></div>
              <div class="selection-grid"><label v-for="(visit, index) in visits" :key="index"><input v-model="selectedVisits" type="checkbox" :value="index" /> {{ visit.name || visit.label || `Visit ${index + 1}` }}</label></div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-heading"><span>3</span><div><h4>Package contents</h4><small>Choose what the downloaded ZIP should contain.</small></div></div>
            <div class="checkbox-options section-content">
              <label :class="{ disabled: scope === 'audit' }"><input v-model="includeData" type="checkbox" :disabled="scope === 'audit'" /><i class="fas fa-table"></i><span><strong>Analysis data</strong><small>Human-labelled phenotype TSV files</small></span></label>
              <label :class="{ disabled: scope === 'audit' }"><input v-model="includeTemplate" type="checkbox" :disabled="scope === 'audit'" /><i class="fas fa-file-code"></i><span><strong>Study template</strong><small>Versioned schema for reproducibility</small></span></label>
              <label :class="{ disabled: scope === 'audit' }"><input v-model="includeFiles" type="checkbox" :disabled="scope === 'audit'" /><i class="fas fa-paperclip"></i><span><strong>Uploaded files</strong><small>Subject and study-level files</small></span></label>
              <label><input v-model="includeAudit" type="checkbox" :disabled="scope === 'audit'" /><i class="fas fa-history"></i><span><strong>Audit log</strong><small>Study and subject change history</small></span></label>
              <label :class="{ disabled: scope === 'audit' }"><input v-model="includeSubjectFolders" type="checkbox" :disabled="scope === 'audit'" /><i class="fas fa-folder-open"></i><span><strong>Individual subject folders</strong><small>Visit data and files grouped per subject</small></span></label>
            </div>
            <label v-if="includeFiles && scope !== 'audit'" class="field-row">
              <span>Files to include</span>
              <select v-model="fileScope" class="form-select">
                <option value="all">Subject and study-level files</option>
                <option value="subject">Subject files only</option>
                <option value="study">Study-level files only</option>
              </select>
            </label>
          </div>
        </template>
      </div>

      <div class="dialog-actions">
        <div class="download-summary">
          <strong>{{ summaryTitle }}</strong>
          <small>{{ summaryText }}</small>
        </div>
        <button class="btn-minimal" type="button" :disabled="downloading" @click="$emit('close')">Cancel</button>
        <button class="btn-primary" type="button" :disabled="downloading || invalidSelection" @click="submit">
          {{ downloading ? 'Preparing ZIP…' : 'Download ZIP' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "StudyDownloadDialog",
  props: {
    open: { type: Boolean, default: false },
    downloading: { type: Boolean, default: false },
    subjects: { type: Array, default: () => [] },
    groups: { type: Array, default: () => [] },
    visits: { type: Array, default: () => [] },
    versions: { type: Array, default: () => [] },
  },
  emits: ["close", "download"],
  data() {
    return {
      mode: "bids", versionMode: "latest", specificVersion: null, scope: "whole",
      selectedSubjects: [], selectedGroups: [], selectedVisits: [],
      includeData: true, includeTemplate: true, includeFiles: true, includeAudit: false, includeSubjectFolders: true, fileScope: "all",
      scopes: [
        { value: "whole", icon: "fas fa-th-large", label: "Whole study", help: "All subjects and visits" },
        { value: "subjects", icon: "fas fa-user", label: "Subject-wise", help: "Selected subjects" },
        { value: "groups", icon: "fas fa-users", label: "Group-wise", help: "Selected groups" },
        { value: "visits", icon: "fas fa-calendar-alt", label: "Visit-wise", help: "Selected visits" },
        { value: "files", icon: "fas fa-folder-open", label: "Files only", help: "Uploaded files" },
        { value: "audit", icon: "fas fa-history", label: "Audit log only", help: "Change history" },
      ],
    };
  },
  computed: {
    normalizedVersions() { return (this.versions || []).map(v => Number(v.version ?? v)).filter(Number.isFinite).sort((a, b) => a - b); },
    latestVersion() { return this.normalizedVersions[this.normalizedVersions.length - 1] || 1; },
    invalidSelection() {
      return this.mode === "custom" && ((this.scope === "subjects" && !this.selectedSubjects.length) || (this.scope === "groups" && !this.selectedGroups.length) || (this.scope === "visits" && !this.selectedVisits.length));
    },
    summaryTitle() { return this.mode === "bids" ? "BIDS-compliant whole study" : this.scopes.find(item => item.value === this.scope)?.label || "Custom export"; },
    summaryText() {
      if (this.mode === "bids") return `Latest version (v${this.latestVersion}), ${this.subjects.length} subject${this.subjects.length === 1 ? "" : "s"}`;
      return this.versionMode === "all" ? "All study versions" : this.versionMode === "specific" ? `Study version ${this.specificVersion}` : `Latest version (v${this.latestVersion})`;
    },
  },
  watch: {
    open(value) { if (value && !this.specificVersion) this.specificVersion = this.latestVersion; },
    scope(value) {
      if (value === "audit") { this.includeAudit = true; this.includeData = false; this.includeTemplate = false; this.includeFiles = false; }
      if (value === "files") { this.includeFiles = true; this.includeData = false; this.includeTemplate = false; this.includeAudit = false; }
    },
  },
  methods: {
    toggleAll(kind) {
      const map = { subjects: ["selectedSubjects", this.subjects], groups: ["selectedGroups", this.groups], visits: ["selectedVisits", this.visits] };
      const [key, items] = map[kind];
      this[key] = this[key].length === items.length ? [] : items.map((_, index) => index);
    },
    submit() {
      if (this.invalidSelection) return;
      if (this.mode === "bids") {
        this.$emit("download", { versions: "latest", include_data: true, include_template: true, include_files: true, file_scope: "all", include_audit: false, include_subject_folders: this.includeSubjectFolders });
        return;
      }
      const payload = {
        versions: this.versionMode === "specific" ? String(this.specificVersion) : this.versionMode,
        include_data: this.scope === "audit" ? false : this.includeData,
        include_template: this.scope === "audit" ? false : this.includeTemplate,
        include_files: this.scope === "audit" ? false : this.includeFiles,
        file_scope: this.fileScope,
        include_audit: this.scope === "audit" ? true : this.includeAudit,
        audit_only: this.scope === "audit",
        include_subject_folders: this.scope === "audit" ? false : this.includeSubjectFolders,
      };
      if (this.scope === "subjects") payload.subject_indexes = this.selectedSubjects.join(",");
      if (this.scope === "groups") payload.group_indexes = this.selectedGroups.join(",");
      if (this.scope === "visits") payload.visit_indexes = this.selectedVisits.join(",");
      this.$emit("download", payload);
    },
  },
};
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(0, 0, 0, .35); }
.dialog { width: 100%; max-width: 860px; max-height: 88vh; display: flex; flex-direction: column; padding: 16px; overflow: hidden; border-radius: 12px; background: #fff; box-shadow: 0 10px 30px rgba(0, 0, 0, .15); color: #111827; }
.dialog-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 2px 2px 14px; border-bottom: 1px solid #e5e7eb; }
.dialog h3 { margin: 0; font-size: 18px; font-weight: 700; }.dialog-subtitle { margin: 5px 0 0; color: #6b7280; font-size: 13px; }
.dialog-body { overflow-y: auto; padding: 18px 4px 0 2px; }
.mode-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.mode-card { position: relative; display: flex; gap: 13px; min-height: 128px; padding: 16px; border: 1px solid #e0e0e0; border-radius: 10px; background: #fff; cursor: pointer; transition: border-color .2s, background .2s, box-shadow .2s, transform .05s; }
.mode-card:hover { border-color: #b8bcc3; background: #fcfcfc; }.mode-card.selected { border-color: #111827; background: #f9fafb; box-shadow: 0 0 0 2px rgba(17, 24, 39, .06); }.mode-card > input { position: absolute; opacity: 0; pointer-events: none; }
.mode-icon { flex: 0 0 auto; display: grid; place-items: center; width: 42px; height: 42px; border-radius: 9px; background: #111827; color: #fff; font-size: 16px; }.mode-icon.secondary { border: 1px solid #e0e0e0; background: #f3f4f6; color: #374151; }
.mode-copy { display: flex; flex-direction: column; min-width: 0; }.mode-title { font-size: 15px; font-weight: 700; }.mode-description { margin-top: 5px; color: #4b5563; font-size: 12px; line-height: 1.45; }.mode-meta { margin-top: auto; padding-top: 8px; color: #6b7280; font-size: 11px; font-weight: 600; }
.default-pill { position: absolute; top: -9px; right: 11px; padding: 3px 8px; border-radius: 999px; background: #111827; color: #fff; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.package-preview { margin-top: 14px; padding: 14px; border: 1px solid #e0e0e0; border-radius: 10px; background: #fafafa; font-size: 13px; }.preview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; margin-top: 10px; color: #374151; }.preview-grid i { width: 15px; color: #111827; font-size: 10px; }.package-preview p { margin: 12px 0 0; color: #6b7280; font-size: 12px; line-height: 1.5; }
.subject-folder-option { display: grid; grid-template-columns: auto 24px 1fr; gap: 8px; align-items: center; margin-top: 12px; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; cursor: pointer; }.subject-folder-option > i { color: #4b5563; text-align: center; }.subject-folder-option strong, .subject-folder-option small { display: block; }.subject-folder-option small { margin-top: 3px; color: #6b7280; font-size: 11px; line-height: 1.4; }
.form-section { padding: 18px 0; border-bottom: 1px solid #e5e7eb; }.form-section:last-child { border-bottom: 0; }.section-heading { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 12px; }.section-heading > span { display: grid; place-items: center; flex: 0 0 24px; height: 24px; border-radius: 50%; background: #111827; color: #fff; font-size: 11px; font-weight: 700; }.section-heading h4 { margin: 0; font-size: 14px; font-weight: 700; }.section-heading small { display: block; margin-top: 2px; color: #6b7280; font-size: 11px; }.section-content { margin-left: 34px; }
.scope-options strong, .scope-options small, .checkbox-options strong, .checkbox-options small { display: block; }.scope-options small, .checkbox-options small { margin-top: 3px; color: #6b7280; font-size: 11px; }
.inline-options { display: flex; flex-wrap: wrap; gap: 9px; align-items: center; font-size: 13px; }.inline-options > label { padding: 8px 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fff; }
.scope-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }.scope-options > label { display: grid; grid-template-columns: auto 25px 1fr; gap: 7px; align-items: center; min-height: 54px; padding: 9px; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; }.scope-options > label.selected { border-color: #111827; background: #f9fafb; box-shadow: 0 0 0 1px rgba(17, 24, 39, .05); }.scope-options > label > i { color: #4b5563; font-size: 15px; text-align: center; }
.form-select { min-height: 36px; padding: 7px 10px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; color: #111827; font-size: 13px; }.selection-box { margin: 10px 0 0 34px; padding: 12px; max-height: 170px; overflow: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; }.selection-head { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; }.selection-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 13px; }.text-button { padding: 0; border: 0; background: none; color: #374151; text-decoration: underline; cursor: pointer; }.disabled { opacity: .5; }
.checkbox-options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; }.checkbox-options > label { display: grid; grid-template-columns: auto 26px 1fr; gap: 8px; align-items: center; padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fff; cursor: pointer; }.checkbox-options > label > i { color: #4b5563; font-size: 14px; text-align: center; }.field-row { display: flex; align-items: center; gap: 12px; margin: 12px 0 0 34px; color: #4b5563; font-size: 13px; }
.dialog-actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding-top: 14px; border-top: 1px solid #e5e7eb; }.download-summary { display: flex; flex: 1; flex-direction: column; gap: 2px; font-size: 12px; }.download-summary small { color: #6b7280; }.btn-primary { padding: 10px 12px; border: 1px solid transparent; border-radius: 10px; background: #111827; color: #fff; font-size: 14px; cursor: pointer; }.btn-primary[disabled] { opacity: .6; cursor: not-allowed; }.btn-minimal { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; background: none; color: #555; font-size: 14px; cursor: pointer; }.btn-minimal:hover:not([disabled]) { background: #e8e8e8; color: #000; }.btn-minimal.icon-only { padding: 5px 10px; font-size: 20px; line-height: 1; }input { accent-color: #111827; }
@media (max-width: 700px) { .mode-grid, .checkbox-options { grid-template-columns: 1fr; }.scope-options, .selection-grid { grid-template-columns: 1fr 1fr; }.download-summary { display: none; }.section-content, .selection-box, .field-row { margin-left: 0; } }
</style>
