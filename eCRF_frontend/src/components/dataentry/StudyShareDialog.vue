<template>
  <div v-if="visible" class="share-dialog-overlay" @click.self="handleClose">
    <div class="share-dialog">
      <div class="dialog-header">
        <div>
          <h3>
            {{ activeMode === "create" ? "Create Shared Link" : "Manage Shared Links" }}
          </h3>
          <p class="dialog-subtitle">
            <template v-if="activeMode === 'create'">
              Choose permission, expiry and which sections should be visible in the shared link.
            </template>
            <template v-else>
              View generated links, usage statistics and access status for this study.
            </template>
          </p>
        </div>

        <button
          type="button"
          class="icon-close"
          @click="handleClose"
          aria-label="Close share dialog"
        >
          ×
        </button>
      </div>

      <div class="share-mode-tabs">
        <button
          type="button"
          class="share-mode-tab"
          :class="{ active: activeMode === 'create' }"
          @click="switchMode('create')"
        >
          Create Shared Link
        </button>

        <button
          type="button"
          class="share-mode-tab"
          :class="{ active: activeMode === 'manage' }"
          @click="switchMode('manage')"
        >
          Manage Shared Links
        </button>
      </div>

      <!-- CREATE MODE -->
      <div v-if="activeMode === 'create'">
        <div class="share-info-card">
          <div class="info-row">
            <span class="info-label">Subject</span>
            <span class="info-value">{{ subjectLabel }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Group</span>
            <span class="info-value">{{ groupLabel || "Unassigned" }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Visit</span>
            <span class="info-value">{{ visitLabel }}</span>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-row">
            <label for="share-permission">Permission</label>
            <select id="share-permission" v-model="localPermission">
              <option value="view">View</option>
              <option value="add">Add Data</option>
            </select>
          </div>

          <div class="form-row">
            <label for="share-max-uses">Max Uses</label>
            <input
              id="share-max-uses"
              type="number"
              min="1"
              v-model.number="localMaxUses"
            />
          </div>

          <div class="form-row">
            <label for="share-expires-days">Expires (days)</label>
            <input
              id="share-expires-days"
              type="number"
              min="1"
              v-model.number="localExpiresInDays"
            />
          </div>
        </div>

        <div v-if="!bulkEnabled" class="form-row">
          <div class="sections-header">
            <label>Allowed Sections</label>

            <div class="sections-actions">
              <button type="button" class="btn-link" @click="selectAllSections">
                Select All
              </button>
              <button type="button" class="btn-link" @click="clearAllSections">
                Clear All
              </button>
            </div>
          </div>

          <div class="share-sections-box">
            <div
              v-if="normalizedSections.length"
              class="share-sections-list"
            >
              <label
                v-for="sec in normalizedSections"
                :key="sec.id"
                class="share-section-row"
              >
                <input
                  type="checkbox"
                  :value="sec.id"
                  v-model="selectedSectionIds"
                />
                <span class="section-title">{{ sec.title }}</span>
              </label>
            </div>

            <div v-else class="share-sections-empty">
              No sections available.
            </div>
          </div>

          <div class="selection-hint">
            {{ selectedSectionIds.length }} section(s) selected
          </div>
        </div>

        <!-- BULK GENERATION -->
        <div class="bulk-card">
          <label class="bulk-toggle">
            <input type="checkbox" v-model="bulkEnabled" />
            <span>Generate for multiple subjects</span>
          </label>

          <p class="bulk-help">
            Bulk links can only be generated for subjects in the same group as the selected subject
            because section assignments are group-specific. Subjects from other groups are not shown.
            To generate links for another group, select a subject from that group and open this dialog again.
          </p>

          <div v-if="bulkEnabled" class="bulk-grid">
            <div class="bulk-panel">
              <div class="bulk-panel-header">
                <strong>Subjects in {{ groupLabel || "Unassigned" }}</strong>
                <div class="bulk-panel-actions">
                  <button type="button" class="btn-link" @click="selectAllSameGroupSubjects">
                    Select All
                  </button>
                  <button type="button" class="btn-link" @click="clearSelectedSubjects">
                    Clear
                  </button>
                </div>
              </div>

              <div class="bulk-list">
                <label
                  v-for="subject in sameGroupSubjects"
                  :key="'bulk-subject-' + subject.index"
                  class="bulk-row"
                >
                  <input
                    type="checkbox"
                    :value="subject.index"
                    v-model="selectedSubjectIndexes"
                  />
                  <span>{{ subject.id }}</span>
                </label>

                <div v-if="!sameGroupSubjects.length" class="bulk-empty">
                  No subjects available in this group.
                </div>
              </div>
            </div>

            <div class="bulk-panel bulk-panel-wide">
              <div class="bulk-panel-header">
                <strong>Visits and sections</strong>
                <div class="bulk-panel-actions">
                  <button type="button" class="btn-link" @click="selectAllVisits">
                    Select All Visits
                  </button>
                  <button type="button" class="btn-link" @click="clearSelectedVisits">
                    Clear Visits
                  </button>
                </div>
              </div>

              <p class="bulk-help compact">
                Select the sections separately for each visit. Only sections assigned to
                {{ groupLabel || "this group" }} are shown for each visit.
              </p>

              <div class="visit-section-matrix">
                <div
                  v-for="visitRow in bulkVisitRows"
                  :key="'visit-section-row-' + visitRow.visitIndex"
                  class="visit-section-row"
                >
                  <div class="visit-section-main">
                    <label class="visit-check-row">
                      <input
                        type="checkbox"
                        :value="visitRow.visitIndex"
                        v-model="selectedVisitIndexes"
                      />
                      <strong>{{ visitRow.visitName }}</strong>
                    </label>

                    <div class="visit-section-actions">
                      <button
                        type="button"
                        class="btn-link"
                        :disabled="!isBulkVisitSelected(visitRow.visitIndex) || !visitRow.sections.length"
                        @click="selectAllBulkSectionsForVisit(visitRow.visitIndex)"
                      >
                        Select All Sections
                      </button>

                      <button
                        type="button"
                        class="btn-link"
                        :disabled="!isBulkVisitSelected(visitRow.visitIndex) || !visitRow.sections.length"
                        @click="clearBulkSectionsForVisit(visitRow.visitIndex)"
                      >
                        Clear Sections
                      </button>
                    </div>
                  </div>

                  <div v-if="visitRow.sections.length" class="visit-section-options">
                    <label
                      v-for="section in visitRow.sections"
                      :key="'visit-' + visitRow.visitIndex + '-section-' + section.id"
                      class="visit-section-option"
                      :class="{ disabled: !isBulkVisitSelected(visitRow.visitIndex) }"
                    >
                      <input
                        type="checkbox"
                        :checked="isBulkSectionSelected(visitRow.visitIndex, section.id)"
                        :disabled="!isBulkVisitSelected(visitRow.visitIndex)"
                        @change="toggleBulkSectionForVisit(visitRow.visitIndex, section.id, $event.target.checked)"
                      />
                      <span>{{ section.title }}</span>
                    </label>
                  </div>

                  <div v-else class="bulk-empty left">
                    No sections are assigned for this group and visit.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="bulkEnabled" class="bulk-preview">
            <div class="bulk-preview-title">
              Preview: {{ readyBulkRowCount }} ready / {{ bulkPreviewRows.length }} total
            </div>

            <div class="bulk-preview-table-wrap">
              <table class="bulk-preview-table">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Group</th>
                    <th>Visit</th>
                    <th>Selected Sections</th>
                    <th>Status</th>
                    <th>Message</th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="row in bulkPreviewRows"
                    :key="row.subjectIndex + '-' + row.visitIndex"
                  >
                    <td>{{ row.subjectId }}</td>
                    <td>{{ row.group || "Unassigned" }}</td>
                    <td>{{ row.visitName }}</td>
                    <td>
                      <span v-if="row.sectionTitles.length">
                        {{ row.sectionTitles.join(", ") }}
                      </span>
                      <span v-else>—</span>
                    </td>
                    <td>
                      <span
                        class="status-pill"
                        :class="{
                          'is-active': row.status === 'Ready',
                          'is-expired': row.status !== 'Ready'
                        }"
                      >
                        {{ row.status }}
                      </span>
                    </td>
                    <td>{{ row.message }}</td>
                  </tr>

                  <tr v-if="!bulkPreviewRows.length">
                    <td colspan="6" class="manager-empty-cell">
                      Select at least one subject and one visit.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SINGLE GENERATED LINK -->
        <div v-if="generatedLink" class="generated-link-card">
          <label class="generated-label">Generated Link</label>

          <div class="generated-link-row">
            <input
              class="generated-link-input"
              type="text"
              :value="generatedLink"
              readonly
            />
            <button type="button" class="btn-copy" @click="$emit('copy')">
              Copy
            </button>
          </div>

          <div v-if="copyStatus" class="copy-status">
            {{ copyStatus }}
          </div>
        </div>

        <!-- BULK GENERATED LINKS -->
        <div v-if="generatedLinks.length" class="generated-link-card">
          <div class="generated-bulk-header">
            <label class="generated-label">
              Generated Links: {{ generatedLinks.length }}
            </label>

            <button
              type="button"
              class="btn-secondary btn-small"
              @click="$emit('export-links', generatedLinks)"
            >
              Export CSV
            </button>
          </div>

          <div class="generated-links-list">
            <div
              v-for="link in generatedLinks"
              :key="link.token || link.link"
              class="generated-link-item"
            >
              <div>
                <strong>{{ link.subjectId }}</strong>
                <span> — {{ link.visitName }}</span>
              </div>

              <button
                type="button"
                class="btn-link"
                @click="$emit('copy-link', link)"
              >
                Copy
              </button>
            </div>
          </div>

          <div v-if="copyStatus" class="copy-status">
            {{ copyStatus }}
          </div>
        </div>

        <div class="dialog-actions">
          <button type="button" class="btn-secondary" @click="handleClose">
            Cancel
          </button>

          <button
              v-if="!generatedLink && !generatedLinks.length && !bulkEnabled"
              type="button"
              class="btn-primary"
              :disabled="generating || !selectedSectionIds.length"
              @click="onGenerate"
            >
              {{ generating ? "Generating Link…" : "Generate Link" }}
            </button>

          <button
              v-if="!generatedLink && !generatedLinks.length && bulkEnabled"
              type="button"
              class="btn-primary"
              :disabled="generating || readyBulkRowCount === 0"
              @click="onBulkGenerate"
            >
              {{ generating ? "Generating Link…" : `Generate ${readyBulkRowCount} Link(s)` }}
            </button>
        </div>
      </div>

      <!-- MANAGE MODE -->
      <div v-else class="shared-link-manager">
        <div class="manager-header">
          <div>
            <h4>Shared links</h4>
            <p>
              View generated links, usage, expiry and access status for this study.
            </p>
          </div>

          <button
            type="button"
            class="btn-secondary"
            @click="$emit('export-links', sharedLinks)"
            :disabled="!sharedLinks.length"
          >
            Export CSV
          </button>
        </div>

        <div v-if="sharedLinksLoading" class="manager-empty">
          Loading shared links…
        </div>

        <div v-else-if="!sharedLinks.length" class="manager-empty">
          No shared links generated yet.
        </div>

        <div v-else class="manager-table-wrap">
          <table class="manager-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Group</th>
                <th>Visit</th>
                <th>Sections</th>
                <th>Permission</th>
                <th>Usage</th>
                <th>Status</th>
                <th>Expiry</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="link in sharedLinks" :key="link.token">
                <td>{{ link.subject_id || link.subjectId || "—" }}</td>
                <td>{{ link.group || "—" }}</td>
                <td>{{ link.visit_name || link.visitName || "—" }}</td>
                <td>
                  <span class="sections-inline">
                    {{
                      Array.isArray(link.section_titles)
                        ? link.section_titles.join(", ")
                        : Array.isArray(link.sections)
                          ? link.sections.join(", ")
                          : "—"
                    }}
                  </span>
                </td>
                <td>{{ link.permission || "—" }}</td>
                <td>{{ link.used_count ?? 0 }} / {{ link.max_uses ?? "—" }}</td>
                <td>
                  <span class="status-pill" :class="statusClass(link.status)">
                    {{ link.status || "Active" }}
                  </span>
                </td>
                <td>{{ formatDate(link.expires_at) }}</td>
                <td class="manager-actions">
                  <button
                    type="button"
                    class="btn-link"
                    @click="$emit('copy-link', link)"
                  >
                    Copy
                  </button>

                  <button
                    type="button"
                    class="btn-link danger"
                    :disabled="String(link.status || 'Active').toLowerCase() !== 'active'"
                    @click="$emit('revoke-link', link)"
                  >
                    Invalidate
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <div v-if="copyStatus" class="copy-status manager-copy-status">
            {{ copyStatus }}
          </div>
        </div>

        <div class="dialog-actions">
          <button type="button" class="btn-secondary" @click="handleClose">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "StudyShareDialog",

  props: {
    visible: { type: Boolean, default: false },
    subjectLabel: { type: String, default: "N/A" },
    visitLabel: { type: String, default: "N/A" },

    permission: { type: String, default: "view" },
    maxUses: { type: Number, default: 1 },
    expiresInDays: { type: Number, default: 7 },
    studyName: { type: String, default: "" },
    groupLabel: { type: String, default: "" },
    sameGroupSubjects: { type: Array, default: () => [] },
    visits: { type: Array, default: () => [] },
    sectionAvailabilityByVisit: { type: Object, default: () => ({}) },
    generatedLinks: { type: Array, default: () => [] },
    sharedLinks: { type: Array, default: () => [] },
    sharedLinksLoading: { type: Boolean, default: false },

    availableSections: {
      type: Array,
      default: () => [],
    },

    generatedLink: { type: String, default: "" },
    copyStatus: { type: String, default: "" },
    generating: { type: Boolean, default: false },
  },

  emits: [
  "close",
  "generate",
  "bulk-generate",
  "copy",
  "copy-link",
  "load-shared-links",
  "revoke-link",
  "export-links",
],

  data() {
      return {
        localPermission: "view",
        localMaxUses: 1,
        localExpiresInDays: 7,
        selectedSectionIds: [],
        activeMode: "create",
        bulkEnabled: false,
        selectedSubjectIndexes: [],
        selectedVisitIndexes: [],
        bulkSelectedSectionIdsByVisit: {},
      };
    },

  computed: {
      normalizedSections() {
        return (this.availableSections || [])
          .map((s, idx) => ({
            id: String(s?.id || `section-${idx}`).trim(),
            title: s?.title || s?.label || `Section ${idx + 1}`,
          }))
          .filter((s) => s.id);
      },

      currentSectionTitleById() {
        const out = {};

        this.normalizedSections.forEach((section) => {
          out[section.id] = section.title;
        });

        return out;
      },

      bulkVisitRows() {
        const visits = Array.isArray(this.visits) ? this.visits : [];

        return visits.map((visit, visitIdx) => {
          const rawSections = this.sectionAvailabilityByVisit?.[visitIdx] || [];

          const sections = rawSections
            .map((section, sectionIdx) => {
              if (typeof section === "string" || typeof section === "number") {
                const id = String(section).trim();

                return {
                  id,
                  title: this.currentSectionTitleById[id] || id || `Section ${sectionIdx + 1}`,
                };
              }

              const id = String(
                section?.id ||
                section?._id ||
                section?.uuid ||
                `section-${visitIdx}-${sectionIdx}`
              ).trim();

              return {
                id,
                title:
                  section?.title ||
                  section?.label ||
                  this.currentSectionTitleById[id] ||
                  `Section ${sectionIdx + 1}`,
              };
            })
            .filter((section) => section.id);

          return {
            visitIndex: visitIdx,
            visitName: visit?.name || `Visit ${visitIdx + 1}`,
            sections,
          };
        });
      },

      bulkPreviewRows() {
        if (!this.bulkEnabled) return [];

        const rows = [];

        this.selectedSubjectIndexes.forEach((subjectIndex) => {
          const subject = this.sameGroupSubjects.find(
            (s) => Number(s.index) === Number(subjectIndex)
          );

          if (!subject) return;

          this.selectedVisitIndexes.forEach((visitIndex) => {
            const visitRow = this.bulkVisitRows.find(
              (row) => Number(row.visitIndex) === Number(visitIndex)
            );

            if (!visitRow) return;

            const availableSectionIds = visitRow.sections.map((section) => section.id);
            const selectedIds = (this.bulkSelectedSectionIdsByVisit?.[visitIndex] || [])
              .map((id) => String(id).trim())
              .filter((id) => availableSectionIds.includes(id));

            const selectedTitles = selectedIds.map((id) => {
              const matched = visitRow.sections.find((section) => section.id === id);
              return matched?.title || id;
            });

            rows.push({
              subjectIndex: Number(subjectIndex),
              subjectId: subject.id,
              group: subject.group,
              visitIndex: Number(visitIndex),
              visitName: visitRow.visitName,
              sectionIds: selectedIds,
              sectionTitles: selectedTitles,
              status: selectedIds.length ? "Ready" : "Error",
              message: selectedIds.length
                ? "Ready"
                : "No sections selected for this visit.",
            });
          });
        });

        return rows;
      },

      readyBulkRowCount() {
        return this.bulkPreviewRows.filter((row) => row.status === "Ready").length;
      },
    },

  watch: {
      visible: {
        immediate: true,
        handler(val) {
          if (val) {
            this.localPermission = this.permission || "view";
            this.localMaxUses = Number(this.maxUses) || 1;
            this.localExpiresInDays = Number(this.expiresInDays) || 7;
            this.selectedSectionIds = this.normalizedSections.map((s) => s.id);

            this.bulkEnabled = false;
            this.activeMode = "create";
            this.selectedSubjectIndexes = this.sameGroupSubjects.map((s) => s.index);

            // Default bulk flow: all visits selected.
            this.selectedVisitIndexes = this.visits.map((_, idx) => idx);

            this.rebuildBulkSectionSelections();
          }
        },
      },

      availableSections: {
        immediate: true,
        deep: true,
        handler() {
          const validIds = this.normalizedSections.map((s) => s.id);

          if (!this.selectedSectionIds.length) {
            this.selectedSectionIds = [...validIds];
          } else {
            this.selectedSectionIds = this.selectedSectionIds.filter((id) =>
              validIds.includes(id)
            );
          }

          this.rebuildBulkSectionSelections();
        },
      },

      sectionAvailabilityByVisit: {
        deep: true,
        handler() {
          this.rebuildBulkSectionSelections();
        },
      },

      sameGroupSubjects: {
        deep: true,
        handler() {
          const validIndexes = this.sameGroupSubjects.map((s) => s.index);

          this.selectedSubjectIndexes = this.selectedSubjectIndexes.filter((idx) =>
            validIndexes.includes(idx)
          );

          if (!this.selectedSubjectIndexes.length) {
            this.selectedSubjectIndexes = [...validIndexes];
          }
        },
      },

      visits: {
        deep: true,
        handler() {
          const validIndexes = this.visits.map((_, idx) => idx);

          this.selectedVisitIndexes = this.selectedVisitIndexes.filter((idx) =>
            validIndexes.includes(idx)
          );

          if (!this.selectedVisitIndexes.length) {
            this.selectedVisitIndexes = [...validIndexes];
          }

          this.rebuildBulkSectionSelections();
        },
      },
    },

  methods: {

    selectAllSameGroupSubjects() {
      this.selectedSubjectIndexes = this.sameGroupSubjects.map((s) => s.index);
    },

    clearSelectedSubjects() {
      this.selectedSubjectIndexes = [];
    },

    selectAllVisits() {
      this.selectedVisitIndexes = this.visits.map((_, idx) => idx);
      this.rebuildBulkSectionSelections();
    },

    clearSelectedVisits() {
      this.selectedVisitIndexes = [];
    },
        getBulkVisitSectionIds(visitIndex) {
      const visitRow = this.bulkVisitRows.find(
        (row) => Number(row.visitIndex) === Number(visitIndex)
      );

      if (!visitRow) return [];

      return visitRow.sections.map((section) => section.id);
    },

    rebuildBulkSectionSelections() {
      const next = { ...(this.bulkSelectedSectionIdsByVisit || {}) };

      this.bulkVisitRows.forEach((visitRow) => {
        const availableIds = visitRow.sections.map((section) => section.id);
        const existing = Array.isArray(next[visitRow.visitIndex])
          ? next[visitRow.visitIndex]
          : [];

        const filteredExisting = existing.filter((id) =>
          availableIds.includes(id)
        );

        // Default each visit to all sections assigned for that visit.
        next[visitRow.visitIndex] = filteredExisting.length
          ? filteredExisting
          : [...availableIds];
      });

      this.bulkSelectedSectionIdsByVisit = next;
    },

    isBulkVisitSelected(visitIndex) {
      return this.selectedVisitIndexes
        .map((idx) => Number(idx))
        .includes(Number(visitIndex));
    },

    isBulkSectionSelected(visitIndex, sectionId) {
      const selected = this.bulkSelectedSectionIdsByVisit?.[visitIndex] || [];
      return selected.includes(sectionId);
    },

    toggleBulkSectionForVisit(visitIndex, sectionId, checked) {
      const current = this.bulkSelectedSectionIdsByVisit?.[visitIndex] || [];
      let next;

      if (checked) {
        next = current.includes(sectionId)
          ? current
          : [...current, sectionId];
      } else {
        next = current.filter((id) => id !== sectionId);
      }

      this.bulkSelectedSectionIdsByVisit = {
        ...(this.bulkSelectedSectionIdsByVisit || {}),
        [visitIndex]: next,
      };
    },

    selectAllBulkSectionsForVisit(visitIndex) {
      this.bulkSelectedSectionIdsByVisit = {
        ...(this.bulkSelectedSectionIdsByVisit || {}),
        [visitIndex]: this.getBulkVisitSectionIds(visitIndex),
      };
    },

    clearBulkSectionsForVisit(visitIndex) {
      this.bulkSelectedSectionIdsByVisit = {
        ...(this.bulkSelectedSectionIdsByVisit || {}),
        [visitIndex]: [],
      };
    },
    onBulkGenerate() {
      this.$emit("bulk-generate", {
        permission: this.localPermission,
        maxUses: Math.max(1, Number(this.localMaxUses) || 1),
        expiresInDays: Math.max(1, Number(this.localExpiresInDays) || 7),

        // Bulk uses row.sectionIds because each visit can have different sections.
        allowed_section_ids: [],
        rows: this.bulkPreviewRows,
      });
    },

    switchMode(mode) {
      this.activeMode = mode;

      if (mode === "manage") {
        this.$emit("load-shared-links");
      }
    },
    handleClose() {
      this.$emit("close");
    },

    selectAllSections() {
      this.selectedSectionIds = this.normalizedSections.map((s) => s.id);
    },

    clearAllSections() {
      this.selectedSectionIds = [];
    },

    onGenerate() {
      this.$emit("generate", {
        permission: this.localPermission,
        maxUses: Math.max(1, Number(this.localMaxUses) || 1),
        expiresInDays: Math.max(1, Number(this.localExpiresInDays) || 7),
        allowed_section_ids: [...this.selectedSectionIds],
      });
    },
     formatDate(value) {
      if (!value) return "—";

      try {
        return new Date(value).toLocaleString();
      } catch {
        return value;
      }
    },

    statusClass(status) {
      const s = String(status || "Active").toLowerCase();

      return {
        "is-active": s === "active",
        "is-expired": s.includes("expired") || s.includes("invalid") || s.includes("revoked"),
        "is-used": s.includes("usage"),
      };
    },
  },
};
</script>

