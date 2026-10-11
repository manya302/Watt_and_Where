import {
  formatMonth,
  formatRupees,
  formatUnits,
  confidenceLabel,
} from "./strings.js";

export {
  formatMonth,
  formatRupees,
  formatUnits,
  confidenceLabel,
};

export function safeNumber(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number) ? number : fallback;
}

export function optionalNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

export function formatPercent(value, digits = 0) {
  const number = optionalNumber(value);

  if (number === null) return "Not available";

  return `${number.toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}%`;
}

export function formatSignedPercent(value, digits = 0) {
  const number = optionalNumber(value);

  if (number === null) return "Not available";

  const sign = number > 0 ? "+" : "";

  return `${sign}${formatPercent(number, digits)}`;
}

export function formatMonthLabel(month) {
  if (!month) return "Unknown month";

  try {
    return formatMonth(month);
  } catch {
    return String(month);
  }
}

export function formatDateTime(value) {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function getLatestByMonth(items) {
  if (!Array.isArray(items)) return null;

  return [...items]
    .filter((item) => item?.month)
    .sort((a, b) =>
      String(b.month).localeCompare(String(a.month))
    )[0] || null;
}

export function getMonthStatus(month) {
  const status = String(month?.status || "").toLowerCase();

  if (status === "alert") return "alert";
  if (status === "watch") return "watch";

  return "normal";
}