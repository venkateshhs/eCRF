import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import store from "./store";
import "./assets/styles/_base.scss";
import formatLabelPlugin from './plugins/format-label'
import FormFieldsPlugin  from './components/forms'

createApp(App).use(router).use(store).use(formatLabelPlugin).use(FormFieldsPlugin).mount("#app");
