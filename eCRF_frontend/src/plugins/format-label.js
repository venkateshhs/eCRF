// src/plugins/format-label.js
export function formatLabel(key) {
  if (typeof key !== 'string') return ''
  let s = key
    .replace(/_/g, ' ')                     // underscores → spaces
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2') // camel/Pascal → spaced
    .replace(/([A-Za-z])(\d)/g, '$1 $2')    // word-digit boundary
    .replace(/\s+/g, ' ')                   // collapse spaces
    .trim()
  // Title Case each word
  s = s.replace(/\b\w/g, c => c.toUpperCase())
  return s
}
export default {
  install(app) {
    app.config.globalProperties.$formatLabel = formatLabel
    app.provide('formatLabel', formatLabel)
  }
}
