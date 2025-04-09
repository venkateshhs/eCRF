<template>
  <div class="study-creation-container">
    <h1>Study Management</h1>
    <!-- Study creation form visible when mapping screen is not active -->
    <div v-if="!showMappingScreen" class="new-study-form">
      <h2>Create a New Study</h2>
      <!-- Render fields from the TTL StudyShape -->
      <div
        v-for="(field, index) in studySchemaProperties"
        :key="index"
        class="schema-field-row"
      >
        <label :for="field.field">
          {{ field.label }}<span v-if="field.required" class="required">*</span>
        </label>
        <!-- Render textarea -->
        <template v-if="field.type === 'textarea'">
          <textarea
            :id="field.field"
            v-model="customStudy[field.field]"
            :placeholder="field.placeholder"
            :required="field.required"
          ></textarea>
        </template>
        <!-- Render select (dropdown) -->
        <template v-else-if="field.type === 'select'">
          <select
            :id="field.field"
            v-model="customStudy[field.field]"
            :required="field.required"
          >
            <option value="">{{ field.placeholder }}</option>
            <option
              v-for="option in field.options"
              :key="option"
              :value="option"
            >
              {{ option }}
            </option>
          </select>
        </template>
        <!-- Render date input -->
        <template v-else-if="field.type === 'date'">
          <input
            type="date"
            :id="field.field"
            v-model="customStudy[field.field]"
            :placeholder="field.placeholder"
            :required="field.required"
          />
        </template>
        <!-- Render text input as default -->
        <template v-else>
          <input
            type="text"
            :id="field.field"
            v-model="customStudy[field.field]"
            :placeholder="field.placeholder"
            :required="field.required"
          />
        </template>
        <small
          v-if="showErrors && field.required && !customStudy[field.field]"
          class="error-text"
        >
          {{ field.placeholder }} is required.
        </small>
      </div>

      <!-- Custom Field Generator -->
      <div class="custom-fields-section" v-if="customFields.length">
        <h3>Custom Fields</h3>
        <div
          v-for="(field, index) in customFields"
          :key="index"
          class="custom-field-row"
        >
          <div class="custom-field-display">
            <label class="added-field-label">{{ field.fieldName }}</label>
            <div class="added-field-value">
              <template v-if="field.fieldType === 'date'">
                <input type="date" v-model="field.fieldValue" class="field-value" />
              </template>
              <template v-else-if="field.fieldType === 'number'">
                <input type="number" v-model="field.fieldValue" class="field-value" />
              </template>
              <template v-else-if="field.fieldType === 'area'">
                <textarea v-model="field.fieldValue" class="field-value"></textarea>
              </template>
              <template v-else>
                <input type="text" v-model="field.fieldValue" class="field-value" />
              </template>
            </div>
          </div>
          <button type="button" @click="removeField(index)" class="remove-btn">
            Remove
          </button>
        </div>
      </div>

      <!-- Custom Field Editor Toggle -->
      <div class="meta-toggle-container">
        <label class="switch">
          <input type="checkbox" v-model="showCustomFieldEditor" />
          <span class="slider"></span>
        </label>
        <span class="toggle-label">Show Custom Field Editor</span>
      </div>
      <div class="new-field-section" v-if="showCustomFieldEditor">
        <h3>Add New Custom Field</h3>
        <div class="custom-field-inputs">
          <select v-model="newField.fieldType" class="field-type">
            <option value="">Select Field Type</option>
            <option value="text">Text</option>
            <option value="number">Number</option>
            <option value="date">Date</option>
            <option value="area">Area</option>
          </select>
          <input
            type="text"
            v-model="newField.fieldName"
            placeholder="Field Name"
            class="field-name"
          />
          <template v-if="newField.fieldType === 'date'">
            <input type="date" v-model="newField.fieldValue" class="field-value" />
          </template>
          <template v-else-if="newField.fieldType === 'number'">
            <input type="number" v-model="newField.fieldValue" class="field-value" />
          </template>
          <template v-else-if="newField.fieldType === 'area'">
            <textarea
              v-model="newField.fieldValue"
              placeholder="Field Value"
              class="field-value"
            ></textarea>
          </template>
          <template v-else>
            <input
              type="text"
              v-model="newField.fieldValue"
              placeholder="Field Value"
              class="field-value"
            />
          </template>
          <button type="button" @click="addField" class="add-btn">
            Add Field
          </button>
        </div>
      </div>

      <!-- Form Action Buttons -->
      <div class="form-actions">
        <button @click="validateAndProceed" class="btn-option">
          Proceed
        </button>
        <button @click="resetForm" class="btn-option">
          Cancel
        </button>
      </div>
    </div>

    <!-- Mapping Screen -->
    <div v-if="showMappingScreen" class="mapping-screen">
      <h2>Mapping Data Models to Visits</h2>
      <!-- Container with fixed dimensions and scroll for both axes -->
      <div class="table-container">
        <table class="mapping-table">
          <thead>
            <tr>
              <th>Data Model / Visit</th>
              <th v-for="(label, index) in visitLabels" :key="index">
                <!-- Editable visit label input -->
                <input
                  type="text"
                  v-model="visitLabels[index]"
                  class="visit-label-input"
                />
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(dataModel, rowIndex) in dataModels" :key="dataModel">
              <td class="sticky-col">{{ dataModel }}</td>
              <td
                v-for="n in numberOfVisits"
                :key="n"
                class="cell"
                @click="toggleMapping(rowIndex, n - 1)"
              >
                <span v-if="mappingSelection[rowIndex][n - 1]" class="tick-mark">
                  ✓
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <button @click="finalizeMapping" class="btn-option">Finalize</button>
    </div>

    <!-- Modal Dialog for Number of Visits -->
    <div v-if="showVisitDialog" class="modal-overlay">
      <div class="modal-dialog">
        <h3>How many visits are planned?</h3>
        <input type="number" v-model.number="numberOfVisitsInput" min="1" />
        <div class="modal-actions">
          <button @click="submitNumberOfVisits">Submit</button>
          <button @click="cancelVisitDialog">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import * as $rdf from "rdflib";

