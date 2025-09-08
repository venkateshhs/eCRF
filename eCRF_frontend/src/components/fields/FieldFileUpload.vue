<template>
  <div class="field-file-upload" :class="{ readonly, invalid: !!error }">
    <!-- LOCAL UPLOAD MODE -->
    <div v-if="storagePreference==='local'" class="uploader">
      <input
        ref="fileInput"
        type="file"
        :accept="acceptAttr"
        class="hidden-file-input"
        :disabled="readonly"
        :multiple="isMultiple"
        @change="onFilePicked"
      />
      <button
        class="attach-btn"
        type="button"
        :disabled="readonly"
        @click="triggerPick"
        title="Choose file(s)"
      >
        <i :class="icons.paperclip" />
        {{ attachLabel }}
      </button>

      <!-- SINGLE FILE META -->
      <div v-if="!isMultiple && singleLocal" class="meta">
        <div class="file-row">
          <span class="name" :title="singleLocal.name">{{ singleLocal.name }}</span>
          <span class="meta-dot">•</span>
          <span class="size">{{ humanSize(singleLocal.size) }}</span>
          <span class="meta-dot" v-if="singleLocal.type">•</span>
          <span class="mime" v-if="singleLocal.type">{{ singleLocal.type }}</span>
          <button class="icon-inline danger" type="button" @click="clearValue" title="Remove">
            <i :class="icons.trash" />
          </button>
        </div>
        <small class="note" v-if="isBuilderStage">
          Files are <b>not persisted</b> during study creation. This control captures metadata only.
        </small>
      </div>

      <!-- MULTIPLE FILES META -->
      <div v-else-if="isMultiple && localItems.length" class="meta">
        <div
          class="file-row"
          v-for="(it, i) in localItems"
          :key="`${it.name}-${it.size}-${it.lastModified}-${i}`"
        >
          <span class="name" :title="it.name">{{ it.name }}</span>
          <span class="meta-dot">•</span>
          <span class="size">{{ humanSize(it.size) }}</span>
          <span class="meta-dot" v-if="it.type">•</span>
          <span class="mime" v-if="it.type">{{ it.type }}</span>
          <button class="icon-inline danger" type="button" @click="removeLocalAt(i)" title="Remove">
            <i :class="icons.trash" />
          </button>
        </div>
        <small class="note" v-if="isBuilderStage">
          Files are <b>not persisted</b> during study creation. This control captures metadata only.
        </small>
      </div>
    </div>

    <!-- URL MODE -->
    <div v-else-if="storagePreference==='url'" class="url-box">
      <!-- MULTIPLE URLS -->
      <div v-if="isMultiple">
        <div class="url-add-row">
          <input
            type="url"
            :placeholder="urlPlaceholder"
            v-model="localUrl"
            :readonly="readonly"
            @keydown.enter.prevent="addUrl"
          />
          <button class="btn-option add-url-btn" type="button" :disabled="readonly" @click="addUrl">
            Add
          </button>
        </div>
        <div v-if="urlItems.length" class="meta">
          <div class="file-row" v-for="(it, i) in urlItems" :key="`${it.url}-${i}`">
            <span class="name" :title="it.url">{{ truncate(it.url, 60) }}</span>
            <button class="icon-inline danger" type="button" @click="removeUrlAt(i)" title="Remove">
              <i :class="icons.trash" />
            </button>
          </div>
        </div>
        <small class="note">
          Use stable, accessible URLs (institutional storage, or DOI).
        </small>
      </div>

      <!-- SINGLE URL -->
      <div v-else class="url-row">
        <input
          type="url"
          :placeholder="urlPlaceholder"
          :value="displayedUrl"
          @input="onUrlInput"
          @blur="onUrlBlur"
          :readonly="readonly"
        />
        <small class="note">
          Use a stable, accessible URL (institutional storage, or DOI).
        </small>
      </div>
    </div>

    <!-- Help only (constraints removed to avoid duplication with “?” dialog) -->
    <div class="rules">
      <small v-if="helpText" class="help">{{ helpText }}</small>
    </div>

    <!-- Error -->
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script>
/* eslint-disable */
import icons from "@/assets/styles/icons";

const KB = 1024;
const MB = 1024 * KB;
const DEFAULT_ALLOWED = [];       // ← no default restriction
const DEFAULT_MAX_MB = null;      // ← no default size limit

