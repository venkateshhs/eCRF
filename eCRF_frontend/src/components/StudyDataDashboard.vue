/* eslint-disable */
<template>
  <div class="study-dashboard-container" :class="{ embedded, fullscreen, 'has-group-column': canViewGroupColumn }"
  v-if="study">
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
            <p>
              Table fields are expanded horizontally as TableName.rowNumber.ColumnName.
            </p>
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
              <th
                class="sticky-col sticky-subject identity-header"
                @click="sortTable('subjectId')"
              >
                Subject ID
                <i :class="sortIcon('subjectId')"></i>
              </th>

              <th
                v-if="canViewGroupColumn"
                class="sticky-col sticky-group identity-header"
                @click="sortTable('group')"
              >
                Group
                <i :class="sortIcon('group')"></i>
              </th>

              <th
                class="sticky-col sticky-visit identity-header"
                @click="sortTable('visit')"
              >
                Visit
                <i :class="sortIcon('visit')"></i>
              </th>

              <template v-for="group in headerGroups" :key="'hdr-group-'+group.key">
                <th class="section-header-cell" :colspan="group.colspan">
                  <span class="section-header-label">
                    {{ group.title }}
                  </span>
                </th>
              </template>
            </tr>

            <tr>
              <th class="sticky-col sticky-subject identity-subheader"></th>

              <th
                v-if="canViewGroupColumn"
                class="sticky-col sticky-group identity-subheader"
              ></th>

              <th class="sticky-col sticky-visit identity-subheader"></th>

              <template v-for="col in dashboardColumns" :key="'hdr-col-'+col.key">
                <th @click="sortTable(col.key)">
                  {{ col.label }}
                  <i :class="sortIcon(col.key)"></i>
                </th>
              </template>
            </tr>

          <tr class="filter-row">
              <th class="sticky-col sticky-subject">
                <input v-model="filters.subjectId" placeholder="Filter Subject ID">
              </th>

              <th v-if="canViewGroupColumn" class="sticky-col sticky-group">
                <input v-model="filters.group" placeholder="Filter Group">
              </th>

              <th class="sticky-col sticky-visit">
                <input v-model="filters.visit" placeholder="Filter Visit">
              </th>

            <template v-for="col in dashboardColumns" :key="'filter-'+col.key">
              <th>
                <input
                  v-model="filters[col.key]"
                  :placeholder="`Filter ${col.label}`"
                />
              </th>
            </template>
          </tr>
        </thead>

        <tbody>
          <template v-for="(row, rowIdx) in paginatedData" :key="'row-'+rowIdx">
            <tr>
              <td class="fixed-col sticky-col sticky-subject">{{ row.subjectId }}</td>
              <td v-if="canViewGroupColumn" class="fixed-col sticky-col sticky-group">{{ row.group }}</td>
              <td class="fixed-col sticky-col sticky-visit">
                <span class="visit-cell-content">
                  <span>{{ row.visit }}</span>
                  <button
                    v-if="row.__uploadedFiles && row.__uploadedFiles.length"
                    type="button"
                    class="uploaded-files-inline-btn"
                    :title="`${row.__uploadedFiles.length} uploaded file(s)`"
                    @click.stop="openUploadedFilesDialog(row)"
                  >
                    <i class="fas fa-paperclip" aria-hidden="true"></i>
                  </button>
                </span>
              </td>

              <template v-for="col in dashboardColumns" :key="'cell-'+rowIdx+'-'+col.key">
                <td :class="dashboardCellClass(row, col)">
                  <template v-if="fileItemsForCell(row, col).length">
                    <span class="file-cell-list">
                      <span
                        v-for="(file, fileIdx) in fileItemsForCell(row, col)"
                        :key="`${col.key}-${fileIdx}-${file.dbId || file.id || file.file_id || file.displayName}`"
                        class="file-cell-item"
                      >
                        <span class="file-cell-name" :title="file.displayName">{{ file.displayName }}</span>
                        <button
                          v-if="file.downloadable"
                          type="button"
                          class="file-download-inline-btn"
                          title="Download file"
                          @click.stop="downloadUploadedFile(file)"
                        >
                          <i class="fas fa-download" aria-hidden="true"></i>
                        </button>
                      </span>
                    </span>
                  </template>
                  <template v-else>
                    {{ row[col.key] }}
                  </template>
                </td>
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

    <UploadedFilesDialog
      v-if="showUploadedFilesDialog"
      :files="uploadedFilesDialogFiles"
      :subject-label="uploadedFilesDialogSubject"
      :visit-label="uploadedFilesDialogVisit"
      @close="closeUploadedFilesDialog"
      @download-file="downloadUploadedFile"
    />
  </div>

  <div v-else class="loading">
    Loading study data…
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";
import UploadedFilesDialog from "@/components/dataentry/UploadedFilesDialog.vue";
import {
  collectUploadedFilesForSlot,
  inferUploadedFileFieldContext,
  normalizeUploadedFiles,
  uploadedFileId,
  uploadedFileName,
} from "@/utils/uploadedFiles";

