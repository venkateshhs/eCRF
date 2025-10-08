<template>
  <div class="protocol-matrix-container">
    <div class="screen-header">
      <h2 class="screen-title">Schedule of Assessments</h2>
      <button class="icon-btn header-info-btn" @click="showInfo = true" aria-label="What is Protocol Matrix?">
        <i class="fas fa-question-circle"></i>
      </button>
    </div>

    <!-- 1. Visit Navigator (when >3 visits) -->
    <div v-if="visitList.length > 3" class="visit-nav">
      <button @click="prevVisit" :disabled="currentVisitIndex === 0" class="nav-btn">&lt;</button>

      <div class="visit-nav-center">
        <span class="visit-counter">
          Visit {{ currentVisitIndex + 1 }} / {{ visitList.length }}
        </span>
        <!-- show current visit name directly below -->
        <span class="visit-name">{{ visitList[currentVisitIndex]?.name || 'Visit' }}</span>
      </div>

      <button @click="nextVisit" :disabled="currentVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
    </div>

    <!-- 2. Protocol Matrix -->
    <div class="table-container card-surface">
      <table class="protocol-table">
        <!-- Full matrix if ≤3 visits -->
        <thead v-if="visitList.length <= 3">
          <tr>
            <th rowspan="2">Data Models</th>
            <th v-for="(visit, vIdx) in visitList" :key="`vh-${vIdx}`" :colspan="groupList.length">
              <span class="th-title">Visit:</span>
              <span class="th-chip">{{ visit.name }}</span>
            </th>
          </tr>
          <tr>
            <template v-for="(_, vIdx) in visitList" :key="`vg-${vIdx}`">
              <th v-for="(group, gIdx) in groupList" :key="`vg-${vIdx}-${gIdx}`">
                <span class="group-name">Group/Cohort: {{ group.name }}</span>
              </th>
            </template>
          </tr>
        </thead>

        <!-- Single-visit view if >3 visits -->
        <thead v-else>
          <tr>
            <th>Data Models</th>
            <th v-for="(group, gIdx) in groupList" :key="`g-${gIdx}`">
              <span class="group-name">{{ group.name }}</span>
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(model, mIdx) in selectedModels" :key="`m-${mIdx}`">
            <td class="model-cell">
              <span class="model-title">{{ model.title }}</span>
            </td>

            <!-- Full-matrix cells -->
            <template v-if="visitList.length <= 3">
              <template v-for="(_, vIdx) in visitList" :key="`row-${mIdx}-v-${vIdx}`">
                <td v-for="(_, gIdx) in groupList" :key="`cell-${mIdx}-${vIdx}-${gIdx}`">
                  <label class="chk-wrap" :title="`Toggle ${model.title} @ ${visitList[vIdx]?.name} / ${groupList[gIdx]?.name}`">
                    <input
                      type="checkbox"
                      :checked="assignments[mIdx][vIdx][gIdx]"
                      @change="onToggle(mIdx, vIdx, gIdx, $event.target.checked)"
                    />
                    <!-- Unchecked: outline square; Checked: check-square -->
                    <i class="fa-chk" :class="[assignments[mIdx][vIdx][gIdx] ? 'fas fa-check-square' : 'far fa-square']"></i>
                  </label>
                </td>
              </template>
            </template>

            <!-- Single-visit cells -->
            <template v-else>
              <td v-for="(_, gIdx) in groupList" :key="`celln-${mIdx}-${gIdx}`">
                <label class="chk-wrap" :title="`Toggle ${model.title} @ ${visitList[currentVisitIndex]?.name} / ${groupList[gIdx]?.name}`">
                  <input
                    type="checkbox"
                    :checked="assignments[mIdx][currentVisitIndex][gIdx]"
                    @change="onToggle(mIdx, currentVisitIndex, gIdx, $event.target.checked)"
                  />
                  <i class="fa-chk" :class="[assignments[mIdx][currentVisitIndex][gIdx] ? 'fas fa-check-square' : 'far fa-square']"></i>
                </label>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 3. Preview Modal -->
    <div v-if="showPreviewModal" class="modal-overlay">
      <div class="modal protocol-preview-modal">
        <div class="preview-header">
          <!-- Visit nav -->
          <button @click="prevPreviewVisit" :disabled="previewVisitIndex === 0" class="nav-btn">&lt;</button>
          <span class="preview-label">
            Visit:
            <span class="th-chip">{{ visitList[previewVisitIndex].name }}</span>
          </span>
          <button @click="nextPreviewVisit" :disabled="previewVisitIndex === visitList.length - 1" class="nav-btn">&gt;</button>
          <span class="spacer"></span>
          <!-- Group nav -->
          <button @click="prevPreviewGroup" :disabled="previewGroupPos === 0" class="nav-btn">&lt;</button>
          <span class="preview-label">
            Group/Cohort:
            <span class="th-chip">{{ groupList[assignedGroups[previewGroupPos]].name }}</span>
          </span>
          <button
            @click="nextPreviewGroup"
            :disabled="previewGroupPos === assignedGroups.length - 1"
            class="nav-btn"
          >&gt;</button>
        </div>

        <div class="preview-content">
          <FormPreview :form="previewForm" />
        </div>
        <div class="modal-actions">
          <button @click="closePreview" class="btn-action">Close</button>
        </div>
      </div>
    </div>

    <!-- 4. Custom Dialog for Notifications -->
    <CustomDialog :message="dialogMessage" :isVisible="showDialog" @close="closeDialog" />

    <!-- 4a. Info dialog for ProtocolMatrix -->
    <div v-if="showInfo" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">What is this screen?</h3>
        <p class="validation-text">
          This matrix helps you decide which <strong>forms/data models</strong> are collected for each
          study <strong>Visit</strong> and <strong>Group/Cohort</strong>. Click a checkbox to assign a form
          to that visit and group. Use the arrows to move between visits when there are many.
        </p>
        <ul class="empty-visits-list">
          <li>Checked = that form will appear for participants in that group at that visit.</li>
          <li>Use <strong>Preview</strong> to see what participants will fill out.</li>
          <li><strong>Save</strong> stores your setup. We’ll warn you if a visit has nothing assigned.</li>
        </ul>
        <div class="modal-actions">
          <button class="btn-primary" @click="showInfo = false">Got it</button>
        </div>
      </div>
    </div>

    <!-- 4b. Empty-visit warning modal -->
    <div v-if="showEmptyVisitsModal" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">Some visits have no assigned models</h3>
        <p class="validation-text">
          We found visits without any model assigned. You can go fix them, or save anyway.
        </p>
        <ul class="empty-visits-list">
          <li v-for="vIdx in emptyVisitIndices" :key="'empty-v-'+vIdx">
            <span class="visit-item-title">Visit {{ vIdx + 1 }} — {{ visitList[vIdx]?.name || 'Visit' }}</span>
          </li>
        </ul>
        <div class="modal-actions">
          <button class="btn-option" @click="goToFirstEmptyVisit">Go to first empty visit</button>
          <button class="btn-primary" :disabled="isSavingInProgress" @click="saveAnyway">
            {{ isSavingInProgress ? 'Saving…' : 'Save anyway' }}
          </button>
          <button class="btn-option" @click="closeEmptyVisitsModal">Cancel</button>
        </div>
      </div>
    </div>

    <!-- 4c. Confirm Template Changes -->
    <div v-if="showConfirmChanges" class="modal-overlay">
      <div class="modal validation-modal">
        <h3 class="validation-title">Confirm Template Changes</h3>
        <p class="validation-text">
          You made structural changes. Saving will
          <strong v-if="versionDecision?.will_bump">create a new template version (v{{ versionDecision.decision_version_after }})</strong>
          <strong v-else>update the current version (no new version will be created)</strong>.
          Existing data remains attached to its original versions and is not lost.
        </p>

        <div class="diff-sections">
          <!-- Metadata (generic key-by-key diff) -->
          <div v-if="diffResult.metadata.any" class="diff-block">
            <h4>Study Metadata</h4>
            <ul>
              <li v-for="c in diffResult.metadata.changes" :key="'md-'+c.key">
                <strong>{{ c.label }}:</strong>
                <em>{{ c.from || '—' }}</em> → <em>{{ c.to || '—' }}</em>
              </li>
            </ul>
          </div>

          <!-- Groups -->
          <div v-if="diffResult.groups.any" class="diff-block">
            <h4>Groups</h4>
            <ul>
              <li v-for="n in diffResult.groups.added" :key="'gadd-'+n">➕ Added: <strong>{{ n }}</strong></li>
              <li v-for="n in diffResult.groups.removed" :key="'grem-'+n">➖ Removed: <strong>{{ n }}</strong></li>
              <li v-for="p in diffResult.groups.renamed" :key="'gren-'+p.from+'-'+p.to">
                ✎ Renamed: <strong>{{ p.from }}</strong> → <strong>{{ p.to }}</strong>
              </li>
              <li v-for="chg in diffResult.groups.changed" :key="'gchg-'+chg.name">
                ⚙︎ Updated: <strong>{{ chg.name }}</strong>
                <ul>
                  <li v-for="field in chg.fields" :key="'gchg-'+chg.name+'-'+field.key">
                    {{ field.label }}: <em>{{ field.from || '—' }}</em> → <em>{{ field.to || '—' }}</em>
                  </li>
                </ul>
              </li>
            </ul>
          </div>

          <!-- Visits -->
          <div v-if="diffResult.visits.any" class="diff-block">
            <h4>Visits</h4>
            <ul>
              <li v-for="n in diffResult.visits.added" :key="'vadd-'+n">➕ Added: <strong>{{ n }}</strong></li>
              <li v-for="n in diffResult.visits.removed" :key="'vrem-'+n">➖ Removed: <strong>{{ n }}</strong></li>
              <li v-for="p in diffResult.visits.renamed" :key="'vren-'+p.from+'-'+p.to">
                ✎ Renamed: <strong>{{ p.from }}</strong> → <strong>{{ p.to }}</strong>
              </li>
              <li v-for="chg in diffResult.visits.changed" :key="'vchg-'+chg.name">
                ⚙︎ Updated: <strong>{{ chg.name }}</strong>
                <ul>
                  <li v-for="field in chg.fields" :key="'vchg-'+chg.name+'-'+field.key">
                    {{ field.label }}: <em>{{ field.from || '—' }}</em> → <em>{{ field.to || '—' }}</em>
                  </li>
                </ul>
              </li>
            </ul>
          </div>

          <!-- Subjects -->
          <div v-if="diffResult.subjects.any" class="diff-block">
            <h4>Subjects</h4>
            <ul>
              <li v-for="id in diffResult.subjects.added" :key="'sadd-'+id">➕ Added subject: <strong>{{ id }}</strong></li>
              <li v-for="id in diffResult.subjects.removed" :key="'srem-'+id">➖ Removed subject: <strong>{{ id }}</strong></li>
              <li v-for="r in diffResult.subjects.reassigned" :key="'srea-'+r.id">
                ⇄ <strong>{{ r.id }}</strong> moved group: <em>{{ r.from || '—' }}</em> → <em>{{ r.to || '—' }}</em>
              </li>
            </ul>
          </div>

          <!-- Models (sections) -->
          <div v-if="diffResult.models.meta.any" class="diff-block">
            <h4>Data Models</h4>
            <ul>
              <li v-for="n in diffResult.models.meta.added" :key="'madd-'+n">➕ Added: <strong>{{ n }}</strong></li>
              <li v-for="n in diffResult.models.meta.removed" :key="'mrem-'+n">➖ Removed: <strong>{{ n }}</strong></li>
              <li v-for="p in diffResult.models.meta.renamed" :key="'mren-'+p.from+'-'+p.to">
                ✎ Renamed: <strong>{{ p.from }}</strong> → <strong>{{ p.to }}</strong>
              </li>
            </ul>
          </div>

          <!-- Model Assignments -->
          <div v-if="diffResult.models.assign.any" class="diff-block">
            <h4>Model Assignments</h4>
            <p>Turned <strong>ON</strong>: {{ diffResult.models.assign.turnedOn }}, Turned <strong>OFF</strong>: {{ diffResult.models.assign.turnedOff }}</p>
            <details>
              <summary>Show details</summary>
              <ul>
                <li v-for="t in diffResult.models.assign.toggles" :key="'tg-'+t.key">
                  <span v-if="t.to">✔ Assigned</span><span v-else>✖ Unassigned</span>
                  <strong> {{ t.section }}</strong>
                  <span> @ {{ t.visit }} / {{ t.group }}</span>
                </li>
              </ul>
            </details>
          </div>

          <div v-if="!diffResult.any" class="diff-block">
            <em>No structural changes detected.</em>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-option" @click="cancelConfirm">Cancel</button>
          <button class="btn-primary" @click="confirmAndSave">Confirm & Save</button>
        </div>
      </div>
    </div>

    <!-- 5. Footer Actions -->
    <div class="matrix-actions card-surface">
      <button @click="$emit('edit-template')" class="btn-option">Edit Template</button>
      <button @click="saveStudy" class="btn-primary">Save</button>
      <button @click="openPreview" :disabled="!hasAssignment(currentVisitIndex)" class="btn-option">Preview</button>
      <button @click="goToSaved" class="btn-option">View Saved Study</button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import axios from "axios";
