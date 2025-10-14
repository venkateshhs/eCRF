<template>
  <div class="tdiff-root">
    <div v-if="!diff.any" class="tdiff-empty"><em>No changes detected.</em></div>

    <section v-else class="tdiff-section">
      <!-- Study metadata -->
      <div v-if="diff.metadata.any" class="tdiff-block">
        <h4>Study</h4>
        <ul class="tdiff-list">
          <li v-for="c in diff.metadata.changes" :key="`md-${c.key}`">
            <em>Changed</em> <strong>{{ c.label }}</strong>:
            <span class="muted">{{ showAny(c.from) }}</span>
            <span class="arr">→</span>
            <span class="muted">{{ showAny(c.to) }}</span>
          </li>
        </ul>
      </div>

      <!-- Groups -->
      <div v-if="diff.groups.any" class="tdiff-block">
        <h4>Groups</h4>
        <ul class="tdiff-list">
          <li v-for="n in diff.groups.added" :key="`ga-${n}`"><em>Added</em> <strong>{{ n }}</strong></li>
          <li v-for="n in diff.groups.removed" :key="`gr-${n}`"><em>Removed</em> <strong>{{ n }}</strong></li>
          <li v-for="p in diff.groups.renamed" :key="`gren-${p.from}-${p.to}`">
            <em>Renamed</em> <strong>{{ p.from }}</strong> <span class="arr">→</span> <strong>{{ p.to }}</strong>
          </li>
          <li v-for="chg in diff.groups.changed" :key="`gchg-${chg.name}`">
            <em>Updated</em> <strong>{{ chg.name }}</strong>
            <ul class="tdiff-sublist">
              <li v-for="f in chg.fields" :key="`gchg-${chg.name}-${f.key}`">
                {{ f.label }}:
                <span class="muted">{{ showAny(f.from) }}</span>
                <span class="arr">→</span>
                <span class="muted">{{ showAny(f.to) }}</span>
              </li>
            </ul>
          </li>
        </ul>
      </div>

      <!-- Visits -->
      <div v-if="diff.visits.any" class="tdiff-block">
        <h4>Visits</h4>
        <ul class="tdiff-list">
          <li v-for="n in diff.visits.added" :key="`va-${n}`"><em>Added</em> <strong>{{ n }}</strong></li>
          <li v-for="n in diff.visits.removed" :key="`vr-${n}`"><em>Removed</em> <strong>{{ n }}</strong></li>
          <li v-for="p in diff.visits.renamed" :key="`vren-${p.from}-${p.to}`">
            <em>Renamed</em> <strong>{{ p.from }}</strong> <span class="arr">→</span> <strong>{{ p.to }}</strong>
          </li>
          <li v-for="chg in diff.visits.changed" :key="`vchg-${chg.name}`">
            <em>Updated</em> <strong>{{ chg.name }}</strong>
            <ul class="tdiff-sublist">
              <li v-for="f in chg.fields" :key="`vchg-${chg.name}-${f.key}`">
                {{ f.label }}:
                <span class="muted">{{ showAny(f.from) }}</span>
                <span class="arr">→</span>
                <span class="muted">{{ showAny(f.to) }}</span>
              </li>
            </ul>
          </li>
        </ul>
      </div>

      <!-- Models -->
      <div v-if="diff.models.meta.any" class="tdiff-block">
        <h4>Data Models</h4>
        <ul class="tdiff-list">
          <li v-for="n in diff.models.meta.added" :key="`ma-${n}`"><em>Added</em> <strong>{{ n }}</strong></li>
          <li v-for="n in diff.models.meta.removed" :key="`mr-${n}`"><em>Removed</em> <strong>{{ n }}</strong></li>
          <li v-for="p in diff.models.meta.renamed" :key="`mren-${p.from}-${p.to}`">
            <em>Renamed</em> <strong>{{ p.from }}</strong> <span class="arr">→</span> <strong>{{ p.to }}</strong>
          </li>
        </ul>
      </div>

      <!-- Model assignments -->
      <div v-if="diff.models.assign.any" class="tdiff-block">
        <h4>Model Assignments</h4>
        <p class="muted">
          Turned ON: <strong>{{ diff.models.assign.turnedOn }}</strong>,
          Turned OFF: <strong>{{ diff.models.assign.turnedOff }}</strong>
        </p>
        <details>
          <summary>Details</summary>
          <ul class="tdiff-list">
            <li v-for="t in diff.models.assign.toggles" :key="t.key">
              <strong>{{ t.section }}</strong> @ {{ t.visit }} / {{ t.group }} — <em>{{ t.to ? 'Enabled' : 'Disabled' }}</em>
            </li>
          </ul>
        </details>
      </div>
    </section>
  </div>
