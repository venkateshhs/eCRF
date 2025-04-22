<template>
  <div class="create-form-container">
    <!-- Header -->
    <div class="header-container">
      <button @click="goBack" class="btn-back" title="Go Back">
        <i :class="icons.back"></i> Back
      </button>
    </div>

    <!-- Study Meta Information Section -->
    <StudyMetaInfo
      ref="studyMetaInfo"
      :studyDetails="studyDetails"
      :metaInfo="metaInfo"
      :metaInfoCollapsed="metaInfoCollapsed"
      @toggle-meta-info="toggleMetaInfo"
      @open-meta-edit-dialog="openMetaEditDialog"
      @reload-forms="reloadForms"
    />

    <!-- Main Content: Form Area & Available Fields -->
    <div class="scratch-form-content">
      <!-- Form Area -->
      <div class="form-area">
        <!-- Editable Form Name -->
        <!-- Render Current Form Sections -->
        <div
          v-for="(section, sectionIndex) in currentForm.sections"
          :key="sectionIndex"
          class="form-section"
          :class="{ active: activeSection === sectionIndex }"
          @click.self="setActiveSection(sectionIndex)"
          tabindex="0"
        >
          <div class="section-header">
            <h3>{{ section.title }}</h3>
            <div class="field-actions">
              <button
                @click.prevent="openInputDialog('Enter a new title for this section:', section.title, newVal => editSection(sectionIndex, newVal))"
                class="icon-button"
                title="Edit Section Title"
              >
                <i :class="icons.edit"></i>
              </button>
              <button @click.prevent="addNewSectionBelow(sectionIndex)" class="icon-button" title="Add New Section Below">
                <i :class="icons.add"></i>
              </button>
              <button @click.prevent="copySection(sectionIndex)" class="icon-button" title="Copy Section">
                <i :class="icons.copy"></i>
              </button>
              <button
                @click.prevent="confirmDeleteSection(sectionIndex)"
                class="icon-button"
                title="Delete Section"
              >
                <i :class="icons.delete"></i>
              </button>
              <button @click.prevent="toggleSection(sectionIndex)" class="icon-button"
                      :title="section.collapsed ? 'Expand Section' : 'Collapse Section'">
                <i :class="section.collapsed ? icons.toggleDown : icons.toggleUp"></i>
              </button>
            </div>
          </div>
          <div v-if="!section.collapsed" class="section-content">
            <div
              v-for="(field, fieldIndex) in section.fields"
              :key="fieldIndex"
              class="form-group"
            >
              <div class="field-header">
                <label v-if="field.type !== 'button'" :for="field.name">{{ field.label }}</label>
                <div class="field-actions">
                  <button
                    @click.prevent="openInputDialog('Enter new label for the field:', field.label, newVal => editField(sectionIndex, fieldIndex, newVal))"
                    class="icon-button"
                    title="Edit Field Label"
                  >
                    <i :class="icons.edit"></i>
                  </button>
                  <button
                    @click.prevent="addSimilarField(sectionIndex, fieldIndex)"
                    class="icon-button"
                    title="Add Similar Field"
                  >
                    <i :class="icons.add"></i>
                  </button>
                  <button
                    @click.prevent="removeField(sectionIndex, fieldIndex)"
                    class="icon-button"
                    title="Delete Field"
                  >
                    <i :class="icons.delete"></i>
                  </button>
                  <button
                    @click.prevent="openConstraintsDialog(sectionIndex, fieldIndex)"
                    class="icon-button"
                    title="Edit Field Constraints"
                  >
                    <i :class="icons.cog"></i>
                  </button>
                </div>
              </div>
              <div class="field-box">
                <input
                  v-if="field.type === 'text'"
                  type="text"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.constraints?.placeholder || field.placeholder"
                  :required="field.constraints?.required"
                  :readonly="field.constraints?.readonly"
                  :minlength="field.constraints?.minLength"
                  :maxlength="field.constraints?.maxLength"
                  :pattern="field.constraints?.pattern"
                />
                <textarea
                  v-if="field.type === 'textarea'"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.constraints?.placeholder || field.placeholder"
                  :required="field.constraints?.required"
                  :readonly="field.constraints?.readonly"
                  :minlength="field.constraints?.minLength"
                  :maxlength="field.constraints?.maxLength"
                  :pattern="field.constraints?.pattern"
                  :rows="field.rows"
                ></textarea>
                <input
                  v-if="field.type === 'number'"
                  type="number"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.constraints?.placeholder || field.placeholder"
                  :required="field.constraints?.required"
                  :readonly="field.constraints?.readonly"
                  :min="field.constraints?.min"
                  :max="field.constraints?.max"
                  :step="field.constraints?.step"
                />
                <input
                  v-if="field.type === 'date'"
                  type="date"
                  :id="field.name"
                  v-model="field.value"
                  :placeholder="field.constraints?.placeholder || field.placeholder"
                  :required="field.constraints?.required"
                  :readonly="field.constraints?.readonly"
                  :min="field.constraints?.minDate"
                  :max="field.constraints?.maxDate"
                />
                <select
                  v-if="field.type === 'select'"
                  :id="field.name"
                  v-model="field.value"
                  :required="field.constraints?.required"
                >
                  <option v-for="option in field.options" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select>
                <div v-if="field.type === 'checkbox'" class="checkbox-group">
                  <label v-for="(option, i) in field.options" :key="i">
                    <input
                      type="checkbox"
                      v-model="field.value"
                      :value="option"
                      :required="field.constraints?.required"
                      :readonly="field.constraints?.readonly"
                    /> {{ option }}
                  </label>
                </div>
                <div v-if="field.type === 'radio'" class="radio-group">
                  <label v-for="option in field.options" :key="option">
                    <input
                      type="radio"
                      :name="field.name"
                      v-model="field.value"
                      :value="option"
                      :required="field.constraints?.required"
                    />
                    {{ option }}
                  </label>
                </div>
                <button
                  v-if="field.type === 'button'"
                  type="button"
                  class="form-button"
                  title="Button Action"
                >
                  {{ field.label }}
                </button>
                <small v-if="field.constraints?.helpText" class="help-text">{{ field.constraints.helpText }}</small>
              </div>
            </div>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <div class="button-row">
            <button @click.prevent="addNewSection" class="btn-option">+ Add Section</button>
            <button @click.prevent="confirmClearForm" class="btn-option">Clear Form</button>
            <button @click.prevent="saveForm" class="btn-primary">Save Study</button>
            <button @click="navigateToSavedForms" class="btn-option">View Saved Study</button>
            <button @click="openDownloadDialog" class="btn-option">Download Study</button>
            <button @click="openUploadDialog" class="btn-option">Upload Study</button>
            <button @click="openPreviewDialog" class="btn-option">Preview Study</button>
          </div>
        </div>
      </div>

      <!-- Available Fields Section -->
      <div class="available-fields">
        <h2>Available Fields</h2>
        <div class="tabs">
          <button :class="{ active: activeTab === 'template' }" @click="activeTab = 'template'">Available Template</button>
          <button :class="{ active: activeTab === 'custom' }" @click="activeTab = 'custom'">Custom Fields</button>
          <button :class="{ active: activeTab === 'shacl' }" @click="activeTab = 'shacl'">SHACL Components</button>
        </div>

        <div v-if="activeTab === 'template'" class="template-fields">
          <p class="template-instruction">Click class name to view attributes</p>
          <div v-for="(model, idx) in dataModels" :key="idx" class="available-section">
            <div class="class-item clickable" @click="openModelDialog(model)">
              {{ model.title }}
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'custom'" class="custom-fields">
          <div
            v-for="(field, index) in generalFields"
            :key="index"
            class="available-field-button"
            @click="addFieldToActiveSection(field)"
          >
            <i :class="field.icon"></i> {{ field.label }}
          </div>
        </div>

        <div v-if="activeTab === 'shacl'">
          <ShaclComponents :shaclComponents="shaclComponents" />
        </div>
      </div>
    </div>

    <!-- Model Selection Dialog -->
    <div v-if="showModelDialog" class="modal-overlay">
      <div class="modal model-dialog">
        <h3>Select Properties for {{ currentModel.title }}</h3>
        <div class="model-prop-list">
          <div v-for="(prop, idx) in currentModel.fields" :key="idx" class="prop-row">
            <div class="prop-info">
              <div class="prop-name">{{ prop.label }}</div>
              <div class="prop-desc">{{ prop.placeholder }}</div>
            </div>
            <div class="prop-check">
              <input type="checkbox" v-model="selectedProps[idx]" />
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="takeoverModel" class="btn-primary">Takeover</button>
          <button @click="showModelDialog = false" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Preview Dialog Modal -->
    <div v-if="showPreviewDialog" class="modal-overlay">
      <div class="modal preview-modal">
        <div class="preview-header">
          <button @click="prevPreview" :disabled="previewFormIndex === 0">
            <i :class="icons.prev"></i>
          </button>
          <span>Form {{ previewFormIndex + 1 }} of {{ forms.length }}</span>
          <button @click="nextPreview" :disabled="previewFormIndex === forms.length - 1">
            <i :class="icons.next"></i>
          </button>
        </div>
        <div class="preview-content">
          <FormPreview :form="forms[previewFormIndex]" />
        </div>
        <div class="modal-actions">
          <button @click="closePreviewDialog" class="btn-primary">Close</button>
        </div>
      </div>
    </div>

    <!-- Save Dialog Modal -->
    <div v-if="showSaveDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ saveDialogMessage }}</p>
        <button @click="closeSaveDialog" class="btn-primary">OK</button>
      </div>
    </div>

    <!-- Generic Dialog Modal -->
    <div v-if="showGenericDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ genericDialogMessage }}</p>
        <button @click="closeGenericDialog" class="btn-primary">OK</button>
      </div>
    </div>

    <!-- Input Dialog Modal -->
    <div v-if="showInputDialog" class="modal-overlay">
      <div class="modal input-dialog-modal">
        <p>{{ inputDialogMessage }}</p>
        <input type="text" v-model="inputDialogValue" class="input-dialog-field" />
        <div class="modal-actions">
          <button @click="confirmInputDialog" class="btn-primary">Save</button>
          <button @click="cancelInputDialog" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Confirm Dialog Modal -->
    <div v-if="showConfirmDialog" class="modal-overlay">
      <div class="modal">
        <p>{{ confirmDialogMessage }}</p>
        <div class="modal-actions">
          <button @click="confirmDialogYes" class="btn-primary">Yes</button>
          <button @click="closeConfirmDialog" class="btn-option">No</button>
        </div>
      </div>
    </div>

    <!-- Constraints Edit Dialog Modal -->
    <div v-if="showConstraintsDialog" class="modal-overlay">
      <div class="modal constraints-edit-modal">
        <FieldConstraintsDialog
          :currentFieldType="currentFieldType"
          :constraintsForm="constraintsForm"
          @updateConstraints="confirmConstraintsDialog"
          @closeConstraintsDialog="cancelConstraintsDialog"
        />
      </div>
    </div>

    <!-- Download Dialog Modal -->
    <div v-if="showDownloadDialog" class="modal-overlay">
      <div class="modal">
        <p>Select format to download the form:</p>
        <div class="modal-actions">
          <button @click="downloadFormData('json')" class="btn-primary">JSON</button>
          <button @click="downloadFormData('yaml')" class="btn-primary">YAML</button>
        </div>
        <div class="modal-actions">
          <button @click="closeDownloadDialog" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Upload Dialog Modal -->
    <div v-if="showUploadDialog" class="modal-overlay">
      <div class="modal">
        <p>Select a YAML/JSON file to upload:</p>
        <input type="file" @change="handleFileChange" accept=".json,.yaml,.yml" />
        <div class="modal-actions">
          <button @click="closeUploadDialog" class="btn-option">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import yaml from "js-yaml";
