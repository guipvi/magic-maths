/**
 * GoldfishSim — Feature 2 visualization.
 *
 * Renders the goldfish speed simulation from `simulate_goldfish()` response:
 * 1. Stats grid: avg/median/P10/P90 empty hand turn, probabilities by T5/T7
 * 2. Area chart: cards in hand per turn (avg + P10/P90 bands)
 * 3. Line chart: probability of empty hand per turn
 * 4. Profile card: land count, spell count, avg CMC
 *
 * Props `data` comes from GET /api/analysis/goldfish or the `goldfish` key
 * from /api/analysis/full.
 */
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, AreaChart, Area } from 'recharts'

interface Props {
  data: any
}

export default function GoldfishSim({ data }: Props) {
  const turnData = data.turn_by_turn || []

  const chartData = turnData.map((t: any) => ({
    turno: `T${t.turn}`,
    avg_hand: t.avg_cards_in_hand,
    median_hand: t.median_cards_in_hand,
    p10: t.p10_cards,
    p90: t.p90_cards,
    prob_empty: t.prob_empty_hand,
  }))

  const stats = [
    { label: 'Mão vazia (média)', value: `T${data.avg_empty_hand_turn}`, color: 'text-sky-400' },
    { label: 'Mediana', value: `T${data.median_empty_hand_turn}`, color: 'text-indigo-400' },
    { label: 'P10', value: `T${data.p10_empty_turn}`, color: 'text-emerald-400' },
    { label: 'P90', value: `T${data.p90_empty_turn}`, color: 'text-rose-400' },
    { label: 'Prob. vazio T5', value: `${(data.probability_empty_by_turn_5 * 100).toFixed(0)}%`, color: 'text-amber-400' },
    { label: 'Prob. vazio T7', value: `${(data.probability_empty_by_turn_7 * 100).toFixed(0)}%`, color: 'text-amber-400' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="card text-center">
            <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-magic-muted">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Cards na Mão por Turno (Simulação)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#f1f5f9' }}
            />
            <Legend />
            <Area type="monotone" dataKey="p90" name="P90" stroke="#6366f1" fill="#6366f1" fillOpacity={0.1} />
            <Area type="monotone" dataKey="avg_hand" name="Média" stroke="#22c55e" fill="#22c55e" fillOpacity={0.1} />
            <Area type="monotone" dataKey="p10" name="P10" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.1} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Probabilidade de Mão Vazia por Turno</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#f1f5f9' }}
              formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
            />
            <Line type="monotone" dataKey="prob_empty" name="Prob. mão vazia" stroke="#ef4444" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Perfil do Deck</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xl font-bold text-indigo-400">{data.deck_profile?.land_count}</p>
            <p className="text-xs text-magic-muted">Terrenos</p>
          </div>
          <div>
            <p className="text-xl font-bold text-indigo-400">{data.deck_profile?.spell_count}</p>
            <p className="text-xs text-magic-muted">Mágicas</p>
          </div>
          <div>
            <p className="text-xl font-bold text-indigo-400">{data.deck_profile?.avg_cmc}</p>
            <p className="text-xs text-magic-muted">CMC Médio</p>
          </div>
        </div>
      </div>
    </div>
  )
}