</template>

<script>
/* ------------------ shared utils ------------------ */
function deepClone(o) { return JSON.parse(JSON.stringify(o ?? null)); }
function asName(obj) {
  if (!obj) return "";
  if (typeof obj === "string") return obj.trim();
  if (typeof obj === "object") return String(obj.name || obj.title || "").trim();
  return String(obj).trim();
}
function normalizeNameList(arr) {
  const list = Array.isArray(arr) ? arr : [];
  return list.map(it => (typeof it === "string" ? { name: it } : it));
}

/* Treat undefined/null/empty/whitespace as the same “empty” */
function canon(v) {
  if (v == null) return "";
  if (typeof v === "string") return v.trim();
  return v;
}
function eq(a, b) {
  const ca = canon(a), cb = canon(b);
  return ca === cb;
}

/* Subjects can be "ID", ["ID","GROUP"], or { id, group } */
function normalizeSubjects(list) {
  const arr = Array.isArray(list) ? list : [];
  return arr
    .map(s => {
      if (typeof s === "string") {
        return { id: s.trim(), group: "" };
      } else if (Array.isArray(s)) {
        const id = (s[0] ?? "").toString().trim();
        const group = (s[1] ?? "").toString().trim();
        return { id, group };
      } else if (typeof s === "object" && s) {
        const id = (s.id ?? s[0] ?? "").toString().trim();
        const group = (s.group ?? s[1] ?? s.assignment ?? "").toString().trim();
        return { id, group };
      }
      return { id: "", group: "" };
    })
    .filter(s => s.id);
}

function normalizeModels(list) {
  const arr = Array.isArray(list) ? list : [];
  return arr.map(m => (typeof m === "string" ? { title: m } : m));
}

function normalizeSnapshot(snap) {
  const s = deepClone(snap || {});
  const st = (s.study && typeof s.study === "object") ? s.study : {};
  s.study = {
    ...st,
    title: canon(st.title ?? s.title),
    description: canon(st.description ?? s.description),
  };

  s.groups = normalizeNameList(s.groups);
  s.visits = normalizeNameList(s.visits);

  s.selectedModels = normalizeModels(s.selectedModels ?? s.models ?? []);
  s.assignments = Array.isArray(s.assignments) ? s.assignments : [];

  s.subjects = normalizeSubjects(s.subjects);

  return s;
}

