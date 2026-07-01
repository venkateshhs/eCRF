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

export function isCompleteDateForFormat(value, format) {
  return !!parseDateByConfiguredFormat(value, format);
}
