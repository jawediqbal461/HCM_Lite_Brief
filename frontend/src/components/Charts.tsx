import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const CHART_COLORS = ["#16a34a", "#6366f1", "#f59e0b", "#ef4444", "#0ea5e9", "#a855f7"];

function Card({ title, hasData, children }: { title: string; hasData: boolean; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold mb-2">{title}</h3>
      {hasData ? (
        <div style={{ width: "100%", height: 220 }}>{children}</div>
      ) : (
        <div className="h-[220px] flex items-center justify-center text-sm text-slate-400">
          No data for this range yet.
        </div>
      )}
    </div>
  );
}

export function BarCard({
  title,
  data,
  xKey,
  bars,
}: {
  title: string;
  data: any[];
  xKey: string;
  bars: { key: string; name: string }[];
}) {
  return (
    <Card title={title} hasData={data.length > 0}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {bars.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {bars.map((bar, i) => (
            <Bar key={bar.key} dataKey={bar.key} name={bar.name} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function LineCard({
  title,
  data,
  xKey,
  lines,
}: {
  title: string;
  data: any[];
  xKey: string;
  lines: { key: string; name: string }[];
}) {
  return (
    <Card title={title} hasData={data.length > 0}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {lines.map((line, i) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.name}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function PieCard({
  title,
  data,
  nameKey,
  valueKey,
}: {
  title: string;
  data: any[];
  nameKey: string;
  valueKey: string;
}) {
  return (
    <Card title={title} hasData={data.length > 0}>
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey={valueKey} nameKey={nameKey} outerRadius={80} label={{ fontSize: 11 }}>
            {data.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
