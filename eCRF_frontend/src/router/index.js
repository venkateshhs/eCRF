import { createRouter, createWebHistory } from "vue-router";
import LoginComponent from "../components/LoginComponent.vue";
import RegistrationComponent from "../components/RegistrationComponent.vue";
import DashboardComponent from "../components/DashboardComponent.vue";
import UserInfoComponent from "../components/UserInfoComponent.vue";
import CreateFormComponent from "../components/CreateFormComponent.vue"; // Unified component for template selection and rendering
import ViewFormsComponent from "../components/ViewFormsComponent.vue";
import AnalyticsComponent from "../components/AnalyticsComponent.vue";
import ScratchFormComponent from "../components/ScratchFormComponent.vue";
import SavedFormsComponent from "../components/SavedFormsComponent";
import FormDetailComponent from "../components/FormDetailComponent";
import StudyTypeSelectionComponent from '../components/StudyTypeSelectionComponent.vue';

const routes = [
  { path: "/", redirect: "/login" }, // Redirect root to login
  { path: "/login", name: "Login", component: LoginComponent },
  { path: "/register", name: "Registration", component: RegistrationComponent },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: DashboardComponent,
    children: [
      { path: "user-info", name: "UserInfo", component: UserInfoComponent },
      {path: 'create-study',name: 'CreateStudy',component: StudyTypeSelectionComponent,
    },
      {
        path: "create-form",
        name: "CreateForm",
        component: CreateFormComponent, // Single component for selection and rendering
      },
      { path: "view-forms", name: "ViewForms", component: ViewFormsComponent },
      { path: "analytics", name: "Analytics", component: AnalyticsComponent },
    ],
  },
  {
    path: "/dashboard/create-form-scratch",
    name: "CreateFormScratch",
    component: ScratchFormComponent, // New scratch form creation page
  },
  {
      path: "/saved-forms",
      name: "saved-forms",
      component: SavedFormsComponent,
    },
    {
  path: "/saved-forms/:id",
  name: "FormDetail",
  component: FormDetailComponent,
},
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