import FormPreview from "@/components/FormPreview.vue";
import CustomDialog from "@/components/CustomDialog.vue";

export default {
  name: "ProtocolMatrix",
  components: { FormPreview, CustomDialog },
  props: {
    visits:         { type: Array, required: true },
    groups:         { type: Array, required: true },
    selectedModels: { type: Array, required: true },
    assignments:    { type: Array, required: true }
  },
  emits: ["assignment-updated", "edit-template"],
  setup(props, { emit }) {
    const router = useRouter();
    const store = useStore();

    const isEditing = computed(() => !!(store.state.studyDetails?.study_metadata?.id));

    // Matrix indices
    const currentVisitIndex = ref(0);

    // Preview indices + modal control
    const showPreviewModal  = ref(false);
    const previewVisitIndex = ref(0);
    const previewGroupIndex = ref(0);

    // Dialog state
    const showInfo = ref(false);
    const showDialog = ref(false);
    const dialogMessage = ref("");

    // Empty-visit modal state
    const showEmptyVisitsModal = ref(false);
    const emptyVisitIndices = ref([]);
    const isSavingInProgress = ref(false);

    // Confirm changes
    const showConfirmChanges = ref(false);
    const diffResult = ref({
      any: false,
      metadata: { any: false, changes: [] },
      groups:   { any: false, added: [], removed: [], renamed: [], changed: [] },
      visits:   { any: false, added: [], removed: [], renamed: [], changed: [] },
      subjects: { any: false, added: [], removed: [], reassigned: [] },
      models:   {
        meta:   { any: false, added: [], removed: [], renamed: [] },
        assign: { any: false, toggles: [], turnedOn: 0, turnedOff: 0 }
      }
    });
    const versionDecision = ref(null);

    // Baseline (server)
    const baseline = ref(null);

    // Display lists
    const visitList = computed(() => props.visits.length ? props.visits : [{ name: "All Visits" }]);
    const groupList = computed(() => props.groups.length ? props.groups : [{ name: "All Groups" }]);

    function onToggle(mIdx, vIdx, gIdx, checked) {
      emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
    }

    // Matrix nav
    function prevVisit() {
      if (currentVisitIndex.value > 0) currentVisitIndex.value--;
    }
    function nextVisit() {
      if (currentVisitIndex.value < visitList.value.length - 1) currentVisitIndex.value++;
    }

    // Determine groups for a visit (for preview UX)
    function groupsForVisit(vIdx) {
      return groupList.value
        .map((_, idx) => idx)
        .filter(gIdx =>
          props.selectedModels.some((_, mIdx) =>
            props.assignments[mIdx][vIdx]?.[gIdx]
          )
        );
    }
    const assignedGroups = computed(() => groupsForVisit(previewVisitIndex.value));
    const previewGroupPos = computed(() => assignedGroups.value.indexOf(previewGroupIndex.value));
    function setFirstGroup(vIdx) {
      const arr = groupsForVisit(vIdx);
      previewGroupIndex.value = arr.length ? arr[0] : 0;
    }

    // Preview nav
    function prevPreviewVisit() {
      if (previewVisitIndex.value > 0) {
        previewVisitIndex.value--;
        setFirstGroup(previewVisitIndex.value);
      }
    }
    function nextPreviewVisit() {
      if (previewVisitIndex.value < visitList.value.length - 1) {
        previewVisitIndex.value++;
        setFirstGroup(previewVisitIndex.value);
      }
    }
    function prevPreviewGroup() {
      if (previewGroupPos.value > 0) {
        previewGroupIndex.value = assignedGroups.value[previewGroupPos.value - 1];
      }
    }
    function nextPreviewGroup() {
      if (previewGroupPos.value < assignedGroups.value.length - 1) {
        previewGroupIndex.value = assignedGroups.value[previewGroupPos.value + 1];
      }
    }

    // Build preview form
    const previewForm = computed(() => {
      const visitName = visitList.value[previewVisitIndex.value].name;
      const groupName = groupList.value[previewGroupIndex.value].name;
      const sections = props.selectedModels
        .filter((_, mIdx) =>
          props.assignments[mIdx][previewVisitIndex.value]?.[previewGroupIndex.value]
        )
        .map(m => ({ title: m.title, fields: m.fields }));
      return { formName: `Preview: ${visitName} / ${groupName}`, sections };
    });

    // At least one assignment in a visit?
    function hasAssignment(vIdx) {
      return groupList.value.some((_, gIdx) =>
        props.selectedModels.some((_, mIdx) =>
          props.assignments[mIdx]?.[vIdx]?.[gIdx] === true
        )
      );
    }

    // STRICT check against real visits (for Save)
    function hasAssignmentInVisit(vIdx) {
      return props.groups.some((_, gIdx) =>
        props.selectedModels.some((_, mIdx) =>
          props.assignments?.[mIdx]?.[vIdx]?.[gIdx] === true
        )
      );
    }
    function computeEmptyVisits() {
      const empties = [];
      const realVisitsCount = props.visits.length;
      for (let v = 0; v < realVisitsCount; v++) {
        if (!hasAssignmentInVisit(v)) empties.push(v);
      }
      return empties;
    }
    function openPreview() {
      if (!hasAssignment(currentVisitIndex.value)) return;
      previewVisitIndex.value = currentVisitIndex.value;
      setFirstGroup(currentVisitIndex.value);
      showPreviewModal.value = true;
    }
    function closePreview() { showPreviewModal.value = false; }

    function showDialogMessage(message) { dialogMessage.value = message; showDialog.value = true; }
    function closeDialog() { showDialog.value = false; dialogMessage.value = ""; }

    // ---------- DIFF ENGINE (unchanged core, but metadata now compares all keys) ----------
    function deepClone(o) { return JSON.parse(JSON.stringify(o ?? null)); }
    function normalizeName(s) { return String(s || "").trim(); }
    function levenshtein(a, b) {
      a = a || ""; b = b || "";
      const m = a.length, n = b.length;
      const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
      for (let i = 0; i <= m; i++) dp[i][0] = i;
      for (let j = 0; j <= n; j++) dp[0][j] = j;
      for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
          const cost = a[i-1] === b[j-1] ? 0 : 1;
          dp[i][j] = Math.min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost);
        }
      }
      return dp[m][n];
    }
    function similarity(a, b) {
      const L = Math.max((a || "").length, (b || "").length) || 1;
      return 1 - (levenshtein((a||"").toLowerCase(), (b||"").toLowerCase()) / L);
    }
    function mapBy(arr, keyFn) {
      const m = new Map();
      (arr || []).forEach((x, i) => m.set(keyFn(x, i), { item: x, idx: i }));
      return m;
    }
    function diffListByName(oldList, newList, getName) {
      const oldNames = (oldList || []).map(getName).map(normalizeName);
      const newNames = (newList || []).map(getName).map(normalizeName);
      const oldSet = new Set(oldNames);
      const newSet = new Set(newNames);

      const added = newNames.filter(n => !oldSet.has(n));
      const removed = oldNames.filter(n => !newSet.has(n));

      const renamed = [];
      const stillAdded = [];
      const stillRemoved = [];

      const usedAdded = new Set();
      removed.forEach(r => {
        let best = { name: null, score: 0, j: -1 };
        added.forEach((a, j) => {
          if (usedAdded.has(j)) return;
          const sc = similarity(r, a);
          if (sc > best.score) best = { name: a, score: sc, j };
        });
        if (best.score >= 0.6 && best.j >= 0) {
          usedAdded.add(best.j);
          renamed.push({ from: r, to: best.name, score: Number(best.score.toFixed(2)) });
        } else {
          stillRemoved.push(r);
        }
      });
      added.forEach((a, j) => { if (!usedAdded.has(j)) stillAdded.push(a); });

      const changed = [];
      const oldByName = mapBy(oldList || [], x => normalizeName(getName(x)));
      const newByName = mapBy(newList || [], x => normalizeName(getName(x)));
      newSet.forEach(nm => {
        if (oldSet.has(nm)) {
          const o = oldByName.get(nm)?.item || {};
          const n = newByName.get(nm)?.item || {};
          const local = [];
          ["description", "label"].forEach(k => {
            if ((o?.[k] || "") !== (n?.[k] || "")) {
              local.push({ key: k, label: k[0].toUpperCase() + k.slice(1), from: o?.[k] || "", to: n?.[k] || "" });
            }
          });
          if (local.length) changed.push({ name: nm, fields: local });
        }
      });

      return {
        any: !!(stillAdded.length || stillRemoved.length || renamed.length || changed.length),
        added: stillAdded,
        removed: stillRemoved,
        renamed,
        changed
      };
    }
    function diffMetadata(oldStudy, newStudy) {
      const keys = new Set([...Object.keys(oldStudy || {}), ...Object.keys(newStudy || {})]);
      keys.delete("id");
      const changes = [];
      keys.forEach(k => {
        const fromVal = (oldStudy?.[k] ?? "");
        const toVal   = (newStudy?.[k] ?? "");
        if (JSON.stringify(fromVal) !== JSON.stringify(toVal)) {
          const label = k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
          changes.push({ key: k, label, from: fromVal, to: toVal });
        }
      });
      return { any: changes.length > 0, changes };
    }
    function diffSubjects(oldSubjects, newSubjects) {
      const oldById = mapBy(oldSubjects || [], s => s.id);
      const newById = mapBy(newSubjects || [], s => s.id);
      const oldIds = new Set((oldSubjects || []).map(s => s.id));
      const newIds = new Set((newSubjects || []).map(s => s.id));
      const added = [...newIds].filter(id => !oldIds.has(id));
      const removed = [...oldIds].filter(id => !newIds.has(id));
      const reassigned = [];
      [...oldIds].forEach(id => {
        if (newIds.has(id)) {
          const og = (oldById.get(id)?.item?.group || "").trim();
          const ng = (newById.get(id)?.item?.group || "").trim();
          if (og !== ng) reassigned.push({ id, from: og, to: ng });
        }
      });
      return { any: !!(added.length || removed.length || reassigned.length), added, removed, reassigned };
    }
    function diffModelsMeta(oldModels, newModels) {
      return diffListByName(oldModels || [], newModels || [], m => m.title || m.name);
    }
    function diffModelAssignments(oldModels, newModels, oldAssign, newAssign, visitsOld, visitsNew, groupsOld, groupsNew) {
      const oldIdx = mapBy(oldModels || [], m => (m.title || m.name || "").trim());
      const newIdx = mapBy(newModels || [], m => (m.title || m.name || "").trim());
      const vOld = (visitsOld || []).map(v => v.name);
      const vNew = (visitsNew || []).map(v => v.name);
      const gOld = (groupsOld || []).map(g => g.name);
      const gNew = (groupsNew || []).map(g => g.name);

      const toggles = [];
      let on = 0, off = 0;

      newIdx.forEach((val, title) => {
        if (!oldIdx.has(title)) return;
        const mNew = val.idx;
        const mOld = oldIdx.get(title).idx;

        const vMax = Math.min((oldAssign?.[mOld] || []).length, (newAssign?.[mNew] || []).length);
        const gMaxOld = Math.max(0, ...(oldAssign?.[mOld] || []).map(r => (r || []).length), 0);
        const gMaxNew = Math.max(0, ...(newAssign?.[mNew] || []).map(r => (r || []).length), 0);
        const gMax = Math.min(gMaxOld, gMaxNew);

        for (let v = 0; v < vMax; v++) {
          for (let g = 0; g < gMax; g++) {
            const before = !!(oldAssign?.[mOld]?.[v]?.[g]);
            const after  = !!(newAssign?.[mNew]?.[v]?.[g]);
            if (before !== after) {
              if (after) on++; else off++;
              toggles.push({
                key: `${title}|v${v}|g${g}`,
                section: title,
                visit: vNew[v] ?? vOld[v] ?? `Visit ${v+1}`,
                group: gNew[g] ?? gOld[g] ?? `Group ${g+1}`,
                from: before, to: after
              });
            }
          }
        }
      });

      return { any: toggles.length > 0, toggles, turnedOn: on, turnedOff: off };
    }

    function computeDiff() {
      const base = baseline.value || {};
      const nowStudyDetails = store.state.studyDetails || {};

      const baseStudy  = base.study || {};
      const baseGroups = base.groups || [];
      const baseVisits = base.visits || [];
      const baseSubs   = base.subjects || [];
      const baseModels = base.selectedModels || [];
      const baseAssign = base.assignments || [];

      const nowStudy  = nowStudyDetails.study || {};
      const nowGroups = deepClone(props.groups || []);
      const nowVisits = deepClone(props.visits || []);
      const nowSubs   = nowStudyDetails.subjects || [];
      const nowModels = deepClone(props.selectedModels || []);
      const nowAssign = deepClone(props.assignments || []);

      const metadata = diffMetadata(baseStudy, nowStudy);
      const groups   = diffListByName(baseGroups, nowGroups, g => g.name);
      const visits   = diffListByName(baseVisits, nowVisits, v => v.name);
      const subjects = diffSubjects(baseSubs, nowSubs);
      const modelsMeta = diffModelsMeta(baseModels, nowModels);
      const modelsAssign = diffModelAssignments(baseModels, nowModels, baseAssign, nowAssign, baseVisits, nowVisits, baseGroups, nowGroups);

      const any = metadata.any || groups.any || visits.any || subjects.any || modelsMeta.any || modelsAssign.any;

      const result = { any, metadata, groups, visits, subjects, models: { meta: modelsMeta, assign: modelsAssign } };

      console.groupCollapsed("[ProtocolMatrix] Diff computation");
      console.log("Baseline (server):", base);
      console.log("Current (UI):", {
        study: nowStudy,
        groups: nowGroups, visits: nowVisits,
        subjects: nowSubs, selectedModels: nowModels, assignments: nowAssign
      });
      console.log("Diff result:", result);
      console.groupEnd();

      return result;
    }

    // ---------- BASELINE LOADING ----------
    async function loadBaselineFromServer() {
      const studyId = store.state.studyDetails?.study_metadata?.id;
      if (!studyId) {
        baseline.value = deepClone(store.state.studyDetails || {});
        baseline.value.groups = deepClone(props.groups);
        baseline.value.visits = deepClone(props.visits);
        baseline.value.selectedModels = deepClone(props.selectedModels);
        baseline.value.assignments = deepClone(props.assignments);
        console.groupCollapsed("[ProtocolMatrix] Baseline (create) captured");
        console.log("baseline:", baseline.value);
        console.groupEnd();
        return;
      }
      try {
        const resp = await axios.get(`/forms/studies/${studyId}`, {
          headers: { Authorization: `Bearer ${store.state.token}` }
        });
        const payload = resp.data || {};
        const metadata = payload.metadata || {};
        const studyData = payload.content?.study_data || {};

        const baselineShape = {
          study_metadata: {
            id: metadata.id,
            study_name: metadata.study_name,
            study_description: metadata.study_description,
            created_at: metadata.created_at,
            updated_at: metadata.updated_at,
            created_by: metadata.created_by
          },
          study: {
            id: metadata.id,
            title: (studyData.study?.title ?? metadata.study_name) || "",
            description: (studyData.study?.description ?? metadata.study_description) || "",
            ...((studyData.study || {})) // include all dynamic YAML-driven fields
          },
          groups: studyData.groups || [],
          visits: studyData.visits || [],
          subjects: studyData.subjects || [],
          selectedModels: studyData.selectedModels || [],
          assignments: studyData.assignments || []
        };

        baseline.value = deepClone(baselineShape);

        console.groupCollapsed("[ProtocolMatrix] Baseline fetched from server");
        console.log("GET /forms/studies/:id payload:", payload);
        console.log("Extracted baseline:", baseline.value);
        console.groupEnd();
      } catch (e) {
        console.error("[ProtocolMatrix] Failed to load baseline from server; falling back to store snapshot.", e);
        baseline.value = deepClone(store.state.studyDetails || {});
        baseline.value.groups = deepClone(props.groups);
        baseline.value.visits = deepClone(props.visits);
        baseline.value.selectedModels = deepClone(props.selectedModels);
        baseline.value.assignments = deepClone(props.assignments);
      }
    }

    onMounted(async () => {
      await loadBaselineFromServer();
    });

    // ---------- PREVIEW VERSION DECISION ----------
    async function previewVersionDecision(studyDataPayload) {
      const studyId = store.state.studyDetails?.study_metadata?.id;
      if (!studyId) return { structural_change: false, will_bump: false };

      try {
        const resp = await axios.post(
          `/forms/studies/${studyId}/versioning/preview`,
          { study_content: { study_data: studyDataPayload } },
          { headers: { Authorization: `Bearer ${store.state.token}` } }
        );
        console.log("[ProtocolMatrix] Versioning preview:", resp.data);
        return resp.data || { structural_change: false, will_bump: false };
      } catch (e) {
        console.error("[ProtocolMatrix] Versioning preview failed; falling back to local diff.", e);
        return { structural_change: true, will_bump: true }; // conservative fallback
      }
    }

    // ---------- SAVE ----------
    async function saveStudy() {
      const empties = computeEmptyVisits();
      if (empties.length > 0) {
        emptyVisitIndices.value = empties;
        showEmptyVisitsModal.value = true;
        return;
      }

      // Only gate dialog on edit flows
      if (isEditing.value) {
        // Build proposed study_data (what you'll send to backend on save)
        const studyDetails = store.state.studyDetails || {};
        const proposed = {
          ...studyDetails,
          visits: props.visits,
          groups: props.groups,
          selectedModels: props.selectedModels,
          assignments: props.assignments
        };

        // Ask backend if a bump is needed
        const decision = await previewVersionDecision(proposed);
        versionDecision.value = decision;

        // If backend says no bump → save immediately (no dialog)
        if (!decision.will_bump && !decision.structural_change) {
          await saveStudyImpl();
          return;
        }
        if (!decision.will_bump && decision.structural_change) {
          // Structural change but no bump (latest version has no data) → no need to confirm
          await saveStudyImpl();
          return;
        }

        // Otherwise: bump will happen → show detailed diff to user
        const diff = computeDiff();
        diffResult.value = diff;
        if (diff.any) {
          showConfirmChanges.value = true;
          return;
        }
      }

      // Create flow or nothing to confirm
      await saveStudyImpl();
    }

    function cancelConfirm() { showConfirmChanges.value = false; }
    async function confirmAndSave() {
      showConfirmChanges.value = false;
      await saveStudyImpl();
    }

    function closeEmptyVisitsModal() { showEmptyVisitsModal.value = false; }
    function goToFirstEmptyVisit() {
      if (emptyVisitIndices.value.length) currentVisitIndex.value = emptyVisitIndices.value[0];
      showEmptyVisitsModal.value = false;
    }
    async function saveAnyway() {
      isSavingInProgress.value = true;
      try { await saveStudyImpl(); }
      finally {
        isSavingInProgress.value = false;
        showEmptyVisitsModal.value = false;
      }
    }

    // Original save implementation
    async function saveStudyImpl() {
      const studyDetails = store.state.studyDetails || {};
      const userId = store.state.user?.id;
      const studyId = studyDetails.study_metadata?.id;

      if (!userId) {
        showDialogMessage("Please log in again.");
        return;
      }

      const studyData = {
        ...studyDetails,
        visits: props.visits,
        groups: props.groups,
        selectedModels: props.selectedModels,
        assignments: props.assignments
      };

      let metadata;
      if (studyId) {
        const existingMetadata = studyDetails.study_metadata || {};
        metadata = {
          created_by: existingMetadata.created_by === userId ? existingMetadata.created_by : userId,
          study_name: studyDetails.study?.title || existingMetadata.name || "",
          study_description: existingMetadata.description || studyDetails.study?.description || "",
          created_at: existingMetadata.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
      } else {
        metadata = {
          created_by: userId,
          study_name: studyDetails.study?.title || "",
          study_description: studyDetails.study?.description || "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
      }

      const payload = { study_metadata: metadata, study_content: { study_data: studyData } };
      const url = studyId ? `/forms/studies/${studyId}` : "/forms/studies/";
      const method = studyId ? "put" : "post";

      try {
        const response = await axios[method](url, payload, { headers: { Authorization: `Bearer ${store.state.token}` } });
        const updatedMetadata = response.data.study_metadata || response.data.metadata || metadata;
        const updatedStudyData = response.data.content?.study_data || studyData;

        store.commit("setStudyDetails", {
          study_metadata: {
            id: studyId || response.data.study_metadata?.id || response.data.metadata?.id,
            name: updatedMetadata.study_name,
            description: updatedMetadata.study_description,
            created_at: updatedMetadata.created_at,
            updated_at: updatedMetadata.updated_at,
            created_by: updatedMetadata.created_by
          },
          study: { id: studyId || response.data.study_metadata?.id || response.data.metadata?.id, ...updatedStudyData.study },
          groups: updatedStudyData.groups,
          visits: updatedStudyData.visits,
          subjectCount: updatedStudyData.subjectCount,
          assignmentMethod: updatedStudyData.assignmentMethod,
          subjects: updatedStudyData.subjects,
          assignments: updatedStudyData.assignments,
          selectedModels: updatedStudyData.selectedModels
        });

        // Reload baseline from server so future diffs are accurate
        await loadBaselineFromServer();

        showDialogMessage(studyId ? "Study successfully updated!" : "Study successfully saved!");
      } catch (error) {
        console.error(`Error ${studyId ? "updating" : "saving"} study:`, error);
        showDialogMessage(`Failed to ${studyId ? "update" : "save"} study. Check console for details.`);
      }
    }

    // UPDATED: reroute to Dashboard studies list
    function goToSaved() {
      router.push({ name: "Dashboard", query: { openStudies: "true" } });
    }

    return {
      // state
      visitList,
      groupList,
      isEditing,

      // matrix nav
      currentVisitIndex,
      prevVisit,
      nextVisit,

      // preview
      showPreviewModal,
      previewVisitIndex,
      previewGroupIndex,
      assignedGroups,
      previewGroupPos,
      prevPreviewVisit,
      nextPreviewVisit,
      prevPreviewGroup,
      nextPreviewGroup,
      openPreview,
      closePreview,
      previewForm,

      // toggles
      onToggle,
      hasAssignment,

      // dialogs
      showInfo,
      showDialog,
      dialogMessage,
      closeDialog,

      // empty-visit modal
      showEmptyVisitsModal,
      emptyVisitIndices,
      isSavingInProgress,
      closeEmptyVisitsModal,
      goToFirstEmptyVisit,
      saveAnyway,

      // confirm changes
      showConfirmChanges,
      diffResult,
      cancelConfirm,
      confirmAndSave,
      versionDecision,

      // save + route
      saveStudy,
      goToSaved,
    };
  }
};
</script>

