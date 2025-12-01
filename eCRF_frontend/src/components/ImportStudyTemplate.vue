<template>
  <div class="import-template-wrap">
    <div class="container-box">
      <!-- Header (centered title + subtitle, back on top-left) -->
      <div class="header-row">
        <button class="btn-minimal back-btn" @click="goBack">Back</button>
        <h1 class="title">Import Study Template</h1>
        <p class="subtitle">
          Import a <strong>template only</strong> (no participant data). Use a JSON created via “Export Study”.
        </p>
      </div>

      <!-- File panel -->
      <div class="panel card-surface">
        <label class="file-label">Template JSON</label>

        <div class="file-pick">
          <div class="file-name" v-if="fileName">{{ fileName }}</div>
          <div class="file-name muted" v-else>No file selected</div>

          <div class="buttons center">
            <button class="btn-option" @click.prevent="triggerFilePick">
              Choose File
            </button>
            <input
              ref="fileInput"
              class="hidden-file"
              type="file"
              accept=".json,application/json"
              @change="onFilePicked"
            />
          </div>
        </div>

        <p class="hint">
          We will parse the JSON and show a summary before creating the study (template only).
        </p>

        <p v-if="error" class="msg err">{{ error }}</p>
      </div>

      <!-- Summary / meta edit -->
      <div v-if="parsed" class="panel card-surface">
        <h3 class="section-title">Template Summary</h3>

        <div class="meta-grid">
          <div class="kv full">
            <span class="k">Study Name</span>
            <input v-model="studyName" placeholder="Study name" />
          </div>
          <div class="kv full">
            <span class="k">Description</span>
            <textarea v-model="studyDescription" rows="2" placeholder="Optional description"></textarea>
          </div>

          <div class="kv">
            <span class="k">Groups</span>
            <span class="v">{{ groupsCount }}</span>
          </div>
          <div class="kv">
            <span class="k">Visits</span>
            <span class="v">{{ visitsCount }}</span>
          </div>
          <div class="kv">
            <span class="k">Subjects</span>
            <span class="v">{{ subjectsCount }}</span>
          </div>
          <div class="kv">
            <span class="k">Form Sections</span>
            <span class="v">{{ sectionsCount }}</span>
          </div>
        </div>

        <div class="buttons center">
          <button class="btn-primary" :disabled="creating" @click="createStudy">
            {{ creating ? 'Creating…' : 'Create Study from Template' }}
          </button>
          <button class="btn-option" :disabled="creating" @click="resetAll">Clear</button>
        </div>
      </div>

      <!-- Success -->
      <div v-if="createdStudy" class="panel success card-surface">
        <h3 class="section-title">Study Imported</h3>
        <p class="ok">“{{ createdStudy.study_name }}” was created successfully.</p>
        <div class="buttons center">
          <button class="btn-primary" @click="openStudy(createdStudy.id)">Open Study</button>
          <button class="btn-option" @click="goDashboard">Go to Dashboard</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "ImportStudyTemplate",
  data() {
    return {
      file: null,
      fileName: "",
      parsed: null,          // normalized template JSON
      studyName: "",
      studyDescription: "",
      error: null,
      creating: false,
      createdStudy: null,
    };
  },
  computed: {
    token() { return this.$store.state.token; },
    authHeader() { return { Authorization: `Bearer ${this.token}` }; },
    currentUserId() { return this.$store.state.user?.id || null; },

    groupsCount() { return (this.parsed?.groups || []).length; },
    visitsCount() { return (this.parsed?.visits || []).length; },
    subjectsCount() { return (this.parsed?.subjects || []).length; },
    sectionsCount() { return (this.parsed?.selectedModels || []).length; },
  },
  methods: {
    goBack() { this.$router.back(); },
    goDashboard() { this.$router.push({ name: "Dashboard" }); },
    openStudy(id) { this.$router.push({ name: "StudyView", params: { id } }); },

    triggerFilePick() {
      this.$refs.fileInput?.click();
    },
    onFilePicked(e) {
      const f = e.target.files && e.target.files[0];
      if (f) this.handleFile(f);
    },
    async handleFile(f) {
      this.error = null;
      this.parsed = null;
      this.createdStudy = null;
      this.file = f;
      this.fileName = f.name || "";

      try {
        const text = await f.text();
        const raw = JSON.parse(text);

        // Accept either wrapper {study_data: {...}} or raw template at root
        const candidate = raw?.study_data && typeof raw.study_data === "object" ? raw.study_data : raw;
        const sd = typeof candidate === "object" ? candidate : null;

        if (!sd || !Array.isArray(sd.selectedModels)) {
          throw new Error("Invalid template format. Missing selectedModels.");
        }

        // Keep entire object (no data loss) and then ensure study title/description
        this.parsed = sd;

        const studyObj = sd.study || {};
        this.studyName = studyObj.title || raw.study_name || "Imported Study";
        this.studyDescription = studyObj.description || raw.study_description || "";
      } catch (err) {
        console.error(err);
        this.error = "Failed to parse JSON. Please select a valid template file.";
      }
    },
    resetAll() {
      this.file = null;
      this.fileName = "";
      this.parsed = null;
      this.studyName = "";
      this.studyDescription = "";
      this.error = null;
      this.createdStudy = null;
      const el = this.$refs.fileInput;
      if (el) el.value = "";
    },

    // Use EXACT SAME POST signature as ProtocolMatrix: POST /forms/studies/
    async createStudy() {
      if (!this.parsed || !this.studyName) {
        this.error = "Missing template or study name.";
        return;
      }
      if (!this.token) {
        alert("Please log in again.");
        return this.$router.push("/login");
      }

      this.creating = true;
      this.error = null;

      try {
        // study_metadata (same shape ProtocolMatrix uses)
        const study_metadata = {
          created_by: this.currentUserId,
          study_name: this.studyName,
          study_description: this.studyDescription,
        };

        // Build study_data WITHOUT losing any keys from the template:
        const original = JSON.parse(JSON.stringify(this.parsed || {})); // safe clone
        const studyNode = {
          ...(original.study || {}),
          title: this.studyName,
          description: this.studyDescription,
        };
        const study_data = { ...original, study: studyNode };

        const payload = {
          study_metadata,
          study_content: { study_data },
        };

        const resp = await axios.post("/forms/studies/", payload, { headers: this.authHeader });
        const meta = resp.data?.study_metadata || resp.data?.metadata || {};
        this.createdStudy = {
          id: meta.id ?? resp.data?.id,
          study_name: meta.study_name ?? this.studyName,
        };
      } catch (e) {
        console.error(e);
        this.error = e?.response?.data?.detail || "Failed to create study from template.";
      } finally {
        this.creating = false;
      }
    },
  },
};
</script>

