// src/components/form/index.js

import BaseTextField   from './BaseTextField.vue'
import BaseTextarea    from './BaseTextarea.vue'
import BaseNumberField from './BaseNumberField.vue'
import BaseDateField   from './BaseDateField.vue'
import BaseSelectField from './BaseSelectField.vue'

export default {
  install(app) {
    app.component('BaseTextField',   BaseTextField)
    app.component('BaseTextarea',    BaseTextarea)
    app.component('BaseNumberField', BaseNumberField)
    app.component('BaseDateField',   BaseDateField)
    app.component('BaseSelectField', BaseSelectField)
  }
}
