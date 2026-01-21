<template>
  <div
    class="study-view-layout"
    :class="{ 'sv-dashboard-fullscreen': activeTab === 'viewdata' && dashboardFullscreen }"
  >
    <header class="sv-header" v-if="!(activeTab === 'viewdata' && dashboardFullscreen)">
      <button class="btn-minimal back-btn" @click="goBackToDashboard" aria-label="Back to Dashboard">Back</button>
      <div class="title-wrap">
        <h1 class="sv-title">{{ studyMeta.study_name || 'Study' }}</h1>
        <p class="sv-subtitle" v-if="studyMeta.study_description">{{ studyMeta.study_description }}</p>
      </div>
      <div class="header-spacer" aria-hidden="true"></div>
    </header>

    <div
      class="sv-content card"
      :class="{
        'sv-viewdata': activeTab === 'viewdata',
        'sv-sidebar-collapsed': activeTab === 'viewdata' && dataSidebarCollapsed,
        'sv-dashboard-fullscreen': activeTab === 'viewdata' && dashboardFullscreen
      }"
    >
      <!-- Vertical Tabs -->
      <aside
        v-if="!(activeTab === 'viewdata' && dashboardFullscreen)"
        class="v-tabs"
        :class="{ collapsed: activeTab === 'viewdata' && dataSidebarCollapsed }"
        role="tablist"
        aria-orientation="vertical"
      >
        <!--  Collapse/Expand icon only for View Data tab -->
        <div class="v-tabs-tools" v-if="activeTab === 'viewdata'">
          <button
            class="btn-minimal icon-only"
            type="button"
            @click="toggleDataSidebar"
            :title="dataSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
            :aria-label="dataSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          >
            <i :class="dataSidebarCollapsed ? icons.chevronRight : icons.chevronLeft"></i>
          </button>
        </div>

        <button
          v-for="t in visibleTabs"
          :key="t.key"
          :class="['v-tab', { active: activeTab === t.key }]"
          @click="activeTab = t.key"
          role="tab"
          :aria-selected="activeTab === t.key"
          :title="t.label"
        >
          {{ (activeTab === 'viewdata' && dataSidebarCollapsed) ? tabAbbrev(t.label) : t.label }}
        </button>
      </aside>

      <!-- Panels -->
      <section class="v-panel" :class="{ 'v-panel-tight': activeTab === 'viewdata' }">
        <!-- META-DATA -->
        <div v-if="activeTab === 'meta'">
          <h2 class="panel-title center">Meta-data</h2>

          <!-- Core meta (only show fields that have values) -->
          <div class="meta-grid">
            <div class="meta-item" v-if="hasValue(studyMeta.id)">
              <div class="meta-label">Study ID</div>
              <div class="meta-value monospace">{{ studyMeta.id }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.study_name)">
              <div class="meta-label">Name</div>
              <div class="meta-value">{{ studyMeta.study_name }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.study_description)">
              <div class="meta-label">Description</div>
              <div class="meta-value">{{ studyMeta.study_description }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.created_by_display)">
              <div class="meta-label">Created By</div>
              <div class="meta-value">{{ studyMeta.created_by_display }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.created_at)">
              <div class="meta-label">Created At</div>
              <div class="meta-value">{{ formatDateTime(studyMeta.created_at) }}</div>
            </div>
            <div class="meta-item" v-if="hasValue(studyMeta.updated_at)">
              <div class="meta-label">Updated At</div>
              <div class="meta-value">{{ formatDateTime(studyMeta.updated_at) }}</div>
            </div>
          </div>

          <!-- Collapsible meta sections (collapsed by default) -->
          <div class="meta-sections">
            <!-- Study Data -->
            <div class="meta-section">
              <div class="meta-section-head">
                <h3 class="sub-title">Study Data</h3>
                <button
                  class="btn-minimal icon-only meta-toggle"
                  type="button"
                  @click="toggleMetaSection('studyData')"
                  :title="metaCollapsed.studyData ? 'Expand' : 'Collapse'"
                  :aria-label="metaCollapsed.studyData ? 'Expand Study Data' : 'Collapse Study Data'"
                  :aria-expanded="(!metaCollapsed.studyData).toString()"
                >
                  <i :class="metaCollapsed.studyData ? icons.toggleDown : icons.toggleUp"></i>
                </button>
              </div>
              <div class="meta-section-body" v-show="!metaCollapsed.studyData">
                <div v-if="studyKVEntries.length" class="kv-grid">
                  <div class="kv-row" v-for="entry in studyKVEntries" :key="entry[0]">
                    <div class="kv-key">{{ prettyLabel(entry[0]) }}</div>
                    <div class="kv-val">{{ formatAny(entry[1]) }}</div>
                  </div>
                </div>
                <div v-else class="empty-state">No additional study data.</div>
              </div>
            </div>

            <!-- Groups -->
            <div class="meta-section">
              <div class="meta-section-head">
                <h3 class="sub-title">Groups</h3>
                <button
                  class="btn-minimal icon-only meta-toggle"
                  type="button"
                  @click="toggleMetaSection('groups')"
                  :title="metaCollapsed.groups ? 'Expand' : 'Collapse'"
                  :aria-label="metaCollapsed.groups ? 'Expand Groups' : 'Collapse Groups'"
                  :aria-expanded="(!metaCollapsed.groups).toString()"
                >
                  <i :class="metaCollapsed.groups ? icons.toggleDown : icons.toggleUp"></i>
                </button>
              </div>
              <div class="meta-section-body" v-show="!metaCollapsed.groups">
                <div v-if="groups && groups.length" class="list-grid">
                  <div class="list-card" v-for="(g, gi) in groups" :key="gi">
                    <div class="kv-row" v-for="entry in objectEntriesFiltered(g)" :key="entry[0]">
                      <div class="kv-key">{{ prettyLabel(entry[0]) }}</div>
                      <div class="kv-val">{{ formatAny(entry[1]) }}</div>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-state">No groups defined.</div>
              </div>
            </div>

            <!-- Visits -->
            <div class="meta-section">
              <div class="meta-section-head">
                <h3 class="sub-title">Visits</h3>
                <button
                  class="btn-minimal icon-only meta-toggle"
                  type="button"
                  @click="toggleMetaSection('visits')"
                  :title="metaCollapsed.visits ? 'Expand' : 'Collapse'"
                  :aria-label="metaCollapsed.visits ? 'Expand Visits' : 'Collapse Visits'"
                  :aria-expanded="(!metaCollapsed.visits).toString()"
                >
                  <i :class="metaCollapsed.visits ? icons.toggleDown : icons.toggleUp"></i>
                </button>
              </div>
              <div class="meta-section-body" v-show="!metaCollapsed.visits">
                <div v-if="visits && visits.length" class="list-grid">
                  <div class="list-card" v-for="(v, vi) in visits" :key="vi">
                    <div class="kv-row" v-for="entry in objectEntriesFiltered(v)" :key="entry[0]">
                      <div class="kv-key">{{ prettyLabel(entry[0]) }}</div>
                      <div class="kv-val">{{ formatAny(entry[1]) }}</div>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-state">No visits defined.</div>
              </div>
            </div>

            <!-- Subject Assignment -->
            <div class="meta-section">
              <div class="meta-section-head">
                <h3 class="sub-title">Subject Assignment</h3>
                <button
                  class="btn-minimal icon-only meta-toggle"
                  type="button"
                  @click="toggleMetaSection('assignment')"
                  :title="metaCollapsed.assignment ? 'Expand' : 'Collapse'"
                  :aria-label="metaCollapsed.assignment ? 'Expand Subject Assignment' : 'Collapse Subject Assignment'"
                  :aria-expanded="(!metaCollapsed.assignment).toString()"
                >
                  <i :class="metaCollapsed.assignment ? icons.toggleDown : icons.toggleUp"></i>
                </button>
              </div>
              <div class="meta-section-body" v-show="!metaCollapsed.assignment">
                <div class="kv-grid">
                  <div class="kv-row" v-if="hasValue(studyData.assignmentMethod)">
                    <div class="kv-key">Assignment Method</div>
                    <div class="kv-val">{{ studyData.assignmentMethod }}</div>
                  </div>
                  <div class="kv-row" v-if="hasValue(studyData.subjectCount)">
                    <div class="kv-key">Subjects Planned</div>
                    <div class="kv-val">{{ studyData.subjectCount }}</div>
                  </div>
                  <div class="kv-row" v-if="Array.isArray(subjects)">
                    <div class="kv-key">Subjects Enrolled</div>
                    <div class="kv-val">{{ subjects.length }}</div>
                  </div>
                  <div class="kv-row" v-if="assignmentSize">
                    <div class="kv-key">Assignment Matrix</div>
                    <div class="kv-val">
                      {{ assignmentSize.m }} × {{ assignmentSize.v }} × {{ assignmentSize.g }}
                      <span class="muted">(models × visits × groups)</span>
                    </div>
                  </div>
                </div>

                <!-- Per-Subject Group mapping (PI/Admin only) -->
                <div v-if="isPIOrAdmin" class="per-subject-block">
                  <h4 class="per-subject-title">Per-Subject Group Assignment</h4>
                  <div v-if="subjectAssignments.length" class="ps-table-wrap">
                    <table class="ps-table" aria-label="Per-subject group assignment">
                      <thead>
                        <tr>
                          <th scope="col">Subject ID</th>
                          <th scope="col">Assigned Group</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="row in subjectAssignments" :key="row.subjectId">
                          <td class="monospace">{{ row.subjectId }}</td>
                          <td>{{ row.groupName || '—' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div v-else class="empty-state">No subjects enrolled yet.</div>
                </div>
              </div>
            </div>

            <!-- Template Versions -->
            <div class="meta-section">
              <div class="meta-section-head">
                <h3 class="sub-title">Template Versions</h3>
                <button
                  class="btn-minimal icon-only meta-toggle"
                  type="button"
                  @click="toggleMetaSection('versions')"
                  :title="metaCollapsed.versions ? 'Expand' : 'Collapse'"
                  :aria-label="metaCollapsed.versions ? 'Expand Template Versions' : 'Collapse Template Versions'"
                  :aria-expanded="(!metaCollapsed.versions).toString()"
                >
                  <i :class="metaCollapsed.versions ? icons.toggleDown : icons.toggleUp"></i>
                </button>
              </div>

              <div class="meta-section-body" v-show="!metaCollapsed.versions">
                <div class="versions-wrap">
                  <div v-if="versionsLoading" class="muted">Loading versions…</div>
                  <div v-else-if="!versions.length" class="empty-state">No template versions yet.</div>

                  <div v-else class="version-list">
                    <div class="version-card" v-for="(v, idx) in versions" :key="`ver-${v.version}`">
                      <div class="vc-head">
                        <div class="vc-title">
                          <span class="tag">v{{ v.version }}</span>
                          <span class="vc-date">{{ formatDateTime(v.created_at) }}</span>
                          <span v-if="idx === versions.length - 1" class="pill ok">Latest</span>
                        </div>

                        <div class="vc-summary" v-if="v.version > 1">
                          <template v-if="canShowVersionDetails && versionDiffs[v.version]">
                            <span class="muted">Changes from v{{ v.version - 1 }}:</span>
                            <span class="vc-summary-line">{{ versionDiffs[v.version].summary }}</span>
                          </template>
                          <template v-else>
                            <span class="muted">Changes from previous version are hidden (insufficient permission).</span>
                          </template>
                        </div>
                      </div>

                      <!-- Details -->
                      <details v-if="v.version > 1 && canShowVersionDetails && versionDiffs[v.version]">
                        <summary>Show details</summary>
                        <div class="vc-details diff-scroll">
                          <TemplateDiffView
                            :from="versionSchemas[v.version - 1]"
                            :to="versionSchemas[v.version]"
                            compact
                          />
                        </div>
                      </details>

                      <div v-else-if="v.version === 1" class="muted">Initial version.</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!--  EDIT STUDY TAB -->
        <div v-else-if="activeTab === 'edit'">
          <h2 class="panel-title center">Edit Study</h2>

          <p class="muted center" style="margin-top:-6px;">
            Choose exactly what you want to edit. Each step can be saved independently.
          </p>

          <div class="edit-steps-grid">
            <button
              v-for="s in editSteps"
              :key="s.step"
              class="edit-step-card"
              @click="openEditStep(s.step)"
              :disabled="!canEditStudy"
            >
              <div class="esc-title">{{ s.label }}</div>
              <div class="esc-desc">{{ s.desc }}</div>
            </button>
          </div>

          <div class="edit-hint muted">
            Tip: This will open the individual steps in edit mode with a dedicated Save button.
          </div>
        </div>

        <!-- DOCUMENTS -->
        <div v-else-if="activeTab === 'docs'">
          <h2 class="panel-title center">Study Documents</h2>

          <h3 class="sub-title">Existing Study Attachments</h3>
          <div v-if="studyLevelFiles.length" class="doc-list">
            <div v-for="doc in studyLevelFiles" :key="doc.id || doc.file_name" class="doc-item">
              <div class="doc-name">{{ doc.file_name || doc.name || 'Document' }}</div>
              <div class="doc-meta muted">
                {{ doc.storage_option || 'file' }}
                <span v-if="doc.bytes || doc.size"> • </span>
                <span v-if="doc.bytes">{{ prettyBytes(doc.bytes) }}</span>
                <span v-else-if="doc.size">{{ prettyBytes(doc.size) }}</span>
              </div>
              <div v-if="doc.description" class="doc-desc">{{ doc.description }}</div>
              <div class="doc-path" :title="docPathTooltip(doc)">
                <span class="label">On disk:</span>
                <span class="file-path">{{ docRelativePath(doc) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">No study-level attachments yet.</div>

          <!-- Attach New Study Documents -->
          <div class="subsection">
            <h3 class="sub-title">Attach New Study Documents</h3>

            <div class="attach-row">
              <FieldFileUpload
                :value="attachTempValue"
                :constraints="{ allowMultipleFiles: true, storagePreference: 'local' }"
                :readonly="uploading"
                stage="runtime"
                @input="onAttachTempChange"
                @file-selected="onFilesSelected"
              />
            </div>

            <div v-if="pendingFiles.length" class="pending-list">
              <div class="pending-item" v-for="(p, idx) in pendingFiles" :key="p.key">
                <div class="pi-head">
                  <div class="pi-name" :title="p.file.name">{{ p.file.name }}</div>
                  <div class="pi-size">{{ prettyBytes(p.file.size) }}</div>
                  <button class="icon-inline danger" type="button" @click="removePending(idx)" title="Remove">✕</button>
                </div>
                <label class="pi-desc-label">Description (optional)</label>
                <input
                  class="pi-desc-input"
                  type="text"
                  v-model="p.description"
                  :placeholder="'e.g., IRB approval PDF, protocol v2, consent form…'"
                  :disabled="uploading"
                />
              </div>
            </div>

            <div class="attach-actions">
              <button class="btn-primary" :disabled="!pendingFiles.length || uploading" @click="saveStudyAttachments">
                {{ uploading ? 'Saving…' : 'Save Attachments' }}
              </button>
            </div>
          </div>
        </div>

        <!-- SETTINGS / ACCESS MANAGEMENT -->
        <div v-else-if="activeTab === 'team'">
          <h2 class="panel-title center">Study Access Management</h2>

          <div class="subsection">
            <h3 class="sub-title">Access for this Study</h3>

            <div class="table-wrap">
              <table class="access-table" aria-label="Study access">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Permissions</th>
                    <th>Granted By</th>
                    <th>Granted At</th>
                    <th v-if="canManageAccess">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr class="owner-row">
                    <td class="strong">
                      {{ studyMeta.created_by_display || 'Owner' }}
                      <span class="tag">Owner</span>
                    </td>
                    <td>{{ studyMeta.created_by_email || '—' }}</td>
                    <td>PI / Admin</td>
                    <td>
                      <span class="pill ok">View</span>
                      <span class="pill ok">Add data</span>
                      <span class="pill ok">Edit study</span>
                    </td>
                    <td>System</td>
                    <td>{{ formatDateTime(studyMeta.created_at) || '—' }}</td>
                    <td v-if="canManageAccess">—</td>
                  </tr>

                  <tr v-for="g in accessList" :key="g.user_id">
                    <td class="strong">{{ g.display_name || g.username || g.email || ('User#' + g.user_id) }}</td>
                    <td>{{ g.email || '—' }}</td>
                    <td>{{ prettyGrantRole(g.role) }}</td>
                    <td>
                      <span class="pill" :class="g.permissions?.view ? 'ok' : 'muted'">View</span>
                      <span class="pill" :class="g.permissions?.add_data ? 'ok' : 'muted'">Add data</span>
                      <span class="pill" :class="g.permissions?.edit_study ? 'ok' : 'muted'">Edit study</span>
                    </td>
                    <td>{{ g.granted_by_display || g.granted_by || '—' }}</td>
                    <td>{{ formatDateTime(g.created_at) || '—' }}</td>
                    <td v-if="canManageAccess">
                      <button class="btn-link danger" :disabled="revokeBusy[g.user_id]" @click="openRevokeDialog(g)" title="Revoke access">Revoke</button>
                    </td>
                  </tr>

                  <tr v-if="!accessList.length">
                    <td :colspan="canManageAccess ? 7 : 6" class="muted center">No additional users have access.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Revoke confirm dialog -->
          <div v-if="confirm.visible" class="modal-backdrop" role="dialog" aria-modal="true" @click.self="cancelRevoke">
            <div class="modal" @keydown.esc.prevent="cancelRevoke" tabindex="-1">
              <h3 class="modal-title">Revoke access?</h3>
              <p class="modal-text">
                This will remove access for
                <span class="strong">
                  {{ confirm.target?.display_name || confirm.target?.email || ('User#' + confirm.target?.user_id) }}
                </span>.
              </p>
              <div class="modal-actions">
                <button class="btn-minimal" @click="cancelRevoke">Cancel</button>
                <button class="btn-primary danger" :disabled="revokeBusy[confirm.target?.user_id]" @click="confirmRevoke">
                  {{ revokeBusy[confirm.target?.user_id] ? 'Revoking…' : 'Revoke' }}
                </button>
              </div>
        </div>
          </div>

          <!-- GRANT FORM -->
          <div v-if="canManageAccess" class="subsection">
            <h3 class="sub-title">Grant Access</h3>

            <div class="grant-grid">
              <div class="field">
                <label class="label">Select User</label>
                <select v-model="selectedUserId" class="input input-select">
                  <option value="" disabled>Select a user…</option>
                  <option v-for="u in grantableUsers" :key="u.id" :value="u.id">
                    {{ userDisplay(u) }}
                  </option>
                </select>
                <div class="help" v-if="!allUsers.length">No users found to grant.</div>
              </div>

              <div class="field">
                <label class="label">Permission</label>
                <select v-model="permissionPreset" class="input input-select" disabled>
                  <option value="data-entry">Add data only</option>
                </select>
                <div class="help">Adds the user with ability to submit data to this study; no editing.</div>
              </div>

              <div class="actions">
                <button class="btn-primary" :disabled="!selectedUserId || granting" @click="grantAccess">
                  {{ granting ? 'Granting…' : 'Grant Access' }}
                </button>
              </div>
            </div>
          </div>

          <!-- STUDY CONFIGURATIONS (placeholder) -->
          <div class="subsection">
            <h3 class="sub-title">Study Configurations</h3>
            <p class="muted">
              (Yet to Decide on this part) This section can include configuration options such as: edit windows for visits, allowed data entry roles,
              randomization settings, subject ID format, data export preferences, and notification settings.
            </p>
          </div>
        </div>

        <!--  VIEW DATA: embedded (NO routing) -->
        <div v-else-if="activeTab === 'viewdata'" class="viewdata-host">
          <StudyDataDashboard
            :study-id="studyId"
            :embedded="true"
            :fullscreen="dashboardFullscreen"
            @toggle-fullscreen="toggleDashboardFullscreen"
          />
        </div>

        <!-- AUDIT LOGS -->
        <div v-else-if="activeTab === 'audit'">
          <StudyAuditLogs :study-id="studyId" />
        </div>

        <!-- EXPORT OPTIONS TAB -->
        <div v-else-if="activeTab === 'bids'">
          <h2 class="panel-title center">Export Options</h2>

          <!-- moved from Dashboard 3-dot menu -->
          <div class="subsection">
            <h3 class="sub-title">Study exports</h3>
            <p class="muted">
              Export the study template or download a ZIP bundle of the study.
            </p>

            <div class="bids-actions export-actions">
              <button class="btn-primary" type="button" @click="exportStudyTemplate">
                Export Study Template
              </button>

              <button
                class="btn-primary"
                type="button"
                :disabled="downloadingZip"
                @click="downloadStudyZip"
              >
                {{ downloadingZip ? "Downloading…" : "Download Study (ZIP)" }}
              </button>
            </div>
          </div>

          <!-- Existing dataset (kept as-is) -->
          <div v-if="canSeeBidsButton" class="subsection bids-location">
            <h3 class="sub-title">Dataset location</h3>

            <p class="muted">
              Dataset folder on disk for this study:
              <span v-if="bidsDatasetPath">
                <code class="file-path">{{ bidsDatasetPath }}</code>
                <span v-if="!bidsPathExists" class="muted"> (folder does not exist yet)</span>
              </span>
              <span v-else>
                Not available yet.
              </span>
            </p>

            <div class="bids-actions">
              <button
                class="btn-primary"
                type="button"
                :disabled="openingBids || !bidsDatasetPath || !bidsPathExists"
                @click="openBidsFolder"
              >
                {{ openingBids ? 'Opening…' : 'Open Dataset Folder' }}
              </button>
            </div>
          </div>

          <p v-else class="muted">
            Only the study owner or an administrator can view the BIDS dataset location.
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import FieldFileUpload from "@/components/fields/FieldFileUpload.vue";
import StudyAuditLogs from "@/components/StudyAuditLogs.vue";
import TemplateDiffView, { computeTemplateDiff, buildVersionSummary } from "@/components/TemplateDiffView.vue";
import StudyDataDashboard from "@/components/StudyDataDashboard.vue";
import icons from "@/assets/styles/icons";
import { downloadStudyBundle } from "@/utils/studyDownload";

export default {
  name: "StudyView",
  components: { FieldFileUpload, StudyAuditLogs, TemplateDiffView, StudyDataDashboard },
  data() {
    return {
      studyId: this.$route.params.id,

      // meta/content
      studyMeta: {
        id: null,
        study_name: "",
        study_description: "",
        created_by_id: null,
        created_by_display: "",
        created_by_email: "",
        created_at: "",
        updated_at: "",
      },
      studyData: {},
      me: null,
      confirm: { visible: false, target: null },

      icons,

      // Meta tab collapsibles (collapsed by default)
      metaCollapsed: {
        studyData: true,
        groups: true,
        visits: true,
        assignment: true,
        versions: true,
      },

      //  View Data embedding state
      dataSidebarCollapsed: false,
      dashboardFullscreen: false,

      // tabs
      activeTab: "meta",
      tabs: [
        { key: "meta", label: "Meta-data" },
        { key: "edit", label: "Edit Study", requiresEdit: true },
        { key: "docs", label: "Documents" },
        { key: "team", label: "Study Access" },
        { key: "viewdata", label: "View Data" },
        { key: "audit", label: "Audit logs" },
        { key: "bids", label: "Export Options" },
      ],

      //  7-step edit launcher (kept)
      editSteps: [
        { step: 1, label: "1) Study details", desc: "Title, description, basics" },
        { step: 2, label: "2) Arms / Groups", desc: "Treatment arms, groups, labels" },
        { step: 3, label: "3) Visits", desc: "Visit definitions, windows, order" },
        { step: 4, label: "4) eCRF / Forms", desc: "Forms, sections, fields (templates)" },
        { step: 5, label: "5) Subject assignment", desc: "Randomization / assignment settings" },
        { step: 6, label: "6) Subjects / Enrollment", desc: "Planned subject count, identifiers (if used)" },
        { step: 7, label: "7) Schedule of assessments", desc: "SoA matrix: which forms in which visits/groups" },
      ],

      // files
      allFiles: [],
      attachTempValue: [],
      pendingFiles: [],
      uploading: false,

      // access management
      accessList: [],
      allUsers: [],
      selectedUserId: "",
      permissionPreset: "data-entry",
      granting: false,
      revokeBusy: {},

      // versions
      versionsLoading: false,
      versions: [],
      versionSchemas: {},
      versionDiffs: {},
      canShowVersionDetails: true,

      bidsDatasetPath: "",
      bidsPathExists: false,
      openingBids: false,


      downloadingZip: false,
    };
  },
  computed: {
    visibleTabs() {
      return (this.tabs || []).filter(t => !t.requiresEdit || this.canEditStudy);
    },

    groups() { return Array.isArray(this.studyData.groups) ? this.studyData.groups : []; },
    visits() { return Array.isArray(this.studyData.visits) ? this.studyData.visits : []; },
    subjects() { return Array.isArray(this.studyData.subjects) ? this.studyData.subjects : []; },
    assignmentSize() {
      const a = this.studyData.assignments;
      if (!Array.isArray(a) || !a.length) return null;
      const m = a.length;
      const v = Array.isArray(a[0]) ? a[0].length : 0;
      const g = v && Array.isArray(a[0][0]) ? a[0][0].length : 0;
      return { m, v, g };
    },
    studyKVEntries() { return this.objectEntriesFiltered(this.studyData.study); },

    studyLevelFiles() {
      const arr = Array.isArray(this.allFiles) ? this.allFiles : [];
      return arr.filter(f => f.subject_index == null && f.visit_index == null && f.group_index == null);
    },

    token() { return this.$store.state.token; },

    // roles
    myRoleRaw() { return (this.me && (this.me.profile?.role || this.me.role)) || ""; },
    myRole() { return String(this.myRoleRaw).trim(); },
    isAdmin() { return this.myRole.toLowerCase() === "administrator"; },
    isPI() {
      const r = this.myRole.toLowerCase();
      return r === "principal investigator" || r === "pi";
    },
    isPIOrAdmin() { return this.isAdmin || this.isPI; },

    // ownership + capabilities
    isOwner() {
      const meId = this.me?.id;
      return meId != null && this.studyMeta.created_by_id != null && Number(meId) === Number(this.studyMeta.created_by_id);
    },
    canEditStudy() { return this.isAdmin || this.isOwner; },
    canManageAccess() { return this.isAdmin || this.isOwner; },
    canSeeBidsButton() { return this.isAdmin || this.isOwner; },

    // per-subject table
    subjectAssignments() {
      const subs = this.subjects || [];
      return subs.map((s) => ({ subjectId: s?.id || "", groupName: s?.group || "" }));
    },

    grantableUsers() {
      const grantedIds = new Set(this.accessList.map(g => g.user_id));
      if (this.studyMeta.created_by_id != null) grantedIds.add(Number(this.studyMeta.created_by_id));
      return (this.allUsers || [])
        .filter(u => u && u.id != null && !grantedIds.has(Number(u.id)))
        .sort((a, b) => this.userDisplay(a).localeCompare(this.userDisplay(b)));
    },
  },
  watch: {
    activeTab(val) {
      if (val === "viewdata") {
        this.dataSidebarCollapsed = true;
      } else {
        this.dataSidebarCollapsed = false;
        this.dashboardFullscreen = false;
      }

      if (val === "team") this.ensureAccessData();
      if (val === "bids" && this.canSeeBidsButton) this.fetchBidsPath();

      this.$router
        .replace({ query: { ...this.$route.query, tab: val } })
        .catch(() => null);
    },
  },
  methods: {
    tabAbbrev(label) {
      const s = String(label || "").trim();
      if (!s) return "•";
      const words = s.split(/\s+/).filter(Boolean);
      if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
      return (words[0][0] + words[1][0]).toUpperCase();
    },
    toggleDataSidebar() {
      this.dataSidebarCollapsed = !this.dataSidebarCollapsed;
    },
    toggleDashboardFullscreen() {
      if (this.activeTab !== "viewdata") return;
      this.dashboardFullscreen = !this.dashboardFullscreen;
    },

    toggleMetaSection(key) {
      if (!key || !Object.prototype.hasOwnProperty.call(this.metaCollapsed, key)) return;
      this.metaCollapsed[key] = !this.metaCollapsed[key];
    },

    //  moved actions
    exportStudyTemplate() {
      // same behavior as Dashboard: route to export-study page
      this.$router.push(`/dashboard/export-study/${this.studyId}`);
    },
    async downloadStudyZip() {
      const token = this.token;
      if (!token) {
        alert("Please log in again.");
        this.$router.push("/login");
        return;
      }
      this.downloadingZip = true;
      try {
        await downloadStudyBundle({ studyId: this.studyId, token });
      } catch (e) {
        console.error("Failed to download study bundle:", e);
        alert("Failed to download study bundle.");
      } finally {
        this.downloadingZip = false;
      }
    },

    // tiny helpers
    userDisplay(u) {
      const firstLast = [u.first_name || u.profile?.first_name, u.last_name || u.profile?.last_name].filter(Boolean).join(" ").trim();
      return u.name || u.full_name || firstLast || u.username || u.email || `User#${u.id}`;
    },
    prettyGrantRole(role) {
      if (!role) return "Investigator";
      const r = String(role).toLowerCase();
      if (r.includes("investigator")) return "Investigator";
      if (r.includes("principal") || r === "pi") return "PI";
      if (r.includes("admin")) return "Admin";
      return role;
    },

    // layout helpers
    makeDatasetFolder(studyId, studyName) {
      const alnum = (s) => String(s || "").replace(/[^A-Za-z0-9]/g, "");
      const base = (studyName || `study${studyId}`).replace(/ /g, "");
      const slug = alnum(base).slice(0, 48);
      return slug ? `study_${studyId}_${slug}` : `study_${studyId}`;
    },
    docRelativePath(file) {
      const folder = this.makeDatasetFolder(this.studyMeta.id, this.studyMeta.study_name);
      const fname = file?.file_name || "";
      return `bids_datasets/${folder}/metadata/${fname}`;
    },
    docPathTooltip(file) {
      return `Location on disk (relative to backend working directory): ${this.docRelativePath(file)}`;
    },

    scrollToTop() {
      try {
        window.scrollTo({ top: 0, left: 0, behavior: "auto" });
        if (this.$el && typeof this.$el.scrollTop === "number") this.$el.scrollTop = 0;
      } catch (err) {
        console.warn("StudyView scrollToTop failed:", err);
      }
    },
    goBackToDashboard() {
      this.$router.push({ name: "Dashboard", query: { openStudies: "true" } });
    },
    formatDateTime(d) {
      if (!d) return "";
      return new Date(d).toLocaleString("en-GB", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
    },
    prettyBytes(n) {
      if (n === 0) return "0 B";
      if (!n && n !== 0) return "";
      const units = ["B","KB","MB","GB","TB"];
      const i = Math.floor(Math.log(n)/Math.log(1024));
      return `${(n/Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
    },
    prettyLabel(key) {
      if (!key) return "";
      return String(key)
        .replace(/[_-]+/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/\s+/g, " ")
        .replace(/^./, s => s.toUpperCase());
    },
    formatAny(val) {
      if (val == null) return "—";
      if (typeof val === "boolean") return val ? "Yes" : "No";
      if (Array.isArray(val)) return val.length ? JSON.stringify(val) : "—";
      if (typeof val === "object") return Object.keys(val).length ? JSON.stringify(val) : "—";
      const s = String(val);
      return s.trim().length ? s : "—";
    },
    hasValue(val) {
      if (val === null || val === undefined) return false;
      if (typeof val === "string") return val.trim().length > 0;
      if (Array.isArray(val)) return val.length > 0;
      if (typeof val === "object") return Object.keys(val).length > 0;
      return true;
    },
    objectEntriesFiltered(obj) {
      return Object.entries(obj || {}).filter(([, v]) => this.hasValue(v));
    },

    async fetchMe() {
      const token = this.token;
      if (!token) return;
      try {
        const { data } = await axios.get("/users/me", { headers: { Authorization: `Bearer ${token}` } });
        this.me = data || null;
      } catch (e) {
        console.warn("Failed to fetch /users/me:", e?.response?.data || e.message);
      }
    },
    async fetchUserNameById(userId) {
      const token = this.token;
      if (!token || userId == null) return null;
      try {
        const { data } = await axios.get(`/users/${userId}`, { headers: { Authorization: `Bearer ${token}` } });
        const u = data || {};
        const firstLast = [u?.profile?.first_name, u?.profile?.last_name].filter(Boolean).join(" ").trim();
        return u.name || u.full_name || firstLast || u.username || u.email || null;
      } catch (e) {
        return null;
      }
    },
    async fetchStudy() {
      const token = this.token;
      if (!token) { this.$router.push("/login"); return; }
      try {
        const resp = await axios.get(`/forms/studies/${this.studyId}`, { headers: { Authorization: `Bearer ${token}` } });
        const sd = resp.data?.content?.study_data || {};
        const meta = resp.data?.metadata || {};

        let createdByDisplay =
          meta.created_by_name ||
          meta.created_by_full_name ||
          meta.created_by_display ||
          meta.created_by_username ||
          meta.created_by_email ||
          null;

        if (!createdByDisplay && meta.created_by != null) {
          const resolved = await this.fetchUserNameById(meta.created_by);
          createdByDisplay = resolved || String(meta.created_by);
        }

        this.studyMeta = {
          id: meta.id,
          study_name: meta.study_name,
          study_description: meta.study_description,
          created_by_id: meta.created_by,
          created_by_display: createdByDisplay || "-",
          created_by_email: meta.created_by_email || "",
          created_at: meta.created_at,
          updated_at: meta.updated_at,
        };
        this.studyData = sd || {};
      } catch (e) { console.error("Failed to fetch study view:", e); }
    },
    async fetchStudyFiles() {
      const token = this.token;
      if (!token) return;
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}/files`, { headers: { Authorization: `Bearer ${token}` } });
        this.allFiles = Array.isArray(data) ? data : [];
      } catch (e) { console.warn("Failed to fetch study files:", e?.response?.data || e.message); }
    },

    async fetchVersionsAndDiffs() {
      const token = this.token;
      if (!token) return;
      this.versionsLoading = true;
      this.canShowVersionDetails = true;
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}/versions`, { headers: { Authorization: `Bearer ${token}` } });
        const list = Array.isArray(data) ? data : [];
        this.versions = [...list].sort((a, b) => Number(a.version) - Number(b.version));

        if (!this.versions.length) { this.versionSchemas = {}; this.versionDiffs = {}; return; }

        const schemas = {};
        for (const v of this.versions) {
          try {
            const resp = await axios.get(`/forms/studies/${this.studyId}/template`, {
              params: { version: v.version }, headers: { Authorization: `Bearer ${token}` }
            });
            schemas[v.version] = resp.data?.schema || {};
          } catch (e) {
            if (e?.response?.status === 403) { this.canShowVersionDetails = false; break; }
            console.warn(`Failed to fetch schema for v${v.version}:`, e?.response?.data || e.message);
          }
        }
        this.versionSchemas = schemas;

        if (!this.canShowVersionDetails) { this.versionDiffs = {}; return; }

        const diffs = {};
        for (const v of this.versions) {
          const ver = Number(v.version);
          if (ver <= 1) continue;
          const prev = this.versionSchemas[ver - 1];
          const next = this.versionSchemas[ver];
          if (prev && next) {
            const d = computeTemplateDiff(prev, next);
            d.summary = buildVersionSummary(d);
            diffs[ver] = d;
          }
        }
        this.versionDiffs = diffs;
      } catch (e) {
        console.error("fetchVersionsAndDiffs failed:", e?.response?.data || e.message);
        this.versions = []; this.versionSchemas = {}; this.versionDiffs = {};
      } finally { this.versionsLoading = false; }
    },

    async ensureAccessData() { await Promise.all([this.fetchAccessList(), this.fetchAllUsers()]); },
    async fetchAccessList() {
      const token = this.token; if (!token) return;
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}/access`, { headers: { Authorization: `Bearer ${token}` } });
        const list = Array.isArray(data) ? data : (data?.items || []);
        this.accessList = list.map((g) => ({
          user_id: g.user_id,
          role: g.role || "Investigator",
          email: g.email || g.user_email || "",
          username: g.username || "",
          display_name: g.display_name || g.user_display || "",
          granted_by: g.created_by,
          granted_by_display: g.created_by_display || "",
          created_at: g.created_at,
          permissions: {
            view: !!(g.permissions?.view ?? true),
            add_data: !!(g.permissions?.add_data ?? true),
            edit_study: !!(g.permissions?.edit_study ?? false),
          },
        }));
      } catch (e) {
        console.warn("fetchAccessList failed:", e?.response?.data || e.message);
        this.accessList = [];
      }
    },
    async fetchAllUsers() {
      const token = this.token; if (!token) return;
      try {
        const { data } = await axios.get(`/users/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
        const arr = Array.isArray(data) ? data : (data?.items || []);
        this.allUsers = arr;
      } catch (e) {
        console.warn("fetchAllUsers failed:", e?.response?.data || e.message);
        this.allUsers = [];
      }
    },
    async grantAccess() {
      if (!this.selectedUserId) return;
      this.granting = true;
      const token = this.token;
      try {
        const payload = { user_id: Number(this.selectedUserId), role: "Investigator", permissions: { view: true, add_data: true, edit_study: false } };
        await axios.post(`/forms/studies/${this.studyId}/access`, payload, { headers: { Authorization: `Bearer ${token}` } });
        this.selectedUserId = ""; await this.fetchAccessList();
      } catch (e) { console.error("grantAccess failed:", e?.response?.data || e.message); }
      finally { this.granting = false; }
    },
    async revokeAccess(g) {
      if (!g || g.user_id == null) return;
      const token = this.token;
      this.$set ? this.$set(this.revokeBusy, g.user_id, true) : (this.revokeBusy = { ...this.revokeBusy, [g.user_id]: true });
      try {
        await axios.delete(`/forms/studies/${this.studyId}/access/${g.user_id}`, { headers: { Authorization: `Bearer ${token}` } });
        await this.fetchAccessList();
      } catch (e) { console.error("revokeAccess failed:", e?.response?.data || e.message); }
      finally { const next = { ...this.revokeBusy }; delete next[g.user_id]; this.revokeBusy = next; }
    },

    // shared loader (kept)
    async loadStudyIntoStoreForEdit() {
      localStorage.removeItem("setStudyDetails");
      localStorage.removeItem("scratchForms");

      const token = this.token;
      if (!token) { this.$router.push("/login"); return false; }

      try {
        const resp = await axios.get(`/forms/studies/${this.studyId}`, { headers: { Authorization: `Bearer ${token}` } });
        const sd = resp.data.content?.study_data;
        const meta = resp.data.metadata || {};
        if (!sd) { alert("Study content is empty."); return false; }

        let assignments = Array.isArray(sd.assignments) ? sd.assignments : [];
        if (!assignments.length && sd.selectedModels?.length) {
          const m = sd.selectedModels.length;
          const v = sd.visits?.length || 0;
          const g = sd.groups?.length || 0;
          assignments = Array.from({ length: m }, () =>
            Array.from({ length: v }, () =>
              Array.from({ length: g }, () => false)
            )
          );
        }

        const studyInfo = {
          id: meta.id,
          name: meta.study_name,
          description: meta.study_description,
          created_at: meta.created_at,
          updated_at: meta.updated_at,
          created_by: meta.created_by
        };

        this.$store.commit("setStudyDetails", {
          study_metadata: studyInfo,
          study: { id: meta.id, ...sd.study },
          groups: sd.groups || [],
          visits: sd.visits || [],
          subjectCount: sd.subjectCount || 0,
          assignmentMethod: sd.assignmentMethod || "random",
          subjects: sd.subjects || [],
          assignments: assignments,
          forms: sd.selectedModels ? [{
            sections: sd.selectedModels.map(model => ({
              title: model.title,
              fields: model.fields,
              source: "template"
            }))
          }] : []
        });

        if (sd.selectedModels) {
          const scratchForms = [{
            sections: sd.selectedModels.map(model => ({
              title: model.title,
              fields: model.fields,
              source: "template"
            }))
          }];
          localStorage.setItem("scratchForms", JSON.stringify(scratchForms));
        }

        return true;
      } catch (e) {
        console.error("Failed to load study details:", e);
        alert("Failed to load study details.");
        return false;
      }
    },

    // open single step edit
    async openEditStep(stepNumber) {
      if (!this.canEditStudy) return;

      const ok = await this.loadStudyIntoStoreForEdit();
      if (!ok) return;

      const step = Number(stepNumber);
      this.$router.push({
        name: "CreateStudy",
        params: { id: this.studyId },
        query: {
          mode: "edit",
          single: "true",
          step: String(step),
          returnTo: "StudyView",
          returnId: String(this.studyId),
          returnTab: "edit",
        },
      });
    },

    // attach handlers
    onAttachTempChange(val) {
      this.attachTempValue = Array.isArray(val) ? val : [];
    },
    onFilesSelected(files) {
      const arr = Array.isArray(files) ? files : (files ? [files] : []);
      if (!arr.length) return;
      const existing = new Set(this.pendingFiles.map((p) => `${p.file.name}|${p.file.size}|${p.file.lastModified || ""}`));
      const next = [];
      for (const f of arr) {
        const key = `${f.name}|${f.size}|${f.lastModified || ""}`;
        if (!existing.has(key)) next.push({ key, file: f, description: "" });
      }
      if (next.length) this.pendingFiles = this.pendingFiles.concat(next);
    },
    removePending(idx) {
      if (idx >= 0 && idx < this.pendingFiles.length) this.pendingFiles.splice(idx, 1);
    },
    async saveStudyAttachments() {
      if (!this.pendingFiles.length) return;
      const token = this.token;
      if (!token) { this.$router.push("/login"); return; }
      this.uploading = true;
      try {
        for (const item of this.pendingFiles) {
          const fd = new FormData();
          fd.append("uploaded_file", item.file);
          fd.append("description", item.description || "");
          fd.append("storage_option", "local");
          fd.append("modalities_json", "[]");
          await axios.post(
            `/forms/studies/${this.studyId}/files`,
            fd,
            { headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" } }
          );
        }
        this.pendingFiles = [];
        this.attachTempValue = [];
        await this.fetchStudyFiles();
      } catch (e) {
        console.error("Save attachments failed:", e?.response?.data || e.message);
      } finally {
        this.uploading = false;
      }
    },

    openRevokeDialog(g) {
      this.confirm = { visible: true, target: g };
      this.$nextTick(() => {
        try {
          const el = this.$el.querySelector('.modal');
          el && el.focus();
        } catch (err) {
          console.warn('openRevokeDialog: failed to focus modal', err);
        }
      });
    },
    cancelRevoke() { this.confirm = { visible: false, target: null }; },
    async confirmRevoke() {
      const g = this.confirm.target;
      if (!g) return;
      await this.revokeAccess(g);
      this.cancelRevoke();
    },

    async fetchBidsPath() {
      const token = this.token;
      if (!token) return;

      try {
        const { data } = await axios.get(
          `/forms/studies/${this.studyId}/bids_path`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        this.bidsDatasetPath = data?.dataset_path || "";
        this.bidsPathExists = !!data?.exists;
      } catch (e) {
        console.warn("Failed to fetch BIDS path:", e?.response?.data || e.message);
        this.bidsDatasetPath = "";
        this.bidsPathExists = false;
      }
    },

    async openBidsFolder() {
      if (!this.bidsDatasetPath || !this.bidsPathExists) return;

      const token = this.token;
      if (!token) { this.$router.push("/login"); return; }

      this.openingBids = true;
      try {
        await axios.post(
          `/forms/studies/${this.studyId}/bids_open`,
          {},
          { headers: { Authorization: `Bearer ${token}` } }
        );
      } catch (e) {
        console.error("Failed to open BIDS folder:", e?.response?.data || e.message);
      } finally {
        this.openingBids = false;
      }
    },

    // NOTE: other methods you pasted (docs, grant/revoke, save attachments, etc.) remain unchanged in your file
  },
  async mounted() {
    this.scrollToTop?.();

    const qTab = this.$route.query?.tab;
    if (qTab && this.tabs.some(t => t.key === qTab)) this.activeTab = qTab;

    await this.fetchMe();
    await this.fetchStudy();
    if (this.canSeeBidsButton) await this.fetchBidsPath();
    await Promise.all([this.fetchStudyFiles(), this.fetchVersionsAndDiffs()]);
  },
  beforeRouteEnter(to, from, next) { next((vm) => vm.scrollToTop?.()); },
  beforeRouteUpdate(to, from, next) {
    this.studyId = to.params.id;

    const qTab = to.query?.tab;
    if (qTab && this.tabs.some(t => t.key === qTab)) this.activeTab = qTab;

    this.scrollToTop?.();
    Promise.resolve()
      .then(() => this.fetchStudy())
      .then(() => {
        if (this.canSeeBidsButton) return this.fetchBidsPath();
      })
      .then(() => Promise.all([this.fetchStudyFiles(), this.fetchVersionsAndDiffs()]))
      .finally(() => next());
  },
};
</script>

<style scoped>
/* IMPORTANT: do NOT apply font-family to * (breaks FontAwesome icons).
   Keep typography scoped to the page container only. */
.study-view-layout {
  font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif;
  letter-spacing: 0.1px;
}

.study-view-layout { display: flex; flex-direction: column; gap: 16px; padding: 24px; background: #f9fafb; min-height: 100%; }

/*  Fullscreen overlay for View Data */
.study-view-layout.sv-dashboard-fullscreen {
  position: fixed;
  inset: 0;
  padding: 0;
  gap: 0;
  background: #fff;
  z-index: 3000;
}

/* Header */
.sv-header { position: relative; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; }
.back-btn { position: absolute; left: 0; top: 50%; transform: translateY(-50%); }
.title-wrap { grid-column: 2 / 3; min-width: 0; text-align: center; }
.sv-title { margin: 0; font-size: 22px; font-weight: 800; color: #111827; }
.sv-subtitle { margin: 6px 0 0; color: #6b7280; }
.header-spacer { width: 56px; height: 1px; }

/* Card layout */
.card { display: grid; grid-template-columns: 240px 1fr; background: #fff; border: 1px solid #ececec; border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.04); overflow: hidden; }

/*  When viewdata and sidebar collapsed */
.card.sv-sidebar-collapsed { grid-template-columns: 52px 1fr; }

/*  When fullscreen, no sidebar column */
.card.sv-dashboard-fullscreen { grid-template-columns: 1fr; border-radius: 0; border: none; box-shadow: none; height: 100vh; }

/* Vertical tabs */
.v-tabs { background: #fcfcff; border-right: 1px solid #f0f0f6; padding: 10px; display: flex; flex-direction: column; gap: 8px; min-height: 360px; }
.v-tabs.collapsed { padding: 8px 6px; gap: 8px; }

.v-tabs-tools { display: flex; justify-content: center; padding-bottom: 6px; }

/* Tabs */
.v-tab { text-align: left; background: #fff; border: 1px solid #ececec; border-radius: 10px; padding: 10px 12px; font-size: 14px; color: #374151; cursor: pointer; transition: background .2s, color .2s, box-shadow .2s, border .2s; }
.v-tabs.collapsed .v-tab { text-align: center; padding: 10px 8px; font-size: 12px; }
.v-tab:hover { background: #f8fafc; }
.v-tab.active { background: #eef2ff; color: #3538cd; border-color: #e0e7ff; box-shadow: 0 3px 10px rgba(53,56,205,0.08); }

/* Panel */
.v-panel { padding: 18px 20px; }
.v-panel-tight { padding: 0; overflow: hidden; min-height: 0; }

/* Viewdata host fills */
.viewdata-host { height: 100%; min-height: 0; }

/* Panel titles */
.panel-title { margin: 4px 0 12px; font-size: 16px; font-weight: 700; }
.panel-title.center { text-align: center; }

/* Subsections */
.subsection { margin-top: 18px; }
.sub-title { margin: 0; font-size: 14px; font-weight: 700; color: #111827; }

/* Meta grid */
.meta-grid { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 12px; }
.meta-item { border: 1px solid #f1f1f1; border-radius: 10px; padding: 10px 12px; background: #fff; }
.meta-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: #6b7280; margin-bottom: 6px; }
.meta-value { font-size: 14px; color: #111827; word-break: break-word; }
.monospace { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }

/* Collapsible meta sections: consistent containers */
.meta-sections { margin-top: 14px; display: flex; flex-direction: column; gap: 12px; }

.meta-section {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
}

.meta-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.meta-section-body { margin-top: 10px; }

.meta-toggle {
  padding: 6px 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* Key-value grids */
.kv-grid { display: grid; grid-template-columns: 1fr; gap: 8px; }
.kv-row { display: grid; grid-template-columns: 200px 1fr; gap: 8px; padding: 8px 10px; border: 1px solid #f5f5f5; border-radius: 8px; background: #fff; }
.kv-key { color: #6b7280; font-size: 13px; }
.kv-val { color: #111827; font-size: 14px; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }

/* Lists */
.list-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 10px; }
.list-card { border: 1px solid #f1f1f1; border-radius: 12px; padding: 10px; background: #fff; }
.list-card .kv-row { display: grid; grid-template-columns: minmax(120px, 220px) 1fr; gap: 8px; align-items: start; }

/* per-subject table */
.per-subject-block { margin-top: 14px; }
.per-subject-title { margin: 8px 0; font-size: 13px; font-weight: 700; color: #111827; }
.ps-table-wrap { overflow: auto; border: 1px solid #f1f1f1; border-radius: 10px; background: #fff; }
.ps-table { width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }
.ps-table th, .ps-table td { border-bottom: 1px solid #f5f5f5; padding: 8px 10px; text-align: left; }
.ps-table th { background: #fafafe; color: #374151; font-weight: 600; }
.ps-table tr:last-child td { border-bottom: none; }

/* Docs */
.doc-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.doc-item { border: 1px solid #f1f1f1; border-radius: 12px; padding: 12px; background: #fff; }
.doc-name { font-weight: 700; word-break: break-word; }
.doc-meta { font-size: 12px; margin: 6px 0 8px; color: #6b7280; }
.doc-desc { margin-top: 4px; font-size: 13px; color: #374151; }

.doc-path { margin-top: 6px; font-size: 12px; color: #6b7280; display: flex; gap: 6px; align-items: flex-start; }
.doc-path .label { flex: 0 0 auto; color: #6b7280; }
.doc-path .file-path { flex: 1 1 auto; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; word-break: break-word; overflow-wrap: anywhere; white-space: normal; }

/* Attach */
.attach-row { margin-bottom: 10px; }
.pending-list { display: grid; grid-template-columns: 1fr; gap: 10px; }
.pending-item { border: 1px solid #f1f1f1; border-radius: 10px; padding: 10px; background: #fff; display: flex; flex-direction: column; gap: 6px; }
.pi-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pi-name { font-weight: 600; min-width: 0; word-break: break-word; }
.pi-size { color: #6b7280; font-size: 12px; }
.icon-inline { border:none; background:transparent; padding:6px; border-radius:8px; cursor:pointer; }
.icon-inline.danger { color:#b91c1c; }
.pi-desc-label { font-size: 12px; color: #6b7280; }
.pi-desc-input { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
.attach-actions { margin-top: 10px; }

/* Buttons */
.btn-primary { border-radius: 10px; padding: 10px 12px; font-size: 14px; cursor: pointer; transition: transform .05s, box-shadow .2s, background .2s, color .2s, border .2s; border: 1px solid transparent; background: #111827; color: #fff; }
.btn-primary[disabled] { opacity: 0.6; cursor: not-allowed; }
.btn-primary:hover:not([disabled]) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(0,0,0,.1); }
.btn-minimal { background: none; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px 12px; font-size: 14px; color: #555; cursor: pointer; transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease; }
.btn-minimal:hover { background: #e8e8e8; color: #000; border-color: #d6d6d6; }
.btn-minimal.icon-only { padding: 8px 10px; }

/* Empty + util */
.empty-state { color: #6b7280; }
.center { text-align: center; }
.strong { font-weight: 600; }
.muted { color: #6b7280; }

/* Access table */
.table-wrap { overflow: auto; border: 1px solid #f1f1f1; border-radius: 12px; background: #fff; }
.access-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.access-table th, .access-table td { padding: 10px 12px; border-bottom: 1px solid #f6f6f6; text-align: left; }
.access-table thead th { background: #fafafe; color: #374151; font-weight: 600; }
.access-table tr:last-child td { border-bottom: none; }
.owner-row { background: #fcfcff; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-right: 6px; border: 1px solid #e5e7eb; color: #6b7280; background: #fff; }
.pill.ok { color: #065f46; background: #ecfdf5; border-color: #a7f3d0; }
.pill.muted { color: #6b7280; background: #f9fafb; }
.tag { margin-left: 8px; font-size: 11px; border-radius: 6px; padding: 2px 6px; background: #eef2ff; color: #3538cd; border: 1px solid #e0e7ff; }
.btn-link { background: transparent; border: none; padding: 0; cursor: pointer; text-decoration: underline; }
.btn-link.danger { color: #b91c1c; }

/* Grant form */
.grant-grid {
  display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px;
  background: #fff; border: 1px solid #f1f1f1; border-radius: 12px; padding: 12px; align-items: start;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; }
.input { width: 100%; height: 40px; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; box-sizing: border-box; background: #fff; }
.input-select { appearance: none; -webkit-appearance: none; -moz-appearance: none; background-position: right 10px center; }
.help { font-size: 12px; color: #6b7280; }
.actions { display: flex; gap: 8px; align-self: end; }

/* Modal */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 12px; padding: 16px; width: 100%; max-width: 420px; box-shadow: 0 10px 30px rgba(0,0,0,.15); outline: none; }
.modal-title { margin: 0 0 8px; font-size: 16px; font-weight: 700; color: #111827; }
.modal-text { margin: 0 0 14px; color: #374151; font-size: 14px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.btn-primary.danger { background: #b91c1c; border-color: #a11a1a; }
.btn-primary.danger:hover { background: #991b1b; }

/* Versions */
.versions-wrap { display: block; }
.version-list { display: grid; grid-template-columns: 1fr; gap: 10px; }
.version-card { border: 1px solid #f1f1f1; border-radius: 12px; padding: 12px; background: #fff; }
.vc-head { display: flex; flex-direction: column; gap: 4px; }
.vc-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.vc-date { color: #6b7280; font-size: 12px; }
.vc-summary { color: #374151; font-size: 13px; margin-top: 2px; }
.vc-summary-line { display: block; margin-top: 2px; }
.diff-scroll { overflow: auto; border: 1px solid #f1f1f1; border-radius: 10px; padding: 12px; background: #fff; }

.bids-location .file-path { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; word-break: break-all; }
.bids-actions { margin-top: 8px; }

/* edit steps grid */
.edit-steps-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.edit-step-card {
  text-align: left;
  background: #fff;
  border: 1px solid #ececec;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background .2s, border .2s, box-shadow .2s, transform .05s;
}
.edit-step-card:hover:not([disabled]) { background: #f8fafc; border-color: #e5e7eb; box-shadow: 0 8px 18px rgba(0,0,0,0.06); transform: translateY(-1px); }
.edit-step-card[disabled] { opacity: 0.6; cursor: not-allowed; }
.esc-title { font-weight: 800; color: #111827; margin-bottom: 4px; }
.esc-desc { color: #6b7280; font-size: 13px; }
.edit-hint { margin-top: 10px; text-align: center; }

/* Responsive */
@media (max-width: 900px) {
  .edit-steps-grid { grid-template-columns: 1fr; }
}
.bids-actions.export-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.bids-actions.export-actions .btn-primary {
  margin: 0;
}
</style>
