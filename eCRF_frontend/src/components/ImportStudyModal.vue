<template>
  <div class="import-overlay" @click.self="onClose">
    <div class="import-dialog">
      <header class="dialog-header">
        <h3>Import Study</h3>
        <button class="icon-close" @click="onClose">×</button>
      </header>

      <section class="dialog-body">
        <div class="controls">
          <label class="row">
            <span>Format</span>
            <select v-model="kind">
              <option value="csv">CSV</option>
              <option value="excel">Excel (.xlsx)</option>
              <option value="bids">BIDS</option>
            </select>
          </label>

          <label class="row" v-if="kind !== 'bids'">
            <span>File</span>
            <input type="file" @change="onFileChange" :accept="accepts" />
          </label>

          <div v-if="kind === 'csv'" class="row-inline">
            <label class="row">
              <span>Delimiter</span>
              <input type="text" v-model="delimiter" maxlength="3" placeholder="," />
            </label>
            <label class="row chk">
              <input type="checkbox" v-model="hasHeader" />
              <span>Has header</span>
            </label>
          </div>

          <div class="actions">
            <button class="btn" :disabled="!file && kind!=='bids'" @click="preview">Preview</button>
          </div>
        </div>

        <div v-if="loading" class="loading">Loading preview…</div>

        <div v-if="error" class="error">{{ error }}</div>

        <div v-if="previewData" class="preview">
          <h4>Auto-mapping</h4>
          <div class="mapping-grid">
            <div class="map-row" v-for="key in ['subject','visit','group','assignment']" :key="key">
              <label class="map-label">{{ key }}</label>
              <select class="map-select" v-model="mapping[key]">
                <option :value="null">— None —</option>
                <option v-for="c in previewData.preview.columns" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
          </div>

          <h4>Other columns → study_data JSON</h4>
          <div class="chips">
            <span v-for="c in otherColumnsComputed" :key="c" class="chip">{{ c }}</span>
            <span v-if="!otherColumnsComputed.length" class="chip chip-empty">None</span>
          </div>

          <h4>Sample rows (first {{ previewData.preview.rows.length }})</h4>
          <div class="table-wrap">
            <table class="mini-table">
              <thead>
                <tr>
                  <th v-for="c in previewData.preview.columns" :key="c">{{ c }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in previewData.preview.rows" :key="i">
                  <td v-for="c in previewData.preview.columns" :key="c">{{ r[c] }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="actions sticky">
            <button class="btn btn-primary" @click="saveMock">Save (no-op)</button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "ImportStudyModal",
  props: {
    studyId: { type: [Number, String], default: null },
  },
  data() {
    return {
      kind: "csv",
      file: null,
      delimiter: ",",
      hasHeader: true,
      loading: false,
      error: "",
      previewData: null,
      mapping: {
        subject: null,
        visit: null,
        group: null,
        assignment: null,
      },
    };
  },
  computed: {
    accepts() {
      if (this.kind === "csv") return ".csv,text/csv";
      if (this.kind === "excel") return ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      return "";
    },
    otherColumnsComputed() {
      if (!this.previewData) return [];
      const cols = this.previewData.preview.columns || [];
      const used = new Set(Object.values(this.mapping).filter(Boolean));
      return cols.filter((c) => !used.has(c));
    },
  },
  methods: {
    onClose() {
      console.log("[ImportModal] close");
      this.$emit("close");
    },
    onFileChange(e) {
      const f = e.target.files?.[0] || null;
      this.file = f;
      console.log("[ImportModal] selected file:", f?.name);
    },
    async preview() {
      this.error = "";
      this.previewData = null;
      if (this.kind !== "bids" && !this.file) {
        this.error = "Please choose a file.";
        return;
      }
      this.loading = true;
      try {
        const token = this.$store.state.token;
        const fd = new FormData();
        // if not provided, server defaults to -1
        if (this.studyId !== null && this.studyId !== undefined) {
          fd.append("study_id", String(this.studyId));
        }
        fd.append("kind", this.kind);
        if (this.file) fd.append("file", this.file);
        if (this.kind === "csv") {
          fd.append("delimiter", this.delimiter || ",");
          fd.append("has_header", String(this.hasHeader));
        }

        console.log("[ImportModal] POST /import/preview", {
          kind: this.kind,
          study_id: this.studyId ?? "(default -1)",
          file: this.file?.name,
          delimiter: this.delimiter,
          hasHeader: this.hasHeader,
        });

        const { data } = await axios.post("http://127.0.0.1:8000/import/preview", fd, {
          headers: { Authorization: `Bearer ${token}` },
        });
        console.log("[ImportModal] preview response:", data);
        this.previewData = data;

        // adopt server mapping if present
        if (data.mapping) {
          this.mapping = {
            subject: data.mapping.subject ?? null,
            visit: data.mapping.visit ?? null,
            group: data.mapping.group ?? null,
            assignment: data.mapping.assignment ?? null,
          };
        }
      } catch (e) {
        console.error("[ImportModal] preview error:", e?.response?.data || e.message);
        this.error = e?.response?.data?.detail || "Failed to generate preview.";
      } finally {
        this.loading = false;
      }
      // reveal sticky action bar on scroll
      this.$nextTick(() => {
        const el = document.querySelector(".dialog-body");
        if (el) el.scrollTop = 0;
      });
    },
    saveMock() {
      // For now, just log the decisions
      console.log("[ImportModal] SAVE (no-op) with mapping:", this.mapping, "other columns:", this.otherColumnsComputed);
      alert("Saved (no-op). Mapping and other columns logged to console.");
    },
  },
};
</script>

<style scoped>
/* Overlay */
.import-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: grid;
  place-items: center;
  z-index: 2000;
}

