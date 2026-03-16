<template>
    <div v-if="showLegendDialog" class="mini-overlay" @click.self="$emit('close-legend')">
      <div class="mini-dialog" role="dialog" aria-modal="true">
        <div class="mini-head">
          <h4 class="mini-title">Legend</h4>
          <button class="mini-close" @click="$emit('close-legend')" aria-label="Close">✕</button>
        </div>
        <ul class="mini-list">
          <li><span class="legend-swatch swatch-none"></span> None — no data saved yet.</li>
          <li><span class="legend-swatch swatch-partial"></span> Partial — some fields filled.</li>
          <li><span class="legend-swatch swatch-complete"></span> Complete — all assigned fields filled.</li>
          <li><span class="legend-swatch swatch-skipped"></span> Skipped — one or more required fields were skipped.</li>
        </ul>
      </div>
    </div>

    <div v-if="showStatusLegend" class="mini-overlay" @click.self="$emit('close-status-legend')">
      <div class="mini-dialog" role="dialog" aria-modal="true">
        <div class="mini-head">
          <h4 class="mini-title">Selection Status</h4>
          <button class="mini-close" @click="$emit('close-status-legend')" aria-label="Close">✕</button>
        </div>
        <ul class="mini-list legend-explain">
          <li><span class="legend-swatch swatch-none"></span> None — no data saved yet.</li>
          <li><span class="legend-swatch swatch-partial"></span> Partial — some fields filled.</li>
          <li><span class="legend-swatch swatch-complete"></span> Complete — all assigned fields filled.</li>
          <li><span class="legend-swatch swatch-skipped"></span> Skipped — one or more required fields were skipped.</li>
        </ul>
      </div>
    </div>
</template>

<script>
export default {
  name: "StudyLegendDialogs",
  props: {
    showLegendDialog: { type: Boolean, default: false },
    showStatusLegend: { type: Boolean, default: false },
  },
  emits: ["close-legend", "close-status-legend"],
};
</script>

<style scoped>
.mini-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.mini-dialog {
  width: 360px;
  max-width: 92%;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  padding: 12px 12px 10px;
}
.mini-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.mini-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}
.mini-close {
  background: transparent;
  border: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}
.mini-close:hover {
  color: #111827;
}
.mini-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 14px;
}
.mini-list li {
  margin: 4px 0;
}
.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  display: inline-block;
  margin-right: 8px;
  vertical-align: -1px;
}
.swatch-none {
  background: #e5e7eb;
}
.swatch-partial {
  background: #fbbf24;
}
.swatch-complete {
  background: #16a34a;
}
.swatch-skipped {
  background: #ef4444;
}
.legend-explain li {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>