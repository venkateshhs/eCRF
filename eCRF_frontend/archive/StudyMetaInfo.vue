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

    <!-- Dynamic Rendering of Study Details from Vuex -->
    <div v-if="!metaInfoCollapsed" class="meta-details">
      <div v-if="studyDetails">
        <div v-for="(value, key) in studyDetails" :key="key">
          <template v-if="!isObject(value)">
            <p v-if="value">
              <strong>{{ formatKey(key) }}:</strong> {{ value }}
            </p>
          </template>
          <template v-else>
            <!-- Special handling for metaInfo: show visits, groups, visit names if present -->
            <div v-if="key === 'metaInfo'">
              <h3>{{ formatKey(key) }}</h3>
              <div v-for="(subValue, subKey) in value" :key="subKey">
                <p v-if="Array.isArray(subValue)">
                  <strong>{{ formatKey(subKey) }}:</strong> {{ subValue.join(', ') }}
                </p>
                <p v-else>
                  <strong>{{ formatKey(subKey) }}:</strong> {{ subValue }}
                </p>
              </div>
            </div>
            <!-- For custom fields arrays -->
            <div v-else-if="Array.isArray(value)">
              <h3>{{ formatKey(key) }}</h3>
              <ul>
                <li v-for="(item, index) in value" :key="index">
                  <strong>{{ item.fieldName }}</strong>: {{ item.fieldValue }}
                </li>
              </ul>
            </div>
            <!-- For plain objects -->
            <div v-else>
              <p>
                <strong>{{ formatKey(key) }}:</strong> {{ value }}
              </p>
            </div>
          </template>
        </div>
      </div>

      <!-- File Attachments Section -->
      <div class="file-attachment">
        <label for="meta-file-upload" class="attach-file-label">Attach File(s):</label>
        <input type="file" id="meta-file-upload" ref="metaFileInput" @change="handleMetaFile" multiple />
        <label for="meta-storage-option" class="attach-file-label">Storage Option:</label>
        <select id="meta-storage-option" v-model="metaStorageOption">
          <option value="db">Store in Database</option>
          <option value="local">Store on Local Disk</option>
        </select>
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

  <!-- Mapping Modal / Transition Screen -->
  <div v-if="showMappingModal" class="modal-overlay">
    <div class="modal-dialog">
      <h3>Mapping Details</h3>
      <div class="modal-input-group">
        <label>Number of Visits</label>
        <input type="number" v-model.number="numberOfVisitsInput" min="1" />
      </div>
      <div class="modal-input-group">
        <label>Number of Groups/Cohorts</label>
        <input type="number" v-model.number="numberOfGroupsInput" min="1" />
      </div>
      <div class="modal-input-group groups-container">
        <label>Enter Group Names</label>
        <div v-for="n in numberOfGroupsInput" :key="n">
          <input type="text" v-model="groups[n - 1]" :placeholder="`Group ${n}`" />
        </div>
      </div>
      <div class="modal-input-group">
        <label>Visit Names</label>
        <div v-for="(visit, index) in numberOfVisitsInput" :key="'visit-'+index">
          <input type="text" v-model="visitLabels[index]" :placeholder="`Visit ${index + 1}`" />
        </div>
      </div>
      <div class="modal-actions">
        <button @click="submitMappingDetails">Submit</button>
        <button @click="cancelMappingModal">Cancel</button>
      </div>
    </div>
  </div>

  <!-- Mapping Screen: Matrix Layout -->
  <div v-if="showMappingScreen" class="mapping-screen">
    <h2>Mapping Data Models</h2>
    <div class="table-container">
      <table class="mapping-table">
        <thead>
          <tr>
            <th rowspan="2">Data Model</th>
            <template v-for="(visit, vIndex) in numberOfVisits" :key="'visit-' + vIndex">
              <th :colspan="groups.length">
                <input type="text" v-model="visitLabels[vIndex]" class="visit-label-input" />
              </th>
            </template>
          </tr>
          <tr>
            <template v-for="(visit, vIndex) in numberOfVisits" :key="'groups-' + vIndex">
              <th v-for="(group, gIndex) in groups" :key="'group-' + vIndex + '-' + gIndex">
                {{ group }}
              </th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(dm, dmIndex) in dataModels" :key="'dm-' + dmIndex">
            <td class="sticky-col">{{ dm }}</td>
            <template v-for="(visit, vIndex) in numberOfVisits" :key="'cell-' + vIndex">
              <td v-for="(group, gIndex) in groups" :key="'cell-' + vIndex + '-' + gIndex">
                <input type="checkbox" v-model="mappingSelection[vIndex][gIndex][dmIndex]" class="small-checkbox" />
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
    <button @click="finalizeMapping" class="btn-option">Finalize</button>
  </div>

  <!-- Dynamic Meta Edit Dialog Modal -->
  <div v-if="showMetaEditDialog" class="modal-overlay">
    <div class="modal meta-edit-dialog">
      <h3>Edit Meta Information</h3>
      <div v-for="(value, key) in metaEditForm" :key="key" class="meta-edit-field">
        <label>{{ formatKey(key) }}:</label>
        <template v-if="!isObject(value)">
          <input type="text" v-model="metaEditForm[key]" />
        </template>
        <template v-else-if="Array.isArray(value)">
          <div v-for="(item, idx) in value" :key="idx" class="array-field">
            <input type="text" v-model="metaEditForm[key][idx]" />
          </div>
        </template>
        <template v-else>
          <textarea v-model="metaEditForm[key]"></textarea>
        </template>
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

  <!-- File Description Dialog Modal -->
  <div v-if="showDescriptionDialog" class="modal-overlay">
    <div class="modal description-dialog">
      <h3>Enter Description for Attached File(s)</h3>
      <div v-for="(fileObj, index) in pendingFiles" :key="index" class="description-item">
        <p><strong>{{ fileObj.file.name }}</strong></p>
        <input type="text" v-model="fileObj.description" placeholder="Enter description for this file" class="file-description-input" />
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
      metaInfoCollapsed: true,
      showMetaEditDialog: false,
      showReinitConfirm: false,
      pendingMetaEdit: null,
      icons,
      metaStorageOption: "db",
      // metaEditForm will be set dynamically from the Vuex store's studyDetails.
      metaEditForm: {},
      metaEditErrors: {},
    };
  },
  computed: {
    ...mapGetters(["getStudyDetails"]),
    studyDetails() {
      return this.getStudyDetails || {};
    },
  },
  created() {
    // Instead of assuming specific fields, we simply clone the entire studyDetails object.
    if (this.getStudyDetails) {
      this.metaEditForm = JSON.parse(JSON.stringify(this.getStudyDetails));
    }
    console.log("Initial Vuex studyDetails:", this.getStudyDetails);
  },
  watch: {
    getStudyDetails(newVal) {
      console.log("Updated Vuex studyDetails:", newVal);
    },
  },
  methods: {
    formatKey(key) {
      if (!key) return "";
      return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ");
    },
    isObject(val) {
      return val !== null && typeof val === "object";
    },
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
      // Clone the store details into metaEditForm without assumptions.
      this.metaEditForm = JSON.parse(JSON.stringify(this.getStudyDetails || {}));
      // Reset errors
      this.metaEditErrors = {};
      this.showMetaEditDialog = true;
    },
    cancelMetaEditDialog() {
      this.showMetaEditDialog = false;
    },
    saveMetaEditDialog() {
      // For a dynamic form, perform minimal validation:
      // (Here you could iterate over keys and set errors if needed)
      // For now, we assume all entered values are valid.
      this.$store.commit("setStudyDetails", this.metaEditForm);
      this.showMetaEditDialog = false;
    },
    confirmReinit() {
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
    commitMetaEdit() {
      this.$store.commit("setStudyDetails", this.metaEditForm);
      this.showMetaEditDialog = false;
    },
    submitMappingDetails() {
      // Initialize mappingSelection based on input values.
      if (this.numberOfVisitsInput < 1 || this.numberOfGroupsInput < 1) return;
      this.numberOfVisits = this.numberOfVisitsInput;
      this.mappingSelection = Array.from({ length: this.numberOfVisits }, () =>
        Array.from({ length: this.groups.length }, () =>
          Array(this.dataModels.length).fill(false)
        )
      );
      this.showMappingModal = false;
      this.showMappingScreen = true;
    },
    cancelMappingModal() {
      this.showMappingModal = false;
    },
    finalizeMapping() {
      // Merge the new mapping details into the studyDetails object.
      const updatedDetails = Object.assign({}, this.getStudyDetails, {
        mapping: {
          numberOfVisits: this.numberOfVisits,
          groups: this.groups,
          visitLabels: this.visitLabels,
          mappingSelection: this.mappingSelection,
          dataModels: this.dataModels,
        },
      });
      console.log("Final study details to save:", updatedDetails);
      this.$store.commit("setStudyDetails", updatedDetails);
      this.$router.push({ name: "CreateFormScratch" });
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
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-dialog {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  width: 320px;
  max-height: 80vh;
  overflow-y: auto;
}
.modal-input-group {
  margin-bottom: 10px;
}
.modal-input-group label {
  font-size: 14px;
  margin-bottom: 5px;
  display: block;
}
.modal-input-group input {
  width: 100%;
  margin-bottom: 5px;
}
.groups-container {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid #ccc;
  padding: 5px;
}
.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}
.modal-actions button {
  flex: 1;
}
.meta-edit-dialog {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.meta-edit-dialog h3 {
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
.error-input {
  border-color: red;
}
.error-text {
  color: red;
  font-size: 12px;
}
.modal.forms-confirm-dialog {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.modal.forms-confirm-dialog p {
  margin: 0;
}
.new-field-section {
  margin-top: 20px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background: #fff;
}
.new-field-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
}
.custom-field-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.field-type,
.field-name,
.field-value {
  flex: 1 1 150px;
}
.visit-label-input {
  width: 100%;
  padding: 4px;
  font-size: 14px;
  text-align: center;
  border: none;
  background: transparent;
}
</style>
