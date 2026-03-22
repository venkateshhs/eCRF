<template>
  <div
    class="merge-page"
    :class="{
      embedded: isEmbedded,
      expanded: isExpanded
    }"
  >
    <!-- Header -->
    <div class="header-row">
      <h2 class="existing-studies-title">Import Data</h2>

      <div class="header-actions">
        <button
          type="button"
          class="btn-minimal icon-btn"
          @click="toggleExpand"
          :title="isExpanded ? 'Shrink' : 'Expand'"
        >
          <i :class="isExpanded ? icons.compress : icons.expand" aria-hidden="true"></i>
        </button>
      </div>
    </div>

    <!-- Source selection -->
    <div class="top-bar card-surface">
      <div class="source-switch">
        <label class="source-pill" :class="{ active: sourceType === 'bundle' }">
          <input type="radio" value="bundle" v-model="sourceType" @change="resetImportStateKeepStudy()" />
          <span>Merge study data from other device</span>
        </label>

        <label class="source-pill" :class="{ active: sourceType === 'subject-import' }">
          <input type="radio" value="subject-import" v-model="sourceType" @change="resetImportStateKeepStudy()" />
          <span>Import Subject data</span>
        </label>
      </div>

      <div class="actions">
        <input
          ref="fileInputBundle"
          type="file"
          accept=".zip"
          class="file-hidden"
          @change="onBundleFile"
        />

        <input
          ref="fileInputSubject"
          type="file"
          accept=".csv,.xlsx,.xls"
          class="file-hidden"
          @change="onSubjectImportFile"
        />

        <button
          v-if="sourceType === 'bundle'"
          class="btn-primary"
          @click="triggerFile"
        >
          Choose study bundle (.zip)
        </button>

        <button
          class="btn-option"
          :disabled="!hasBundle && !subjectImportReady"
          @click="clearBundle"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- Banner -->
    <div
      v-if="parseInfo.message"
      class="parse-banner"
      :class="parseInfo.ok ? 'ok' : 'warn'"
    >
      {{ parseInfo.message }}
    </div>

    <!-- Bundle template mismatch -->
    <div
      v-if="sourceType === 'bundle' && hasBundle && parseInfo.ok && templateMismatch"
      class="parse-banner warn"
    >
      Merge is currently disabled because the template in this file does not
      match the study template. Please align template versions before merging.
    </div>

    <!-- Subject import assumption warning -->
    <div
      v-if="sourceType === 'subject-import' && subjectImportReady && subjectImportAssumptionWarning"
      class="parse-banner warn"
    >
      Subject / visit columns were not found in the uploaded file. This import assumes the data belongs to
      subject <strong>{{ selectedSubjectLabel || "—" }}</strong>
      and visit <strong>{{ selectedVisitLabel || "—" }}</strong>.
    </div>

    <!-- Empty -->
    <div
      v-if="sourceType === 'bundle' && !hasBundle"
      class="empty-state card-surface"
    >
      <p class="empty-title">Merge study data from other device</p>
      <p class="empty-text">
        Select the ZIP file exported from another Case-e device. It should contain
        <code>template_vX.json</code> and <code>data_vX.csv</code>.
      </p>
    </div>

    <div
      v-if="sourceType === 'subject-import' && !subjectImportReady"
      class="empty-state card-surface"
    >
      <p class="empty-title">Import Subject data</p>
      <p class="empty-text">
        Select the target subject and visit first, then upload a CSV or Excel file.
      </p>
    </div>

    <!-- Bundle layout -->
    <div
      v-if="sourceType === 'bundle' && hasBundle"
      class="main-layout"
      :class="{ 'single-column': !showImportDetails || conflicts.length === 0 }"
    >
      <section v-if="showImportDetails" class="card-surface left-column">
        <div class="section-header">
          <h3>Import summary</h3>
        </div>

        <div class="summary-grid">
          <div class="summary-item">
            <div class="label">Import file</div>
            <div class="value">{{ bundleFileName }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Imported version</div>
            <div class="value">v{{ bundleVersion || "—" }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Rows in CSV</div>
            <div class="value">{{ bundleRowCount }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Subjects in file</div>
            <div class="value">{{ bundleSubjectIds.length }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Visits in file</div>
            <div class="value">{{ bundleVisitNames.length }}</div>
          </div>
        </div>

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

          <div v-if="templateMismatch" class="template-warning">
            <div>
              Template structure does not match. Merge is disabled to avoid data loss.
            </div>
            <ul v-if="templateMismatchDetails.length" class="mismatch-list">
              <li v-for="(msg, idx) in templateMismatchDetails" :key="idx">
                {{ msg }}
              </li>
            </ul>
          </div>
        </div>

        <div class="section-header mt">
          <h3>Merge scope</h3>
        </div>

        <div class="scope-card">
          <label class="radio-row">
            <input
              type="radio"
              value="all"
              v-model="scopeMode"
              @change="computeConflicts"
            />
            <span>Merge data for all subjects in the file</span>
          </label>

          <label class="radio-row">
            <input
              type="radio"
              value="subset"
              v-model="scopeMode"
              @change="computeConflicts"
            />
            <span>Merge data only for selected subjects</span>
          </label>

          <div v-if="scopeMode === 'subset'" class="subject-select">
            <p class="helper">
              Select subjects from the file to include in this merge.
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
                  @change="computeConflicts"
                />
                <span>{{ sid }}</span>
              </label>
            </div>
            <button class="btn-minimal sm" @click="selectAllSubjects">Select all</button>
            <button class="btn-minimal sm" @click="clearSelectedSubjects">Clear</button>
          </div>
        </div>

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
              {{ autoMergePossible ? "Yes (no conflicts)" : "No (review needed)" }}
            </div>
          </div>
        </div>
      </section>

      <section class="card-surface right-column" v-if="conflicts.length">
        <div class="section-header">
          <h3>Resolve conflicts</h3>

          <div class="section-actions">
            <button
              type="button"
              class="btn-minimal sm"
              @click="toggleImportDetails"
            >
              {{ showImportDetails ? "Hide import details" : "Show import details" }}
            </button>

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

            <button class="btn-option sm" @click="applyDecisionToAll('incoming')">
              Use incoming for all
            </button>
            <button class="btn-option sm" @click="applyDecisionToAll('existing')">
              Keep existing for all
            </button>
          </div>
        </div>

        <p class="helper">
          For each difference, choose whether to keep the current value or use the value from the imported file.
        </p>

        <div class="conflict-table-wrapper">
          <table class="conflict-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Visit</th>
                <th>Section</th>
                <th>Field</th>
                <th>Existing</th>
                <th>Incoming</th>
                <th>Choice</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in visibleConflicts" :key="c.key">
                <td>{{ c.subjectId }}</td>
                <td>{{ c.visitName }}</td>
                <td>{{ c.sectionTitle }}</td>
                <td>{{ c.fieldLabel }}</td>
                <td>
                  <div class="val-cell">
                    <div class="val-main">{{ displayVal(c.existingValue) }}</div>
                    <div class="val-meta">v{{ c.existingVersion || "—" }}</div>
                  </div>
                </td>
                <td>
                  <div class="val-cell">
                    <div class="val-main">{{ displayVal(c.incomingValue) }}</div>
                    <div class="val-meta">v{{ c.incomingVersion || "—" }}</div>
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
                      Existing
                    </label>

                    <label class="radio-inline">
                      <input
                        type="radio"
                        :name="c.key"
                        value="incoming"
                        :checked="decisions[c.key] === 'incoming'"
                        @change="setDecision(c.key, 'incoming')"
                      />
                      Incoming
                    </label>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else class="card-surface right-column no-conflicts-panel">
        <div class="section-header">
          <h3>No conflicts</h3>
          <div class="section-actions">
            <button
              type="button"
              class="btn-minimal sm"
              @click="toggleImportDetails"
            >
              {{ showImportDetails ? "Hide import details" : "Show import details" }}
            </button>
          </div>
        </div>

        <p class="helper large">
          All incoming values either match existing data or fill empty fields.
          You can go ahead and merge safely.
        </p>

        <div class="summary-grid summary-grid-4">
          <div class="summary-item">
            <div class="label">Entries to import</div>
            <div class="value">{{ importEntryCount }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Subjects in scope</div>
            <div class="value">{{ scopeMode === "all" ? bundleSubjectIds.length : selectedSubjectIds.length }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Conflicts</div>
            <div class="value">0</div>
          </div>
        </div>
      </section>
    </div>

    <!-- Subject import layout -->
    <div
      v-if="sourceType === 'subject-import'"
      class="subject-import-layout"
    >
      <!-- Step 1 -->
      <section class="card-surface subject-step">
        <div class="section-header">
          <h3>1. Select target subject and visit</h3>
        </div>

        <div class="control-grid">
          <div class="control-block">
            <label>Subject</label>
            <select v-model.number="subjectImport.subjectIndex" @change="onSubjectSelectionChange">
              <option
                v-for="(s, idx) in subjects"
                :key="`subj-${idx}`"
                :value="idx"
              >
                {{ s.id }}
              </option>
            </select>
          </div>

          <div class="control-block">
            <label>Visit</label>
            <select v-model.number="subjectImport.visitIndex" @change="rebuildSubjectImportPreview">
              <option
                v-for="(v, idx) in availableVisitsForSelectedSubject"
                :key="`visit-${idx}`"
                :value="v.index"
              >
                {{ v.name }}
              </option>
            </select>
          </div>

          <div class="control-block">
            <label>Group</label>
            <input
              type="text"
              :value="selectedSubjectGroupLabel"
              disabled
            />
          </div>
        </div>
      </section>

      <!-- Step 2 -->
      <section class="card-surface subject-step">
        <div class="section-header">
          <h3>2. Upload file</h3>
        </div>

        <div class="step-upload-actions">
          <button
            type="button"
            class="btn-primary"
            @click="triggerSubjectImportFile"
          >
            Choose data file (.csv, .xlsx, .xls)
          </button>
        </div>

        <p class="helper mt">
          Supported layouts:
        </p>

        <div class="layout-hint-wrap">
          <div class="layout-hint">
            <div class="layout-title">Horizontal</div>
            <code>Header1 | Header2 | Header3</code><br />
            <code>Value1&nbsp;&nbsp;| Value2&nbsp;&nbsp;| Value3</code>
          </div>
          <div class="layout-hint">
            <div class="layout-title">Vertical key-value</div>
            <code>Header1 | Value1</code><br />
            <code>Header2 | Value2</code>
          </div>
        </div>

        <div v-if="subjectImport.fileName" class="file-meta">
          <strong>File:</strong> {{ subjectImport.fileName }}
        </div>
      </section>

      <!-- Step 3 -->
      <section
        v-if="subjectImportReady"
        class="card-surface subject-step"
      >
        <div class="section-header">
          <h3>3. Selected row / data source</h3>
        </div>

        <div class="summary-grid summary-grid-4">
          <div class="summary-item">
            <div class="label">Target subject</div>
            <div class="value">{{ selectedSubjectLabel || "—" }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Target visit</div>
            <div class="value">{{ selectedVisitLabel || "—" }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Detected layout</div>
            <div class="value">{{ subjectImport.detectedLayoutLabel }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Matched source</div>
            <div class="value">{{ subjectImport.matchResultLabel }}</div>
          </div>
        </div>

        <div
          v-if="subjectImportHorizontalHeaders.length"
          class="preview-table-wrap spreadsheet-row-preview"
        >
          <table class="preview-table row-preview-table">
            <thead>
              <tr>
                <th
                  v-for="header in subjectImportHorizontalHeaders"
                  :key="`hdr-${header}`"
                >
                  {{ header }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td
                  v-for="header in subjectImportHorizontalHeaders"
                  :key="`val-${header}`"
                >
                  {{ subjectImportHorizontalValues[header] || "—" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="subjectImportReady && !subjectImportHasMatchedValues"
          class="template-warning mt"
        >
          No uploaded columns could be matched to Case-e fields for the current subject / visit selection.
          Please check the file headers or choose the correct row / layout.
        </div>
      </section>

      <!-- Step 4 -->
      <section
        v-if="subjectImportSummaryRows.length"
        class="card-surface subject-step"
      >
        <div class="section-header">
          <h3>4. Data that will be imported</h3>
        </div>

        <div class="summary-grid summary-grid-4">
          <div class="summary-item">
            <div class="label">Matched fields</div>
            <div class="value">{{ subjectImportSummaryRows.length }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Unmatched file headers</div>
            <div class="value">{{ subjectImport.unmatchedHeaders.length }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Existing entry</div>
            <div class="value">{{ subjectImportExistingEntry ? "Yes" : "No" }}</div>
          </div>
          <div class="summary-item">
            <div class="label">Save mode</div>
            <div class="value">Merge into target visit</div>
          </div>
        </div>

        <div class="preview-table-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Field</th>
                <th>Imported value</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in subjectImportSummaryRows" :key="row.key">
                <td>{{ row.sectionTitle }}</td>
                <td>{{ row.fieldLabel }}</td>
                <td>{{ row.value || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="subjectImport.unmatchedHeaders.length"
          class="template-warning mt"
        >
          The following file headers could not be matched to Case-e fields:
          <strong>{{ subjectImport.unmatchedHeaders.join(", ") }}</strong>
        </div>
      </section>
    </div>

    <!-- Footer -->
    <div
      class="global-commit"
      v-if="
        (sourceType === 'bundle' && hasBundle && importEntryCount > 0) ||
        (sourceType === 'subject-import' && subjectImportHasMatchedValues)
      "
      :class="{ embedded: isEmbedded && !isExpanded }"
    >
      <div class="gc-left" v-if="sourceType === 'bundle'">
        <div class="sel-summary">
          <span>Subjects in scope:</span>
          <strong>
            {{
              scopeMode === "all"
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

      <div class="gc-left" v-else>
        <div class="sel-summary">
          <span>Target:</span>
          <strong>{{ selectedSubjectLabel || "—" }}</strong>
          <span class="dot">·</span>
          <span>Visit:</span>
          <strong>{{ selectedVisitLabel || "—" }}</strong>
          <span class="dot">·</span>
          <span>Fields to import:</span>
          <strong>{{ subjectImportSummaryRows.length }}</strong>
        </div>
      </div>

      <div class="gc-right">
        <button
          v-if="sourceType === 'bundle'"
          class="btn-primary"
          :disabled="!canMerge"
          @click="performMerge"
        >
          {{
            isMerging
              ? "Merging…"
              : (autoMergePossible ? "Merge" : "Merge with decisions")
          }}
        </button>

        <button
          v-else
          class="btn-primary"
          :disabled="!canSaveSubjectImport || isSavingSubjectImport"
          @click="saveSubjectImport"
        >
          {{ isSavingSubjectImport ? "Saving…" : "Save imported data" }}
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
import * as XLSX from "xlsx";
import CustomDialog from "@/components/CustomDialog.vue";
import icons from "@/assets/styles/icons";

export default {
  name: "MergeStudyBundle",
  components: { CustomDialog },
  props: {
    studyId: {
      type: [String, Number],
      default: null,
    },
  },
  data() {
    return {
      icons,

      // layout
      isEmbedded: false,
      isExpanded: false,
      _prevBodyOverflow: "",

      // current study
      study: null,
      meta: {},
      subjects: [],
      visits: [],
      groups: [],
      subjectToGroupIdx: [],

      // template index
      sectionIndex: new Map(),
      sectionTitleByCanon: new Map(),

      // existing entries
      entries: [],
      entriesIndex: new Map(),

      // main mode
      sourceType: "bundle", // bundle | subject-import

      // bundle merge state
      hasBundle: false,
      bundleFileName: "",
      bundleVersion: null,
      bundleRowCount: 0,
      bundleSubjectIds: [],
      bundleVisitNames: [],
      importedSchema: null,
      incomingEntries: {},

      scopeMode: "all",
      selectedSubjectIds: [],

      conflicts: [],
      decisions: {},
      selectedConflictSubject: "ALL",

      parseInfo: { ok: false, message: "" },
      isMerging: false,

      showDialog: false,
      dialogMessage: "",

      showImportDetails: true,

      // subject import state
      subjectImport: {
        subjectIndex: 0,
        visitIndex: 0,
        groupIndex: 0,
        fileName: "",
        workbook: null,
        sheetNames: [],
        selectedSheetName: "",
        rawAoA: [],
        detectedLayout: "", // horizontal | vertical
        matchedPairs: {},   // header -> value from source
        normalizedImportData: {}, // section -> field -> value
        unmatchedHeaders: [],
        matchResultLabel: "—",
        detectedLayoutLabel: "—",
      },
      subjectImportAssumptionWarning: false,
      isSavingSubjectImport: false,
    };
  },

  computed: {
    subjectImportHorizontalHeaders() {
      return Object.keys(this.subjectImport.matchedPairs || {});
    },

    subjectImportHorizontalValues() {
      return this.subjectImport.matchedPairs || {};
    },

    resolvedStudyId() {
      const fromProp = this.studyId;
      const fromRoute = this.$route?.params?.id;
      const raw = fromProp != null ? fromProp : fromRoute;
      const n = Number(raw);
      return Number.isFinite(n) ? n : null;
    },

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
      if (this.importEntryCount <= 0) return false;
      if (this.scopeMode === "subset" && this.selectedSubjectIds.length === 0) return false;
      if (!this.autoMergePossible && this.decidedConflictCount < this.conflicts.length) return false;
      return !this.isMerging;
    },

    currentTemplateSummary() {
      const sd = this.study?.content?.study_data || {};
      const sections = sd.selectedModels || [];
      let fieldCount = 0;
      sections.forEach((sec) => {
        fieldCount += (sec.fields || []).length;
      });
      return { sections: sections.length, fields: fieldCount };
    },

    importedTemplateSummary() {
      const schema = this.importedSchema || {};
      const sections = Array.isArray(schema.selectedModels) ? schema.selectedModels : [];
      let fieldCount = 0;
      sections.forEach((sec) => {
        fieldCount += (sec.fields || []).length;
      });
      return { sections: sections.length, fields: fieldCount };
    },

    templateMismatch() {
      return (
        this.currentTemplateSummary.sections !== this.importedTemplateSummary.sections ||
        this.currentTemplateSummary.fields !== this.importedTemplateSummary.fields
      );
    },

    templateMismatchDetails() {
      const details = [];
      if (!this.importedSchema) return details;

      const current = this.study?.content?.study_data?.selectedModels || [];
      const imported = Array.isArray(this.importedSchema.selectedModels)
        ? this.importedSchema.selectedModels
        : [];

      const currentNames = current
        .map((s) => (s.title || s.name || "").trim())
        .filter(Boolean);
      const importedNames = imported
        .map((s) => (s.title || s.name || "").trim())
        .filter(Boolean);

      if (currentNames.length !== importedNames.length) {
        details.push(`Section count differs (current ${currentNames.length}, import ${importedNames.length}).`);
      }

      const impSet = new Set(importedNames.map((n) => n.toLowerCase()));
      const curSet = new Set(currentNames.map((n) => n.toLowerCase()));

      const missingInImport = currentNames.filter((n) => !impSet.has(n.toLowerCase()));
      const missingInCurrent = importedNames.filter((n) => !curSet.has(n.toLowerCase()));

      if (missingInImport.length) details.push(`Missing in import: ${missingInImport.join(", ")}`);
      if (missingInCurrent.length) details.push(`Only in import: ${missingInCurrent.join(", ")}`);

      current.forEach((sec) => {
        const name = (sec.title || sec.name || "").trim();
        if (!name) return;
        const other = imported.find((s) => (s.title || s.name || "").trim() === name);
        if (!other) return;
        const curCount = (sec.fields || []).length;
        const impCount = (other.fields || []).length;
        if (curCount !== impCount) {
          details.push(`Field count differs for "${name}" (current ${curCount}, import ${impCount}).`);
        }
      });

      return details;
    },

    conflictSubjectOptions() {
      const set = new Set(this.conflicts.map((c) => String(c.subjectId)));
      return Array.from(set).sort();
    },

    visibleConflicts() {
      if (!this.selectedConflictSubject || this.selectedConflictSubject === "ALL") {
        return this.conflicts;
      }
      return this.conflicts.filter((c) => String(c.subjectId) === String(this.selectedConflictSubject));
    },

    selectedSubjectLabel() {
      const s = this.subjects[this.subjectImport.subjectIndex];
      return s?.id ? String(s.id) : "";
    },

    selectedVisitLabel() {
      const v = this.visits[this.subjectImport.visitIndex];
      return v?.name ? String(v.name) : "";
    },

    selectedSubjectGroupLabel() {
      const g = this.groups[this.subjectImport.groupIndex];
      return g?.name ? String(g.name) : "";
    },

    availableVisitsForSelectedSubject() {
      return (this.visits || []).map((v, idx) => ({
        index: idx,
        name: v.name,
      }));
    },

    subjectImportReady() {
      return !!this.subjectImport.fileName;
    },

    subjectImportHasMatchedValues() {
      return this.subjectImportSummaryRows.length > 0;
    },

    subjectImportMatchedPreviewRows() {
      return Object.keys(this.subjectImport.matchedPairs || {}).map((k) => ({
        key: k,
        header: k,
        value: this.subjectImport.matchedPairs[k],
      }));
    },

    subjectImportSummaryRows() {
      const out = [];
      const data = this.subjectImport.normalizedImportData || {};
      Object.keys(data).forEach((sectionTitle) => {
        const sec = data[sectionTitle] || {};
        Object.keys(sec).forEach((fieldName) => {
          const fieldLabel = this.displayLabelForField(sectionTitle, fieldName);
          out.push({
            key: `${sectionTitle}__${fieldName}`,
            sectionTitle,
            fieldName,
            fieldLabel,
            value: sec[fieldName],
          });
        });
      });
      return out;
    },

    canSaveSubjectImport() {
      return this.subjectImportHasMatchedValues && !this.isSavingSubjectImport;
    },

    subjectImportExistingEntry() {
      const key = `${this.subjectImport.subjectIndex}|${this.subjectImport.visitIndex}|${this.subjectImport.groupIndex}`;
      return this.entriesIndex.get(key) || null;
    },
  },

  async created() {
    if (!this.resolvedStudyId) {
      this.showDialogMessage("Invalid study id.");
      return;
    }
    await this.loadStudy();
    await this.loadEntries();
    this.indexEntries();
    this.buildSectionIndex();
    this.initSubjectImportDefaults();
  },

  mounted() {
    try {
      const el = this.$el;
      this.isEmbedded = !!(el && (el.closest(".merge-panel") || el.closest(".study-data-container")));
    } catch (e) {
      this.isEmbedded = false;
    }
  },

  beforeDestroy() {
    this.restoreBodyOverflow();
  },

  methods: {
    triggerSubjectImportFile() {
      this.$refs.fileInputSubject && this.$refs.fileInputSubject.click();
    },

    // ---------- Layout ----------
    toggleExpand() {
      this.isExpanded = !this.isExpanded;
      if (this.isExpanded) this.lockBodyScroll();
      else this.restoreBodyOverflow();
    },

    lockBodyScroll() {
      try {
        this._prevBodyOverflow = document.body.style.overflow || "";
        document.body.style.overflow = "hidden";
      } catch (e) {}
    },

    restoreBodyOverflow() {
      try {
        document.body.style.overflow = this._prevBodyOverflow || "";
      } catch (e) {}
    },

    // ---------- Dialog ----------
    showDialogMessage(msg) {
      this.dialogMessage = msg;
      this.showDialog = true;
    },

    closeDialog() {
      this.showDialog = false;
      this.dialogMessage = "";
    },

    toggleImportDetails() {
      this.showImportDetails = !this.showImportDetails;
    },

    // ---------- Load study ----------
    async loadStudy() {
      try {
        const { data } = await axios.get(`/forms/studies/${this.resolvedStudyId}`, {
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
        console.error("[Import] Failed to load study:", e);
        this.showDialogMessage("Failed to load study.");
      }
    },

    async loadEntries() {
      try {
        const { data } = await axios.get(`/forms/studies/${this.resolvedStudyId}/data_entries`, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        });
        this.entries = Array.isArray(data) ? data : data?.entries || [];
      } catch (e) {
        console.error("[Import] Failed to load entries:", e);
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

    // ---------- Template / field helpers ----------
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

    displayLabelForField(sectionTitle, fieldName) {
      const idx = this.sectionIndex.get(sectionTitle);
      if (!idx) return fieldName;
      return idx.displayByCanon?.[this.canonKey(fieldName)] || fieldName;
    },

    displayFor(sectionTitle, canon) {
      const m = this.sectionIndex.get(sectionTitle);
      return (m?.displayByCanon?.[canon]) || this.prettyFromCanon(canon);
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
        if (Object.keys(row).length > 0) out[secTitle] = row;
      }
      return out;
    },

    mapSectionTitle(raw) {
      const mapped = this.sectionTitleByCanon.get(this.canonKey(raw));
      return mapped || raw;
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

    makeSkipSkeleton() {
      const models = this.study?.content?.study_data?.selectedModels || [];
      return models.map((sec) => (sec.fields || []).map(() => false));
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

    // ---------- Reset ----------
    resetImportStateKeepStudy() {
      // bundle
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

      // subject import
      this.subjectImport = {
        subjectIndex: 0,
        visitIndex: 0,
        groupIndex: 0,
        fileName: "",
        workbook: null,
        sheetNames: [],
        selectedSheetName: "",
        rawAoA: [],
        detectedLayout: "",
        matchedPairs: {},
        normalizedImportData: {},
        unmatchedHeaders: [],
        matchResultLabel: "—",
        detectedLayoutLabel: "—",
      };
      this.subjectImportAssumptionWarning = false;
      this.isSavingSubjectImport = false;

      if (this.$refs.fileInputBundle) this.$refs.fileInputBundle.value = "";
      if (this.$refs.fileInputSubject) this.$refs.fileInputSubject.value = "";

      this.initSubjectImportDefaults();
    },

    clearBundle() {
      this.resetImportStateKeepStudy();
    },

    triggerFile() {
      if (this.sourceType === "bundle") {
        this.$refs.fileInputBundle && this.$refs.fileInputBundle.click();
      } else {
        this.$refs.fileInputSubject && this.$refs.fileInputSubject.click();
      }
    },

    // ---------- Bundle flow ----------
    async onBundleFile(ev) {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      try {
        await this.parseBundle(f);
      } catch (e) {
        console.error("[Bundle] Failed to parse file:", e);
        this.parseInfo = { ok: false, message: "Failed to read bundle file. See console." };
        this.hasBundle = false;
      }
    },

    async parseBundle(file) {
      this.resetImportStateKeepStudy();
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
        this.parseInfo = { ok: false, message: "ZIP file must contain template_vX.json and data_vX.csv." };
        return;
      }

      const templateText = await templateFile.async("string");
      const csvText = await dataFile.async("string");

      let schema = {};
      try {
        const parsed = JSON.parse(templateText);
        schema = parsed?.schema || parsed || {};
      } catch (e) {
        console.error("[Bundle] Failed to parse template JSON:", e);
        this.parseInfo = { ok: false, message: "Failed to parse template JSON." };
        return;
      }

      const csvRes = Papa.parse(csvText, { skipEmptyLines: "greedy" });
      const rows = csvRes.data || [];
      if (rows.length < 3) {
        this.parseInfo = { ok: false, message: "CSV file must have 2 header rows + data." };
        return;
      }

      const tmplMatch = templateFile.name.match(/template_v(\d+)/i);
      const dataMatch = dataFile.name.match(/data_v(\d+)/i);
      const versionFromName =
        (tmplMatch && Number(tmplMatch[1])) ||
        (dataMatch && Number(dataMatch[1])) ||
        Number(schema.version || 1);

      this.bundleVersion = versionFromName || 1;
      this.bundleRowCount = rows.length - 2;
      this.importedSchema = schema;

      const { incomingEntries, subjectIds, visitNames, warnings } =
        this.buildIncomingEntriesFromRows(rows, schema, this.bundleVersion);

      if (warnings.length) {
        this.parseInfo = {
          ok: false,
          message: `File contains unknown subjects/visits: ${warnings.join("; ")}. Merge is disabled to avoid data loss.`,
        };
        return;
      }

      if (!Object.keys(incomingEntries || {}).length) {
        this.parseInfo = {
          ok: false,
          message: "No valid study entries were found in the uploaded bundle. Nothing can be merged.",
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

      this.computeConflicts();
    },
    buildIncomingEntriesFromRows(rows, schema, bundleVersion) {
  const studyData = this.study?.content?.study_data || {};
  const sections = Array.isArray(schema.selectedModels) ? schema.selectedModels : [];
  const incomingEntries = {};
  const subjectIdsSet = new Set();
  const visitNamesSet = new Set();
  const warnings = [];

  const subjMap = {};
  this.subjects.forEach((s, idx) => {
    subjMap[String(s.id)] = idx;
  });

  const visitMap = {};
  this.visits.forEach((v, idx) => {
    visitMap[String(v.name).trim().toLowerCase()] = idx;
  });

  // Build current template field lookup so we only accept fields that actually exist in current Case-e study
  const currentSections = this.study?.content?.study_data?.selectedModels || [];
  const currentFieldMap = new Map();

  currentSections.forEach((section) => {
    const secTitle = section.title || section.name || "";
    if (!secTitle) return;

    const fieldCanonToName = new Map();
    (section.fields || []).forEach((field, idx) => {
      const fieldName =
        field?.name ||
        field?.key ||
        field?.id ||
        field?.label ||
        field?.title ||
        `f${idx}`;

      const candidates = [
        field?.name,
        field?.key,
        field?.id,
        field?.label,
        field?.title,
        this.humanizeCamel(field?.name),
        this.humanizeCamel(field?.label),
      ]
        .filter(Boolean)
        .map((x) => this.canonKey(x));

      candidates.forEach((canon) => {
        fieldCanonToName.set(canon, fieldName);
      });
    });

    currentFieldMap.set(secTitle, fieldCanonToName);
  });

  for (let r = 2; r < rows.length; r++) {
    const row = rows[r] || [];
    const subjectId = String(row[0] || "").trim();
    const visitName = String(row[1] || "").trim();

    if (!subjectId || !visitName) continue;

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

    const rowData = {};
    let matchedValueCount = 0;

    let col = 2;
    sections.forEach((section, sIndex) => {
      const importedSectionTitle = section.title || section.name || `Section ${sIndex + 1}`;
      const mappedSectionTitle = this.mapSectionTitle(importedSectionTitle);
      const currentFieldsForSection = currentFieldMap.get(mappedSectionTitle);

      const fields = section.fields || [];
      if (!currentFieldsForSection) {
        col += fields.length;
        return;
      }

      fields.forEach((field, fIdx) => {
        const val = row[col++] ?? "";
        const trimmed = String(val).trim();
        if (trimmed === "") return;

        const importedFieldKey =
          field?.name ||
          field?.key ||
          field?.id ||
          field?.label ||
          field?.title ||
          `f${fIdx}`;

        const importedCandidates = [
          field?.name,
          field?.key,
          field?.id,
          field?.label,
          field?.title,
          this.humanizeCamel(field?.name),
          this.humanizeCamel(field?.label),
        ]
          .filter(Boolean)
          .map((x) => this.canonKey(x));

        let matchedCurrentFieldName = null;
        for (const canon of importedCandidates) {
          const hit = currentFieldsForSection.get(canon);
          if (hit) {
            matchedCurrentFieldName = hit;
            break;
          }
        }

        if (!matchedCurrentFieldName) {
          return;
        }

        if (!rowData[mappedSectionTitle]) rowData[mappedSectionTitle] = {};
        rowData[mappedSectionTitle][matchedCurrentFieldName] = trimmed;
        matchedValueCount += 1;
      });
    });

    // Only keep row if at least one actual Case-e field matched
    if (matchedValueCount > 0) {
      subjectIdsSet.add(subjectId);
      visitNamesSet.add(visitName);

      const key = `${sIdx}|${vIdx}|${groupIdx}`;

      if (!incomingEntries[key]) {
        incomingEntries[key] = {
          study_id: this.resolvedStudyId,
          subject_index: sIdx,
          visit_index: vIdx,
          group_index: groupIdx,
          form_version: bundleVersion,
          data: {},
        };
      }

      const entry = incomingEntries[key];
      Object.keys(rowData).forEach((secTitle) => {
        if (!entry.data[secTitle]) entry.data[secTitle] = {};
        Object.assign(entry.data[secTitle], rowData[secTitle]);
      });
    }
  }

  return {
    incomingEntries,
    subjectIds: Array.from(subjectIdsSet),
    visitNames: Array.from(visitNamesSet),
    warnings,
  };
},

    computeConflicts() {
      const conflicts = [];
      const scopeAll = this.scopeMode === "all";
      const scopeSet = new Set(this.selectedSubjectIds || []);
      const conflictSeen = new Set();

      for (const svgKey of Object.keys(this.incomingEntries || {})) {
        const incoming = this.incomingEntries[svgKey];
        const sIdx = incoming.subject_index;
        const vIdx = incoming.visit_index;

        const subject = this.subjects[sIdx];
        const visit = this.visits[vIdx];
        const subjectId = subject?.id;
        const visitName = visit?.name;

        if (!subjectId || !visitName) continue;
        if (!scopeAll && !scopeSet.has(String(subjectId))) continue;

        const existing = this.entriesIndex.get(svgKey);
        if (!existing) continue;

        const exDict = this.entryToDictNormalized(existing);
        const inDict = this.entryToDictNormalized(incoming);

        const allSections = new Set([
          ...Object.keys(exDict || {}),
          ...Object.keys(inDict || {}),
        ]);

        for (const secTitle of allSections) {
          const exSec = exDict[secTitle] || {};
          const inSec = inDict[secTitle] || {};
          const canons = new Set([...Object.keys(exSec), ...Object.keys(inSec)]);

          for (const canon of canons) {
            const exVal = exSec[canon];
            const inVal = inSec[canon];
            if (!this.hasValue(exVal) && !this.hasValue(inVal)) continue;

            if (this.hasValue(exVal) && this.hasValue(inVal) && !this.valuesEqual(exVal, inVal)) {
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

    selectAllSubjects() {
      this.selectedSubjectIds = [...this.bundleSubjectIds];
      this.computeConflicts();
    },

    clearSelectedSubjects() {
      this.selectedSubjectIds = [];
      this.computeConflicts();
    },

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
            const canons = new Set([...Object.keys(exSec), ...Object.keys(inSec)]);

            for (const canon of canons) {
              const exVal = exSec[canon];
              const inVal = inSec[canon];
              const hasEx = this.hasValue(exVal);
              const hasIn = this.hasValue(inVal);
              const cKey = `${svgKey}|${secTitle}|${canon}`;

              if (hasEx && hasIn && !this.valuesEqual(exVal, inVal) && conflictKeySet.has(cKey)) {
                const choice = this.decisions[cKey] || "existing";
                if (choice === "incoming") exSec[canon] = inVal;
                else exSec[canon] = hasEx ? exVal : inVal;
              } else {
                if (hasIn && !hasEx) exSec[canon] = inVal;
                else if (!hasIn && hasEx) exSec[canon] = exVal;
                else if (hasIn && hasEx) exSec[canon] = inVal;
                else exSec[canon] = "";
              }
            }
          }

          const payload = {
            study_id: this.resolvedStudyId,
            subject_index: sIdx,
            visit_index: vIdx,
            group_index: gIdx,
            data: this.denormalizeForSave(baseDict),
            skipped_required_flags: this.makeSkipSkeleton(),
          };

          if (existing?.id) {
            await axios.put(
              `/forms/studies/${this.resolvedStudyId}/data_entries/${existing.id}`,
              payload,
              headers
            );
          } else {
            await axios.post(
              `/forms/studies/${this.resolvedStudyId}/data`,
              payload,
              headers
            );
          }
        }

        await this.loadEntries();
        this.indexEntries();
        this.showDialogMessage("Merge completed successfully.");
      } catch (e) {
        console.error("[Bundle] Merge failed:", e?.response?.data || e);
        this.showDialogMessage("Merge failed. See console for details.");
      } finally {
        this.isMerging = false;
      }
    },

    // ---------- Subject import flow ----------
    initSubjectImportDefaults() {
      const subjectIndex = 0;
      const groupIndex = this.subjectToGroupIdx[subjectIndex] || 0;
      this.subjectImport.subjectIndex = subjectIndex;
      this.subjectImport.visitIndex = 0;
      this.subjectImport.groupIndex = groupIndex;
    },

    onSubjectSelectionChange() {
      this.subjectImport.groupIndex = this.subjectToGroupIdx[this.subjectImport.subjectIndex] || 0;

      const available = this.availableVisitsForSelectedSubject;
      if (!available.some((v) => Number(v.index) === Number(this.subjectImport.visitIndex))) {
        this.subjectImport.visitIndex = available.length ? available[0].index : 0;
      }

      this.rebuildSubjectImportPreview();
    },

    async onSubjectImportFile(event) {
      const file = event?.target?.files?.[0];
      if (!file) return;

      this.subjectImport.fileName = file.name;
      this.subjectImportAssumptionWarning = false;
      this.subjectImport.matchedPairs = {};
      this.subjectImport.normalizedImportData = {};
      this.subjectImport.unmatchedHeaders = [];
      this.subjectImport.matchResultLabel = "—";
      this.subjectImport.detectedLayoutLabel = "—";
      this.parseInfo = { ok: false, message: "" };

      try {
        const buffer = await file.arrayBuffer();
        let workbook = null;
        const lower = file.name.toLowerCase();

        if (lower.endsWith(".csv")) {
          const text = new TextDecoder("utf-8").decode(buffer);
          const parsed = Papa.parse(text, { skipEmptyLines: false });
          const aoa = parsed.data || [];
          workbook = XLSX.utils.book_new();
          const ws = XLSX.utils.aoa_to_sheet(aoa);
          XLSX.utils.book_append_sheet(workbook, ws, "Sheet1");
        } else {
          workbook = XLSX.read(buffer, { type: "array" });
        }

        this.subjectImport.workbook = workbook;
        this.subjectImport.sheetNames = workbook.SheetNames || [];
        this.subjectImport.selectedSheetName = this.subjectImport.sheetNames[0] || "";

        if (!this.subjectImport.selectedSheetName) {
          this.parseInfo = { ok: false, message: "No sheet was found in the uploaded file." };
          return;
        }

        const sheet = workbook.Sheets[this.subjectImport.selectedSheetName];
        const aoa = XLSX.utils.sheet_to_json(sheet, {
          header: 1,
          defval: "",
          raw: false,
          blankrows: false,
        });

        this.subjectImport.rawAoA = Array.isArray(aoa) ? aoa : [];
        this.rebuildSubjectImportPreview();
      } catch (e) {
        console.error("[SubjectImport] Failed to read file", e);
        this.parseInfo = { ok: false, message: "The selected file could not be read. Please upload a valid CSV or Excel file." };
      }
    },

    normalizeText(s) {
      return String(s || "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ")
        .replace(/[._/\\|:-]+/g, " ")
        .replace(/[()]/g, "")
        .trim();
    },

    findMetadataColumns(headers) {
      const normHeaders = headers.map((h) => this.normalizeText(h));
      const findIdx = (patterns) => {
        return normHeaders.findIndex((h) => patterns.some((p) => h.includes(p)));
      };

      return {
        subjectIdx: findIdx(["subject id", "subject", "participant", "participant id"]),
        visitIdx: findIdx(["visit", "visit name", "session", "timepoint"]),
      };
    },

    detectSubjectImportLayout(aoa) {
      const rows = Array.isArray(aoa) ? aoa.filter((r) => Array.isArray(r)) : [];
      if (!rows.length) return "unknown";

      // vertical: many rows, first col header, second col value, usually 2 cols
      const maxCols = Math.max(...rows.map((r) => r.length), 0);
      if (maxCols <= 2 && rows.length >= 2) {
        return "vertical";
      }

      // horizontal default
      return "horizontal";
    },

    extractPairsFromVertical(aoa) {
      const pairs = {};
      (aoa || []).forEach((row) => {
        if (!Array.isArray(row)) return;
        const k = String(row[0] || "").trim();
        const v = row.length > 1 ? row[1] : "";
        if (!k) return;
        if (String(v).trim() === "") return;
        pairs[k] = String(v).trim();
      });
      return pairs;
    },

    extractPairsFromHorizontalForSelectedTarget(aoa) {
      const rows = (aoa || []).filter((r) => Array.isArray(r));
      if (rows.length < 2) return { pairs: {}, usedFallback: true, label: "No usable row found" };

      const headers = (rows[0] || []).map((x) => String(x || "").trim());
      const dataRows = rows.slice(1);

      const { subjectIdx, visitIdx } = this.findMetadataColumns(headers);
      const targetSubject = String(this.selectedSubjectLabel || "").trim();
      const targetVisit = String(this.selectedVisitLabel || "").trim().toLowerCase();

      let matchedRow = null;
      let usedFallback = false;
      let label = "";

      if (subjectIdx >= 0 && visitIdx >= 0) {
        matchedRow = dataRows.find((row) => {
          const subj = String(row?.[subjectIdx] || "").trim();
          const vis = String(row?.[visitIdx] || "").trim().toLowerCase();
          return subj === targetSubject && vis === targetVisit;
        });

        if (matchedRow) {
          label = `Matched row using subject + visit columns`;
        } else {
          usedFallback = true;
          matchedRow = dataRows[0] || [];
          label = `No exact row match found, used first data row`;
        }
      } else {
        usedFallback = true;
        matchedRow = dataRows[0] || [];
        label = `Used first data row`;
      }

      const pairs = {};
      headers.forEach((h, idx) => {
        const val = matchedRow?.[idx];
        if (!h) return;
        if (!this.hasValue(val)) return;
        pairs[h] = String(val).trim();
      });

      return { pairs, usedFallback, label, hasSubjectVisitCols: subjectIdx >= 0 && visitIdx >= 0 };
    },

    matchPairsToCaseEFields(pairs) {
      const normalizedImportData = {};
      const unmatchedHeaders = [];
      const fields = this.study?.content?.study_data?.selectedModels || [];

      const allFieldCandidates = [];
      fields.forEach((sec) => {
        const sectionTitle = sec.title || sec.name || "";
        (sec.fields || []).forEach((f, idx) => {
          const fieldName = f?.name || "";
          const fieldLabel = f?.label || f?.title || f?.name || `Field ${idx + 1}`;
          if (!fieldName) return;

          const candidates = new Set([
            this.normalizeText(fieldName),
            this.normalizeText(fieldLabel),
            this.normalizeText(`${sectionTitle} ${fieldLabel}`),
            this.normalizeText(`${sectionTitle}.${fieldLabel}`),
            this.normalizeText(this.humanizeCamel(fieldName)),
          ]);

          allFieldCandidates.push({
            sectionTitle,
            fieldName,
            fieldLabel,
            candidates: Array.from(candidates).filter(Boolean),
          });
        });
      });

      const isMetadataHeader = (header) => {
        const h = this.normalizeText(header);

        const metadataPatterns = [
          "subject id",
          "subject",
          "participant",
          "participant id",
          "visit",
          "visit name",
          "session",
          "timepoint",
          "group",
          "arm",
          "cohort",
        ];

        return metadataPatterns.some((p) => h === p || h.includes(p));
      };

      Object.keys(pairs || {}).forEach((header) => {
        const val = pairs[header];
        const h = this.normalizeText(header);

        let matched = allFieldCandidates.find((f) => f.candidates.includes(h));

        if (!matched) {
          matched = allFieldCandidates.find((f) =>
            f.candidates.some((c) => c.includes(h) || h.includes(c))
          );
        }

        if (!matched) {
          if (!isMetadataHeader(header)) {
            unmatchedHeaders.push(header);
          }
          return;
        }

        if (!normalizedImportData[matched.sectionTitle]) {
          normalizedImportData[matched.sectionTitle] = {};
        }
        normalizedImportData[matched.sectionTitle][matched.fieldName] = val;
      });

      return { normalizedImportData, unmatchedHeaders };
    },

    rebuildSubjectImportPreview() {
      if (!this.subjectImport.rawAoA || !this.subjectImport.rawAoA.length) {
        this.subjectImport.matchedPairs = {};
        this.subjectImport.normalizedImportData = {};
        this.subjectImport.unmatchedHeaders = [];
        this.subjectImport.matchResultLabel = "—";
        this.subjectImport.detectedLayoutLabel = "—";
        this.subjectImportAssumptionWarning = false;
        this.parseInfo = { ok: false, message: "" };
        return;
      }

      this.subjectImport.groupIndex = this.subjectToGroupIdx[this.subjectImport.subjectIndex] || 0;

      const layout = this.detectSubjectImportLayout(this.subjectImport.rawAoA);
      this.subjectImport.detectedLayout = layout;
      this.subjectImport.detectedLayoutLabel =
        layout === "vertical" ? "Vertical key-value" : "Horizontal row";

      let pairs = {};
      let usedFallback = false;
      let label = "";
      let hasSubjectVisitCols = false;

      if (layout === "vertical") {
        pairs = this.extractPairsFromVertical(this.subjectImport.rawAoA);
        usedFallback = true;
        label = "Used key-value pairs from file";
        hasSubjectVisitCols = false;
      } else {
        const res = this.extractPairsFromHorizontalForSelectedTarget(this.subjectImport.rawAoA);
        pairs = res.pairs || {};
        usedFallback = !!res.usedFallback;
        label = res.label || "Used row from file";
        hasSubjectVisitCols = !!res.hasSubjectVisitCols;
      }

      this.subjectImport.matchedPairs = pairs;
      this.subjectImport.matchResultLabel = label;
      this.subjectImportAssumptionWarning = !hasSubjectVisitCols;

      const { normalizedImportData, unmatchedHeaders } = this.matchPairsToCaseEFields(pairs);
      this.subjectImport.normalizedImportData = normalizedImportData;
      this.subjectImport.unmatchedHeaders = unmatchedHeaders;

      const matchedFieldCount = this.subjectImportSummaryRows.length;

      if (matchedFieldCount === 0) {
        this.parseInfo = {
          ok: false,
          message:
            "No file headers could be matched to Case-e fields for the selected subject/visit. Nothing will be imported.",
        };
      } else {
        this.parseInfo = {
          ok: true,
          message: `Prepared subject import. Matched fields: ${matchedFieldCount}. Unmatched headers: ${unmatchedHeaders.length}.`,
        };
      }
    },

    async saveSubjectImport() {
      if (!this.canSaveSubjectImport) {
        this.showDialogMessage("No matched Case-e fields were found in the uploaded file. Nothing to save.");
        return;
      }

      this.isSavingSubjectImport = true;
      try {
        const sIdx = this.subjectImport.subjectIndex;
        const vIdx = this.subjectImport.visitIndex;
        const gIdx = this.subjectImport.groupIndex;
        const svgKey = `${sIdx}|${vIdx}|${gIdx}`;

        const existing = this.entriesIndex.get(svgKey) || null;
        const baseDict = this.entryToDictNormalized(existing);

        const incomingEntry = {
          study_id: this.resolvedStudyId,
          subject_index: sIdx,
          visit_index: vIdx,
          group_index: gIdx,
          form_version: Number(this.study?.metadata?.version || 1),
          data: this.subjectImport.normalizedImportData,
        };

        const inDict = this.entryToDictNormalized(incomingEntry);

        const allSections = new Set([
          ...Object.keys(baseDict || {}),
          ...Object.keys(inDict || {}),
        ]);

        for (const secTitle of allSections) {
          if (!baseDict[secTitle]) baseDict[secTitle] = {};
          const exSec = baseDict[secTitle];
          const inSec = inDict[secTitle] || {};

          Object.keys(inSec).forEach((canon) => {
            if (this.hasValue(inSec[canon])) {
              exSec[canon] = inSec[canon];
            }
          });
        }

        const payload = {
          study_id: this.resolvedStudyId,
          subject_index: sIdx,
          visit_index: vIdx,
          group_index: gIdx,
          data: this.denormalizeForSave(baseDict),
          skipped_required_flags: this.makeSkipSkeleton(),
        };

        const headers = {
          headers: { Authorization: `Bearer ${this.$store.state.token}` },
        };

        if (existing?.id) {
          await axios.put(
            `/forms/studies/${this.resolvedStudyId}/data_entries/${existing.id}`,
            payload,
            headers
          );
        } else {
          await axios.post(
            `/forms/studies/${this.resolvedStudyId}/data`,
            payload,
            headers
          );
        }

        await this.loadEntries();
        this.indexEntries();

        this.showDialogMessage("Subject data imported successfully.");
      } catch (e) {
        console.error("[SubjectImport] Save failed:", e?.response?.data || e);
        this.showDialogMessage("Failed to save imported subject data. See console for details.");
      } finally {
        this.isSavingSubjectImport = false;
      }
    },
  },
};
</script>

<style scoped>
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

.icon-btn {
  padding: 8px 10px;
  line-height: 1;
}
.file-hidden {
  display: none;
}

.merge-page:not(.embedded):not(.expanded) {
  max-width: 1400px;
  margin: 24px auto;
  padding: 0 16px 72px;
}
.merge-page.embedded:not(.expanded) {
  width: 100%;
  margin: 0;
  padding: 0;
}
.merge-page.expanded {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #ffffff;
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 12px 12px 72px;
  overflow: auto;
  box-sizing: border-box;
}

.header-row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  margin-bottom: 12px;
}
.header-actions {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
}
.existing-studies-title {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.source-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.source-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
}
.source-pill.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}
.source-pill input {
  margin: 0;
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

.main-layout {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 0.58fr) minmax(0, 0.42fr);
  gap: 12px;
  align-items: flex-start;
}
.main-layout.single-column {
  grid-template-columns: minmax(0, 1fr);
}
.left-column,
.right-column {
  padding: 14px 14px 16px;
}

.subject-import-layout {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}
.subject-step {
  padding: 14px 14px 16px;
}

.no-conflicts-panel {
  min-height: 220px;
}

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
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.summary-grid-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
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

.template-compare,
.scope-card {
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
.mismatch-list {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 12px;
}

.radio-row {
  display: flex;
  align-items: center;
  font-size: 13px;
  gap: 8px;
  margin-bottom: 6px;
}
.helper {
  margin: 0 0 6px;
  font-size: 13px;
  color: #6b7280;
}
.helper.large {
  font-size: 14px;
}
.subject-select {
  margin-top: 8px;
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

.control-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 10px;
}
.control-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.control-block label {
  font-size: 12px;
  color: #374151;
  font-weight: 600;
}
.control-block select,
.control-block input {
  min-height: 38px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  background: #fff;
}
.control-block input[disabled] {
  background: #f3f4f6;
  color: #6b7280;
}

.layout-hint-wrap {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 8px;
}
.layout-hint {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  font-size: 13px;
  color: #374151;
}
.layout-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #111827;
}

.file-meta {
  margin-top: 10px;
  font-size: 14px;
  color: #374151;
}

.conflict-table-wrapper,
.preview-table-wrap {
  margin-top: 10px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}
.conflict-table-wrapper {
  max-height: 70vh;
}

.conflict-table,
.preview-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 860px;
  font-size: 13px;
}
.preview-table {
  min-width: 700px;
}
.conflict-table th,
.conflict-table td,
.preview-table th,
.preview-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px 10px;
  vertical-align: top;
  text-align: left;
}
.conflict-table th,
.preview-table th {
  background: #f3f4f6;
  color: #111827;
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
.global-commit.embedded {
  position: sticky;
  left: auto;
  right: auto;
  bottom: 0;
  margin-top: 12px;
  z-index: 5;
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

.mt {
  margin-top: 12px;
}

@media (max-width: 1180px) {
  .control-grid,
  .summary-grid-4,
  .layout-hint-wrap {
    grid-template-columns: 1fr;
  }
}

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
.step-upload-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.spreadsheet-row-preview {
  overflow-x: auto;
}

.row-preview-table {
  min-width: max-content;
  width: auto;
}

.row-preview-table th,
.row-preview-table td {
  min-width: 180px;
  white-space: nowrap;
}
</style>