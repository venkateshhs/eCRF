<!-- src/components/ShaclComponents.vue -->
<template>
  <div class="shacl-components">
    <h2>SHACL Components</h2>
    <p v-if="shaclComponents.length === 0">No SHACL components available.</p>
    <div v-else>
      <div v-for="component in shaclComponents" :key="component.id" class="shacl-item">
        <i :class="component.icon"></i> {{ component.label }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ShaclComponents",
  props: {
    shaclComponents: {
      type: Array,
      required: true,
    },
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
.shacl-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  font-size: 14px;
  background: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}
.shacl-item:hover {
  background: #e0e0e0;
}
</style>
