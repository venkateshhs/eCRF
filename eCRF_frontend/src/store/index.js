import { createStore } from "vuex";

const store = createStore({
  state: {
    user: null,
  },
  mutations: {
    setUser(state, user) {
      state.user = user;
    },
  },
  actions: {
    login({ commit }, user) {
      if (user.username === "admin" && user.password === "admin123") {
        commit("setUser", user);
        return true;
      }
      return false;
    },
    register(_, user) {
      console.log("Register user", user);
      return true;
    },
  },
});

export default store;
