<template>
  <div class="shacl-components">
    <h2>SHACL Classes</h2>
    <p v-if="loading">Loading SHACL components...</p>
    <p v-else-if="error">Error loading SHACL components: {{ error }}</p>

    <ul v-else>
      <li
        v-for="(iri, index) in filteredShapeIRIs"
        :key="index"
        @click="openDialog(iri)"
        class="shape-item"
      >
        {{ getClassName(iri) }}
      </li>
    </ul>

    <!-- Selection dialog with nested attributes support -->
    <div
      v-for="(dialog, dIndex) in dialogStack"
      :key="dIndex"
      class="dialog-overlay"
      :style="{ zIndex: 1000 + dIndex }"
      @click.self="dIndex === dialogStack.length - 1 && cancelDialog()"
    >
      <div class="dialog" @click.stop>
        <h3>Select Properties for {{ getClassName(dialog.iri) }}</h3>

        <div class="scrollable-content">
          <p class="template-instruction">Click to pick properties (expand references to select nested)</p>

          <div
            v-for="(group, gIndex) in dialog.groups"
            :key="gIndex"
            class="group-container"
          >
            <h4 class="group-header">{{ formatGroupName(group.name) }}</h4>

            <div
              v-for="(prop, pIndex) in group.properties"
              :key="pIndex"
              class="prop-row"
            >
              <div class="prop-info">
                <div class="prop-top">
                  <strong>{{ prop.name }}</strong>
                  <span v-if="prop.isReference" class="ref-chip">Reference</span>
                </div>
                <p v-if="prop.helpText" class="prop-desc">{{ prop.helpText }}</p>
                <small class="prop-meta">
                  <span v-if="prop.datatype && !prop.isReference">Type: {{ prop.datatype }}</span>
                  <span v-if="prop.isReference && prop.refTarget"> · Ref: {{ getClassName(prop.refTarget) }}</span>
                  <span v-if="prop.options && prop.options.length"> · Options: {{ prop.options.join(', ') }}</span>
                  <span v-if="prop.required"> · required</span>
                </small>

                <div
                  v-if="prop.isReference && prop.nested && prop.nested.length"
                  class="nested-block"
                >
                  <button class="toggle-nested" @click="prop.expanded = !prop.expanded">
                    <span v-if="prop.expanded">▾</span><span v-else>▸</span>
                    Expand {{ getClassName(prop.refTarget) }} properties
                  </button>

                  <div v-if="prop.expanded" class="nested-groups">
                    <div
                      v-for="(ng, ngIdx) in prop.nested"
                      :key="ngIdx"
                      class="nested-group"
                    >
                      <div class="nested-group-title">{{ formatGroupName(ng.name) }}</div>
                      <div
                        v-for="(np, npIdx) in ng.properties"
                        :key="npIdx"
                        class="nested-prop-row"
                      >
                        <div class="nested-prop-info">
                          <strong>{{ np.name }}</strong>
                          <small class="prop-meta">
                            <span v-if="np.datatype && !np.isReference">Type: {{ np.datatype }}</span>
                            <span v-if="np.options && np.options.length"> · Options: {{ np.options.join(', ') }}</span>
                            <span v-if="np.required"> · required</span>
                          </small>
                          <p v-if="np.helpText" class="prop-desc">{{ np.helpText }}</p>
                        </div>
                        <label class="prop-check">
                          <input type="checkbox" v-model="np.selected" />
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <label class="prop-check">
                <input
                  type="checkbox"
                  v-model="prop.selected"
                  :disabled="prop.isReference && prop.nested && prop.nested.length"
                  :title="prop.isReference && prop.nested && prop.nested.length ? 'Select individual nested fields below' : ''"
                />
              </label>
            </div>
          </div>
        </div>

        <div class="dialog-buttons">
          <button
            class="btn btn-primary"
            :disabled="!hasAnySelection(dialog)"
            @click="onTakeover(dialog)"
          >
            Takeover
          </button>
          <button class="btn" @click="cancelDialog">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from "vue";
