<template>
  <div>
    <h1 v-if="template?.name">{{ template.name }}</h1>
    <form v-if="template?.fields?.length">
      <div v-for="field in template.fields" :key="field.name" class="form-group">
        <label :for="field.name">{{ field.label }}</label>
        <input
          :type="field.type"
          :id="field.name"
          v-model="formData[field.name]"
          :placeholder="field.placeholder"
        />
      </div>
      <button @click.prevent="submitForm" class="btn-submit">Submit</button>
    </form>
    <p v-else>No template selected or template is empty.</p>
  </div>
</template>

<script>
import { reactive, watch } from "vue";

export default {
  name: "RenderTemplateComponent",
  props: {
    template: {
      type: Object,
      default: () => ({}),
    },
  },
  setup(props) {
    const formData = reactive({});

    const loadTemplate = () => {
      console.log("Loading template:", props.template);
      if (props.template?.fields && Array.isArray(props.template.fields)) {
        props.template.fields.forEach((field) => {
          formData[field.name] = "";
        });
        console.log("Initialized formData:", formData);
      } else {
        console.warn("Template fields are missing or invalid.");
      }
    };

    const submitForm = () => {
      console.log("Submitted Data:", formData);
    };

    watch(
      () => props.template,
      (newTemplate) => {
        console.log("Template updated:", newTemplate);
        loadTemplate();
      },
      { immediate: true }
    );

    return {
      formData,
      submitForm,
    };
  },
};
</script>


<style scoped>
/* Add your styling for form-group, labels, input, and buttons */
.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  font-size: 14px;
  margin-bottom: 5px;
}

input {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}

input:focus {
  border-color: #007bff;
  outline: none;
}

.btn-submit {
  padding: 10px 20px;
  font-size: 16px;
  color: white;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.btn-submit:hover {
  background-color: #0056b3;
}
</style>
