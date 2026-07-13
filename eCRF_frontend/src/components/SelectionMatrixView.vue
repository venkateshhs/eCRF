<template>
  <div>
    <!-- Initializing message (prevents flashing ALL visits first) -->
    <div v-if="!matrixReady" class="boot-message">
      Preparing visit matrix…
    </div>

    <template v-else>
      <!-- Matrix toolbar: visit filter + helper + add subjects (left) … info button (far right) -->
      <div class="matrix-toolbar">
        <div class="matrix-toolbar-left">
          <div class="visit-filter">
            <label>Visit filter</label>
            <select
              class="visit-select"
              :value="selectedVisitIndex"
              @change="onVisitChange"
            >
              <option :value="-1">All visits</option>
              <option v-for="(v, i) in visitList" :key="'vopt-'+i" :value="i">
                {{ v.name }}
              </option>
            </select>
          </div>

          <!-- Subject search: scrolls to the matching subject, does NOT filter rows -->
          <div class="subject-search">
            <label>Search subject</label>

            <div class="subject-search-box">
              <input
                type="search"
                class="subject-search-input"
                v-model.trim="subjectSearch"
                placeholder="Search subject ID…"
                @input="onSubjectSearchInput"
                @keydown.enter.prevent="goToNextSubjectMatch"
                @keydown.esc.prevent="clearSubjectSearch"
              />

              <button
                v-if="subjectSearch"
                type="button"
                class="subject-search-clear"
                title="Clear search"
                @click="clearSubjectSearch"
              >
                ×
              </button>
            </div>

            <div v-if="subjectSearch" class="subject-search-result">
              <template v-if="matchedSubjectIndices.length">
                {{ activeMatchPosition + 1 }} / {{ matchedSubjectIndices.length }}
              </template>
              <template v-else>
                No match
              </template>
            </div>
          </div>

          <!-- Helper message: to which version we add data -->
          <div
            v-if="selectedVersion"
            class="version-helper"
            :title="'All new data will be saved on the latest template version'"
          >
            Saving to Version {{ selectedVersion }}
          </div>

          <!-- Add subjects button: always visible in selection view -->
          <button
            type="button"
            class="btn-add-subject"
            @click="$emit('add-subjects')"
          >
            + Add subjects
          </button>
        </div>

        <!-- Info icon MUST be extreme right -->
        <button
          type="button"
          class="legend-icon-btn"
          @click="$emit('open-status-legend')"
          title="Legend / Color meaning"
        >
          <i :class="infoIcon"></i>
        </button>
      </div>

      <div ref="matrixWrap" class="matrix-wrap">
        <!-- Loading overlay while (re)hydrating visits -->
        <div v-if="visitLoading" class="busy-overlay"><div class="spinner"></div></div>

        <table class="selection-matrix" :class="{ fluid: isFluidMatrix }">
          <thead>
            <tr>
              <th ref="subjectHeader" class="subject-col" :style="subjectColStyle">
                Subject / Visit
              </th>
              <th
                v-if="showGroupColumn"
                class="group-col"
              >
                Group
              </th>

              <th
                v-for="vIdx in displayedVisitIndices"
                :key="'visit-th-' + vIdx"
                class="visit-col"
                :style="visitColStyle"
              >
                {{ visitList[vIdx].name }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(subject, sIdx) in subjects"
              :key="'sv-row-'+sIdx"
              :ref="el => setSubjectRowRef(el, sIdx)"
              class="subject-row"
              :class="{
                'subject-row-search-match': isSearchMatchedSubject(sIdx),
                'subject-row-search-active': activeMatchedSubjectIndex === sIdx
              }"
            >

              <td class="subject-cell" :style="subjectColStyle">
                {{ subject.id }}
              </td>


              <td
                v-if="showGroupColumn"
                class="group-cell"
              >
                {{ subject.group || "—" }}
              </td>

              <td
                v-for="vIdx in displayedVisitIndices"
                :key="'visit-td-' + sIdx + '-' + vIdx"
                class="visit-cell"
                :style="visitColStyle"
              >
                <button
                  class="select-btn"
                  :class="statusClass(sIdx, vIdx)"
                  :style="progressStyle(sIdx, vIdx)"
                  @click="$emit('select-cell', sIdx, vIdx)"
                >
                  <span class="select-btn-fill"></span>
                  <span class="select-btn-label">
                    {{ progressLabel(sIdx, vIdx) || "Select" }}
                  </span>
                </button>
              </td>
            </tr>
            <tr v-if="!subjects || subjects.length === 0">
              <td colspan="999" class="no-subjects-placeholder">
                No subjects have been created for this study.<br />
                You can add subjects directly here using the button below.
                <div class="no-subjects-actions">
                  <button
                    type="button"
                    class="btn-add-subject-inline"
                    @click="$emit('add-subjects')"
                  >
                    + Add subjects
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: "SelectionMatrixView",
  props: {
    matrixReady: { type: Boolean, default: false },
    visitList: { type: Array, default: () => [] },
    selectedVisitIndex: { type: Number, required: true },
    displayedVisitIndices: { type: Array, default: () => [] },
    subjects: { type: Array, default: () => [] },
    visitLoading: { type: Boolean, default: false },
    isFluidMatrix: { type: Boolean, default: false },
    subjectColStyle: { type: Object, default: () => ({}) },
    visitColStyle: { type: Object, default: () => ({}) },
    // function provided by parent: (sIdx, vIdx) => "status-none" | "status-partial" | ...
    statusClass: { type: Function, required: true },
    statusProgress: {
      type: Function,
      default: () => ({ percentage: 0, label: "", status: "none" }),
    },
    selectedVersion: { type: [String, Number, null], default: null },
    infoIcon: { type: String, default: "fas fa-info-circle" },

    showGroupColumn: { type: Boolean, default: false },
  },
  emits: [
    "update:selectedVisitIndex",
    "add-subjects",
    "select-cell",
    "open-status-legend",
  ],

  data() {
    return {
      subjectSearch: "",
      matchedSubjectIndices: [],
      activeMatchPosition: 0,
      subjectRowRefs: {},
    };
  },

  computed: {
    activeMatchedSubjectIndex() {
      if (!this.matchedSubjectIndices.length) return null;
      return this.matchedSubjectIndices[this.activeMatchPosition] ?? null;
    },
  },

  methods: {
    onVisitChange(event) {
      const val = parseInt(event.target.value, 10);
      this.$emit("update:selectedVisitIndex", Number.isNaN(val) ? -1 : val);
    },

    progressInfo(sIdx, vIdx) {
      const info = this.statusProgress(sIdx, vIdx) || {};
      const percentage = Math.max(0, Math.min(100, Number(info.percentage || 0)));
      return {
        ...info,
        percentage,
      };
    },

    progressStyle(sIdx, vIdx) {
      const info = this.progressInfo(sIdx, vIdx);
      return {
        "--progress-pct": `${info.percentage}%`,
      };
    },

    progressLabel(sIdx, vIdx) {
      return this.progressInfo(sIdx, vIdx).label || "";
    },

    setSubjectRowRef(el, sIdx) {
      if (el) {
        this.subjectRowRefs[sIdx] = el;
      } else if (this.subjectRowRefs && sIdx in this.subjectRowRefs) {
        delete this.subjectRowRefs[sIdx];
      }
    },

    normalizeSearchText(value) {
      return String(value || "")
        .trim()
        .toLowerCase();
    },

    getSubjectSearchLabel(subject, index) {
      return String(
        subject?.id ||
        subject?.subject_id ||
        subject?.name ||
        `Subject ${index + 1}`
      );
    },

    rebuildSubjectMatches() {
      const query = this.normalizeSearchText(this.subjectSearch);

      if (!query) {
        this.matchedSubjectIndices = [];
        this.activeMatchPosition = 0;
        return;
      }

      const subjects = Array.isArray(this.subjects) ? this.subjects : [];

      this.matchedSubjectIndices = subjects
        .map((subject, index) => {
          const label = this.normalizeSearchText(
            this.getSubjectSearchLabel(subject, index)
          );

          return label.includes(query) ? index : null;
        })
        .filter((index) => index !== null);

      this.activeMatchPosition = 0;
    },

    onSubjectSearchInput() {
      this.rebuildSubjectMatches();

      this.$nextTick(() => {
        this.scrollToActiveSubjectMatch();
      });
    },

    goToNextSubjectMatch() {
      if (!this.subjectSearch) return;

      if (!this.matchedSubjectIndices.length) {
        this.rebuildSubjectMatches();
      }

      if (!this.matchedSubjectIndices.length) return;

      this.activeMatchPosition =
        (this.activeMatchPosition + 1) % this.matchedSubjectIndices.length;

      this.$nextTick(() => {
        this.scrollToActiveSubjectMatch();
      });
    },

    scrollToActiveSubjectMatch() {
      const sIdx = this.activeMatchedSubjectIndex;
      if (sIdx == null) return;

      const wrap = this.$refs.matrixWrap;
      const row = this.subjectRowRefs?.[sIdx];

      if (!wrap || !row) return;

      const header = wrap.querySelector("thead");
      const headerHeight = header?.offsetHeight || 0;

      const targetTop = Math.max(0, row.offsetTop - headerHeight - 10);

      wrap.scrollTo({
        top: targetTop,
        behavior: "smooth",
      });
    },

    isSearchMatchedSubject(sIdx) {
      return this.matchedSubjectIndices.includes(sIdx);
    },

    clearSubjectSearch() {
      this.subjectSearch = "";
      this.matchedSubjectIndices = [];
      this.activeMatchPosition = 0;
    },
  },

  watch: {
    // IMPORTANT: ref doesn't exist until matrixReady becomes true (v-else)
    matrixReady(val) {
      if (!val) return;
      this.$nextTick(() => {
        if (this._updateSubjectWidth) this._updateSubjectWidth();

        if (this.subjectSearch) {
          this.rebuildSubjectMatches();
          this.scrollToActiveSubjectMatch();
        }
      });
    },

    subjects: {
      deep: true,
      handler() {
        this.$nextTick(() => {
          if (this.subjectSearch) {
            this.rebuildSubjectMatches();
            this.scrollToActiveSubjectMatch();
          }
        });
      },
    },

    selectedVisitIndex() {
      this.$nextTick(() => {
        if (this._updateSubjectWidth) this._updateSubjectWidth();

        if (this.subjectSearch) {
          this.scrollToActiveSubjectMatch();
        }
      });
    },
  },

  mounted() {
    // safe default so group never overlaps even before ref exists
    this.$el.style.setProperty("--subject-width", "200px");

    this._updateSubjectWidth = () => {
      const w = this.$refs.subjectHeader?.offsetWidth;
      if (!w) return; // prevent "undefinedpx"
      this.$el.style.setProperty("--subject-width", w + "px");
    };

    this.$nextTick(() => {
      this._updateSubjectWidth();
    });

    window.addEventListener("resize", this._updateSubjectWidth);
  },

  beforeUnmount() {
    window.removeEventListener("resize", this._updateSubjectWidth);
  },
};
</script>

