<template>
  <div class="uploaded-files-backdrop" @click.self="$emit('close')">
    <div class="uploaded-files-dialog" role="dialog" aria-modal="true">
      <div class="dialog-head">
        <div>
          <h3>Uploaded Files</h3>
          <p>{{ subjectLabel }} · {{ visitLabel }}</p>
        </div>
        <button type="button" class="close-btn" @click="$emit('close')" aria-label="Close">
          ×
        </button>
      </div>

      <div v-if="!groupedFiles.length" class="empty-state">
        No uploaded files found for this subject and visit.
      </div>

      <div v-else class="files-body">
        <section v-for="section in groupedFiles" :key="section.key" class="section-group">
          <h4>{{ section.title }}</h4>

          <div v-for="field in section.fields" :key="field.key" class="field-group">
            <div class="field-title">{{ field.label }}</div>

            <div v-for="file in field.files" :key="file.key" class="file-row">
              <i class="fas fa-paperclip" aria-hidden="true"></i>
              <span class="file-name" :title="file.displayName">{{ file.displayName }}</span>
              <button
                type="button"
                class="download-btn"
                :disabled="!file.downloadable"
                :title="file.downloadable ? 'Download file' : 'Download unavailable'"
                @click="$emit('download-file', file)"
              >
                <i class="fas fa-download" aria-hidden="true"></i>
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "UploadedFilesDialog",
  props: {
    files: { type: Array, default: () => [] },
    subjectLabel: { type: String, default: "Subject" },
    visitLabel: { type: String, default: "Visit" },
  },
  emits: ["close", "download-file"],
  computed: {
    groupedFiles() {
      const sections = [];
      const sectionMap = new Map();

      (this.files || []).forEach((file, index) => {
        const sectionTitle = file.sectionTitle || "Section";
        const fieldLabel = file.fieldLabel || "Field";
        const sectionKey = `${file.sectionIndex ?? sectionTitle}`;
        const fieldKey = `${sectionKey}|${file.fieldIndex ?? fieldLabel}`;

        if (!sectionMap.has(sectionKey)) {
          const section = { key: sectionKey, title: sectionTitle, fields: [], fieldMap: new Map() };
          sectionMap.set(sectionKey, section);
          sections.push(section);
        }

        const section = sectionMap.get(sectionKey);
        if (!section.fieldMap.has(fieldKey)) {
          const field = { key: fieldKey, label: fieldLabel, files: [] };
          section.fieldMap.set(fieldKey, field);
          section.fields.push(field);
        }

        section.fieldMap.get(fieldKey).files.push({
          ...file,
          key: `${fieldKey}|${file.dbId || file.id || file.file_id || file.displayName || index}|${index}`,
        });
      });

      return sections.map((section) => ({
        key: section.key,
        title: section.title,
        fields: section.fields,
      }));
    },
  },
};
</script>

<style scoped>
.uploaded-files-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  background: rgba(15, 23, 42, 0.45);
}

.uploaded-files-dialog {
  width: min(760px, 96vw);
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.28);
}

.dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}

.dialog-head h3 {
  margin: 0 0 4px;
  color: #111827;
}

.dialog-head p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.close-btn,
.download-btn {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.close-btn {
  width: 34px;
  height: 34px;
  font-size: 22px;
  line-height: 1;
}

.files-body {
  padding: 16px 20px 20px;
  overflow-y: auto;
}

.empty-state {
  padding: 30px 20px;
  color: #6b7280;
  text-align: center;
}

.section-group {
  margin-bottom: 18px;
}

.section-group h4 {
  margin: 0 0 10px;
  color: #111827;
}

.field-group {
  margin: 10px 0;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
}

.field-title {
  margin-bottom: 8px;
  color: #374151;
  font-weight: 700;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px 0;
}

.file-name {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.download-btn {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  color: #2563eb;
}

.download-btn:disabled {
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
