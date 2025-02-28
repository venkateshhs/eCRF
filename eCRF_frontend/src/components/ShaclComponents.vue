<template>
  <div class="shacl-components">
    <h2>SHACL Classes</h2>

    <p v-if="loading">Loading SHACL components...</p>
    <p v-else-if="error">Error loading SHACL components: {{ error }}</p>

    <ul v-else>
      <li
        v-for="(iri, index) in nodeShapeIRIs ?? []"
        :key="index"
        @click="openDialog(iri)"
        class="shape-item"
      >
        {{ getClassName(iri) }}
      </li>
    </ul>

    <!-- Dialog for Person Record -->
    <div v-if="dialogVisible" class="dialog-overlay" @click="closeDialog">
      <div class="dialog" @click.stop>
        <h3>{{ getClassName(personData.iri) }}</h3>

        <div class="scrollable-content">
          <form>
            <div v-for="(prop, index) in personData.properties" :key="index" class="form-group">
              <label :for="'input-' + index">{{ prop.name }}</label>

              <!-- Render appropriate input field -->
              <template v-if="prop.datatype === 'string'">
                <input type="text" :id="'input-' + index" v-model="prop.value" placeholder="Enter text" />
              </template>

              <template v-else-if="prop.datatype === 'number'">
                <input type="number" :id="'input-' + index" v-model="prop.value" placeholder="Enter number" />
              </template>

              <template v-else-if="prop.datatype === 'date'">
                <input type="date" :id="'input-' + index" v-model="prop.value" />
              </template>

              <template v-else-if="prop.datatype === 'select'">
                <select :id="'input-' + index" v-model="prop.value">
                  <option v-for="option in prop.options" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select>
              </template>

              <template v-else-if="prop.datatype === 'uri'">
                <input type="url" :id="'input-' + index" v-model="prop.value" placeholder="Enter URL" />
              </template>

              <template v-else-if="prop.datatype === 'boolean'">
                <input type="checkbox" :id="'input-' + index" v-model="prop.value" />
              </template>

              <div class="action-buttons">
                <button @click.prevent="editField(index)" class="btn">Edit</button>
                <button @click.prevent="deleteField(index)" class="btn btn-delete">Delete</button>
              </div>
            </div>
          </form>
        </div>

        <div class="add-section">
          <button class="btn btn-add" @click="addField">+ Add New Field</button>
        </div>

        <button class="close-button" @click="closeDialog">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import { useShapeData } from "shacl-vue";

export default {
  name: "ShaclComponents",
  setup() {
    const config = { value: { shapes_url: "/dlschemas_shacl.ttl" } };
    const { getSHACLschema, nodeShapes, nodeShapeIRIs } = useShapeData(config);

    const loading = ref(true);
    const error = ref(null);
    const dialogVisible = ref(false);
    const personData = ref({ iri: "", properties: [] });

    const dataTypeMapping = {
      "http://www.w3.org/2001/XMLSchema#string": "string",
      "http://www.w3.org/2001/XMLSchema#integer": "number",
      "http://www.w3.org/2001/XMLSchema#boolean": "boolean",
      "http://www.w3.org/2001/XMLSchema#date": "date",
      "http://www.w3.org/2001/XMLSchema#anyURI": "uri",
    };

    onMounted(async () => {
      try {
        await getSHACLschema();
        loading.value = false;
      } catch (err) {
        error.value = err.message;
        loading.value = false;
      }
    });

    function getClassName(uri) {
      return uri.split("/").pop();
    }

    function openDialog(iri) {
      const personRecord = nodeShapes.value[iri];

      if (personRecord) {
        personData.value = {
          iri,
          properties: personRecord.properties.map(prop => ({
            name: prop["http://www.w3.org/ns/shacl#name"] || "Unnamed",
            datatype: dataTypeMapping[prop["http://www.w3.org/ns/shacl#datatype"]] || "unknown",
            options: prop["http://www.w3.org/ns/shacl#in"] || [],
            value: null,
          })),
        };
        dialogVisible.value = true;
      }
    }

    function closeDialog() {
      dialogVisible.value = false;
    }

    function editField(index) {
      const newValue = prompt(`Edit field "${personData.value.properties[index].name}"`, personData.value.properties[index].value);
      if (newValue !== null) {
        personData.value.properties[index].value = newValue;
      }
    }

    function deleteField(index) {
      if (confirm(`Are you sure you want to delete "${personData.value.properties[index].name}"?`)) {
        personData.value.properties.splice(index, 1);
      }
    }

    function addField() {
      const newFieldName = prompt("Enter the name for the new field:");
      if (newFieldName) {
        personData.value.properties.push({
          name: newFieldName,
          datatype: "string",
          value: "",
        });
      }
    }

    return { nodeShapeIRIs, loading, error, dialogVisible, personData, openDialog, closeDialog, editField, deleteField, addField, getClassName };
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
