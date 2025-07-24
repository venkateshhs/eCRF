<template>
  <div v-if="loading" class="loading">Loading…</div>
  <div v-else-if="error" class="error">{{ error }}</div>
  <div v-else>
    <DataEntryForm
      :study="{ metadata: { id: info.study_id }, content: { study_data: info.study_data } }"
      :subjectIndex="info.subject_index"
      :visitIndex="info.visit_index"
      :permission="info.permission"
    />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import DataEntryForm from '@/components/DataEntryComponent.vue';

export default {
  components: { DataEntryForm },
  setup() {
    const route   = useRoute();
    const loading = ref(true);
    const error   = ref(null);
    const info    = ref(null);

    onMounted(async () => {
      const token = route.params.token;
      try {
        const resp = await axios.get(
          `http://localhost:8000/forms/shared/${token}`
        );
        info.value = resp.data;
      } catch (e) {
        error.value = e.response?.data?.detail || e.message;
      } finally {
        loading.value = false;
      }
    });

    return { loading, error, info };
  }
};
</script>


<style scoped>
.loading, .error {
  text-align: center;
  margin: 2rem;
  color: #555;
}
.error { color: tomato; }
</style>
