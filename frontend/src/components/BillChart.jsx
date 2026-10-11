import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

function formatMonth(value) {
  if (!value) return "Unknown month";
  const match = /^(\d{4})-(\d{2})$/.exec(String(value));
  if (!match) return String(value);

  const date = new Date(Number(match[1]), Number(match[2]) - 1, 1);
  return date.toLocaleDateString("en-IN", {
    month: "short",
    year: "numeric",
  });
}

function getAmount(item) {
  const candidates = [
    ["amount", item?.amount],
    ["total_amount", item?.total_amount],
    ["bill_amount", item?.bill_amount],
    ["amount_inr", item?.amount_inr],
    ["bill_inr", item?.bill_inr],
    ["billed_amount", item?.billed_amount],
  ];

  for (const [field, value] of candidates) {
    if (value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value))) {
      return { value: Number(value), isCurrency: true, sourceField: field };
    }
  }

  // The analysis endpoint records billed units (kWh), not rupees.
  if (item?.actual_units !== null && item?.actual_units !== undefined) {
    const value = Number(item.actual_units);
    if (Number.isFinite(value)) {
      return { value, isCurrency: false, sourceField: "actual_units" };
    }
  }

  return { value: null, isCurrency: false, sourceField: null };
}

function formatValue(value, isCurrency) {
  const formatted = Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  });
  return isCurrency ? `₹${formatted}` : formatted;
}

export default function BillChart({
  data = [],
  months = [],
  selectedMonth,
  onSelectMonth,
  showNumbers = true,
}) {
  const source = Array.isArray(data) && data.length ? data : months;
  const chartData = source
    .map((item) => {
      const amount = getAmount(item);
      return {
        month: item?.month ?? item?.billing_month ?? item?.date ?? "Unknown month",
        displayMonth: formatMonth(item?.month ?? item?.billing_month ?? item?.date),
        amount: amount.value,
        isCurrency: amount.isCurrency,
        status: item?.status,
      };
    })
    .filter((item) => Number.isFinite(item.amount));

  const isCurrency = chartData.some((item) => item.isCurrency);
  // Truncated axis: use a tight range around the actual values so differences
  // are visible, while explicitly indicating that zero is omitted.
  const values = chartData.map((item) => item.amount);
  const dataMin = values.length ? Math.min(...values) : 0;
  const dataMax = values.length ? Math.max(...values) : 1000;
  const spread = dataMax - dataMin;
  const padding = Math.max(spread * 0.18, Math.abs(dataMax) * 0.015, 1);
  const step = spread > 12000 ? 2500 : spread > 5000 ? 1000 : spread > 1500 ? 500 : spread > 500 ? 100 : spread > 100 ? 50 : 10;
  const zoomLower = Math.max(0, Math.floor((dataMin - padding) / step) * step);
  const zoomUpper = Math.ceil((dataMax + padding) / step) * step;
  const zoomTicks = [];
  for (let value = zoomLower; value <= zoomUpper; value += step) zoomTicks.push(value);

  return (
    <section className="bill-chart-section">
      <h2>Monthly electricity bill</h2>
      <p className="chart-description">
        Truncated Y-axis to make month-to-month differences easier to compare.
        The bars start at the displayed baseline, not zero; use the values/table for exact comparisons.
      </p>

      {chartData.length === 0 ? (
        <p role="status" className="chart-empty-state">
          No monthly bill data is available to display yet.
        </p>
      ) : (
        <>
          <div className="bill-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 16, right: 16, left: 12, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="4 4"
                  vertical={false}
                  stroke="#d8e2df"
                />
                <XAxis
                  dataKey="displayMonth"
                  tick={{ fill: "#65716f", fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: "#b9c7c3" }}
                  minTickGap={24}
                />
                <YAxis
                  domain={[zoomLower, zoomUpper]}
                  ticks={zoomTicks}
                  tickFormatter={(value) =>
                    isCurrency
                      ? `₹${value.toLocaleString("en-IN")}`
                      : value.toLocaleString("en-IN")
                  }
                  tick={{ fill: "#65716f", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  width={82}
                  allowDataOverflow
                />
                <Tooltip
                  labelFormatter={(label) => label}
                  formatter={(value) => [
                    showNumbers ? formatValue(value, isCurrency) : "Hidden",
                    isCurrency ? "Bill amount" : "Billed units",
                  ]}
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid #d8e2df",
                  }}
                />
                <ReferenceLine
                  y={zoomLower}
                  stroke="#8c9b97"
                  strokeDasharray="3 3"
                />
                <Bar
                  dataKey="amount"
                  name={isCurrency ? "Monthly bill" : "Billed units"}
                  fill="#9bbfba"
                  radius={[8, 8, 0, 0]}
                  maxBarSize={44}
                  onClick={(entry) => onSelectMonth?.(entry.month)}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-axis-break" aria-label="Vertical axis break; the Y-axis is truncated and does not start at zero">
            <span className="axis-break-zigzag" aria-hidden="true">〰</span>
            <span>Y-axis break · scale starts at {formatValue(zoomLower, isCurrency)}, not zero</span>
          </div>

          <h3>Monthly bill table</h3>
          <div className="bill-table-wrapper">
            <table className="bill-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>{isCurrency ? "Electricity bill" : "Billed units"}</th>
                </tr>
              </thead>
              <tbody>
                {chartData.map((item, index) => (
                  <tr
                    key={`${item.month}-${index}`}
                    className={item.month === selectedMonth ? "is-selected" : ""}
                  >
                    <td>
                      {onSelectMonth ? (
                        <button
                          type="button"
                          className="chart-month-link"
                          onClick={() => onSelectMonth(item.month)}
                        >
                          {item.displayMonth}
                        </button>
                      ) : (
                        item.displayMonth
                      )}
                    </td>
                    <td>
                      {showNumbers ? formatValue(item.amount, item.isCurrency) : "Hidden"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