<style scoped lang="scss">
@import "@/assets/styles/_base.scss";

/* Subtle app-like surface and spacing */
.protocol-matrix-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 100%);
  border-radius: 12px;
}

/* Header */
.screen-header {
  position: relative;
  text-align: center;
  padding: 4px 4px 0;
}
.screen-title {
  margin: 0 0 4px;
  font-weight: 800;
  font-size: 18px;
  color: #101828;
}
.icon-btn {
  background: transparent;
  cursor: pointer;
  border: none;
}
.header-info-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: #667085;
}
.header-info-btn:hover { color: #111827; }

/* Reusable surface */
.card-surface {
  border: 1px solid $border-color;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 25px rgba(16, 24, 40, 0.06);
}

/* Visit Pagination */
.visit-nav {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  position: relative;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f5f6fa;
  border: 1px solid $border-color;
}

.visit-nav .nav-btn {
  justify-self: start;
}
.visit-nav .nav-btn:last-child {
  justify-self: end;
}

.visit-nav-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.visit-counter {
  font-weight: 700;
  letter-spacing: 0.2px;
  color: $text-color;
}

.th-chip,
.visit-name {
  display: inline-block;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  hyphens: auto;
  line-height: 1.25;
  max-width: clamp(30ch, 36vw, 64ch);
  text-align: center;
}

.nav-btn {
  background: #ffffff;
  padding: 8px 12px;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  font-size: 16px;
  transition: transform .05s ease, box-shadow .2s ease, background .2s ease;
}
.nav-btn:hover:not(:disabled) {
  background: #f8fafc;
  box-shadow: 0 4px 10px rgba(16,24,40,.08);
}
.nav-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Matrix */
.table-container {
  overflow: auto;
}

.protocol-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.protocol-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  border-bottom: 1px solid $border-color;
  white-space: normal;
  vertical-align: middle;
}

