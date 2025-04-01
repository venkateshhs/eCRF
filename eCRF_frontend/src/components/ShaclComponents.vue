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

    <!-- Render each dialog in the stack -->
    <div
      v-for="(dialog, dIndex) in dialogStack"
      :key="dIndex"
      class="dialog-overlay"
      :style="{ zIndex: 1000 + dIndex }"
      @click.self="dIndex === dialogStack.length - 1 && cancelDialog()"
    >
      <div class="dialog" @click.stop>
        <h3>{{ getClassName(dialog.iri) }}</h3>
        <div class="scrollable-content">
          <form>
            <!-- Iterate over groups -->
            <div
              v-for="(group, gIndex) in dialog.groups"
              :key="gIndex"
              class="group-container"
            >
              <!-- Render group header -->
              <h4 class="group-header">{{ formatGroupName(group.name) }}</h4>
              <!-- Iterate over properties in the group -->
              <div
                v-for="(prop, pIndex) in group.properties"
                :key="pIndex"
                class="form-group"
              >
                <label :for="'input-' + dIndex + '-' + gIndex + '-' + pIndex">
                  {{ prop.name }}
                </label>
                <div class="field-container">
                  <!-- For non-reference fields, render the input -->
                  <template v-if="prop.datatype !== 'reference'">
                    <template v-if="prop.datatype === 'string'">
                      <input
                        type="text"
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                        placeholder="Enter text"
                      />
                    </template>
                    <template v-else-if="prop.datatype === 'number'">
                      <input
                        type="number"
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                        placeholder="Enter number"
                      />
                    </template>
                    <template v-else-if="prop.datatype === 'date'">
                      <input
                        type="date"
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                      />
                    </template>
                    <!-- Updated branch: For datetime, use calendar (input type date) only -->
                    <template v-else-if="prop.datatype === 'datetime'">
                      <input
                        type="date"
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                        placeholder="Select date"
                      />
                    </template>
                    <template v-else-if="prop.datatype === 'select'">
                      <select
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                      >
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
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                        placeholder="Enter URL"
                      />
                    </template>
                    <template v-else>
                      <input
                        type="text"
                        :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                        v-model="prop.value"
                        placeholder="Enter text"
                      />
                    </template>
                  </template>
                  <!-- For reference fields, no input is rendered -->
                  <template v-else>
                    <!-- (No input for reference fields) -->
                  </template>
                  <!-- Action buttons appear inline next to the field -->
                  <div class="action-buttons">
                    <template v-if="prop.datatype === 'reference'">
                      <button
                        @click.prevent="editReferenceField(gIndex, pIndex)"
                        class="btn"
                      >
                        View Class: {{ getClassName(prop.classRef) }}
                      </button>
                      <button
                        @click.prevent="openDeleteDialog(gIndex, pIndex)"
                        class="btn"
                      >
                        Delete
                      </button>
                    </template>
                    <template v-else>
                      <button
                        @click.prevent="openEditFieldDialog(gIndex, pIndex)"
                        class="btn"
                      >
                        Edit
                      </button>
                      <button
                        @click.prevent="openDeleteDialog(gIndex, pIndex)"
                        class="btn"
                      >
                        Delete
                      </button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>
        <div class="dialog-buttons">
          <button v-if="dIndex > 0" @click="saveReference" class="btn">
            Save
          </button>
          <button @click="cancelDialog" class="btn">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Edit Field Name Modal -->
    <div
      v-if="editFieldDialog"
      class="edit-dialog-overlay"
      @click.self="cancelEditFieldDialog"
    >
      <div class="edit-dialog" @click.stop>
        <h3>Edit Field Name</h3>
        <input type="text" v-model="editFieldDialog.newName" />
        <div class="dialog-buttons">
          <button @click="saveEditedFieldName" class="btn">Save</button>
          <button @click="cancelEditFieldDialog" class="btn">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="deleteFieldDialog"
      class="delete-dialog-overlay"
      @click.self="cancelDeleteDialog"
    >
      <div class="delete-dialog" @click.stop>
        <h3>Confirm Deletion</h3>
        <p>Are you sure you want to delete "{{ deleteFieldDialog.fieldName }}"?</p>
        <div class="dialog-buttons">
          <button @click="confirmDelete" class="btn">Yes</button>
          <button @click="cancelDeleteDialog" class="btn">No</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from "vue";
