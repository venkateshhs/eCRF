/* eslint-env node */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");

function loadConflictModule() {
  const sourcePath = path.resolve(__dirname, "../src/utils/dataEntryConflict.js");
  const transformed = babel.transformSync(fs.readFileSync(sourcePath, "utf8"), {
    filename: sourcePath,
    cwd: path.resolve(__dirname, ".."),
    babelrc: false,
    configFile: false,
    plugins: ["@babel/plugin-transform-modules-commonjs"],
  }).code;
  const loaded = { exports: {} };
  new Function("module", "exports", "require", transformed)(
    loaded,
    loaded.exports,
    require
  );
  return loaded.exports;
}

const {
  applyConflictDecisions,
  mergeDataEntryFields,
} = loadConflictModule();

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function createLongForm(sectionCount = 100, fieldsPerSection = 50) {
  const data = {};
  for (let section = 0; section < sectionCount; section += 1) {
    const sectionKey = `Section ${section + 1}`;
    data[sectionKey] = {};
    for (let field = 0; field < fieldsPerSection; field += 1) {
      data[sectionKey][`field-${field + 1}`] = "";
    }
  }
  return data;
}

function mergeAndRequireNoConflict(base, local, latest, label) {
  const result = mergeDataEntryFields(base, local, latest);
  assert.equal(result.conflicts.length, 0, `${label}: unexpected conflict`);
  return result.merged;
}

// 1. Different sections: both clinicians' changes survive.
{
  const base = { Vitals: { pulse: "" }, Medication: { dose: "" } };
  const latest = clone(base);
  latest.Vitals.pulse = 72;
  const local = clone(base);
  local.Medication.dose = "5 mg";
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "different sections"),
    { Vitals: { pulse: 72 }, Medication: { dose: "5 mg" } }
  );
}

// 2. Different fields in the same section: both survive.
{
  const base = { Vitals: { pulse: "", temperature: "" } };
  const latest = { Vitals: { pulse: 72, temperature: "" } };
  const local = { Vitals: { pulse: "", temperature: 37.1 } };
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "same section"),
    { Vitals: { pulse: 72, temperature: 37.1 } }
  );
}

// 3. Same field, different values: exactly one genuine conflict.
{
  const base = { Vitals: { pulse: 70 } };
  const latest = { Vitals: { pulse: 72 } };
  const local = { Vitals: { pulse: 75 } };
  const result = mergeDataEntryFields(base, local, latest);
  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].sectionKey, "Vitals");
  assert.equal(result.conflicts[0].fieldKey, "pulse");
}

// 4. Same field, same resulting value: no unnecessary dialog.
{
  const base = { Vitals: { pulse: 70 } };
  const local = { Vitals: { pulse: 72 } };
  const latest = { Vitals: { pulse: 72 } };
  assert.equal(mergeDataEntryFields(base, local, latest).conflicts.length, 0);
}

// 5. An untouched local field never blanks a newly saved backend value.
{
  const base = { History: { allergy: "" } };
  const local = clone(base);
  const latest = { History: { allergy: "Penicillin" } };
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "untouched local field"),
    latest
  );
}

// 6. Intentional clearing is preserved when nobody else changed that field.
{
  const base = { History: { note: "Old note", allergy: "" } };
  const local = { History: { note: "", allergy: "" } };
  const latest = { History: { note: "Old note", allergy: "Penicillin" } };
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "intentional clear"),
    { History: { note: "", allergy: "Penicillin" } }
  );
}

// 7. Clearing a field that another user changed is a genuine conflict.
{
  const result = mergeDataEntryFields(
    { History: { note: "Old" } },
    { History: { note: "" } },
    { History: { note: "Updated remotely" } }
  );
  assert.equal(result.conflicts.length, 1);
}

// 8. Six clinicians opened the same revision and save disjoint fields in turn.
{
  const original = {
    Visit: { a: "", b: "", c: "", d: "", e: "", f: "" },
  };
  let latest = clone(original);
  ["a", "b", "c", "d", "e", "f"].forEach((field, index) => {
    const local = clone(original);
    local.Visit[field] = `clinician-${index + 1}`;
    latest = mergeAndRequireNoConflict(
      original,
      local,
      latest,
      `six users, user ${index + 1}`
    );
  });
  assert.deepEqual(latest.Visit, {
    a: "clinician-1",
    b: "clinician-2",
    c: "clinician-3",
    d: "clinician-4",
    e: "clinician-5",
    f: "clinician-6",
  });
}