.protocol-table th,
.protocol-table td {
  border-right: 1px solid $border-color;
  border-bottom: 1px solid $border-color;
  padding: 12px;
  text-align: center;
  font-size: 14px;
}
.protocol-table th:first-child,
.protocol-table td:first-child {
  border-left: 1px solid $border-color;
}

.protocol-table tr:nth-child(even) td {
  background: #fbfdff;
}
.protocol-table tbody tr:hover td {
  background: #eef6ff;
}

.th-title {
  color: #667085;
  font-size: 12px;
  margin-right: 6px;
}
.group-name {
  font-weight: 600;
  color: #101828;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.th-chip {
  display: inline-block;
  font-size: 12px;
  background: #eef2ff;
  color: #3538cd;
  border: 1px solid #e0e7ff;
  padding: 1px 8px;
  border-radius: 999px;
}

.model-cell {
  text-align: left;
  background: #fff;
}
.model-title {
  font-weight: 600;
  color: #101828;
}

/* Checkbox */
.chk-wrap {
  --size: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--size);
  height: var(--size);
  position: relative;
  cursor: pointer;
  background: transparent;
}
.chk-wrap input {
  opacity: 0;
  width: var(--size);
  height: var(--size);
  position: absolute;
  margin: 0;
}
.fa-chk {
  font-size: 18px;
  line-height: 1;
  pointer-events: none;
  color: #98a2b3;
}
.chk-wrap input:checked + .fa-chk {
  color: $primary-color;
}
.chk-wrap:focus-within .fa-chk {
  outline: 2px solid rgba(52, 96, 255, .25);
  outline-offset: 2px;
}

