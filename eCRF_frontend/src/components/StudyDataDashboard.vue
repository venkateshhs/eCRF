<template>
  <div class="study-dashboard-container" v-if="study">
    <!-- header controls -->
    <div class="dashboard-header-controls">
      <button class="btn-minimal" @click="goBack">
        ← Back
      </button>
      <h2 class="dashboard-title">{{ study.metadata.study_name }}</h2>
      <div class="export-dropdown">
        <!-- stop propagation here -->
        <button class="btn-minimal" @click.stop="toggleExportMenu">
          Export ▼
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
          <tr>
            <th rowspan="3">Subject ID</th>
            <th
              v-for="(visit, vIdx) in visits"
              :key="'hdr1-v'+vIdx"
              :colspan="totalFieldsPerVisit"
            >
              {{ visit.name }}
            </th>
          </tr>
          <tr>
            <template v-for="(visit, vIdx) in visits" :key="'hdr2-v'+vIdx">
              <th
                v-for="(section, sIdx) in sections"
                :key="'hdr2-v'+vIdx+'-s'+sIdx"
                :colspan="fieldsPerSection[sIdx]"
              >
                {{ section.title }}
              </th>
            </template>
          </tr>
          <tr>
            <template v-for="(visit, vIdx) in visits" :key="'hdr3-v'+vIdx">
              <template v-for="(section, sIdx) in sections" :key="'hdr3-v'+vIdx+'-s'+sIdx">
                <th
                  v-for="(field, fIdx) in section.fields"
                  :key="'hdr3-v'+vIdx+'-s'+sIdx+'-f'+fIdx"
                >
                  {{ field.label }}
                </th>
              </template>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(subject, subjIdx) in subjects" :key="'row-'+subjIdx">
            <td>{{ subject.id }}</td>
            <template
              v-for="(visit, vIdx) in visits"
              :key="'row-'+subjIdx+'-v'+vIdx"
            >
              <template
                v-for="(section, sIdx) in sections"
                :key="'row-'+subjIdx+'-v'+vIdx+'-s'+sIdx"
              >
                <td
                  v-for="(field, fIdx) in section.fields"
                  :key="'cell-'+subjIdx+'-'+vIdx+'-'+sIdx+'-'+fIdx"
                >
                  {{ getValue(subjIdx, vIdx, sIdx, fIdx) }}
                </td>
              </template>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div v-else class="loading">
    Loading study data…
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'StudyDataDashboard',
  data() {
    return {
      study: null,
      entries: [],
      showExportMenu: false,
      token: this.$store.state.token
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
    },
    totalFieldsPerVisit() {
      return this.fieldsPerSection.reduce((sum, n) => sum + n, 0);
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
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.dashboard-header-controls .btn-minimal {
  justify-self: start;
}

.dashboard-header-controls .export-dropdown {
  justify-self: end;
  /* allow absolute menu to sit here */
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
  border: 1px solid #bbb;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 0.9rem;
  color: #333;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.btn-minimal:hover {
  background: #f5f5f5;
  border-color: #999;
  color: #000;
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  z-index: 20;
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
  background: #f0f0f0;
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
  border: 1px solid #ddd;
  padding: 8px 12px;
  white-space: nowrap;
  font-size: 0.9rem;
}

.dashboard-table thead th {
  background: #fafafa;
  font-weight: 600;
  text-align: center;
}

.dashboard-table tbody tr:nth-child(odd) {
  background: #fcfcfc;
}

.dashboard-table tbody tr:hover {
  background: #f1faff;
}

.loading {
  text-align: center;
  padding: 24px;
  color: #666;
}
</style>