import { ShapesDataset } from "shacl-tulip";

export default {
  name: "ShaclComponents",
  emits: [],
  setup() {
    const loading = ref(true);
    const error = ref(null);
    const dialogStack = ref([]);
    const nodeShapes = ref({});
    const nodeShapeIRIs = ref([]);
    const editFieldDialog = ref(null);
    const deleteFieldDialog = ref(null);

    const config = { showOnlyClassesWithId: true };

    function getClassName(uri) {
      const name = uri.split("/").pop();
      console.log(`Transforming IRI: ${uri} --> Class Name: ${name}`);
      return name;
    }

    function extractLastSegment(url) {
      const lastSegment = url.split("/").pop();
      if (lastSegment.includes("22-rdf-syntax-ns#")) {
        const parts = lastSegment.split("22-rdf-syntax-ns#");
        const extracted = parts[1] || lastSegment;
        console.log(`Extracted "${extracted}" from last segment "${lastSegment}"`);
        return extracted;
      }
      return lastSegment;
    }

    function getOrder(prop) {
      const order = prop["http://www.w3.org/ns/shacl#order"];
      if (
        order === undefined ||
        order === null ||
        (typeof order === "string" && order.trim() === "")
      ) {
        return Infinity;
      }
      const n = parseInt(order, 10);
      return isNaN(n) ? Infinity : n;
    }

    function formatGroupName(groupValue) {
      return groupValue === "Ungrouped"
        ? "Default Properties"
        : extractLastSegment(groupValue);
    }

    const filteredShapeIRIs = computed(() => {
      if (!nodeShapeIRIs.value) {
        console.log("No nodeShapeIRIs available, returning empty array.");
        return [];
      }
      console.log("Original nodeShapeIRIs:", nodeShapeIRIs.value);
      let result = [];
      if (config.showOnlyClassesWithId) {
        result = nodeShapeIRIs.value.filter((iri) => {
          const shape = nodeShapes.value[iri];
          if (!shape || !shape.properties) {
            console.log(`Shape ${iri} has no properties; excluding.`);
            return false;
          }
          const hasId = shape.properties.some((prop) => {
            const path = prop["http://www.w3.org/ns/shacl#path"];
            const match =
              typeof path === "string" &&
              path.toLowerCase().endsWith("/id");
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
        console.log(
          "showOnlyClassesWithId flag is false, returning all IRIs:",
          result
        );
      }
      return result;
    });

    const dataTypeMapping = {
      "http://www.w3.org/2001/XMLSchema#string": "string",
      "http://www.w3.org/2001/XMLSchema#integer": "number",
      "http://www.w3.org/2001/XMLSchema#boolean": "boolean",
      "http://www.w3.org/2001/XMLSchema#date": "date",
      "http://www.w3.org/2001/XMLSchema#anyURI": "uri",
      "https://www.w3.org/TR/NOTE-datetime": "datetime"
    };

    onMounted(() => {
      console.log("Fetching SHACL schema...");
      const shapesDS = new ShapesDataset();
      const fileUrl = "/dlschemas_shacl.ttl";
      shapesDS.addEventListener("graphLoaded", (event) => {
        console.log("Shapes graph fully loaded:", event.detail);
        console.log("Property Groups:", shapesDS.propertyGroups);
        console.log("Node Shapes:", shapesDS.nodeShapes);
        console.log("Node Shape IRIs:", shapesDS.nodeShapeIRIs);
        nodeShapes.value = shapesDS.nodeShapes;
        nodeShapeIRIs.value = shapesDS.nodeShapeIRIs;
        loading.value = false;
      });
      shapesDS.loadRDF(fileUrl).catch((err) => {
        error.value = err.message;
        loading.value = false;
        console.error("Error loading SHACL schema:", err);
      });
    });

    function openDialog(iri, parentInfo = null) {
      console.log("Opening dialog for IRI:", iri);
      const record = nodeShapes.value[iri];
      if (record) {
        console.log(`Processing shape record for IRI: ${iri}`);
        const groupsObj = {};
        record.properties.forEach((prop) => {
          let groupVal = prop["http://www.w3.org/ns/shacl#group"];
          if (!groupVal || groupVal.trim() === "") {
            groupVal = "Ungrouped";
          }
          if (!groupsObj[groupVal]) {
            groupsObj[groupVal] = [];
          }
          groupsObj[groupVal].push(prop);
        });
        let groupKeys = Object.keys(groupsObj);
        groupKeys.sort((a, b) => {
          if (a === "Ungrouped" && b !== "Ungrouped") return 1;
          if (b === "Ungrouped" && a !== "Ungrouped") return -1;
          return a.localeCompare(b);
        });
        const groupsArray = groupKeys.map((key) => {
          const sortedProps = groupsObj[key]
            .slice()
            .sort((a, b) => getOrder(a) - getOrder(b))
            .map((prop, idx) => {
              console.log(
                `\nProcessing property (group: ${key}) #${idx}:`,
                JSON.stringify(prop, null, 2)
              );
              const nameValue = prop["http://www.w3.org/ns/shacl#name"];
              let fieldName = "";
              if (nameValue && nameValue.trim() !== "") {
                fieldName = nameValue;
                console.log(`Property #${idx}: Found shacl#name: "${nameValue}"`);
              } else {
                const pathValue = prop["http://www.w3.org/ns/shacl#path"];
                if (pathValue && pathValue.trim() !== "") {
                  fieldName = extractLastSegment(pathValue);
                  console.log(
                    `Property #${idx}: shacl#name is empty, using extracted label from shacl#path: "${fieldName}"`
                  );
                } else {
                  fieldName = "Unnamed";
                  console.log(
                    `Property #${idx}: Both shacl#name and shacl#path are empty. Defaulting to "Unnamed"`
                  );
                }
              }
              let fieldType = "";
              let classRef = "";
              if (prop["http://www.w3.org/ns/shacl#class"]) {
                fieldType = "reference";
                classRef = prop["http://www.w3.org/ns/shacl#class"];
                console.log(
                  `Property #${idx}: Found shacl#class: "${classRef}". Setting type to "reference".`
                );
              } else {
                const datatypeURI = prop["http://www.w3.org/ns/shacl#datatype"];
                fieldType = dataTypeMapping[datatypeURI] || "string";
                console.log(
                  `Property #${idx}: datatype URI: "${datatypeURI}" mapped to type: "${fieldType}"`
                );
              }
              const options = prop["http://www.w3.org/ns/shacl#in"] || [];
              console.log(`Property #${idx}: options:`, options);
              return {
                name: fieldName,
                order: getOrder(prop),
                datatype: fieldType,
                options: options,
                value: null,
                classRef: classRef,
              };
            });
          return { name: key, properties: sortedProps };
        });

        const dialogData = {
          iri,
          groups: groupsArray,
          parentInfo,
        };
        console.log("Final dialog data JSON:", JSON.stringify(dialogData, null, 2));
        dialogStack.value.push(dialogData);
      } else {
        console.warn("No record found for IRI:", iri);
      }
    }

    function openEditFieldDialog(groupIndex, propertyIndex) {
      const currentDialog = dialogStack.value[dialogStack.value.length - 1];
      const field = currentDialog.groups[groupIndex].properties[propertyIndex];
      editFieldDialog.value = { groupIndex, propertyIndex, newName: field.name };
    }

    function saveEditedFieldName() {
      if (editFieldDialog.value) {
        const { groupIndex, propertyIndex, newName } = editFieldDialog.value;
        const currentDialog = dialogStack.value[dialogStack.value.length - 1];
        console.log(
          `Updating field name at group ${groupIndex}, index ${propertyIndex} to "${newName}"`
        );
        currentDialog.groups[groupIndex].properties[propertyIndex].name = newName;
        editFieldDialog.value = null;
      }
    }

    function cancelEditFieldDialog() {
      editFieldDialog.value = null;
    }

    function editReferenceField(groupIndex, propertyIndex) {
      editField(groupIndex, propertyIndex);
    }

    function editField(groupIndex, propertyIndex) {
      const currentDialog = dialogStack.value[dialogStack.value.length - 1];
      const field = currentDialog.groups[groupIndex].properties[propertyIndex];
      if (field.datatype === "reference" && field.classRef) {
        const currentIndex = dialogStack.value.length - 1;
        console.log(
          `Editing reference field "${field.name}". Opening dialog for referenced class: ${field.classRef}`
        );
        openDialog(field.classRef, {
          parentDialogIndex: currentIndex,
          fieldLocation: { groupIndex, propertyIndex },
        });
      } else {
        openEditFieldDialog(groupIndex, propertyIndex);
      }
    }

    function openDeleteDialog(groupIndex, propertyIndex) {
      const currentDialog = dialogStack.value[dialogStack.value.length - 1];
      const field = currentDialog.groups[groupIndex].properties[propertyIndex];
      deleteFieldDialog.value = { groupIndex, propertyIndex, fieldName: field.name };
    }

    function confirmDelete() {
      const { groupIndex, propertyIndex } = deleteFieldDialog.value;
      const currentDialog = dialogStack.value[dialogStack.value.length - 1];
      console.log(
        `Deleting field at group ${groupIndex}, index ${propertyIndex}`
      );
      currentDialog.groups[groupIndex].properties.splice(propertyIndex, 1);
      deleteFieldDialog.value = null;
    }

    function cancelDeleteDialog() {
      deleteFieldDialog.value = null;
    }

    function deleteField(groupIndex, propertyIndex) {
      openDeleteDialog(groupIndex, propertyIndex);
    }

    function saveReference() {
      const childDialog = dialogStack.value.pop();
      if (childDialog.parentInfo) {
        const { parentDialogIndex, fieldLocation } = childDialog.parentInfo;
        const parentDialog = dialogStack.value[parentDialogIndex];
        console.log(
          `Saving reference. Updating parent's field at group ${fieldLocation.groupIndex}, index ${fieldLocation.propertyIndex} with data:`,
          childDialog
        );
        parentDialog.groups[fieldLocation.groupIndex].properties[fieldLocation.propertyIndex].value = childDialog;
      }
    }

    function cancelDialog() {
      dialogStack.value.pop();
    }

    function closeDialog() {
      dialogStack.value = [];
    }

    return {
      loading,
      error,
      dialogStack,
      filteredShapeIRIs,
      getClassName,
      openDialog,
      closeDialog,
      editField,
      editReferenceField,
      deleteField,
      saveReference,
      cancelDialog,
      formatGroupName,
      editFieldDialog,
      openEditFieldDialog,
      saveEditedFieldName,
      cancelEditFieldDialog,
      deleteFieldDialog,
      openDeleteDialog,
      confirmDelete,
      cancelDeleteDialog,
    };
  },
};
</script>

<style scoped>
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
  color: #333;
}
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
.scrollable-content {
  max-height: 50vh;
  overflow-y: auto;
  padding: 10px;
  border-top: 1px solid #ddd;
}
.group-container {
  margin-bottom: 20px;
}
.group-header {
  margin-bottom: 10px;
  font-size: 1.1em;
  font-weight: bold;
  border-bottom: 1px solid #ccc;
  padding-bottom: 4px;
}
.form-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}
label {
  font-weight: 500;
  margin-bottom: 4px;
}
.field-container {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.field-container input,
.field-container select {
  flex: 1;
  padding: 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.action-buttons {
  display: flex;
  gap: 5px;
}
.btn {
  padding: 4px 8px;
  border: 1px solid #ccc;
  background-color: #f5f5f5;
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.9em;
  color: #333;
}
.btn:hover {
  background-color: #e0e0e0;
}
.dialog-buttons {
  margin-top: 10px;
  display: flex;
  justify-content: center;
  gap: 10px;
}
.close-button {
  display: block;
  margin: 15px auto 0;
  padding: 8px 12px;
  background: #ddd;
  border: none;
  cursor: pointer;
  border-radius: 5px;
}
.edit-dialog-overlay,
.delete-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.edit-dialog,
.delete-dialog {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}
.edit-dialog h3,
.delete-dialog h3 {
  margin-top: 0;
  font-size: 1.2em;
  margin-bottom: 20px;
}
.edit-dialog input {
  width: 100%;
  padding: 10px;
  font-size: 1em;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-bottom: 20px;
}
.edit-dialog .dialog-buttons,
.delete-dialog .dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
