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
          :title="'Legend / Color meaning'"
        >
          <i :class="infoIcon"></i>
        </button>
      </div>

      <div class="matrix-wrap">
        <!-- Loading overlay while (re)hydrating visits -->
        <div v-if="visitLoading" class="busy-overlay"><div class="spinner"></div></div>

        <table class="selection-matrix" :class="{ fluid: isFluidMatrix }">
          <thead>
            <tr>
              <th class="subject-col" :style="subjectColStyle">Subject / Visit</th>
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
            <tr v-for="(subject, sIdx) in subjects" :key="'sv-row-'+sIdx">
              <td class="subject-cell" :style="subjectColStyle">{{ subject.id }}</td>
              <td
                v-for="vIdx in displayedVisitIndices"
                :key="'visit-td-' + sIdx + '-' + vIdx"
                class="visit-cell"
                :style="visitColStyle"
              >
                <button
                  class="select-btn"
                  :class="statusClass(sIdx, vIdx)"
                  @click="$emit('select-cell', sIdx, vIdx)"
                >
                  Select
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
    selectedVersion: { type: [String, Number, null], default: null },
    infoIcon: { type: String, default: "fas fa-info-circle" },
  },
  emits: [
    "update:selectedVisitIndex",
    "add-subjects",
    "select-cell",
    "open-status-legend",
  ],
  methods: {
    onVisitChange(event) {
      const val = parseInt(event.target.value, 10);
      this.$emit("update:selectedVisitIndex", Number.isNaN(val) ? -1 : val);
    },
  },
};
</script>

<style scoped>
/* ========= Boot / init messaging ========= */
.boot-message {
  padding: 16px;
  margin-bottom: 10px;
  border: 1px dashed #e5e7eb;
  background: #fafafa;
  color: #4b5563;
  border-radius: 8px;
  font-size: 14px;
}

/* ========= Matrix toolbar (visit dropdown) ========= */
.matrix-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.matrix-toolbar-left {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
.visit-filter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.visit-filter label {
  font-size: 13px;
  color: #444;
}
.visit-select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 8px;
  min-width: 220px;
  background: #fff;
}
.version-helper {
  font-size: 12px;
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 10px 12px;
  line-height: 1;
  white-space: nowrap;
  align-self: flex-end;
}

/* Add subjects button in toolbar */
.btn-add-subject {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  font-size: 13px;
  cursor: pointer;
  align-self: flex-end;
}
.btn-add-subject:hover {
  background: #e5e7eb;
}

/* Info icon at far right */
.legend-icon-btn {
  background: transparent;
  border: none;
  padding: 4px 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  line-height: 1;
  color: #6b7280;
  margin-left: auto;
}
.legend-icon-btn:hover {
  color: #374151;
}
.legend-icon-btn i {
  font-size: 14px;
}

/* ========= Scrollable selection matrix ========= */
.matrix-wrap {
  position: relative;
  overflow: auto;
  max-height: 70vh;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  width: 100%;
}

/* Loading overlay */
.busy-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}
.spinner {
  width: 28px;
  height: 28px;
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

/* Make table fill container or scroll based on column count */
.selection-matrix {
  border-collapse: collapse;
  width: max-content;
  min-width: 720px;
  table-layout: fixed;
}
.selection-matrix.fluid {
  width: 100%;
  min-width: 100%;
}

/* Base table cells */
.selection-matrix th,
.selection-matrix td {
  border: 1px solid #e5e7eb;
  padding: 10px 12px;
  text-align: center;
  vertical-align: middle;
  white-space: nowrap;
}

/* Sticky header row */
.selection-matrix thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: #f9fafb;
  font-weight: 600;
  color: #1f2937;
}

/* Subject column sticky */
.subject-col,
.subject-cell {
  position: sticky;
  left: 0;
  z-index: 4;
  background: #ffffff;
  text-align: left;
}
.subject-col {
  background: #f3f4f6;
  font-weight: 600;
  color: #1f2937;
}

/* Default fixed sizing */
.subject-col,
.subject-cell {
  min-width: 200px;
  max-width: 320px;
}
.visit-col {
  min-width: 132px;
  max-width: 200px;
  text-align: center;
}
.visit-cell {
  width: 140px;
  text-align: center;
  padding: 8px;
}

/* Fluid mode overrides */
.selection-matrix.fluid .subject-col,
.selection-matrix.fluid .subject-cell,
.selection-matrix.fluid .visit-col,
.selection-matrix.fluid .visit-cell {
  min-width: 0;
  max-width: none;
}

/* Buttons */
.select-btn {
  display: inline-block;
  width: 100%;
  min-width: 100px;
  max-width: 160px;
  color: #fff;
  border: none;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1.15;
  transition: opacity 0.15s ease-in-out, transform 0.02s ease-in-out;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.selection-matrix.fluid .select-btn {
  min-width: 0;
  max-width: none;
}
.select-btn:active {
  transform: translateY(1px);
}
.select-btn:hover {
  opacity: 0.9;
}

.select-btn.status-none {
  background: #9ca3af;
  color: #1f2937;
}
.select-btn.status-partial {
  background: #f59e0b;
}
.select-btn.status-complete {
  background: #16a34a;
}
.select-btn.status-skipped {
  background: #ef4444;
}

.selection-matrix tbody tr:nth-child(odd) .subject-cell {
  background: #fafafa;
}
.selection-matrix tbody tr:nth-child(odd) td:not(.subject-cell) {
  background: #fcfcfc;
}

.matrix-wrap::-webkit-scrollbar {
  height: 10px;
  width: 10px;
}
.matrix-wrap::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 8px;
}
.matrix-wrap::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* No subjects placeholder & button */
.no-subjects-placeholder {
  text-align: center;
  padding: 20px;
  color: #6b7280;
  font-style: italic;
  background: #fafafa;
}
.no-subjects-actions {
  margin-top: 12px;
}
.btn-add-subject-inline {
  padding: 8px 14px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  font-size: 14px;
  cursor: pointer;
}
.btn-add-subject-inline:hover {
  background: #e5e7eb;
}

@media (max-width: 900px) {
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
</style>
