import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat.js";

dayjs.extend(customParseFormat);

export const SUPPORTED_DATE_FORMATS = [
  "dd.MM.yyyy",
  "DD.MM.YYYY",
  "dd-MM-yyyy",
  "DD-MM-YYYY",
  "MM-dd-yyyy",
  "MM-DD-YYYY",
  "yyyy-MM-dd",
  "YYYY-MM-DD",
  "dd/MM/yyyy",
  "DD/MM/YYYY",
  "MM/dd/yyyy",
  "MM/DD/YYYY",
  "yyyy/MM/dd",
  "YYYY/MM/DD",
  "dd MMM yyyy",
  "DD MMM YYYY",
  "yyyy",
  "YYYY",
  "MM-yyyy",
  "MM-YYYY",
  "yyyy-MM",
  "YYYY-MM",
  "MM/yyyy",
  "MM/YYYY",
  "yyyy/MM",
  "YYYY/MM",
  "yyyy-MM-dd HH:mm",
  "YYYY-MM-DD HH:mm",
  "yyyy HH:mm",
  "YYYY HH:mm",
  "HH:mm",
  "yyyy-MM-dd HH:mm:ss",
  "YYYY-MM-DD HH:mm:ss",
];

export function toDayjsFormat(format) {
  return String(format || "dd.MM.yyyy")
    .replace(/yyyy/g, "YYYY")
    .replace(/dd/g, "DD");
}

export function toDatePickerFormat(format) {
  return String(format || "dd.MM.yyyy")
    .replace(/YYYY/g, "yyyy")
    .replace(/DD/g, "dd");
}

export function parseDateByConfiguredFormat(value, format) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;

  const dayjsFormat = toDayjsFormat(format);
  const parsed = dayjs(raw, dayjsFormat, true);
  if (!parsed.isValid()) return null;

  return parsed.toDate();
}

export function formatDateByConfiguredFormat(dateObj, format) {
  if (!(dateObj instanceof Date) || Number.isNaN(dateObj.getTime())) return "";
  return dayjs(dateObj).format(toDayjsFormat(format));
}

export function normalizeImportedDateForFormat(value, format) {
  const targetFormat = format || "dd.MM.yyyy";
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return formatDateByConfiguredFormat(value, targetFormat);
  }

  const raw = String(value ?? "").trim();
  if (!raw) return "";

  const exact = parseDateByConfiguredFormat(raw, targetFormat);
  if (exact) return formatDateByConfiguredFormat(exact, targetFormat);

  // A date-only target may receive a timestamp from CSV exports. Keep the
  // calendar date and intentionally discard the time component.
  const targetLength = toDayjsFormat(targetFormat).length;
  const configuredPrefix = raw.slice(0, targetLength);
  const prefixDate = parseDateByConfiguredFormat(configuredPrefix, targetFormat);
  if (prefixDate && /^\s|T/.test(raw.slice(targetLength, targetLength + 1))) {
    return formatDateByConfiguredFormat(prefixDate, targetFormat);
  }

  for (const sourceFormat of [
    "YYYY-MM-DDTHH:mm:ss.SSSZ",
    "YYYY-MM-DDTHH:mm:ssZ",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY-MM-DD HH:mm",
    "YYYY-MM-DD",
  ]) {
    const parsed = dayjs(raw, sourceFormat, true);
    if (parsed.isValid()) return formatDateByConfiguredFormat(parsed.toDate(), targetFormat);
  }

  const slashFormats = toDayjsFormat(targetFormat).startsWith("DD")
    ? ["D/M/YYYY H:mm:ss", "D/M/YYYY H:mm", "D/M/YYYY", "DD/MM/YYYY HH:mm:ss", "DD/MM/YYYY HH:mm", "DD/MM/YYYY", "M/D/YYYY H:mm:ss", "M/D/YYYY H:mm", "M/D/YYYY", "MM/DD/YYYY HH:mm:ss", "MM/DD/YYYY HH:mm", "MM/DD/YYYY"]
    : ["M/D/YYYY H:mm:ss", "M/D/YYYY H:mm", "M/D/YYYY", "MM/DD/YYYY HH:mm:ss", "MM/DD/YYYY HH:mm", "MM/DD/YYYY", "D/M/YYYY H:mm:ss", "D/M/YYYY H:mm", "D/M/YYYY", "DD/MM/YYYY HH:mm:ss", "DD/MM/YYYY HH:mm", "DD/MM/YYYY"];
  // Excel's common short-date export uses a two-digit year in month/day order.
  slashFormats.unshift("M/D/YY H:mm:ss", "M/D/YY H:mm", "M/D/YY h:mm A", "M/D/YY");
  for (const sourceFormat of slashFormats) {
    const parsed = dayjs(raw, sourceFormat, true);
    if (parsed.isValid()) return formatDateByConfiguredFormat(parsed.toDate(), targetFormat);
  }

  return raw;
}

export function isCompleteDateForFormat(value, format) {
  return !!parseDateByConfiguredFormat(value, format);
}
