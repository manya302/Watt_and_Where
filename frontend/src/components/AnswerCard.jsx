import { STRINGS } from "../strings.js";
import { formatMonthLabel, formatUnits } from "../formatters.js";

export default function AnswerCard({
  headline,
  activeMonth,
  showNumbers,
  onToggleNumbers,
  onOpenAlert,
}) {
  const status = headline?.status || "empty";

  const statusLabel =
    status === "alert"
      ? STRINGS.dashboard.flagged
      : status === "watch"
        ? STRINGS.dashboard.check
        : status === "normal"
          ? STRINGS.dashboard.steady
          : STRINGS.dashboard.notAvailable;

  return (
    <section
      className={`answer-card answer-card--${status}`}
      aria-labelledby="answer-title"
    >
      <div className="answer-card__top">
        <span className="answer-card__label">
          {STRINGS.dashboard.shortAnswer}
        </span>

        <span className={`status-pill status-pill--${status}`}>
          {statusLabel}
        </span>
      </div>

      <h2 id="answer-title">
        {headline?.title || STRINGS.dashboard.noAnalysisTitle}
      </h2>

      <p className="answer-card__message">
        {headline?.message || STRINGS.dashboard.noAnalysisMessage}
      </p>

      {activeMonth && (
        <div className="answer-card__metrics">
          <div>
            <span>{STRINGS.dashboard.latestMonth}</span>
            <strong>{formatMonthLabel(activeMonth.month)}</strong>
          </div>

          <div>
            <span>{STRINGS.dashboard.actualUnits}</span>
            <strong>
              {showNumbers
                ? formatUnits(activeMonth.actual_units)
                : "Hidden"}
            </strong>
          </div>
        </div>
      )}

      <div className="answer-card__actions">
        {status === "alert" && (
          <button
            className="button button--primary"
            type="button"
            onClick={onOpenAlert}
          >
            {STRINGS.dashboard.viewFlaggedMonth}
          </button>
        )}

        <button
          className="button button--secondary"
          type="button"
          onClick={onToggleNumbers}
        >
          {showNumbers
            ? STRINGS.dashboard.hideNumbers
            : STRINGS.dashboard.showNumbers}
        </button>
      </div>
    </section>
  );
}