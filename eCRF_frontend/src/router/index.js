import { createRouter, createWebHistory } from "vue-router";
import LoginComponent from "../components/LoginComponent.vue";
import RegistrationComponent from "../components/RegistrationComponent.vue";
import DashboardComponent from "../components/DashboardComponent.vue";
import UserInfoComponent from "../components/UserInfoComponent.vue";
import CreateFormComponent from "../components/CreateFormComponent.vue";
import ViewFormsComponent from "../components/ViewFormsComponent.vue";
import AnalyticsComponent from "../components/AnalyticsComponent.vue";

const routes = [
  { path: "/", name: "Login", component: LoginComponent },
  { path: "/register", name: "Registration", component: RegistrationComponent },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: DashboardComponent,
    children: [
      { path: "user-info", name: "UserInfo", component: UserInfoComponent },
      { path: "create-form", name: "CreateForm", component: CreateFormComponent },
      { path: "view-forms", name: "ViewForms", component: ViewFormsComponent },
      { path: "analytics", name: "Analytics", component: AnalyticsComponent },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;