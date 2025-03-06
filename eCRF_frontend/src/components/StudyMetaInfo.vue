<template>
  <div class="meta-info-container" :class="{ collapsed: metaInfoCollapsed }">
    <div class="meta-header">
      <h2>Study Meta Information</h2>
      <div class="meta-actions">
        <button @click="openMetaEditDialog" class="btn-meta-edit" title="Edit Meta Information">
          <i :class="icons.edit"></i>
        </button>
        <button
          @click="toggleMetaInfo"
          class="btn-meta-toggle"
          :title="metaInfoCollapsed ? 'Expand Meta Information' : 'Collapse Meta Information'"
        >
          <i :class="metaInfoCollapsed ? icons.toggleDown : icons.toggleUp"></i>
        </button>
      </div>
    </div>
    <div v-if="!metaInfoCollapsed">
      <p v-if="studyDetails.name"><strong>Study Name:</strong> {{ studyDetails.name }}</p>
      <p v-if="studyDetails.description"><strong>Description:</strong> {{ studyDetails.description }}</p>
      <p v-if="studyDetails.numberOfForms"><strong>Number of Forms:</strong> {{ studyDetails.numberOfForms }}</p>
      <p v-if="metaInfo.numberOfSubjects"><strong>Number of Subjects:</strong> {{ metaInfo.numberOfSubjects }}</p>
      <p v-if="metaInfo.numberOfVisits"><strong>Number of Visits per Subject:</strong> {{ metaInfo.numberOfVisits }}</p>
      <p v-if="metaInfo.studyMetaDescription"><strong>Study Meta Description:</strong> {{ metaInfo.studyMetaDescription }}</p>

      <!-- File Attachment Option -->
      <div class="file-attachment">
        <label for="meta-file-upload" class="attach-file-label">Attach File(s):</label>
        <input type="file" id="meta-file-upload" ref="metaFileInput" @change="handleMetaFile" multiple />
        <div v-if="metaFiles.length" class="attached-files-info">
          <div v-for="(fileObj, index) in metaFiles" :key="index" class="attached-file-info">
            <span>{{ fileObj.file.name }}</span>
            <p v-if="fileObj.description" class="file-description">
              <em>{{ fileObj.description }}</em>
            </p>
            <button @click="removeMetaFile(index)" class="btn-remove-file" title="Remove attached file">
              <i :class="icons.delete"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Description Dialog Modal -->
  <div v-if="showDescriptionDialog" class="modal-overlay">
    <div class="modal description-dialog">
      <h3>Enter Description for Attached File(s)</h3>
      <div v-for="(fileObj, index) in pendingFiles" :key="index" class="description-item">
        <p><strong>{{ fileObj.file.name }}</strong></p>
        <input
          type="text"
          v-model="fileObj.description"
          placeholder="Enter description for this file"
          class="file-description-input"
        />
      </div>
      <div class="modal-actions">
        <button @click="saveDescriptions" class="btn-primary modal-btn" title="Save Descriptions">Save</button>
        <button @click="cancelDescriptions" class="btn-option modal-btn" title="Cancel">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script>
import icons from "@/assets/styles/icons";
export default {
  name: "StudyMetaInfo",
  props: {
    studyDetails: {
      type: Object,
      required: true,
    },
    metaInfo: {
      type: Object,
      required: true,
    },
    metaInfoCollapsed: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      metaFiles: [],
      pendingFiles: [],
      showDescriptionDialog: false,
      icons,
    };
  },
  methods: {
    handleMetaFile(event) {
      const files = event.target.files;
      if (files && files.length) {
        this.pendingFiles = [];
        for (let i = 0; i < files.length; i++) {
          this.pendingFiles.push({
            file: files[i],
            description: "",
          });
        }
        this.showDescriptionDialog = true;
      }
    },
    saveDescriptions() {
      this.metaFiles = this.metaFiles.concat(this.pendingFiles);
      this.pendingFiles = [];
      this.showDescriptionDialog = false;
      if (this.$refs.metaFileInput) {
        this.$refs.metaFileInput.value = "";
      }
    },
    cancelDescriptions() {
      this.pendingFiles = [];
      this.showDescriptionDialog = false;
      if (this.$refs.metaFileInput) {
        this.$refs.metaFileInput.value = "";
      }
    },
    removeMetaFile(index) {
      this.metaFiles.splice(index, 1);
      if (this.$refs.metaFileInput) {
        this.$refs.metaFileInput.value = "";
      }
    },
    toggleMetaInfo() {
      this.$emit("toggle-meta-info");
    },
    openMetaEditDialog() {
      this.$emit("open-meta-edit-dialog");
    },
  },
};
</script>

<style scoped>
.meta-info-container {
  width: 100%;
  box-sizing: border-box;
  background: white;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  transition: padding 0.3s ease, font-size 0.3s ease;
}
.meta-info-container.collapsed {
  padding: 5px 10px;
  font-size: 12px;
}
.meta-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.meta-actions {
  display: flex;
  gap: 10px;
}
.btn-meta-edit,
.btn-meta-toggle {
  background: #ccc;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 5px 8px;
  cursor: pointer;
  transition: background 0.3s ease;
}
.btn-meta-edit:hover,
.btn-meta-toggle:hover {
  background: #bbb;
}
.file-attachment {
  margin-top: 15px;
  padding: 10px;
  border-top: 1px solid #ccc;
}
.attach-file-label {
  font-weight: bold;
  margin-right: 10px;
}
.attached-files-info {
  margin-top: 5px;
}
.attached-file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 5px;
}
.file-description {
  margin: 0;
  font-style: italic;
  color: #555;
}
.btn-remove-file {
  background: transparent;
  border: none;
  cursor: pointer;
}

/* Description Dialog Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal.description-dialog {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.description-item {
  margin-bottom: 10px;
}
.file-description-input {
  width: 100%;
  padding: 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-top: 5px;
  box-sizing: border-box;
}
.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}
.modal-actions button {
  flex: 1;
}
</style>