export default {
  name: "FieldFileUpload",
  props: {
    // value can be: null | metaObject | metaObject[]   (when allowMultipleFiles)
    value: { type: [Object, Array, null], default: null },
    constraints: { type: Object, default: () => ({}) },
    readonly: { type: Boolean, default: false },
    required: { type: Boolean, default: false },
    stage: { type: String, default: "builder" } // 'builder' | 'runtime'
  },
  data() {
    return {
      icons,
      localUrl: "",
      error: ""
    };
  },
  computed: {
    isBuilderStage() { return (this.stage || "builder") === "builder"; },
    helpText() { return this.constraints?.helpText || ""; },

    storagePreference() {
      const v = (this.constraints?.storagePreference || "local").toLowerCase();
      return (v === "url") ? "url" : "local";
    },

    // Default to allowing multiple when not explicitly disabled
    isMultiple() {
      const flag = this.constraints?.allowMultipleFiles;
      return flag === undefined ? true : !!flag;
    },

    maxSizeMB() {
      const n = Number(this.constraints?.maxSizeMB);
      return Number.isFinite(n) && n > 0 ? n : null;
    },
    effectiveMaxSizeMB() { return this.maxSizeMB ?? DEFAULT_MAX_MB; },

    allowedFormats() {
      const arr = Array.isArray(this.constraints?.allowedFormats)
        ? this.constraints.allowedFormats
        : [];
      return arr.map(String).map(s => s.trim()).filter(Boolean);
    },
    effectiveAllowedFormats() {
      return this.allowedFormats.length ? this.allowedFormats : DEFAULT_ALLOWED;
    },
    acceptAttr() { return this.effectiveAllowedFormats.join(","); },

    // Button label
    attachLabel() {
      if (this.storagePreference === 'local') {
        if (this.isMultiple) return "Attach files";
        return this.value ? "Change file" : "Attach file";
      }
      return this.isMultiple ? "Add links" : "Add link";
    },

    // Local (single)
    singleLocal() {
      const v = this.value;
      return (v && !Array.isArray(v) && v.source === "local") ? v : null;
    },

    // Local (multiple)
    localItems() {
      if (!this.isMultiple) return [];
      const v = this.value;
      const arr = Array.isArray(v) ? v : [];
      return arr.filter(it => it && it.source === "local");
    },

    // URL (multiple)
    urlItems() {
      if (this.storagePreference !== 'url') return [];
      if (!this.isMultiple) return [];
      const v = this.value;
      const arr = Array.isArray(v) ? v : [];
      return arr.filter(it => it && it.source === "url");
    },

    urlPlaceholder() { return "https://example.org/path/to/large/file"; },
    displayedUrl() {
      if (this.value && !Array.isArray(this.value) && this.value.source === "url") return this.value.url || "";
      return this.localUrl;
    }
  },
  mounted() {
    if (this.value && !Array.isArray(this.value) && this.value.source === "url") {
      this.localUrl = this.value.url || "";
    }
  },
  methods: {
    triggerPick() {
      if (this.readonly) return;
      this.$refs.fileInput && this.$refs.fileInput.click();
    },

    onFilePicked(e) {
      this.error = "";
      const fileList = Array.from(e?.target?.files || []);
      if (!fileList.length) return;

      // Validate + map
      const accepted = [];
      for (const file of fileList) {
        if (this.effectiveMaxSizeMB && file.size > this.effectiveMaxSizeMB * MB) {
          this.error = `File exceeds max size (${this.effectiveMaxSizeMB} MB).`;
          continue;
        }
        if (this.effectiveAllowedFormats.length && !this.matchesAccept(file, this.effectiveAllowedFormats)) {
          this.error = `Invalid type. Allowed: ${this.effectiveAllowedFormats.join(", ")}.`;
          continue;
        }
        accepted.push(file);
      }

      if (!accepted.length) {
        e.target.value = "";
        return;
      }

      if (this.isMultiple) {
        const newMetas = accepted.map(f => ({
          source: "local",
          name: f.name,
          size: f.size,
          type: f.type || "",
          lastModified: f.lastModified || null
        }));

        const current = Array.isArray(this.value) ? this.value.slice() : [];
        // Deduplicate by (name,size,lastModified)
        const key = (m) => `${m.name}|${m.size}|${m.lastModified ?? ""}`;
        const existingKeys = new Set(current.map(key));
        for (const m of newMetas) {
          if (!existingKeys.has(key(m))) {
            existingKeys.add(key(m));
            current.push(m);
          }
        }

        this.$emit("input", current);
        this.$emit("file-selected", accepted); // emit array of Files
      } else {
        const file = accepted[0];
        const meta = {
          source: "local",
          name: file.name,
          size: file.size,
          type: file.type || "",
          lastModified: file.lastModified || null
        };
        this.$emit("input", meta);
        this.$emit("file-selected", file);
      }

      e.target.value = "";
    },

    onUrlInput(evt) {
      this.localUrl = evt.target.value;
    },

    onUrlBlur() {
      if (this.isMultiple) return; // handled by addUrl()
      const url = String(this.localUrl || "").trim();
      if (!url) { this.$emit("input", null); return; }
      let parsed;
      try { parsed = new URL(url); } catch { this.error = "Invalid URL."; return; }
      if (!/^https?:$/.test(parsed.protocol)) { this.error = "Only http(s) URLs are supported."; return; }
      this.error = "";
      this.$emit("input", { source: "url", url });
    },

    addUrl() {
      if (!this.isMultiple) return;
      const url = String(this.localUrl || "").trim();
      if (!url) return;
      let parsed;
      try { parsed = new URL(url); } catch { this.error = "Invalid URL."; return; }
      if (!/^https?:$/.test(parsed.protocol)) { this.error = "Only http(s) URLs are supported."; return; }
      this.error = "";

      const current = Array.isArray(this.value) ? this.value.slice() : [];
      if (!current.some(it => it && it.source === "url" && it.url === url)) {
        current.push({ source: "url", url });
        this.$emit("input", current);
      }
      this.localUrl = "";
    },

    removeLocalAt(idx) {
      if (!this.isMultiple) return;
      const current = Array.isArray(this.value) ? this.value.slice() : [];
      const localIdxs = current
        .map((it, i) => ({ it, i }))
        .filter(x => x.it && x.it.source === "local")
        .map(x => x.i);
      const toRemove = localIdxs[idx];
      if (toRemove !== undefined) {
        current.splice(toRemove, 1);
        this.$emit("input", current);
      }
    },

    removeUrlAt(idx) {
      if (!this.isMultiple) return;
      const current = Array.isArray(this.value) ? this.value.slice() : [];
      const urlIdxs = current
        .map((it, i) => ({ it, i }))
        .filter(x => x.it && x.it.source === "url")
        .map(x => x.i);
      const toRemove = urlIdxs[idx];
      if (toRemove !== undefined) {
        current.splice(toRemove, 1);
        this.$emit("input", current);
      }
    },

    clearValue() {
      this.error = "";
      this.localUrl = "";
      this.$emit("input", this.isMultiple ? [] : null);
    },

    humanSize(bytes) {
      if (!Number.isFinite(bytes)) return "";
      if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
      if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      return `${bytes} B`;
    },
    truncate(s, n) {
      const str = String(s || "");
      return str.length > n ? str.slice(0, n - 1) + "…" : str;
    },
    matchesAccept(file, accepts) {
      const name = file.name?.toLowerCase() || "";
      const mime = (file.type || "").toLowerCase();
      const checks = accepts.map(a => a.trim().toLowerCase()).filter(Boolean);
      if (!checks.length) return true;
      return checks.some(a => {
        if (a.endsWith("/*")) {
          const base = a.slice(0, -2);
          return mime.startsWith(base + "/");
        }
        if (a.startsWith(".")) {
          return name.endsWith(a);
        }
        if (a.includes("/")) {
          return mime === a;
        }
        return name.endsWith("." + a.replace(/^\./, ""));
      });
    }
  }
};
</script>