/* Dialog */
.import-dialog {
  width: min(100vw - 32px, 820px);
  max-height: min(90vh, 720px);
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}

/* Header */
.dialog-header {
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.icon-close {
  background: none; border: none; font-size: 22px; cursor: pointer;
}

/* Body (scrollable) */
.dialog-body {
  padding: 14px 16px 0;
  overflow: auto;
}

/* Controls */
.controls { display: grid; gap: 12px; margin-bottom: 8px; }
.row { display: grid; grid-template-columns: 130px 1fr; align-items: center; gap: 10px; }
.row-inline { display: flex; gap: 16px; align-items: center; }
.row.chk { grid-template-columns: auto 1fr; gap: 8px; }

.actions { display: flex; gap: 8px; justify-content: flex-start; }
.btn {
  padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; cursor: pointer; background: #fafafa;
}
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }

/* Preview */
.preview { display: grid; gap: 12px; padding-bottom: 60px; }

.mapping-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: 140px 1fr;
  align-items: center;
}
.map-row { display: contents; }
.map-label { font-weight: 600; color: #333; }
.map-select { padding: 6px 8px; }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { background: #eef2ff; color: #3730a3; padding: 4px 8px; border-radius: 999px; font-size: 12px; }
.chip-empty { background: #f3f4f6; color: #6b7280; }

.table-wrap { overflow: auto; border: 1px solid #eee; border-radius: 8px; }
.mini-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.mini-table th, .mini-table td { border-bottom: 1px solid #f0f0f0; padding: 6px 8px; white-space: nowrap; }
.mini-table thead th { position: sticky; top: 0; background: #fafafa; z-index: 1; }

/* Sticky footer actions inside scroll area */
.actions.sticky {
  position: sticky; bottom: 0; background: linear-gradient(to top, #fff, #ffffffcc);
  padding: 10px 0; border-top: 1px solid #eee; margin-top: 8px;
}

/* Status */
.loading { padding: 8px; color: #555; }
.error { padding: 8px; color: #b91c1c; background: #fee2e2; border: 1px solid #fecaca; border-radius: 6px; }
</style>