import icons from "@/assets/styles/icons";
import StudyMetaInfo from "./StudyMetaInfo.vue";
import ShaclComponents from "./ShaclComponents.vue";
import FieldConstraintsDialog from "./FieldConstraintsDialog.vue";
import FormPreview from "./FormPreview.vue";

export default {
  name: "ScratchFormComponent",
  components: {
    StudyMetaInfo,
    ShaclComponents,
    FieldConstraintsDialog,
    FormPreview,
  },
  data() {
    return {
      forms: [],
      currentFormIndex: 0,
      totalForms: 1,
      activeSection: 0,
      activeTab: "template",
      generalFields: [],
      dataModels: [],
      showModelDialog: false,
      currentModel: null,
      selectedProps: [],
      showSaveDialog: false,
      saveDialogMessage: "",
      showGenericDialog: false,
      genericDialogMessage: "",
      genericDialogCallback: null,
      showInputDialog: false,
      inputDialogMessage: "",
      inputDialogValue: "",
      inputDialogCallback: null,
      showConfirmDialog: false,
      confirmDialogMessage: "",
      confirmDialogCallback: null,
      showConstraintsDialog: false,
      constraintsForm: {},
      currentFieldType: "",
      currentFieldIndices: {},
      showDownloadDialog: false,
      showUploadDialog: false,
      showPreviewDialog: false,
      previewFormIndex: 0,
      metaInfo: {
        numberOfSubjects: null,
        numberOfVisits: null,
        studyMetaDescription: ""
      },
      metaInfoCollapsed: true,
      studyDetails: {}
    };
  },
  computed: {
    token() {
      return this.$store.state.token;
    },
    currentForm() {
      return this.forms[this.currentFormIndex] || { formName: "", sections: [] };
    },
    formName: {
      get() {
        return this.currentForm.formName;
      },
      set(value) {
        this.forms[this.currentFormIndex].formName = value;
      },
    },
    icons() {
      return icons;
    },
  },
  watch: {
    forms: {
      handler(newForms) {
        localStorage.setItem("scratchForms", JSON.stringify(newForms));
      },
      deep: true,
    }
  },
  async mounted() {
    const details = this.$store.state.studyDetails || {};
    this.studyDetails = details;
    this.totalForms = details.numberOfForms || 1;
    if (details.metaInfo) {
      this.metaInfo = details.metaInfo;
    }
    const stored = localStorage.getItem("scratchForms");
    if (stored) {
      this.forms = JSON.parse(stored);
      this.totalForms = this.forms.length;
    } else {
      for (let i = 0; i < this.totalForms; i++) {
        this.forms.push({
          formName: `Form${i + 1}`,
          sections: [{ title: "Default Section", fields: [], collapsed: false }],
        });
      }
    }

    try {
      const gen = await axios.get("http://127.0.0.1:8000/forms/available-fields");
      this.generalFields = gen.data;
    } catch (e) {
      console.error("Error loading general fields", e);
    }

    await this.loadDataModels();
  },
  methods: {
    goBack() { this.$router.back(); },
    navigateToSavedForms() { this.$router.push("/saved-forms"); },
    async saveForm() {
      if (!this.token) {
        this.openGenericDialog("Authentication error: No token found. Please log in again.", () => {
          this.$router.push("/login");
        });
        return;
      }
      const payload = {
        study_metadata: {
          created_by: this.$store.state.user?.id || 0,
          study_name: this.studyDetails.name || "Untitled Study",
          study_description: this.studyDetails.description || ""
        },
        study_content: {
          study_data: {
            meta_info: {
              name: this.studyDetails.name || "",
              description: this.studyDetails.description || "",
              numberOfForms: this.studyDetails.numberOfForms || 1,
              numberOfSubjects: this.studyDetails.metaInfo?.numberOfSubjects,
              studyType: this.studyDetails.studyType,
              numberOfVisits: this.studyDetails.metaInfo?.numberOfVisits,
              studyMetaDescription: this.studyDetails.metaInfo?.studyMetaDescription || "",
              customFields: this.studyDetails.customFields || [],
              metaCustomFields: this.studyDetails.metaCustomFields || []
            },
            forms: this.forms.map(form => ({
              form_name: form.formName,
              sections: form.sections
            }))
          }
        }
      };
      try {
        let response;
        if (this.studyDetails.id) {
          response = await axios.put(
            `http://127.0.0.1:8000/forms/studies/${this.studyDetails.id}`,
            payload,
            { headers: { "Content-Type": "application/json", Authorization: `Bearer ${this.token}` } }
          );
          this.openSaveDialog(`Study "${response.data.metadata.study_name}" updated successfully!`);
        } else {
          response = await axios.post(
            "http://127.0.0.1:8000/forms/studies/",
            payload,
            { headers: { "Content-Type": "application/json", Authorization: `Bearer ${this.token}` } }
          );
          this.openSaveDialog(`Study "${response.data.metadata.study_name}" saved successfully!`);
        }
      } catch (error) {
        console.error("Error saving study:", error.response?.data || error.message);
        this.openGenericDialog("Failed to save study. Please try again.");
      }
    },
    openSaveDialog(message) { this.saveDialogMessage = message; this.showSaveDialog = true; },
    closeSaveDialog() {
      this.showSaveDialog = false;
      if (this.currentFormIndex < this.totalForms - 1) this.currentFormIndex++;
      else this.openGenericDialog("All forms have been saved.");
    },
    openGenericDialog(message, callback=null) {
      this.genericDialogMessage = message; this.genericDialogCallback = callback; this.showGenericDialog = true;
    },
    closeGenericDialog() {
      this.showGenericDialog = false;
      if (this.genericDialogCallback) { this.genericDialogCallback(); this.genericDialogCallback = null; }
    },
    openInputDialog(message, defaultValue, callback) {
      this.inputDialogMessage = message; this.inputDialogValue = defaultValue; this.inputDialogCallback = callback; this.showInputDialog = true;
    },
    confirmInputDialog() {
      this.inputDialogCallback?.(this.inputDialogValue);
      this.showInputDialog = false;
    },
    cancelInputDialog() {
      this.showInputDialog = false;
    },
    openConfirmDialog(message, callback) {
      this.confirmDialogMessage = message; this.confirmDialogCallback = callback; this.showConfirmDialog = true;
    },
    confirmDialogYes() {
      this.confirmDialogCallback?.(); this.closeConfirmDialog();
    },
    closeConfirmDialog() {
      this.showConfirmDialog = false;
    },
    async loadDataModels() {
      try {
        const res = await fetch("/study_schema.yaml");
        const doc = yaml.load(await res.text());
        this.dataModels = Object.entries(doc.classes)
          .filter(([n]) => n !== "Study")
          .map(([n, cls]) => ({
            title: n,
            fields: Object.entries(cls.attributes).map(([attr, def]) => {
              let type="text", r=(def.range||"").toLowerCase();
              if(r==="date"||r==="datetime") type="date";
              else if(["integer","decimal"].includes(r)) type="number";
              if(def.enum) type="select";
              return { name:`${attr}_${Date.now()}`, label:attr, type, options:def.enum||[], placeholder:def.description||"", value:"", constraints:{required:!!def.required} };
            })
          }));
      } catch(err){ console.error("Failed to load data models:",err); }
    },
    openModelDialog(model) {
      this.currentModel=model;
      this.selectedProps=model.fields.map(()=>false);
      this.showModelDialog=true;
    },
    takeoverModel() {
      const chosen=this.currentModel.fields.filter((_,i)=>this.selectedProps[i]).map(f=>({...f}));
      const newSection={ title:this.currentModel.title, collapsed:false, fields:chosen };
      const idx=this.activeSection;
      this.currentForm.sections.splice(idx+1,0,newSection);
      this.activeSection=idx+1;
      this.showModelDialog=false;
    },
    prevForm(){ if(this.currentFormIndex>0){ this.currentFormIndex--; this.activeSection=0; } },
    nextForm(){ if(this.currentFormIndex<this.totalForms-1){ this.currentFormIndex++; this.activeSection=0; } },
    toggleSection(i){ this.currentForm.sections.forEach((s,idx)=>{ s.collapsed = idx!==i ? true : !s.collapsed; if(!s.collapsed) this.activeSection=i; }); },
    setActiveSection(i){ this.activeSection=i; },
    addFieldToActiveSection(field){
      const section=this.currentForm.sections[this.activeSection];
      if(section.collapsed) this.toggleSection(this.activeSection);
      section.fields.push({...field});
    },
    addNewSection(){ this.currentForm.sections.push({title:`New Section ${this.currentForm.sections.length+1}`,fields:[],collapsed:false}); this.toggleSection(this.currentForm.sections.length-1); },
    addNewSectionBelow(i){ this.currentForm.sections.splice(i+1,0,{title:`New Section ${i+2}`,fields:[],collapsed:false}); this.toggleSection(i+1); },
    confirmDeleteSection(i){
      if(this.currentForm.sections.length===1&&this.currentForm.sections[0].title==="Default Section"){
        this.openGenericDialog("Default section cannot be deleted."); return;
      }
      this.openConfirmDialog("Are you sure you want to delete this section?",()=>{
        this.currentForm.sections.splice(i,1);
        if(this.activeSection>=i) this.activeSection=Math.max(0,this.activeSection-1);
        this.toggleSection(this.activeSection);
      });
    },
    confirmClearForm(){
      this.openConfirmDialog("Are you sure you want to clear the form?",()=>{
        this.currentForm.sections=[{title:"Default Section",fields:[],collapsed:false}];
        this.activeSection=0;
      });
    },
    editSection(i,v){ if(v) this.currentForm.sections[i].title=v; },
    editField(si,fi,v){ if(v) this.currentForm.sections[si].fields[fi].label=v; },
    copySection(i){
      const s=this.currentForm.sections[i];
      const copy=JSON.parse(JSON.stringify(s));
      copy.title=`${s.title} (Copy)`;
      copy.fields=s.fields.map(f=>({...f,name:`${f.name}_copy_${Date.now()}`}));
      copy.collapsed=true;
      this.currentForm.sections.splice(i+1,0,copy);
      this.toggleSection(i+1);
    },
    addSimilarField(si,fi){
      const f=this.currentForm.sections[si].fields[fi];
      const nf={...f,name:`${f.type}_${Date.now()}`};
      this.currentForm.sections[si].fields.splice(fi+1,0,nf);
    },
    removeField(si,fi){ this.currentForm.sections[si].fields.splice(fi,1); },
    openConstraintsDialog(si,fi){
      const f=this.currentForm.sections[si].fields[fi];
      this.currentFieldIndices={sectionIndex:si,fieldIndex:fi};
      this.currentFieldType=f.type;
      this.constraintsForm=f.constraints?{...f.constraints}:(f.type==="number"?{min:null,max:null,maxDigits:null}:(["text","textarea"].includes(f.type)?{minLength:null,maxLength:null,pattern:"",required:false}:{}));
      this.showConstraintsDialog=true;
    },
    confirmConstraintsDialog(c){
      const {sectionIndex,fieldIndex}=this.currentFieldIndices;
      const f=this.currentForm.sections[sectionIndex].fields[fieldIndex];
      f.constraints={...c};
      if(["text","textarea"].includes(f.type)){
        f.placeholder=c.placeholder||f.placeholder; f.required=c.required||false; f.readonly=c.readonly||false;
        f.minLength=c.minLength; f.maxLength=c.maxLength; f.pattern=c.pattern;
      }
      if(f.type==="number"){
        f.placeholder=c.placeholder||f.placeholder; f.required=c.required||false; f.readonly=c.readonly||false;
        f.min=c.min; f.max=c.max; f.step=c.step;
      }
      if(f.type==="date"){
        f.placeholder=c.placeholder||f.placeholder; f.required=c.required||false; f.readonly=c.readonly||false;
        f.minDate=c.minDate; f.maxDate=c.maxDate;
      }
      if(["select","radio","checkbox"].includes(f.type)){
        f.required=c.required||false;
      }
      if(c.defaultValue!==undefined) f.value=c.defaultValue;
      this.showConstraintsDialog=false;
    },
    cancelConstraintsDialog(){ this.showConstraintsDialog=false; },
    openDownloadDialog(){ this.showDownloadDialog=true; },
    closeDownloadDialog(){ this.showDownloadDialog=false; },
    downloadFormData(format){
      const data={studyDetails:this.studyDetails,forms:this.forms};
      let str,name; const pref=this.studyDetails.name?.trim().replace(/\s+/g,"_")||"formData";
      if(format==="json"){str=JSON.stringify(data,null,2);name=`${pref}.json`;}
      else{try{str=yaml.dump(data);name=`${pref}.yaml`;}catch{str="Error";name="formData.txt";}}
      const b=new Blob([str],{type:"text/plain"}),url=URL.createObjectURL(b),a=document.createElement("a");
      a.href=url; a.download=name; a.click(); URL.revokeObjectURL(url); this.showDownloadDialog=false;
    },
    openUploadDialog(){ this.showUploadDialog=true; },
    closeUploadDialog(){ this.showUploadDialog=false; },
    handleFileChange(e){
      const f=e.target.files[0]; if(!f)return; const r=new FileReader();
      r.onload=evt=>{
        let pd,ct=evt.target.result.trim();
        try{pd=JSON.parse(ct);}catch{try{pd=yaml.load(ct);}catch{return this.openGenericDialog("Invalid file.");}}
        if(pd.studyDetails){this.studyDetails=pd.studyDetails;this.$store.commit("setStudyDetails",pd.studyDetails);}
        if(pd.metaInfo) this.metaInfo=pd.metaInfo;
        if(pd.forms){this.forms=pd.forms;this.totalForms=pd.forms.length;this.currentFormIndex=0;this.activeSection=0;}
      };
      r.readAsText(f); this.closeUploadDialog();
    },
    openPreviewDialog(){ this.previewFormIndex=this.currentFormIndex; this.showPreviewDialog=true; },
    closePreviewDialog(){ this.showPreviewDialog=false; },
    prevPreview(){ if(this.previewFormIndex>0)this.previewFormIndex--; },
    nextPreview(){ if(this.previewFormIndex<this.forms.length-1)this.previewFormIndex++; }
  },
};
</script>

