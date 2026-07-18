/**
 * LandRecommender — Feature 4 visualization.
 *
 * Renders the land recommendation from `recommend_lands()` response:
 * 1. Stats grid: recommended lands, current lands, range, deck profile
 * 2. Secondary stats: avg CMC, ramp count, draw count, deck size
 * 3. Mana curve bar chart (CMC distribution)
 * 4. Color source recommendations per color (pip-based)
 * 5. Formula metadata footer
 *
 * Props `data` comes from GET /api/analysis/land-recommendation or the
 * `land_recommendation` key from /api/analysis/full.
 */
import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface Props {
  data: any
  cards?: any[]
}

export default function LandRecommender({ data, cards = [] }: Props) {
  const [selectedCmc, setSelectedCmc] = useState<number | null>(null)

  const manaCurve = data.mana_curve || {}
  const curveData = Object.entries(manaCurve).map(([cmc, count]) => ({
    cmc: Number(cmc),
    label: `CMC ${cmc}`,
    count: count as number,
  }))

  const cardsByCmc: Record<number, any[]> = {}
  cards.forEach((entry: any) => {
    const c = entry.card
    if (!c || entry.is_sideboard) return
    const cmc = Math.floor(c.cmc)
    const qty = entry.quantity || 1
    for (let i = 0; i < qty; i++) {
      if (!cardsByCmc[cmc]) cardsByCmc[cmc] = []
      cardsByCmc[cmc].push(c)
    }
  })

  const selectedCards = selectedCmc != null ? (cardsByCmc[selectedCmc] || []) : []

  const profileLabels: Record<string, string> = {
    aggro: 'Aggro',
    midrange: 'Midrange',
    control: 'Control',
    combo: 'Combo',
    unknown: 'Desconhecido',
  }

  const profileColors: Record<string, string> = {
    aggro: 'text-rose-400',
    midrange: 'text-amber-400',
    control: 'text-indigo-400',
    combo: 'text-violet-400',
    unknown: 'text-magic-muted',
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-3xl font-bold text-indigo-400">{data.recommended_lands}</p>
          <p className="text-xs text-magic-muted">Terrenos Recomendados</p>
        </div>
        <div className="card text-center">
          <p className="text-3xl font-bold text-amber-400">{data.current_lands}</p>
          <p className="text-xs text-magic-muted">Terrenos Atuais</p>
        </div>
        <div className="card text-center">
          <p className="text-xl font-bold text-emerald-400">{data.range.low} &ndash; {data.range.high}</p>
          <p className="text-xs text-magic-muted">Range Recomendado</p>
        </div>
        <div className="card text-center">
          <p className={`text-xl font-bold ${profileColors[data.profile] || 'text-magic-text'} capitalize`}>
            {profileLabels[data.profile] || data.profile}
          </p>
          <p className="text-xs text-magic-muted">Perfil do Deck</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-lg font-bold text-magic-text">{data.avg_cmc}</p>
          <p className="text-xs text-magic-muted">CMC Médio</p>
        </div>
        <div className="card text-center">
          <p className="text-lg font-bold text-emerald-400">{data.ramp_count}</p>
          <p className="text-xs text-magic-muted">Ramp Spells</p>
        </div>
        <div className="card text-center">
          <p className="text-lg font-bold text-sky-400">{data.draw_count}</p>
          <p className="text-xs text-magic-muted">Draw Spells</p>
        </div>
        <div className="card text-center">
          <p className="text-lg font-bold text-magic-text">{data.deck_size}</p>
          <p className="text-xs text-magic-muted">Total de Cards</p>
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Curva de Mana Atual</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={curveData} onClick={(e) => {
            if (e?.activePayload?.[0]) {
              const cmc = e.activePayload[0].payload.cmc
              setSelectedCmc(prev => prev === cmc ? null : cmc)
            }
          }} style={{ cursor: 'pointer' }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="label" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#f1f5f9' }}
            />
            <Bar dataKey="count" name="Cards" radius={[4, 4, 0, 0]}
              fill="#6366f1"
              onClick={(_, index) => {
                const cmc = curveData[index]?.cmc
                if (cmc != null) setSelectedCmc(prev => prev === cmc ? null : cmc)
              }}
            />
          </BarChart>
        </ResponsiveContainer>
        {selectedCmc != null && (
          <div className="mt-4 border-t border-magic-border pt-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-sm">
                CMC {selectedCmc} — {selectedCards.length} {selectedCards.length === 1 ? 'carta' : 'cartas'}
              </h4>
              <button
                onClick={() => setSelectedCmc(null)}
                className="text-xs text-magic-muted hover:text-white transition-colors"
              >
                Fechar
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {selectedCards.map((c: any, i: number) => (
                <div key={`${c.id}-${i}`} className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-2">
                  {c.image_uris?.small ? (
                    <img src={c.image_uris.small} alt={c.name} className="w-10 h-14 rounded object-cover flex-shrink-0" />
                  ) : (
                    <div className="w-10 h-14 rounded bg-slate-700 flex-shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{c.name}</p>
                    <p className="text-xs text-magic-muted truncate">{c.mana_cost || '—'}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {Object.keys(data.color_sources || {}).length > 0 && (
        <div className="card">
          <h3 className="font-semibold mb-3">Fontes de Cor Recomendadas</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(data.color_sources).map(([color, count]) => (
              <div key={color} className="bg-slate-800 rounded-lg px-4 py-3 text-center">
                <p className="text-lg font-bold">{count as number}</p>
                <p className="text-xs text-magic-muted">
                  {color === 'W' ? 'Branca' : color === 'U' ? 'Azul' : color === 'B' ? 'Preta' : color === 'R' ? 'Vermelha' : color === 'G' ? 'Verde' : color}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card text-xs text-magic-muted">
        <p>Fórmula: {data.formula} (escalonada para {data.deck_size} cards)</p>
        <p>Ajuste aplicado por perfil: {data.adjustment_applied > 0 ? `+${data.adjustment_applied}` : data.adjustment_applied}</p>
      </div>
    </div>
  )
}