<style scoped>
/* ========= Boot / init messaging ========= */
.boot-message {
  padding: 16px 18px;
  margin-bottom: 14px;
  border: 1px dashed #d1d5db;
  background: #f9fafb;
  color: #4b5563;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
}

/* ========= Matrix toolbar ========= */
.matrix-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.matrix-toolbar-left {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  min-width: 0;
}

.visit-filter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.visit-filter label {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}

.visit-select {
  min-width: 220px;
  min-height: 40px;
  padding: 8px 34px 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #1f2937;
  font-size: 14px;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.visit-select:hover {
  border-color: #9ca3af;
}

.visit-select:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.12);
}

/* Subject search: scrolls to the matching subject, does NOT filter rows */
.subject-search {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 220px;
}

.subject-search label {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}

.subject-search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.subject-search-input {
  width: 240px;
  min-height: 40px;
  padding: 8px 34px 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #1f2937;
  font-size: 14px;
  box-sizing: border-box;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.subject-search-input:hover {
  border-color: #9ca3af;
}

.subject-search-input:focus {
  outline: none;
  border-color: #6b7280;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.12);
}

.subject-search-clear {
  position: absolute;
  right: 8px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 999px;
  background: #e5e7eb;
  color: #374151;
  cursor: pointer;
  font-size: 17px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.subject-search-clear:hover {
  background: #d1d5db;
  color: #111827;
}

.subject-search-result {
  min-height: 14px;
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  line-height: 1;
}

/* Version badge */
.version-helper {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  box-sizing: border-box;
  font-size: 12px;
  font-weight: 700;
  color: #374151;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 8px;
  padding: 8px 11px;
  line-height: 1;
  align-self: flex-end;
}

/* Add subjects button */
.btn-add-subject {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 13px;
  border-radius: 8px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  align-self: flex-end;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.btn-add-subject:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.btn-add-subject:active {
  transform: translateY(0);
}

/* Info icon at far right */
.legend-icon-btn {
  width: 38px;
  height: 38px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  color: #6b7280;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: auto;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease;
}

.legend-icon-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
  transform: translateY(-1px);
}

.legend-icon-btn i {
  font-size: 15px;
}

/* ========= Matrix card / scroll container ========= */
.matrix-wrap {
  position: relative;
  overflow: auto;
  max-height: 70vh;
  width: 100%;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

/* Loading overlay */
.busy-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.76);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  backdrop-filter: blur(1px);
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #d1d5db;
  border-top-color: #6b7280;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ========= Matrix table ========= */
.selection-matrix {
  border-collapse: separate;
  border-spacing: 0;
  width: max-content;
  min-width: 720px;
  table-layout: fixed;
  background: #ffffff;
}

.selection-matrix.fluid {
  width: 100%;
  min-width: 100%;
}

/* Base cells */
.selection-matrix th,
.selection-matrix td {
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 14px;
  text-align: center;
  vertical-align: middle;
  white-space: nowrap;
  box-sizing: border-box;
}

.selection-matrix th:last-child,
.selection-matrix td:last-child {
  border-right: none;
}

.selection-matrix tbody tr:last-child td {
  border-bottom: none;
}

/* Sticky header row */
.selection-matrix thead th {
  position: sticky;
  top: 0;
  z-index: 6;
  background: #eef4f9;
  color: #111827;
  font-size: 14px;
  font-weight: 800;
  border-bottom: 1px solid #dbe4ee;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

/* Subject sticky column */
.subject-col,
.subject-cell {
  position: sticky;
  left: 0;
  min-width: 200px;
  max-width: 320px;
  text-align: left !important;
}

.subject-col {
  z-index: 9 !important;
  background: #eaf1f8 !important;
  color: #111827;
  font-weight: 800;
}

.subject-cell {
  z-index: 5;
  background: #ffffff;
  color: #1f2937;
  font-weight: 800;
}

/* Group sticky column */
.group-col,
.group-cell {
  position: sticky;
  left: var(--subject-width, 200px);
  min-width: 160px;
  width: 180px;
  text-align: left !important;
}

.group-col {
  z-index: 8 !important;
  background: #eaf1f8 !important;
  color: #111827;
  font-weight: 800;
}

.group-cell {
  z-index: 4;
  background: #ffffff;
  color: #4b5563;
  font-size: 13px;
  font-weight: 700;
}

/* Visit columns */
.visit-col {
  min-width: 132px;
  max-width: 200px;
  text-align: center;
}

.visit-cell {
  width: 140px;
  text-align: center;
  padding: 9px 10px;
}

/* Fluid mode overrides */
.selection-matrix.fluid .subject-col,
.selection-matrix.fluid .subject-cell,
.selection-matrix.fluid .visit-col,
.selection-matrix.fluid .visit-cell {
  min-width: 0;
  max-width: none;
}

/* Zebra rows */
.selection-matrix tbody tr:nth-child(odd) td {
  background: #fcfcfd;
}

.selection-matrix tbody tr:nth-child(odd) .subject-cell,
.selection-matrix tbody tr:nth-child(odd) .group-cell {
  background: #f8fafc;
}

/* Hover rows */
.selection-matrix tbody tr:hover td {
  background: #f8fafc;
}

.selection-matrix tbody tr:hover .subject-cell,
.selection-matrix tbody tr:hover .group-cell {
  background: #f1f5f9;
}

/* Subject search row highlight */
.subject-row-search-match td {
  background: #eff6ff !important;
}

.subject-row-search-match .subject-cell,
.subject-row-search-match .group-cell {
  background: #dbeafe !important;
}

.subject-row-search-active td {
  background: #dbeafe !important;
}

.subject-row-search-active .subject-cell,
.subject-row-search-active .group-cell {
  background: #bfdbfe !important;
}

.subject-row-search-active .subject-cell {
  box-shadow: inset 4px 0 0 #3b82f6;
}
/* ========= Select/status button ========= */
.select-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-width: 100px;
  max-width: 160px;
  min-height: 34px;
  border: 1px solid transparent;
  padding: 7px 11px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.15;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  isolation: isolate;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.select-btn-fill {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--progress-pct, 0%);
  border-radius: inherit;
  z-index: 0;
  transition: width 0.18s ease;
}

.select-btn-label {
  position: relative;
  z-index: 1;
}

.selection-matrix.fluid .select-btn {
  min-width: 0;
  max-width: none;
}

.select-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.09);
}

