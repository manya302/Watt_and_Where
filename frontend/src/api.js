const API_URL = import.meta.env.VITE_API_URL?.replace(/\/+$/, "");
const API_KEY = import.meta.env.VITE_API_KEY;
const DEFAULT_OFFLINE = import.meta.env.VITE_DEFAULT_OFFLINE === "true";

export function isOfflineMode() {
  const forcedOffline =
    new URLSearchParams(window.location.search).get("demo") === "offline";

  return (
    forcedOffline ||
    DEFAULT_OFFLINE ||
    !API_URL ||
    !API_KEY
  );
}

export class ApiError extends Error {
  constructor(message, status = 0, kind = "network") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
  }
}

function friendlyError(status) {
  if (status === 403) {
    return "Access problem. Please check the app's setup.";
  }

  if (status === 429) {
    return "Too many requests. Please wait a moment and try again.";
  }

  if (status >= 500) {
    return "We couldn't reach the server. Please try again.";
  }

  return "We couldn't reach the server. Please try again.";
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "x-api-key": API_KEY,
      ...(options.method === "POST"
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(
      friendlyError(response.status),
      response.status,
      "http"
    );
  }

  return response.json();
}

async function loadOfflineSnapshot() {
  const snapshotUrl = `${import.meta.env.BASE_URL}demo-snapshot.json`;

  let response;

  try {
    response = await fetch(snapshotUrl, {
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "We couldn't read the saved example. Check that demo-snapshot.json exists and try again.",
      0,
      "snapshot"
    );
  }

  if (!response.ok) {
    throw new ApiError(
      "We couldn't read the saved example. Check that demo-snapshot.json exists and try again.",
      response.status,
      "snapshot"
    );
  }

  let snapshot;

  try {
    snapshot = await response.json();
  } catch {
    throw new ApiError(
      "We couldn't read the saved example. Check that demo-snapshot.json exists and try again.",
      0,
      "snapshot"
    );
  }

  if (
    !snapshot ||
    typeof snapshot !== "object" ||
    !("bills" in snapshot) ||
    !("analysis" in snapshot) ||
    !("summary" in snapshot)
  ) {
    throw new ApiError(
      "The saved example is missing required information. Check demo-snapshot.json.",
      0,
      "snapshot"
    );
  }

  return {
    bills: snapshot.bills,
    analysis: snapshot.analysis,
    summary: snapshot.summary,
    mode: "offline",
  };
}

/**
 * Initial dashboard load.
 *
 * Offline: one request for the bundled snapshot only.
 * Live: read the three existing GET endpoints.
 */
export async function loadDashboardData() {
  if (isOfflineMode()) {
    return loadOfflineSnapshot();
  }

  const [bills, analysis, summary] = await Promise.all([
    request("/bills"),
    request("/analysis").catch((error) => {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      throw error;
    }),
    request("/summary").catch((error) => {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      throw error;
    }),
  ]);

  return {
    bills,
    analysis,
    summary,
    mode: "live",
  };
}

export async function runAnalysis() {
  if (isOfflineMode()) {
    throw new ApiError(
      "Available in the live version (see the README)",
      0,
      "offline"
    );
  }

  return request("/analysis/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function createSummary() {
  if (isOfflineMode()) {
    throw new ApiError(
      "Available in the live version (see the README)",
      0,
      "offline"
    );
  }

  return request("/summary/generate", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/**
 * Generates a fresh report URL on each click.
 * Do not store the returned URL: it expires after 15 minutes.
 */
export async function createReport() {
  if (isOfflineMode()) {
    throw new ApiError(
      "Available in the live version (see the README)",
      0,
      "offline"
    );
  }

  return request("/report", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getSampleReportUrl() {
  return `${import.meta.env.BASE_URL}sample-report.html`;
}