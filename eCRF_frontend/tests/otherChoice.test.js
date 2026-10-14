/* eslint-env node */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const babel = require('@babel/core');

function load(relative) {
  const filename = path.resolve(__dirname, '../src', relative);
  let source = fs.readFileSync(filename, 'utf8');
  if (filename.endsWith('.vue')) source = source.match(/<script>([\s\S]*?)<\/script>/)[1];
  const code = babel.transformSync(source, {
    filename, babelrc: false, configFile: false,
    plugins: ['@babel/plugin-transform-modules-commonjs'],
  }).code;
  const module = { exports: {} };
  new Function('module', 'exports', 'require', code)(module, module.exports,
    name => name.startsWith('@/') ? load(name.slice(2) + '.js') : require(name));
  return module.exports;
}

function instance(component, props) {
  const vm = { $attrs: {}, $refs: {}, $nextTick: fn => fn() };
  for (const [key, definition] of Object.entries(component.props)) {
    vm[key] = typeof definition.default === 'function' ? definition.default() : definition.default;
  }
  Object.assign(vm, props, component.data ? component.data() : {});
  for (const [key, method] of Object.entries(component.methods)) vm[key] = method.bind(vm);
  for (const [key, getter] of Object.entries(component.computed)) {
    Object.defineProperty(vm, key, typeof getter === 'function'
      ? { get: getter.bind(vm) }
      : { get: getter.get.bind(vm), set: getter.set.bind(vm) });
  }
  vm.$emit = (event, value) => {
    if (event !== 'update:modelValue') return;
    vm.modelValue = value;
    component.watch.modelValue.handler.call(vm);
  };
  component.mounted.call(vm);
  return vm;
}

const radio = load('components/fields/FieldRadioGroup.vue').default;
const select = load('components/fields/FieldSelect.vue').default;
for (const component of [radio, select]) {
  const vm = instance(component, {
    options: ['A', 'Other'], defaultValue: 'A', allowOther: false,
  });
  assert.equal(vm.modelValue, 'A', 'Standard defaults must remain unchanged');
  assert.deepEqual(vm.stringOptions, ['A', 'Other'], 'Ordinary Other labels must remain standard options');
  assert.equal(vm.otherActive, false);
  vm.options = ['B'];
  component.watch.options.call(vm);
  assert.equal(vm.modelValue, '', 'Invalid standard choices must still be cleared');
}
for (const component of [radio, select]) {
  const existing = instance(component, { options: ['Other', 'A'], allowOther: true });
  assert.deepEqual(existing.stringOptions, ['A'], 'Existing Other must not be duplicated');
  const vm = instance(component, { options: ['A', 'None'], allowOther: true, modelValue: 'Custom answer' });
  assert.equal(vm.otherText, 'Custom answer', 'Saved free text must survive mounting');
  component.watch.options.call(vm);
  assert.equal(vm.modelValue, 'Custom answer', 'Option refresh must preserve free text');
  vm.modelValue = 'A';
  component.watch.modelValue.handler.call(vm);
  assert.equal(vm.otherActive, false, 'External replacement must close Other');
}
const single = instance(radio, { options: ['A'], allowOther: true });
single.onSelectOther();
single.onOtherInput('My answer');
assert.equal(single.modelValue, 'My answer');
single.onSelectSingle('A');
assert.equal(single.otherActive, false);
assert.equal(single.modelValue, 'A');
const multi = instance(radio, {
  options: ['A', 'None'], allowOther: true, allowMultiple: true,
  dominantOptions: ['None'], modelValue: ['A', 'Custom'],
});
assert.deepEqual(multi.modelValue, ['A', 'Custom']);
multi.onToggleMulti('None', true);
assert.deepEqual(multi.modelValue, ['None']);
assert.equal(multi.otherActive, false);
multi.onToggleOther(true);
multi.onOtherInput('A');
multi.onOtherInput('Apple');
assert.deepEqual(multi.modelValue, ['Apple'], 'Typing through a standard label must not select it');
multi.onOtherInput('Another answer');
assert.deepEqual(multi.modelValue, ['Another answer']);
multi.onToggleOther(false);
assert.deepEqual(multi.modelValue, []);
const dropdown = instance(select, { options: ['A'], allowOther: true });
dropdown.proxy = dropdown.otherToken;
assert.equal(dropdown.otherActive, true);
dropdown.updateOther('Custom');
assert.equal(dropdown.modelValue, 'Custom');
dropdown.proxy = 'A';
assert.equal(dropdown.otherActive, false);
dropdown.disabled = true;
dropdown.updateOther('Must not save');
assert.equal(dropdown.modelValue, 'A');

const { normalizeConstraints } = load('utils/constraints.js');
const { createAjv, validateFieldValue } = load('utils/jsonschemaValidation.js');
const ajv = createAjv();
for (const type of ['radio', 'select']) {
  assert.equal(normalizeConstraints(type, { allowOther: true }).allowOther, true);
  const field = { type, options: ['A'], constraints: { allowOther: true, required: true } };
  assert.equal(validateFieldValue(ajv, field, 'Custom').valid, true);
  assert.equal(validateFieldValue(ajv, field, '').valid, false);
  field.constraints.allowOther = false;
  assert.equal(validateFieldValue(ajv, field, 'Custom').valid, false);
}
console.log('Other choice tests passed');