.select-btn:active {
  transform: translateY(0);
}

/* Status colors - stronger clinician visibility, keeping no-data as grey */
.select-btn.status-none {
  background: #e5e7eb;
  color: #374151;
  border-color: #9ca3af;
}

.select-btn.status-none .select-btn-fill {
  background: transparent;
}

.select-btn.status-none:hover {
  background: #d1d5db;
  color: #111827;
  border-color: #6b7280;
}

.select-btn.status-partial {
  background: #e5e7eb;
  color: #78350f;
  border-color: #f59e0b;
}

.select-btn.status-partial .select-btn-fill {
  background: #fde68a;
}

.select-btn.status-partial:hover {
  background: #d1d5db;
  color: #78350f;
  border-color: #d97706;
}

.select-btn.status-partial:hover .select-btn-fill {
  background: #fcd34d;
}

.select-btn.status-complete {
  background: #e5e7eb;
  color: #14532d;
  border-color: #16a34a;
}

.select-btn.status-complete .select-btn-fill {
  width: 100%;
  background: #bbf7d0;
}

.select-btn.status-complete:hover {
  background: #d1d5db;
  color: #14532d;
  border-color: #15803d;
}

.select-btn.status-complete:hover .select-btn-fill {
  background: #86efac;
}

.select-btn.status-skipped {
  background: #fecaca;
  color: #7f1d1d;
  border-color: #dc2626;
}

