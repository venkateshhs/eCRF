<template>
  <div class="data-entry-form">
    <h3>
      Enter Data for Subject {{ subjectIndex + 1 }}, Visit:
      "{{ visitList[visitIndex]?.name }}"
    </h3>

    <div v-if="!assignedModels.length">
      <p>No sections assigned for this visit.</p>
    </div>

    <div v-else>
      <div v-for="(mIdx, secIdx) in assignedModels" :key="mIdx" class="section-block">
        <h4>{{ selectedModels[mIdx].title }}</h4>
        <div v-for="(field, fIdx) in selectedModels[mIdx].fields" :key="fIdx" class="form-field">
          <label :for="fieldId(mIdx, fIdx)">
            {{ field.label }}
            <span v-if="field.constraints?.required" class="required">*</span>
          </label>
          <component
            :is="fieldComponent(field.type)"
            :id="fieldId(mIdx, fIdx)"
            v-model="entryData[secIdx][fIdx]"
            v-bind="fieldProps(field)"
            :readonly="permission === 'view'"
          ></component>
          <div v-if="errors[fieldKey(mIdx,fIdx)]" class="error-message">
            {{ errors[fieldKey(mIdx,fIdx)] }}
          </div>
        </div>
      </div>
      <div class="form-actions" v-if="permission === 'add'">
        <button @click="submitData" class="btn-save">Save</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: "DataEntryForm",
  props: {
    study:        { type: Object, required: true },
    subjectIndex: { type: Number, required: true },
    visitIndex:   { type: Number, required: true },
    permission:   { type: String, default: "view" },
  },
  data() {
    return {
      entryData: [],   // [ sectionIdx ][ fieldIdx ]
      errors:    {}
    };
  },
  computed: {
    visitList() {
      return this.study.content.study_data.visits || [];
    },
    selectedModels() {
      return this.study.content.study_data.selectedModels || [];
    },
    assignments() {
      return this.study.content.study_data.assignments || [];
    },
    // find which sections apply for this visit
    assignedModels() {
      const gIdx = 0; // always group 0 in shared
      return this.selectedModels
        .map((_, idx) => idx)
        .filter(idx => this.assignments[idx]?.[this.visitIndex]?.[gIdx]);
    }
  },
  created() {
    // initialize entryData for each assigned section
    this.entryData = this.assignedModels.map(
      mIdx => this.selectedModels[mIdx].fields.map(() => "")
    );
  },
  methods: {
    fieldId(mIdx, fIdx) {
      return `s${this.subjectIndex}_v${this.visitIndex}_m${mIdx}_f${fIdx}`;
    },
    fieldKey(mIdx, fIdx) {
      return [this.subjectIndex, this.visitIndex, mIdx, fIdx].join("-");
    },
    fieldComponent(type) {
      if (type === "textarea") return "textarea";
      if (type === "number")   return "input";
      if (type === "date")     return "input";
      if (type === "select")   return "select";
      return "input";
    },
    fieldProps(field) {
      const p = {};
      if (field.type === "number") p.type = "number";
      if (field.type === "date")   p.type = "date";
      if (field.type === "select") p.options = field.options;
      if (field.placeholder)       p.placeholder = field.placeholder;
      if (field.constraints?.required) p.required = true;
      if (field.constraints?.min != null) p.min = field.constraints.min;
      if (field.constraints?.max != null) p.max = field.constraints.max;
      return p;
    },
    async submitData() {
      this.errors = {};
      // simple required‐field validation
      let ok = true;
      this.assignedModels.forEach((mIdx, secIdx) => {
        this.selectedModels[mIdx].fields.forEach((f, fIdx) => {
          if (f.constraints?.required && !this.entryData[secIdx][fIdx]) {
            this.$set(this.errors, this.fieldKey(mIdx,fIdx), `${f.label} is required`);
            ok = false;
          }
        });
      });
      if (!ok) return;

      try {
        await axios.post(
          `http://localhost:8000/forms/studies/${this.study.metadata.id}/data`,
          {
            study_id:      this.study.metadata.id,
            subject_index: this.subjectIndex,
            visit_index:   this.visitIndex,
            group_index:   0,
            data:          this.entryData,
          },
          { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
        );
        alert("Saved successfully.");
      } catch (err) {
        console.error(err);
        alert("Save failed.");
      }
    }
  }
};
</script>



<style scoped>
.data-entry-form {
  margin-top: 20px;
}
.section-block {
  padding: 12px;
  border: 1px solid #ddd;
  margin-bottom: 16px;
  background: #fafafa;
}
.form-field {
  margin-bottom: 12px;
}
.required {
  color: red;
  margin-left: 4px;
}
.error-message {
  color: red;
  font-size: 12px;
}
.btn-save {
  background: #28a745;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-save:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