/* Preview Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 12, 34, 0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 12px;
}

.protocol-preview-modal, .validation-modal {
  background: white;
  border-radius: 12px;
  width: 96%;
  max-width: 900px;
  padding: 20px;
  box-shadow: 0 20px 50px rgba(16,24,40,.18);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 14px;
  background: #f2f4f7;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid $border-color;
}

.preview-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #344054;
}

.spacer { flex: 1; }

.preview-content {
  background: white;
  padding: 16px;
  border: 1px solid $border-color;
  border-radius: 10px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

/* Footer */
.matrix-actions {
  position: sticky;
  bottom: 0;
  padding: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  z-index: 10;
}

.btn-option,
.btn-primary {
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  font-size: 14px;
  border: 1px solid transparent;
  transition: transform .05s ease, box-shadow .2s ease, background .2s ease, color .2s ease, border-color .2s ease;
}

.btn-option {
  background: #ffffff;
  border: 1px solid $border-color;
  color: #111827;
}
.btn-option:hover {
  background: #f8fafc;
  box-shadow: 0 6px 14px rgba(16,24,40,.08);
}

.btn-primary {
  background: $primary-color;
  color: #fff;
}
.btn-primary:hover {
  background: darken($primary-color, 6%);
  box-shadow: 0 8px 18px rgba(52, 96, 255, .25);
}

/* Validation modal */
.validation-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 800;
  color: #101828;
}
.validation-text {
  margin: 0 0 10px;
  color: #475467;
}
.empty-visits-list {
  margin: 0 0 8px 18px;
  padding: 0;
  list-style: disc;
  color: #344054;
  max-height: 40vh;
  overflow-y: auto;
}
.empty-visits-list .visit-item-title {
  display: inline-block;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.3;
}
</style>