<style scoped>
.share-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.share-dialog {
  width: min(980px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
  padding: 22px;
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.dialog-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.dialog-subtitle {
  margin: 6px 0 0 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.45;
}

.icon-close {
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
}

.icon-close:hover {
  background: #f3f4f6;
  color: #111827;
}

.share-info-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}

.info-row + .info-row {
  margin-top: 8px;
}

.info-label {
  color: #6b7280;
  font-weight: 600;
}

.info-value {
  color: #111827;
  font-weight: 500;
  text-align: right;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.form-row {
  margin-bottom: 14px;
}

.form-row label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.form-row input,
.form-row select {
  width: 100%;
  min-height: 40px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  color: #111827;
  background: #ffffff;
  box-sizing: border-box;
}

.form-row input:focus,
.form-row select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.sections-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.sections-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-link {
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.btn-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.share-sections-box {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
  padding: 10px;
}

.share-sections-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}

.share-section-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
}

.share-section-row:hover {
  background: #f3f4f6;
}

.share-section-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin: 0;
  flex: 0 0 auto;
}

.section-title {
  font-size: 14px;
  color: #111827;
}

.share-sections-empty {
  padding: 12px;
  font-size: 13px;
  color: #6b7280;
  text-align: center;
}

.selection-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.generated-link-card {
  margin-top: 10px;
  margin-bottom: 8px;
  padding: 12px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 10px;
}