<style lang="scss" scoped>
@import "@/assets/styles/_base.scss";

.create-form-container {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  background-color: $light-background;
}
.header-container {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}
.btn-back {
  @include button-reset;
  font-size: 16px;
  color: $text-color;
}
.scratch-form-content {
  display: flex;
  gap: 20px;
}
.form-area {
  flex: 1;
  background: white;
  padding: 20px;
  border: 1px solid $border-color;
  border-radius: 8px;
  min-width: 600px;
}
.form-heading-container {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}
.heading-input {
  font-size: 22px;
  font-weight: 500;
  text-align: center;
  border-bottom: 1px solid $border-color;
  outline: none;
  width: 100%;
  max-width: 400px;
}
.form-section {
  padding: 15px;
  border-bottom: 1px solid $border-color;
  &.active {
    background: #e7f3ff;
    border-left: 3px solid $text-color;
  }
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.field-actions { display: flex; gap: 10px; }
.field-box { margin-top: 10px; }
input,textarea,select {
  width: 100%; padding: 8px; border: 1px solid $border-color; border-radius: 5px; margin-top: 5px;
}
.form-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}
.button-row { display: flex; gap: 15px; width: 100%; }
.btn-option {
  background: $secondary-color;
  padding: $button-padding;
  border: 1px solid $border-color;
  border-radius: $button-border-radius;
  cursor: pointer;
  flex: 1;
}
.btn-primary {
  background: $primary-color; color:white;
  padding: $button-padding;
  border-radius: $button-border-radius;
  flex: 1; cursor: pointer;
}
.available-fields {
  width: 300px;
  background: white; padding: 20px;
  border: 1px solid $border-color; border-radius: 8px;
  max-height: calc(100vh - 60px); overflow-y: auto;
}
.tabs {
  display: flex; gap: 10px; margin-bottom: 15px;
}
.tabs button {
  padding: 10px; border: 1px solid $border-color; background: $secondary-color; border-radius: 4px; flex:1;
  cursor: pointer;
}
.tabs button.active {
  background: $primary-color; color: white; border: none;
}
.template-instruction {
  font-style: italic; margin-bottom: 10px;
}
.template-fields, .custom-fields, .shacl { padding: 10px 0; }
.class-item.clickable {
  cursor: pointer; padding: 5px 0; font-weight: bold;
}
.available-field-button {
  display:flex; align-items:center; gap:10px;
  padding:10px; margin-bottom:10px;
  background:#f9f9f9; border:1px solid $border-color; border-radius:4px;
  cursor:pointer;
}
.model-dialog { width: 400px; }
.model-prop-list {
  max-height: 300px; overflow-y: auto; margin-bottom: 15px;
}
.prop-row {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
}
.prop-info {
  flex: 1;
}
.prop-name {
  font-weight: bold;
}
.prop-desc {
  font-size: 0.9em; color: #666;
}
.prop-check {
  margin-left: 10px;
}
.modal-overlay {
  position: fixed; top:0; left:0; right:0; bottom:0;
  background: rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center;
}
.modal {
  background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.modal-actions {
  display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;
}
.preview-modal {
  display:flex; flex-direction:column; width:500px; height:80vh; overflow:hidden;
}
.preview-header {
  display:flex; justify-content:space-between; align-items:center;
  background:#f2f3f4; padding:10px;
}
.preview-content {
  flex:1; overflow-y:auto; padding:10px; background:white;
}
@media (max-width: 768px) {
  .scratch-form-content { flex-direction: column; }
  .form-area, .available-fields { width:100%; }
}
</style>
