export default function KpiCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className={`text-2xl font-bold ${accent || "text-brand-dark"}`}>{value}</div>
      <div className="text-sm text-slate-500">{label}</div>
    </div>
  );
}
