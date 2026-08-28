<template>
  <div class="contact-page">
    <PublicHeader />

    <main>
      <section class="contact-hero">
        <div class="contact-copy">
          <p class="eyebrow">Contact the team</p>
          <h1>Let’s make research data easier to work with.</h1>
          <p class="lead">
            Planning a clinical study, considering case‑e for your team, or interested in collaboration?
            Tell us what you are working on.
          </p>
          <a class="email-button" href="mailto:j.dukart@fz-juelich.de?subject=case-e%20enquiry">
            Email Prof. Jürgen Dukart <span aria-hidden="true">→</span>
          </a>
          <p class="email-address">j.dukart@fz-juelich.de</p>
        </div>

        <aside class="contact-card" aria-label="Helpful links">
          <p class="card-label">Before you write</p>
          <h2>Useful starting points</h2>
          <a href="https://venkateshhs.github.io/case-e-docs/" target="_blank" rel="noopener noreferrer">
            <span class="link-icon" aria-hidden="true">01</span>
            <span><strong>Read the documentation</strong><small>Setup, workflows, and deployment guidance</small></span>
            <b aria-hidden="true">↗</b>
          </a>
          <a href="https://github.com/Biomarker-Development-at-INM7/eCRF" target="_blank" rel="noopener noreferrer">
            <span class="link-icon" aria-hidden="true">02</span>
            <span><strong>Explore the source</strong><small>View case‑e on GitHub</small></span>
            <b aria-hidden="true">↗</b>
          </a>
          <a href="https://www.fz-juelich.de/en/inm/inm-7/research-groups/biomarker-development" target="_blank" rel="noopener noreferrer">
            <span class="link-icon" aria-hidden="true">03</span>
            <span><strong>Meet the research group</strong><small>Biomarker Development at INM-7</small></span>
            <b aria-hidden="true">↗</b>
          </a>
        </aside>
      </section>

      <section class="partners" aria-labelledby="partners-title">
        <div>
          <p class="eyebrow">Collaboration partners</p>
          <h2 id="partners-title">Research works better together.</h2>
        </div>
        <div class="partner-list">
          <a href="https://www.fz-juelich.de/" target="_blank" rel="noopener noreferrer"><span>FZJ</span>Forschungszentrum Jülich</a>
          <a href="https://www.uk-essen.de/" target="_blank" rel="noopener noreferrer"><span>UME</span>Universitätsmedizin Essen</a>
          <a href="https://www.uniklinik-duesseldorf.de/" target="_blank" rel="noopener noreferrer"><span>UKD</span>Universitätsklinikum Düsseldorf</a>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import PublicHeader from "@/components/public/PublicHeader.vue";

export default {
  name: "ContactUsComponent",
  components: { PublicHeader },
};
</script>

<style scoped>
.contact-page { min-height: 100vh; color: #17324d; background: radial-gradient(circle at 86% 8%, #dff2ff 0, transparent 32%), #f7fafc; }
main { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 62px 0 80px; }
.contact-hero { display: grid; grid-template-columns: 1.12fr 0.88fr; align-items: center; gap: clamp(40px, 8vw, 100px); }
.eyebrow { margin: 0 0 10px; color: #0878d1; font-size: 13px; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
h1 { max-width: 720px; margin: 0; font-size: clamp(42px, 6vw, 72px); line-height: 1.02; letter-spacing: -0.052em; }
.lead { max-width: 650px; margin: 24px 0 30px; color: #60758b; font-size: 18px; line-height: 1.65; }
.email-button { display: inline-flex; align-items: center; gap: 18px; padding: 14px 19px; border-radius: 11px; color: #fff; background: #0878d1; box-shadow: 0 12px 24px rgba(8, 120, 209, 0.22); font-weight: 800; text-decoration: none; }
.email-button:hover, .email-button:focus-visible { background: #075eac; outline: 3px solid rgba(8,120,209,.2); outline-offset: 3px; }
.email-address { margin: 11px 0 0 3px; color: #718096; font-size: 13px; }
.contact-card { padding: 28px; border: 1px solid #dce8f3; border-radius: 22px; background: rgba(255,255,255,.9); box-shadow: 0 18px 55px rgba(29, 72, 107, .11); }
.card-label { margin: 0; color: #7c8ea2; font-size: 12px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.contact-card h2 { margin: 7px 0 22px; font-size: 25px; }
.contact-card > a { display: grid; grid-template-columns: 40px 1fr auto; align-items: center; gap: 13px; padding: 15px 0; border-top: 1px solid #e8eef4; color: #17324d; text-decoration: none; }
.link-icon { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 10px; color: #0878d1; background: #eaf5ff; font-size: 11px; font-weight: 900; }
.contact-card strong, .contact-card small { display: block; }.contact-card small { margin-top: 4px; color: #708399; line-height: 1.35; }.contact-card b { color: #0878d1; }
.partners { margin-top: 100px; padding-top: 36px; border-top: 1px solid #d9e5ef; display: grid; grid-template-columns: .65fr 1.35fr; gap: 40px; align-items: start; }
.partners h2 { margin: 0; font-size: 30px; letter-spacing: -.025em; }
.partner-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.partner-list a { min-height: 115px; padding: 18px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; gap: 16px; border: 1px solid #dce8f3; border-radius: 15px; color: #425a70; background: #fff; font-size: 13px; font-weight: 700; line-height: 1.35; text-decoration: none; transition: transform .2s ease, border-color .2s ease; }
.partner-list a:hover, .partner-list a:focus-visible { transform: translateY(-2px); border-color: #83bde8; outline: none; }.partner-list span { color: #0878d1; font-size: 21px; font-weight: 900; letter-spacing: -.04em; }
@media (max-width: 860px) { .contact-hero, .partners { grid-template-columns: 1fr; }.contact-card { max-width: 620px; }.partners { margin-top: 70px; } }
@media (max-width: 620px) { main { width: min(100% - 28px, 1180px); padding-top: 38px; }.partner-list { grid-template-columns: 1fr; }.partner-list a { min-height: 95px; } }
</style>
