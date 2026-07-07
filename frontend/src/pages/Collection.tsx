import { useState, useEffect, FormEvent } from 'react'
import { collection } from '../services/api'
import { PackageOpen, Plus, Trash2, Search, Loader2 } from 'lucide-react'

/**
 * Personal card collection page for Magic Maths.
 *
 * Fetches the user's collection from `collection.list()` (GET
 * `/api/collection`) on mount. Allows adding cards by name and
 * quantity via `collection.add()`, and deleting entries via
 * `collection.delete()`. Supports client-side filtering by card
 * name. Displays card name, CMC, type, quantity, condition, and
 * foil status.
 *
 * @file Collection.tsx
 * @route /collection
 */
interface CollectionEntry {
  id: number
  card: { name: string; oracle_id: string; cmc: number; type_line: string }
  quantity: number
  is_foil: boolean
  condition: string
}

export default function Collection() {
  const [entries, setEntries] = useState<CollectionEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [cardName, setCardName] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const loadCollection = () => {
    setLoading(true)
    collection.list()
      .then((res) => setEntries(res.data.collection))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadCollection()
  }, [])

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!cardName.trim()) return
    setAdding(true)
    try {
      await collection.add({ card_name: cardName.trim(), quantity })
      setCardName('')
      setQuantity(1)
      loadCollection()
    } catch (err) {
      console.error(err)
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await collection.delete(id)
      setEntries((prev) => prev.filter((e) => e.id !== id))
    } catch (err) {
      console.error(err)
    }
  }

  const filtered = searchTerm
    ? entries.filter((e) => e.card?.name?.toLowerCase().includes(searchTerm.toLowerCase()))
    : entries

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <PackageOpen className="w-6 h-6 text-indigo-400" />
          Minha Coleção
        </h1>
        <span className="text-sm text-magic-muted">
          {entries.reduce((a, e) => a + e.quantity, 0)} cards
        </span>
      </div>

      <div className="card">
        <form onSubmit={handleAdd} className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="label">Nome do Card</label>
            <input
              className="input"
              value={cardName}
              onChange={(e) => setCardName(e.target.value)}
              placeholder="Ex: Sol Ring"
            />
          </div>
          <div className="w-24">
            <label className="label">Qtd</label>
            <input
              type="number"
              min={1}
              className="input"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            />
          </div>
          <button type="submit" disabled={adding || !cardName.trim()} className="btn-primary flex items-center gap-2">
            {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Adicionar
          </button>
        </form>
      </div>

      {entries.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <Search className="w-4 h-4 text-magic-muted" />
            <input
              className="input flex-1"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filtrar cards..."
            />
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-magic-muted">Carregando...</div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-12">
          <PackageOpen className="w-12 h-12 text-magic-muted mx-auto mb-3" />
          <p className="text-magic-muted">
            {searchTerm ? 'Nenhum card encontrado' : 'Sua coleção está vazia'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-magic-muted border-b border-magic-border">
                <th className="text-left py-3 px-2">Card</th>
                <th className="text-center py-3 px-2">CMC</th>
                <th className="text-left py-3 px-2">Tipo</th>
                <th className="text-center py-3 px-2">Qtd</th>
                <th className="text-center py-3 px-2">Condição</th>
                <th className="text-right py-3 px-2">Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => (
                <tr key={entry.id} className="border-b border-magic-border hover:bg-slate-800/50">
                  <td className="py-3 px-2 font-medium">{entry.card?.name || '---'}</td>
                  <td className="py-3 px-2 text-center">{entry.card?.cmc ?? '---'}</td>
                  <td className="py-3 px-2 text-magic-muted text-xs">{entry.card?.type_line || '---'}</td>
                  <td className="py-3 px-2 text-center">
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-sm font-medium">
                      {entry.quantity}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-center text-xs text-magic-muted">
                    {entry.condition}{entry.is_foil ? ' ✦' : ''}
                  </td>
                  <td className="py-3 px-2 text-right">
                    <button
                      onClick={() => handleDelete(entry.id)}
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
  )
}