// 9. Long eCRF: 5,000 fields and ten clinicians with stale forms.
{
  const original = createLongForm();
  let latest = clone(original);
  for (let user = 0; user < 10; user += 1) {
    const local = clone(original);
    for (let edit = 0; edit < 20; edit += 1) {
      const section = `Section ${user * 10 + (edit % 10) + 1}`;
      const field = `field-${edit + 1}`;
      local[section][field] = `user-${user + 1}-value-${edit + 1}`;
    }
    latest = mergeAndRequireNoConflict(
      original,
      local,
      latest,
      `long form, user ${user + 1}`
    );
  }
  assert.equal(Object.keys(latest).length, 100);
  assert.equal(latest["Section 1"]["field-1"], "user-1-value-1");
  assert.equal(latest["Section 100"]["field-20"], "user-10-value-20");
}

// 10. Long-duration session: 25 other saves occur before the clinician saves.
{
  const original = createLongForm(30, 20);
  const longSessionLocal = clone(original);
  longSessionLocal["Section 30"]["field-20"] = "late-session value";
  let latest = clone(original);

  for (let user = 0; user < 25; user += 1) {
    const other = clone(original);
    other[`Section ${(user % 25) + 1}`]["field-1"] = `intervening-${user + 1}`;
    latest = mergeAndRequireNoConflict(
      original,
      other,
      latest,
      `long session intervening save ${user + 1}`
    );
  }

  latest = mergeAndRequireNoConflict(
    original,
    longSessionLocal,
    latest,
    "long session final save"
  );
  assert.equal(latest["Section 30"]["field-20"], "late-session value");
  assert.equal(latest["Section 25"]["field-1"], "intervening-25");
}

// 11. One dialog can contain conflicts from several sections and fields.
{
  const base = {
    Vitals: { pulse: 70, temperature: 36.5 },
    History: { note: "base" },
  };
  const local = {
    Vitals: { pulse: 75, temperature: 37.0 },
    History: { note: "mine" },
  };
  const latest = {
    Vitals: { pulse: 72, temperature: 38.0 },
    History: { note: "theirs" },
  };
  const result = mergeDataEntryFields(base, local, latest);
  assert.equal(result.conflicts.length, 3);
  assert.deepEqual(
    new Set(result.conflicts.map((item) => item.sectionKey)),
    new Set(["Vitals", "History"])
  );
}

// 12. Bulk choice buttons: choosing all local or all latest is deterministic.
{
  const result = mergeDataEntryFields(
    { A: { x: 1, y: 1 } },
    { A: { x: 2, y: 2 } },
    { A: { x: 3, y: 3 } }
  );
  const allLocal = Object.fromEntries(
    result.conflicts.map((item) => [item.key, "local"])
  );
  const allLatest = Object.fromEntries(
    result.conflicts.map((item) => [item.key, "latest"])
  );
  assert.deepEqual(
    applyConflictDecisions(result.merged, result.conflicts, allLocal),
    { A: { x: 2, y: 2 } }
  );
  assert.deepEqual(
    applyConflictDecisions(result.merged, result.conflicts, allLatest),
    { A: { x: 3, y: 3 } }
  );
}

// 13. Tables, file lists and multi-selects are atomic field values.
{
  const base = {
    Complex: {
      table: [{ test: "Hb", value: 10 }],
      files: [{ dbId: 1, name: "a.pdf" }],
      choices: ["A"],
    },
  };
  const local = clone(base);
  local.Complex.table[0].value = 11;
  local.Complex.choices = ["A", "B"];
  const latest = clone(base);
  latest.Complex.files.push({ dbId: 2, name: "b.pdf" });
  const result = mergeDataEntryFields(base, local, latest);
  assert.equal(result.conflicts.length, 0);
  assert.equal(result.merged.Complex.table[0].value, 11);
  assert.equal(result.merged.Complex.files.length, 2);
  assert.deepEqual(result.merged.Complex.choices, ["A", "B"]);
}

