import { Shield, Trash2, Ban, Rabbit, RotateCcw, Skull } from 'lucide-react'

interface Props {
  data: any
  categories?: any[]
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

export default function InteractionBreakdown({ data, categories }: Props) {
  const breakdown = data?.breakdown || {}
  const spells = data?.spells || []

  const activeActions = Object.entries(breakdown).filter(([_, v]: any) => v.total > 0)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-2xl font-bold text-indigo-400">{data?.total_interaction_spells ?? 0}</p>
          <p className="text-xs text-magic-muted">Total de Spells de Interação</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-rose-400">{data?.total_removal ?? 0}</p>
          <p className="text-xs text-magic-muted">Remoções (Destroy/Exile/Bounce)</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-indigo-400">{data?.total_counterspells ?? 0}</p>
          <p className="text-xs text-magic-muted">Counterspells</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-emerald-400">{data?.total_graveyard_hate ?? 0}</p>
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
          </div>
        )
      })}

      {spells.length > 0 && (
        <div className="card">
          <h3 className="font-semibold mb-3">Cartas Atribuídas</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-magic-muted border-b border-magic-border">
                  <th className="text-left py-2 px-2">Carta</th>
                  <th className="text-left py-2 px-2">Tipo</th>
                  <th className="text-left py-2 px-2">Ação</th>
                </tr>
              </thead>
              <tbody>
                {spells.map((s: any, i: number) => (
                  <tr key={i} className="border-b border-magic-border">
                    <td className="py-2 px-2 font-medium">{s.name}</td>
                    <td className="py-2 px-2 text-magic-muted">{s.type_line}</td>
                    <td className="py-2 px-2">
                      {s.interactions?.map((int: any, j: number) => (
                        <span key={j}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-700 mr-1 ${
                            actionColors[int.action] || 'text-magic-text'
                          }`}
                        >
                          {actionLabels[int.action] || int.action}
                        </span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeActions.length === 0 && (
        <div className="card text-center text-magic-muted py-8">
          Nenhuma interação atribuída a este deck.
          Atribua cartas às categorias de interação (destroy, exile, bounce, counter, damage, graveyard, tuck) na aba Categorias.
        </div>
      )}
    </div>
  )
}