<style scoped>
.field-file-upload,
.field-file-upload .url-box,
.field-file-upload .url-row {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}
.field-file-upload .url-row input,
.field-file-upload .url-add-row input {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}
.field-file-upload { overflow: hidden; }
.uploader { display:flex; flex-direction:column; gap:8px }
.hidden-file-input { display:none }
.attach-btn { display:inline-flex; align-items:center; gap:8px; border:1px solid #d1d5db; background:white; padding:10px 14px; border-radius:8px; cursor:pointer; }
.url-box { display:flex; flex-direction:column; gap:6px }
.url-row { width:100%; }
.url-add-row { display:grid; grid-template-columns:1fr auto; gap:8px; align-items:center; }
.add-url-btn { padding:10px 14px; border-radius:8px; border:1px solid #d1d5db; background:#f9fafb; cursor:pointer; }
.icon-inline { border:none; background:transparent; padding:6px; border-radius:8px; cursor:pointer; }
.icon-inline.danger i { color:#b91c1c }
.meta { display:flex; flex-direction:column; gap:4px }
.file-row { display:flex; align-items:center; gap:8px; flex-wrap:wrap }
.name { font-weight:600 }
.size,.mime { color:#6b7280 }
.meta-dot { color:#9ca3af }
.rules { display:flex; flex-direction:column; gap:2px }
.help { color:#6b7280 }
.error { color:#dc2626; font-size:12px }
.readonly .attach-btn { opacity:.6; cursor:not-allowed }
.invalid input { border-color:#dc2626 }
.btn-option { background:#e5e7eb; color:#111827; border:none; }
</style>
