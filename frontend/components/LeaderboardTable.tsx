import { LeaderboardEntry } from "@/lib/api";

export default function LeaderboardTable({ entries }: { entries: LeaderboardEntry[] }) {
  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="text-left border-b border-gray-300">
          <th className="py-2 pr-4">Rank</th>
          <th className="py-2 pr-4">Type</th>
          <th className="py-2 pr-4">Platform</th>
          <th className="py-2 pr-4">Hook</th>
          <th className="py-2 pr-4">Topics</th>
          <th className="py-2 pr-4">Posted</th>
          <th className="py-2 pr-4">Performance (z)</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr
            key={e.content_id}
            className={`border-b border-gray-100 ${e.is_top_performer ? "bg-green-50" : ""}`}
          >
            <td className="py-2 pr-4">{e.rank}</td>
            <td className="py-2 pr-4">{e.content_type}</td>
            <td className="py-2 pr-4">{e.platform}</td>
            <td className="py-2 pr-4">{e.hook_type ?? "—"}</td>
            <td className="py-2 pr-4">{e.topic_tags.join(", ")}</td>
            <td className="py-2 pr-4">{new Date(e.posted_at).toLocaleDateString()}</td>
            <td className="py-2 pr-4">{e.performance_z.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}