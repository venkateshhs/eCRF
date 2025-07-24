/**
 * Turns "first_name" → "First name", "user_id" → "User id", "title" → "Title", etc.
 */
export function formatLabel(key) {
  if (typeof key !== 'string') return ''
  // replace underscores with spaces
  let s = key.replace(/_/g, ' ')
  // lowercase everything, then uppercase first letter
  s = s.toLowerCase().replace(/^\w/, c => c.toUpperCase())
  return s
}
export default {
  install(app) {
    // expose as this.$formatLabel() in options API & templates
    app.config.globalProperties.$formatLabel = formatLabel
    // also make injectable in composition API
    app.provide('formatLabel', formatLabel)
  }
}