.generated-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1e3a8a;
}

.generated-link-row {
  display: flex;
  gap: 10px;
}

.generated-link-input {
  flex: 1;
  min-width: 0;
  min-height: 40px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
  color: #111827;
}

.copy-status {
  margin-top: 8px;
  font-size: 12px;
  color: #15803d;
  font-weight: 600;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-primary,
.btn-secondary,
.btn-copy {
  min-height: 40px;
  border-radius: 8px;
  padding: 0 14px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: none;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-secondary {
  background: #f3f4f6;
  color: #111827;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-copy {
  background: #111827;
  color: #ffffff;
  border: none;
  white-space: nowrap;
}

.btn-copy:hover {
  background: #1f2937;
}

@media (max-width: 640px) {
  .share-dialog {
    padding: 16px;
    border-radius: 12px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .generated-link-row {
    flex-direction: column;
  }

  .dialog-actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary,
  .btn-copy {
    width: 100%;
  }
}
.share-mode-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.share-mode-tab {
  border: none;
  background: transparent;
  padding: 10px 12px;
  font-size: 14px;
  font-weight: 700;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 3px solid transparent;
}

.share-mode-tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.bulk-card {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 10px;
}

.bulk-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}

.bulk-toggle input {
  width: 16px;
  height: 16px;
}

.bulk-help {
  margin: 8px 0 0;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.45;
}

.bulk-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.bulk-panel {
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 10px;
}

.bulk-panel-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 13px;
}

.bulk-panel-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.bulk-list {
  max-height: 180px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bulk-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  background: #ffffff;
}

.bulk-row input {
  width: 16px;
  height: 16px;
}

.bulk-empty {
  padding: 10px;
  font-size: 12px;
  color: #6b7280;
  text-align: center;
}

.bulk-preview {
  margin-top: 12px;
}

.bulk-preview-title {
  font-size: 13px;
  font-weight: 800;
  color: #1f2937;
  margin-bottom: 8px;
}

.bulk-preview-table-wrap,
.manager-table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}