// 14. Object key order does not create false conflicts.
{
  const base = { Table: { row: { a: 1, b: 2 } } };
  const local = { Table: { row: { b: 2, a: 1 } } };
  const latest = { Table: { row: { a: 1, b: 2 } } };
  assert.equal(mergeDataEntryFields(base, local, latest).conflicts.length, 0);
}

// 15. A third user saves while the dialog is open; retry merges again safely.
{
  const base = { Vitals: { pulse: 70, temperature: 36.5, weight: 70 } };
  const userTwo = { Vitals: { pulse: 75, temperature: 36.5, weight: 70 } };
  const userOneSaved = { Vitals: { pulse: 72, temperature: 36.5, weight: 70 } };
  const firstAttempt = mergeDataEntryFields(base, userTwo, userOneSaved);
  const resolved = applyConflictDecisions(
    firstAttempt.merged,
    firstAttempt.conflicts,
    { [firstAttempt.conflicts[0].key]: "local" }
  );

  const userThreeSaved = {
    Vitals: { pulse: 72, temperature: 38.0, weight: 70 },
  };
  const retry = mergeDataEntryFields(userOneSaved, resolved, userThreeSaved);
  assert.equal(retry.conflicts.length, 0);
  assert.deepEqual(retry.merged.Vitals, {
    pulse: 75,
    temperature: 38.0,
    weight: 70,
  });
}

// 16. Falsy clinical values (0 and false) are real values, not blanks.
{
  const base = { Scores: { score: "", symptomPresent: "" } };
  const local = { Scores: { score: 0, symptomPresent: "" } };
  const latest = { Scores: { score: "", symptomPresent: false } };
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "falsy values"),
    { Scores: { score: 0, symptomPresent: false } }
  );
}

// 17. Required-field skip flags from different fields merge without loss.
{
  const base = { Required: { consent: false, reason: false } };
  const local = { Required: { consent: true, reason: false } };
  const latest = { Required: { consent: false, reason: true } };
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "required skip flags"),
    { Required: { consent: true, reason: true } }
  );
}

// 18. Date, time, Unicode and decimal values remain exact.
{
  const base = {
    Visit: { date: "", time: "", note: "", decimal: "" },
  };
  const local = {
    Visit: { date: "17.07.2026", time: "", note: "Übelkeit – mäßig", decimal: "" },
  };
  const latest = {
    Visit: { date: "", time: "14:35", note: "", decimal: 0.25 },
  };
  assert.deepEqual(
    mergeAndRequireNoConflict(base, local, latest, "clinical value formats"),
    {
      Visit: {
        date: "17.07.2026",
        time: "14:35",
        note: "Übelkeit – mäßig",
        decimal: 0.25,
      },
    }
  );
}

// 19. A section excluded from a patient's form accepts the clinician's data.
{
  const patientBase = { "Patient questionnaire": { symptom: "" } };
  const patientLocal = { "Patient questionnaire": { symptom: "Mild" } };
  const clinicianLatest = {
    "Patient questionnaire": { symptom: "" },
    "Clinician assessment": { diagnosis: "Confirmed" },
  };
  assert.deepEqual(
    mergeAndRequireNoConflict(
      patientBase,
      patientLocal,
      clinicianLatest,
      "patient-inaccessible clinician section"
    ),
    {
      "Patient questionnaire": { symptom: "Mild" },
      "Clinician assessment": { diagnosis: "Confirmed" },
    }
  );
}

// 20. Equivalent blank representations do not create false conflicts.
{
  const result = mergeDataEntryFields(
    { Empty: { text: null, files: [] } },
    { Empty: { text: "", files: null } },
    { Empty: { text: "Clinician entered this", files: [{ dbId: 7 }] } }
  );
  assert.equal(result.conflicts.length, 0);
  assert.deepEqual(result.merged, {
    Empty: {
      text: "Clinician entered this",
      files: [{ dbId: 7 }],
    },
  });
}

console.log("multi-user clinician scenario tests passed (20 scenarios)");