export default {
  name: "StudyDataDashboard",
  components: { UploadedFilesDialog },
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

      sortConfig: { key: "subjectId", direction: "asc" },
      filters: { subjectId: "", group: "", visit: "" },

      currentPage: 1,
      pageSize: 50,
      VIEW_ALL_MAX_ROWS: 1000,
      viewAll: false,
      isLoadingEntries: false,

      studyVersions: [],
      selectedVersion: null,
      templateCache: new Map(),
      studyFiles: [],
      showUploadedFilesDialog: false,
      uploadedFilesDialogFiles: [],
      uploadedFilesDialogSubject: "",
      uploadedFilesDialogVisit: "",
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

    totalGridRows() {
      return this.baseRowsCountEstimate;
    },

    baseRowsCountEstimate() {
      return this.subjects.length * this.visits.length;
    },

    canViewAll() {
      return this.totalGridRows > 0 && this.totalGridRows <= this.VIEW_ALL_MAX_ROWS;
    },

    currentUser() {
      return this.$store.getters.getUser || {};
    },
    role() {
      return this.currentUser.profile?.role || "";
    },
    isAdmin() {
      return this.role === "Administrator";
    },
    isCreator() {
      const meta = this.study?.metadata || {};
      const createdBy = meta.created_by;
      if (createdBy == null) return false;

      const myId =
        this.currentUser?.id ??
        this.currentUser?.user_id ??
        this.currentUser?.profile?.id ??
        null;

      if (myId == null) return false;
      return String(createdBy) === String(myId);
    },
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
    canViewGroupColumn() {
      return this.isAdmin || this.isCreator || this.hasAddPermission || this.hasEditPermission;
    },

    dashboardColumns() {
      return this.buildDashboardColumns({
        entries: this.entries,
        forceAllPairs: this.viewAll,
      });
    },

    headerGroups() {
      return this.buildHeaderGroupsForColumns(this.dashboardColumns);
    },

    filteredData() {
      return this.buildDashboardRows({
        entries: this.entries,
        columns: this.dashboardColumns,
        forceAllPairs: this.viewAll,
        applyFilters: true,
        applySort: true,
      });
    },

    totalPages() {
      if (this.viewAll) return 1;
      const wholeGridPages = Math.ceil(Math.max(1, this.totalGridRows) / this.pageSize);
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
    fullscreen() {
      this.$nextTick(() => {
        this.updateStickyColumnOffsets?.();
      });
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
      },
    },
  },

  async created() {
      await this.bootstrap();
    },

  mounted() {
      this.updateStickyColumnOffsets();
      window.addEventListener("resize", this.updateStickyColumnOffsets);
    },

  updated() {
      this.$nextTick(() => {
        this.updateStickyColumnOffsets();
      });
    },

  beforeUnmount() {
      window.removeEventListener("resize", this.updateStickyColumnOffsets);
    },

  methods: {
    updateStickyColumnOffsets() {
      this.$nextTick(() => {
        const root = this.$el;
        if (!root) return;

        const table = root.querySelector(".dashboard-table");
        if (!table) return;

        const subjectCell = table.querySelector("thead .sticky-subject");
        const groupCell = table.querySelector("thead .sticky-group");
        const visitCell = table.querySelector("thead .sticky-visit");

        const headerRow1 = table.querySelector("thead tr:nth-child(1)");
        const headerRow2 = table.querySelector("thead tr:nth-child(2)");

        const subjectWidth = subjectCell
          ? Math.ceil(subjectCell.getBoundingClientRect().width)
          : 0;

        const groupWidth = groupCell && this.canViewGroupColumn
          ? Math.ceil(groupCell.getBoundingClientRect().width)
          : 0;

        const visitWidth = visitCell
          ? Math.ceil(visitCell.getBoundingClientRect().width)
          : 0;

        const row1Height = headerRow1
          ? Math.ceil(headerRow1.getBoundingClientRect().height)
          : 40;

        const row2Height = headerRow2
          ? Math.ceil(headerRow2.getBoundingClientRect().height)
          : 40;

        root.style.setProperty("--sticky-subject-left", "0px");
        root.style.setProperty("--sticky-group-left", `${subjectWidth}px`);
        root.style.setProperty("--sticky-visit-left", `${subjectWidth + groupWidth}px`);
        root.style.setProperty("--sticky-section-left", `${subjectWidth + groupWidth + visitWidth}px`);

        root.style.setProperty("--header-row-1-h", `${row1Height}px`);
        root.style.setProperty("--header-row-2-h", `${row2Height}px`);
      });
    },
    getStudyId() {
      return this.studyId != null ? String(this.studyId) : String(this.$route.params.id);
    },

    normalizeKey(k) {
      return String(k || "").trim().toLowerCase();
    },

    sectionDictKey(sectionObj) {
      return sectionObj?.title ?? "";
    },

    fieldDictKey(fieldObj, fallbackIndex) {
      return (
        fieldObj?._id ??
        fieldObj?.id ??
        fieldObj?.field_id ??
        fieldObj?.uid ??
        fieldObj?.key ??
        fieldObj?.name ??
        fieldObj?.label ??
        fieldObj?.title ??
        `f${fallbackIndex}`
      );
    },

    dictRead(dataDict, sIdx, fIdx) {
      if (!dataDict || typeof dataDict !== "object" || Array.isArray(dataDict)) return undefined;

      const sec = this.sections[sIdx];
      const fld = sec?.fields?.[fIdx];
      const sKey = this.sectionDictKey(sec);

      let secObj = dataDict[sKey];
      if (!secObj) {
        const wanted = this.normalizeKey(sKey);
        const hitKey = Object.keys(dataDict).find((k) => this.normalizeKey(k) === wanted);
        if (hitKey) secObj = dataDict[hitKey];
      }
      if (!secObj || typeof secObj !== "object") return undefined;

      const candidates = [
        fld?._id,
        fld?.id,
        fld?.field_id,
        fld?.uid,
        fld?.key,
        fld?.name,
        fld?.label,
        fld?.title,
        `f${fIdx}`,
      ].filter(Boolean);

      for (const candidate of candidates) {
        if (Object.prototype.hasOwnProperty.call(secObj, candidate)) {
          return secObj[candidate];
        }
      }

      const normalizedCandidates = candidates.map((c) => this.normalizeKey(c));
      const hitField = Object.keys(secObj).find((k) => normalizedCandidates.includes(this.normalizeKey(k)));
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
        await this.loadStudyFiles(studyId);

        this.initDynamicFilters();

        if (this.canViewAll) this.viewAll = false;
        await this.fetchPageEntries();
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
        if (err.response && err.response.status === 401) {
          this.$router.push({ name: "Login" });
        } else {
          alert("Could not load study data");
        }
      }
    },

    async loadStudyFiles(studyId) {
      if (!studyId) {
        this.studyFiles = [];
        return;
      }

      try {
        const resp = await axios.get(`/forms/studies/${studyId}/files`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.studyFiles = Array.isArray(resp.data) ? resp.data : [];
      } catch (err) {
        console.warn("Failed to load uploaded files", err?.response?.data || err.message);
        this.studyFiles = [];
      }
    },

    initDynamicFilters() {
      const base = {
        subjectId: this.filters.subjectId || "",
        group: this.filters.group || "",
        visit: this.filters.visit || "",
      };

      const next = { ...base };

      this.dashboardColumns.forEach((col) => {
        next[col.key] = this.filters[col.key] || "";
      });

      if (!this.canViewGroupColumn) next.group = "";

      const currentKeys = Object.keys(this.filters).sort();
      const nextKeys = Object.keys(next).sort();

      const sameKeys =
        currentKeys.length === nextKeys.length &&
        currentKeys.every((key, idx) => key === nextKeys[idx]);

      const sameValues =
        sameKeys &&
        nextKeys.every((key) => String(this.filters[key] ?? "") === String(next[key] ?? ""));

      if (sameValues) return;

      this.filters = next;
    },

    async loadVersions(studyId) {
      try {
        const resp = await axios.get(`/forms/studies/${studyId}/versions`, {
          headers: { Authorization: `Bearer ${this.token}` },
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
          params: { version: this.selectedVersion },
        });
        const schema = resp?.data?.schema || {};
        this.templateCache.set(this.selectedVersion, schema);
        this.applyTemplateSchema(schema);
      } catch (e) {
        // keep current schema if template fetch fails
      }
    },

    applyTemplateSchema(schema) {
      const current = this.study?.content?.study_data || {};
      const normalized = {
        study: schema?.study ?? current.study ?? {},
        subjects: Array.isArray(schema?.subjects) && schema.subjects.length ? schema.subjects : current.subjects || [],
        subjectCount: Number.isFinite(schema?.subjectCount)
          ? schema.subjectCount
          : current.subjectCount ?? (current.subjects?.length || 0),
        visits: Array.isArray(schema?.visits) && schema.visits.length ? schema.visits : current.visits || [],
        groups: Array.isArray(schema?.groups) && schema.groups.length ? schema.groups : current.groups || [],
        selectedModels: Array.isArray(schema?.selectedModels) ? schema.selectedModels : current.selectedModels || [],
        assignments: Array.isArray(schema?.assignments) ? schema.assignments : current.assignments || [],
      };

      if (!this.study) this.study = { metadata: {}, content: { study_data: normalized } };
      else if (!this.study.content) this.study.content = { study_data: normalized };
      else this.study.content.study_data = normalized;
    },

    currentWindowIndexSets(options = {}) {
      const forceAll = options.forceAll === true;
      const S = this.subjects.length;
      const V = this.visits.length;

      const allSubjectIndexes = new Set([...Array(S).keys()]);
      const allVisitIndexes = new Set([...Array(V).keys()]);

      if (forceAll || this.viewAll || S === 0 || V === 0) {
        return {
          subjectIdxPageSet: allSubjectIndexes,
          visitIdxPageSet: allVisitIndexes,
          pairKeySet: null,
          totalRowsInWindow: S * V,
        };
      }

      const pageStart = (this.currentPage - 1) * this.pageSize;
      const pageEndExcl = Math.min(pageStart + this.pageSize, S * V);

      const subjSet = new Set();
      const visitSet = new Set();
      const pairKeySet = new Set();

      for (let idx = pageStart; idx < pageEndExcl; idx++) {
        const subjIdx = Math.floor(idx / V);
        const visitIdx = idx % V;
        subjSet.add(subjIdx);
        visitSet.add(visitIdx);
        pairKeySet.add(`${subjIdx}:${visitIdx}`);
      }

      return {
        subjectIdxPageSet: subjSet,
        visitIdxPageSet: visitSet,
        pairKeySet,
        totalRowsInWindow: pageEndExcl - pageStart,
      };
    },

    isPairInWindow(windowInfo, subjIdx, visitIdx) {
      if (!windowInfo?.pairKeySet) return true;
      return windowInfo.pairKeySet.has(`${subjIdx}:${visitIdx}`);
    },

    async fetchPageEntries() {
      if (!this.study) return;
      const studyId = this.getStudyId();

      const { subjectIdxPageSet, visitIdxPageSet } = this.currentWindowIndexSets();

      const subject_indexes = this.viewAll
        ? null
        : Array.from(subjectIdxPageSet).sort((a, b) => a - b).join(",");

      const visit_indexes = this.viewAll
        ? null
        : Array.from(visitIdxPageSet).sort((a, b) => a - b).join(",");

      const params = new URLSearchParams();
      if (this.viewAll) params.append("all", "true");
      if (subject_indexes) params.append("subject_indexes", subject_indexes);
      if (visit_indexes) params.append("visit_indexes", visit_indexes);
      if (Number.isFinite(this.selectedVersion)) params.append("version", String(this.selectedVersion));

      const url = `/forms/studies/${studyId}/data_entries` + (params.toString() ? `?${params.toString()}` : "");

      try {
        this.isLoadingEntries = true;
        const resp = await axios.get(url, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        const payload = Array.isArray(resp.data)
          ? { entries: resp.data, total: resp.data.length }
          : resp.data || {};
        this.entries = payload.entries || [];
        this.totalEntries = payload.total ?? this.entries.length;
      } catch (err) {
        console.error("Failed to load entries:", err);
        this.entries = [];
      } finally {
        this.isLoadingEntries = false;
      }
    },

    toggleExportMenu() {
      this.showExportMenu = !this.showExportMenu;
    },

    resolveGroup(subjIdx) {
      const subjGroup = (this.subjects[subjIdx]?.group || "").trim().toLowerCase();
      const grpList = this.study?.content?.study_data?.groups || [];
      const idx = grpList.findIndex((g) => (g.name || "").trim().toLowerCase() === subjGroup);
      return idx >= 0 ? idx : 0;
    },

    resolveGroupName(subjIdx) {
      const subjGroup = (this.subjects[subjIdx]?.group || "").trim();
      const subjGroupNorm = subjGroup.toLowerCase();
      const grpList = this.study?.content?.study_data?.groups || [];
      const hit = grpList.find((g) => (g.name || "").trim().toLowerCase() === subjGroupNorm);
      return hit?.name || subjGroup || "";
    },

    isAssigned(sectionIdx, visitIdx, groupIdx) {
      return !!this.study?.content?.study_data?.assignments?.[sectionIdx]?.[visitIdx]?.[groupIdx];
    },

    findBestEntry(subjIdx, visitIdx, groupIdx) {
      return this.findBestEntryFromEntries(this.entries, subjIdx, visitIdx, groupIdx);
    },

    findBestEntryFromEntries(entries, subjIdx, visitIdx, groupIdx) {
      const all = (entries || []).filter(
        (e) =>
          e.subject_index === subjIdx &&
          e.visit_index === visitIdx &&
          e.group_index === groupIdx
      );
      if (!all.length) return null;

      const target = Number(this.selectedVersion);
      const exact = all.find((e) => Number(e.form_version) === target);
      if (exact) return exact;

      const le = all
        .filter((e) => Number(e.form_version) <= target)
        .sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
      if (le) return le;

      return all.sort((a, b) => Number(b.form_version) - Number(a.form_version))[0];
    },

    getValue(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      return this.getValueFromEntries(this.entries, subjIdx, visitIdx, sectionIdx, fieldIdx);
    },

    getValueFromEntries(entries, subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.findBestEntryFromEntries(entries, subjIdx, visitIdx, groupIdx);
      if (!entry || !entry.data) return "";

      const d = entry.data;
      if (!Array.isArray(d)) {
        const v = this.dictRead(d, sectionIdx, fieldIdx);
        return v != null ? v : "";
      }

      const section = Array.isArray(d) ? d[sectionIdx] || [] : [];
      return section[fieldIdx] != null ? section[fieldIdx] : "";
    },

    getTableRows(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      return this.getTableRowsFromEntries(this.entries, subjIdx, visitIdx, sectionIdx, fieldIdx);
    },

    getTableRowsFromEntries(entries, subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const raw = this.getValueFromEntries(entries, subjIdx, visitIdx, sectionIdx, fieldIdx);
      if (!raw || typeof raw !== "object") return [];
      if (!Array.isArray(raw.rows)) return [];
      return raw.rows;
    },
    readTableCellValue(tableRow, tableColDef, fallbackIndex) {
      if (!tableRow || typeof tableRow !== "object") return "";

      const candidates = [
        tableColDef?.id,
        tableColDef?._id,
        tableColDef?.key,
        tableColDef?.name,
        tableColDef?.label,
        `column_${fallbackIndex + 1}`,
      ].filter(Boolean);

      for (const candidate of candidates) {
        if (Object.prototype.hasOwnProperty.call(tableRow, candidate)) {
          return tableRow[candidate];
        }
      }

      const normalizedCandidates = candidates.map((c) => this.normalizeKey(c));
      const hitKey = Object.keys(tableRow).find((k) =>
        normalizedCandidates.includes(this.normalizeKey(k))
      );

      if (hitKey) return tableRow[hitKey];

      return "";
    },

    getMaxTableRowsForTableField(sectionIdx, fieldIdx, entries, forceAllPairs = false) {
      let maxRows = 0;
      const windowInfo = this.currentWindowIndexSets({ forceAll: forceAllPairs });

      this.subjects.forEach((subject, subjIdx) => {
        if (!windowInfo.subjectIdxPageSet.has(subjIdx)) return;

        const groupIdx = this.resolveGroup(subjIdx);

        this.visits.forEach((visit, vIdx) => {
          if (!windowInfo.visitIdxPageSet.has(vIdx)) return;
          if (!this.isPairInWindow(windowInfo, subjIdx, vIdx)) return;
          if (!this.isAssigned(sectionIdx, vIdx, groupIdx)) return;

          const rows = this.getTableRowsFromEntries(entries, subjIdx, vIdx, sectionIdx, fieldIdx);
          if (rows.length > maxRows) maxRows = rows.length;
        });
      });

      return maxRows;
    },

    buildDashboardColumns(options = {}) {
      const entries = options.entries || this.entries;
      const forceAllPairs = options.forceAllPairs === true;
      const cols = [];

      this.sections.forEach((section, sIdx) => {
        const sectionTitle = section?.title || `Section ${sIdx + 1}`;

        (section.fields || []).forEach((field, fIdx) => {
          const fieldLabel = field?.label || field?.name || field?.title || `Field ${fIdx + 1}`;
          const type = String(field?.type || "").toLowerCase();

          if (type === "table") {
            const tableCols = Array.isArray(field?.tableConfig?.columns)
              ? field.tableConfig.columns
              : [];

            const maxRowsForThisTable = this.getMaxTableRowsForTableField(
              sIdx,
              fIdx,
              entries,
              forceAllPairs
            );

            const visibleRowCount = Math.max(1, maxRowsForThisTable);

            for (let tableRowIdx = 0; tableRowIdx < visibleRowCount; tableRowIdx += 1) {
              tableCols.forEach((tc, tIdx) => {
                const tableColLabel = tc?.label || `Column ${tIdx + 1}`;

                cols.push({
                  kind: "tableCell",
                  key: `s${sIdx}_f${fIdx}__r${tableRowIdx}__tc${tIdx}`,
                  label: `${fieldLabel} [${tableRowIdx + 1}] - ${tableColLabel}`,
                  groupTitle: sectionTitle,
                  sectionTitle,
                  sIdx,
                  fIdx,
                  tIdx,
                  tableRowIdx,
                  tableKey: tc?.key || tc?.id || `column_${tIdx + 1}`,
                  tableKeyCandidates: [
                    tc?.id,
                    tc?._id,
                    tc?.key,
                    tc?.name,
                    tc?.label,
                    `column_${tIdx + 1}`,
                  ].filter(Boolean),
                  fieldType: "table",
                });
              });
            }
          } else {
            cols.push({
              kind: "normal",
              key: `s${sIdx}_f${fIdx}`,
              label: fieldLabel,
              groupTitle: sectionTitle,
              sectionTitle,
              sIdx,
              fIdx,
              fieldType: type,
            });
          }
        });
      });

      return cols;
    },

    buildHeaderGroupsForColumns(columns) {
      const groups = [];
      let current = null;

      columns.forEach((col) => {
        const title = col.sectionTitle || col.groupTitle || "";
        const key = `${col.sectionTitle}`;

        if (!current || current.key !== key) {
          current = { key, title, colspan: 1 };
          groups.push(current);
        } else {
          current.colspan += 1;
        }
      });

      return groups;
    },

    buildDashboardRows(options = {}) {
      const entries = options.entries || this.entries;
      const columns = options.columns || this.dashboardColumns;
      const forceAllPairs = options.forceAllPairs === true;
      const applyFilters = options.applyFilters !== false;
      const applySort = options.applySort !== false;

      let data = [];
      const windowInfo = this.currentWindowIndexSets({ forceAll: forceAllPairs });

      this.subjects.forEach((subject, subjIdx) => {
        if (!windowInfo.subjectIdxPageSet.has(subjIdx)) return;

        const groupIdx = this.resolveGroup(subjIdx);
        const groupName = this.resolveGroupName(subjIdx);

        this.visits.forEach((visit, vIdx) => {
          if (!windowInfo.visitIdxPageSet.has(vIdx)) return;
          if (!this.isPairInWindow(windowInfo, subjIdx, vIdx)) return;

          const row = {
            subjectId: subject.id,
            group: groupName,
            visit: visit.name,
            __sIdx: subjIdx,
            __vIdx: vIdx,
            __gIdx: groupIdx,
            __uploadedFiles: [],
            __fileItems: {},
          };

          const entry = this.findBestEntryFromEntries(entries, subjIdx, vIdx, groupIdx);
          row.__uploadedFiles = this.uploadedFilesForRow(subjIdx, vIdx, entry?.data || []);

          columns.forEach((col) => {
            const assigned = this.isAssigned(col.sIdx, vIdx, groupIdx);

            if (!assigned) {
              row[col.key] = "";
              return;
            }

            if (col.kind === "normal") {
              const field = this.sections?.[col.sIdx]?.fields?.[col.fIdx];
              const raw = this.getValueFromEntries(entries, subjIdx, vIdx, col.sIdx, col.fIdx);
              const type = String(field?.type || "").toLowerCase();

              if (type === "checkbox") {
                row[col.key] = raw === true ? "Yes" : raw === false ? "No" : "";
              } else if (type === "file") {
                row[col.key] = this.formatFileCell(raw);
                row.__fileItems[col.key] = normalizeUploadedFiles(raw).map((file) => ({
                  ...file,
                  sectionIndex: col.sIdx,
                  fieldIndex: col.fIdx,
                  sectionTitle: col.sectionTitle,
                  fieldLabel: col.label,
                }));
              } else if (Array.isArray(raw)) {
                row[col.key] = raw.join(", ");
              } else {
                row[col.key] = raw == null || raw === "" ? "" : raw;
              }

              return;
            }

            if (col.kind === "tableCell") {
                const field = this.sections?.[col.sIdx]?.fields?.[col.fIdx];
                const tableRows = this.getTableRowsFromEntries(entries, subjIdx, vIdx, col.sIdx, col.fIdx);
                const tableRow = tableRows[col.tableRowIdx] || null;
                const tableColDef = field?.tableConfig?.columns?.[col.tIdx] || {};
                const raw = this.readTableCellValue(tableRow, tableColDef, col.tIdx);
                const tableColType = String(tableColDef?.type || "").toLowerCase();

              if (tableColType === "checkbox") {
                row[col.key] = raw === true ? "Yes" : raw === false ? "No" : "";
              } else if (tableColType === "file") {
                row[col.key] = this.formatFileCell(raw);
                row.__fileItems[col.key] = normalizeUploadedFiles(raw).map((file) => ({
                  ...file,
                  sectionIndex: col.sIdx,
                  fieldIndex: col.fIdx,
                  sectionTitle: col.sectionTitle,
                  fieldLabel: col.label,
                }));
              } else if (Array.isArray(raw)) {
                row[col.key] = raw.join(", ");
              } else {
                row[col.key] = raw == null || raw === "" ? "" : raw;
              }
            }
          });

          data.push(row);
        });
      });

      if (applyFilters) {
        data = this.applyDashboardFilters(data, columns);
      }

      if (applySort) {
        data = this.applyDashboardSort(data);
      }

      return data;
    },

    applyDashboardFilters(data, columns) {
      return data.filter((row) => {
        if (this.filters.subjectId && !String(row.subjectId).toLowerCase().includes(this.filters.subjectId.toLowerCase())) return false;
        if (this.canViewGroupColumn && this.filters.group && !String(row.group).toLowerCase().includes(this.filters.group.toLowerCase())) return false;
        if (this.filters.visit && !String(row.visit).toLowerCase().includes(this.filters.visit.toLowerCase())) return false;

        for (const col of columns) {
          const filterVal = this.filters[col.key];
          if (!filterVal) continue;
          if (!String(row[col.key] ?? "").toLowerCase().includes(String(filterVal).toLowerCase())) {
            return false;
          }
        }

        return true;
      });
    },

    applyDashboardSort(data) {
      if (!this.sortConfig.key) return data;

      const key = this.sortConfig.key;
      const dir = this.sortConfig.direction === "asc" ? 1 : -1;

      return [...data].sort((a, b) => {
        let valA = a[key] ?? "";
        let valB = b[key] ?? "";

        if (key === "group" && !this.canViewGroupColumn) {
          valA = "";
          valB = "";
        }

        if (typeof valA === "number" && typeof valB === "number") {
          return (valA - valB) * dir;
        }

        const aNum = Number(valA);
        const bNum = Number(valB);
        if (!Number.isNaN(aNum) && !Number.isNaN(bNum) && String(valA).trim() !== "" && String(valB).trim() !== "") {
          return (aNum - bNum) * dir;
        }

        valA = String(valA).toLowerCase();
        valB = String(valB).toLowerCase();

        if (valA < valB) return -1 * dir;
        if (valA > valB) return 1 * dir;
        return 0;
      });
    },

    isCellSkipped(subjIdx, visitIdx, sectionIdx, fieldIdx) {
      const groupIdx = this.resolveGroup(subjIdx);
      const entry = this.findBestEntry(subjIdx, visitIdx, groupIdx);
      if (!entry) return false;
      const flags = entry.skipped_required_flags;
      return !!(
        Array.isArray(flags) &&
        Array.isArray(flags[sectionIdx]) &&
        flags[sectionIdx][fieldIdx] === true
      );
    },

    dashboardCellClass(row, col) {
      if (col.kind === "normal") {
        const assigned = this.isAssigned(col.sIdx, row.__vIdx, row.__gIdx);
        return {
          "cell-unassigned": !assigned,
          "cell-skipped": assigned && this.isCellSkipped(row.__sIdx, row.__vIdx, col.sIdx, col.fIdx),
        };
      }

      if (col.kind === "tableCell") {
        const assigned = this.isAssigned(col.sIdx, row.__vIdx, row.__gIdx);
        return {
          "cell-unassigned": !assigned,
        };
      }

      return {};
    },

    sortTable(key) {
      if (key === "group" && !this.canViewGroupColumn) return;
      if (this.sortConfig.key === key) {
        this.sortConfig.direction = this.sortConfig.direction === "asc" ? "desc" : "asc";
      } else {
        this.sortConfig = { key, direction: "asc" };
      }
    },

    sortIcon(key) {
      return this.sortConfig.key === key && this.sortConfig.direction === "desc"
        ? this.icons.toggleDown
        : this.icons.toggleUp;
    },

    formatFileCell(val) {
      const baseName = (p) => {
        if (!p) return "";
        const s = String(p);
        const parts = s.split(/[\\/]/);
        return parts[parts.length - 1];
      };

      const fromObj = (o) => o.file_name || o.name || baseName(o.url) || baseName(o.file_path) || "";

      if (Array.isArray(val)) {
        const names = val
          .map((v) => {
            if (v && typeof v === "object") return fromObj(v);
            if (typeof v === "string") return baseName(v);
            return "";
          })
          .filter(Boolean);
        return names.join(", ");
      }

      if (val && typeof val === "object") return fromObj(val);
      if (typeof val === "string") return baseName(val);
      return "";
    },

    studyFileRecordsForCell(sIdx, vIdx) {
      return (this.studyFiles || []).filter(
        (file) =>
          Number(file?.subject_index) === Number(sIdx) &&
          Number(file?.visit_index) === Number(vIdx)
      );
    },

    uploadedFilesForRow(sIdx, vIdx, data) {
      const collected = collectUploadedFilesForSlot({
        sections: this.sections,
        data,
      });
      const seenIds = new Set(
        collected
          .map((file) => String(uploadedFileId(file) || ""))
          .filter(Boolean)
      );

      this.studyFileRecordsForCell(sIdx, vIdx).forEach((file) => {
        const id = String(file.id || "");
        if (id && seenIds.has(id)) return;
        const context = inferUploadedFileFieldContext(file, this.sections) || {};
        collected.push({
          ...file,
          dbId: file.id,
          displayName: uploadedFileName(file),
          downloadable: true,
          sectionIndex: context.sectionIndex ?? -1,
          fieldIndex: context.fieldIndex ?? -1,
          sectionTitle: context.sectionTitle || "Uploaded files",
          fieldLabel: context.fieldLabel || file.description || "File upload",
        });
      });

      return collected;
    },

    fileItemsForCell(row, col) {
      return row?.__fileItems?.[col?.key] || [];
    },

    openUploadedFilesDialog(row) {
      this.uploadedFilesDialogFiles = row?.__uploadedFiles || [];
      this.uploadedFilesDialogSubject = row?.subjectId || "Subject";
      this.uploadedFilesDialogVisit = row?.visit || "Visit";
      this.showUploadedFilesDialog = true;
    },

    closeUploadedFilesDialog() {
      this.showUploadedFilesDialog = false;
      this.uploadedFilesDialogFiles = [];
      this.uploadedFilesDialogSubject = "";
      this.uploadedFilesDialogVisit = "";
    },

    async downloadUploadedFile(file) {
      if (!file) return;

      const url =
        file.source === "url"
          ? file.url
          : String(file.storage_option || "").toLowerCase() === "url"
          ? file.file_path
          : "";

      if (url) {
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }

      const fileId = uploadedFileId(file);
      if (!fileId || !this.studyId) {
        alert("This file is not available for download.");
        return;
      }

      if (!this.token) {
        this.$router.push("/login");
        return;
      }

      try {
        const response = await axios.get(
          `/forms/studies/${this.studyId}/files/${fileId}/download`,
          {
            headers: { Authorization: `Bearer ${this.token}` },
            responseType: "blob",
          }
        );

        const blob = new Blob([response.data]);
        const objectUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = uploadedFileName(file) || "download";
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(objectUrl);
      } catch (e) {
        console.error("Failed to download uploaded file", e);
        alert("Failed to download file.");
      }
    },

    goFirst() {
      this.currentPage = 1;
    },
    goPrev() {
      if (this.currentPage > 1) this.currentPage--;
    },
    goNext() {
      if (this.currentPage < this.totalPages) this.currentPage++;
    },
    goLast() {
      this.currentPage = this.totalPages;
    },

    async exportCSV() {
      const { rows, columns, headerGroups } = await this.ensureAllEntriesForExport();
      this.downloadDelimited(rows, columns, headerGroups, "csv");
      this.showExportMenu = false;
    },

    async exportExcel() {
      const { rows, columns, headerGroups } = await this.ensureAllEntriesForExport();
      this.downloadDelimited(rows, columns, headerGroups, "xls");
      this.showExportMenu = false;
    },

    async ensureAllEntriesForExport() {
      const studyId = this.getStudyId();
      let entriesForExport = this.entries;

      if (!this.viewAll || !this.canViewAll) {
        try {
          const resp = await axios.get(
            `/forms/studies/${studyId}/data_entries?all=true&version=${this.selectedVersion}`,
            { headers: { Authorization: `Bearer ${this.token}` } }
          );
          const payload = Array.isArray(resp.data) ? { entries: resp.data } : resp.data || {};
          entriesForExport = payload.entries || [];
        } catch (e) {
          console.error("Failed to fetch all entries for export, using current page only.", e);
        }
      }

      const columns = this.buildDashboardColumns({
        entries: entriesForExport,
        forceAllPairs: true,
      });

      const headerGroups = this.buildHeaderGroupsForColumns(columns);

      const rows = this.buildDashboardRows({
        entries: entriesForExport,
        columns,
        forceAllPairs: true,
        applyFilters: true,
        applySort: true,
      }).map((r) => ({ ...r }));

      return { rows, columns, headerGroups };
    },

    downloadDelimited(rows, columns, headerGroups, kind) {
      const quote = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;

      const headerTop = this.canViewGroupColumn
        ? ["Subject ID", "Group", "Visit", ...headerGroups.flatMap((g) => Array(g.colspan).fill(g.title))]
        : ["Subject ID", "Visit", ...headerGroups.flatMap((g) => Array(g.colspan).fill(g.title))];

      const headerBottom = this.canViewGroupColumn
        ? ["", "", "", ...columns.map((c) => c.label)]
        : ["", "", ...columns.map((c) => c.label)];

      const lines = [];
      lines.push(headerTop.map(quote).join(","));
      lines.push(headerBottom.map(quote).join(","));

      rows.forEach((row) => {
        const cells = this.canViewGroupColumn
          ? [row.subjectId, row.group, row.visit]
          : [row.subjectId, row.visit];

        columns.forEach((col) => {
          cells.push(row[col.key]);
        });

        lines.push(cells.map(quote).join(","));
      });

      const mime =
        kind === "xls"
          ? "application/vnd.ms-excel"
          : "text/csv";
      const ext = kind === "xls" ? "xls" : "csv";

      const blob = new Blob([lines.join("\r\n")], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${this.study?.metadata?.study_name || "study"}_v${this.selectedVersion}_data.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
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

.left-controls,
.right-controls {
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

.btn-minimal:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #1f2937;
}

.icon-only {
  padding: 6px 10px;
  font-size: 1rem;
}

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

.visit-cell-content,
.file-cell-list,
.file-cell-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.file-cell-list {
  flex-wrap: wrap;
}

.file-cell-item {
  max-width: 220px;
  padding: 2px 4px;
  border-radius: 6px;
  background: #f8fafc;
}

.file-cell-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uploaded-files-inline-btn,
.file-download-inline-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 24px;
  border: 1px solid #bfdbfe;
  border-radius: 7px;
  background: #eff6ff;
  color: #2563eb;
  cursor: pointer;
}

.uploaded-files-inline-btn:hover,
.file-download-inline-btn:hover {
  background: #dbeafe;
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
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  z-index: 300;
  padding: 12px;
  min-width: 240px;
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

.legend-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 6px;
  border: 1px solid #d1d5db;
  vertical-align: -2px;
  background: #ffffff;
}

.swatch-none {
  background: #ffffff;
  border-color: #d1d5db;
}

.swatch-gray {
  background: #e5e7eb;
  border-color: #9ca3af;
}

.swatch-red {
  background: #fee2e2;
  border-color: #ef4444;
}

.table-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 0;
  color: #4b5563;
  font-size: 0.9rem;
  gap: 10px;
  flex-wrap: wrap;
}

.table-controls .view-all {
  margin-left: 12px;
}

.study-dashboard-container {
  --sticky-subject-left: 0px;
  --sticky-group-left: 0px;
  --sticky-visit-left: 0px;
  --sticky-section-left: 0px;

  --sticky-subject-min-w: 150px;
  --sticky-group-min-w: 120px;
  --sticky-visit-min-w: 160px;

  --header-row-1-h: 40px;
  --header-row-2-h: 40px;

  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  padding: 12px;
}

.study-dashboard-container.embedded,
.study-dashboard-container.fullscreen {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.study-dashboard-container.fullscreen {
  width: 100%;
}

.table-wrapper {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  width: 100%;
  max-width: 100%;
  position: relative;
}

.study-dashboard-container.embedded .table-wrapper,
.study-dashboard-container.fullscreen .table-wrapper {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.dashboard-table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin-top: 8px;
}

.dashboard-table th,
.dashboard-table td {
  border: 1px solid #e5e7eb;
  border-right: 0;
  border-bottom: 0;
  padding: 8px 12px;
  font-size: 0.9rem;
  text-align: center;
  white-space: nowrap;
  box-sizing: border-box;
}

.dashboard-table th:last-child,
.dashboard-table td:last-child {
  border-right: 1px solid #e5e7eb;
}

.dashboard-table tbody tr:last-child td {
  border-bottom: 1px solid #e5e7eb;
}

.dashboard-table th {
  cursor: pointer;
}

.dashboard-table th i {
  font-size: 0.8rem;
  color: #1f2937;
  margin-left: 4px;
}

/* ============================================================
   STICKY HEADER STRUCTURE
   Expected thead:
   Row 1: Subject / Group / Visit + Section headers
   Row 2: blank identity placeholders + Field headers
   Row 3: Filters
   ============================================================ */

.dashboard-table thead tr:nth-child(1) th {
  position: sticky;
  top: 0;
  height: var(--header-row-1-h);
  background: #e5e7eb;
  color: #1f2937;
  font-weight: 600;
  z-index: 40;
}

.dashboard-table thead tr:nth-child(2) th {
  position: sticky;
  top: var(--header-row-1-h);
  height: var(--header-row-2-h);
  background: #f3f4f6;
  color: #374151;
  font-weight: 600;
  z-index: 30;
}

.dashboard-table thead tr.filter-row th {
  position: sticky;
  top: calc(var(--header-row-1-h) + var(--header-row-2-h));
  background: #ffffff;
  z-index: 35;
}

/* ============================================================
   STICKY LEFT IDENTITY COLUMNS
   Subject / Group / Visit remain fixed during horizontal scroll.
   ============================================================ */

.dashboard-table .sticky-col {
  position: sticky;
  box-sizing: border-box;
  white-space: nowrap;
  background-clip: padding-box;
}

.dashboard-table .sticky-subject {
  left: var(--sticky-subject-left);
  min-width: var(--sticky-subject-min-w);
}

.dashboard-table .sticky-group {
  left: var(--sticky-group-left);
  min-width: var(--sticky-group-min-w);
}

.dashboard-table .sticky-visit {
  left: var(--sticky-visit-left);
  min-width: var(--sticky-visit-min-w);
}

/* Row 1 identity headers */
.dashboard-table thead tr:nth-child(1) th.identity-header {
  position: sticky;
  top: 0;
  z-index: 160;
  background: #e5e7eb;
}

/* Row 2 blank identity placeholders */
.dashboard-table thead tr:nth-child(2) th.identity-subheader {
  position: sticky;
  top: var(--header-row-1-h);
  z-index: 150;
  background: #f3f4f6;
  padding: 0;
  cursor: default;
}

/* Row 3 identity filter cells */
.dashboard-table thead tr.filter-row th.sticky-col {
  z-index: 145;
  background: #ffffff;
}

/* Body sticky identity cells */
.dashboard-table tbody td.sticky-col {
  position: sticky;
  z-index: 60;
  background: #f9fafb;
  font-weight: 600;
  color: #1f2937;
}

/* Strong visual separation after the last sticky identity column */
.dashboard-table thead th.sticky-visit,
.dashboard-table tbody td.sticky-visit {
  box-shadow: 2px 0 0 #d1d5db;
}

/* ============================================================
   SECTION HEADER STICKY BEHAVIOR
   Section names stick after Subject / Group / Visit.
   Next section naturally replaces the current section.
   ============================================================ */

.dashboard-table thead tr:nth-child(1) th.section-header-cell {
  position: sticky;
  left: var(--sticky-section-left);
  top: 0;
  z-index: 120;
  background: #e5e7eb;
  text-align: left;
  padding: 0;
  overflow: hidden;
  box-shadow: 2px 0 0 #d1d5db;
}

.dashboard-table thead tr:nth-child(1) th.section-header-cell .section-header-label {
  position: static;
  display: inline-flex;
  align-items: center;
  max-width: calc(100vw - var(--sticky-section-left) - 32px);
  height: 100%;
  padding: 8px 12px;
  box-sizing: border-box;
  background: #e5e7eb;
  color: #1f2937;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Normal field headers should pass behind identity columns */
.dashboard-table thead tr:nth-child(2) th:not(.sticky-col) {
  z-index: 80;
}

/* Normal filter headers should pass behind identity filter cells */
.dashboard-table thead tr.filter-row th:not(.sticky-col) {
  z-index: 75;
}

/* Ensure sticky cells visually cover content moving underneath */
.dashboard-table thead th.sticky-col,
.dashboard-table tbody td.sticky-col {
  background-clip: padding-box;
}

/* ============================================================
   BODY CELLS
   ============================================================ */

.dashboard-table tbody td.fixed-col {
  background: #f9fafb;
  font-weight: 600;
  color: #1f2937;
}

.dashboard-table tbody td:not(.fixed-col) {
  background: #ffffff;
  color: #4b5563;
}

.dashboard-table tbody tr:hover td {
  background: #f1f5f9;
}

.dashboard-table tbody tr:hover td.sticky-col {
  background: #f1f5f9;
}

/* Preserve skipped/unassigned colors even with sticky cells */
.cell-unassigned {
  background: #e5e7eb !important;
  color: #374151;
  border-color: #d1d5db !important;
}

.cell-skipped {
  background: #fee2e2 !important;
  color: #991b1b;
  border-color: #ef4444 !important;
  font-weight: 600;
}

.dashboard-table tbody td.cell-unassigned.sticky-col {
  background: #e5e7eb !important;
}

.dashboard-table tbody td.cell-skipped.sticky-col {
  background: #fee2e2 !important;
}

/* ============================================================
   FILTER ROW
   ============================================================ */

.filter-row input {
  width: 100%;
  min-width: 120px;
  padding: 4px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
}

/* ============================================================
   LOADING / EMPTY STATES
   ============================================================ */

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

/* ============================================================
   STICKY PAGINATION
   Keeps pagination visible while horizontally scrolling.
   ============================================================ */

.pagination-controls {
  position: sticky;
  left: 0;
  bottom: 0;
  z-index: 150;

  width: 100%;
  min-width: 100%;

  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;

  margin: 0;
  padding: 10px 12px;

  background: #ffffff;
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);

  box-sizing: border-box;
  flex-wrap: wrap;
}

.pagination-controls button {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 4px;
  white-space: nowrap;
}

.pagination-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-controls span {
  white-space: nowrap;
}
</style>
