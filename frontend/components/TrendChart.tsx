"use client";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { MonthlyPerformanceEntry } from "@/lib/api";
import { useTheme } from "@/lib/ThemeContext";
import { chartColors } from "@/lib/chartTheme";

export default function TrendChart({ data }: { data: MonthlyPerformanceEntry[] }) {
  const { theme } = useTheme();
  const c = chartColors(theme);
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
          <XAxis dataKey="period" tick={{ fill: c.axisText, fontSize: 11 }} axisLine={{ stroke: c.axisLine }} tickLine={{ stroke: c.axisLine }} />
          <YAxis tick={{ fill: c.axisText, fontSize: 11 }} axisLine={{ stroke: c.axisLine }} tickLine={{ stroke: c.axisLine }} />
          <Tooltip
            contentStyle={{ background: c.tooltipBg, border: `1px solid ${c.tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: c.tooltipText, fontWeight: 600 }}
            itemStyle={{ color: c.accent }}
            cursor={{ stroke: c.axisLine }}
            formatter={(v: number) => [`${v.toFixed(2)} SD`, "Performance"]}
          />
          <Line type="monotone" dataKey="mean_performance_z" stroke={c.accent} strokeWidth={2} dot={{ r: 3, fill: c.accent }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}