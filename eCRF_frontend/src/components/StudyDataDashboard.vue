/* eslint-disable */
<template>
  <div class="study-dashboard-container" :class="{ embedded, fullscreen }" v-if="study">
    <!-- header controls (NO back button, NO study name header) -->
    <div class="dashboard-header-controls">
      <div class="left-controls">
        <div class="version-dropdown">
          <label for="version-select">Version:</label>
          <select id="version-select" v-model.number="selectedVersion">
            <option v-for="v in studyVersions" :key="'ver-'+v.version" :value="v.version">
              {{ v.version }}
            </option>
          </select>
        </div>
      </div>

      <div class="right-controls">
        <!-- Fit-to-screen -->
        <button
          class="btn-minimal icon-only"
          type="button"
          @click="$emit('toggle-fullscreen')"
          :title="fullscreen ? 'Exit fit to screen' : 'Fit to screen'"
          aria-label="Fit to screen"
        >
          <i :class="fullscreen ? icons.compress : icons.expand"></i>
        </button>

        <div class="legend-dropdown">
          <button class="btn-minimal icon-only" @click="showLegend = !showLegend" title="Table Legend">
            <i :class="icons.info"></i>
          </button>
          <div v-if="showLegend" class="legend-content" @click.stop>
            <p>
              <span class="legend-swatch swatch-gray"></span>
              <strong>Gray cell:</strong> No section assigned for this subject’s group at this visit.
            </p>
            <p>
              <span class="legend-swatch swatch-none"></span>
              <strong>No color:</strong> Section assigned but no data has been entered.
            </p>
            <p>
              <span class="legend-swatch swatch-red"></span>
              <strong>Red cell:</strong> Required field was <em>skipped</em> when saving.
            </p>
            <p>Data is displayed for each subject under the visit and section assigned to their group.</p>
          </div>
        </div>

        <div class="export-dropdown">
          <button class="btn-minimal" @click.stop="toggleExportMenu">
            Export <i :class="icons.export"></i>
          </button>
          <div v-if="showExportMenu" class="export-menu" @click.stop>
            <button @click="exportCSV">Download CSV</button>
            <button @click="exportExcel">Download Excel</button>
            <button @click="exportStudyZip">Download Study (ZIP)</button>
          </div>
        </div>
      </div>
    </div>

    <div class="table-controls">
      <div class="left">
        <span>Total rows: {{ totalGridRows }}</span>
        <label v-if="canViewAll" class="view-all">
          <input type="checkbox" v-model="viewAll" />
          View all (≤ {{ VIEW_ALL_MAX_ROWS }})
        </label>
      </div>
      <div class="right" v-if="!viewAll">
        <label for="page-size">Rows per page:</label>
        <select id="page-size" v-model.number="pageSize">
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
    </div>

    <div class="table-wrapper">
      <div class="loading" v-if="isLoadingEntries">Building dashboard…</div>

      <table class="dashboard-table" v-else>
        <thead>
          <tr>
            <th rowspan="2" @click="sortTable('subjectId')">
              Subject ID
              <i :class="sortIcon('subjectId')"></i>
            </th>

            <!-- Group column: Admin OR Creator/Owner OR has add_data/edit_study (NOT view-only) -->
            <th v-if="canViewGroupColumn" rowspan="2" @click="sortTable('group')">
              Group
              <i :class="sortIcon('group')"></i>
            </th>
            <th rowspan="2" @click="sortTable('visit')">
              Visit
              <i :class="sortIcon('visit')"></i>
            </th>
            <template v-for="(section, sIdx) in sections" :key="'hdr-sec-'+sIdx">
              <th :colspan="fieldsPerSection[sIdx]">{{ section.title }}</th>
            </template>
          </tr>
          <tr>
            <template v-for="(section, sIdx) in sections" :key="'hdr-fld-'+sIdx">
              <template v-for="(field, fIdx) in section.fields" :key="'hdr-fld-'+sIdx+'-'+fIdx">
                <th @click="sortTable(`s${sIdx}_f${fIdx}`)">
                  {{ field.label || field.name || field.title || `Field ${fIdx+1}` }}
                  <i :class="sortIcon(`s${sIdx}_f${fIdx}`)"></i>
                </th>
              </template>
            </template>
          </tr>
          <tr class="filter-row">
            <th><input v-model="filters.subjectId" placeholder="Filter Subject ID"></th>
            <th v-if="canViewGroupColumn"><input v-model="filters.group" placeholder="Filter Group"></th>
            <th><input v-model="filters.visit" placeholder="Filter Visit"></th>
            <template v-for="(section, sIdx) in sections" :key="'filter-sec-'+sIdx">
              <template v-for="(field, fIdx) in section.fields" :key="'filter-fld-'+sIdx+'-'+fIdx">
                <th>
                  <input
                    v-model="filters[`s${sIdx}_f${fIdx}`]"
                    :placeholder="`Filter ${field.label || field.name || field.title || (fIdx+1)}`"
                  >
                </th>
              </template>
            </template>
          </tr>
        </thead>

        <tbody>
          <template v-for="(row, rowIdx) in paginatedData" :key="'row-'+rowIdx">
            <tr>
              <td class="fixed-col">{{ row.subjectId }}</td>
              <td v-if="canViewGroupColumn" class="fixed-col">{{ row.group }}</td>
              <td class="fixed-col">{{ row.visit }}</td>
              <template v-for="(section, sIdx) in sections" :key="'row-sec-'+rowIdx+'-s'+sIdx">
                <template v-for="(field, fIdx) in section.fields" :key="'cell-'+rowIdx+'-s'+sIdx+'-f'+fIdx">
                  <td :class="cellClass(row.__sIdx, row.__vIdx, sIdx, fIdx)">
                    {{ row[`s${sIdx}_f${fIdx}`] }}
                  </td>
                </template>
              </template>
            </tr>
          </template>
        </tbody>
      </table>

      <div class="pagination-controls" v-if="!viewAll && !isLoadingEntries">
        <button :disabled="currentPage === 1" @click="goFirst">First</button>
        <button :disabled="currentPage === 1" @click="goPrev">Previous</button>
        <span>Page {{ currentPage }} of {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="goNext">Next</button>
        <button :disabled="currentPage === totalPages" @click="goLast">Last</button>
      </div>
    </div>

    <div v-if="!filteredData.length && !isLoadingEntries" class="no-data">
      No data entries found. Please enter data for the assigned sections using the data entry form.
    </div>
  </div>

  <div v-else class="loading">
    Loading study data…
  </div>
</template>

<script>
import axios from 'axios';
import icons from "@/assets/styles/icons";
import { downloadStudyBundle } from "@/utils/studyDownload";

export default {
  name: 'StudyDataDashboard',
  props: {
    studyId: { type: [String, Number], default: null },
    embedded: { type: Boolean, default: false },
    fullscreen: { type: Boolean, default: false },
  },
  data() {
    return {
      study: null,
      entries: [],
      totalEntries: 0,

      showExportMenu: false,
      showLegend: false,
      token: this.$store.state.token,
      icons,

      sortConfig: { key: 'subjectId', direction: 'asc' },
      filters: { subjectId: '', group: '', visit: '' },

      currentPage: 1,
      pageSize: 50,
      VIEW_ALL_MAX_ROWS: 1000,
      viewAll: false,
      isLoadingEntries: false,

      studyVersions: [],
      selectedVersion: null,
      templateCache: new Map(),
    };
  },
  computed: {
    visits() { return this.study?.content?.study_data?.visits || []; },
    sections() { return this.study?.content?.study_data?.selectedModels || []; },
    subjects() { return this.study?.content?.study_data?.subjects || []; },
    fieldsPerSection() { return this.sections.map(sec => sec.fields?.length || 0); },

    totalGridRows() { return (this.subjects?.length || 0) * (this.visits?.length || 0); },
    canViewAll() { return this.totalGridRows > 0 && this.totalGridRows <= this.VIEW_ALL_MAX_ROWS; },

    currentUser() {
      return this.$store.getters.getUser || {};
    },
    role() {
      return this.currentUser.profile?.role || "";
    },
    userName() {
      const p = this.currentUser.profile || {};
      const firstLast = [p.first_name, p.last_name].filter(Boolean).join(" ").trim();
      return (
        p.name ||
        p.full_name ||
        firstLast ||
        this.currentUser.username ||
        this.currentUser.email ||
        "User"
      );
    },
    isAdmin() {
      return this.role === "Administrator";
    },

    // Owner/author (creator) check (matches backend created_by being numeric)
    isCreator() {
      const meta = this.study?.metadata || {};
      const createdBy = meta.created_by;
      if (createdBy == null) return false;

      const myId = this.currentUser?.id ?? this.currentUser?.user_id ?? this.currentUser?.profile?.id ?? null;
      if (myId == null) return false;

      return String(createdBy) === String(myId);
    },

    // permissions are expected at `study.metadata.permissions` (same as dashboard option-a)
    studyPerms() {
      const perms = this.study?.metadata?.permissions;
      return perms && typeof perms === "object" ? perms : null;
    },

    hasAddPermission() {
      const p = this.studyPerms;
      return p ? p.add_data === true : false;
    },
    hasEditPermission() {
      const p = this.studyPerms;
      return p ? p.edit_study === true : false;
    },

    // IMPORTANT FIX:
    // Group column visible only to:
    // - Admin
    // - Creator/Owner
    // - users with add_data OR edit_study
    // View-only users do NOT see Group column.
    canViewGroupColumn() {
      return this.isAdmin || this.isCreator || this.hasAddPermission || this.hasEditPermission;
    },

    filteredData() {
      let data = [];
      const { subjectIdxPageSet, visitIdxPageSet } = this.currentWindowIndexSets();

      this.subjects.forEach((subject, subjIdx) => {
        if (!subjectIdxPageSet.has(subjIdx)) return;

        const groupIdx = this.resolveGroup(subjIdx);
        const groupName = this.resolveGroupName(subjIdx);
        this.visits.forEach((visit, vIdx) => {
          if (!visitIdxPageSet.has(vIdx)) return;

          const row = { subjectId: subject.id, group: groupName, visit: visit.name, __sIdx: subjIdx, __vIdx: vIdx };
          this.sections.forEach((section, sIdx) => {
            const assigned = this.isAssigned(sIdx, vIdx, groupIdx);
            section.fields.forEach((field, fIdx) => {
              let value = '';
              if (assigned) {
                const raw = this.getValue(subjIdx, vIdx, sIdx, fIdx);
                const type = (field.type || '').toLowerCase();
                if (type === 'checkbox') value = (raw === true) ? 'Yes' : (raw === false) ? 'No' : '';
                else if (type === 'file') value = this.formatFileCell(raw);
                else value = (raw == null || raw === '') ? '' : raw;
              }
              row[`s${sIdx}_f${fIdx}`] = value;
            });
          });
          data.push(row);
        });
      });

      data = data.filter(row => {
        if (this.filters.subjectId && !String(row.subjectId).toLowerCase().includes(this.filters.subjectId.toLowerCase())) return false;
        if (this.canViewGroupColumn && this.filters.group && !String(row.group).toLowerCase().includes(this.filters.group.toLowerCase())) return false;
        if (this.filters.visit && !String(row.visit).toLowerCase().includes(this.filters.visit.toLowerCase())) return false;

        for (const key in this.filters) {
          if (key === 'subjectId' || key === 'group' || key === 'visit') continue;
          const filterVal = this.filters[key];
          if (filterVal && !String(row[key] ?? '').toLowerCase().includes(String(filterVal).toLowerCase())) return false;
        }
        return true;
      });

      if (this.sortConfig.key) {
        const key = this.sortConfig.key;
        const dir = this.sortConfig.direction === 'asc' ? 1 : -1;
        data.sort((a, b) => {
          let valA = a[key] ?? '';
          let valB = b[key] ?? '';
          if (key === 'group' && !this.canViewGroupColumn) {
            valA = '';
            valB = '';
          }
          valA = String(valA).toLowerCase();
          valB = String(valB).toLowerCase();
          if (valA < valB) return -1 * dir;
          if (valA > valB) return 1 * dir;
          return 0;
        });
      }

      return data;
    },

    totalPages() {
      if (this.viewAll) return 1;
      const wholeGridPages = Math.ceil(this.totalGridRows / this.pageSize);
      return Math.max(1, wholeGridPages);
    },

    paginatedData() {
      return this.filteredData;
    },
  },
  watch: {
    pageSize() {
      if (this.viewAll) return;
      this.currentPage = 1;
      this.fetchPageEntries();
    },
    currentPage() {
      if (this.viewAll) return;
      this.fetchPageEntries();
    },
    viewAll() {
      this.currentPage = 1;
      this.fetchPageEntries();
    },
    filters: {
      handler() {
        if (!this.viewAll) this.fetchPageEntries();
      },
      deep: true,
    },
    selectedVersion: {
      async handler() {
        if (!this.study) return;
        await this.loadTemplateForSelectedVersion();
        this.initDynamicFilters();
        this.currentPage = 1;
        await this.fetchPageEntries();
      }
    }
  },
  async created() {
    await this.bootstrap();
  },
  methods: {
    getStudyId() {
      return this.studyId != null ? String(this.studyId) : String(this.$route.params.id);
    },

    normalizeKey(k){ return String(k || '').trim().toLowerCase(); },
    sectionDictKey(sectionObj) { return sectionObj?.title ?? ''; },
    fieldDictKey(fieldObj, fallbackIndex) {
      return fieldObj?.name ?? fieldObj?.key ?? fieldObj?.id ?? fieldObj?.label ?? fieldObj?.title ?? `f${fallbackIndex}`;
    },
    dictRead(dataDict, sIdx, fIdx) {
      if (!dataDict || typeof dataDict !== 'object' || Array.isArray(dataDict)) return undefined;

      const sec = this.sections[sIdx];
      const fld = sec?.fields?.[fIdx];

      const sKey = this.sectionDictKey(sec);
      const fKey = this.fieldDictKey(fld, fIdx);

      let secObj = dataDict[sKey];
      if (!secObj) {
        const wanted = this.normalizeKey(sKey);
        const hitKey = Object.keys(dataDict).find(k => this.normalizeKey(k) === wanted);
        if (hitKey) secObj = dataDict[hitKey];
      }
      if (!secObj || typeof secObj !== 'object') return undefined;

      if (Object.prototype.hasOwnProperty.call(secObj, fKey)) return secObj[fKey];

      const wantedField = this.normalizeKey(fKey);
      const hitField = Object.keys(secObj).find(k => this.normalizeKey(k) === wantedField);
      if (hitField) return secObj[hitField];

      return undefined;
    },

    async bootstrap() {
      const studyId = this.getStudyId();
      try {
        const studyResp = await axios.get(`/forms/studies/${studyId}`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.study = studyResp.data;

        await this.loadVersions(studyId);
        if (!this.selectedVersion && this.studyVersions.length) {
          this.selectedVersion = this.studyVersions[this.studyVersions.length - 1].version;
        }
        await this.loadTemplateForSelectedVersion();

        this.initDynamicFilters();

        if (this.canViewAll) this.viewAll = false;
        await this.fetchPageEntries();
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        if (err.response && err.response.status === 401) {
          this.$router.push({ name: 'Login' });
        } else {
          alert('Could not load study data');
        }
      }
    },

    initDynamicFilters() {
      const base = { subjectId: this.filters.subjectId || '', group: this.filters.group || '', visit: this.filters.visit || '' };
      const next = { ...base };
      this.sections.forEach((section, sIdx) => {
        section.fields.forEach((_, fIdx) => {
          const key = `s${sIdx}_f${fIdx}`;
          next[key] = this.filters[key] || '';
        });
      });

      if (!this.canViewGroupColumn) next.group = '';
      this.filters = next;
    },

    async loadVersions(studyId) {
      try {
        const resp = await axios.get(`/forms/studies/${studyId}/versions`, {
          headers: { Authorization: `Bearer ${this.token}` }
        });
        const arr = Array.isArray(resp.data) ? resp.data : [];
        this.studyVersions = arr.sort((a, b) => a.version - b.version);
      } catch (e) {
        this.studyVersions = [{ version: 1 }];
      }
    },

    async loadTemplateForSelectedVersion() {
      const studyId = this.getStudyId();
      if (!studyId || !this.selectedVersion) return;

      if (this.templateCache.has(this.selectedVersion)) {
        const cached = this.templateCache.get(this.selectedVersion);
        this.applyTemplateSchema(cached);
        return;
      }
      try {
        const resp = await axios.get(`/forms/studies/${studyId}/template`, {
          headers: { Authorization: `Bearer ${this.token}` },
          params: { version: this.selectedVersion }
        });
        const schema = resp?.data?.schema || {};
        this.templateCache.set(this.selectedVersion, schema);
        this.applyTemplateSchema(schema);
      } catch (e) {
        // eslint: ignore template fetch failures; keep current schema
      }
    },

    applyTemplateSchema(schema) {
      const current = this.study?.content?.study_data || {};
      const normalized = {
        study: schema?.study ?? current.study ?? {},
        subjects: Array.isArray(schema?.subjects) && schema.subjects.length ? schema.subjects : (current.subjects || []),
        subjectCount: Number.isFinite(schema?.subjectCount) ? schema.subjectCount : (current.subjectCount ?? (current.subjects?.length || 0)),
        visits: Array.isArray(schema?.visits) && schema.visits.length ? schema.visits : (current.visits || []),
        groups: Array.isArray(schema?.groups) && schema.groups.length ? schema.groups : (current.groups || []),
        selectedModels: Array.isArray(schema?.selectedModels) ? schema.selectedModels : (current.selectedModels || []),
        assignments: Array.isArray(schema?.assignments) ? schema.assignments : (current.assignments || []),
      };
      if (!this.study) this.study = { metadata: {}, content: { study_data: normalized } };
      else if (!this.study.content) this.study.content = { study_data: normalized };
      else this.study.content.study_data = normalized;
    },

    currentWindowIndexSets() {
      const S = this.subjects.length;
      const V = this.visits.length;

      if (this.viewAll || S === 0 || V === 0) {
        return {
          subjectIdxPageSet: new Set([...Array(S).keys()]),
          visitIdxPageSet: new Set([...Array(V).keys()]),
          totalRowsInWindow: S * V,
        };
      }

      const pageStart = (this.currentPage - 1) * this.pageSize;
      const pageEndExcl = Math.min(pageStart + this.pageSize, S * V);

      const subjSet = new Set();
      const visitSet = new Set();

      for (let idx = pageStart; idx < pageEndExcl; idx++) {
        const subjIdx = Math.floor(idx / V);
        const visitIdx = idx % V;
        subjSet.add(subjIdx);
        visitSet.add(visitIdx);
      }

      return {
        subjectIdxPageSet: subjSet,
        visitIdxPageSet: visitSet,
        totalRowsInWindow: pageEndExcl - pageStart,
      };
    },

    async fetchPageEntries() {
      if (!this.study) return;
      const studyId = this.getStudyId();

      const { subjectIdxPageSet, visitIdxPageSet } = this.currentWindowIndexSets();

      const subject_indexes = this.viewAll
        ? null
        : Array.from(subjectIdxPageSet).sort((a, b) => a - b).join(',');
      const visit_indexes = this.viewAll
        ? null
        : Array.from(visitIdxPageSet).sort((a, b) => a - b).join(',');

      const params = new URLSearchParams();
      if (this.viewAll) params.append('all', 'true');
      if (subject_indexes) params.append('subject_indexes', subject_indexes);
      if (visit_indexes) params.append('visit_indexes', visit_indexes);
      if (Number.isFinite(this.selectedVersion)) params.append('version', String(this.selectedVersion));

      const url = `/forms/studies/${studyId}/data_entries` + (params.toString() ? `?${params.toString()}` : '');

      try {
        this.isLoadingEntries = true;
        const resp = await axios.get(url, { headers: { Authorization: `Bearer ${this.token}` } });
        const payload = Array.isArray(resp.data) ? { entries: resp.data, total: resp.data.length } : (resp.data || {});
        this.entries = payload.entries || [];
        this.totalEntries = payload.total ?? this.entries.length;
      } catch (err) {
        console.error('Failed to load entries:', err);
        this.entries = [];
      } finally {
        this.isLoadingEntries = false;
      }
    },

    toggleExportMenu() { this.showExportMenu = !this.showExportMenu; },

    resolveGroup(subjIdx) {
      const subjGroup = (this.subjects[subjIdx]?.group || '').trim().toLowerCase();
      const grpList = this.study?.content?.study_data?.groups || [];
      const idx = grpList.findIndex(g => (g.name || '').trim().toLowerCase() === subjGroup);
      return idx >= 0 ? idx : 0;
    },
    resolveGroupName(subjIdx) {
      const subjGroup = (this.subjects[subjIdx]?.group || '').trim();
      const subjGroupNorm = subjGroup.toLowerCase();
      const grpList = this.study?.content?.study_data?.groups || [];
      const hit = grpList.find(g => (g.name || '').trim().toLowerCase() === subjGroupNorm);
      return hit?.name || subjGroup || '';
    },
    isAssigned(sectionIdx, visitIdx, groupIdx) {
      return !!(this.study?.content?.study_data?.assignments?.[sectionIdx]?.[visitIdx]?.[groupIdx]);
    },
    findBestEntry(subjIdx, visitIdx, groupIdx) {
      const all = (this.entries || []).filter(e =>
        e.subject_index === subjIdx &&
        e.visit_index === visitIdx &&
        e.group_index === groupIdx
      );
      if (!all.length) return null;

      const target = Number(this.selectedVersion);
      const exact = all.find(e => Number(e.form_version) === target);
      if (exact) return exact;

      const le = all
        .filter(e => Number(e.form_version) <= target)
        .sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
      if (le) return le;

      return all.sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
    },

    getValue(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.findBestEntry(subjIdx, visitIdx, groupIdx);
      if (!entry || !entry.data) return '';
      const d = entry.data;
      if (!Array.isArray(d)) {
        const v = this.dictRead(d, sectionIdx, fieldIdx);
        return v != null ? v : '';
      }
      const section = Array.isArray(d) ? (d[sectionIdx] || []) : [];
      return section[fieldIdx] != null ? section[fieldIdx] : '';
    },
    isCellSkipped(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.findBestEntry(subjIdx, visitIdx, groupIdx);
      if (!entry) return false;
      const flags = entry.skipped_required_flags;
      return !!(Array.isArray(flags) &&
                Array.isArray(flags[sectionIdx]) &&
                flags[sectionIdx][fieldIdx] === true);
    },
    cellClass(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const assigned = this.isAssigned(sectionIdx, visitIdx, groupIdx);
      return {
        'cell-skipped': this.isCellSkipped(subjIdx, visitIdx, sectionIdx, fieldIdx),
        'cell-unassigned': !assigned,
        'cell-empty-assigned': false
      };
    },

    sortTable(key) {
      if (key === 'group' && !this.canViewGroupColumn) return;
      if (this.sortConfig.key === key) {
        this.sortConfig.direction = this.sortConfig.direction === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortConfig = { key, direction: 'asc' };
      }
    },
    sortIcon(key) {
      return this.sortConfig.key === key && this.sortConfig.direction === 'desc'
        ? this.icons.toggleDown
        : this.icons.toggleUp;
    },

    formatFileCell(val) {
      const baseName = (p) => {
        if (!p) return '';
        const s = String(p);
        const parts = s.split(/[\\/]/);
        return parts[parts.length - 1];
      };
      const fromObj = (o) => o.file_name || o.name || baseName(o.url) || baseName(o.file_path) || '';
      if (Array.isArray(val)) {
        const names = val.map(v => {
          if (v && typeof v === 'object') return fromObj(v);
          if (typeof v === 'string') return baseName(v);
          return '';
        }).filter(Boolean);
        return names.join(', ');
      }
      if (val && typeof val === 'object') return fromObj(val);
      if (typeof val === 'string') return baseName(val);
      return '';
    },

    goFirst() { this.currentPage = 1; },
    goPrev()  { if (this.currentPage > 1) this.currentPage--; },
    goNext()  { if (this.currentPage < this.totalPages) this.currentPage++; },
    goLast()  { this.currentPage = this.totalPages; },

    async exportCSV() {
      const allRows = await this.ensureAllEntriesForExport();
      this.downloadDelimited(allRows, 'csv');
      this.showExportMenu = false;
    },
    async exportExcel() {
      const allRows = await this.ensureAllEntriesForExport();
      this.downloadDelimited(allRows, 'xls');
      this.showExportMenu = false;
    },
    async ensureAllEntriesForExport() {
      const studyId = this.getStudyId();

      let entriesForExport = this.entries;

      if (!this.viewAll && !this.canViewAll) {
        try {
          const resp = await axios.get(
            `/forms/studies/${studyId}/data_entries?all=true&version=${this.selectedVersion}`,
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          const payload = Array.isArray(resp.data) ? { entries: resp.data } : (resp.data || {});
          entriesForExport = payload.entries || [];
        } catch (e) {
          console.error('Failed to fetch all entries for export, using current page only.', e);
        }
      }

      const original = this.entries;
      this.entries = entriesForExport;

      const rows = [];
      this.subjects.forEach((subject, subjIdx) => {
        const groupIdx = this.resolveGroup(subjIdx);
        const groupName = this.resolveGroupName(subjIdx);
        this.visits.forEach((visit, vIdx) => {
          const row = { subjectId: subject.id, group: groupName, visit: visit.name };
          this.sections.forEach((section, sIdx) => {
            const assigned = this.isAssigned(sIdx, vIdx, groupIdx);
            section.fields.forEach((field, fIdx) => {
              let value = '';
              if (assigned) {
                const raw = this.getValue(subjIdx, vIdx, sIdx, fIdx);
                const type = (field.type || '').toLowerCase();
                if (type === 'checkbox') value = (raw === true) ? 'Yes' : (raw === false) ? 'No' : '';
                else if (type === 'file') value = this.formatFileCell(raw);
                else value = (raw == null || raw === '') ? '' : raw;
              }
              row[`s${sIdx}_f${fIdx}`] = value;
            });
          });
          rows.push(row);
        });
      });

      this.entries = original;
      return rows;
    },
    downloadDelimited(rows, kind) {
      const quote = v => `"${String(v).replace(/"/g, '""')}"`;
      const hdr1 = this.canViewGroupColumn
        ? ['Subject ID', 'Group', 'Visit', ...this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))]
        : ['Subject ID', 'Visit', ...this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))];
      const hdr2 = this.canViewGroupColumn
        ? ['', '', '', ...this.sections.flatMap(sec => sec.fields.map(f => f.label || f.name || f.title))]
        : ['', '', ...this.sections.flatMap(sec => sec.fields.map(f => f.label || f.name || f.title))];

      const lines = [];
      lines.push(hdr1.map(quote).join(','));
      lines.push(hdr2.map(quote).join(','));

      const filteredRows = rows.filter(row => {
        if (this.filters.subjectId && !String(row.subjectId).toLowerCase().includes(this.filters.subjectId.toLowerCase())) return false;
        if (this.canViewGroupColumn && this.filters.group && !String(row.group).toLowerCase().includes(this.filters.group.toLowerCase())) return false;
        if (this.filters.visit && !String(row.visit).toLowerCase().includes(this.filters.visit.toLowerCase())) return false;
        for (const key in this.filters) {
          if (key === 'subjectId' || key === 'group' || key === 'visit') continue;
          const f = this.filters[key];
          if (f && !String(row[key] ?? '').toLowerCase().includes(String(f).toLowerCase())) return false;
        }
        return true;
      });

      filteredRows.forEach(row => {
        const cells = this.canViewGroupColumn ? [row.subjectId, row.group, row.visit] : [row.subjectId, row.visit];
        this.sections.forEach((section, sIdx) => {
          section.fields.forEach((_, fIdx) => {
            cells.push(row[`s${sIdx}_f${fIdx}`]);
          });
        });
        lines.push(cells.map(quote).join(','));
      });

      const mime = kind === 'xls'
        ? 'application/vnd.ms-excel'
        : 'text/csv';
      const ext = kind === 'xls' ? 'xls' : 'csv';

      const blob = new Blob([lines.join('\r\n')], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.study?.metadata?.study_name || 'study'}_v${this.selectedVersion}_data.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },

    async exportStudyZip() {
      try {
        await downloadStudyBundle({
          studyId: this.getStudyId(),
          token: this.token,
        });
        this.showExportMenu = false;
      } catch (e) {
        console.error("Failed to download study bundle:", e);
        alert("Failed to download study bundle.");
      }
    },
  },
};
</script>