export default {
  name: "StudyCreationComponent",
  setup() {
    const router = useRouter();
    // Study form states
    const studySchemaProperties = ref([]);
    const customStudy = ref({});
    const customFields = ref([]);
    const newField = ref({ fieldType: "", fieldName: "", fieldValue: "" });
    const showCustomFieldEditor = ref(false);
    const showErrors = ref(false);

    // Visit dialog and mapping states
    const showVisitDialog = ref(false);
    const numberOfVisitsInput = ref(1);
    const numberOfVisits = ref(0);
    const showMappingScreen = ref(false);
    const dataModels = ref(["Data Model 1", "Data Model 2", "Data Model 3"]);
    const mappingSelection = ref([]);
    const visitLabels = ref([]);

    // RDF Namespaces and StudyShape IRI
    const SH = $rdf.Namespace("http://www.w3.org/ns/shacl#");
    const DLSCHEMAS = $rdf.Namespace("https://concepts.datalad.org/s/");
    const studyShapeIRI = $rdf.sym(DLSCHEMAS("StudyShape").value);

    // Helper: Traverse an RDF list using rdf:first and rdf:rest
    function getCollectionElements(head, store) {
      const RDF = $rdf.Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#");
      let elements = [];
      let current = head;
      while (current && current.value !== RDF("nil").value) {
        const first = store.any(current, RDF("first"));
        if (first) {
          elements.push(first.value);
        } else {
          break;
        }
        current = store.any(current, RDF("rest"));
      }
      return elements;
    }

    function parseTTL(ttlText) {
      return new Promise((resolve, reject) => {
        const store = $rdf.graph();
        const contentType = "text/turtle";
        try {
          $rdf.parse(ttlText, store, DLSCHEMAS("").value, contentType);
          resolve(store);
        } catch (err) {
          reject(err);
        }
      });
    }

    async function loadStudySchema() {
      try {
        console.log("Fetching TTL file from /study_schema.ttl");
        const response = await fetch("/study_schema.ttl");
        const ttlText = await response.text();
        console.log("TTL file loaded. Content:\n", ttlText);
        const store = await parseTTL(ttlText);
        console.log("RDF store created. Total triples:", store.length);
        const propertyNodes = store.each(studyShapeIRI, SH("property"));
        console.log("Found", propertyNodes.length, "property nodes for StudyShape.");
        const properties = [];
        propertyNodes.forEach((propNode, index) => {
          const pathTerm = store.any(propNode, SH("path"));
          if (!pathTerm) {
            console.warn(`Property node ${index} has no sh:path; skipping.`);
            return;
          }
          let field = pathTerm.value;
          // Normalize field name: substring after last "/"
          field = field.substring(field.lastIndexOf("/") + 1);
          const descriptionTerm = store.any(propNode, SH("description"));
          const placeholder = descriptionTerm ? descriptionTerm.value : field;
          const label = field;
          const datatypeTerm = store.any(propNode, SH("datatype"));
          let type = "text";
          if (datatypeTerm) {
            const dt = datatypeTerm.value;
            if (dt.indexOf("dateTime") !== -1 || dt.indexOf("date") !== -1) {
              type = "date";
            } else if (dt.indexOf("integer") !== -1 || dt.indexOf("number") !== -1) {
              type = "number";
            }
          }
          let options = [];
          const inConstraint = store.any(propNode, SH("in"));
          if (inConstraint) {
            const RDF = $rdf.Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#");
            if (store.holds(inConstraint, RDF("first"))) {
              options = getCollectionElements(inConstraint, store);
            } else {
              options = [inConstraint.value];
            }
            type = "select";
          }
          const minCountTerm = store.any(propNode, SH("minCount"));
          const required = minCountTerm && parseInt(minCountTerm.value) > 0;
          properties.push({ field, label, placeholder, type, required, options });
        });
        console.log("TTL parsing complete. Extracted properties:", properties);
        studySchemaProperties.value = properties;
        initializeCustomStudy();
      } catch (error) {
        console.error("Error loading or parsing TTL file:", error);
      }
    }

    function initializeCustomStudy() {
      console.log("Initializing customStudy object with extracted fields.");
      studySchemaProperties.value.forEach((prop) => {
        customStudy.value[prop.field] = "";
      });
      console.log("customStudy initialized:", customStudy.value);
    }

    function addField() {
      if (!newField.value.fieldType || !newField.value.fieldName) return;
      customFields.value.push({ ...newField.value });
      newField.value = { fieldType: "", fieldName: "", fieldValue: "" };
    }

    function removeField(index) {
      customFields.value.splice(index, 1);
    }

    // Validate required fields and open the visit dialog.
    function validateAndProceed() {
      showErrors.value = true;
      const missingRequired = studySchemaProperties.value.some(
        (field) => field.required && !customStudy.value[field.field]
      );
      if (missingRequired) {
        console.log("Validation failed. Missing required fields:", customStudy.value);
        return;
      }
      showVisitDialog.value = true;
    }

    function submitNumberOfVisits() {
      if (numberOfVisitsInput.value < 1) return;
      numberOfVisits.value = numberOfVisitsInput.value;
      // Initialize default visit labels (editable) e.g., "Visit 1", "Visit 2", etc.
      visitLabels.value = [];
      for (let i = 1; i <= numberOfVisits.value; i++) {
        visitLabels.value.push(`Visit ${i}`);
      }
      // Initialize mapping selection 2D array for each data model (rows) and visit (columns)
      mappingSelection.value = dataModels.value.map(() => {
        return Array(numberOfVisits.value).fill(false);
      });
      showVisitDialog.value = false;
      showMappingScreen.value = true;
    }

    function cancelVisitDialog() {
      showVisitDialog.value = false;
    }

    function toggleMapping(rowIndex, colIndex) {
      mappingSelection.value[rowIndex][colIndex] = !mappingSelection.value[rowIndex][colIndex];
    }

    // Finalize mapping and navigate to the specified route.
    function finalizeMapping() {
      console.log("Mapping finalized:", mappingSelection.value);
      router.push({ name: "CreateFormScratch" });
    }

    function resetForm() {
      studySchemaProperties.value.forEach((prop) => {
        customStudy.value[prop.field] = "";
      });
      customFields.value = [];
      newField.value = { fieldType: "", fieldName: "", fieldValue: "" };
      showCustomFieldEditor.value = false;
      showErrors.value = false;
      console.log("Form has been reset.");
    }

    onMounted(loadStudySchema);

    return {
      studySchemaProperties,
      customStudy,
      customFields,
      newField,
      showCustomFieldEditor,
      showErrors,
      addField,
      removeField,
      validateAndProceed,
      resetForm,
      showVisitDialog,
      numberOfVisitsInput,
      submitNumberOfVisits,
      cancelVisitDialog,
      showMappingScreen,
      numberOfVisits,
      dataModels,
      mappingSelection,
      toggleMapping,
      finalizeMapping,
      visitLabels,
    };
  },
};
</script>

