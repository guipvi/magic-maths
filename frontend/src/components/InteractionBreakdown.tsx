/**
 * InteractionBreakdown — Feature 3 visualization.
 *
 * Renders the interaction analysis from `analyze_interactions()` response:
 * 1. Summary cards: total interaction spells, removals, counters, gy hate
 * 2. Per-action breakdown cards with target-type chips
 *    (actions: destroy, exile, bounce, counter, damage, graveyard, tuck)
 *
 * Props `data` comes from GET /api/analysis/interactions or the `interactions`
 * key from /api/analysis/full.
 */
import { Shield, Trash2, Ban, Rabbit, RotateCcw, Skull } from 'lucide-react'

interface Props {
  data: any
}

const actionIcons: Record<string, any> = {
  destroy: Trash2,
  exile: Shield,
  bounce: RotateCcw,
  counter: Ban,
  damage: Rabbit,
  graveyard: Skull,
  tuck: RotateCcw,
}

const actionColors: Record<string, string> = {
  destroy: 'text-rose-400',
  exile: 'text-violet-400',
  bounce: 'text-sky-400',
  counter: 'text-indigo-400',
  damage: 'text-orange-400',
  graveyard: 'text-emerald-400',
  tuck: 'text-amber-400',
}

const actionLabels: Record<string, string> = {
  destroy: 'Destruir',
  exile: 'Exilar',
  bounce: 'Bounce',
  counter: 'Counterspell',
  damage: 'Dano',
  graveyard: 'Gy Hate',
  tuck: 'Tuck',
}

export default function InteractionBreakdown({ data }: Props) {
  const breakdown = data.breakdown || {}
  const targets = ['creature', 'artifact', 'enchantment', 'planeswalker', 'land', 'battle', 'permanent', 'spell', 'graveyard']

  const targetLabels: Record<string, string> = {
    creature: 'Criatura',
    artifact: 'Artefato',
    enchantment: 'Encantamento',
    planeswalker: 'Planeswalker',
    land: 'Terreno',
    battle: 'Batalha',
    permanent: 'Permanente',
    spell: 'Mágica',
    graveyard: 'Cemitério',
  }

  const activeActions = Object.entries(breakdown).filter(([_, v]: any) => v.total > 0)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-2xl font-bold text-indigo-400">{data.total_interaction_spells}</p>
          <p className="text-xs text-magic-muted">Total de Spells de Interação</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-rose-400">{data.total_removal}</p>
          <p className="text-xs text-magic-muted">Remoções (Destroy/Exile/Bounce)</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-indigo-400">{data.total_counterspells}</p>
          <p className="text-xs text-magic-muted">Counterspells</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-emerald-400">{data.total_graveyard_hate}</p>
          <p className="text-xs text-magic-muted">Graveyard Hate</p>
        </div>
      </div>

      {activeActions.map(([action, info]: any) => {
        const Icon = actionIcons[action] || Shield
        const color = actionColors[action] || 'text-magic-text'
        return (
          <div key={action} className="card">
            <h3 className={`font-semibold mb-3 flex items-center gap-2 ${color}`}>
              <Icon className="w-4 h-4" />
              {actionLabels[action] || action} ({info.total})
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {targets
                .filter((t) => (info.by_target?.[t] || 0) > 0)
                .map((target) => (
                  <div key={target} className="bg-slate-800 rounded-lg px-3 py-2 flex items-center justify-between">
                    <span className="text-sm text-magic-muted">{targetLabels[target] || target}</span>
                    <span className="text-sm font-semibold">{info.by_target[target]}</span>
                  </div>
                ))}
            </div>
          </div>
        )
      })}

      {activeActions.length === 0 && (
        <div className="card text-center text-magic-muted py-8">
          Nenhuma interação detectada neste deck
        </div>
      )}
    </div>
  )
}
