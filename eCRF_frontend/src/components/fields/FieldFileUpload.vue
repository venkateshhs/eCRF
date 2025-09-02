<template>
  <div class="field-file-upload" :class="{ readonly, invalid: !!error }">
    <!-- LOCAL UPLOAD MODE (Attachment button only) -->
    <div v-if="storagePreference==='local'" class="uploader">
      <input
        ref="fileInput"
        type="file"
        :accept="acceptAttr"
        class="hidden-file-input"
        :disabled="readonly"
        @change="onFilePicked"
      />
      <button
        class="attach-btn"
        type="button"
        :disabled="readonly"
        @click="triggerPick"
        title="Choose a file"
      >
        <i :class="icons.paperclip" />
        {{ value && value.source==='local' ? 'Replace file' : 'Attach file' }}
      </button>

      <div v-if="value && value.source==='local'" class="meta">
        <div class="file-row">
          <span class="name" :title="value.name">{{ value.name }}</span>
          <span class="meta-dot">•</span>
          <span class="size">{{ humanSize(value.size) }}</span>
          <span class="meta-dot" v-if="value.type">•</span>
          <span class="mime" v-if="value.type">{{ value.type }}</span>
          <button class="icon-inline danger" type="button" @click="clearValue" title="Remove">
            <i :class="icons.trash" />
          </button>
        </div>
        <small class="note" v-if="isBuilderStage">
          Files are <b>not persisted</b> during study creation. This control captures metadata only.
        </small>
      </div>
    </div>

    <!-- LINK VIA URL MODE (URL input only) -->
    <div v-else-if="storagePreference==='url'" class="url-box">
      <div class="url-row">
        <input
          type="url"
          :placeholder="urlPlaceholder"
          :value="displayedUrl"
          @input="onUrlInput"
          @blur="onUrlBlur"
          :readonly="readonly"
        />
      </div>
      <small class="note">
        Use a stable, accessible URL (institutional storage, or DOI).
      </small>
    </div>

    <!-- Help / rules -->
    <div class="rules">
      <small v-if="helpText" class="help">{{ helpText }}</small>
      <small class="constraints">
        Allowed: {{ allowedText }} • Max {{ effectiveMaxSizeMB }} MB
        <template v-if="modalities && modalities.length">
          • Modalities: {{ modalities.join(', ') }}
        </template>
      </small>
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
const DEFAULT_ALLOWED = ['.pdf', '.csv', '.tsv', 'image/*', 'txt'];
const DEFAULT_MAX_MB = 100; // ← default allowed storage is 100 MB

export default {
  name: "FieldFileUpload",
  props: {
    value: { type: [Object, null], default: null }, // { source: 'local'|'url', name, size, type, url? }
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

    // Storage behavior from settings (controls which UI appears)
    storagePreference() {
      const v = (this.constraints?.storagePreference || "local").toLowerCase();
      return (v === "url") ? "url" : "local";
    },

    maxSizeMB() {
      const n = Number(this.constraints?.maxSizeMB);
      return Number.isFinite(n) && n > 0 ? n : null;
    },
    effectiveMaxSizeMB() {
      return this.maxSizeMB || DEFAULT_MAX_MB;
    },

    allowedFormats() {
      const arr = Array.isArray(this.constraints?.allowedFormats)
        ? this.constraints.allowedFormats
        : [];
      return arr.map(String).map(s => s.trim()).filter(Boolean);
    },
    effectiveAllowedFormats() {
      return this.allowedFormats.length ? this.allowedFormats : DEFAULT_ALLOWED;
    },
    acceptAttr() {
      return this.effectiveAllowedFormats.join(",");
    },
    allowedText() {
      return this.effectiveAllowedFormats.join(", ");
    },

    modalities() {
      return Array.isArray(this.constraints?.modalities)
        ? this.constraints.modalities.filter(Boolean).map(String)
        : [];
    },

    urlPlaceholder() { return "https://example.org/path/to/large/file"; },
    displayedUrl() {
      if (this.value?.source === "url") return this.value.url || "";
      return this.localUrl;
    }
  },
  mounted() {
    if (this.value?.source === "url") {
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
      const file = e?.target?.files?.[0];
      if (!file) return;

      if (this.effectiveMaxSizeMB && file.size > this.effectiveMaxSizeMB * MB) {
        this.error = `File exceeds max size (${this.effectiveMaxSizeMB} MB).`;
        e.target.value = "";
        return;
      }

      if (this.effectiveAllowedFormats.length) {
        const ok = this.matchesAccept(file, this.effectiveAllowedFormats);
        if (!ok) {
          this.error = `Invalid type. Allowed: ${this.allowedText}.`;
          e.target.value = "";
          return;
        }
      }

      const meta = {
        source: "local",
        name: file.name,
        size: file.size,
        type: file.type || "",
        lastModified: file.lastModified || null
      };
      this.$emit("input", meta);
      e.target.value = "";
    },
    onUrlInput(evt) {
      this.localUrl = evt.target.value;
    },
    onUrlBlur() {
      // Save URL value (no download)
      const url = String(this.localUrl || "").trim();
      if (!url) { this.$emit("input", null); return; }
      let parsed;
      try { parsed = new URL(url); } catch { this.error = "Invalid URL."; return; }
      if (!/^https?:$/.test(parsed.protocol)) { this.error = "Only http(s) URLs are supported."; return; }
      this.error = "";
      this.$emit("input", { source: "url", url });
    },
    clearValue() {
      this.error = "";
      this.localUrl = "";
      this.$emit("input", null);
    },
    humanSize(bytes) {
      if (!Number.isFinite(bytes)) return "";
      if (bytes >= MB) return `${(bytes / MB).toFixed(2)} MB`;
      if (bytes >= KB) return `${(bytes / KB).toFixed(1)} KB`;
      return `${bytes} B`;
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
  min-width: 0;        /* critical in flex layouts */
}

.field-file-upload .url-row input {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box; /* include padding/border in width */
  display: block;
  overflow: hidden;
  text-overflow: ellipsis; /* long URLs don’t push layout */
}

.field-file-upload { overflow: hidden; }
.uploader { display:flex; flex-direction:column; gap:8px }
.hidden-file-input { display:none }
.attach-btn { display:inline-flex; align-items:center; gap:8px; border:1px solid #d1d5db; background:white; padding:10px 14px; border-radius:8px; cursor:pointer; }
.url-box { display:flex; flex-direction:column; gap:6px }
.url-row { width:100%; }
.url-row input { width:100%; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px; }
.icon-inline { border:none; background:transparent; padding:6px; border-radius:8px; cursor:pointer; }
.icon-inline.danger i { color:#b91c1c }
.meta { display:flex; flex-direction:column; gap:4px }
.file-row { display:flex; align-items:center; gap:8px; flex-wrap:wrap }
.name { font-weight:600 }
.size,.mime { color:#6b7280 }
.meta-dot { color:#9ca3af }
.rules { display:flex; flex-direction:column; gap:2px }
.help { color:#6b7280 }
.constraints { color:#9ca3af }
.error { color:#dc2626; font-size:12px }
.readonly .attach-btn { opacity:.6; cursor:not-allowed }
.invalid input { border-color:#dc2626 }
</style>
