<template>
  <div class="merge-page">
    <!-- Header -->
    <div class="back-header-row">
      <div class="back-button-container">
        <button class="btn-minimal" @click="goBack">
          <i :class="icons.back" aria-hidden="true"></i> Back
        </button>
      </div>
      <h2 class="existing-studies-title">Merge Study Data</h2>
    </div>

    <!-- Study meta + file chooser -->
    <div class="top-bar card-surface">
      <div class="meta">
        <div class="meta-title">Study: <strong>{{ meta.study_name || '—' }}</strong></div>
        <div class="meta-sub" v-if="meta.study_description">{{ meta.study_description }}</div>
        <div class="meta-stats">
          Subjects: {{ subjects.length }} · Visits: {{ visits.length }} · Groups: {{ groups.length }}
        </div>
      </div>

      <div class="actions">
        <input ref="fileInput" type="file" accept=".csv,.xlsx,.xls" class="file-hidden" @change="onFile" />
        <button class="btn-primary" @click="triggerFile">Choose File</button>
        <button class="btn-option" :disabled="!hasIncoming" @click="clearIncoming">Clear</button>
      </div>
    </div>

    <div v-if="parseInfo.message" class="parse-banner" :class="parseInfo.ok ? 'ok' : 'warn'">
      {{ parseInfo.message }}
    </div>

    <div class="main-layout" v-if="hasIncoming">
      <!-- Left: tree -->
      <aside class="tree-panel card-surface">
        <div class="tree-head">
          <div class="tree-title">Incoming</div>
          <label class="chk">
            <input type="checkbox" v-model="showConflictsOnly" /> Conflicts only
          </label>
        </div>

        <div class="tree-scroll">
          <ul class="tree">
            <li v-for="sid in treeSubjects" :key="sid" class="tree-subject">
              <button
                class="tree-row subject"
                :class="{ active: sid === sel.subjectId }"
                @click="selectSubject(sid)"
                :title="sid"
              >
                <span class="label">Subject</span>
                <strong class="value">{{ sid }}</strong>
                <span class="counts" v-if="countsBySubject[sid]">
                  <span class="badge conflict" v-if="countsBySubject[sid].conflict">
                    {{ countsBySubject[sid].conflict }}
                  </span>
                </span>
              </button>

              <ul v-if="sid === sel.subjectId">
                <li
                  v-for="vn in treeVisitsForSubject(sid)"
                  :key="sid + '|' + vn"
                  class="tree-visit"
                >
                  <button
                    class="tree-row visit"
                    :class="{ active: vn === sel.visitName }"
                    @click="selectVisit(vn)"
                    :title="vn"
                  >
                    <span class="label">Visit</span>
                    <strong class="value">{{ vn }}</strong>
                    <span class="counts" v-if="countsByVisit[sid+'|'+vn]">
                      <span class="badge conflict" v-if="countsByVisit[sid+'|'+vn].conflict">
                        {{ countsByVisit[sid+'|'+vn].conflict }}
                      </span>
                    </span>
                  </button>

                  <ul v-if="vn === sel.visitName">
                    <li
                      v-for="sec in treeSectionsFor(sid, vn)"
                      :key="sid + '|' + vn + '|' + sec"
                      class="tree-section"
                    >
                      <button
                        class="tree-row section"
                        :class="{ active: sec === sel.sectionName }"
                        @click="selectSection(sec)"
                        :title="sec"
                      >
                        <span class="label">Section</span>
                        <strong class="value">{{ sec }}</strong>
                        <span class="counts" v-if="countsBySection[sid+'|'+vn+'|'+sec]">
                          <span class="badge conflict" v-if="countsBySection[sid+'|'+vn+'|'+sec].conflict">
                            {{ countsBySection[sid+'|'+vn+'|'+sec].conflict }}
                          </span>
                        </span>
                      </button>
                    </li>
                  </ul>
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </aside>

      <!-- Right: side-by-side compare -->
      <section class="compare-panel card-surface" :class="{ fullscreen: isFullscreen }" ref="comparePanel" tabindex="-1">
        <div class="compare-head">
          <div class="path">
            <span>Subject:</span> <strong>{{ sel.subjectId || '—' }}</strong>
            <span class="sep">·</span>
            <span>Visit:</span> <strong>{{ sel.visitName || '—' }}</strong>
            <span class="sep">·</span>
            <span>Section:</span> <strong>{{ sel.sectionName || '—' }}</strong>
          </div>

        <div class="compare-actions">
            <button class="btn-option" :disabled="!sectionRows.length" @click="keepAllExisting">Keep existing</button>
            <button class="btn-option" :disabled="!sectionRows.length" @click="acceptAllIncoming">Accept all incoming</button>
            <button class="btn-option" :disabled="!sectionRows.length" @click="acceptIncomingWhereEmpty">Accept where empty</button>
            <button class="btn-primary" :disabled="!canCommitSection" @click="commitCurrentSelection">
              {{ isCommitting ? 'Merging…' : 'Commit Section' }}
            </button>
            <button class="btn-minimal" @click="toggleFullscreen" :title="isFullscreen ? 'Exit full size' : 'Enlarge'">
              <i :class="isFullscreen ? (icons.compress || 'fas fa-compress') : (icons.expand || 'fas fa-expand')" aria-hidden="true"></i>
              <span>{{ isFullscreen ? 'Exit' : 'Enlarge' }}</span>
            </button>
          </div>
        </div>

        <div v-if="!sectionRows.length" class="empty-note big">
          Select a Section from the left to compare values.
        </div>

        <div v-else class="split-view" @keydown.esc="ensureExitFullscreen">
          <div class="col col-existing">
            <div class="col-title">Existing</div>
            <table class="val-table">
              <thead>
                <tr>
                  <th style="width: 38%;">Field</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sectionRows" :key="row.key" :class="rowClass(row)">
                  <td class="field-name">
                    {{ row.display }}
                    <span class="resolved-pill" v-if="row.resolved">Resolved</span>
                  </td>
                  <td class="value-cell">{{ displayVal(row.existing) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="col col-incoming">
            <div class="col-title">Incoming</div>
            <table class="val-table">
              <thead>
                <tr>
                  <th style="width: 38%;">Field</th>
                  <th>
                    Value
                    <span class="hint">(choose)</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sectionRows" :key="row.key" :class="rowClass(row)">
                  <td class="field-name">
                    {{ row.display }}
                    <span class="resolved-pill" v-if="row.resolved">Resolved</span>
                  </td>
                  <td class="value-cell">
                    <div class="value">{{ displayVal(row.incoming) }}</div>
                    <div class="resolve">
                      <label class="radio">
                        <input
                          type="radio"
                          :name="row.radioName"
                          value="incoming"
                          :checked="decisions[row.key] === 'incoming'"
                          @change="setDecision(row.key, 'incoming')"
                        />
                        Use incoming
                      </label>
                      <label class="radio" :class="{ muted: !hasValue(row.existing) }">
                        <input
                          type="radio"
                          :name="row.radioName"
                          value="existing"
                          :checked="decisions[row.key] === 'existing'"
                          @change="setDecision(row.key, 'existing')"
                        />
                        Keep existing
                      </label>
                      <label class="radio" v-if="!hasValue(row.existing) && !hasValue(row.incoming)">
                        <input
                          type="radio"
                          :name="row.radioName"
                          value="none"
                          :checked="decisions[row.key] === 'none'"
                          @change="setDecision(row.key, 'none')"
                        />
                        Leave empty
                      </label>
                      <button class="btn-minimal" v-if="decisions[row.key]" @click="clearDecision(row.key)">Clear</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <!-- Sticky footer -->
    <div class="global-commit" v-if="hasIncoming">
      <div class="gc-left">
        <div class="sel-path">
          <span>Subject:</span> <strong>{{ sel.subjectId || '—' }}</strong>
          <span class="sep">·</span>
          <span>Visit:</span> <strong>{{ sel.visitName || '—' }}</strong>
          <span class="sep">·</span>
          <span>Section:</span> <strong>{{ sel.sectionName || '—' }}</strong>
        </div>
        <div class="sel-counts" v-if="sectionRows.length">
          Unresolved Conflicts: <strong>{{ currentCounts.conflict }}</strong>
          <span class="dot">·</span>
          Adds: <strong>{{ currentCounts.add }}</strong>
          <span class="dot">·</span>
          Same/Resolved: <strong>{{ currentCounts.same }}</strong>
        </div>
      </div>
      <div class="gc-right">
        <button class="btn-primary" :disabled="!canCommitSection" @click="commitCurrentSelection">
          {{ isCommitting ? 'Merging…' : 'Merge & Commit' }}
        </button>
        <button class="btn-option" :disabled="!sectionRows.length || isCommitting" @click="resetCurrentDecisions">Reset</button>
      </div>
    </div>

    <CustomDialog :message="dialogMessage" :isVisible="showDialog" @close="closeDialog" />
  </div>
</template>

<script>
/* eslint-disable */
import axios from "axios";
import * as Papa from "papaparse";
import * as XLSX from "xlsx";
import CustomDialog from "@/components/CustomDialog.vue";
import icons from "@/assets/styles/icons";

export default {
  name: "MergeStudy",
  components: { CustomDialog },
  data() {
    return {
      icons,
      studyId: null,
      study: null,
      meta: {},
      subjects: [],
      visits: [],
      groups: [],
      subjectToGroupIdx: [],

      // template index
      sectionIndex: new Map(),       // title -> { displayByCanon, fieldNameByCanon, fieldTypeByCanon }
      sectionTitleByCanon: new Map(),// canon(sectionTitle) -> sectionTitle (exact template title)

      // server entries
      entries: [],
      entriesIndex: new Map(),

      // incoming parsed file
      incoming: {},        // sid -> visitName -> { sections: { [secTitle]: { [rawFieldOrLabel]: val } }, groupName }
      decisions: {},       // key -> 'incoming' | 'existing' | 'none'
      showConflictsOnly: false,

      // selection in UI
      sel: { subjectId: "", visitName: "", sectionName: "" },

      parseInfo: { ok: false, message: "" },
      isFullscreen: false,
      isCommitting: false,

      showDialog: false,
      dialogMessage: "",
    };
  },
  computed: {
    hasIncoming() { return Object.keys(this.incoming || {}).length > 0; },
    treeSubjects() { return Object.keys(this.incoming || {}).sort(); },
    canCommitSection() { return this.sectionRows.length > 0 && !this.isCommitting; },

    countsBySubject() {
      const out = {};
      for (const sid of Object.keys(this.incoming)) {
        let c = { conflict: 0, add: 0, same: 0 };
        for (const vn of Object.keys(this.incoming[sid])) {
          const s = this.countFor(sid, vn);
          c.conflict += s.conflict; c.add += s.add; c.same += s.same;
        }
        out[sid] = c;
      }
      return out;
    },
    countsByVisit() {
      const out = {};
      for (const sid of Object.keys(this.incoming)) {
        for (const vn of Object.keys(this.incoming[sid])) {
          out[`${sid}|${vn}`] = this.countFor(sid, vn);
        }
      }
      return out;
    },
    countsBySection() {
      const out = {};
      for (const sid of Object.keys(this.incoming)) {
        for (const vn of Object.keys(this.incoming[sid])) {
          const secs = Object.keys(this.incoming[sid][vn]?.sections || {});
          for (const sec of secs) out[`${sid}|${vn}|${sec}`] = this.countFor(sid, vn, sec);
        }
      }
      return out;
    },

    sectionRows() {
      const sid = this.sel.subjectId, vn = this.sel.visitName, sec = this.sel.sectionName;
      if (!sid || !vn || !sec) return [];

      const { sIdx, vIdx, gIdx } = this.resolveSVG(sid, vn);
      if (sIdx < 0 || vIdx < 0) return [];

      const existingDict = this.entryToDictNormalized(this.entriesIndex.get(`${sIdx}|${vIdx}|${gIdx}`));
      const incomingDict = this.incomingNormalized();

      const exSec = (existingDict[sec] || {});
      const inSec = (incomingDict[sid]?.[vn]?.sections?.[sec] || {});

      const allCanons = Array.from(new Set([...Object.keys(exSec), ...Object.keys(inSec)])).sort();

      const rows = [];
      for (const canon of allCanons) {
        const display = this.displayFor(sec, canon);
        const existing = exSec[canon];
        const incoming = inSec[canon];

        if (!this.hasValue(existing) && !this.hasValue(incoming)) continue;

        const rawState = this.decideState(existing, incoming);
        const key = `${sid}|${vn}|${sec}|${canon}`;
        const decision = this.decisions[key];

        const resolved = (rawState === "conflict" && !!decision) ? true : false;
        const state = resolved ? "same" : rawState;

        rows.push({
          key,
          radioName: `choose|${sid}|${vn}|${sec}|${canon}`,
          display,
          canon,
          existing,
          incoming,
          resolved,
          state,
        });
      }

      this.$nextTick(() => this.ensureAutoDecisions(rows));
      return this.showConflictsOnly ? rows.filter(r => r.state === "conflict") : rows;
    },

    currentCounts() {
      let c = { conflict: 0, add: 0, same: 0 };
      for (const r of this.sectionRows) {
        if (r.state === "conflict") c.conflict++;
        else if (r.state === "add") c.add++;
        else c.same++;
      }
      return c;
    },
  },
  async created() {
    this.studyId = this.$route.params.id;
    await this.loadStudy();
    await this.loadEntries();
    this.indexEntries();
    this.buildSectionIndex();
  },
  methods: {
    normalizeCheckbox(val) {
      if (val === true) return true;
      if (val === false) return false;
      if (val == null || String(val).trim() === '') return ''; // preserve empty
      const s = String(val).trim().toLowerCase();
      if (['true','yes','1','y','on','checked'].includes(s)) return true;
      if (['false','no','0','n','off','unchecked'].includes(s)) return false;
      return '';
    },
    // ---------- Navigation ----------
    goBack() { this.$router.push({ name: "Dashboard", query: { openStudies: "true" } }); },
    selectSubject(sid) {
      this.sel.subjectId = sid;
      const visits = this.treeVisitsForSubject(sid);
      this.sel.visitName = visits[0] || "";
      const secs = this.sel.visitName ? this.treeSectionsFor(sid, this.sel.visitName) : [];
      this.sel.sectionName = secs[0] || "";
    },
    selectVisit(vn) {
      this.sel.visitName = vn;
      const secs = this.sel.subjectId ? this.treeSectionsFor(this.sel.subjectId, vn) : [];
      this.sel.sectionName = secs[0] || "";
    },
    selectSection(sec) { this.sel.sectionName = sec; },

    showDialogMessage(msg) { this.dialogMessage = msg; this.showDialog = true; },
    closeDialog() { this.showDialog = false; this.dialogMessage = ""; },
    triggerFile() { this.$refs.fileInput && this.$refs.fileInput.click(); },
    toggleFullscreen() { this.isFullscreen = !this.isFullscreen; if (this.isFullscreen) this.$nextTick(() => this.$refs.comparePanel?.focus?.()); },
    ensureExitFullscreen() { if (this.isFullscreen) this.isFullscreen = false; },

    // ---------- Load ----------
    async loadStudy() {
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}`, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` }
        });
        this.study = data;
        this.meta = data?.metadata || {};
        const sd = data?.content?.study_data || {};
        this.subjects = sd.subjects || [];
        this.visits   = sd.visits || [];
        this.groups   = sd.groups || [];
        this.subjectToGroupIdx = (this.subjects || []).map(s => {
          const gn = (s.group || "").toLowerCase().trim();
          const gi = (this.groups || []).findIndex(g => (g.name || "").toLowerCase().trim() === gn);
          return gi >= 0 ? gi : 0;
        });
        console.log('[Merge] Study loaded', { subjects: this.subjects.length, visits: this.visits.length, groups: this.groups.length });
      } catch (e) {
        console.error('[Merge] Failed to load study:', e);
        this.showDialogMessage("Failed to load study.");
      }
    },
    async loadEntries() {
      try {
        const { data } = await axios.get(`/forms/studies/${this.studyId}/data_entries`, {
          headers: { Authorization: `Bearer ${this.$store.state.token}` }
        });
        this.entries = Array.isArray(data) ? data : (data?.entries || []);
        console.log('[Merge] Loaded entries', this.entries.length);
      } catch (e) {
        console.error('[Merge] Failed to load entries:', e);
        this.entries = [];
      }
    },
    indexEntries() {
      const m = new Map();
      for (const e of this.entries) {
        const key = `${e.subject_index}|${e.visit_index}|${e.group_index}`;
        const cur = m.get(key);
        if (!cur || Number(e.form_version) >= Number(cur?.form_version || 0)) m.set(key, e);
      }
      this.entriesIndex = m;
    },

    // ---------- Template index & section title mapping ----------
    buildSectionIndex() {
      this.sectionIndex = new Map();
      this.sectionTitleByCanon = new Map();

      const models = this.study?.content?.study_data?.selectedModels || [];
      models.forEach((sec) => {
        const title = sec?.title || "";
        if (!title) return;

        const displayByCanon = {};
        const fieldNameByCanon = {};
        const fieldTypeByCanon = {};

        // section title canonical map (for CSV section → template section)
        this.sectionTitleByCanon.set(this.canonKey(title), title);

        (sec.fields || []).forEach((f, idx) => {
          const label = f?.label || f?.title || f?.name || `Field ${idx + 1}`;
          const name  = f?.name  || label; // key used by data-entry save path
          const type  = (f?.type || '').toLowerCase();

          // candidates that should map to this field (for matching CSV + existing)
          const candidates = new Set([
            name,
            label,
            f?.title || "",
            this.humanizeCamel(name),
            this.humanizeCamel(label),
          ].filter(Boolean));

          for (const c of candidates) {
            const canon = this.canonKey(c);
            fieldNameByCanon[canon] = name;       // map many -> one name
            fieldTypeByCanon[this.canonKey(name)] = type; // type keyed by name’s canon
          }

          // UI display map: show label for the canon(name)
          displayByCanon[this.canonKey(name)] = label;
        });

        // IMPORTANT: store fieldTypeByCanon too (used later for checkbox handling, etc.)
        this.sectionIndex.set(title, { displayByCanon, fieldNameByCanon, fieldTypeByCanon });
      });

      console.log('[Merge] Section index built for', this.sectionIndex.size, 'sections');
    },

    mapSectionTitle(raw) {
      const mapped = this.sectionTitleByCanon.get(this.canonKey(raw));
      return mapped || raw;
    },

    displayFor(sectionTitle, canon) {
      const m = this.sectionIndex.get(sectionTitle);
      return (m?.displayByCanon?.[canon]) || this.prettyFromCanon(canon);
    },

    // ---------- Normalization helpers ----------
    canonKey(s) {
      return String(s ?? "")
        .toLowerCase()
        .replace(/[\W_]+/g, ''); // strip non-alphanumerics
    },
    humanizeCamel(s) {
      if (!s) return "";
      const w = String(s)
        .replace(/[_\-]+/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .toLowerCase();
      return w.replace(/\b\w/g, c => c.toUpperCase());
    },
    prettyFromCanon(canon) { return this.humanizeCamel(canon); },
    hasValue(v) { return v !== null && v !== undefined && String(v).trim() !== ""; },
    displayVal(v) { return this.hasValue(v) ? String(v) : ""; },

    /**
     * Normalize a section dict (incoming labels or existing names) to:
     *   { canon(field.name) -> value }
     * We ALWAYS key by canon(field.name) to avoid duplicates (label vs name).
     */
    normalizeSectionDict(sectionTitle, rawSectionDict) {
      const out = {};
      if (!rawSectionDict || typeof rawSectionDict !== 'object') return out;

      const idx = this.sectionIndex.get(sectionTitle);
      if (!idx) return out;

      for (const rawKey of Object.keys(rawSectionDict)) {
        const cRaw = this.canonKey(rawKey);
        const fieldName = idx.fieldNameByCanon?.[cRaw]; // resolve to template field.name
        if (!fieldName) continue;

        const canonName = this.canonKey(fieldName);     // <-- single source of truth
        const val = rawSectionDict[rawKey];
        if (!(canonName in out) || this.hasValue(val)) out[canonName] = val;
      }
      return out;
    },

    // existing entry (server) -> { sectionTitle -> { canon(field.name) -> value } }
    entryToDictNormalized(entry) {
      const models = this.study?.content?.study_data?.selectedModels || [];
      const out = {};
      if (!entry) {
        for (const sec of models) out[sec.title] = {};
        return out;
      }

      if (entry.data && !Array.isArray(entry.data) && typeof entry.data === "object") {
        for (const sec of models) {
          const secTitle = sec.title;
          const secObj = entry.data?.[secTitle] || {};
          // Build a dict by field.name, then normalize once more
          const byName = {};
          (sec.fields || []).forEach((f) => {
            const name = f?.name || "";
            const label = f?.label || f?.title || "";
            if (!name) return;
            let v = secObj[name];
            if (v === undefined) v = secObj[label]; // tolerate legacy label-saved records
            if (v !== undefined) byName[name] = v;
          });
          out[secTitle] = this.normalizeSectionDict(secTitle, byName);
        }
        return out;
      }

      // array-shape fallback (older entries)
      const arr = Array.isArray(entry.data) ? entry.data : [];
      models.forEach((sec, sIdx) => {
        const secTitle = sec.title;
        const row = Array.isArray(arr[sIdx]) ? arr[sIdx] : [];
        const byName = {};
        (sec.fields || []).forEach((f, fIdx) => {
          const name = f?.name || f?.label || f?.title || `Field ${fIdx + 1}`;
          byName[name] = row[fIdx] != null ? row[fIdx] : "";
        });
        out[secTitle] = this.normalizeSectionDict(secTitle, byName);
      });
      return out;
    },

    // incoming (parsed file) -> { subjectId -> visitName -> { sections: { sectionTitle -> { canon(field.name) -> value } }, groupName } }
    incomingNormalized() {
      const out = {};
      for (const sid of Object.keys(this.incoming || {})) {
        out[sid] = {};
        for (const vn of Object.keys(this.incoming[sid] || {})) {
          const row = this.incoming[sid][vn];
          const secOut = {};
          const secMap = row?.sections || {};
          for (const rawSecName of Object.keys(secMap)) {
            const secTitle = this.mapSectionTitle(rawSecName);
            secOut[secTitle] = this.normalizeSectionDict(secTitle, secMap[rawSecName]);
          }
          out[sid][vn] = { sections: secOut, groupName: row.groupName || "" };
        }
      }
      return out;
    },

    // ---------- CSV/XLSX parsing (2 header rows) ----------
    onFile(ev) {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      const name = f.name.toLowerCase();
      if (name.endsWith(".csv")) this.readCSV(f);
      else if (name.endsWith(".xlsx") || name.endsWith(".xls")) this.readXLSX(f);
      else this.parseInfo = { ok: false, message: "Unsupported file type. Use CSV or Excel." };
    },
    readCSV(file) {
      Papa.parse(file, {
        skipEmptyLines: "greedy",
        complete: (res) => this.consume2RowHeader(res.data || []),
        error: () => this.parseInfo = { ok: false, message: "Failed to read CSV." }
      });
    },
    readXLSX(file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const wb = XLSX.read(new Uint8Array(e.target.result), { type: "array" });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false, defval: "" });
        this.consume2RowHeader(rows);
      };
      reader.onerror = () => this.parseInfo = { ok: false, message: "Failed to read Excel file." };
      reader.readAsArrayBuffer(file);
    },
    consume2RowHeader(rows) {
      if (!rows || rows.length < 3) {
        this.parseInfo = { ok: false, message: "Need 2 header rows + at least 1 data row." };
        return;
      }
      const H0 = rows[0].map(x => String(x || "").trim()); // sections
      const H1 = rows[1].map(x => String(x || "").trim()); // fields

      const idxOf = (names) => {
        const lc1 = H1.map(h => h.toLowerCase());
        const lc0 = H0.map(h => h.toLowerCase());
        for (let i = 0; i < H1.length; i++) {
          for (const n of names) {
            const nn = n.toLowerCase();
            if (lc1[i] === nn || lc0[i] === nn) return i;
          }
        }
        return -1;
      };
      const cSubject = idxOf(["subject id","subject","subject_id","participant id"]);
      const cVisit   = idxOf(["visit","visit name","visit_name"]);
      const cGroup   = idxOf(["group","arm","cohort"]);

      if (cSubject < 0 || cVisit < 0) {
        this.parseInfo = { ok: false, message: "Could not detect Subject and Visit columns." };
        return;
      }

      // Map columns to (section, field label/name) with sticky section cells
      const colMap = [];
      let currentSection = "";
      for (let col = 0; col < H1.length; col++) {
        if ([cSubject,cVisit,cGroup].includes(col)) continue;
        const secRaw = (H0[col] || "").trim();
        if (secRaw) currentSection = secRaw;
        const field = (H1[col] || "").trim();
        if (!currentSection || !field) continue;

        // Map the section title to the template's title now (tolerant)
        const mappedSection = this.mapSectionTitle(currentSection);
        colMap.push({ col, section: mappedSection, field }); // keep raw "field" (label or name); we normalize later
      }
      if (!colMap.length) {
        this.parseInfo = { ok: false, message: "No (section, field) columns found." };
        return;
      }

      const incoming = {};
      let dataRows = 0;

      for (let r = 2; r < rows.length; r++) {
        const row = rows[r] || [];
        const sid = String(row[cSubject] || "").trim();
        const vn  = String(row[cVisit] || "").trim();
        const gn  = (cGroup >= 0) ? String(row[cGroup] || "").trim() : "";
        if (!sid || !vn) continue;

        incoming[sid] ||= {};
        incoming[sid][vn] ||= { sections: {}, groupName: gn };

        for (const m of colMap) {
          const v = row[m.col];
          incoming[sid][vn].sections[m.section] ||= {};
          // NOTE: we keep raw header here (label or name). normalizeSectionDict will map to canon(field.name).
          incoming[sid][vn].sections[m.section][m.field] = this.normalizeCell(v);
        }
        dataRows++;
      }

      if (!dataRows) {
        this.parseInfo = { ok: false, message: "No data rows found." };
        this.incoming = {};
        return;
      }

      this.incoming = incoming;
      this.parseInfo = { ok: true, message: `Parsed ${dataRows} row(s).` };

      // Default selection
      const sid0 = Object.keys(incoming)[0];
      const vn0  = sid0 ? Object.keys(incoming[sid0])[0] : "";
      const sec0 = (sid0 && vn0) ? Object.keys(incoming[sid0][vn0].sections || {})[0] : "";
      this.sel = { subjectId: sid0 || "", visitName: vn0 || "", sectionName: sec0 || "" };
      this.decisions = {};
      console.log('[Merge] Parsed file; initial selection', this.sel);
    },

    // ---------- Tree helpers ----------
    treeVisitsForSubject(sid) {
      const map = this.incoming[sid] || {};
      let vns = Object.keys(map);
      if (this.showConflictsOnly) vns = vns.filter(vn => this.countFor(sid, vn).conflict > 0);
      return vns.sort();
    },
    treeSectionsFor(sid, vn) {
      const secs = Object.keys(this.incoming[sid]?.[vn]?.sections || {});
      return (this.showConflictsOnly
        ? secs.filter(sec => this.countFor(sid, vn, sec).conflict > 0)
        : secs
      ).sort();
    },

    // ---------- Compare & counts ----------
    resolveSVG(subjectId, visitName) {
      const sIdx = this.subjects.findIndex(s => String(s.id).trim() === String(subjectId).trim());
      const vIdx = this.visits.findIndex(v => (v.name || "").trim().toLowerCase() === String(visitName).trim().toLowerCase());
      const gIdx = sIdx >= 0 ? (this.subjectToGroupIdx[sIdx] ?? 0) : 0;
      return { sIdx, vIdx, gIdx };
    },
    countFor(sid, vn, secOpt) {
      const { sIdx, vIdx, gIdx } = this.resolveSVG(sid, vn);
      const exAll = (sIdx >= 0 && vIdx >= 0) ? this.entryToDictNormalized(this.entriesIndex.get(`${sIdx}|${vIdx}|${gIdx}`)) : {};
      const inAll = this.incomingNormalized();

      let conflict = 0, add = 0, same = 0;
      const secs = secOpt ? [secOpt] : Object.keys(inAll[sid]?.[vn]?.sections || {});
      for (const sec of secs) {
        const exSec = (exAll?.[sec] || {});
        const inSec = (inAll?.[sid]?.[vn]?.sections?.[sec] || {});
        const canons = new Set([...Object.keys(exSec), ...Object.keys(inSec)]);
        for (const c of canons) {
          const ex = exSec[c], i = inSec[c];
          if (!this.hasValue(ex) && !this.hasValue(i)) continue;
          const st = this.decideState(ex, i);

          if (st === "conflict" && this.decisions[`${sid}|${vn}|${sec}|${c}`]) { // resolved by decision
            same++; continue;
          }

          if (st === "conflict") conflict++;
          else if (st === "add") add++;
          else same++;
        }
      }
      return { conflict, add, same };
    },

    decideState(existing, incoming) {
      const hv = (v) => v !== null && v !== undefined && String(v).trim() !== "";
      if (!hv(existing) && !hv(incoming)) return "same";
      if (hv(existing) && hv(incoming)) return this.valuesEqual(existing, incoming) ? "same" : "conflict";
      return hv(incoming) ? "add" : "same";
    },
    valuesEqual(a, b) {
      const hv = (v) => v !== null && v !== undefined && String(v).trim() !== "";
      if (!hv(a) && !hv(b)) return true;
      const aa = String(a ?? "").trim();
      const bb = String(b ?? "").trim();
      const na = Number(aa), nb = Number(bb);
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na === nb;
      return aa === bb;
    },

    rowClass(row) {
      return {
        conflict: row.state === "conflict",
        add: row.state === "add",
        same: row.state === "same",
      };
    },

    // ---------- Decisions ----------
    ensureAutoDecisions(rows = this.sectionRows) {
      for (const r of rows) {
        if (this.decisions[r.key]) continue;
        const hasEx = this.hasValue(r.existing);
        const hasIn = this.hasValue(r.incoming);
        if (hasIn && !hasEx) this.setDecision(r.key, "incoming");
        else if (hasEx && !hasIn) this.setDecision(r.key, "existing");
      }
    },
    setDecision(key, choice) {
      const next = { ...this.decisions, [key]: choice };
      this.decisions = next;
    },
    clearDecision(key) {
      const next = { ...this.decisions };
      delete next[key];
      this.decisions = next;
    },
    keepAllExisting() {
      for (const r of this.sectionRows) {
        this.setDecision(r.key, this.hasValue(r.existing) ? "existing" : "none");
      }
    },
    acceptAllIncoming() {
      for (const r of this.sectionRows) this.setDecision(r.key, "incoming");
    },
    acceptIncomingWhereEmpty() {
      for (const r of this.sectionRows) {
        if (!this.hasValue(r.existing) && this.hasValue(r.incoming)) this.setDecision(r.key, "incoming");
      }
    },
    resetCurrentDecisions() {
      const keys = this.sectionRows.map(r => r.key);
      const next = { ...this.decisions };
      for (const k of keys) delete next[k];
      this.decisions = next;
      this.$nextTick(() => this.ensureAutoDecisions());
    },

    // ---------- Commit ----------
    normalizeCell(v) { return v == null ? "" : String(v).trim(); },

    // Build skipped flags (m x n) from template
    makeSkipSkeleton() {
      const models = this.study?.content?.study_data?.selectedModels || [];
      return models.map(sec => (sec.fields || []).map(() => false));
    },

    // Convert normalized dict (canon(field.name) -> value) back to server dict using template field.name keys
    denormalizeForSave(normBySection) {
      const out = {};
      for (const rawSecName of Object.keys(normBySection || {})) {
        const secTitle = this.mapSectionTitle(rawSecName);
        const secDictCanon = normBySection[rawSecName] || {};
        const map = this.sectionIndex.get(secTitle);
        if (!map) continue;

        const row = {};
        for (const canon of Object.keys(secDictCanon)) {
          const fieldKey = map.fieldNameByCanon?.[canon]; // template field.name
          if (!fieldKey) continue;

          const fType = map.fieldTypeByCanon?.[canon];
          let val = secDictCanon[canon];                 // <-- let (not const)
          if (fType === 'checkbox') val = this.normalizeCheckbox(val);
          row[fieldKey] = val;
        }
        if (Object.keys(row).length > 0) {
          out[secTitle] = row; // only include non-empty sections
        }
      }
      return out;
    },

    async commitCurrentSelection() {
      const sid = this.sel.subjectId, vn = this.sel.visitName, sec = this.sel.sectionName;
      if (!sid || !vn || !sec || !this.sectionRows.length) {
        console.log('[Merge] Commit skipped: selection incomplete or no rows', { sid, vn, sec, rows: this.sectionRows.length });
        return;
      }

      const { sIdx, vIdx, gIdx } = this.resolveSVG(sid, vn);
      if (sIdx < 0 || vIdx < 0) {
        this.showDialogMessage("Selected Subject/Visit not found in study.");
        console.warn('[Merge] Subject/Visit not found', { sid, vn, sIdx, vIdx });
        return;
      }

      const existing = this.entriesIndex.get(`${sIdx}|${vIdx}|${gIdx}`);
      const baseDict = this.entryToDictNormalized(existing);
      baseDict[sec] ||= {};

      // apply decisions
      for (const r of this.sectionRows) {
        const decision = this.decisions[r.key];
        if (decision === "incoming") baseDict[sec][r.canon] = r.incoming;
        else if (decision === "existing") baseDict[sec][r.canon] = this.hasValue(r.existing) ? r.existing : "";
        else if (decision === "none") baseDict[sec][r.canon] = "";
        else {
          if (r.state === "add") baseDict[sec][r.canon] = r.incoming;
          else if (r.state === "conflict") baseDict[sec][r.canon] = r.existing;
        }
      }

      // to server shape (section title -> field.name -> value), skipping unknown/empty sections
      const payload = {
        study_id: this.studyId,
        subject_index: sIdx,
        visit_index: vIdx,
        group_index: gIdx,
        data: this.denormalizeForSave(baseDict),
        skipped_required_flags: this.makeSkipSkeleton(),
      };

      console.log('[Merge] COMMIT payload', JSON.parse(JSON.stringify(payload)));

      this.isCommitting = true;
      try {
        const headers = { headers: { Authorization: `Bearer ${this.$store.state.token}` } };
        if (existing?.id) {
          await axios.put(`/forms/studies/${this.studyId}/data_entries/${existing.id}`, payload, headers);
          console.log('[Merge] PUT OK', existing.id);
        } else {
          const { data } = await axios.post(`/forms/studies/${this.studyId}/data`, payload, headers);
          console.log('[Merge] POST OK', data?.id);
        }

        await this.loadEntries();
        this.indexEntries();

        // clear decisions for this section after success
        for (const r of this.sectionRows) this.clearDecision(r.key);

        this.showDialogMessage("Merged successfully.");
        this.$nextTick(() => this.ensureAutoDecisions());
      } catch (e) {
        console.error('[Merge] Commit failed:', e?.response?.data || e);
        this.showDialogMessage("Merge failed. See console.");
      } finally {
        this.isCommitting = false;
      }
    },
  }
};
</script>

