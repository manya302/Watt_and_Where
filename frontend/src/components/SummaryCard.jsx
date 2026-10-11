import { useState } from "react";
import { STRINGS } from "../strings.js";

export default function SummaryCard({
  summary,
  offline = false,
  onCreateSummary,
}) {
  const [copied, setCopied] = useState(false);

  async function copySummary() {
    if (!summary?.text || !navigator.clipboard?.writeText) return;

    try {
      await navigator.clipboard.writeText(summary.text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  const sourceLabel =
    summary?.source === "bedrock"
      ? STRINGS.dashboard?.summaryBedrock || "AI-generated summary"
      : STRINGS.dashboard?.summaryFallback || "Standard summary";

  return (
    <section className="panel summary-panel" aria-labelledby="summary-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {STRINGS.dashboard?.summaryEyebrow || "Your report"}
          </p>
          <h2 id="summary-title">
            {STRINGS.dashboard?.summaryTitle || "Electricity summary"}
          </h2>
        </div>

        {summary?.source && (
          <span
            className={`summary-badge summary-badge--${
              summary.source === "bedrock" ? "bedrock" : "fallback"
            }`}
          >
            {sourceLabel}
          </span>
        )}
      </div>

      {summary?.text ? (
        <>
          <p className="summary-copy">{summary.text}</p>

          <button
            type="button"
            className="button button--secondary"
            onClick={copySummary}
            disabled={!navigator.clipboard?.writeText}
          >
            {copied
              ? STRINGS.dashboard?.copied || "Copied"
              : STRINGS.dashboard?.copySummary || "Copy summary"}
          </button>
        </>
      ) : (
        <p>
          {STRINGS.dashboard?.noSummary ||
            "A summary is not available yet."}
        </p>
      )}

      {offline ? (
        <p className="muted-note">
          {STRINGS.dashboard?.offlineActionNote ||
            "Available in the live version (see the README)."}
        </p>
      ) : onCreateSummary ? (
        <button
          type="button"
          className="button button--primary"
          onClick={onCreateSummary}
        >
          {STRINGS.dashboard?.createSummary || "Create summary"}
        </button>
      ) : null}
    </section>
  );
}