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
            <th rowspan="2">Subject ID</th>
            <th rowspan="2">Visit</th>
            <template v-for="(section, sIdx) in sections" :key="'hdr-sec-'+sIdx">
              <th :colspan="fieldsPerSection[sIdx]">{{ section.title }}</th>
            </template>
          </tr>
          <!-- Second header row: field labels -->
          <tr>
            <template v-for="(section, sIdx) in sections" :key="'hdr-fld-'+sIdx">
              <template v-for="(field, fIdx) in section.fields" :key="'hdr-fld-'+sIdx+'-'+fIdx">
                <th>{{ field.label }}</th>
              </template>
            </template>
          </tr>
        </thead>
        <tbody>
          <template v-for="(subject, subjIdx) in subjects" :key="'subject-'+subjIdx">
            <template v-for="(visit, vIdx) in visits" :key="'row-'+subjIdx+'-v'+vIdx">
              <tr>
                <td>{{ subject.id }}</td>
                <td>{{ visit.name }}</td>
                <template v-for="(section, sIdx) in sections" :key="'row-'+subjIdx+'-v'+vIdx+'-s'+sIdx">
                  <template v-if="study.content.study_data.assignments[sIdx]?.[vIdx]?.[ resolveGroup(subjIdx) ]">
                    <td
                      v-for="(field, fIdx) in section.fields"
                      :key="'cell-'+subjIdx+'-'+vIdx+'-'+sIdx+'-'+fIdx"
                    >
                      {{ getValue(subjIdx, vIdx, sIdx, fIdx) || '(No data)' }}
                    </td>
                  </template>
                  <template v-else>
                    <td
                      v-for="(_f, fIdx) in section.fields"
                      :key="'empty-'+subjIdx+'-'+vIdx+'-'+sIdx+'-'+fIdx"
                    >-</td>
                  </template>
                </template>
              </tr>
            </template>
          </template>
        </tbody>
      </table>
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
      showLegend: false, // Default to collapsed
      token: this.$store.state.token,
      icons
    };
  },
  computed: {
    visits() {
      return this.study.content.study_data.visits || [];
    },
    sections() {
      return this.study.content.study_data.selectedModels || [];
    },
    subjects() {
      return this.study.content.study_data.subjects || [];
    },
    fieldsPerSection() {
      return this.sections.map(sec => sec.fields.length);
    }
  },
  created() {
    const studyId = this.$route.params.id;
    Promise.all([
      axios.get(`http://localhost:8000/forms/studies/${studyId}`, {
        headers: { Authorization: `Bearer ${this.token}` }
      }),
      axios.get(`http://localhost:8000/forms/studies/${studyId}/data_entries`, {
        headers: { Authorization: `Bearer ${this.token}` }
      })
    ])
    .then(([studyResp, entriesResp]) => {
      this.study = studyResp.data;
      this.entries = entriesResp.data;
    })
    .catch(err => {
      // if token expired or invalid, go back to login
      if (err.response && err.response.status === 401) {
        this.$router.push({ name: 'Login' });
      } else {
        console.error('Failed to load dashboard data', err);
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
      const subjGroup = (this.subjects[subjIdx].group || '').trim().toLowerCase();
      const grpList = this.study.content.study_data.groups || [];
      const idx = grpList.findIndex(g => (g.name||'').trim().toLowerCase() === subjGroup);
      return idx >= 0 ? idx : 0;
    },
    getValue(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const entry = this.entries.find(e =>
        e.subject_index === subjIdx &&
        e.visit_index    === visitIdx &&
        e.group_index    === this.resolveGroup(subjIdx)
      );
      if (!entry || !Array.isArray(entry.data)) return '';
      const section = entry.data[sectionIdx] || [];
      return section[fieldIdx] != null ? section[fieldIdx] : '';
    },
    exportCSV() {
      const quote = v => `"${String(v).replace(/"/g,'""')}"`;

      const hdr1 = [
        'Subject ID',
        ...this.visits.flatMap(v => Array(this.totalFieldsPerVisit).fill(v.name))
      ];
      const hdr2 = [
        ...this.visits.flatMap(() =>
          this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))
        )
      ];
      const hdr3 = [
        ...this.visits.flatMap(() =>
          this.sections.flatMap(sec => sec.fields.map(f => f.label))
        )
      ];

      const rows = [
        hdr1.map(quote).join(','),
        hdr2.map(quote).join(','),
        hdr3.map(quote).join(',')
      ];

      this.subjects.forEach((subj, subjIdx) => {
        const cells = [subj.id];
        this.visits.forEach((_, vIdx) => {
          this.sections.forEach((_, sIdx) => {
            this.sections[sIdx].fields.forEach((_, fIdx) => {
              cells.push(this.getValue(subjIdx, vIdx, sIdx, fIdx));
            });
          });
        });
        rows.push(cells.map(quote).join(','));
      });

      const blob = new Blob([rows.join('\r\n')], { type: 'text/csv' });
      const url  = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href     = url;
      a.download = `${this.study.metadata.study_name || 'study'}_data.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showExportMenu = false;
    },
    exportExcel() {
      const quote = v => `"${String(v).replace(/"/g,'""')}"`;
      const rows = [];

      rows.push(
        ['Subject ID', ...this.visits.flatMap(v => Array(this.totalFieldsPerVisit).fill(v.name))]
          .map(quote).join(',')
      );
      rows.push(
        [...this.visits.flatMap(() =>
          this.sections.flatMap((s, i) => Array(this.fieldsPerSection[i]).fill(s.title))
        )]
        .map(quote).join(',')
      );
      rows.push(
        [...this.visits.flatMap(() =>
          this.sections.flatMap(sec => sec.fields.map(f => f.label))
        )]
        .map(quote).join(',')
      );

      this.subjects.forEach((subj, subjIdx) => {
        const cells = [subj.id];
        this.visits.forEach((_, vIdx) => {
          this.sections.forEach((_, sIdx) => {
            this.sections[sIdx].fields.forEach((_, fIdx) => {
              cells.push(this.getValue(subjIdx, vIdx, sIdx, fIdx));
            });
          });
        });
        rows.push(cells.map(quote).join(','));
      });

      const blob = new Blob([rows.join('\r\n')], { type: 'application/vnd.ms-excel' });
      const url  = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href     = url;
      a.download = `${this.study.metadata.study_name || 'study'}_data.xls`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showExportMenu = false;
    }
  }
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
}

.dashboard-table thead tr:nth-child(1) th {
  background: #e5e7eb;
  font-weight: 600;
  text-align: center;
  color: #1f2937;
}

.dashboard-table thead tr:nth-child(2) th {
  background: #f3f4f6;
  font-weight: 600;
  text-align: center;
  color: #374151;
}

.dashboard-table thead tr:nth-child(3) th {
  background: #f9fafb;
  font-weight: 500;
  text-align: center;
  color: #4b5563;
}

.dashboard-table tbody td:first-child {
  background: #f9fafb;
  font-weight: 600;
  color: #1f2937;
}

.dashboard-table tbody td:not(:first-child) {
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
</style>