<style scoped>
/* Shared surface + buttons (consistent with eCRF) */
.card-surface {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 25px rgba(16,24,40,0.06);
}
.btn-primary {
  background: #2f6fed;
  border: 1px solid #245fe0;
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  transition: background .15s ease, box-shadow .2s ease, transform .02s ease;
}
.btn-primary:hover { background: #285fce; box-shadow: 0 2px 10px rgba(47,111,237,.25); }
.btn-option {
  background: #fff;
  border: 1px solid #e0e0e0;
  color: #111827;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  transition: background .15s ease;
}
.btn-option:hover { background: #f8fafc; }
.btn-minimal {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-minimal:hover { background: #e8e8e8; color: #000; border-color: #d6d6d6; }
.file-hidden { display: none; }

/* Page shell */
.merge-page { max-width: 1160px; margin: 24px auto; padding: 0 16px 72px; }
.back-header-row { position: relative; display: flex; align-items: center; justify-content: center; min-height: 42px; margin-bottom: 12px; }
.back-button-container { position: absolute; left: 0; top: 50%; transform: translateY(-50%); }
.existing-studies-title { margin: 0; font-size: 20px; color: #333; }

/* Top bar */
.top-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; margin-bottom: 12px; }
.meta-title { font-size: 16px; color: #111827; }
.meta-sub { color: #4b5563; margin-top: 4px; }
.meta-stats { color: #6b7280; font-size: 13px; margin-top: 2px; }
.actions { display: flex; align-items: center; gap: 10px; }

.parse-banner { margin: 10px 0; padding: 10px 12px; border-radius: 8px; font-size: 14px; }
.parse-banner.ok   { background: #f0fdf4; color: #065f46; border: 1px solid #bbf7d0; }
.parse-banner.warn { background: #fff7ed; color: #9a3412; border: 1px solid #fed7aa; }

/* Layout */
.main-layout { display: grid; grid-template-columns: 300px 1fr; gap: 12px; align-items: start; }

/* Tree panel */
.tree-panel { padding: 10px; }
.tree-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.tree-title { font-weight: 700; color: #111827; }
.chk { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: #374151; }

.tree-scroll { max-height: 68vh; overflow: auto; }
.tree { list-style: none; padding: 0; margin: 0; }
.tree-row {
  width: 100%;
  text-align: left;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 8px;
  padding: 8px 10px;
  margin: 4px 0;
  cursor: pointer;
  display: flex;
  gap: 8px;
  align-items: center;
}
.tree-row:hover { background: #f5f5f5; }
.tree-row.active { border-color: #2f6fed; box-shadow: 0 0 0 2px rgba(47,111,237,.15) inset; }
.tree-row .label { color: #6b7280; font-size: 12px; min-width: 60px; }
.tree-row .value { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.counts { display: inline-flex; gap: 6px; }
.badge { padding: 1px 6px; border-radius: 999px; font-size: 11px; border: 1px solid #fecaca; background: #fef2f2; color: #991b1b; }

/* Compare panel */
.compare-panel { padding: 10px; position: relative; outline: none; }
.compare-panel.fullscreen {
  position: fixed;
  inset: 10px;
  z-index: 1200;
  max-width: none;
  width: auto;
  height: auto;
  background: #fff;
}
.compare-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.path { display: flex; gap: 6px; align-items: center; color: #374151; flex-wrap: wrap; }
.sep { color: #9ca3af; }
.compare-actions { display: flex; gap: 8px; align-items: center; }

.empty-note.big { text-align: center; padding: 24px; color: #6b7280; }

.split-view { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.col { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; background: #fff; }
.col-title { background: #f8fafc; padding: 8px 10px; border-bottom: 1px solid #e5e7eb; font-weight: 600; color: #111827; }
.val-table { width: 100%; border-collapse: collapse; }
.val-table th, .val-table td { border-bottom: 1px solid #e5e7eb; padding: 8px 10px; vertical-align: top; }
.field-name { font-weight: 600; color: #111827; }
.value-cell .value { white-space: pre-wrap; word-break: break-word; }
.value-cell .hint { color: #6b7280; font-weight: 400; font-size: 12px; margin-left: 6px; }
.resolve { margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; }
.radio { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.radio.muted { opacity: .7; }

.val-table tr.conflict td { background: #fff7f7; }
.val-table tr.add td      { background: #f6fffa; }
.val-table tr.same td     { background: #f8fafc; }

.resolved-pill {
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-weight: 600;
  font-size: 11px;
}

/* Sticky footer */
.global-commit {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(16,24,40,0.08);
}
.sel-path { display: flex; gap: 6px; align-items: center; color: #374151; flex-wrap: wrap; }
.sel-counts { color: #6b7280; }
.sel-counts .dot { margin: 0 8px; color: #9ca3af; }

/* Responsive */
@media (max-width: 980px) {
  .main-layout { grid-template-columns: 1fr; }
  .tree-panel { order: 1; }
  .compare-panel { order: 2; }
  .split-view { grid-template-columns: 1fr; }
}
</style>
