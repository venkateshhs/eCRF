<template>
  <div class="login-page">
    <PublicHeader />

    <main>
      <section class="login-hero">
        <div class="hero-copy">
          <p class="eyebrow">Electronic data capture</p>
          <h1>Clinical data capture,<br />made clear.</h1>
          <p class="hero-intro">
            Design flexible eCRFs, capture structured clinical data, and manage studies in one traceable electronic data capture workspace.
          </p>
        </div>

        <aside class="login-container" aria-labelledby="login-title">
          <img class="login-logo" src="../assets/Logo_CaseE.png" alt="case-e" />
          <div class="login-card-heading">
            <h2 id="login-title">Sign in to case‑e</h2>
            <p>Access your study workspace</p>
          </div>
          <form class="login-form" @submit.prevent="handleLogin">
            <div class="form-group">
              <label for="username">Username</label>
              <input id="username" v-model="username" type="text" autocomplete="username" placeholder="Enter your username" />
            </div>
            <div class="form-group">
              <label for="password">Password</label>
              <div class="password-wrapper">
                <input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Enter your password" />
                <button type="button" class="toggle-password" @click="togglePasswordVisibility">
                  {{ showPassword ? "Hide" : "Show" }}
                </button>
              </div>
            </div>
            <button type="submit" class="btn-login">Sign in</button>
          </form>
          <div class="login-links">
            <router-link to="/forgot-password">Forgot password?</router-link>
            <span aria-hidden="true">·</span>
            <router-link to="/register">Create account</router-link>
          </div>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
        </aside>
      </section>

      <EcosystemShowcase />

      <section class="partners" aria-labelledby="partner-title">
        <h2 id="partner-title">Collaboration partners</h2>
        <div class="partner-grid">
          <a href="https://www.fz-juelich.de/" target="_blank" rel="noopener noreferrer">Forschungszentrum Jülich</a>
          <a href="https://www.uk-essen.de/" target="_blank" rel="noopener noreferrer">Universitätsmedizin Essen</a>
          <a href="https://www.uniklinik-duesseldorf.de/" target="_blank" rel="noopener noreferrer">Universitätsklinikum Düsseldorf</a>
        </div>
      </section>

      <section class="contact-strip">
        <p>Questions about case‑e or interested in collaboration?</p>
        <router-link to="/contact">Contact the case‑e team →</router-link>
      </section>
    </main>
    <BuildInfoFooter class="login-build-footer" />
  </div>
</template>

<script>
import BuildInfoFooter from "@/components/BuildInfoFooter.vue";
import PublicHeader from "@/components/public/PublicHeader.vue";
import EcosystemShowcase from "@/components/public/EcosystemShowcase.vue";

export default {
  name: "LoginComponent",
  components: { BuildInfoFooter, PublicHeader, EcosystemShowcase },
  data() {
    return {
      username: "",
      password: "",
      showPassword: false,
      error: null,
    };
  },
  methods: {
    togglePasswordVisibility() {
      this.showPassword = !this.showPassword;
    },
    async handleLogin() {
      this.error = null;

      try {
        const success = await this.$store.dispatch("login", {
          username: this.username,
          password: this.password,
        });

        if (success) {
          const user = this.$store.getters.getUser;
          if (user?.must_change_password) {
            this.$router.push("/dashboard/user-info");
          } else {
            this.$router.push("/dashboard");
          }
        } else {
          this.error = "Invalid username or password.";
        }
      } catch (error) {
        if (error.response && error.response.status) {
          const { status, data } = error.response;
          if (status === 403) {
            this.error = "Your account does not have permission to access this application.";
          } else if (status === 400) {
            this.error = "Invalid username or password.";
          } else {
            this.error = data?.detail || "An unexpected error occurred. Please try again.";
          }
        } else {
          this.error = "Unable to reach server. Please try again.";
        }
      }
    },
  },
};
</script>

