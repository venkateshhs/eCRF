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
        <div
          v-if="showLegend"
          class="legend-content"
          @click.stop
        >
          <p><strong>-</strong>: No section is assigned to this subject's group for this visit.</p>
          <p><strong>(No data)</strong>: Section is assigned, but no data has been entered. Use the data entry form to add data.</p>
          <p>Data is displayed for each subject under the visit and section assigned to their group.</p>
        </div>
      </div>

      <div class="export-dropdown">
        <button class="btn-minimal" @click.stop="toggleExportMenu">
          Export <i :class="icons.export"></i>
        </button>
        <div
          v-if="showExportMenu"
          class="export-menu"
          @click.stop
        >
          <button @click="exportCSV">Download CSV</button>
          <button @click="exportExcel">Download Excel</button>
        </div>
      </div>
    </div>

    <div class="table-wrapper">
      <table class="dashboard-table">
        <thead>
          <!-- First header row: Subject ID, Visit, then each section title spanning its fields -->
          <tr>
            <th rowspan="2" @click="sortTable('subjectId')">
              Subject ID
              <i :class="sortConfig.key === 'subjectId' && sortConfig.direction === 'desc' ? icons.toggleDown : icons.toggleUp"></i>
            </th>
            <th rowspan="2" @click="sortTable('visit')">
              Visit
              <i :class="sortConfig.key === 'visit' && sortConfig.direction === 'desc' ? icons.toggleDown : icons.toggleUp"></i>
            </th>
            <template v-for="(section, sIdx) in sections" :key="'hdr-sec-'+sIdx">
              <th :colspan="fieldsPerSection[sIdx]">{{ section.title }}</th>
            </template>
          </tr>
          <!-- Second header row: field labels and filters -->
          <tr>
            <template v-for="(section, sIdx) in sections" :key="'hdr-fld-'+sIdx">
              <template v-for="(field, fIdx) in section.fields" :key="'hdr-fld-'+sIdx+'-'+fIdx">
                <th @click="sortTable(`s${sIdx}_f${fIdx}`)">
                  {{ field.label }}
                  <i :class="sortConfig.key === `s${sIdx}_f${fIdx}` && sortConfig.direction === 'desc' ? icons.toggleDown : icons.toggleUp"></i>
                </th>
              </template>
            </template>
          </tr>
          <!-- Filter row: Inputs for each column -->
          <tr class="filter-row">
            <th><input v-model="filters.subjectId" placeholder="Filter Subject ID"></th>
            <th><input v-model="filters.visit" placeholder="Filter Visit"></th>
            <template v-for="(section, sIdx) in sections" :key="'filter-sec-'+sIdx">
              <template v-for="(field, fIdx) in section.fields" :key="'filter-fld-'+sIdx+'-'+fIdx">
                <th><input v-model="filters[`s${sIdx}_f${fIdx}`]" :placeholder="`Filter ${field.label}`"></th>
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
                  <td>{{ row[`s${sIdx}_f${fIdx}`] }}</td>
                </template>
              </template>
            </tr>
          </template>
        </tbody>
      </table>
      <!-- Pagination controls -->
      <div class="pagination-controls">
        <button :disabled="currentPage === 1" @click="currentPage = 1">First</button>
        <button :disabled="currentPage === 1" @click="currentPage--">Previous</button>
        <span>Page {{ currentPage }} of {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="currentPage++">Next</button>
        <button :disabled="currentPage === totalPages" @click="currentPage = totalPages">Last</button>
        <select v-model="pageSize">
          <option :value="5">5 per page</option>
          <option :value="10">10 per page</option>
          <option :value="20">20 per page</option>
        </select>
      </div>
    </div>

    <div v-if="!entries.length" class="no-data">
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
      entries: [],
      showExportMenu: false,
      showLegend: false,
      token: this.$store.state.token,
      icons,
      sortConfig: { key: 'subjectId', direction: 'asc' },
      filters: { subjectId: '', visit: '' },
      currentPage: 1,
      pageSize: 10,
    };
  },
  computed: {
    visits() {
      const visits = this.study?.content.study_data.visits || [];
      console.log('Computed visits:', visits);
      return visits;
    },
    sections() {
      const sections = this.study?.content.study_data.selectedModels || [];
      console.log('Computed sections:', sections);
      return sections;
    },
    subjects() {
      const subjects = this.study?.content.study_data.subjects || [];
      console.log('Computed subjects:', subjects);
      return subjects;
    },
    fieldsPerSection() {
      const fields = this.sections.map(sec => sec.fields?.length || 0);
      console.log('Computed fields per section:', fields);
      return fields;
    },
    filteredData() {
      let data = [];
      this.subjects.forEach((subject, subjIdx) => {
        const groupIdx = this.resolveGroup(subjIdx);
        this.visits.forEach((visit, vIdx) => {
          const row = {
            subjectId: subject.id,
            visit: visit.name,
          };
          this.sections.forEach((section, sIdx) => {
            const isAssigned = this.study.content.study_data.assignments?.[sIdx]?.[vIdx]?.[groupIdx] || false;
            section.fields.forEach((field, fIdx) => {
              const value = isAssigned ? this.getValue(subjIdx, vIdx, sIdx, fIdx) || '(No data)' : '-';
              row[`s${sIdx}_f${fIdx}`] = value;
            });
          });
          data.push(row);
        });
      });

      // Apply filters
      data = data.filter(row => {
        if (this.filters.subjectId && !String(row.subjectId).toLowerCase().includes(this.filters.subjectId.toLowerCase())) return false;
        if (this.filters.visit && !String(row.visit).toLowerCase().includes(this.filters.visit.toLowerCase())) return false;
        for (const key in this.filters) {
          if (key !== 'subjectId' && key !== 'visit' && this.filters[key]) {
            if (!String(row[key] || '').toLowerCase().includes(this.filters[key].toLowerCase())) return false;
          }
        }
        return true;
      });

      // Apply sorting
      if (this.sortConfig.key) {
        const key = this.sortConfig.key;
        const direction = this.sortConfig.direction === 'asc' ? 1 : -1;
        data.sort((a, b) => {
          let valA = a[key] || '';
          let valB = b[key] || '';
          if (valA === '-' && valB !== '-') return 1 * direction;
          if (valB === '-' && valA !== '-') return -1 * direction;
          if (valA === '(No data)' && valB !== '(No data)') return 1 * direction;
          if (valB === '(No data)' && valA !== '(No data)') return -1 * direction;
          valA = String(valA).toLowerCase();
          valB = String(valB).toLowerCase();
          return valA < valB ? -1 * direction : valA > valB ? 1 * direction : 0;
        });
        console.log('Sorted table data:', { key, direction, data });
      } else {
        console.log('Unsorted table data:', data);
      }

      return data;
    },
    totalPages() {
      const total = Math.ceil(this.filteredData.length / this.pageSize);
      console.log('Computed total pages:', total);
      return total;
    },
    paginatedData() {
      const start = (this.currentPage - 1) * this.pageSize;
      const paginated = this.filteredData.slice(start, start + this.pageSize);
      console.log('Paginated data:', { page: this.currentPage, pageSize: this.pageSize, start, end: start + this.pageSize, data: paginated });
      return paginated;
    },
  },
  watch: {
    pageSize() {
      this.currentPage = 1; // Reset to first page on page size change
      console.log('Page size changed:', this.pageSize);
    },
    filters: {
      handler() {
        this.currentPage = 1; // Reset to first page on filter change
        console.log('Filters changed:', this.filters);
      },
      deep: true,
    },
  },
  created() {
    const studyId = this.$route.params.id;
    console.log('Fetching data for studyId:', studyId, 'Token:', this.token);
    Promise.all([
      axios.get(`http://localhost:8000/forms/studies/${studyId}`, {
        headers: { Authorization: `Bearer ${this.token}` },
      }),
      axios.get(`http://localhost:8000/forms/studies/${studyId}/data_entries`, {
        headers: { Authorization: `Bearer ${this.token}` },
      }),
    ])
      .then(([studyResp, entriesResp]) => {
        console.log('Study response:', studyResp.data);
        console.log('Entries response:', entriesResp.data);
        this.study = studyResp.data;
        this.entries = entriesResp.data;
        // Initialize dynamic filters for section fields
        this.sections.forEach((section, sIdx) => {
          section.fields.forEach((_, fIdx) => {
            this.filters[`s${sIdx}_f${fIdx}`] = '';
          });
        });
        console.log('Initialized filters:', this.filters);
      })
      .catch(err => {
        console.error('Failed to load dashboard data:', err);
        if (err.response && err.response.status === 401) {
          console.log('Unauthorized, redirecting to login');
          this.$router.push({ name: 'Login' });
        } else {
          console.error('Error details:', err.response?.data || err);
          alert('Could not load study data');
        }
      });
  },
  methods: {
    goBack() {
      this.$router.push({ name: 'Dashboard', query: { openStudies: 'true' } });
    },
    toggleExportMenu() {
      this.showExportMenu = !this.showExportMenu;
    },
    resolveGroup(subjIdx) {
      const subjGroup = (this.subjects[subjIdx]?.group || '').trim().toLowerCase();
      const grpList = this.study?.content.study_data.groups || [];
      const idx = grpList.findIndex(g => (g.name || '').trim().toLowerCase() === subjGroup);
      const groupIdx = idx >= 0 ? idx : 0;
      console.log('Resolved group:', { subjectId: this.subjects[subjIdx]?.id, subjGroup, groupIdx, groups: grpList });
      return groupIdx;
    },
    getValue(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.entries.find(e =>
        e.subject_index === subjIdx &&
        e.visit_index === visitIdx &&
        e.group_index === groupIdx
      );
      console.log('Fetching value:', {
        subjectId: this.subjects[subjIdx]?.id,
        visitIdx,
        sectionIdx,
        fieldIdx,
        groupIdx,
        entryExists: !!entry,
      });
      if (!entry || !Array.isArray(entry.data)) return '';
      const section = entry.data[sectionIdx] || [];
      const value = section[fieldIdx] != null ? section[fieldIdx] : '';
      console.log('Value retrieved:', { fieldKey: `s${sectionIdx}_f${fieldIdx}`, value });
      return value;
    },
    sortTable(key) {
      console.log('Sorting table:', { key, currentSort: this.sortConfig });
      if (this.sortConfig.key === key) {
        this.sortConfig.direction = this.sortConfig.direction === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortConfig = { key, direction: 'asc' };
      }
      this.currentPage = 1; // Reset to first page on sort change
    },
    exportCSV() {
      const quote = v => `"${String(v).replace(/"/g, '""')}"`;
      const rows = [];

      // Header rows
      const hdr1 = ['Subject ID', 'Visit', ...this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))];
      const hdr2 = ['', '', ...this.sections.flatMap(sec => sec.fields.map(f => f.label))];

      console.log('Export CSV headers:', { hdr1, hdr2 });
      rows.push(hdr1.map(quote).join(','));
      rows.push(hdr2.map(quote).join(','));

      // Data rows (use filtered data)
      this.filteredData.forEach(row => {
        const cells = [row.subjectId, row.visit];
        this.sections.forEach((section, sIdx) => {
          section.fields.forEach((_, fIdx) => {
            cells.push(row[`s${sIdx}_f${fIdx}`]);
          });
        });
        rows.push(cells.map(quote).join(','));
      });

      const blob = new Blob([rows.join('\r\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.study.metadata.study_name || 'study'}_data.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showExportMenu = false;
    },
    exportExcel() {
      const quote = v => `"${String(v).replace(/"/g, '""')}"`;
      const rows = [];

      // Header rows
      const hdr1 = ['Subject ID', 'Visit', ...this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))];
      const hdr2 = ['', '', ...this.sections.flatMap(sec => sec.fields.map(f => f.label))];

      console.log('Export Excel headers:', { hdr1, hdr2 });
      rows.push(hdr1.map(quote).join(','));
      rows.push(hdr2.map(quote).join(','));

      // Data rows (use filtered data)
      this.filteredData.forEach(row => {
        const cells = [row.subjectId, row.visit];
        this.sections.forEach((section, sIdx) => {
          section.fields.forEach((_, fIdx) => {
            cells.push(row[`s${sIdx}_f${fIdx}`]);
          });
        });
        rows.push(cells.map(quote).join(','));
      });

      const blob = new Blob([rows.join('\r\n')], { type: 'application/vnd.ms-excel' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.study.metadata.study_name || 'study'}_data.xls`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showExportMenu = false;
    },
  },
};
</script>

<style scoped>
.dashboard-header-controls {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.dashboard-header-controls .btn-minimal {
  justify-self: start;
}

.dashboard-header-controls .export-dropdown {
  justify-self: end;
  position: relative;
}

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

.btn-minimal:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #1f2937;
}

.icon-only {
  padding: 6px;
  font-size: 1rem;
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
  min-width: 200px;
}

.export-menu button {
  display: block;
  width: 100%;
  padding: 8px 16px;
  background: none;
  border: none;
  text-align: left;
  font-size: 0.9rem;
  cursor: pointer;
}

.export-menu button:hover {
  background: #f3f4f6;
}

.legend-content p {
  font-size: 0.9rem;
  color: #4b5563;
  margin: 0 0 8px;
}

.table-wrapper {
  overflow-x: auto;
  width: 100% !important;
  max-width: 100% !important;
}

.dashboard-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}

.dashboard-table th,
.dashboard-table td {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  font-size: 0.9rem;
  text-align: center;
}

.dashboard-table th {
  cursor: pointer;
  white-space: nowrap;
}

.dashboard-table th i {
  font-size: 0.8rem;
  color: #1f2937;
  margin-left: 4px;
}

.dashboard-table thead tr:nth-child(1) th {
  background: #e5e7eb;
  font-weight: 600;
  color: #1f2937;
}

.dashboard-table thead tr:nth-child(2) th {
  background: #f3f4f6;
  font-weight: 600;
  color: #374151;
}

.dashboard-table tbody td:first-child,
.dashboard-table tbody td:nth-child(2) {
  background: #f9fafb;
  font-weight: 600;
  color: #1f2937;
}

.dashboard-table tbody td:not(:first-child):not(:nth-child(2)) {
  background: #ffffff;
  color: #4b5563;
}

.dashboard-table tbody tr:hover td {
  background: #f1f5f9;
}

.loading {
  text-align: center;
  padding: 24px;
  color: #6b7280;
}

.no-data {
  text-align: center;
  padding: 16px;
  color: #6b7280;
  font-style: italic;
}

.filter-row input {
  width: 100%;
  padding: 4px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
}

.pagination-controls button {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 4px;
}

.pagination-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-controls select {
  border: 1px solid #d1d5db;
  padding: 6px;
  border-radius: 4px;
}
</style>