import { STRINGS, formatMonth, formatRupees } from "./strings.js";

function getMonths(analysis) {
  return Array.isArray(analysis?.months) ? analysis.months : [];
}

function getAlerts(analysis) {
  return Array.isArray(analysis?.alerts) ? analysis.alerts : [];
}

function getLatestMonth(months) {
  return [...months]
    .filter((month) => month?.month)
    .sort((a, b) => String(b.month).localeCompare(String(a.month)))[0] || null;
}

function getLatestAlert(analysis) {
  return [...getAlerts(analysis)]
    .filter((alert) => alert?.month)
    .sort((a, b) => String(b.month).localeCompare(String(a.month)))[0] || null;
}

function formatMonthSafely(month) {
  if (!month) return "the selected month";

  try {
    return formatMonth(month);
  } catch {
    return String(month);
  }
}

function formatSaving(value) {
  const amount = Number(value);

  if (!Number.isFinite(amount) || amount <= 0) return "";

  try {
    return formatRupees(amount);
  } catch {
    return `₹${amount.toLocaleString("en-IN")}`;
  }
}

function getText(key, fallback) {
  const value = STRINGS?.dashboard?.[key];
  return typeof value === "string" && value.trim()
    ? value
    : fallback;
}

export function buildHeadline(analysis) {
  const months = getMonths(analysis);
  const latestMonth = getLatestMonth(months);

  if (!latestMonth) {
    return {
      title: getText("noAnalysisTitle", "Let's look at your bills"),
      message: getText(
        "noAnalysisMessage",
        "Your electricity insights will appear here once your bills have been analysed."
      ),
      status: "empty",
      month: null,
      saving: null,
    };
  }

  const alerts = getAlerts(analysis);
  const monthAlert =
    alerts.find((alert) => alert.month === latestMonth.month) ||
    (latestMonth.status === "alert" ? getLatestAlert(analysis) : null);

  const monthName = formatMonthSafely(latestMonth.month);

  if (latestMonth.status === "alert" || monthAlert) {
    const saving = formatSaving(
      monthAlert?.expected_monthly_saving?.inr
    );

    const message = saving
      ? getText(
          "alertMessageWithSaving",
          "We found an unusual change in {month}. Reviewing it could help save around {saving} per month."
        )
      : getText(
          "alertMessage",
          "We found an unusual change in {month}."
        );

    return {
      title: getText(
        "alertTitle",
        "Your electricity use needs a closer look"
      ),
      message: message
        .replace("{month}", monthName)
        .replace("{saving}", saving),
      status: "alert",
      month: latestMonth.month,
      saving: saving || null,
    };
  }

  if (latestMonth.status === "watch") {
    return {
      title: getText("watchTitle", "One month is worth checking"),
      message: getText(
        "watchMessage",
        "Some electricity use in {month} looks different from usual."
      ).replace("{month}", monthName),
      status: "watch",
      month: latestMonth.month,
      saving: null,
    };
  }

  return {
    title: getText(
      "normalTitle",
      "Your electricity use looks steady"
    ),
    message: getText(
      "normalMessage",
      "No major unusual change was flagged for {month}."
    ).replace("{month}", monthName),
    status: "normal",
    month: latestMonth.month,
    saving: null,
  };
}

export default buildHeadline;