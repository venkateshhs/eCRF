<template>
  <section class="ecosystem" aria-labelledby="ecosystem-title">
    <div class="section-heading">
      <h2 id="ecosystem-title">Digital research platform</h2>
      <p>Other tools from the Biomarker Development Group</p>
    </div>

    <div class="product-grid">
      <a class="product-card" href="https://jdash.inm7.de/en/login/" target="_blank" rel="noopener noreferrer">
        <img class="product-mark" src="../../assets/products/jdash.png" alt="" />
        <span class="product-copy"><strong>JDash</strong><span>JTrack Digital Platform</span></span>
        <span class="card-action" aria-hidden="true">↗</span>
      </a>

      <a class="product-card" href="https://apps.apple.com/de/app/jtrack-ema/id1605100657" target="_blank" rel="noopener noreferrer">
        <img class="product-mark" src="../../assets/products/jtrack-ema.jpeg" alt="" />
        <span class="product-copy"><strong>JTrack EMA</strong><span>Collect ecological momentary assessments, daily symptoms, and study questionnaires directly from participants in real-world settings.</span></span>
        <span class="card-action" aria-hidden="true">↗</span>
      </a>

      <a class="product-card" href="https://apps.apple.com/de/app/jtrack-social/id1645319896" target="_blank" rel="noopener noreferrer">
        <img class="product-mark" src="../../assets/products/jtrack-social.jpeg" alt="" />
        <span class="product-copy"><strong>JTrack Social</strong><span>Track social interaction, activity context, and daily-life behavior patterns for longitudinal digital health research.</span></span>
        <span class="card-action" aria-hidden="true">↗</span>
      </a>
    </div>
  </section>
</template>

<script>
export default {
  name: "EcosystemShowcase",
};
</script>

<style scoped>
.ecosystem {
  width: min(1080px, calc(100% - 40px));
  min-height: 150px;
  margin: 0 auto;
  padding: 10px 12px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 190px 1fr;
  gap: 12px;
  align-items: center;
  border: 1px solid #dce6ed;
  border-radius: 10px;
  background: #f2f7fa;
}

.section-heading h2 { margin: 0; color: #23435f; font-size: 14px; }
.section-heading p { margin: 3px 0 0; color: #718497; font-size: 10px; line-height: 1.3; }
.product-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.product-card {
  min-height: 128px;
  padding: 8px;
  display: grid;
  grid-template-columns: 36px 1fr auto;
  align-items: center;
  gap: 8px;
  border: 1px solid #dce6ed;
  border-radius: 8px;
  color: #17324d;
  background: #fff;
  text-decoration: none;
}
.product-card:hover, .product-card:focus-visible { border-color: #8bbddd; outline: 2px solid rgba(18,119,189,.12); }
.product-mark { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; }
.product-copy { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.product-copy strong { font-size: 12px; }
.product-copy span { display: -webkit-box; overflow: hidden; color: #667b8f; font-size: 9px; line-height: 1.3; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.card-action { color: #0b6cab; font-weight: 800; }

@media (max-width: 840px) {
  .ecosystem { width: min(100% - 24px, 680px); min-height: 0; grid-template-columns: 145px 1fr; gap: 8px; padding: 7px 8px; }
  .section-heading h2 { font-size: 11px; }
  .section-heading p { font-size: 8px; }
  .product-card { min-height: 51px; padding: 6px; grid-template-columns: 27px 1fr; gap: 5px; }
  .product-mark { width: 27px; height: 27px; }
  .product-copy strong { font-size: 9px; }
  .product-copy span { font-size: 7px; }
  .card-action { display: none; }
}

@media (max-width: 620px) {
  .ecosystem { grid-template-columns: 105px 1fr; }
  .product-grid { gap: 4px; }
  .product-card { min-height: 44px; display: flex; flex-direction: column; align-items: flex-start; }
  .product-mark { width: 22px; height: 22px; }
  .product-copy span { display: none; }
}
</style>