import { ShapesDataset } from 'shacl-tulip';

export default {
  name: "ShaclComponents",
  emits: ["takeover"],
  setup(_, { emit }) {
    const loading = ref(true);
    const error = ref(null);
    const dialogStack = ref([]);

    const nodeShapes = ref(null);
    const nodeShapeIRIs = ref(null);


    const NEST_DEPTH = 2;

    const isMap = (v) => v && typeof v === "object" && typeof v.get === "function";
    const isSet = (v) => v && typeof v === "object" && typeof v.has === "function" && typeof v.add === "function";
    const seen = new WeakSet();

    function asArray(maybe) {
      if (!maybe) return [];
      if (Array.isArray(maybe)) return maybe;
      if (isSet(maybe)) return Array.from(maybe);
      return [];
    }

    function isLikelyIRI(s) {
      return typeof s === "string" && /^(https?:|urn:|[_a-zA-Z].*#|[_a-zA-Z].*\/)/.test(s);
    }

    function deepPick(obj, names = [], depth = 3) {
      if (!obj || typeof obj !== "object" || depth < 0 || seen.has(obj)) return null;
      seen.add(obj);
      for (const k of Object.keys(obj)) if (names.includes(k) && obj[k]) return obj[k];
      for (const k of Object.keys(obj)) {
        const v = obj[k];
        if (v && typeof v === "object") {
          const found = deepPick(v, names, depth - 1);
          if (found) return found;
        }
      }
      return null;
    }

    function termToString(t) {
      if (t == null) return "";
      if (typeof t === "string") return t;
      if (typeof t === "object") {
        if (t.value) return String(t.value);
        if (t["@id"]) return String(t["@id"]);
        if (t.id) return String(t.id);
      }
      return String(t);
    }

    function lastSegment(uriOrTerm) {
      const s = termToString(uriOrTerm);
      const seg = s.split(/[#/]/).pop();
      if (seg && seg.includes("22-rdf-syntax-ns#")) {
        const parts = seg.split("22-rdf-syntax-ns#");
        return parts[1] || seg;
      }
      return seg || s;
    }

    function getClassName(uri) {
      const name = lastSegment(uri);
      return name;
    }

    function getOrder(prop) {
      const raw = prop["http://www.w3.org/ns/shacl#order"];
      const s = termToString(raw).trim();
      if (!s) return Infinity;
      const n = parseInt(s, 10);
      return Number.isFinite(n) ? n : Infinity;
    }

    function formatGroupName(groupValue) {
      const s = termToString(groupValue);
      return s === "Ungrouped" || !s ? "Default Properties" : lastSegment(s);
    }

    function getShapeRecord(iri) {
      const shapes = nodeShapes.value;
      if (!shapes) return null;
      return isMap(shapes) ? shapes.get(iri) : shapes[iri] || null;
    }

    function getShapeProperties(shapeRecord) {
      if (!shapeRecord) return [];
      const props = shapeRecord.propertyShapes || shapeRecord.properties || [];
      return Array.isArray(props) ? props : props ? Array.from(props) : [];
    }

    const dataTypeToScratchType = {
      "http://www.w3.org/2001/XMLSchema#string": "text",
      "http://www.w3.org/2001/XMLSchema#integer": "number",
      "http://www.w3.org/2001/XMLSchema#boolean": "checkbox",
      "http://www.w3.org/2001/XMLSchema#date": "date",
      "http://www.w3.org/2001/XMLSchema#anyURI": "text",
      "http://www.w3.org/2001/XMLSchema#dateTime": "date",
      "https://www.w3.org/TR/NOTE-datetime": "date"
    };

    function logDataset(ds, note = "") {
      try {
        console.groupCollapsed(`%c[SHACL] Dataset snapshot ${note}`, "color:#6b7280");
        console.log("All top-level keys:", Object.keys(ds || {}));
        console.log("ds.data keys:", ds?.data ? Object.keys(ds.data) : "no .data");
        const dataNS = ds?.data;

        const ns = dataNS?.nodeShapes ?? deepPick(ds, ["nodeShapes"]);
        const iris = dataNS?.nodeShapeIRIs ?? deepPick(ds, ["nodeShapeIRIs"]);
        const groups = dataNS?.propertyGroups ?? deepPick(ds, ["propertyGroups"]);

        console.log("nodeShapes (resolved):", ns);
        console.log("nodeShapeIRIs (resolved):", iris);
        console.log("propertyGroups (resolved):", groups);

        if (isMap(ns)) console.log("nodeShapes size (Map):", ns.size);
        else console.log("nodeShapes keys (Object):", ns ? Object.keys(ns) : []);

        if (isSet(iris)) console.log("nodeShapeIRIs size (Set):", iris.size);
        else console.log("nodeShapeIRIs length (Array):", Array.isArray(iris) ? iris.length : 0);

        console.groupEnd();
      } catch (e) {
        console.warn("[SHACL] logDataset failed:", e);
      }
    }

    const filteredShapeIRIs = computed(() => {
  const iris = asArray(nodeShapeIRIs.value);
  if (!iris.length) {
    console.warn("[SHACL] No nodeShapeIRIs available, returning empty array.");
    return [];
  }

  // If you want to keep the old behavior, toggle this to false.
  const requireIdPath = true;

  if (!requireIdPath) return iris;

  const filtered = iris.filter((iri) => {
    const shape = getShapeRecord(iri);
    const props = getShapeProperties(shape);
    if (!props.length) return false;
    return props.some((prop) => {
      const path = termToString(prop["http://www.w3.org/ns/shacl#path"]).toLowerCase();
      return path.endsWith("/id") || path.endsWith("#id") || path === "id";
    });
  });


  if (!filtered.length) {
    console.warn("[SHACL] ID-path filter removed all classes; falling back to show all node shapes.");
    return iris;
  }
  return filtered;
});


    onMounted(async () => {
      const fileUrl = "/dlschemas_shacl.ttl";

      try { await fetch(fileUrl, { method: "HEAD" }); }
      catch (e) { console.debug("[SHACL] HEAD probe failed (non-fatal):", e); }

      const shapesDS = new ShapesDataset();

      shapesDS.addEventListener("graphLoaded", () => {
        const dataNS = shapesDS.data;
        let ns = dataNS?.nodeShapes;
        let iris = dataNS?.nodeShapeIRIs;

        if (!ns || !iris) {
          ns = ns || deepPick(shapesDS, ["nodeShapes"]);
          iris = iris || deepPick(shapesDS, ["nodeShapeIRIs"]);
        }

        if (!iris) {
          const namesArr = dataNS?.nodeShapeNamesArray || deepPick(shapesDS, ["nodeShapeNamesArray"]);
          if (Array.isArray(namesArr) && namesArr.some(isLikelyIRI)) {
            iris = namesArr;
          }
        }

        nodeShapes.value = ns || null;
        nodeShapeIRIs.value = iris || null;

        logDataset(shapesDS, "after graphLoaded");
        loading.value = false;
      });

      try {
        await shapesDS.loadRDF(fileUrl);
        setTimeout(() => {
          if (loading.value) {
            const dataNS = shapesDS.data;
            let ns = dataNS?.nodeShapes || deepPick(shapesDS, ["nodeShapes"]);
            let iris = dataNS?.nodeShapeIRIs || deepPick(shapesDS, ["nodeShapeIRIs"]);

            if (!iris) {
              const namesArr = dataNS?.nodeShapeNamesArray || deepPick(shapesDS, ["nodeShapeNamesArray"]);
              if (Array.isArray(namesArr) && namesArr.some(isLikelyIRI)) {
                iris = namesArr;
              }
            }

            nodeShapes.value = ns || null;
            nodeShapeIRIs.value = iris || null;

            logDataset(shapesDS, "timeout snapshot");
            loading.value = false;
          }
        }, 2500);
      } catch (e) {
        error.value = e?.message || String(e);
        loading.value = false;
      }
    });

    function buildShapeView(iri, depth = NEST_DEPTH) {
      const record = getShapeRecord(iri);
      if (!record) return [];
      const props = getShapeProperties(record);

      const groupsObj = {};
      props.forEach((prop) => {
        const groupVal = prop["http://www.w3.org/ns/shacl#group"];
        const groupKey = termToString(groupVal) || "Ungrouped";
        (groupsObj[groupKey] ||= []).push(prop);
      });

      const groupKeys = Object.keys(groupsObj).sort((a, b) => {
        if (a === "Ungrouped" && b !== "Ungrouped") return 1;
        if (b === "Ungrouped" && a !== "Ungrouped") return -1;
        return a.localeCompare(b);
      });

      const groupsArray = groupKeys.map((key) => {
        const rows = groupsObj[key]
          .slice()
          .sort((a, b) => getOrder(a) - getOrder(b))
          .map((prop) => enrichProp(prop, depth));
        return { name: key, properties: rows };
      });

      return groupsArray;
    }

    function enrichProp(prop, depth) {
      const nameValue = prop["http://www.w3.org/ns/shacl#name"];
      const pathValue = prop["http://www.w3.org/ns/shacl#path"];
      const fieldName = (termToString(nameValue) || lastSegment(pathValue) || "Unnamed");

      const dtURI = termToString(prop["http://www.w3.org/ns/shacl#datatype"]);
      const inList = prop["http://www.w3.org/ns/shacl#in"];
      const options = Array.isArray(inList) ? inList.map(termToString) : [];

      const minCount = termToString(prop["http://www.w3.org/ns/shacl#minCount"]);
      const required = !!(minCount && parseInt(minCount, 10) > 0);
      const defVal = prop["http://www.w3.org/ns/shacl#defaultValue"];
      const description = termToString(prop["http://www.w3.org/ns/shacl#description"]);
      const pattern = termToString(prop["http://www.w3.org/ns/shacl#pattern"]);

      const classRef = prop["http://www.w3.org/ns/shacl#class"];
      const nodeRef  = prop["http://www.w3.org/ns/shacl#node"];
      let refTarget = termToString(classRef) || termToString(nodeRef) || "";
      if (refTarget && !isLikelyIRI(refTarget)) refTarget = "";

      const isReference = !!refTarget;

      const row = {
        name: fieldName,
        datatype: isReference ? undefined : (dataTypeToScratchType[dtURI] || "text"),
        isReference,
        refTarget: refTarget || undefined,
        options,
        required,
        defaultValue: termToString(defVal) || undefined,
        helpText: description || "",
        pattern: pattern || undefined,
        path: termToString(pathValue) || "",
        selected: false,
        expanded: false
      };

      if (isReference && depth > 0) {
        const nestedGroups = buildShapeView(refTarget, depth - 1);
        row.nested = nestedGroups;
      } else {
        row.nested = [];
      }

      return row;
    }

    function openDialog(iri) {
      const groupsArray = buildShapeView(iri, NEST_DEPTH);
      const dialogData = { iri, groups: groupsArray };
      dialogStack.value.push(dialogData);
    }

    function hasAnySelection(dialog) {
      return dialog.groups.some((g) =>
        g.properties.some((p) => p.selected || (p.nested && p.nested.some(ng => ng.properties.some(np => np.selected))))
      );
    }

    // KEEP ONE: only constraints.helpText; placeholder stays empty (except date)
    function toScratchField(prop, parentTrail = []) {
      let type = prop.datatype || "text";
      if (prop.options && prop.options.length) type = "select";

      const trail = [...parentTrail, prop.name].filter(Boolean);
      const label = trail.join(" · ");
      const uniqueName = `${trail.map(s => s.replace(/[^a-zA-Z0-9_]/g, "_")).join("_")}_${Date.now()}`;

      const constraints = { required: !!prop.required };
      if (prop.pattern) constraints.pattern = prop.pattern;
      if (prop.helpText) constraints.helpText = prop.helpText; // keep hint here ONLY

      const field = {
        name: uniqueName,
        label,
        type,
        options: type === "select" ? [...(prop.options || [])] : [],
        placeholder: "", // no duplication with helpText
        value: type === "checkbox" ? false : "",
        constraints
      };

      if (prop.defaultValue !== undefined && prop.defaultValue !== "") {
        if (type === "number") {
          const n = Number(prop.defaultValue);
          if (Number.isFinite(n)) field.value = n;
        } else if (type === "select") {
          field.value = field.options.includes(prop.defaultValue) ? prop.defaultValue : "";
        } else if (type === "checkbox") {
          const s = String(prop.defaultValue).toLowerCase();
          field.value = s === "true" || s === "1";
        } else {
          field.value = String(prop.defaultValue);
        }
      }

      if (type === "date") {
        field.constraints.dateFormat = "dd.MM.yyyy";
        field.placeholder = "dd.MM.yyyy"; // format aid only
      }

      return field;
    }

    function collectSelected(dialog) {
      const fields = [];
      dialog.groups.forEach((g) => {
        g.properties.forEach((p) => {
          if (p.nested && p.nested.length) {
            p.nested.forEach((ng) => {
              ng.properties.forEach((np) => {
                if (np.selected) fields.push(toScratchField(np, [p.name]));
              });
            });
          } else if (p.selected) {
            fields.push(toScratchField(p, []));
          }
        });
      });
      return fields;
    }

    function onTakeover(dialog) {
      const fields = collectSelected(dialog);
      if (!fields.length) return;
      const section = { title: getClassName(dialog.iri), fields };
      emit("takeover", section);
      dialogStack.value.pop();
    }

    function cancelDialog() {
      dialogStack.value.pop();
    }

    return {
      loading, error, dialogStack,
      filteredShapeIRIs,
      getClassName, formatGroupName,
      openDialog, onTakeover, hasAnySelection, cancelDialog
    };
  },
};
</script>

<style scoped>
.shacl-components {
  background: white;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-top: 10px;
}
.shape-item { cursor: pointer; color: #555; text-decoration: underline; margin: 5px 0; }
.shape-item:hover { color: #333; }

.template-instruction { font-style: italic; margin-bottom: 10px; }

.dialog-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; }
.dialog { background: white; padding: 20px; border-radius: 8px; max-width: 800px; width: 92%; max-height: 84vh; overflow-y: auto; }
.scrollable-content { max-height: 64vh; overflow-y: auto; padding: 10px; border-top: 1px solid #ddd; }

.group-container { margin-bottom: 16px; }
.group-header { margin-bottom: 8px; font-size: 1.05em; font-weight: 600; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; color: #111827; }

.prop-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; padding: 10px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 8px; }
.prop-info { flex: 1; min-width: 0; }
.prop-top { display: flex; align-items: center; gap: 8px; }
.ref-chip { font-size: 12px; background: #eef2ff; color: #3730a3; padding: 2px 6px; border-radius: 999px; }
.prop-desc { color: #6b7280; margin: 4px 0 0; }
.prop-meta { color: #6b7280; display: inline-block; margin-top: 4px; }
.prop-check input { width: 18px; height: 18px; }

.nested-block { margin-top: 8px; }
.toggle-nested { border: none; background: transparent; color: #2563eb; cursor: pointer; padding: 4px 0; }
.nested-groups { margin-top: 6px; border-left: 3px solid #e5e7eb; padding-left: 10px; }

.nested-group { margin-bottom: 8px; }
.nested-group-title { font-weight: 600; font-size: 0.95em; margin-bottom: 6px; color: #374151; }
.nested-prop-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 8px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 6px; }
.nested-prop-info { flex: 1; min-width: 0; }

.dialog-buttons { margin-top: 12px; display: flex; justify-content: flex-end; gap: 10px; }
.btn { padding: 8px 12px; border: 1px solid #ccc; background-color: #f5f5f5; cursor: pointer; border-radius: 6px; font-size: 0.95em; color: #333; }
.btn:hover { background-color: #e0e0e0; }
.btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.btn-primary[disabled] { opacity: .5; cursor: not-allowed; }
</style>
