<template>
  <div class="form-preview">
    <h2 class="form-title">{{ form.formName }}</h2>
    <div
      v-for="(section, sIndex) in form.sections"
      :key="sIndex"
      class="preview-section"
    >
      <div class="section-header">
        <h3 class="section-title">{{ section.title }}</h3>
        <button class="toggle-section-btn" @click="toggleSection(sIndex)">
          <i :class="expandedSections[sIndex] ? icons.toggleUp : icons.toggleDown"></i>
        </button>
      </div>
      <div class="fields-container" v-show="expandedSections[sIndex]">
        <div v-for="(field, fIndex) in section.fields" :key="fIndex" class="preview-field">
          <label class="field-label">{{ field.label }}</label>
          <div class="field-value">
            <!-- Text / Textarea Field -->
            <template v-if="field.type === 'text' || field.type === 'textarea'">
              <input
                type="text"
                :value="field.value || field.placeholder || ''"
                disabled
              />
            </template>
            <!-- Number Field -->
            <template v-else-if="field.type === 'number'">
              <input
                type="number"
                :value="field.value || field.placeholder || ''"
                disabled
              />
            </template>
            <!-- Date Field -->
            <template v-else-if="field.type === 'date'">
              <input
                type="date"
                :value="field.value || field.placeholder || ''"
                disabled
              />
            </template>
            <!-- Select Field -->
            <template v-else-if="field.type === 'select'">
              <select disabled>
                <option :selected="true">{{ field.value || '---' }}</option>
              </select>
            </template>
            <!-- Checkbox Field -->
            <template v-else-if="field.type === 'checkbox'">
              <div class="checkbox-values">
                <span
                  v-for="(item, i) in (Array.isArray(field.value) ? field.value : [field.value])"
                  :key="i"
                >
                  {{ item || '---' }}
                </span>
              </div>
            </template>
            <!-- Radio Field -->
            <template v-else-if="field.type === 'radio'">
              <span>{{ field.value || '---' }}</span>
            </template>
            <!-- Button Field -->
            <template v-else-if="field.type === 'button'">
              <button disabled>{{ field.label }}</button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import icons from "@/assets/styles/icons";

export default {
  name: "FormPreview",
  props: {
    form: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      expandedSections: [],
    };
  },
  computed: {
    icons() {
      return icons;
    },
  },
  created() {
    this.initializeSections();
  },
  watch: {
    form: {
      handler() {
        this.initializeSections();
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    initializeSections() {
      this.expandedSections = this.form.sections.map(() => true);
    },
    toggleSection(index) {
      this.expandedSections[index] = !this.expandedSections[index];
    },
  },
};
</script>

<style scoped>
.form-preview {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
.form-title {
  text-align: center;
  margin-bottom: 20px;
  font-size: 24px;
}
.preview-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 6px;
  background: #f9f9f9;
  transition: all 0.3s ease;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.section-title {
  font-size: 18px;
  margin: 0;
}
.toggle-section-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 18px;
  color: black; /* Ensure the icon color is black */
}
.fields-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.preview-field {
  display: flex;
  flex-direction: column;
}
.field-label {
  font-weight: bold;
  margin-bottom: 5px;
}
.field-value input,
.field-value select,
.field-value button {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #eee;
  color: #333;
}
.field-value input:disabled,
.field-value select:disabled,
.field-value button:disabled {
  background: #f5f5f5;
  color: #777;
}
.checkbox-values {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  font-size: 14px;
}
</style>
