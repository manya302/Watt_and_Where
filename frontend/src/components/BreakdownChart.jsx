import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import { STRINGS } from "../strings.js";
import { formatUnits } from "../formatters.js";

const CATEGORY_KEYS = [
  ["pump", "pump"],
  ["lift", "lift"],
  ["stp", "stp"],
  ["water_treatment", "waterTreatment"],
  ["lighting", "lighting"],
];

export default function BreakdownChart({
  month,
  showNumbers = true,
}) {
  const estimates = month?.estimated_by_category || {};

  const categories = CATEGORY_KEYS.map(([key, labelKey]) => ({
    key,
    label:
      STRINGS.categories?.[labelKey] ||
      {
        pump: "Pumps",
        lift: "Lifts",
        stp: "Sewage treatment",
        waterTreatment: "Water treatment",
        lighting: "Lighting",
      }[labelKey],
    units: Math.max(0, Number(estimates[key]) || 0),
  }));

  const accounted = categories.reduce(
    (sum, category) => sum + category.units,
    0
  );

  const unexplained =
    month?.unexplained_kwh !== null &&
    month?.unexplained_kwh !== undefined
      ? Math.max(0, Number(month.unexplained_kwh) || 0)
      : Math.max(0, (Number(month?.actual_units) || 0) - accounted);

  const chartData = [
    ...categories,
    {
      key: "unexplained",
      label:
        STRINGS.dashboard?.notAccountedFor || "Not accounted for",
      units: unexplained,
    },
  ];

  return (
    <section className="breakdown-chart">
      <h3>
        {STRINGS.dashboard?.breakdownTitle ||
          "Where the electricity may be going"}
      </h3>

      <p className="muted-note">
        {STRINGS.dashboard?.breakdownDescription ||
          "These are estimates based on the available information, not direct measurements for each category."}
      </p>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 8, right: 12, left: 8, bottom: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) =>
                showNumbers ? Number(value).toLocaleString("en-IN") : ""
              }
            />
            <YAxis
              type="category"
              dataKey="label"
              width={125}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              formatter={(value) => [
                showNumbers ? formatUnits(value) : "Hidden",
                STRINGS.dashboard?.estimatedUnits || "Estimated use",
              ]}
            />
            <Bar dataKey="units" radius={[0, 5, 5, 0]}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={
                    entry.key === "unexplained" ? "#B45309" : "#0F5E63"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="breakdown-list">
        {chartData.map((category) => (
          <div className="category-row" key={category.key}>
            <span>{category.label}</span>
            <strong>
              {showNumbers ? formatUnits(category.units) : "Hidden"}
            </strong>
          </div>
        ))}
      </div>
    </section>
  );
}