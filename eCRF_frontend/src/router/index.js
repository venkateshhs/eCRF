import { createRouter, createWebHistory } from "vue-router";
import LoginComponent from "../components/LoginComponent.vue";
import RegistrationComponent from "../components/RegistrationComponent.vue";
import DashboardComponent from "../components/DashboardComponent.vue";
import UserInfoComponent from "../components/UserInfoComponent.vue";
// import CreateFormComponent from "../components/CreateFormComponent.vue";
import AnalyticsComponent from "../components/AnalyticsComponent.vue";
import ScratchFormComponent from "../components/ScratchFormComponent.vue";
import StudyDataEntryComponent from "../components/StudyDataEntryComponent.vue";
import StudyCreationComponent from "../components/StudyCreationComponent.vue";
//import YamlViewerComponent from "../components/YamlViewerComponent.vue";
import StudySettings from "../components/StudySettings.vue";
//import SavedStudyView         from '../components/SavedStudyView.vue'
//import SharedFormComponent from '../components/SharedFormComponent.vue'
//import StudyDataEntryComponent from '../components/DataEntryComponent.vue'
import StudyView from "@/components/StudyView.vue";

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

      // Create / Edit Study INSIDE dashboard layout
      {
        path: "create-study/:id?",
        name: "CreateStudy",
        component: StudyCreationComponent,
        props: true,
      },

      { path: "analytics", name: "Analytics", component: AnalyticsComponent },

      // MOVE ScratchForm INSIDE dashboard layout (same URL as before)
      {
        path: "create-form-scratch",
        name: "CreateFormScratch",
        component: ScratchFormComponent,
      },

      // Add Data inside Dashboard layout
      {
        path: "studies/:id/add-data",
        name: "DashboardAddData",
        component: StudyDataEntryComponent,
        props: true,
      },

      // View Study inside Dashboard layout
      {
        path: "studies/:id/view",
        name: "StudyView",
        component: StudyView,
        props: true,
      },

    ],
  },
  //  {
  //    path: "/dashboard/view-yaml/:category/:fileName",
  //    name: "YamlViewer",
  //    component: YamlViewerComponent,
  //    props: true,
  //  },

  {
    path: "/studies/:id",
    name: "StudyDetail",
    component: StudyDataEntryComponent,
  },
  {
    path: "/settings",
    name: "StudySettings",
    component: StudySettings,
  },
  {
    path: "/shared/:token",
    name: "SharedForm",
    component: StudyDataEntryComponent,
  },
  {
    path: "/dashboard/study/:id/data",
    name: "StudyDataDashboard",
    component: () => import("@/components/StudyDataDashboard.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/dashboard/export-study/:id",
    name: "ExportStudy",
    component: () => import("@/components/ExportStudy.vue"),
  },
  {
    path: "/dashboard/merge-study/:id",
    name: "MergeStudy",
    component: () => import("@/components/MergeStudy.vue"),
    props: true,
  },

  //  {
  //    path: "/studies/:id",
  //    name: "StudyDataEntry",
  //    component: StudyDataEntryComponent,
  //    props: route => ({ id: Number(route.params.id) })
  //  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
