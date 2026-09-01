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

      <div class="support-bands">
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
      </div>
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
.login-page { height: 100vh; height: 100dvh; overflow: hidden; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; color: #17324d; background: #f7fafc; }
main { min-height: 0; padding: clamp(14px, 2.8vh, 28px) 0 8px; display: grid; grid-template-rows: minmax(0, 1fr) auto auto; align-content: stretch; gap: clamp(7px, 1vh, 10px); }
.login-hero { width: min(1080px, calc(100% - 40px)); min-height: 0; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1fr) 350px; gap: clamp(42px, 6vw, 72px); align-items: center; }
.eyebrow { margin: 0 0 7px; color: #0878d1; font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.hero-copy h1 { margin: 0; color: #17324d; font-size: clamp(38px, 4.6vw, 54px); line-height: 1.02; letter-spacing: -.04em; }
.hero-intro { max-width: 560px; margin: 14px 0 0; color: #60758b; font-size: clamp(14px, 1.35vw, 16px); line-height: 1.5; }
.login-container { min-height: clamp(400px, 53vh, 480px); padding: 18px 22px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; border: 1px solid #d9e4ec; border-radius: 11px; background: #fff; box-shadow: 0 10px 28px rgba(27, 70, 104, .09); }
.login-logo { width: 52px; height: 52px; margin-bottom: 7px; border-radius: 8px; object-fit: cover; }
.login-card-heading { margin-bottom: 14px; }
.login-card-heading h2 { margin: 0; color: #17324d; font-size: 22px; }
.login-card-heading p { margin: 3px 0 0; color: #75879a; font-size: 12px; }
.form-group { margin-bottom: 11px; text-align: left; }
label { display: block; margin-bottom: 4px; color: #42566c; font-size: 12px; font-weight: 700; }
input { width: 100%; min-height: 39px; padding: 8px 11px; box-sizing: border-box; border: 1px solid #cbd9e5; border-radius: 7px; background: #fbfdff; color: #17324d; font-size: 13px; }
input:focus { border-color: #0878d1; outline: 3px solid rgba(8,120,209,.12); }
.password-wrapper { position: relative; }
.password-wrapper input { padding-right: 62px; }
.toggle-password { position: absolute; top: 50%; right: 8px; transform: translateY(-50%); padding: 7px; border: 0; color: #0878d1; background: transparent; cursor: pointer; font-size: 11px; font-weight: 800; }
.toggle-password:hover, .toggle-password:focus-visible { text-decoration: underline; outline: none; }
.btn-login { width: 100%; min-height: 39px; margin-top: 1px; border: 0; border-radius: 7px; color: #fff; background: #0878d1; cursor: pointer; font-size: 13px; font-weight: 800; }
.btn-login:hover, .btn-login:focus-visible { background: #075eac; outline: 3px solid rgba(8,120,209,.18); outline-offset: 2px; }
.login-links { margin-top: 11px; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 11px; }
.login-links a { color: #0878d1; font-weight: 700; text-decoration: none; }
.login-links a:hover { text-decoration: underline; }
.login-links span { color: #a1afbd; }
.error { margin: 8px 0 0; padding: 7px 9px; border-radius: 7px; color: #a62727; background: #fff0f0; font-size: 11px; line-height: 1.3; }
.support-bands { width: min(1080px, calc(100% - 40px)); margin: 0 auto; border-top: 1px solid #d9e5ed; border-bottom: 1px solid #d9e5ed; }
.partners { min-height: 38px; display: flex; align-items: center; gap: 24px; }
.partners h2 { flex: 0 0 auto; margin: 0; color: #667b8f; font-size: 10px; letter-spacing: .07em; text-transform: uppercase; }
.partner-grid { flex: 1; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px 18px; }
.partner-grid a { color: #405a70; font-size: 11px; font-weight: 700; text-decoration: none; }
.partner-grid a:hover, .partner-grid a:focus-visible { color: #0878d1; text-decoration: underline; outline: none; }
.contact-strip { min-height: 32px; display: flex; align-items: center; justify-content: space-between; gap: 20px; border-top: 1px solid #e3ebf1; color: #61768a; font-size: 11px; }
.contact-strip p { margin: 0; }
.contact-strip a { color: #0878d1; font-weight: 800; text-decoration: none; }
.contact-strip a:hover { text-decoration: underline; }
.login-build-footer { position: static; padding: 5px 12px; font-size: 10px; line-height: 1.2; }

@media (max-height: 800px) and (min-width: 841px) {
  .login-container { min-height: 390px; }
}

@media (max-height: 760px) and (min-width: 761px) {
  main { padding-top: 10px; gap: 7px; }
  .login-container { min-height: 0; padding: 12px 18px; }
  .login-logo { width: 40px; height: 40px; margin-bottom: 4px; }
  .login-card-heading { margin-bottom: 9px; }
  .form-group { margin-bottom: 7px; }
  input, .btn-login { min-height: 34px; }
  .login-links { margin-top: 7px; }
}

@media (max-width: 760px) {
  main { padding: 8px 0 4px; gap: 6px; }
  .login-hero { width: min(100% - 24px, 680px); grid-template-columns: minmax(0, 1fr) minmax(245px, 44%); gap: 18px; }
  .hero-copy h1 { font-size: clamp(25px, 7vw, 36px); }
  .hero-intro { margin-top: 8px; font-size: 11px; line-height: 1.35; }
  .eyebrow { margin-bottom: 4px; font-size: 9px; }
  .login-container { min-height: 0; padding: 12px 14px; }
  .login-logo { width: 38px; height: 38px; margin-bottom: 3px; }
  .login-card-heading { margin-bottom: 8px; }
  .login-card-heading h2 { font-size: 17px; }
  .login-card-heading p { font-size: 9px; }
  .form-group { margin-bottom: 6px; }
  label { margin-bottom: 2px; font-size: 9px; }
  input, .btn-login { min-height: 32px; padding-block: 6px; font-size: 10px; }
  .toggle-password { font-size: 9px; }
  .login-links { margin-top: 6px; gap: 5px; font-size: 8px; }
  .support-bands { width: min(100% - 24px, 680px); }
  .partners { min-height: 30px; gap: 10px; }
  .partners h2, .partner-grid a, .contact-strip { font-size: 8px; }
  .partner-grid { gap: 4px 9px; }
  .contact-strip { min-height: 25px; }
}

@media (max-width: 520px) {
  main { grid-template-rows: auto auto minmax(0, 1fr); }
  .login-hero { grid-template-columns: 1fr; grid-template-rows: auto auto; gap: 6px; align-content: center; }
  .hero-copy { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 0 10px; align-items: end; }
  .eyebrow { grid-column: 1 / -1; }
  .hero-copy h1 { font-size: 22px; }
  .hero-intro { margin: 0; font-size: 8px; }
  .login-container { padding: 8px 10px; display: grid; grid-template-columns: 32px 1fr; gap: 0 7px; }
  .login-logo { width: 30px; height: 30px; margin: 0; }
  .login-card-heading { margin: 0; align-self: center; }
  .login-card-heading h2 { font-size: 14px; }
  .login-form, .login-links, .error { grid-column: 1 / -1; }
  .login-form { margin-top: 6px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px 7px; }
  .form-group { min-width: 0; margin: 0; }
  .btn-login { grid-column: 1 / -1; }
  input, .btn-login { min-height: 27px; }
  .partners { align-items: flex-start; padding: 5px 0; }
  .support-bands { align-self: end; }
  .partner-grid { justify-content: flex-start; }
  .contact-strip { gap: 6px; }
  .contact-strip p { max-width: 55%; }
}
</style>
