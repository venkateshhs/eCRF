<template>
  <div class="shacl-components">
    <h2>SHACL Classes</h2>

    <p v-if="loading">Loading SHACL components...</p>
    <p v-else-if="error">Error loading SHACL components: {{ error }}</p>

    <ul v-else>
      <li
        v-for="(iri, index) in filteredShapeIRIs"
        :key="index"
        @click="openDialog(iri)"
        class="shape-item"
      >
        {{ getClassName(iri) }}
      </li>
    </ul>

    <!-- Dialog for displaying shape details -->
    <div v-if="dialogVisible" class="dialog-overlay" @click="closeDialog">
      <div class="dialog" @click.stop>
        <h3>{{ getClassName(shapeData.iri) }}</h3>
        <div class="scrollable-content">
          <form>
            <div
              v-for="(prop, index) in shapeData.properties"
              :key="index"
              class="form-group"
            >
              <label :for="'input-' + index">{{ prop.name }}</label>
              <!-- Render input based on datatype -->
              <template v-if="prop.datatype === 'string'">
                <input
                  type="text"
                  :id="'input-' + index"
                  v-model="prop.value"
                  placeholder="Enter text"
                />
              </template>
              <template v-else-if="prop.datatype === 'number'">
                <input
                  type="number"
                  :id="'input-' + index"
                  v-model="prop.value"
                  placeholder="Enter number"
                />
              </template>
              <template v-else-if="prop.datatype === 'date'">
                <input type="date" :id="'input-' + index" v-model="prop.value" />
              </template>
              <template v-else-if="prop.datatype === 'select'">
                <select :id="'input-' + index" v-model="prop.value">
                  <option
                    v-for="option in prop.options"
                    :key="option"
                    :value="option"
                  >
                    {{ option }}
                  </option>
                </select>
              </template>
              <template v-else-if="prop.datatype === 'uri'">
                <input
                  type="url"
                  :id="'input-' + index"
                  v-model="prop.value"
                  placeholder="Enter URL"
                />
              </template>
              <template v-else-if="prop.datatype === 'boolean'">
                <input type="checkbox" :id="'input-' + index" v-model="prop.value" />
              </template>
              <div class="action-buttons">
                <button @click.prevent="editField(index)" class="btn">
                  Edit
                </button>
                <button @click.prevent="deleteField(index)" class="btn btn-delete">
                  Delete
                </button>
              </div>
            </div>
          </form>
        </div>
        <div class="add-section">
          <button class="btn btn-add" @click="addField">
            + Add New Field
          </button>
        </div>
        <button class="close-button" @click="closeDialog">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from "vue";
import { useShapeData } from "shacl-vue";