<style scoped>
.dashboard-header-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.left-controls, .right-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-minimal {
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 0.9rem;
  color: #374151;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-minimal:hover { background: #f3f4f6; border-color: #9ca3af; color: #1f2937; }
.icon-only { padding: 6px 10px; font-size: 1rem; }

.version-dropdown label {
  margin-right: 6px;
  font-size: 0.9rem;
  color: #374151;
}
.version-dropdown select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  font-size: 0.9rem;
  color: #374151;
}

.export-dropdown,
.legend-dropdown {
  justify-self: end;
  position: relative;
}

.export-menu,
.legend-content {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  z-index: 20;
  padding: 12px;
  min-width: 240px;
}
.export-menu button {
  display: block; width: 100%; padding: 8px 16px; background: none; border: none;
  text-align: left; font-size: 0.9rem; cursor: pointer;
}
.export-menu button:hover { background: #f3f4f6; }

.legend-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 6px;
  border: 1px solid #d1d5db;
  vertical-align: -2px;
  background: #ffffff;
}
.swatch-none { background: #ffffff; border-color: #d1d5db; }
.swatch-gray { background: #e5e7eb; border-color: #9ca3af; }
.swatch-red  { background: #fee2e2; border-color: #ef4444; }

/* table controls */
.table-controls {
  display: flex; justify-content: space-between; align-items: center; margin: 8px 0;
  color: #4b5563; font-size: 0.9rem; gap: 10px; flex-wrap: wrap;
}
.table-controls .view-all { margin-left: 12px; }

/* wrapper */
.study-dashboard-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  padding: 12px;
}

.table-wrapper {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  width: 100%;
  max-width: 100%;
}

/* table */
.dashboard-table { width: max-content; min-width: 100%; border-collapse: collapse; margin-top: 8px; }
.dashboard-table th, .dashboard-table td {
  border: 1px solid #e5e7eb; padding: 8px 12px; font-size: 0.9rem; text-align: center; white-space: nowrap;
}
.dashboard-table th { cursor: pointer; }
.dashboard-table th i { font-size: 0.8rem; color: #1f2937; margin-left: 4px; }
.dashboard-table thead tr:nth-child(1) th { background: #e5e7eb; font-weight: 600; color: #1f2937; }
.dashboard-table thead tr:nth-child(2) th { background: #f3f4f6; font-weight: 600; color: #374151; }

.dashboard-table tbody td.fixed-col {
  background: #f9fafb; font-weight: 600; color: #1f2937;
}
.dashboard-table tbody td:not(.fixed-col) { background: #ffffff; color: #4b5563; }
.dashboard-table tbody tr:hover td { background: #f1f5f9; }

.cell-unassigned { background: #e5e7eb !important; color: #374151; border-color: #d1d5db !important; }
.cell-skipped { background: #fee2e2 !important; color: #991b1b; border-color: #ef4444 !important; font-weight: 600; }

.loading { text-align: center; padding: 24px; color: #6b7280; }
.no-data { text-align: center; padding: 16px; color: #6b7280; font-style: italic; }

.filter-row input {
  width: 100%; padding: 4px; box-sizing: border-box;
  border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.9rem;
}

.pagination-controls {
  display: flex; justify-content: center; gap: 8px; margin: 12px 0 0; flex-wrap: wrap;
}
.pagination-controls button {
  background: #f3f4f6; border: 1px solid #d1d5db; padding: 6px 12px; cursor: pointer; border-radius: 4px;
}
.pagination-controls button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>