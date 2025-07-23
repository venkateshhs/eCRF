import { createRouter, createWebHistory } from "vue-router";
import LoginComponent from "../components/LoginComponent.vue";
import RegistrationComponent from "../components/RegistrationComponent.vue";
import DashboardComponent from "../components/DashboardComponent.vue";
import UserInfoComponent from "../components/UserInfoComponent.vue";
// import CreateFormComponent from "../components/CreateFormComponent.vue";
import AnalyticsComponent from "../components/AnalyticsComponent.vue";
import ScratchFormComponent from "../components/ScratchFormComponent.vue";
import SavedFormsComponent from "../components/SavedFormsComponent.vue";
import FormDetailComponent from "../components/FormDetailComponent.vue";
import StudyCreationComponent from "../components/StudyCreationComponent.vue";
//import YamlViewerComponent from "../components/YamlViewerComponent.vue";
import StudySettings from "../components/StudySettings.vue";
import SavedStudyView         from '../components/SavedStudyView.vue'
import SharedFormComponent from '../components/SharedFormComponent.vue'
import StudyDataEntryComponent from '../components/DataEntryComponent.vue'
const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", name: "Login", component: LoginComponent },
  { path: "/register", name: "Registration", component: RegistrationComponent },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: DashboardComponent,
    children: [
      { path: "user-info", name: "UserInfo", component: UserInfoComponent },
      { path: "create-study/:id?", name: "CreateStudy", component: StudyCreationComponent, props: true, },
      //{ path: "create-form", name: "CreateForm", component: CreateFormComponent },
      { path: "view-forms", name: "ViewForms", component: SavedFormsComponent },
      { path: "analytics", name: "Analytics", component: AnalyticsComponent },
    ],
  },
//  {
//    path: "/dashboard/view-yaml/:category/:fileName",
//    name: "YamlViewer",
//    component: YamlViewerComponent,
//    props: true,
//  },
  {
    path: "/dashboard/create-form-scratch",
    name: "CreateFormScratch",
    component: ScratchFormComponent,
  },
  {
    path: "/saved-forms",
    name: "SavedForms",
    component: SavedFormsComponent,
  },
  {
    path: "/studies/:id",
    name: "StudyDetail",
    component: FormDetailComponent,
  },
  {
    path: '/saved-study',
    name: 'SavedStudyView',
    component: SavedStudyView
  },
  {
      path: "/settings",
      name: "StudySettings",
      component: StudySettings,
    },
    {
    path: "/forms/shared/:token",
    name: "SharedForm",
    component: SharedFormComponent,
  },
  {
    path: "/studies/:id",
    name: "StudyDataEntry",
    component: StudyDataEntryComponent,
    props: route => ({ id: Number(route.params.id) })
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
