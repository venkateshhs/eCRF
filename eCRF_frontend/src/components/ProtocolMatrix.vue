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
            <th
              v-for="(group, gIdx) in groups"
              :key="gIdx"
            >
              {{ group.name }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="(model, mIdx) in selectedModels"
            :key="model.title"
          >
            <td>{{ model.title }}</td>

            <!-- Full-matrix cells -->
            <template v-if="showFullMatrix">
              <template
                v-for="(visit, vIdx) in visits"
                :key="`row-${mIdx}-${vIdx}`"
              >
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
              <td
                v-for="(group, gIdx) in groups"
                :key="gIdx"
              >
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
      <button
        class="nav-btn"
        @click="prevVisit"
        :disabled="currentVisitIndex === 0"
      >&lt;</button>
      <span class="visit-counter">
        {{ currentVisitIndex + 1 }} / {{ visits.length }}
      </span>
      <button
        class="nav-btn"
        @click="nextVisit"
        :disabled="currentVisitIndex === visits.length - 1"
      >&gt;</button>
    </div>
  </div>
</template>

<script>
export default {
  name: "ProtocolMatrix",
  props: {
    visits:          { type: Array, required: true },
    groups:          { type: Array, required: true },
    selectedModels:  { type: Array, required: true },
    assignments:     { type: Array, required: true }
  },
  emits: ["assignment-updated"],
  data() {
    return {
      currentVisitIndex: 0
    };
  },
  computed: {
    showPaginateVisits() {
      return this.visits.length > 3;
    },
    showFullMatrix() {
      return !this.showPaginateVisits;
    }
  },
  methods: {
    prevVisit() {
      if (this.currentVisitIndex > 0) {
        this.currentVisitIndex--;
      }
    },
    nextVisit() {
      if (this.currentVisitIndex < this.visits.length - 1) {
        this.currentVisitIndex++;
      }
    },
    onToggle(mIdx, vIdx, gIdx, checked) {
      this.$emit("assignment-updated", { mIdx, vIdx, gIdx, checked });
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

/* Top visit name */
.visit-header {
  text-align: center;
  font-size: 1.3em;
  font-weight: bold;
  margin-bottom: 10px;
}

/* Horizontal scroll container for wide group lists */
.table-container {
  overflow-x: auto;
}

/* Bottom visit navigation */
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
</style>
