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
      <p v-if="studyDetails.metaInfo && studyDetails.metaInfo.numberOfSubjects">
        <strong>Number of Subjects:</strong> {{ studyDetails.metaInfo.numberOfSubjects }}
      </p>
      <p v-if="studyDetails.metaInfo && studyDetails.metaInfo.numberOfVisits">
        <strong>Number of Visits per Subject:</strong> {{ studyDetails.metaInfo.numberOfVisits }}
      </p>
      <p v-if="studyDetails.metaInfo && studyDetails.metaInfo.studyMetaDescription">
        <strong>Study Meta Description:</strong> {{ studyDetails.metaInfo.studyMetaDescription }}
      </p>

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

  <!-- Meta Edit Dialog Modal -->
  <div v-if="showMetaEditDialog" class="modal-overlay">
    <div class="modal meta-edit-dialog">
      <h3>Edit Meta Information</h3>
      <div class="meta-edit-field">
        <label>Study Name:</label>
        <input type="text" v-model="metaEditForm.name" placeholder="Enter study name" />
      </div>
      <div class="meta-edit-field">
        <label>Description:</label>
        <textarea v-model="metaEditForm.description" placeholder="Enter study description"></textarea>
      </div>
      <div class="meta-edit-field">
        <label>Number of Forms:</label>
        <input type="number" v-model.number="metaEditForm.numberOfForms" placeholder="Enter number of forms" />
      </div>
      <div class="meta-edit-field">
        <label>Number of Subjects:</label>
        <input type="number" v-model.number="metaEditForm.numberOfSubjects" placeholder="Enter number of subjects" />
      </div>
      <div class="meta-edit-field">
        <label>Number of Visits per Subject:</label>
        <input type="number" v-model.number="metaEditForm.numberOfVisits" placeholder="Enter number of visits" />
      </div>
      <div class="meta-edit-field">
        <label>Study Meta Description:</label>
        <textarea v-model="metaEditForm.studyMetaDescription" placeholder="Enter meta description"></textarea>
      </div>
      <div class="modal-actions">
        <button @click="saveMetaEditDialog" class="btn-primary modal-btn" title="Save Meta Information">Save</button>
        <button @click="cancelMetaEditDialog" class="btn-option modal-btn" title="Cancel Meta Edit">Cancel</button>
      </div>
    </div>
  </div>

  <!-- Reinitialization Confirmation Modal -->
  <div v-if="showReinitConfirm" class="modal-overlay">
    <div class="modal forms-confirm-dialog">
      <p>Changing the number of forms will reinitialize your current forms. Proceed?</p>
      <div class="modal-actions">
        <button @click="confirmReinit" class="btn-primary modal-btn" title="Confirm Reinitialization">Yes</button>
        <button @click="cancelReinit" class="btn-option modal-btn" title="Cancel Reinitialization">No</button>
      </div>
    </div>
  </div>

  <!-- Description Dialog Modal for File Attachments -->
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
import { mapGetters } from "vuex";
import icons from "@/assets/styles/icons";
export default {
  name: "StudyMetaInfo",
  emits: ["toggle-meta-info", "reload-forms"],
  data() {
    return {
      metaFiles: [],
      pendingFiles: [],
      showDescriptionDialog: false,
      metaInfoCollapsed: true, // collapsed by default
      showMetaEditDialog: false,
      showReinitConfirm: false,
      pendingMetaEdit: null,
      icons,
      // metaEditForm holds the editable copy of study details (including metaInfo)
      metaEditForm: {
        name: "",
        description: "",
        numberOfForms: null,
        numberOfSubjects: null,
        numberOfVisits: null,
        studyMetaDescription: "",
      },
    };
  },
  computed: {
    ...mapGetters(["getStudyDetails"]),
    studyDetails() {
      return this.getStudyDetails || {};
    },
    metaInfo() {
      return (this.getStudyDetails.metaInfo) ? this.getStudyDetails.metaInfo : {};
    },
  },
  created() {
    // Initialize metaEditForm from Vuex store if available
    if (this.getStudyDetails) {
      this.metaEditForm = {
        name: this.getStudyDetails.name || "",
        description: this.getStudyDetails.description || "",
        numberOfForms: this.getStudyDetails.numberOfForms || 1,
        numberOfSubjects: this.getStudyDetails.metaInfo?.numberOfSubjects,
        numberOfVisits: this.getStudyDetails.metaInfo?.numberOfVisits,
        studyMetaDescription: this.getStudyDetails.metaInfo?.studyMetaDescription || "",
      };
    }
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
      this.metaInfoCollapsed = !this.metaInfoCollapsed;
      this.$emit("toggle-meta-info", this.metaInfoCollapsed);
    },
    openMetaEditDialog() {
      // Initialize metaEditForm from current Vuex store values
      this.metaEditForm = {
        name: this.getStudyDetails.name || "",
        description: this.getStudyDetails.description || "",
        numberOfForms: this.getStudyDetails.numberOfForms || 1,
        numberOfSubjects: this.getStudyDetails.metaInfo?.numberOfSubjects,
        numberOfVisits: this.getStudyDetails.metaInfo?.numberOfVisits,
        studyMetaDescription: this.getStudyDetails.metaInfo?.studyMetaDescription || "",
      };
      this.showMetaEditDialog = true;
    },
    cancelMetaEditDialog() {
      this.showMetaEditDialog = false;
    },
    saveMetaEditDialog() {
      // If numberOfForms changed compared to stored value, prompt reinit confirmation
      if (this.getStudyDetails.numberOfForms !== this.metaEditForm.numberOfForms) {
        this.pendingMetaEdit = { ...this.metaEditForm };
        this.showMetaEditDialog = false;
        this.showReinitConfirm = true;
      } else {
        this.commitMetaEdit();
      }
    },
    commitMetaEdit() {
      // Merge updated metaEditForm into stored studyDetails and commit to Vuex
      let updatedDetails = { ...this.getStudyDetails, ...this.metaEditForm };
      updatedDetails.metaInfo = {
        numberOfSubjects: this.metaEditForm.numberOfSubjects,
        numberOfVisits: this.metaEditForm.numberOfVisits,
        studyMetaDescription: this.metaEditForm.studyMetaDescription,
      };
      this.$store.commit("setStudyDetails", updatedDetails);
      this.showMetaEditDialog = false;
    },
    confirmReinit() {
      // Emit event to reload form container with new number of forms
      this.$emit("reload-forms", this.pendingMetaEdit.numberOfForms);
      this.commitMetaEdit();
      this.showReinitConfirm = false;
      this.pendingMetaEdit = null;
    },
    cancelReinit() {
      this.showReinitConfirm = false;
      this.pendingMetaEdit = null;
      this.commitMetaEdit();
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

/* Additional CSS for Toggle Switch and Container */
.meta-toggle-container {
  margin-top: 15px;
  display: flex;
  align-items: center;
}
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
  margin-right: 10px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.4s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.4s;
  border-radius: 50%;
}
.switch input:checked + .slider {
  background-color: #2196F3;
}
.switch input:checked + .slider:before {
  transform: translateX(26px);
}
.toggle-label {
  font-size: 14px;
  color: #333;
}
.meta-container {
  margin-top: 15px;
  padding: 15px;
  background-color: #fff;
  border: 1px solid #ccc;
  border-radius: 8px;
}

/* New styles for Meta Edit Dialog */
.modal.meta-edit-dialog {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.modal.meta-edit-dialog h3 {
  margin-top: 0;
}
.meta-edit-dialog label {
  font-weight: bold;
  display: block;
  margin-top: 10px;
}
.meta-edit-dialog input,
.meta-edit-dialog textarea {
  width: 100%;
  padding: 8px;
  margin-top: 5px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}
.meta-edit-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

/* New styles for Reinitialization Confirmation Dialog */
.modal.forms-confirm-dialog {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.modal.forms-confirm-dialog h3 {
  margin-top: 0;
}
</style>
