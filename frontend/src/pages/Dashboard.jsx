import { useMemo, useState } from "react";

import { STRINGS } from "../strings.js";
import { buildHeadline } from "../buildHeadline.js";

import {
  formatMonthLabel,
  formatUnits,
  formatRupees,
  formatPercent,
  getLatestByMonth,
  getMonthStatus,
} from "../formatters.js";

import AnswerCard from "../components/AnswerCard.jsx";
import BillChart from "../components/BillChart.jsx";
import BreakdownChart from "../components/BreakdownChart.jsx";
import EvidenceSection from "../components/EvidenceSection.jsx";
import ActionsChecklist from "../components/ActionsChecklist.jsx";
import SummaryCard from "../components/SummaryCard.jsx";

function getMonths(analysis) {
  return Array.isArray(analysis?.months) ? analysis.months : [];
}

function getAlerts(analysis) {
  return Array.isArray(analysis?.alerts) ? analysis.alerts : [];
}

function getBills(billsData) {
  if (Array.isArray(billsData)) return billsData;
  if (Array.isArray(billsData?.bills)) return billsData.bills;
  return [];
}

function findAlertForMonth(analysis, month) {
  return getAlerts(analysis).find((alert) => alert.month === month) || null;
}

export default function Dashboard({
  data,
  onRetry,
  activeTab = "overview",
}) {
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [showNumbers, setShowNumbers] = useState(true);
  const [showHowItWorks, setShowHowItWorks] = useState(false);

  const analysis = data?.analysis;
  const bills = getBills(data?.bills);
  const isOffline = data?.mode === "offline";

  const months = useMemo(
    () =>
      [...getMonths(analysis)].sort((a, b) =>
        String(a.month).localeCompare(String(b.month))
      ),
    [analysis]
  );

  const headline = useMemo(
    () => buildHeadline(analysis),
    [analysis]
  );

  const latestMonth = getLatestByMonth(months);

  const activeMonth =
    months.find((month) => month.month === selectedMonth) || latestMonth;

  const activeAlert = activeMonth
    ? findAlertForMonth(analysis, activeMonth.month)
    : null;

  const monthIndex = activeMonth
    ? months.findIndex((month) => month.month === activeMonth.month)
    : -1;

  const previousMonth = monthIndex > 0 ? months[monthIndex - 1] : null;

  const nextMonth =
    monthIndex >= 0 && monthIndex < months.length - 1
      ? months[monthIndex + 1]
      : null;

  const billForActiveMonth = activeMonth
    ? bills.find((bill) => bill.month === activeMonth.month)
    : null;

  const status = getMonthStatus(activeMonth);

  function selectMonth(month) {
    const monthValue = typeof month === "string" ? month : month?.month;

    if (monthValue) {
      setSelectedMonth(monthValue);
    }
  }

  function openLatestAlert() {
    const latestAlert = getLatestByMonth(getAlerts(analysis));

    if (latestAlert?.month) {
      setSelectedMonth(latestAlert.month);
    }
  }

  function renderMonthNavigation() {
    if (!activeMonth) return null;

    return (
      <div className="month-navigation">
        <button
          type="button"
          className="button button--secondary"
          disabled={!previousMonth}
          onClick={() => selectMonth(previousMonth)}
        >
          {STRINGS.dashboard.previousMonth}
        </button>

        <span className="month-navigation__current">
          {formatMonthLabel(activeMonth.month)}
        </span>

        <button
          type="button"
          className="button button--secondary"
          disabled={!nextMonth}
          onClick={() => selectMonth(nextMonth)}
        >
          {STRINGS.dashboard.nextMonth}
        </button>
      </div>
    );
  }

  function renderMonthMetrics() {
    if (!activeMonth) return null;

    return (
      <>
        <div className="metric-grid">
          <div className="metric-card">
            <span>{STRINGS.dashboard.actualUnits}</span>
            <strong>
              {showNumbers
                ? formatUnits(activeMonth.actual_units)
                : "Hidden"}
            </strong>
          </div>

          <div className="metric-card">
            <span>{STRINGS.dashboard.estimatedUnits}</span>
            <strong>
              {showNumbers
                ? formatUnits(activeMonth.estimated_total)
                : "Hidden"}
            </strong>
          </div>

          <div className="metric-card">
            <span>{STRINGS.dashboard.statusLabel || "Status"}</span>
            <strong>
              {status === "alert"
                ? STRINGS.dashboard.flagged
                : status === "watch"
                  ? STRINGS.dashboard.check
                  : STRINGS.dashboard.steady}
            </strong>
          </div>
        </div>

        <p className="plain-explanation">
          {STRINGS.dashboard.kwhExplanation}
        </p>
      </>
    );
  }

  function renderBillAmount() {
    if (billForActiveMonth?.total_amount === undefined) return null;

    return (
      <div className="reference-note">
        <span>{STRINGS.dashboard.billAmount}</span>
        <strong>
          {showNumbers
            ? formatRupees(billForActiveMonth.total_amount)
            : "Hidden"}
        </strong>
      </div>
    );
  }

  function renderOverview() {
    return (
      <>
        <AnswerCard
          headline={headline}
          activeMonth={activeMonth}
          showNumbers={showNumbers}
          onToggleNumbers={() => setShowNumbers((value) => !value)}
          onOpenAlert={openLatestAlert}
        />

        {activeMonth && (
          <section className="panel overview-highlight">
            <p className="eyebrow">
              {STRINGS.dashboard.selectedMonth}
            </p>

            <h2>{formatMonthLabel(activeMonth.month)}</h2>

            {renderMonthNavigation()}
            {renderMonthMetrics()}
            {renderBillAmount()}

            {activeAlert && (
              <p className="overview-alert-note">
                {STRINGS.dashboard.flagged}
              </p>
            )}
          </section>
        )}

        <section className="panel how-it-works">
          <button
            type="button"
            className="disclosure-button"
            aria-expanded={showHowItWorks}
            onClick={() => setShowHowItWorks((value) => !value)}
          >
            <span>{STRINGS.dashboard.howItWorks}</span>
            <span aria-hidden="true">
              {showHowItWorks ? "−" : "+"}
            </span>
          </button>

          {showHowItWorks && (
            <div className="disclosure-content">
              <p>{STRINGS.dashboard.howItWorksText}</p>
            </div>
          )}
        </section>
      </>
    );
  }

  function renderTrends() {
    return (
      <section className="panel bill-panel" aria-labelledby="bill-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              {STRINGS.dashboard.billEyebrow}
            </p>

            <h2 id="bill-title">
              {STRINGS.dashboard.billTitle}
            </h2>

            <p>{STRINGS.dashboard.billDescription}</p>
          </div>
        </div>

        <BillChart
            data={bills}
            months={months}
            selectedMonth={activeMonth?.month}
            onSelectMonth={selectMonth}
            showNumbers={showNumbers}
        />

        {activeMonth && (
          <div className="month-detail">
            <div className="month-detail__heading">
              <div>
                <p className="eyebrow">
                  {STRINGS.dashboard.selectedMonth}
                </p>

                <h3>{formatMonthLabel(activeMonth.month)}</h3>
              </div>

              {renderMonthNavigation()}
            </div>

            {renderMonthMetrics()}

            <div className="reference-note">
              <span>{STRINGS.dashboard.sameMonthLastYear}</span>
              <strong>
                {activeMonth.yoy_pct === null ||
                activeMonth.yoy_pct === undefined
                  ? STRINGS.dashboard.notAvailable
                  : formatPercent(activeMonth.yoy_pct)}
              </strong>
            </div>

            {renderBillAmount()}
          </div>
        )}

        <div className="show-numbers-control">
          <button
            type="button"
            className="button button--secondary"
            onClick={() => setShowNumbers((value) => !value)}
            aria-pressed={showNumbers}
          >
            {showNumbers
              ? "Hide detailed numbers"
              : "Show detailed numbers"}
          </button>
        </div>
      </section>
    );
  }

  function renderBreakdown() {
    return (
      <section className="panel breakdown-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">ENERGY USE</p>
            <h2>Where the electricity goes</h2>
            <p>
              Explore the estimated energy use for each month.
            </p>
          </div>
        </div>

        {activeMonth ? (
          <>
            {renderMonthNavigation()}

            <h3 className="breakdown-month-title">
              {formatMonthLabel(activeMonth.month)}
            </h3>

            <BreakdownChart
              month={activeMonth}
              showNumbers={showNumbers}
            />

            <div className="show-numbers-control">
              <button
                type="button"
                className="button button--secondary"
                onClick={() => setShowNumbers((value) => !value)}
                aria-pressed={showNumbers}
              >
                {showNumbers ? "Hide numbers" : "Show numbers"}
              </button>
            </div>
          </>
        ) : (
          <p>{STRINGS.dashboard.noAnalysisMessage}</p>
        )}
      </section>
    );
  }

  function renderRecommendations() {
    return (
      <>
        <EvidenceSection
          alert={activeAlert}
          showNumbers={showNumbers}
        />

        <ActionsChecklist
          key={activeMonth?.month || "no-month"}
          actions={activeAlert?.recommended_actions || []}
        />

        {!activeAlert && (
          <section className="panel">
            <h2>{STRINGS.dashboard.steady}</h2>
            <p>
              No alert is available for the selected month.
              You can use the month controls in Overview or Bill trends
              to explore another month.
            </p>
          </section>
        )}
      </>
    );
  }

  function renderSummary() {
    return (
      <>
        <SummaryCard
          summary={data?.summary}
          offline={isOffline}
        />

        <section className="panel report-panel">
          <h2>
            {STRINGS.dashboard.reportTitle || "Full report"}
          </h2>

          <p>
            {STRINGS.dashboard.reportDescription ||
              "Open the example report for a more detailed view."}
          </p>

          {isOffline ? (
            <a
              className="button button--primary report-link"
              href={`${import.meta.env.BASE_URL}sample-report.html`}
              target="_blank"
              rel="noreferrer"
            >
              {STRINGS.dashboard.openReport}
            </a>
          ) : (
            <p className="muted-note">
              {STRINGS.dashboard.liveReportNote ||
                "Report generation is available in the configured live version."}
            </p>
          )}
        </section>
      </>
    );
  }

  return (
    <main className="dashboard-page">
      {isOffline && (
        <aside className="sample-banner" aria-label="Example data notice">
          <p>{STRINGS.dashboard.offlineBanner}</p>
        </aside>
      )}

      {!analysis ? (
        <section className="panel empty-state">
          <h1>
            {STRINGS.dashboard.noAnalysisTitle ||
              "Let's look at your bills"}
          </h1>

          <p>
            {STRINGS.dashboard.noAnalysisMessage ||
              "Your electricity insights will appear here once your bills have been analysed."}
          </p>

          {isOffline ? (
            <p className="muted-note">
              {STRINGS.dashboard.offlineActionNote}
            </p>
          ) : (
            <button
              className="button button--primary"
              type="button"
              onClick={onRetry}
            >
              {STRINGS.dashboard.runAnalysis}
            </button>
          )}
        </section>
      ) : (
        <>
          {activeTab === "overview" && renderOverview()}
          {activeTab === "trends" && renderTrends()}
          {activeTab === "breakdown" && renderBreakdown()}
          {activeTab === "actions" && renderRecommendations()}
          {activeTab === "summary" && renderSummary()}
        </>
      )}

      <footer className="dashboard-footer">
        <p>{STRINGS.app.footer}</p>
      </footer>
    </main>
  );
}