/* ------------------ diff helpers ------------------ */
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
  const oldNames = (oldList || []).map(getName);
  const newNames = (newList || []).map(getName);

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
  const oldByName = mapBy(oldList || [], x => getName(x));
  const newByName = mapBy(newList || [], x => getName(x));
  newSet.forEach(nm => {
    if (oldSet.has(nm)) {
      const o = oldByName.get(nm)?.item || {};
      const n = newByName.get(nm)?.item || {};
      const local = [];
      const keys = new Set([...Object.keys(o || {}), ...Object.keys(n || {})]);
      keys.forEach(k => {
        if (k === "name" || k === "title") return;
        const ov = o?.[k], nv = n?.[k];
        const primO = (ov == null || typeof ov !== "object");
        const primN = (nv == null || typeof nv !== "object");
        if (primO && primN && !eq(ov, nv)) {
          const label = k.replace(/[_-]+/g, " ").replace(/\b\w/g, c => c.toUpperCase());
          local.push({ key: k, label, from: ov ?? "", to: nv ?? "" });
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

function diffMetadata(oldSnap, newSnap) {
  const o = oldSnap.study || {};
  const n = newSnap.study || {};
  const pairs = [];
  const add = (key, label, from, to) => { if (!eq(from, to)) pairs.push({ key, label, from: from ?? "", to: to ?? "" }); };

  add("title", "Title", o.title, n.title);
  add("description", "Description", o.description, n.description);

  const keys = new Set([...Object.keys(o || {}), ...Object.keys(n || {})]);
  keys.forEach(k => {
    if (k === "title" || k === "description" || k === "id") return;
    const ov = o?.[k], nv = n?.[k];
    const primO = (ov == null || typeof ov !== "object");
    const primN = (nv == null || typeof nv !== "object");
    if (primO && primN && !eq(ov, nv)) {
      const label = k.replace(/[_-]+/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      pairs.push({ key: k, label, from: ov ?? "", to: nv ?? "" });
    }
  });

  return { any: pairs.length > 0, changes: pairs };
}

function diffSubjects(oldSubs, newSubs) {
  const oldNorm = normalizeSubjects(oldSubs);
  const newNorm = normalizeSubjects(newSubs);

  const oldIds = new Set(oldNorm.map(s => s.id));
  const newIds = new Set(newNorm.map(s => s.id));

  const added = [...newIds].filter(id => !oldIds.has(id));
  const removed = [...oldIds].filter(id => !newIds.has(id));

  const oldById = new Map(oldNorm.map(s => [s.id, s]));
  const newById = new Map(newNorm.map(s => [s.id, s]));
  const reassigned = [];
  [...newIds].forEach(id => {
    if (oldIds.has(id)) {
      const og = oldById.get(id)?.group ?? "";
      const ng = newById.get(id)?.group ?? "";
      if (!eq(og, ng)) reassigned.push({ id, from: og, to: ng });
    }
  });

  return { any: !!(added.length || removed.length || reassigned.length), added, removed, reassigned };
}

function diffModelsMeta(oldModels, newModels) {
  return diffListByName(oldModels || [], newModels || [], m => asName(m));
}

function diffModelAssignments(oldModels, newModels, oldAssign, newAssign, visitsOld, visitsNew, groupsOld, groupsNew) {
  const oldIdx = mapBy(oldModels || [], m => asName(m));
  const newIdx = mapBy(newModels || [], m => asName(m));
  const vOld = (visitsOld || []).map(v => asName(v));
  const vNew = (visitsNew || []).map(v => asName(v));
  const gOld = (groupsOld || []).map(g => asName(g));
  const gNew = (groupsNew || []).map(g => asName(g));

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

function computeTemplateDiff(fromRaw, toRaw) {
  const from = normalizeSnapshot(fromRaw);
  const to   = normalizeSnapshot(toRaw);

  const metadata = diffMetadata(from, to);
  const groups   = diffListByName(from.groups, to.groups, g => asName(g));
  const visits   = diffListByName(from.visits, to.visits, v => asName(v));
  const subjects = diffSubjects(from.subjects, to.subjects);
  const modelsMeta = diffModelsMeta(from.selectedModels, to.selectedModels);
  const modelsAssign = diffModelAssignments(
    from.selectedModels, to.selectedModels,
    from.assignments, to.assignments,
    from.visits, to.visits, from.groups, to.groups
  );

  // ✅ Structural = add/remove/rename of groups/visits/models or any assignment toggle.
  //    Non-structural = metadata changes (incl. study) + groups/visits "changed" fields (e.g., descriptions) + subjects.
  const groupsStructural =
    (groups.added?.length || 0) > 0 ||
    (groups.removed?.length || 0) > 0 ||
    (groups.renamed?.length || 0) > 0;

  const visitsStructural =
    (visits.added?.length || 0) > 0 ||
    (visits.removed?.length || 0) > 0 ||
    (visits.renamed?.length || 0) > 0;

  const modelsMetaStructural =
    (modelsMeta.added?.length || 0) > 0 ||
    (modelsMeta.removed?.length || 0) > 0 ||
    (modelsMeta.renamed?.length || 0) > 0;

  const assignmentsStructural = !!modelsAssign.any;

  const anyStructural = groupsStructural || visitsStructural || modelsMetaStructural || assignmentsStructural;

  return {
    any: metadata.any || groups.any || visits.any || subjects.any || modelsMeta.any || modelsAssign.any,
    anyStructural,
    metadata, groups, visits, subjects,
    models: { meta: modelsMeta, assign: modelsAssign }
  };
}

/* ------------------ summary for StudyView cards ------------------ */
function buildVersionSummary(diff) {
  if (!diff || !diff.any) return "No changes.";

  const parts = [];
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;

  const addCounts = (label, d) => {
    if (!d) return;
    const segs = [];
    if (Array.isArray(d.added)   && d.added.length)   segs.push(`Added ${d.added.length}`);
    if (Array.isArray(d.removed) && d.removed.length) segs.push(`Removed ${d.removed.length}`);
    if (Array.isArray(d.renamed) && d.renamed.length) segs.push(`Renamed ${d.renamed.length}`);
    if (Array.isArray(d.changed) && d.changed.length) segs.push(`Updated ${d.changed.length}`);
    if (segs.length) parts.push(`${label}: ${segs.join(", ")}`);
  };

  if (diff.metadata?.any) {
    const n = diff.metadata.changes?.length || 0;
    parts.push(`Study: Updated ${plural(n, "field")}`);
  }
  addCounts("Groups", diff.groups);
  addCounts("Visits", diff.visits);

  const subs = diff.subjects || {};
  const subsSeg = [];
  if (Array.isArray(subs.added)      && subs.added.length)      subsSeg.push(`Added ${subs.added.length}`);
  if (Array.isArray(subs.removed)    && subs.removed.length)    subsSeg.push(`Removed ${subs.removed.length}`);
  if (Array.isArray(subs.reassigned) && subs.reassigned.length) subsSeg.push(`Moved ${subs.reassigned.length}`);
  if (subsSeg.length) parts.push(`Subjects: ${subsSeg.join(", ")}`);

  addCounts("Data Models", diff.models?.meta);

  if (diff.models?.assign?.any) {
    parts.push(`Assignments: Turned ON ${diff.models.assign.turnedOn}, Turned OFF ${diff.models.assign.turnedOff}`);
  }

  return parts.join(" | ");
}

export default {
  name: "TemplateDiffView",
  props: {
    from: { type: Object, required: true },
    to:   { type: Object, required: true },
    compact: { type: Boolean, default: false }
  },
  computed: {
    diff() { return computeTemplateDiff(this.from, this.to); }
  },
  methods: {
    showAny(v) {
      const c = canon(v);
      if (c === "") return "—";
      if (typeof c === "boolean") return c ? "Yes" : "No";
      if (Array.isArray(c)) return c.length ? JSON.stringify(c) : "—";
      if (typeof c === "object") return Object.keys(c).length ? JSON.stringify(c) : "—";
      return String(c);
    }
  }
};

export {
  deepClone,
  computeTemplateDiff,
  normalizeSnapshot,
  buildVersionSummary
};
</script>

<style scoped>
.tdiff-root { min-width: 680px; }
.tdiff-empty { color: #6b7280; }
.tdiff-section { display: grid; gap: 12px; }
.tdiff-block { border-top: 1px dashed #e5e7eb; padding-top: 10px; }
.tdiff-block h4 { margin: 0 0 6px; font-weight: 700; color: #0f172a; }
.tdiff-list, .tdiff-sublist { list-style: none; padding-left: 0; margin: 0; }
.tdiff-list li { margin: 6px 0; }
.tdiff-sublist { margin-top: 6px; padding-left: 16px; }
.muted { color: #6b7280; }
.arr { margin: 0 6px; }
</style>
