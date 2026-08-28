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
  margin: 48px auto 0;
  padding: 20px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 210px 1fr;
  gap: 20px;
  align-items: center;
  border: 1px solid #dce6ed;
  border-radius: 10px;
  background: #f2f7fa;
}

.section-heading h2 { margin: 0; color: #23435f; font-size: 17px; }
.section-heading p { margin: 5px 0 0; color: #718497; font-size: 12px; line-height: 1.4; }
.product-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.product-card {
  min-height: 112px;
  padding: 12px;
  display: grid;
  grid-template-columns: 46px 1fr auto;
  align-items: center;
  gap: 10px;
  border: 1px solid #dce6ed;
  border-radius: 8px;
  color: #17324d;
  background: #fff;
  text-decoration: none;
}
.product-card:hover, .product-card:focus-visible { border-color: #8bbddd; outline: 2px solid rgba(18,119,189,.12); }
.product-mark { width: 46px; height: 46px; border-radius: 7px; object-fit: cover; }
.product-copy { display: flex; flex-direction: column; gap: 3px; }
.product-copy strong { font-size: 14px; }
.product-copy span { color: #667b8f; font-size: 11px; line-height: 1.45; }
.card-action { color: #0b6cab; font-weight: 800; }

@media (max-width: 840px) {
  .ecosystem { grid-template-columns: 1fr; }
  .product-grid { grid-template-columns: 1fr; }
}

@media (max-width: 620px) {
  .ecosystem { width: min(100% - 28px, 1080px); margin-top: 36px; padding: 16px; }
}
</style>