<style scoped>
.login-page { min-height: 100vh; color: #17324d; background: #f7fafc; }
main { padding: 48px 0 56px; }
.login-hero { width: min(1080px, calc(100% - 40px)); margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1fr) 390px; gap: 72px; align-items: center; }
.eyebrow { margin: 0 0 9px; color: #0878d1; font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.hero-copy h1 { margin: 0; color: #17324d; font-size: clamp(40px, 5vw, 58px); line-height: 1.04; letter-spacing: -.04em; }
.hero-intro { max-width: 560px; margin: 18px 0 0; color: #60758b; font-size: 17px; line-height: 1.6; }
.login-container { padding: 28px; border: 1px solid #d9e4ec; border-radius: 12px; background: #fff; box-shadow: 0 12px 32px rgba(27, 70, 104, .1); }
.login-logo { width: 74px; height: 74px; margin-bottom: 14px; border-radius: 10px; object-fit: cover; }
.login-card-heading { margin-bottom: 24px; }
.login-card-heading h2 { margin: 0; color: #17324d; font-size: 24px; }
.login-card-heading p { margin: 6px 0 0; color: #75879a; font-size: 13px; }
.form-group { margin-bottom: 18px; text-align: left; }
label { display: block; margin-bottom: 7px; color: #42566c; font-size: 13px; font-weight: 700; }
input { width: 100%; min-height: 44px; padding: 10px 12px; box-sizing: border-box; border: 1px solid #cbd9e5; border-radius: 7px; background: #fbfdff; color: #17324d; font-size: 14px; }
input:focus { border-color: #0878d1; outline: 3px solid rgba(8,120,209,.12); }
.password-wrapper { position: relative; }
.password-wrapper input { padding-right: 62px; }
.toggle-password { position: absolute; top: 50%; right: 8px; transform: translateY(-50%); padding: 7px; border: 0; color: #0878d1; background: transparent; cursor: pointer; font-size: 12px; font-weight: 800; }
.toggle-password:hover, .toggle-password:focus-visible { text-decoration: underline; outline: none; }
.btn-login { width: 100%; min-height: 44px; margin-top: 2px; border: 0; border-radius: 7px; color: #fff; background: #0878d1; cursor: pointer; font-size: 14px; font-weight: 800; }
.btn-login:hover, .btn-login:focus-visible { background: #075eac; outline: 3px solid rgba(8,120,209,.18); outline-offset: 2px; }
.login-links { margin-top: 18px; display: flex; align-items: center; justify-content: center; gap: 9px; font-size: 13px; }
.login-links a { color: #0878d1; font-weight: 700; text-decoration: none; }
.login-links a:hover { text-decoration: underline; }
.login-links span { color: #a1afbd; }
.error { margin: 15px 0 0; padding: 10px 12px; border-radius: 7px; color: #a62727; background: #fff0f0; font-size: 13px; line-height: 1.4; }
.partners { width: min(1080px, calc(100% - 40px)); margin: 42px auto 0; padding: 24px 0; display: flex; align-items: center; gap: 30px; border-top: 1px solid #d9e5ed; border-bottom: 1px solid #d9e5ed; }
.partners h2 { flex: 0 0 auto; margin: 0; color: #667b8f; font-size: 12px; letter-spacing: .07em; text-transform: uppercase; }
.partner-grid { display: flex; align-items: center; flex-wrap: wrap; gap: 14px 28px; }
.partner-grid a { color: #405a70; font-size: 13px; font-weight: 700; text-decoration: none; }
.partner-grid a:hover, .partner-grid a:focus-visible { color: #0878d1; text-decoration: underline; outline: none; }
.contact-strip { width: min(1080px, calc(100% - 40px)); margin: 24px auto 0; display: flex; align-items: center; justify-content: space-between; gap: 20px; color: #61768a; font-size: 14px; }
.contact-strip p { margin: 0; }
.contact-strip a { color: #0878d1; font-weight: 800; text-decoration: none; }
.contact-strip a:hover { text-decoration: underline; }
.login-build-footer { position: static; }

@media (max-width: 900px) {
  .login-hero { grid-template-columns: 1fr; gap: 36px; }
  .login-container { width: min(100%, 500px); box-sizing: border-box; }
}

@media (max-width: 620px) {
  main { padding-top: 30px; }
  .login-hero, .partners, .contact-strip { width: min(100% - 28px, 1080px); }
  .hero-copy h1 { font-size: 40px; }
  .login-container { padding: 22px; }
  .partners, .contact-strip { align-items: flex-start; flex-direction: column; gap: 14px; }
}
</style>