.bulk-preview-table,
.manager-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.bulk-preview-table th,
.bulk-preview-table td,
.manager-table th,
.manager-table td {
  padding: 9px 10px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}

.bulk-preview-table th,
.manager-table th {
  background: #f9fafb;
  color: #374151;
  font-weight: 800;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.manager-header h4 {
  margin: 0;
  font-size: 16px;
  color: #111827;
}

.manager-header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.manager-empty,
.manager-empty-cell {
  padding: 18px;
  text-align: center;
  color: #6b7280;
  background: #f9fafb;
  line-height: 1.45;
}

.manager-empty {
  border: 1px dashed #d1d5db;
  border-radius: 10px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.status-pill.is-active {
  color: #14532d;
  background: #dcfce7;
  border: 1px solid #86efac;
}

.status-pill.is-expired,
.status-pill.is-used {
  color: #7f1d1d;
  background: #fee2e2;
  border: 1px solid #fca5a5;
}

.manager-actions {
  white-space: nowrap;
}

.manager-actions .btn-link + .btn-link {
  margin-left: 10px;
}

.btn-link.danger {
  color: #dc2626;
}

.btn-link.danger:disabled {
  color: #9ca3af;
  cursor: not-allowed;
  text-decoration: none;
}

.sections-inline {
  display: inline-block;
  max-width: 220px;
  white-space: normal;
}

.generated-bulk-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}

.generated-links-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.generated-link-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #ffffff;
  font-size: 13px;
}

.btn-small {
  min-height: 32px;
  padding: 0 10px;
  font-size: 12px;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.manager-copy-status {
  padding: 8px 10px;
}

@media (max-width: 760px) {
  .bulk-grid {
    grid-template-columns: 1fr;
  }

  .manager-header,
  .generated-bulk-header {
    flex-direction: column;
    align-items: stretch;
  }
}
.bulk-panel-wide {
  min-width: 0;
}

.visit-section-matrix {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.visit-section-row {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}

.visit-section-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.visit-check-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #111827;
}

.visit-check-row input {
  width: 16px;
  height: 16px;
}

.visit-section-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.visit-section-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.visit-section-option {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 9px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #eff6ff;
  color: #1f2937;
  font-size: 12px;
  font-weight: 700;
}

.visit-section-option.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.visit-section-option input {
  width: 14px;
  height: 14px;
}

.bulk-help.compact {
  margin-bottom: 10px;
}

.bulk-empty.left {
  text-align: left;
}
</style>