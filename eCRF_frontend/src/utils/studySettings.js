export const NUMBER_FORMAT_PRESETS = Object.freeze({
  international: Object.freeze({
    label: "International",
    decimalSeparator: ".",
    groupingSeparator: ",",
    exampleDecimal: "0.8",
    exampleLarge: "100,000.25",
  }),
  german: Object.freeze({
    label: "German (Germany)",
    decimalSeparator: ",",
    groupingSeparator: ".",
    exampleDecimal: "0,8",
    exampleLarge: "100.000,25",
  }),
});

export const MEASUREMENT_CONCEPTS = Object.freeze([
  { value: "", label: "Plain number (no measurement)", units: [] },
  { value: "body_weight", label: "Body weight", units: ["kg", "lb"] },
  { value: "body_height", label: "Body height", units: ["cm", "m", "in"] },
  { value: "body_temperature", label: "Body temperature", units: ["°C", "°F", "K"] },
  { value: "blood_pressure", label: "Blood pressure", units: ["mmHg", "kPa"] },
  { value: "waist_circumference", label: "Waist circumference", units: ["cm", "in"] },
  { value: "volume", label: "Volume", units: ["mL", "L"] },
  { value: "distance", label: "Distance", units: ["m", "km", "mi"] },
]);

export const DEFAULT_MEASUREMENT_UNITS = Object.freeze({
  body_weight: "kg",
  body_height: "cm",
  body_temperature: "°C",
  blood_pressure: "mmHg",
  waist_circumference: "cm",
  volume: "mL",
  distance: "km",
});

export const DEFAULT_STUDY_SETTINGS = Object.freeze({
  version: 1,
  numberFormat: Object.freeze({
    preset: "international",
    decimalSeparator: ".",
    groupingSeparator: ",",
    unexpectedInputPolicy: "confirm",
  }),
  measurementDefaults: DEFAULT_MEASUREMENT_UNITS,
});

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function normalizeStudySettings(value) {
  const source = value && typeof value === "object" ? value : {};
  const requestedPreset = String(source?.numberFormat?.preset || "international");
  const preset = NUMBER_FORMAT_PRESETS[requestedPreset] ? requestedPreset : "international";
  const presetDefinition = NUMBER_FORMAT_PRESETS[preset];
  const policy = ["confirm", "reject", "auto"].includes(source?.numberFormat?.unexpectedInputPolicy)
    ? source.numberFormat.unexpectedInputPolicy
    : "confirm";

  return {
    version: 1,
    numberFormat: {
      preset,
      decimalSeparator: presetDefinition.decimalSeparator,
      groupingSeparator: presetDefinition.groupingSeparator,
      unexpectedInputPolicy: policy,
    },
    measurementDefaults: {
      ...clone(DEFAULT_MEASUREMENT_UNITS),
      ...(source.measurementDefaults && typeof source.measurementDefaults === "object"
        ? source.measurementDefaults
        : {}),
    },
  };
}

export function measurementConcept(value) {
  return MEASUREMENT_CONCEPTS.find((item) => item.value === String(value || "")) || MEASUREMENT_CONCEPTS[0];
}

export function studyNumberExamples(settings) {
  const normalized = normalizeStudySettings(settings);
  return NUMBER_FORMAT_PRESETS[normalized.numberFormat.preset] || NUMBER_FORMAT_PRESETS.international;
}

export function collectStudyMeasurements(forms) {
  const classified = new Map();
  const unclassified = [];

  (Array.isArray(forms) ? forms : []).forEach((form, formIndex) => {
    (form?.sections || []).forEach((section, sectionIndex) => {
      (section?.fields || []).forEach((field, fieldIndex) => {
        const type = String(field?.type || "").toLowerCase();
        if (!["number", "slider"].includes(type)) return;

        const measurement = field?.constraints?.measurement;
        const concept = String(measurement?.concept || "");
        const fieldInfo = {
          key: String(field?._id || field?.id || field?.name || `${formIndex}_${sectionIndex}_${fieldIndex}`),
          label: field?.label || field?.name || `Field ${fieldIndex + 1}`,
          section: section?.title || `Section ${sectionIndex + 1}`,
        };

        if (!concept || !measurementConcept(concept).value) {
          unclassified.push(fieldInfo);
          return;
        }

        if (!classified.has(concept)) classified.set(concept, []);
        classified.get(concept).push(fieldInfo);
      });
    });
  });

  return {
    classified: Array.from(classified.entries()).map(([concept, fields]) => ({ concept, fields })),
    unclassified,
  };
}
