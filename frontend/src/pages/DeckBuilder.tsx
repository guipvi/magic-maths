import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { decks, scryfall } from '../services/api'
import { Search, Upload, FileText, Loader2 } from 'lucide-react'

/**
 * Deck creation page for Magic Maths.
 *
 * Supports two modes:
 *   1. **Import** – paste a plain-text decklist and POST it via
 *      `decks.importDeck()` which parses card names server-side.
 *   2. **Search** – query Scryfall (`scryfall.search()`) and
 *      manually build a deck card-by-card, then POST via
 *      `decks.create()`.
 *
 * Both modes navigate to `/decks/:id` on success. Handles format
 * selection (Commander, Standard, Modern, etc.).
 *
 * @file DeckBuilder.tsx
 * @route /decks/new
 */
export default function DeckBuilder() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'import' | 'search'>('import')
  const [decklist, setDecklist] = useState('')
  const [deckName, setDeckName] = useState('')
  const [format, setFormat] = useState('commander')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [builtCards, setBuiltCards] = useState<{ name: string; quantity: number }[]>([])

  const handleImport = async () => {
    if (!decklist.trim()) {
      setError('Cole a decklist primeiro')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await decks.importDeck({
        decklist,
        name: deckName || undefined,
        format,
      })
      navigate(`/decks/${res.data.deck.id}`)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao importar deck')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const res = await scryfall.search(searchQuery)
      setSearchResults(res.data.data || [])
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const addToDeck = (name: string) => {
    setBuiltCards((prev) => {
      const existing = prev.find((c) => c.name === name)
      if (existing) {
        return prev.map((c) => c.name === name ? { ...c, quantity: c.quantity + 1 } : c)
      }
      return [...prev, { name, quantity: 1 }]
    })
  }

  const removeFromDeck = (name: string) => {
    setBuiltCards((prev) =>
      prev
        .map((c) => c.name === name ? { ...c, quantity: c.quantity - 1 } : c)
        .filter((c) => c.quantity > 0)
    )
  }

  const handleSaveBuilt = async () => {
    if (builtCards.length === 0) {
      setError('Adicione cards ao deck')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await decks.create({
        name: deckName || 'Deck sem nome',
        format,
        cards: builtCards.map((c) => ({ name: c.name, quantity: c.quantity })),
      })
      navigate(`/decks/${res.data.deck.id}`)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao salvar deck')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">Novo Deck</h1>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setMode('import')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === 'import' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-magic-muted hover:text-white'
          }`}
        >
          <Upload className="w-4 h-4" />
          Importar Decklist
        </button>
        <button
          onClick={() => setMode('search')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === 'search' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-magic-muted hover:text-white'
          }`}
        >
          <Search className="w-4 h-4" />
          Buscar Cards
        </button>
      </div>

      <div className="flex gap-3">
        <div className="flex-1">
          <label className="label">Nome do Deck</label>
          <input
            className="input"
            value={deckName}
            onChange={(e) => setDeckName(e.target.value)}
            placeholder="Meu Deck"
          />
        </div>
        <div className="w-40">
          <label className="label">Formato</label>
          <select
            className="input"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
          >
            <option value="commander">Commander</option>
            <option value="standard">Standard</option>
            <option value="modern">Modern</option>
            <option value="pioneer">Pioneer</option>
            <option value="legacy">Legacy</option>
            <option value="vintage">Vintage</option>
            <option value="pauper">Pauper</option>
            <option value="custom">Custom</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-300 px-4 py-2 rounded-lg text-sm">
          {error}
        </div>
      )}

      {mode === 'import' ? (
        <div className="card">
          <label className="label flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4" />
            Cole a decklist (formato texto)
          </label>
          <textarea
            className="input h-64 font-mono text-sm"
            value={decklist}
            onChange={(e) => setDecklist(e.target.value)}
            placeholder={`1 Comet, Stellar Pup\n1 Island\n99 Mountain\n\nSideboard\n3 Pyroblast`}
          />
          <p className="text-xs text-magic-muted mt-2">
            Formatos aceitos: "1 Nome do Card" ou "Nome do Card". Use "// Sideboard" ou "SB:" para separar.
          </p>
          <button
            onClick={handleImport}
            disabled={loading}
            className="btn-primary flex items-center gap-2 mt-4"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {loading ? 'Importando...' : 'Importar Deck'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="card">
            <div className="flex gap-2">
              <input
                className="input flex-1"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Buscar cards na Scryfall..."
              />
              <button onClick={handleSearch} disabled={searching} className="btn-primary">
                {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-3">Resultados</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                {searchResults.slice(0, 20).map((card: any) => (
                  <button
                    key={card.id}
                    onClick={() => addToDeck(card.name)}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800 text-left transition-colors"
                  >
                    {card.image_uris?.small && (
                      <img src={card.image_uris.small} alt="" className="w-10 h-14 rounded object-cover" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{card.name}</p>
                      <p className="text-xs text-magic-muted">{card.type_line} &mdash; {card.mana_cost || `CMC ${card.cmc}`}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {builtCards.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-3">Deck ({builtCards.reduce((a, c) => a + c.quantity, 0)} cards)</h3>
              <div className="max-h-64 overflow-y-auto space-y-1">
                {builtCards.map((card) => (
                  <div key={card.name} className="flex items-center justify-between py-1">
                    <span className="text-sm">
                      <span className="text-magic-muted">{card.quantity}x</span> {card.name}
                    </span>
                    <div className="flex gap-1">
                      <button
                        onClick={() => addToDeck(card.name)}
                        className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-0.5 rounded"
                      >
                        +
                      </button>
                      <button
                        onClick={() => removeFromDeck(card.name)}
                        className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-0.5 rounded"
                      >
                        -
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <button onClick={handleSaveBuilt} disabled={loading} className="btn-primary mt-4">
                {loading ? 'Salvando...' : 'Salvar Deck'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
