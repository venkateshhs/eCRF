<template>
  <div class="constraints-edit-modal">
    <h3>Edit Field Constraints</h3>

    <div class="constraint-field">
      <label>Required:</label>
      <input type="checkbox" v-model="localConstraints.required" />
    </div>
    <div class="constraint-field">
      <label>Readonly:</label>
      <input type="checkbox" v-model="localConstraints.readonly" />
    </div>
    <div class="constraint-field">
      <label>Placeholder:</label>
      <input type="text" v-model="localConstraints.placeholder" />
    </div>
    <div class="constraint-field">
      <label>Help Text:</label>
      <input type="text" v-model="localConstraints.helpText" />
    </div>
    <div class="constraint-field">
      <label>Default Value:</label>
      <input type="text" v-model="localConstraints.defaultValue" />
    </div>

    <!-- Text & Textarea Constraints -->
    <div v-if="currentFieldType === 'text' || currentFieldType === 'textarea'" class="constraints-fields">
      <div class="constraint-field">
        <label>Min Length:</label>
        <input type="number" v-model.number="localConstraints.minLength" />
      </div>
      <div class="constraint-field">
        <label>Max Length:</label>
        <input type="number" v-model.number="localConstraints.maxLength" />
      </div>
      <div class="constraint-field">
        <label>Pattern (Regex):</label>
        <input type="text" v-model="localConstraints.pattern" placeholder="e.g. ^[A-Za-z]+$" />
      </div>
      <div class="constraint-field">
        <label>Custom Error Message:</label>
        <input type="text" v-model="localConstraints.errorMessage" placeholder="Invalid input" />
      </div>
      <div class="constraint-field">
        <label>Transform Text:</label>
        <select v-model="localConstraints.transform">
          <option value="none">None</option>
          <option value="uppercase">Uppercase</option>
          <option value="lowercase">Lowercase</option>
          <option value="capitalize">Capitalize</option>
        </select>
      </div>
    </div>

    <!-- Number Field Constraints -->
    <div v-if="currentFieldType === 'number'" class="constraints-fields">
      <div class="constraint-field">
        <label>Min Value:</label>
        <input type="number" v-model.number="localConstraints.min" />
      </div>
      <div class="constraint-field">
        <label>Max Value:</label>
        <input type="number" v-model.number="localConstraints.max" />
      </div>
      <div class="constraint-field">
        <label>Step Size:</label>
        <input type="number" v-model.number="localConstraints.step" />
      </div>
      <div class="constraint-field">
        <label>Allow Decimals:</label>
        <input type="checkbox" v-model="localConstraints.allowDecimals" />
      </div>
    </div>

    <!-- Date Field Constraints -->
    <div v-if="currentFieldType === 'date'" class="constraints-fields">
      <div class="constraint-field">
        <label>Min Date:</label>
        <input type="date" v-model="localConstraints.minDate" />
      </div>
      <div class="constraint-field">
        <label>Max Date:</label>
        <input type="date" v-model="localConstraints.maxDate" />
      </div>
      <div class="constraint-field">
        <label>Date Format:</label>
        <input type="text" v-model="localConstraints.dateFormat" placeholder="YYYY-MM-DD" />
      </div>
    </div>

    <!-- Dropdown, Radio, Checkbox Constraints -->
    <div v-if="currentFieldType === 'select' || currentFieldType === 'radio' || currentFieldType === 'checkbox'" class="constraints-fields">
      <div class="constraint-field">
        <label>Options:</label>
        <textarea v-model="localConstraints.options" placeholder="Enter options, one per line"></textarea>
      </div>
      <div class="constraint-field" v-if="currentFieldType === 'checkbox'">
        <label>Allow Multiple Selections (Checkbox only):</label>
        <input type="checkbox" v-model="localConstraints.allowMultiple" />
      </div>
      <div class="constraint-field">
        <label>Default Selected Option:</label>
        <input type="text" v-model="localConstraints.defaultSelected" />
      </div>
    </div>

    <div class="modal-actions">
      <button @click="confirmDialog" class="btn-primary">Save</button>
      <button @click="cancelDialog" class="btn-option">Cancel</button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['currentFieldType', 'constraintsForm'],
  data() {
    return {
      localConstraints: { ...this.constraintsForm }
    };
  },
  methods: {
    confirmDialog() {
      this.$emit('updateConstraints', this.localConstraints);
    },
    cancelDialog() {
      this.$emit('closeConstraintsDialog');
    }
  },
  watch: {
    constraintsForm: {
      handler(newVal) {
        this.localConstraints = { ...newVal };
      },
      deep: true,
      immediate: true,
    }
  }
};
</script>

<style scoped>
.constraints-edit-modal {
  width: 350px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}
.constraint-field {
  margin-bottom: 10px;
}
.constraint-field label {
  font-weight: bold;
  display: block;
  margin-bottom: 3px;
}
.constraint-field input,
.constraint-field select,
.constraint-field textarea {
  width: 100%;
  padding: 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.modal-actions {
  display: flex;
  justify-content: space-between;
}
.btn-primary {
  background: #007bff;
  color: white;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-option {
  background: #ccc;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
