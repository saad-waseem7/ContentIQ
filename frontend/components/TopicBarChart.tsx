"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { DimensionEntry } from "@/lib/api";
import { humanizeTopic } from "@/lib/labels";
import { useTheme } from "@/lib/ThemeContext";
import { chartColors } from "@/lib/chartTheme";

export default function TopicBarChart({ entries }: { entries: DimensionEntry[] }) {
  const { theme } = useTheme();
  const c = chartColors(theme);
  const data = entries.map((e) => ({ name: humanizeTopic(e.value), value: e.mean_performance_z }));
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
          <XAxis dataKey="name" tick={{ fill: c.axisText, fontSize: 10 }} axisLine={{ stroke: c.axisLine }} tickLine={{ stroke: c.axisLine }}
                 interval={0} angle={-15} textAnchor="end" height={50} />
          <YAxis tick={{ fill: c.axisText, fontSize: 11 }} axisLine={{ stroke: c.axisLine }} tickLine={{ stroke: c.axisLine }} />
          <Tooltip
            contentStyle={{ background: c.tooltipBg, border: `1px solid ${c.tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: c.tooltipText, fontWeight: 600 }}
            itemStyle={{ color: c.accent }}
            cursor={{ fill: c.cursorFill }}
            formatter={(v: number) => [`${v.toFixed(2)} SD`, "Performance"]}
          />
          <Bar dataKey="value" fill={c.accent} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}