.select-btn.status-skipped .select-btn-fill {
  width: 100%;
  background: #fecaca;
}

.select-btn.status-skipped:hover {
  background: #fca5a5;
  color: #7f1d1d;
  border-color: #b91c1c;
}

/* ========= Scrollbars ========= */
.matrix-wrap::-webkit-scrollbar {
  height: 10px;
  width: 10px;
}

.matrix-wrap::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 999px;
}

.matrix-wrap::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}

.matrix-wrap::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* ========= Empty state ========= */
.no-subjects-placeholder {
  text-align: center;
  padding: 28px 20px !important;
  color: #6b7280;
  font-style: italic;
  background: #f9fafb !important;
  line-height: 1.55;
}

.no-subjects-actions {
  margin-top: 14px;
}

.btn-add-subject-inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.btn-add-subject-inline:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.btn-add-subject-inline:active {
  transform: translateY(0);
}

/* ========= Responsive ========= */
@media (max-width: 900px) {
  .matrix-toolbar {
    align-items: stretch;
  }

  .matrix-toolbar-left {
    flex: 1;
  }

  .visit-col {
    min-width: 112px;
  }

  .visit-cell {
    width: 120px;
  }

  .select-btn {
    min-width: 90px;
    max-width: 140px;
  }
}

@media (max-width: 768px) {
  .matrix-toolbar {
    flex-direction: column;
    align-items: stretch;
    padding: 12px;
  }

  .matrix-toolbar-left {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .visit-select,
  .btn-add-subject,
  .version-helper {
    width: 100%;
  }

  .subject-search,
  .subject-search-input {
    width: 100%;
    min-width: 0;
  }

  .legend-icon-btn {
    align-self: flex-end;
    margin-left: 0;
  }

  .matrix-wrap {
    border-radius: 10px;
  }

  .selection-matrix th,
  .selection-matrix td {
    padding: 10px 9px;
    font-size: 13px;
  }

  .subject-col,
  .subject-cell {
    min-width: 170px;
  }

  .group-col,
  .group-cell {
    min-width: 140px;
    width: 150px;
  }
}
</style>
