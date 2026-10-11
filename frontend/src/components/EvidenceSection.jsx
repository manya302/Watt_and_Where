import { STRINGS } from "../strings.js";
import { formatMonthLabel, formatUnits } from "../formatters.js";

function readableItem(item) {
  if (typeof item === "string") return item;

  return (
    item?.description ||
    item?.title ||
    item?.action ||
    item?.name ||
    ""
  );
}

export default function EvidenceSection({
  alert,
  showNumbers = true,
}) {
  if (!alert) return null;

  const hypotheses = Array.isArray(alert.hypotheses)
    ? alert.hypotheses
    : [];

  const referenceMonth =
    alert.reference_month ||
    alert.attribution_evidence?.reference_month?.month;

  const alertMonthPumpHours =
    alert.attribution_evidence?.pumps?.P1?.alert_month?.avg_daily_h;

  const referencePumpHours =
    alert.attribution_evidence?.pumps?.P1?.reference_month?.avg_daily_h;

  return (
    <section className="panel evidence-panel" aria-labelledby="evidence-title">
      <p className="eyebrow">
        {STRINGS.dashboard?.evidenceEyebrow || "What we found"}
      </p>

      <h2 id="evidence-title">
        {STRINGS.dashboard?.evidenceTitle || "Why this month was flagged"}
      </h2>

      <p>
        {(STRINGS.dashboard?.evidenceMonth ||
          "The electricity use for {month} was flagged for review.").replace(
          "{month}",
          formatMonthLabel(alert.month)
        )}
      </p>

      {alert.actual_units !== undefined && (
        <p>
          <strong>
            {STRINGS.dashboard?.actualUnits || "Actual electricity use"}:
          </strong>{" "}
          {showNumbers ? formatUnits(alert.actual_units) : "Hidden"}
        </p>
      )}

      {referenceMonth && (
        <p>
          <strong>
            {STRINGS.dashboard?.referenceMonth || "Comparison month"}:
          </strong>{" "}
          {formatMonthLabel(referenceMonth)}
        </p>
      )}

      {(alertMonthPumpHours !== undefined ||
        referencePumpHours !== undefined) && (
        <div className="evidence-comparison">
          <h3>
            {STRINGS.dashboard?.pumpEvidenceTitle ||
              "Pump operating time"}
          </h3>

          {alertMonthPumpHours !== undefined && (
            <p>
              {formatMonthLabel(alert.month)}:{" "}
              {showNumbers
                ? `${Number(alertMonthPumpHours).toLocaleString("en-IN", {
                    maximumFractionDigits: 1,
                  })} hours per day`
                : "Hidden"}
            </p>
          )}

          {referencePumpHours !== undefined && (
            <p>
              {referenceMonth
                ? formatMonthLabel(referenceMonth)
                : STRINGS.dashboard?.referenceMonth || "Comparison month"}
              :{" "}
              {showNumbers
                ? `${Number(referencePumpHours).toLocaleString("en-IN", {
                    maximumFractionDigits: 1,
                  })} hours per day`
                : "Hidden"}
            </p>
          )}
        </div>
      )}

      {hypotheses.length > 0 && (
        <>
          <h3>
            {STRINGS.dashboard?.possibleReasonsTitle ||
              "Possible reasons to investigate"}
          </h3>

          <ul className="plain-list">
            {hypotheses.map((item, index) => (
              <li key={`${readableItem(item) || "reason"}-${index}`}>
                {readableItem(item) ||
                  (STRINGS.dashboard?.evidenceItem || "Possible explanation")}
              </li>
            ))}
          </ul>
        </>
      )}

      {alert.coverage_label && (
        <p className="muted-note">
          {STRINGS.dashboard?.evidenceLimit ||
            "Please keep in mind:"}{" "}
          {alert.coverage_label}
        </p>
      )}

      <p className="evidence-caveat">
        {STRINGS.dashboard?.evidenceCaveat ||
          "A flagged month is a reason to investigate. It does not, by itself, prove that equipment is faulty or that electricity was wasted."}
      </p>
    </section>
  );
}