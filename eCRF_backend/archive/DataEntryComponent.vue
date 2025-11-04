<template>
  <div class="data-entry-form">
    <h3 class="form-title">
      Enter Data for Subject {{ subjectIndex + 1 }}, Visit:
      "{{ visitList[visitIndex]?.name }}"
    </h3>

    <!-- No sections assigned -->
    <p v-if="!assignedModels.length" class="no-sections">
      No sections assigned for this visit.
    </p>

    <!-- Collapsible sections -->
    <div
      v-for="(mIdx, secIdx) in assignedModels"
      :key="mIdx"
      class="section-block"
    >
      <div class="section-header" @click="toggleSection(mIdx)">
        <i :class="collapsed[mIdx] ? icons.chevronRight : icons.chevronDown" />
        <span>{{ selectedModels[mIdx].title }}</span>
      </div>

      <div v-show="!collapsed[mIdx]" class="section-content">
        <div
          v-for="(field, fIdx) in selectedModels[mIdx].fields"
          :key="fIdx"
          class="form-field"
        >
          <label :for="fieldId(mIdx, fIdx)">
            {{ field.label }}
            <span v-show="field.constraints?.required" class="required">*</span>
          </label>

          <!-- Dynamic input component -->
          <component
            :is="fieldComponent(field.type)"
            :id="fieldId(mIdx, fIdx)"
            v-model="entryData[secIdx][fIdx]"
            v-bind="fieldProps(field)"
            :disabled="isViewOnly"
            :class="{ 'view-only': isViewOnly }"
          >
            <!-- for <select> -->
            <template v-if="field.type === 'select'">
            <option value="" disabled>Select…</option>
                <option
                  v-for="opt in field.options"
                  :key="opt"
                  :value="opt"
                >{{ opt }}</option>
            </template>
          </component>

          <div v-if="errors[fieldKey(mIdx, fIdx)]" class="error-message">
            {{ errors[fieldKey(mIdx, fIdx)] }}
          </div>
        </div>
      </div>
    </div>

    <!-- Save button -->
    <div class="form-actions">
      <button
        v-if="permission === 'add'"
        @click="submitData"
        class="btn-save"
      >
        Save
      </button>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import icons from "@/assets/styles/icons";

export default {
  name: "DataEntryForm",
  props: {
    study:         { type: Object, required: true },
    subjectIndex:  { type: Number, required: true },
    visitIndex:    { type: Number, required: true },
    permission:    { type: String, default: "view" },
  },
  data() {
    return {
      entryData: [],     // [secIdx][fieldIdx]
      errors: {},
      collapsed: {},     // collapsed state per section mIdx
      icons,
    };
  },
  computed: {
    isViewOnly() {
      return this.permission !== "add";
    },
    visitList() {
      return this.study.content.study_data.visits || [];
    },
    groupIndex() {
      return 0; // blinded single‐group
    },
    selectedModels() {
      return this.study.content.study_data.selectedModels || [];
    },
    assignments() {
      return this.study.content.study_data.assignments || [];
    },
    assignedModels() {
      return this.selectedModels
        .map((_, i) => i)
        .filter(i => this.assignments[i]?.[this.visitIndex]?.[this.groupIndex]);
    },
  },
  created() {
    // init data + collapsed flags
    this.entryData = this.assignedModels.map(mIdx =>
      this.selectedModels[mIdx].fields.map(() => "")
    );
    this.assignedModels.forEach(mIdx => {
      this.collapsed[mIdx] = false
    });
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
      if (type === "select")   return "select";
      if (type === "number")   return "input";
      if (type === "date")     return "input";
      return "input"; // default text
    },
    fieldProps(field) {
      const p = {};
      if (field.placeholder) p.placeholder = field.placeholder;
      if (field.constraints) {
        if (field.constraints.required) p.required = true;
        if (field.constraints.min      != null) p.min = field.constraints.min;
        if (field.constraints.max      != null) p.max = field.constraints.max;
        if (field.type === "number")   p.step = field.constraints.step || "any";
        if (field.type === "date")     p.type = "date";
      }
      return p;
    },
    toggleSection(mIdx) {
      this.collapsed[mIdx] = !this.collapsed[mIdx];
    },
    async submitData() {
      this.errors = {};
      let valid = true;

      // validate required
      this.assignedModels.forEach((mIdx, secIdx) => {
        this.selectedModels[mIdx].fields.forEach((f, fIdx) => {
          const val = this.entryData[secIdx][fIdx];
          if (f.constraints?.required && !val) {
           this.errors[this.fieldKey(mIdx, fIdx)] = `${f.label} is required`

            valid = false;
          }
        });
      });
      if (!valid) return;

      // post
      try {
        await axios.post(
          `http://localhost:8000/api/forms/studies/${this.study.metadata.id}/data`,
          {
            study_id:      this.study.metadata.id,
            subject_index: this.subjectIndex,
            visit_index:   this.visitIndex,
            group_index:   this.groupIndex,
            data:          this.entryData,
          }
        );
        this.$emit("saved");
        alert("Data saved successfully.");
      } catch (err) {
        console.error(err);
        alert("Failed to save data.");
      }
    },
  },
};
</script>

<style scoped>
.data-entry-form {
  max-width: 800px;
  margin: 1rem auto;
  font-family: Arial, sans-serif;
}

.form-title {
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.no-sections {
  font-style: italic;
  color: #666;
}

.section-block {
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 1rem;
  background: #fafafa;
}

.section-header {
  display: flex;
  align-items: center;
  padding: 0.5rem;
  cursor: pointer;
  background: #eee;
}
.section-header i {
  margin-right: 0.5rem;
}
.section-header span {
  font-weight: bold;
}

.section-content {
  padding: 0.75rem;
}

.form-field {
  margin-bottom: 0.75rem;
}
.form-field label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
}
.form-field input,
.form-field textarea,
.form-field select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 0.95rem;
}
.form-field textarea {
  resize: vertical;
}
.form-field input.view-only,
.form-field textarea.view-only,
.form-field select.view-only {
  background: #f5f5f5;
  cursor: default;
  pointer-events: none;
}
.required {
  color: #d00;
  margin-left: 4px;
  font-size: 0.9rem;
}

.error-message {
  color: #d00;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.form-actions {
  text-align: right;
  margin-top: 1rem;
}
.btn-save {
  background: #28a745;
  color: #fff;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  font-size: 0.95rem;
  cursor: pointer;
}
.btn-save:hover {
  background: #218838;
}
</style>