<style scoped>
/* Layout */
.import-template-wrap {
  display: grid;
  place-items: start center;
  padding: 24px;
  background: #fff;
}
.container-box {
  width: min(960px, 96vw);
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-sizing: border-box;
}

/* Header (centered title & subtitle, back on top-left) */
.header-row {
  position: relative;
  text-align: center;
  padding-top: 2px;
  margin-bottom: 6px;
}
.back-btn {
  position: absolute;
  left: 0;
  top: 0;
}
.title {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}
.subtitle {
  margin: 0;
  color: #4b5563;
  font-size: 0.95rem;
}

/* Card surface like ExportStudy */
.card-surface {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 25px rgba(16, 24, 40, 0.06);
}

/* Panels */
.panel {
  padding: 14px;
  margin-top: 12px;
}
.panel.success {
  border-color: #c7f9cc;
  background: #f0fff4;
}

/* File picker (simple, no DnD) */
.file-label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: #374151;
}
.file-pick { display: grid; gap: 10px; }
.hidden-file { display: none; }
.file-name { font-size: 0.95rem; }
.muted { color: #6b7280; }
.hint { color: #6b7280; font-size: 0.9rem; margin-top: 8px; }

/* Summary */
.section-title {
  margin: 0 0 10px 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: #1f2937;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}
.kv { display: contents; }
.kv.full { grid-column: 1 / -1; display: grid; grid-template-columns: 160px 1fr; align-items: center; gap: 10px; }
.k { color: #6b7280; font-weight: 500; }
.v { color: #111827; }

.meta-grid input,
.meta-grid textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.95rem;
  background: #fff;
  outline: none;
  box-sizing: border-box;
}
.meta-grid input:focus,
.meta-grid textarea:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}

/* Buttons */
.buttons { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.buttons.center { justify-content: center; }
.btn-primary {
  padding: 10px 14px;
  background: #4f46e5;
  color: #fff;
  border: 1px solid #4338ca;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.15s ease, box-shadow 0.2s ease;
}
.btn-primary:hover { background: #4338ca; box-shadow: 0 6px 14px rgba(67,56,202,0.25); }
.btn-option {
  padding: 10px 14px;
  background: #ffffff;
  color: #111827;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.15s ease, box-shadow 0.2s ease;
}
.btn-option:hover { background: #f8fafc; box-shadow: 0 6px 14px rgba(16,24,40,0.08); }

/* Back button (same global minimal style) */
.btn-minimal {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.btn-minimal:hover { background: #e8e8e8; color: #000; border-color: #d6d6d6; }

/* Messages */
.msg.err { color: #dc2626; margin-top: 8px; }
.ok { color: #16a34a; }

/* Responsive */
@media (max-width: 820px) {
  .meta-grid { grid-template-columns: 1fr; }
  .kv.full { grid-template-columns: 1fr; }
  .k { margin-bottom: 6px; }
}
</style>
