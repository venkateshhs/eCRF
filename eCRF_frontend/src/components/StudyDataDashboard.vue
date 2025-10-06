<template>
  <div class="study-dashboard-container" v-if="study">
    <!-- header controls -->
    <div class="dashboard-header-controls">
      <button class="btn-minimal" @click="goBack">
        Back
      </button>
      <h2 class="dashboard-title">{{ study.metadata.study_name }}</h2>

      <div class="legend-dropdown">
        <button class="btn-minimal icon-only" @click="showLegend = !showLegend" title="Table Legend">
          <i :class="icons.info"></i>
        </button>
        <div v-if="showLegend" class="legend-content" @click.stop>
          <p><strong>-</strong>: No section is assigned to this subject's group for this visit.</p>
          <p><strong>(No data)</strong>: Section is assigned, but no data has been entered. Use the data entry form to add data.</p>
          <p>
            <span class="legend-swatch cell-skipped"></span>
            <strong>Red cell</strong>: Required field was <em>skipped</em> when saving.
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
      <table class="dashboard-table">
        <thead>
          <tr>
            <th rowspan="2" @click="sortTable('subjectId')">
              Subject ID
              <i :class="sortIcon('subjectId')"></i>
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
            <th><input v-model="filters.visit" placeholder="Filter Visit"></th>
            <template v-for="(section, sIdx) in sections" :key="'filter-sec-'+sIdx">
              <template v-for="(field, fIdx) in section.fields" :key="'filter-fld-'+sIdx+'-'+fIdx">
                <th><input v-model="filters[`s${sIdx}_f${fIdx}`]" :placeholder="`Filter ${field.label || field.name || field.title || (fIdx+1)}`"></th>
              </template>
            </template>
          </tr>
        </thead>
        <tbody>
          <template v-for="(row, rowIdx) in paginatedData" :key="'row-'+rowIdx">
            <tr>
              <td>{{ row.subjectId }}</td>
              <td>{{ row.visit }}</td>
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

      <div class="pagination-controls" v-if="!viewAll">
        <button :disabled="currentPage === 1" @click="goFirst">First</button>
        <button :disabled="currentPage === 1" @click="goPrev">Previous</button>
        <span>Page {{ currentPage }} of {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="goNext">Next</button>
        <button :disabled="currentPage === totalPages" @click="goLast">Last</button>
      </div>
    </div>

    <div v-if="!filteredData.length" class="no-data">
      No data entries found. Please enter data for the assigned sections using the data entry form.
    </div>
  </div>

  <div v-else class="loading">
    Loading study data…
  </div>
</template>

<script>
import axios from 'axios';
import icons from "@/assets/styles/icons"; // eslint-disable-line no-unused-vars

export default {
  name: 'StudyDataDashboard',
  data() {
    return {
      study: null,

      // entries for the current page (or all if viewAll)
      entries: [],
      totalEntries: 0, // informational

      showExportMenu: false,
      showLegend: false,
      token: this.$store.state.token,
      icons,

      sortConfig: { key: 'subjectId', direction: 'asc' },
      filters: { subjectId: '', visit: '' },

      // paging
      currentPage: 1,
      pageSize: 50,
      VIEW_ALL_MAX_ROWS: 1000,
      viewAll: false,
      isLoadingEntries: false,

      // debug (no leading underscores to satisfy vue/no-reserved-keys)
      debugOnce: { study:false, fetch:false, entryShape:false },
    };
  },
  computed: {
    visits() {
      return this.study?.content?.study_data?.visits || [];
    },
    sections() {
      return this.study?.content?.study_data?.selectedModels || [];
    },
    subjects() {
      return this.study?.content?.study_data?.subjects || [];
    },
    fieldsPerSection() {
      return this.sections.map(sec => sec.fields?.length || 0);
    },

    totalGridRows() {
      return (this.subjects?.length || 0) * (this.visits?.length || 0);
    },
    canViewAll() {
      return this.totalGridRows > 0 && this.totalGridRows <= this.VIEW_ALL_MAX_ROWS;
    },

    filteredData() {
      let data = [];
      const { subjectIdxPageSet, visitIdxPageSet } = this.currentWindowIndexSets();

      this.subjects.forEach((subject, subjIdx) => {
        if (!subjectIdxPageSet.has(subjIdx)) return;

        const groupIdx = this.resolveGroup(subjIdx);
        this.visits.forEach((visit, vIdx) => {
          if (!visitIdxPageSet.has(vIdx)) return;

          const row = { subjectId: subject.id, visit: visit.name, __sIdx: subjIdx, __vIdx: vIdx };
          this.sections.forEach((section, sIdx) => {
            const assigned = this.isAssigned(sIdx, vIdx, groupIdx);
            section.fields.forEach((field, fIdx) => {
              let value;
              if (!assigned) {
                value = '-';
              } else {
                const raw = this.getValue(subjIdx, vIdx, sIdx, fIdx);
                if ((field.type || '').toLowerCase() === 'checkbox') {
                  value = (raw === true) ? 'Yes'
                        : (raw === false) ? 'No'
                        : '(No data)';
                } else {
                  value = (raw == null || raw === '') ? '(No data)' : raw;
                }
              }
              row[`s${sIdx}_f${fIdx}`] = value;
            });
          });
          data.push(row);
        });
      });

      // Column filters
      data = data.filter(row => {
        if (this.filters.subjectId && !String(row.subjectId).toLowerCase().includes(this.filters.subjectId.toLowerCase())) return false;
        if (this.filters.visit && !String(row.visit).toLowerCase().includes(this.filters.visit.toLowerCase())) return false;

        for (const key in this.filters) {
          if (key === 'subjectId' || key === 'visit') continue;
          const filterVal = this.filters[key];
          if (filterVal && !String(row[key] ?? '').toLowerCase().includes(String(filterVal).toLowerCase())) {
            return false;
          }
        }
        return true;
      });

      // Sorting
      if (this.sortConfig.key) {
        const key = this.sortConfig.key;
        const dir = this.sortConfig.direction === 'asc' ? 1 : -1;
        data.sort((a, b) => {
          let valA = a[key] ?? '';
          let valB = b[key] ?? '';
          if (valA === '-' && valB !== '-') return 1 * dir;
          if (valB === '-' && valA !== '-') return -1 * dir;
          if (valA === '(No data)' && valB !== '(No data)') return 1 * dir;
          if (valB === '(No data)' && valA !== '(No data)') return -1 * dir;
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
  },
  created() {
    this.bootstrap();
  },
  methods: {
    // ---- debug helpers ----
    dbg(...args){ console.log('[Dashboard]', ...args); },
    groupDbg(label, obj){ console.groupCollapsed('[Dashboard]', label); console.log(obj); console.groupEnd(); },
    normalizeKey(k){ return String(k || '').trim().toLowerCase(); },
    listKeys(obj){ return Object.keys(obj || {}); },

    // ---- dict helpers (section/field keys consistent with save) ----
    sectionDictKey(sectionObj) {
      return sectionObj?.title ?? '';
    },
    fieldDictKey(fieldObj, fallbackIndex) {
      // include 'id' fallback
      return fieldObj?.name ?? fieldObj?.key ?? fieldObj?.id ?? fieldObj?.label ?? fieldObj?.title ?? `f${fallbackIndex}`;
    },
    // tolerant getter: exact match, else case/trim-insensitive fallback (logs on miss)
    dictRead(dataDict, sIdx, fIdx) {
      if (!dataDict || typeof dataDict !== 'object' || Array.isArray(dataDict)) return undefined;

      const sec = this.sections[sIdx];
      const fld = sec?.fields?.[fIdx];

      const sKey = this.sectionDictKey(sec);
      const fKey = this.fieldDictKey(fld, fIdx);

      let secObj = dataDict[sKey];
      // fallback section key (case/trim-insensitive)
      if (!secObj) {
        const wanted = this.normalizeKey(sKey);
        const hitKey = Object.keys(dataDict).find(k => this.normalizeKey(k) === wanted);
        if (hitKey) {
          secObj = dataDict[hitKey];
          this.dbg('Section key fallback used:', { expected: sKey, matched: hitKey });
        }
      }
      if (!secObj || typeof secObj !== 'object') {
        this.dbg('dictRead: section not found', { sIdx, sKey, available: this.listKeys(dataDict) });
        return undefined;
      }

      if (Object.prototype.hasOwnProperty.call(secObj, fKey)) return secObj[fKey];

      // fallback field key (case/trim-insensitive)
      const wantedField = this.normalizeKey(fKey);
      const hitField = Object.keys(secObj).find(k => this.normalizeKey(k) === wantedField);
      if (hitField) {
        this.dbg('Field key fallback used:', { sKey, expectedField: fKey, matchedField: hitField });
        return secObj[hitField];
      }

      this.dbg('dictRead: field not found', {
        sIdx, fIdx, sKey, fKey,
        availableFields: this.listKeys(secObj)
      });
      return undefined;
    },

    async bootstrap() {
      const studyId = this.$route.params.id;
      try {
        const studyResp = await axios.get(`/forms/studies/${studyId}`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.study = studyResp.data;

        if (!this.debugOnce.study) {
          this.debugOnce.study = true;
          this.groupDbg('Study loaded', {
            studyId,
            subjects: this.subjects.length,
            visits: this.visits.length,
            sections: this.sections.map((s, i) => ({
              i, title: s.title,
              fieldKeys: (s.fields || []).map((f, j) => this.fieldDictKey(f, j))
            })),
            assignmentsShape: {
              m: this.sections.length,
              v: this.visits.length,
              g: (this.study?.content?.study_data?.groups || []).length
            }
          });
        }

        // Initialize dynamic filters
        this.sections.forEach((section, sIdx) => {
          section.fields.forEach((_, fIdx) => {
            if (!this.filters[`s${sIdx}_f${fIdx}`]) this.filters[`s${sIdx}_f${fIdx}`] = '';
          });
        });

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
      const studyId = this.$route.params.id;

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

      const url = `/forms/studies/${studyId}/data_entries` + (params.toString() ? `?${params.toString()}` : '');

      try {
        this.isLoadingEntries = true;
        if (!this.debugOnce.fetch) {
          this.debugOnce.fetch = true;
          this.dbg('Fetching entries…', { url, viewAll: this.viewAll, subject_indexes, visit_indexes });
        }
        const resp = await axios.get(url, { headers: { Authorization: `Bearer ${this.token}` } });
        const payload = Array.isArray(resp.data) ? { entries: resp.data, total: resp.data.length } : (resp.data || {});
        this.entries = payload.entries || [];
        this.totalEntries = payload.total ?? this.entries.length;

        if (!this.debugOnce.entryShape) {
          this.debugOnce.entryShape = true;
          const sample = (this.entries || []).slice(0, 3).map(e => ({
            id: e.id,
            s: e.subject_index, v: e.visit_index, g: e.group_index,
            dataType: Array.isArray(e.data) ? 'array' : (e.data && typeof e.data === 'object') ? 'dict' : typeof e.data,
            topKeys: e.data && typeof e.data === 'object' && !Array.isArray(e.data) ? Object.keys(e.data) : null
          }));
          this.groupDbg('Entries fetched', {
            count: this.entries.length,
            sample
          });
          if (sample[0]?.topKeys) {
            this.dbg('First entry dict section keys:', sample[0].topKeys);
          }
        }

      } catch (err) {
        console.error('Failed to load entries:', err);
        this.entries = [];
      } finally {
        this.isLoadingEntries = false;
      }
    },

    goBack() {
      const id = this.$route.params.id;
      this.$router.push({ name: "StudyView", params: { id } });
    },
    toggleExportMenu() {
      this.showExportMenu = !this.showExportMenu;
    },

    // --- helpers to resolve & read data ---
    resolveGroup(subjIdx) {
      const subjGroup = (this.subjects[subjIdx]?.group || '').trim().toLowerCase();
      const grpList = this.study?.content?.study_data?.groups || [];
      const idx = grpList.findIndex(g => (g.name || '').trim().toLowerCase() === subjGroup);
      if (idx < 0) {
        this.dbg('resolveGroup: subject group not found, defaulting to 0', {
          subjectIndex: subjIdx, subjectGroup: subjGroup, availableGroups: grpList.map(g => g.name)
        });
      }
      return idx >= 0 ? idx : 0;
    },
    isAssigned(sectionIdx, visitIdx, groupIdx) {
      const ok = !!(this.study?.content?.study_data?.assignments?.[sectionIdx]?.[visitIdx]?.[groupIdx]);
      if (!ok && (sectionIdx === 0) && (visitIdx === 0) && (groupIdx === 0)) {
        this.dbg('isAssigned=false example', { sectionIdx, visitIdx, groupIdx });
      }
      return ok;
    },
    findEntry(subjIdx, visitIdx, groupIdx) {
      const e = (this.entries || []).find(e =>
        e.subject_index === subjIdx &&
        e.visit_index === visitIdx &&
        e.group_index === groupIdx
      ) || null;
      if (!e) {
        if (subjIdx === 0 && visitIdx === 0 && groupIdx === 0) {
          this.dbg('findEntry: no entry for (s,v,g)', { subjIdx, visitIdx, groupIdx, entries: this.entries.length });
        }
      }
      return e;
    },
    getValue(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.findEntry(subjIdx, visitIdx, groupIdx);
      if (!entry || !entry.data) return '';
      // Primary: dict
      const d = entry.data;
      if (!Array.isArray(d)) {
        const v = this.dictRead(d, sectionIdx, fieldIdx);
        return v != null ? v : '';
      }
      // Fallback (old rows): list-of-lists
      const section = Array.isArray(d) ? (d[sectionIdx] || []) : [];
      return section[fieldIdx] != null ? section[fieldIdx] : '';
    },
    isCellSkipped(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.findEntry(subjIdx, visitIdx, groupIdx);
      if (!entry) return false;
      const flags = entry.skipped_required_flags;
      return !!(Array.isArray(flags) &&
                Array.isArray(flags[sectionIdx]) &&
                flags[sectionIdx][fieldIdx] === true);
    },
    cellClass(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      return {
        'cell-skipped': this.isCellSkipped(subjIdx, visitIdx, sectionIdx, fieldIdx),
      };
    },

    // Sorting
    sortTable(key) {
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

    // Paging helpers
    goFirst() { this.currentPage = 1; },
    goPrev()  { if (this.currentPage > 1) this.currentPage--; },
    goNext()  { if (this.currentPage < this.totalPages) this.currentPage++; },
    goLast()  { this.currentPage = this.totalPages; },

    // Exports
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
      const studyId = this.$route.params.id;

      let entriesForExport = this.entries;

      if (!this.viewAll && !this.canViewAll) {
        try {
          const resp = await axios.get(
            `/forms/studies/${studyId}/data_entries?all=true`,
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          const payload = Array.isArray(resp.data) ? { entries: resp.data } : (resp.data || {});
          entriesForExport = payload.entries || [];
        } catch (e) {
          console.error('Failed to fetch all entries for export, using current page only.', e);
        }
      }

      // Temporarily swap this.entries to build full rows, then restore
      const original = this.entries;
      this.entries = entriesForExport;

      const rows = [];
      this.subjects.forEach((subject, subjIdx) => {
        const groupIdx = this.resolveGroup(subjIdx);
        this.visits.forEach((visit, vIdx) => {
          const row = { subjectId: subject.id, visit: visit.name };
          this.sections.forEach((section, sIdx) => {
            const assigned = this.isAssigned(sIdx, vIdx, groupIdx);
            section.fields.forEach((field, fIdx) => {
              let value;
              if (!assigned) {
                value = '-';
              } else {
                const raw = this.getValue(subjIdx, vIdx, sIdx, fIdx);
                if ((field.type || '').toLowerCase() === 'checkbox') {
                  value = (raw === true) ? 'Yes'
                        : (raw === false) ? 'No'
                        : '(No data)';
                } else {
                  value = (raw == null || raw === '') ? '(No data)' : raw;
                }
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
      const hdr1 = ['Subject ID', 'Visit', ...this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))];
      const hdr2 = ['', '', ...this.sections.flatMap(sec => sec.fields.map(f => f.label || f.name || f.title))];

      const lines = [];
      lines.push(hdr1.map(quote).join(','));
      lines.push(hdr2.map(quote).join(','));

      // Apply current filters to exported rows as well
      const filteredRows = rows.filter(row => {
        if (this.filters.subjectId && !String(row.subjectId).toLowerCase().includes(this.filters.subjectId.toLowerCase())) return false;
        if (this.filters.visit && !String(row.visit).toLowerCase().includes(this.filters.visit.toLowerCase())) return false;
        for (const key in this.filters) {
          if (key === 'subjectId' || key === 'visit') continue;
          const f = this.filters[key];
          if (f && !String(row[key] ?? '').toLowerCase().includes(String(f).toLowerCase())) return false;
        }
        return true;
      });

      filteredRows.forEach(row => {
        const cells = [row.subjectId, row.visit];
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
      a.download = `${this.study?.metadata?.study_name || 'study'}_data.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },
};
</script>

<style scoped>
/* (unchanged styles from your file) */
.dashboard-header-controls {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.dashboard-header-controls .btn-minimal { justify-self: start; }
.dashboard-header-controls .export-dropdown,
.dashboard-header-controls .legend-dropdown {
  justify-self: end;
  position: relative;
}
.dashboard-title {
  justify-self: center;
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
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
.icon-only { padding: 6px; font-size: 1rem; }

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
  border: 1px solid #ef4444;
  vertical-align: -2px;
  background: #fee2e2;
}

.table-controls {
  display: flex; justify-content: space-between; align-items: center; margin: 8px 0;
  color: #4b5563; font-size: 0.9rem;
}
.table-controls .view-all { margin-left: 12px; }

.table-wrapper { overflow-x: auto; width: 100%; max-width: 100%; }

.dashboard-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.dashboard-table th, .dashboard-table td {
  border: 1px solid #e5e7eb; padding: 8px 12px; font-size: 0.9rem; text-align: center;
}
.dashboard-table th { cursor: pointer; white-space: nowrap; }
.dashboard-table th i { font-size: 0.8rem; color: #1f2937; margin-left: 4px; }
.dashboard-table thead tr:nth-child(1) th { background: #e5e7eb; font-weight: 600; color: #1f2937; }
.dashboard-table thead tr:nth-child(2) th { background: #f3f4f6; font-weight: 600; color: #374151; }

.dashboard-table tbody td:first-child,
.dashboard-table tbody td:nth-child(2) {
  background: #f9fafb; font-weight: 600; color: #1f2937;
}
.dashboard-table tbody td:not(:first-child):not(:nth-child(2)) { background: #ffffff; color: #4b5563; }
.dashboard-table tbody tr:hover td { background: #f1f5f9; }

/* Skipped cell */
.cell-skipped {
  background: #fee2e2 !important;
  color: #991b1b;
  border-color: #ef4444 !important;
  font-weight: 600;
}

.loading { text-align: center; padding: 24px; color: #6b7280; }
.no-data { text-align: center; padding: 16px; color: #6b7280; font-style: italic; }

.filter-row input {
  width: 100%; padding: 4px; box-sizing: border-box;
  border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.9rem;
}

.pagination-controls {
  display: flex; justify-content: center; gap: 8px; margin: 12px 0 0;
}
.pagination-controls button {
  background: #f3f4f6; border: 1px solid #d1d5db; padding: 6px 12px; cursor: pointer; border-radius: 4px;
}
.pagination-controls button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
