<template>
  <header class="public-header">
    <div class="header-inner">
      <router-link class="brand" to="/login" aria-label="case-e home">
        <img src="../../assets/logo.png" alt="Forschungszentrum Jülich" />
      </router-link>

      <nav aria-label="Public navigation">
        <a href="https://venkateshhs.github.io/case-e-docs/" target="_blank" rel="noopener noreferrer">Docs</a>
        <a href="https://github.com/Biomarker-Development-at-INM7/eCRF" target="_blank" rel="noopener noreferrer">GitHub</a>
        <router-link class="contact-link" to="/contact">Contact</router-link>
      </nav>
    </div>
  </header>
</template>

<script>
export default {
  name: "PublicHeader",
};
</script>

<style scoped>
.public-header {
  width: 100%;
  border-bottom: 1px solid #d9e4ec;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 16px rgba(27, 70, 104, 0.05);
}

.header-inner {
  width: min(1180px, calc(100% - 40px));
  min-height: 60px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.brand {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #17324d;
  text-decoration: none;
}

.brand img {
  flex: 0 0 auto;
  width: 136px;
  height: auto;
  display: block;
}

nav {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

nav a {
  padding: 8px 10px;
  border-radius: 8px;
  color: #42526b;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.2s ease, background 0.2s ease;
}

nav a:hover,
nav a:focus-visible {
  color: #075eac;
  background: #eaf4ff;
  outline: none;
}

nav .contact-link {
  margin-left: 4px;
  padding-inline: 16px;
  color: #fff;
  background: #0878d1;
}

nav .contact-link:hover,
nav .contact-link:focus-visible {
  color: #fff;
  background: #075eac;
}

@media (max-width: 720px) {
  .header-inner {
    width: min(100% - 28px, 1180px);
    min-height: 52px;
    padding: 0;
  }

  .brand img { width: 112px; }
  nav { gap: 2px; }
  nav a { padding: 7px 8px; font-size: 13px; }
}

@media (max-width: 520px) {
  .header-inner { width: calc(100% - 20px); gap: 8px; }
  .brand img { width: 94px; }
  nav { width: auto; flex: 0 0 auto; flex-wrap: nowrap; justify-content: flex-end; }
  nav a { padding: 6px 5px; font-size: 10px; }
  nav .contact-link { padding-inline: 8px; }
  nav .contact-link { margin-left: 0; }
}
</style>
