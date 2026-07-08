import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, LineChart, Line } from 'recharts'

const COLORS = ['#6366f1', '#22c55e', '#a855f7', '#f59e0b', '#ef4444', '#38bdf8', '#f97316', '#ec4899', '#14b8a6', '#8b5cf6']
const LANDS_COLOR = '#6366f1'

interface Props {
  data: any
}

export default function ManaCurveChart({ data }: Props) {
  const byTurnArr = data.by_turn ? Object.values(data.by_turn) : []

  if (byTurnArr.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-magic-muted">Nenhuma categoria ramp atribuída.</p>
        <p className="text-sm text-magic-muted mt-1">Atribua cartas a categorias do tipo ramp na aba Categorias para visualizar a curva de mana.</p>
      </div>
    )
  }

  return <CategoryManaCurve data={data} byTurnArr={byTurnArr} />
}

function CategoryManaCurve({ data, byTurnArr }: { data: any; byTurnArr: any[] }) {
  const rampCatNames = Object.keys(byTurnArr[0]?.ramp_contributions || {})

  const chartData = byTurnArr.map((t: any) => {
    const row: any = {
      turno: `T${t.turn}`,
      mana_terrenos: t.mana_from_lands,
      total: t.total_expected_mana,
      prob_land_drop: t.prob_hitting_land_drop,
      ...t.ramp_contributions,
    }
    return row
  })

  const summaryItems = [
    { label: 'Total de Lands', value: data.land_count },
    { label: 'CMC Médio', value: data.avg_cmc },
    { label: 'Total Ramp', value: data.total_ramp },
  ]
  if (data.total_draw !== undefined) {
    summaryItems.push({ label: 'Total Draw', value: data.total_draw })
  }
  if (data.total_alcance !== undefined) {
    summaryItems.push({ label: 'Total Alcance', value: data.total_alcance })
  }

  const rampColors: Record<string, string> = {}
  rampCatNames.forEach((name, i) => {
    rampColors[name] = COLORS[(i + 1) % COLORS.length]
  })

  const probData = byTurnArr.map((t: any) => {
    const row: any = { turno: `T${t.turn}` }
    if (t.categories) {
      Object.values(t.categories).forEach((cat: any) => {
        if (cat.type === 'ramp') {
          row[`${cat.name}_>=1`] = cat.prob_at_least_1 ?? 0
        }
      })
    }
    return row
  })
  const probRampCats = probData.length > 0
    ? Object.keys(probData[0]).filter(k => k.endsWith('_>=1'))
    : []

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
        {summaryItems.map((item) => (
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
            <Bar dataKey="mana_terrenos" name="Terrenos" stackId="a" fill={LANDS_COLOR} />
            {rampCatNames.map((name) => (
              <Bar key={name} dataKey={name} name={name} stackId="a" fill={rampColors[name]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Probabilidade de Ramp por Turno</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={probData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#f1f5f9' }}
              formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
            />
            <Legend />
            {probRampCats.map((key) => {
              const catName = key.replace('_>=1', '')
              return (
                <Line key={key} type="monotone" dataKey={key} name={catName}
                  stroke={rampColors[catName] || '#22c55e'} strokeWidth={2} />
              )
            })}
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
                {rampCatNames.map((name) => (
                  <th key={name} className="text-right py-2 px-2">{name}</th>
                ))}
                <th className="text-right py-2 px-2">Total</th>
                <th className="text-right py-2 px-2">Land Drop</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((row: any) => (
                <tr key={row.turno} className="border-b border-magic-border">
                  <td className="py-2 px-2 font-medium">{row.turno}</td>
                  <td className="py-2 px-2 text-right">{row.mana_terrenos?.toFixed(1)}</td>
                  {rampCatNames.map((name) => (
                    <td key={name} className="py-2 px-2 text-right">{row[name]?.toFixed(2)}</td>
                  ))}
                  <td className="py-2 px-2 text-right font-medium text-indigo-400">{row.total?.toFixed(1)}</td>
                  <td className="py-2 px-2 text-right">{row.prob_land_drop != null ? `${(row.prob_land_drop * 100).toFixed(0)}%` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
