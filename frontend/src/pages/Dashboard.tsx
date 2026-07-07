import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { decks } from '../services/api'
import { BarChart3, Layers, Shield, Map, TrendingUp, Plus, Trash2, Sword } from 'lucide-react'

/**
 * Main dashboard page for Magic Maths.
 *
 * Fetches the authenticated user's decks from `decks.list()` (GET
 * `/api/decks`) on mount. Displays feature cards (Mana Ramp, Goldfish
 * Speed, Interactions, Lands) and a table of existing decks with
 * delete capability. Clicking a deck row navigates to `/decks/:id`.
 * Includes a "Novo Deck" link to `/decks/new`.
 *
 * @file Dashboard.tsx
 * @route /
 */
interface DeckSummary {
  id: string
  name: string
  format: string
  card_count: number
  created_at: string
}

export default function Dashboard() {
  const [deckList, setDeckList] = useState<DeckSummary[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    decks.list()
      .then((res) => setDeckList(res.data.decks))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Deletar "${name}"?`)) return
    try {
      await decks.delete(id)
      setDeckList((prev) => prev.filter((d) => d.id !== id))
    } catch (err) {
      console.error(err)
    }
  }

  const features = [
    { icon: BarChart3, title: 'Mana Ramp', desc: 'Previsão de mana por turno com ramps, draws e manipulação', color: 'text-emerald-400', bg: 'bg-emerald-900/20' },
    { icon: TrendingUp, title: 'Goldfish Speed', desc: 'Simulação de velocidade de esvaziamento da mão', color: 'text-sky-400', bg: 'bg-sky-900/20' },
    { icon: Shield, title: 'Interações', desc: 'Contagem de remoções, counterspells e graveyard hate por tipo', color: 'text-rose-400', bg: 'bg-rose-900/20' },
    { icon: Map, title: 'Terrenos', desc: 'Recomendação de lands baseada na fórmula de Frank Karsten', color: 'text-amber-400', bg: 'bg-amber-900/20' },
  ]

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-magic-muted mt-1">Análise estatística de decks de Magic</p>
        </div>
        <Link to="/decks/new" className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Novo Deck
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map((f) => {
          const Icon = f.icon
          return (
            <div key={f.title} className="card">
              <div className={`w-10 h-10 rounded-lg ${f.bg} flex items-center justify-center mb-3`}>
                <Icon className={`w-5 h-5 ${f.color}`} />
              </div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-magic-muted">{f.desc}</p>
            </div>
          )
        })}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-400" />
          Seus Decks
        </h2>
        {loading ? (
          <div className="text-magic-muted py-8 text-center">Carregando...</div>
        ) : deckList.length === 0 ? (
          <div className="text-center py-12">
            <Sword className="w-12 h-12 text-magic-muted mx-auto mb-3" />
            <p className="text-magic-muted mb-4">Nenhum deck ainda</p>
            <Link to="/decks/new" className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Criar Primeiro Deck
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-magic-muted border-b border-magic-border">
                  <th className="text-left py-3 px-2">Nome</th>
                  <th className="text-left py-3 px-2">Formato</th>
                  <th className="text-center py-3 px-2">Cards</th>
                  <th className="text-right py-3 px-2">Ações</th>
                </tr>
              </thead>
              <tbody>
                {deckList.map((deck) => (
                  <tr
                    key={deck.id}
                    className="border-b border-magic-border hover:bg-slate-800/50 cursor-pointer"
                    onClick={() => navigate(`/decks/${deck.id}`)}
                  >
                    <td className="py-3 px-2 font-medium">{deck.name}</td>
                    <td className="py-3 px-2 text-magic-muted capitalize">{deck.format}</td>
                    <td className="py-3 px-2 text-center">{deck.card_count}</td>
                    <td className="py-3 px-2 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(deck.id, deck.name) }}
                        className="text-red-400 hover:text-red-300 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
