<template>
  <div class="new-study-form">


    <table class="assignment-table">
      <thead>
        <tr>
          <th>Subject ID</th>
          <th v-for="group in groupNames" :key="group">{{ group }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(subject, rowIndex) in subjects" :key="subject.id">
          <td>{{ subject.id }}</td>
          <td v-for="(group, colIndex) in groupNames" :key="colIndex">
            <input
              type="radio"
              :name="'group-' + rowIndex"
              :value="group"
              v-model="subject.group"
              @change="emitSubjects"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { computed } from "vue";

export default {
  name: "SubjectAssignmentForm",
  props: {
    subjects: { type: Array, required: true },
    groupData: { type: Array, required: true },
  },
  emits: ["update:subjects", "changed"],
  setup(props, { emit }) {
    const groupNames = computed(() =>
      (props.groupData || []).map((g) => g.name || g.label || "Unnamed")
    );

    const emitSubjects = () => {
      emit("update:subjects", props.subjects);
      emit("changed", { kind: "subjectAssignment" });
    };

    return { groupNames, emitSubjects };
  },
};
</script>

<style scoped>
.assignment-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.assignment-table th,
.assignment-table td {
  padding: 8px 12px;
  border: 1px solid #ccc;
  text-align: center;
}

.assignment-table th {
  background-color: #f0f0f0;
}

.assignment-table input[type="radio"] {
  transform: scale(1.2);
  cursor: pointer;
}
</style>
