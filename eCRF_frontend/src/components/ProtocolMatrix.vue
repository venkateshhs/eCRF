<template>
  <div class="protocol-matrix-container">
    <!-- 1. Visit Name at Top (paginated only) -->
    <div v-if="showPaginateVisits" class="visit-header">
      {{ visits[currentVisitIndex].name }}
    </div>

    <!-- 2. Matrix with horizontal scroll for groups -->
    <div class="table-container">
      <table class="protocol-table">
        <!-- Full matrix when visits ≤ 3 -->
        <thead v-if="showFullMatrix">
          <tr>
            <th rowspan="2">Section</th>
            <th
              v-for="(visit, vIdx) in visits"
              :key="`visit-head-${vIdx}`"
              :colspan="groups.length"
            >
              {{ visit.name }}
            </th>
          </tr>
          <tr>
            <template v-for="(visit, vIdx) in visits" :key="`groups-for-${vIdx}`">
              <th
                v-for="(group, gIdx) in groups"
                :key="`group-head-${vIdx}-${gIdx}`"
              >
                {{ group.name }}
              </th>
            </template>
          </tr>
        </thead>

        <!-- Single-visit matrix when visits > 3 -->
        <thead v-else>
          <tr>
            <th>Section</th>
            <th v-for="(group, gIdx) in groups" :key="gIdx">
              {{ group.name }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(model, mIdx) in selectedModels" :key="model.title">
            <td>{{ model.title }}</td>

            <!-- Full-matrix cells -->
            <template v-if="showFullMatrix">
              <template v-for="(visit, vIdx) in visits" :key="`row-${mIdx}-${vIdx}`">
                <td
                  v-for="(group, gIdx) in groups"
                  :key="`cell-${mIdx}-${vIdx}-${gIdx}`"
                >
                  <input
                    type="checkbox"
                    :checked="assignments[mIdx][vIdx][gIdx]"
                    @change="onToggle(mIdx, vIdx, gIdx, $event.target.checked)"
                  />
                </td>
              </template>
            </template>

            <!-- Single-visit cells -->
            <template v-else>
              <td v-for="(group, gIdx) in groups" :key="gIdx">
                <input
                  type="checkbox"
                  :checked="assignments[mIdx][currentVisitIndex][gIdx]"
                  @change="onToggle(mIdx, currentVisitIndex, gIdx, $event.target.checked)"
                />
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 3. Visit Navigator at Bottom -->
    <div v-if="showPaginateVisits" class="visit-nav">
      <button class="nav-btn" @click="prevVisit" :disabled="currentVisitIndex === 0">&lt;</button>
      <span class="visit-counter">{{ currentVisitIndex + 1 }} / {{ visits.length }}</span>
      <button class="nav-btn" @click="nextVisit" :disabled="currentVisitIndex === visits.length - 1">&gt;</button>
    </div>

    <!-- Matrix Actions -->
    <div class="matrix-actions">
      <button @click="openPreview" class="btn-option">Preview Form</button>
    </div>

    <!-- Preview Form Modal -->
    <div v-if="showPreviewModal" class="modal-overlay">
      <div class="modal protocol-preview-modal">
        <div class="preview-header">
          <button @click="prevPreviewVisit" :disabled="previewVisitIndex === 0">&lt;</button>
          <span>{{ visits[previewVisitIndex].name }}</span>
          <button @click="nextPreviewVisit" :disabled="previewVisitIndex === visits.length - 1">&gt;</button>
          <span> / </span>
          <button @click="prevPreviewGroup" :disabled="previewGroupIndex === 0">&lt;</button>
          <span>{{ groups[previewGroupIndex].name }}</span>
          <button @click="nextPreviewGroup" :disabled="previewGroupIndex === groups.length - 1">&gt;</button>
        </div>
        <div class="preview-content">
          <FormPreview :form="previewForm" />
        </div>
        <div class="modal-actions">
          <button @click="closePreview" class="btn-primary">Close Preview</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FormPreview from "@/components/FormPreview.vue";

export default {
  name: "ProtocolMatrix",
  components: { FormPreview },
  props: {
    visits:          { type: Array, required: true },
    groups:          { type: Array, required: true },
    selectedModels:  { type: Array, required: true },
    assignments:     { type: Array, required: true }
  },
  emits: ["assignment-updated"],
  data() {
    return {
      currentVisitIndex: 0,
      showPreviewModal:  false,
      previewVisitIndex: 0,
      previewGroupIndex: 0
    };
  },
  computed: {
    showPaginateVisits() {
      return this.visits.length > 3;
    },
    showFullMatrix() {
      return !this.showPaginateVisits;
    },
    previewForm() {
      const visit = this.visits[this.previewVisitIndex];
      const group = this.groups[this.previewGroupIndex];
      const sections = this.selectedModels
        .filter((_, mIdx) =>
          this.assignments[mIdx][this.previewVisitIndex][this.previewGroupIndex]
        )
        .map(model => ({
          title:  model.title,
          fields: model.fields
        }));
      return {
        formName: `Preview: ${visit.name} / ${group.name}`,
        sections
      };
    }
  },
  methods: {
    prevVisit() {
      if (this.currentVisitIndex > 0) this.currentVisitIndex--;
    },
    nextVisit() {
      if (this.currentVisitIndex < this.visits.length - 1) this.currentVisitIndex++;
    },
    onToggle(mIdx, vIdx, gIdx, checked) {
      this.$emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
    },
    openPreview() {
      this.previewVisitIndex = this.currentVisitIndex;
      this.previewGroupIndex = 0;
      this.showPreviewModal  = true;
    },
    closePreview() {
      this.showPreviewModal = false;
    },
    prevPreviewVisit() {
      if (this.previewVisitIndex > 0) this.previewVisitIndex--;
    },
    nextPreviewVisit() {
      if (this.previewVisitIndex < this.visits.length - 1) this.previewVisitIndex++;
    },
    prevPreviewGroup() {
      if (this.previewGroupIndex > 0) this.previewGroupIndex--;
    },
    nextPreviewGroup() {
      if (this.previewGroupIndex < this.groups.length - 1) this.previewGroupIndex++;
    }
  }
};
</script>

<style scoped lang="scss">
@import "@/assets/styles/_base.scss";

.protocol-matrix-container {
  background: #fafafa;
  border: 1px solid $border-color;
  border-radius: 5px;
  padding: 15px;
}

.visit-header {
  text-align: center;
  font-size: 1.3em;
  font-weight: bold;
  margin-bottom: 10px;
}

.table-container {
  overflow-x: auto;
}

.visit-nav {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.nav-btn {
  background: $secondary-color;
  border: 1px solid $border-color;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  font-size: 1.2em;
  line-height: 1;
}
.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.visit-counter {
  font-size: 1.1em;
}

.protocol-table {
  width: 100%;
  border-collapse: collapse;
}

.protocol-table th,
.protocol-table td {
  border: 1px solid $border-color;
  padding: 8px;
  text-align: center;
}

.matrix-actions {
  margin-top: 10px;
  text-align: right;
}

.btn-option {
  @include button-reset;
  background: $secondary-color;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  margin-left: 10px;
}

.btn-primary {
  @include button-reset;
  background: $primary-color;
  color: white;
  padding: $button-padding;
  border-radius: $button-border-radius;
  cursor: pointer;
  margin-left: 10px;
}

/* Preview Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.protocol-preview-modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
}
.preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: bold;
}
.preview-content {
  background: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
}
.modal-actions {
  margin-top: 10px;
  text-align: right;
  button {
    @include button-reset;
    background: $primary-color;
    color: white;
    padding: $button-padding;
    border-radius: $button-border-radius;
    cursor: pointer;
  }
}
</style>
