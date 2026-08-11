/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");
const { parse } = require("@vue/compiler-sfc");

function loadImportStudy(axiosMock) {
  const sourcePath = path.resolve(__dirname, "../src/components/ImportStudy.vue");
  const source = fs.readFileSync(sourcePath, "utf8");
  const { descriptor } = parse(source, { filename: sourcePath });
  const transformed = babel.transformSync(descriptor.script.content, {
    filename: sourcePath,
    cwd: path.resolve(__dirname, ".."),
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const loaded = { exports: {} };
  const requireMock = (request) => {
    if (request === "axios") return axiosMock;
    if (request === "xlsx") return { read: () => ({}), utils: {} };
    if (request === "papaparse") return {};
    if (request === "js-yaml") return {};
    if (request === "vuex") return { useStore: () => ({}) };
    if (request.includes("assets/styles/icons")) return {};
    return {};
  };
  new Function("require", "module", "exports", transformed)(requireMock, loaded, loaded.exports);
  return { component: loaded.exports.default, source };
}

const item = {
  subject_index: 0,
  visit_index: 4,
  group_index: 0,
  data: { imported_fields: { weight: 70 } },
  skipped_required_flags: [],
};

(async () => {
  const calls = [];
  const axiosMock = {
    async get(url, config) {
      calls.push({ method: "get", url, config });
      return { data: { revision_token: "empty-slot-token" } };
    },
    async post(url, data, config) {
      calls.push({ method: "post", url, data, config });
      return { data: { id: 1 } };
    },
  };
  const loaded = loadImportStudy(axiosMock);
  const component = loaded.component;
  assert.match(loaded.source, /Field schema JSON/);
  assert.match(loaded.source, /Download example JSON/);
  await component.methods.postImportedEntry.call({ token: "auth-token" }, 11, item);

  assert.equal(calls.length, 2);
  assert.equal(calls[0].method, "get");
  assert.equal(calls[0].url, "/forms/studies/11/slot-data");
  assert.deepEqual(calls[0].config.params, {
    subject_index: 0,
    visit_index: 4,
    group_index: 0,
  });
  assert.equal(calls[1].method, "post");
  assert.equal(calls[1].url, "/forms/studies/11/data");
  assert.equal(calls[1].config.params.expected_revision_token, "empty-slot-token");
  assert.equal(calls[1].config.params.audit_label, "Study Data Import");

  const legacyCalls = [];
  const legacyAxiosMock = {
    async get() {
      const error = new Error("Not found");
      error.response = { status: 404 };
      throw error;
    },
    async post(url, data, config) {
      legacyCalls.push({ url, data, config });
    },
  };
  const legacyComponent = loadImportStudy(legacyAxiosMock).component;
  await legacyComponent.methods.postImportedEntry.call({ token: "auth-token" }, 12, item);
  assert.equal(legacyCalls.length, 1);
  assert.equal(legacyCalls[0].config.params.expected_revision_token, undefined);

  const methods = component.methods;
  const inferenceContext = {
    isStrictDateValue: methods.isStrictDateValue,
  };
  assert.equal(methods.inferFieldType.call(inferenceContext, ["SITE-01", "SITE-02"]), "text");
  assert.equal(methods.inferFieldType.call(inferenceContext, ["2025-01-01", "2025-12-31"]), "date");
  assert.equal(methods.inferFieldType.call(inferenceContext, ["Yes", "No"]), "checkbox");
  assert.equal(methods.isStrictDateValue("2025-02-29"), false);

  let generatedId = 0;
  const importStructureContext = {
    resolvedImportFields: new Map(),
    mapping: { otherCols: ["Assessment Date"] },
    rows: [{ "Assessment Date": "2026-08-10" }],
    columnMeta: new Map([
      ["Assessment Date", { section: "Visit Information", name: "assessment_date", field: "Assessment Date" }],
    ]),
    fieldSchema: null,
    fieldSchemaDefinitionForColumn: methods.fieldSchemaDefinitionForColumn,
    inferFieldType: methods.inferFieldType,
    isStrictDateValue: methods.isStrictDateValue,
    uuidForImport: () => `generated-${++generatedId}`,
  };
  const importedModels = methods.buildSelectedModels.call(importStructureContext);
  assert.equal(importedModels[0]._id, "generated-2");
  assert.equal(importedModels[0].fields[0]._id, "generated-1");

  const normalizedSchema = methods.normalizeFieldSchemaDocument({
    version: 1,
    fields: [
      {
        column: "Assessment Date",
        type: "date",
        section: "Visit Information",
        constraints: { dateFormat: "yyyy-MM-dd" },
      },
      { column: "Site Code", type: "text", section: "Visit Information", required: true },
      { column: "Pain Score", type: "integer", min: 0, max: 10 },
      { column: "Adverse Event", type: "boolean" },
    ],
  });
  assert.equal(normalizedSchema.fields[1].constraints.required, true);
  assert.equal(normalizedSchema.fields[2].type, "number");
  assert.equal(normalizedSchema.fields[2].constraints.max, 10);
  assert.equal(normalizedSchema.fields[3].type, "checkbox");

  const schemaContext = {
    fieldSchema: normalizedSchema,
    headers: ["Subject ID", "Group", "Visit", "Assessment Date", "Site Code", "Pain Score", "Adverse Event"],
    mapping: {
      subject: { idCol: "Subject ID", dateCol: "Assessment Date" },
      group: { nameCol: "Group" },
      visit: { nameCol: "Visit" },
      otherCols: [],
    },
    otherFieldCandidates: ["Assessment Date", "Site Code", "Pain Score", "Adverse Event"],
    fieldSchemaError: "",
    fieldSchemaAppliedCount: 0,
    otherAllSelected: false,
  };
  methods.applyFieldSchemaToCurrentHeaders.call(schemaContext);
  assert.deepEqual(schemaContext.mapping.otherCols, [
    "Assessment Date", "Site Code", "Pain Score", "Adverse Event",
  ]);
  assert.equal(schemaContext.fieldSchemaAppliedCount, 4);

  const modelContext = {
    mapping: { otherCols: schemaContext.mapping.otherCols },
    rows: [{
      "Assessment Date": "2025-01-01",
      "Site Code": "SITE-01",
      "Pain Score": "7",
      "Adverse Event": "No",
    }],
    columnMeta: new Map(schemaContext.mapping.otherCols.map((column) => [column, {
      section: "Imported Fields",
      field: column,
      name: column.toLowerCase().replace(/\s+/g, "_"),
    }])),
    fieldSchema: normalizedSchema,
    fieldSchemaDefinitionForColumn(column) {
      return methods.fieldSchemaDefinitionForColumn.call(this, column);
    },
    inferFieldType(samples) {
      return methods.inferFieldType.call(inferenceContext, samples);
    },
    uuidForImport: methods.uuidForImport,
  };
  const selectedModels = methods.buildSelectedModels.call(modelContext);
  const importedFields = selectedModels.flatMap((section) => section.fields);
  assert.equal(importedFields.find((field) => field.name === "site_code").type, "text");
  assert.equal(importedFields.find((field) => field.name === "assessment_date").constraints.dateFormat, "yyyy-MM-dd");
  assert.equal(importedFields.find((field) => field.name === "adverse_event").type, "checkbox");

  modelContext.normalizeImportedFieldValue = methods.normalizeImportedFieldValue;
  const packed = methods.packRowDataToDict.call(modelContext, modelContext.rows[0]);
  assert.equal(packed["Visit Information"].assessment_date, "2025-01-01");
  assert.equal(packed["Visit Information"].site_code, "SITE-01");
  assert.equal(packed["Imported Fields"].pain_score, 7);
  assert.equal(packed["Imported Fields"].adverse_event, false);

  assert.throws(
    () => methods.normalizeFieldSchemaDocument({ fields: [{ column: "Site Code", type: "mystery" }] }),
    /Unsupported type/
  );

  console.log("Import Study revision-token regression tests passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
