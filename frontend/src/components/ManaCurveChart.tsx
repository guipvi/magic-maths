/**
 * ManaCurveChart — Feature 1 visualization.
 *
 * Renders 3 sections from `analyze_mana_ramp()` response:
 * 1. Summary cards: land count, avg CMC, total ramp
 * 2. Stacked bar chart: mana composition per turn (lands, dorks, rocks, land ramp, rituals)
 * 3. Line chart: Monte Carlo percentiles (P10, P50, P90) per turn
 * 4. Data table: detailed breakdown with probabilities
 *
 * Props `data` comes from GET /api/analysis/mana-ramp or the `mana_ramp` key
 * from /api/analysis/full.
 */
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, LineChart, Line } from 'recharts'

interface Props {
  data: any
}

export default function ManaCurveChart({ data }: Props) {
  const byTurn = data.by_turn ? Object.values(data.by_turn) : []

  const chartData = byTurn.map((t: any) => ({
    turno: `T${t.turn}`,
    mana_terrenos: t.mana_from_lands,
    mana_dorks: t.mana_from_dorks,
    mana_rocks: t.mana_from_rocks,
    mana_land_ramp: t.mana_from_land_ramp,
    mana_rituais: t.mana_from_rituals,
    total: t.total_expected_mana,
    p10: t.mana_percentiles?.p10 || 0,
    p50: t.mana_percentiles?.p50 || 0,
    p90: t.mana_percentiles?.p90 || 0,
    prob_land_drop: t.prob_hitting_land_drop,
  }))

  const rampSummary = [
    { label: 'Total de Lands', value: data.land_count },
    { label: 'CMC Médio', value: data.avg_cmc },
    { label: 'Total Ramp', value: data.total_ramp },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {rampSummary.map((item) => (
          <div key={item.label} className="card text-center">
            <p className="text-2xl font-bold text-indigo-400">{item.value}</p>
            <p className="text-xs text-magic-muted">{item.label}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Mana Esperada por Turno</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#f1f5f9' }}
            />
            <Legend />
            <Bar dataKey="mana_terrenos" name="Terrenos" stackId="a" fill="#6366f1" />
            <Bar dataKey="mana_dorks" name="Dorks" stackId="a" fill="#22c55e" />
            <Bar dataKey="mana_rocks" name="Rochas" stackId="a" fill="#a855f7" />
            <Bar dataKey="mana_land_ramp" name="Ramp Terreno" stackId="a" fill="#f59e0b" />
            <Bar dataKey="mana_rituais" name="Rituais" stackId="a" fill="#ef4444" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Percentis de Mana (Monte Carlo)</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#f1f5f9' }}
            />
            <Legend />
            <Line type="monotone" dataKey="p10" name="P10" stroke="#94a3b8" strokeDasharray="5 5" />
            <Line type="monotone" dataKey="p50" name="P50" stroke="#22c55e" strokeWidth={2} />
            <Line type="monotone" dataKey="p90" name="P90" stroke="#6366f1" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Detalhamento por Turno</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-magic-muted border-b border-magic-border">
                <th className="text-left py-2 px-2">Turno</th>
                <th className="text-right py-2 px-2">Terrenos</th>
                <th className="text-right py-2 px-2">Dorks</th>
                <th className="text-right py-2 px-2">Rochas</th>
                <th className="text-right py-2 px-2">Ramp</th>
                <th className="text-right py-2 px-2">Total</th>
                <th className="text-right py-2 px-2">P50</th>
                <th className="text-right py-2 px-2">Land Drop</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((row: any) => (
                <tr key={row.turno} className="border-b border-magic-border">
                  <td className="py-2 px-2 font-medium">{row.turno}</td>
                  <td className="py-2 px-2 text-right">{row.mana_terrenos}</td>
                  <td className="py-2 px-2 text-right">{row.mana_dorks}</td>
                  <td className="py-2 px-2 text-right">{row.mana_rocks}</td>
                  <td className="py-2 px-2 text-right">{row.mana_land_ramp}</td>
                  <td className="py-2 px-2 text-right font-medium text-indigo-400">{row.total}</td>
                  <td className="py-2 px-2 text-right">{row.p50}</td>
                  <td className="py-2 px-2 text-right">{row.prob_land_drop}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
