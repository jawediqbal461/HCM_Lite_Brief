import { useState } from "react";
import api, { apiErrorMessage } from "../api/client";

export default function AISummaryButton({ kpiJson }: { kpiJson: Record<string, unknown> }) {
  const [bullets, setBullets] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function summarize() {
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/ai/summarize", { kpi_json: kpiJson });
      setBullets(res.data.bullets);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-semibold">AI summary</h3>
        <button onClick={summarize} disabled={loading} className="text-sm bg-brand text-white rounded px-3 py-1">
          {loading ? "Summarizing..." : "Summarize"}
        </button>
      </div>
      {error && <div className="text-red-600 text-sm">{error}</div>}
      {bullets && (
        <ul className="list-disc list-inside text-sm space-y-1">
          {bullets.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
      )}
      {bullets && <div className="text-[10px] text-slate-400 mt-2">AI-generated</div>}
    </div>
  );
}
