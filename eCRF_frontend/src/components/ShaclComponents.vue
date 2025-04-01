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
                <!-- Render input based on datatype -->
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
                <!-- For reference fields, render a button to open a new dialog -->
                <template v-else-if="prop.datatype === 'reference'">
                  <button
                    @click.prevent="editReferenceField(gIndex, pIndex)"
                    class="btn minimal-btn"
                  >
                    Edit Reference
                  </button>
                </template>
                <!-- Default: treat unknown as string -->
                <template v-else>
                  <input
                    type="text"
                    :id="'input-' + dIndex + '-' + gIndex + '-' + pIndex"
                    v-model="prop.value"
                    placeholder="Enter text"
                  />
                </template>
                <!-- Action buttons for non-reference fields -->
                <div
                  class="action-buttons"
                  v-if="prop.datatype !== 'reference'"
                >
                  <button
                    @click.prevent="editField(gIndex, pIndex)"
                    class="btn minimal-btn"
                  >
                    Edit
                  </button>
                  <button
                    @click.prevent="deleteField(gIndex, pIndex)"
                    class="btn minimal-btn btn-delete"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>
        <div class="dialog-buttons">
          <!-- For reference dialogs (not the main one), show a Save button -->
          <button v-if="dIndex > 0" @click="saveReference" class="btn minimal-btn">
            Save
          </button>
          <button @click="cancelDialog" class="btn minimal-btn">
            Close
          </button>
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
    // Maintain a stack of dialogs; the main dialog is pushed first.
    const dialogStack = ref([]);
    const nodeShapes = ref({});
    const nodeShapeIRIs = ref([]);

    const config = { showOnlyClassesWithId: true };

    // Helper: Derive a class name from an IRI.
    function getClassName(uri) {
      const name = uri.split("/").pop();
      console.log(`Transforming IRI: ${uri} --> Class Name: ${name}`);
      return name;
    }

    // Helper: Extract the last segment from a URL.
    // If the segment contains "22-rdf-syntax-ns#", return only what follows.
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

    // Helper: Get the order for a property.
    // If missing or empty, return Infinity so that it sorts at the end.
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

    // Helper: Format the group name.
    // If the group is "Ungrouped", return "Default Properties". Otherwise, extract the last segment.
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

    // Open a dialog for the given IRI.
    // Optional parameter parentInfo is used for reference dialogs.
    function openDialog(iri, parentInfo = null) {
      console.log("Opening dialog for IRI:", iri);
      const record = nodeShapes.value[iri];
      if (record) {
        console.log(`Processing shape record for IRI: ${iri}`);
        // Group properties by "http://www.w3.org/ns/shacl#group"
        // Default to "Ungrouped" if missing.
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
        // Sort group keys so that "Ungrouped" is always last.
        let groupKeys = Object.keys(groupsObj);
        groupKeys.sort((a, b) => {
          if (a === "Ungrouped" && b !== "Ungrouped") return 1;
          if (b === "Ungrouped" && a !== "Ungrouped") return -1;
          return a.localeCompare(b);
        });
        // Convert groups object to an array with sorted properties (by order).
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
          parentInfo, // null for main dialogs; for references, contains parentDialogIndex and fieldLocation
        };
        console.log("Final dialog data JSON:", JSON.stringify(dialogData, null, 2));
        dialogStack.value.push(dialogData);
      } else {
        console.warn("No record found for IRI:", iri);
      }
    }

    // Edit a field in the current (top) dialog.
    // Accepts groupIndex and property index.
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
        const newValue = prompt(`Edit field "${field.name}"`, field.value);
        if (newValue !== null) {
          console.log(
            `Field "${field.name}" updated from "${field.value}" to "${newValue}"`
          );
          currentDialog.groups[groupIndex].properties[propertyIndex].value = newValue;
        }
      }
    }

    // Dedicated function for reference fields.
    function editReferenceField(groupIndex, propertyIndex) {
      editField(groupIndex, propertyIndex);
    }

    function deleteField(groupIndex, propertyIndex) {
      const currentDialog = dialogStack.value[dialogStack.value.length - 1];
      const field = currentDialog.groups[groupIndex].properties[propertyIndex];
      if (confirm(`Are you sure you want to delete "${field.name}"?`)) {
        console.log(
          `Deleting field "${field.name}" at group ${groupIndex} index ${propertyIndex}`
        );
        currentDialog.groups[groupIndex].properties.splice(propertyIndex, 1);
      }
    }

    // Save the currently open reference dialog into its parent.
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

    // Cancel (close) the current dialog.
    function cancelDialog() {
      dialogStack.value.pop();
    }

    // Close the main dialog (clears the entire stack).
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
      addField: () => {}, // addField removed as not required
      saveReference,
      cancelDialog,
      formatGroupName,
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
  background: none;
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.9em;
  color: #333;
}
.minimal-btn:hover {
  background: #f0f0f0;
}
.btn-delete {
  border-color: #e57373;
  color: #e57373;
}
.btn-delete:hover {
  background: #fce4e4;
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
</style>