export default {
  name: "ShaclComponents",
  setup() {
    // Configuration for the schema; filtering enabled by default.
    const config = {
      value: {
        shapes_url: "/dlschemas_shacl.ttl",
        showOnlyClassesWithId: true,
      },
    };

    const { getSHACLschema, nodeShapes, nodeShapeIRIs } = useShapeData(config);

    const loading = ref(true);
    const error = ref(null);
    // Renamed from personData to shapeData so any SHACL class can be rendered.
    const shapeData = ref({ iri: "", properties: [] });
    const dialogVisible = ref(false);

    // Helper to derive a class name from the IRI.
    function getClassName(uri) {
      const name = uri.split("/").pop();
      console.log(`Transforming IRI: ${uri} --> Class Name: ${name}`);
      return name;
    }

    // Dynamic filtering: if showOnlyClassesWithId is true,
    // filter the IRIs to only those whose shape contains a property whose path ends with "/id".
    const filteredShapeIRIs = computed(() => {
      if (!nodeShapeIRIs.value) {
        console.log("No nodeShapeIRIs available, returning empty array.");
        return [];
      }
      console.log("Original nodeShapeIRIs:", nodeShapeIRIs.value);
      let result = [];
      if (config.value.showOnlyClassesWithId) {
        result = nodeShapeIRIs.value.filter((iri) => {
          const shape = nodeShapes.value[iri];
          if (!shape || !shape.properties) {
            console.log(`Shape ${iri} has no properties; excluding.`);
            return false;
          }
          const hasId = shape.properties.some((prop) => {
            const path = prop["http://www.w3.org/ns/shacl#path"];
            // Dynamic check: property path ends with "/id" (case-insensitive)
            const match =
              typeof path === "string" && path.toLowerCase().endsWith("/id");
            console.log(
              `Shape ${iri}: property path ${path} ${
                match ? "matches" : "does not match"
              } the dynamic id check.`
            );
            return match;
          });
          return hasId;
        });
        console.log("Filtered IRIs with dynamic id check:", result);
      } else {
        result = nodeShapeIRIs.value;
        console.log("showOnlyClassesWithId flag is false, returning all IRIs:", result);
      }
      return result;
    });

    const dataTypeMapping = {
      "http://www.w3.org/2001/XMLSchema#string": "string",
      "http://www.w3.org/2001/XMLSchema#integer": "number",
      "http://www.w3.org/2001/XMLSchema#boolean": "boolean",
      "http://www.w3.org/2001/XMLSchema#date": "date",
      "http://www.w3.org/2001/XMLSchema#anyURI": "uri",
    };

    onMounted(async () => {
      try {
        console.log("Fetching SHACL schema...");
        await getSHACLschema();
        loading.value = false;
        console.log("SHACL schema loaded.");
      } catch (err) {
        error.value = err.message;
        loading.value = false;
        console.error("Error loading SHACL schema:", err);
      }
    });

    // Generic openDialog: opens the dialog and populates shapeData with the selected shape.
    function openDialog(iri) {
      console.log("Opening dialog for IRI:", iri);
      const record = nodeShapes.value[iri];
      if (record) {
        shapeData.value = {
          iri,
          properties: record.properties.map((prop, idx) => {
            const fieldName = prop["http://www.w3.org/ns/shacl#name"] || "Unnamed";
            const fieldType =
              dataTypeMapping[prop["http://www.w3.org/ns/shacl#datatype"]] || "unknown";
            console.log(
              `Mapping property #${idx}: Name: ${fieldName}, DataType: ${fieldType}`
            );
            return {
              name: fieldName,
              datatype: fieldType,
              options: prop["http://www.w3.org/ns/shacl#in"] || [],
              value: null,
            };
          }),
        };
        console.log("Shape Data set to:", shapeData.value);
        dialogVisible.value = true;
      } else {
        console.warn("No record found for IRI:", iri);
      }
    }

    function closeDialog() {
      console.log("Closing dialog.");
      dialogVisible.value = false;
    }

    function editField(index) {
      const field = shapeData.value.properties[index];
      const newValue = prompt(`Edit field "${field.name}"`, field.value);
      if (newValue !== null) {
        console.log(`Field "${field.name}" updated from "${field.value}" to "${newValue}"`);
        shapeData.value.properties[index].value = newValue;
      }
    }

    function deleteField(index) {
      const field = shapeData.value.properties[index];
      if (confirm(`Are you sure you want to delete "${field.name}"?`)) {
        console.log(`Deleting field "${field.name}" at index ${index}`);
        shapeData.value.properties.splice(index, 1);
      }
    }

    function addField() {
      const newFieldName = prompt("Enter the name for the new field:");
      if (newFieldName) {
        console.log(`Adding new field with name: "${newFieldName}"`);
        shapeData.value.properties.push({
          name: newFieldName,
          datatype: "string",
          value: "",
        });
      }
    }

    return {
      filteredShapeIRIs,
      loading,
      error,
      dialogVisible,
      shapeData,
      openDialog,
      closeDialog,
      editField,
      deleteField,
      addField,
      getClassName,
    };
  },
};
</script>

<style scoped>
/* Basic Styles */
.shacl-components {
  background: white;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-top: 10px;
}

.shape-item {
  cursor: pointer;
  color: #555;
  text-decoration: underline;
  margin: 5px 0;
}

.shape-item:hover {
  color: black;
}

/* Dialog Styles */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog {
  background: white;
  padding: 30px;
  border-radius: 10px;
  max-width: 600px;
  width: 90%;
  max-height: 70vh;
  overflow-y: auto;
}

/* Scrollable content */
.scrollable-content {
  max-height: 50vh;
  overflow-y: auto;
  padding: 10px;
  border-top: 1px solid #ddd;
}

/* Form Inputs */
.form-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

label {
  flex: 1;
  font-weight: 500;
}

input,
select {
  flex: 2;
  padding: 6px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.action-buttons {
  display: flex;
  gap: 5px;
}

.btn {
  padding: 5px 10px;
  border: none;
  background: #ddd;
  cursor: pointer;
  border-radius: 4px;
}

.btn-delete {
  background: #f8d7da;
}

.btn-add {
  width: 100%;
  margin-top: 10px;
  background: #c8e6c9;
}

/* Close Button */
.close-button {
  display: block;
  margin: 15px auto 0;
  padding: 8px 12px;
  background: #ddd;
  border: none;
  cursor: pointer;
  border-radius: 5px;
}
</style>