<style scoped>
/* Container styling */
.study-creation-container {
  max-width: 1200px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
}

/* Study form styling */
.new-study-form {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  margin-bottom: 20px;
}

label {
  font-weight: bold;
  display: block;
  margin-top: 10px;
}

.required {
  color: red;
}

select,
input,
textarea {
  width: 100%;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin-top: 5px;
  box-sizing: border-box;
}

.error-text {
  color: red;
  font-size: 12px;
  margin-top: 3px;
  display: block;
}

.schema-field-row {
  margin-bottom: 15px;
}

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

.new-field-section {
  margin-top: 20px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #fff;
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

.add-btn {
  background-color: #ccc;
  border: 1px solid #bbb;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
}

.add-btn:hover {
  background-color: #bbb;
}

.custom-fields-section {
  border: 1px dashed #ccc;
  padding: 10px;
  margin-top: 10px;
  border-radius: 5px;
}

.custom-fields-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

.custom-field-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.custom-field-display {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.added-field-label {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 5px;
}

.added-field-value input,
.added-field-value textarea {
  width: 100%;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}

.remove-btn {
  align-self: flex-end;
  margin-left: 10px;
  background-color: #ccc;
  border: 1px solid #bbb;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
}

.remove-btn:hover {
  background-color: #bbb;
}

.form-actions {
  margin-top: 20px;
}

.btn-option {
  display: block;
  width: 100%;
  padding: 10px;
  margin-top: 15px;
  background: #f7f7f7;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  text-align: center;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-dialog {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  width: 300px;
}

.modal-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

/* Mapping Screen styles */
.mapping-screen {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
}

/* Table container with fixed dimensions and scrollbars */
.table-container {
  max-height: 400px;
  width: 100%;
  overflow: auto;
  border: 1px solid #ddd;
  margin-bottom: 15px;
}

/* Fixed layout for the table so each column has a set width */
.mapping-table {
  table-layout: fixed;
  border-collapse: collapse;
  /* Set overall min-width so columns do not shrink */
  min-width: 100%;
}

/* Fixed width for each header and cell (except the first column) */
.mapping-table th,
.mapping-table td {
  width: 150px;
  min-width: 150px;
  text-align: center;
  white-space: nowrap;
  border: 1px solid #ccc;
  padding: 8px;
}

/* Make the first column sticky with a wider fixed width */
.sticky-col {
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 2;
  width: 200px;
  min-width: 200px;
}

/* Sticky header for visit labels */
.mapping-table thead th {
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 3;
}

/* Styling for table cells */
.cell {
  cursor: pointer;
  height: 40px;
}

/* Green tick mark */
.tick-mark {
  color: green;
  font-size: 20px;
}

/* Visit label input styling with fixed width */
.visit-label-input {
  width: 140px;
  min-width: 140px;
  border: none;
  background: transparent;
  text-align: center;
  font-size: 14px;
  padding: 4px;
  box-sizing: border-box;
}
</style>
