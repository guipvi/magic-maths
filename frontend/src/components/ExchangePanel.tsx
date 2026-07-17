import { useState, useEffect, useCallback } from 'react'
import {
  Search, ArrowRightLeft, Plus, Trash2, Loader2, Save, ChevronDown, ChevronUp,
  Zap, Link2, BarChart3, Check, X,
} from 'lucide-react'
import { scryfall, trades as tradesApi, analysis, categories as categoriesApi } from '../services/api'
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'

interface ExchangePanelProps {
  deckId: string
  cards: any[]
  currentAnalysis?: any
  onUpdate: () => void
}

export default function ExchangePanel({ deckId, cards, currentAnalysis, onUpdate }: ExchangePanelProps) {
  const [trades, setTrades] = useState<any[]>([])
  const [allCategories, setAllCategories] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedOut, setSelectedOut] = useState('')
  const [selectedIn, setSelectedIn] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [expandedTradeId, setExpandedTradeId] = useState<number | null>(null)
  const [whatIfResult, setWhatIfResult] = useState<any>(null)
  const [analyzing, setAnalyzing] = useState(false)

  const refreshTrades = useCallback(() => {
    tradesApi.list(deckId).then(r => setTrades(r.data.trades || []))
  }, [deckId])

  useEffect(() => {
    refreshTrades()
    categoriesApi.list().then(r => setAllCategories(r.data || []))
  }, [refreshTrades])

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

  const handleAddTrade = async () => {
    if (!selectedOut) {
      setError('Selecione um card para sair')
      return
    }
    if (!selectedIn) {
      setError('Selecione um card para entrar')
      return
    }
    setLoading(true)
    setError('')
    try {
      await tradesApi.create(deckId, {
        card_out_name: selectedOut,
        card_in_name: selectedIn.name,
      })
      refreshTrades()
      setSelectedOut('')
      setSelectedIn(null)
      setSearchQuery('')
      setSearchResults([])
      setSuccess(`"${selectedIn.name}" adicionada ao pool de trocas`)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao criar troca')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveTrade = async (tradeId: number) => {
    try {
      await tradesApi.remove(deckId, tradeId)
      refreshTrades()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao remover troca')
    }
  }

  const handleUpdateTradeConfig = async (tradeId: number, planned_assignment: any, planned_triggers: any) => {
    try {
      await tradesApi.update(deckId, tradeId, { planned_assignment, planned_triggers })
      refreshTrades()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao atualizar config')
    }
  }

  const handleWhatIf = async () => {
    setAnalyzing(true)
    setError('')
    setWhatIfResult(null)
    try {
      const res = await analysis.whatIf({ deck_id: deckId })
      setWhatIfResult(res.data)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao analisar impacto')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleExecuteAll = async () => {
    if (!trades.length) return
    setExecuting(true)
    setError('')
    setSuccess('')
    try {
      const res = await tradesApi.execute(deckId)
      setSuccess(res.data.message || 'Trocas executadas com sucesso')
      refreshTrades()
      setWhatIfResult(null)
      onUpdate()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao executar trocas')
    } finally {
      setExecuting(false)
    }
  }

  const catLabel = (c: any) => {
    if (!c) return '?'
    if (c.parent_id) {
      const parent = allCategories.find(p => p.id === c.parent_id)
      if (parent) return `${parent.name} › ${c.name}`
    }
    return c.name
  }

  const deckTotal = cards.reduce((sum: number, c: any) => sum + (c.quantity || 1), 0)
  const pendingOut = trades.reduce((sum: number, t: any) => sum + (t.quantity || 1), 0)
  const pendingIn = trades.reduce((sum: number, t: any) => sum + (t.quantity || 1), 0)

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
      <div className="p-6 border-b border-slate-800">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <ArrowRightLeft className="w-5 h-5 text-indigo-400" />
          Pool de Trocas
        </h2>
        <p className="text-magic-muted text-sm mt-1">
          Acumule trocas pendentes, configure atribuições e triggers, analise o impacto e execute todas de uma vez.
        </p>
      </div>

      <div className="p-6 space-y-6">
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 text-red-300 rounded-lg text-sm">{error}</div>
        )}
        {success && (
          <div className="p-3 bg-green-900/30 border border-green-700 text-green-300 rounded-lg text-sm">{success}</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <label className="block text-sm font-medium text-slate-300">Sai do Deck</label>
            <select
              value={selectedOut}
              onChange={(e) => setSelectedOut(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-indigo-500 outline-none appearance-none"
            >
              <option value="">Selecione um card...</option>
              {cards
                .filter((c: any) => !c.is_sideboard)
                .sort((a: any, b: any) => a.card.name.localeCompare(b.card.name))
                .map((c: any) => (
                  <option key={c.id} value={c.card.name}>
                    {c.card.name} {c.quantity > 1 ? `(${c.quantity}x)` : ''}
                  </option>
                ))}
            </select>
            {selectedOut && (
              <div className="p-3 bg-red-900/20 border border-red-900/30 rounded-lg flex items-center gap-3">
                <Trash2 className="w-4 h-4 text-red-400 shrink-0" />
                <span className="text-red-200 font-medium text-sm">{selectedOut}</span>
              </div>
            )}
          </div>

          <div className="space-y-4">
            <label className="block text-sm font-medium text-slate-300">Entra no Deck</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setSelectedIn(null) }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Nome do card..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={searching}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors"
              >
                {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Buscar'}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div className="max-h-[300px] overflow-y-auto bg-slate-800 border border-slate-700 rounded-lg divide-y divide-slate-700">
                {searchResults.map((card) => (
                  <button
                    key={card.id}
                    onClick={() => setSelectedIn(card)}
                    className={`w-full text-left px-4 py-3 hover:bg-slate-700 transition-colors flex items-center justify-between ${
                      selectedIn?.id === card.id ? 'bg-indigo-900/30 border-l-4 border-l-indigo-500' : ''
                    }`}
                  >
                    <div>
                      <div className="font-medium text-white">{card.name}</div>
                      <div className="text-xs text-slate-400">{card.type_line}</div>
                    </div>
                    {selectedIn?.id === card.id ? (
                      <Check className="w-4 h-4 text-indigo-400" />
                    ) : (
                      <Plus className="w-4 h-4 text-slate-500" />
                    )}
                  </button>
                ))}
              </div>
            )}

            {selectedIn && (
              <div className="p-3 bg-green-900/20 border border-green-900/30 rounded-lg flex items-center gap-3">
                <Plus className="w-4 h-4 text-green-400 shrink-0" />
                <span className="text-green-200 font-medium text-sm">{selectedIn.name}</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-center">
          <button
            onClick={handleAddTrade}
            disabled={loading || !selectedOut || !selectedIn}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-lg font-semibold flex items-center gap-2 transition-all"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
            Adicionar ao Pool
          </button>
        </div>

        {trades.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-slate-300">
                Pool de Trocas ({trades.length} pendente{trades.length > 1 ? 's' : ''})
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={handleWhatIf}
                  disabled={analyzing}
                  className="bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                >
                  {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                  Analisar Impacto
                </button>
                <button
                  onClick={handleExecuteAll}
                  disabled={executing}
                  className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors"
                >
                  {executing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Executar Todas
                </button>
              </div>
            </div>

            <div className="space-y-2">
              {trades.map((trade) => (
                <TradeCard
                  key={trade.id}
                  trade={trade}
                  allCategories={allCategories}
                  deckCards={cards}
                  catLabel={catLabel}
                  expanded={expandedTradeId === trade.id}
                  onToggleExpand={() => setExpandedTradeId(expandedTradeId === trade.id ? null : trade.id)}
                  onRemove={() => handleRemoveTrade(trade.id)}
                  onSaveConfig={(pa, pt) => handleUpdateTradeConfig(trade.id, pa, pt)}
                />
              ))}
            </div>
          </div>
        )}

        {trades.length > 0 && (
          <div className="bg-slate-800/50 rounded-lg p-4">
            <h4 className="text-xs font-medium text-slate-400 mb-2">Preview do Deck</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-magic-muted">Atual:</span>{' '}
                <span className="text-white font-medium">{deckTotal} cards</span>
              </div>
              <div>
                <span className="text-magic-muted">Após trocas:</span>{' '}
                <span className="text-white font-medium">{deckTotal - pendingOut + pendingIn} cards</span>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {trades.map((t: any) => (
                <span key={t.id} className="inline-flex items-center gap-1 text-xs">
                  <span className="text-red-300 line-through">{t.card_out?.name}</span>
                  <ArrowRightLeft className="w-3 h-3 text-magic-muted" />
                  <span className="text-green-300">{t.card_in?.name}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {whatIfResult && (
          <WhatIfComparison before={currentAnalysis} after={whatIfResult} />
        )}

        {trades.length === 0 && !loading && (
          <div className="text-center py-8 text-magic-muted text-sm">
            Nenhuma troca pendente. Use os campos acima para adicionar trocas ao pool.
          </div>
        )}
      </div>
    </div>
  )
}

function TradeCard({ trade, allCategories, deckCards, catLabel, expanded, onToggleExpand, onRemove, onSaveConfig }: {
  trade: any
  allCategories: any[]
  deckCards: any[]
  catLabel: (c: any) => string
  expanded: boolean
  onToggleExpand: () => void
  onRemove: () => void
  onSaveConfig: (pa: any, pt: any) => void
}) {
  const pa = trade.planned_assignment
  const pt = trade.planned_triggers

  const [assignCategory, setAssignCategory] = useState<number | ''>(pa?.category_id || '')
  const [assignMultiplier, setAssignMultiplier] = useState(pa?.multiplier ?? 1)
  const [assignManaAmount, setAssignManaAmount] = useState<number | ''>(pa?.mana_amount ?? '')
  const [assignSameTurn, setAssignSameTurn] = useState(pa?.same_turn ?? false)
  const [assignIsPermanent, setAssignIsPermanent] = useState(pa?.is_permanent ?? true)
  const [assignMaxPerTurn, setAssignMaxPerTurn] = useState<number | ''>(pa?.max_per_turn ?? '')
  const [assignWaitFor, setAssignWaitFor] = useState<number[]>(pa?.wait_for_category_ids || [])
  const [assignLimitCategory, setAssignLimitCategory] = useState<number | ''>(pa?.limit_category_id ?? '')
  const [assignLimitOnlySubsequent, setAssignLimitOnlySubsequent] = useState(pa?.limit_only_subsequent ?? false)
  const [assignTutoredCard, setAssignTutoredCard] = useState(pa?.tutored_card_id ?? '')

  const [triggerSourceCategory, setTriggerSourceCategory] = useState<number | ''>('')
  const [triggerSourceCard, setTriggerSourceCard] = useState<number | ''>('')
  const [triggerTarget, setTriggerTarget] = useState<number | ''>('')
  const [triggerCount, setTriggerCount] = useState(1)
  const [triggerPerTurn, setTriggerPerTurn] = useState<(number | null)[]>(pt?.[0]?.per_turn || Array(10).fill(null))
  const [triggerSameTurn, setTriggerSameTurn] = useState(false)
  const [triggerIsPermanent, setTriggerIsPermanent] = useState(true)
  const [triggers, setTriggers] = useState<any[]>(pt || [])

  useEffect(() => {
    const p = trade.planned_assignment
    const t = trade.planned_triggers
    if (p) {
      setAssignCategory(p.category_id || '')
      setAssignMultiplier(p.multiplier ?? 1)
      setAssignManaAmount(p.mana_amount ?? '')
      setAssignSameTurn(p.same_turn ?? false)
      setAssignIsPermanent(p.is_permanent ?? true)
      setAssignMaxPerTurn(p.max_per_turn ?? '')
      setAssignWaitFor(p.wait_for_category_ids || [])
      setAssignLimitCategory(p.limit_category_id ?? '')
      setAssignLimitOnlySubsequent(p.limit_only_subsequent ?? false)
      setAssignTutoredCard(p.tutored_card_id ?? '')
    } else {
      setAssignCategory('')
      setAssignMultiplier(1)
      setAssignManaAmount('')
      setAssignSameTurn(false)
      setAssignIsPermanent(true)
      setAssignMaxPerTurn('')
      setAssignWaitFor([])
      setAssignLimitCategory('')
      setAssignLimitOnlySubsequent(false)
      setAssignTutoredCard('')
    }
    setTriggers(t || [])
  }, [trade.id, trade.planned_assignment, trade.planned_triggers])

  const selectedCat = allCategories.find(c => c.id === assignCategory)
  const isRamp = selectedCat?.config?.type === 'ramp'
  const isTutor = selectedCat?.config?.type === 'tutor'

  const triggerSourceCat = allCategories.find(c => c.id === triggerSourceCategory)
  const triggerTargetCat = allCategories.find(c => c.id === triggerTarget)
  const isTriggerTargetRamp = triggerTargetCat?.config?.type === 'ramp'

  const handleSave = () => {
    const pa = assignCategory !== '' ? {
      category_id: Number(assignCategory),
      multiplier: assignMultiplier,
      mana_amount: isRamp ? (assignManaAmount === '' ? null : Number(assignManaAmount)) : null,
      same_turn: isRamp ? assignSameTurn : null,
      is_permanent: isRamp ? assignIsPermanent : null,
      max_per_turn: assignMaxPerTurn === '' ? null : Number(assignMaxPerTurn),
      tutored_card_id: isTutor ? (assignTutoredCard === '' ? null : Number(assignTutoredCard)) : null,
      wait_for_category_ids: assignWaitFor.length > 0 ? assignWaitFor : undefined,
      limit_category_id: assignLimitCategory === '' ? null : Number(assignLimitCategory),
      limit_only_subsequent: assignLimitCategory !== '' ? assignLimitOnlySubsequent : undefined,
    } : null
    onSaveConfig(pa, triggers.length > 0 ? triggers : null)
  }

  const addTrigger = () => {
    if (triggerSourceCategory === '' || triggerTarget === '') return
    const newTrigger = {
      source_category_id: Number(triggerSourceCategory),
      source_card_id: triggerSourceCard !== '' ? Number(triggerSourceCard) : null,
      target_category_id: Number(triggerTarget),
      trigger_count: triggerCount,
      per_turn: triggerPerTurn.some(v => v !== null) ? triggerPerTurn : null,
      is_permanent: isTriggerTargetRamp ? triggerIsPermanent : null,
      same_turn: isTriggerTargetRamp ? triggerSameTurn : null,
    }
    setTriggers([...triggers, newTrigger])
    setTriggerSourceCategory('')
    setTriggerSourceCard('')
    setTriggerTarget('')
    setTriggerCount(1)
    setTriggerPerTurn(Array(10).fill(null))
    setTriggerSameTurn(false)
    setTriggerIsPermanent(true)
  }

  const removeTrigger = (idx: number) => {
    setTriggers(triggers.filter((_, i) => i !== idx))
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="flex items-center p-4 gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="shrink-0">
            {trade.card_out?.image_uris?.small ? (
              <img src={trade.card_out.image_uris.small} alt="" className="w-10 h-14 rounded object-cover" />
            ) : (
              <div className="w-10 h-14 rounded bg-slate-700 flex items-center justify-center text-[10px] text-magic-muted">?</div>
            )}
          </div>
          <div className="text-red-300 font-medium text-sm truncate">{trade.card_out?.name}</div>
          <ArrowRightLeft className="w-4 h-4 text-magic-muted shrink-0" />
          <div className="shrink-0">
            {trade.card_in?.image_uris?.small ? (
              <img src={trade.card_in.image_uris.small} alt="" className="w-10 h-14 rounded object-cover" />
            ) : (
              <div className="w-10 h-14 rounded bg-slate-700 flex items-center justify-center text-[10px] text-magic-muted">?</div>
            )}
          </div>
          <div className="text-green-300 font-medium text-sm truncate">{trade.card_in?.name}</div>
          {trade.planned_assignment && (
            <span className="text-[10px] bg-indigo-900/50 text-indigo-300 px-1.5 py-0.5 rounded shrink-0">
              <Zap className="w-2.5 h-2.5 inline mr-0.5" />
              config
            </span>
          )}
        </div>
        <button onClick={onToggleExpand} className="text-magic-muted hover:text-white transition-colors shrink-0">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        <button onClick={onRemove} className="text-red-400 hover:text-red-300 transition-colors shrink-0">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {expanded && (
        <div className="border-t border-slate-700 p-4 space-y-4">
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-slate-400 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Atribuição para a carta que entra
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              <select
                value={assignCategory}
                onChange={(e) => setAssignCategory(e.target.value === '' ? '' : Number(e.target.value))}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="">Sem atribuição</option>
                {allCategories.map(cat => (
                  <option key={cat.id} value={cat.id}>{catLabel(cat)}</option>
                ))}
              </select>

              {isTutor ? (
                <select
                  value={assignTutoredCard}
                  onChange={(e) => setAssignTutoredCard(e.target.value === '' ? '' : Number(e.target.value))}
                  className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">Carta tutoriada...</option>
                  {deckCards.filter((c: any) => !c.is_sideboard).map((c: any) => (
                    <option key={c.card_id} value={c.card_id}>{c.card?.name}</option>
                  ))}
                </select>
              ) : isRamp ? (
                <input
                  type="number"
                  value={assignManaAmount}
                  min={0}
                  onChange={(e) => setAssignManaAmount(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="Mana gerada"
                  className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              ) : (
                <input
                  type="number"
                  value={assignMultiplier}
                  min={0}
                  step={0.5}
                  onChange={(e) => setAssignMultiplier(Number(e.target.value))}
                  placeholder="Multiplicador"
                  className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              )}

              <input
                type="number"
                value={assignMaxPerTurn}
                min={0}
                onChange={(e) => setAssignMaxPerTurn(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="Max/turno"
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>

            {isRamp && (
              <div className="flex gap-3 flex-wrap items-center">
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={assignSameTurn} onChange={(e) => setAssignSameTurn(e.target.checked)} />
                  Mesmo turno
                </label>
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={assignIsPermanent} onChange={(e) => setAssignIsPermanent(e.target.checked)} />
                  Permanente
                </label>
                {!assignIsPermanent && <span className="text-xs text-amber-400">Ritual</span>}
              </div>
            )}

            <div>
              <label className="text-[10px] text-magic-muted">Esperar castar para</label>
              <div className="flex flex-wrap gap-1 mt-1">
                {assignWaitFor.map(catId => {
                  const cat = allCategories.find(c => c.id === catId)
                  return (
                    <span key={catId} className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-600 rounded text-xs">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat?.color }} />
                      {catLabel(cat || { parent_id: null, name: String(catId) })}
                      <button onClick={() => setAssignWaitFor(assignWaitFor.filter(id => id !== catId))} className="text-magic-muted hover:text-white">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )
                })}
                <select value="" onChange={(e) => {
                  const val = Number(e.target.value)
                  if (val && !assignWaitFor.includes(val)) setAssignWaitFor([...assignWaitFor, val])
                  e.target.value = ''
                }} className="bg-slate-700 border border-slate-600 rounded px-2 py-0.5 text-xs text-white outline-none">
                  <option value="">+ Adicionar...</option>
                  {allCategories.filter(c => !assignWaitFor.includes(c.id)).map(cat => (
                    <option key={cat.id} value={cat.id}>{catLabel(cat)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-[10px] text-magic-muted">Limitar por:</label>
              <select
                value={assignLimitCategory}
                onChange={(e) => {
                  setAssignLimitCategory(e.target.value === '' ? '' : Number(e.target.value))
                  if (e.target.value === '') setAssignLimitOnlySubsequent(false)
                }}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-0.5 text-xs text-white outline-none"
              >
                <option value="">Sem limite</option>
                {allCategories.filter(c => c.id !== assignCategory).map(cat => (
                  <option key={cat.id} value={cat.id}>{catLabel(cat)}</option>
                ))}
              </select>
              {assignLimitCategory !== '' && (
                <label className="flex items-center gap-1 text-xs">
                  <input type="checkbox" checked={assignLimitOnlySubsequent} onChange={(e) => setAssignLimitOnlySubsequent(e.target.checked)} />
                  Subsequentes
                </label>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-medium text-slate-400 flex items-center gap-1">
              <Link2 className="w-3 h-3" /> Triggers
            </h4>
            <div className="flex gap-2 items-end flex-wrap">
              <select
                value={triggerSourceCategory}
                onChange={(e) => setTriggerSourceCategory(e.target.value === '' ? '' : Number(e.target.value))}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="">Categoria fonte...</option>
                {allCategories.map(cat => (
                  <option key={cat.id} value={cat.id}>{catLabel(cat)}</option>
                ))}
              </select>
              <select
                value={triggerSourceCard}
                onChange={(e) => setTriggerSourceCard(e.target.value === '' ? '' : Number(e.target.value))}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="">Sem condição</option>
                {deckCards.filter((c: any) => !c.is_sideboard).map((c: any) => (
                  <option key={c.card_id} value={c.card_id}>{c.card?.name}</option>
                ))}
              </select>
              <span className="text-magic-muted text-sm">→</span>
              <select
                value={triggerTarget}
                onChange={(e) => setTriggerTarget(e.target.value === '' ? '' : Number(e.target.value))}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="">Categoria alvo...</option>
                {allCategories.map(cat => (
                  <option key={cat.id} value={cat.id}>{catLabel(cat)}</option>
                ))}
              </select>
              <input
                type="number"
                value={triggerCount}
                min={1}
                onChange={(e) => setTriggerCount(Number(e.target.value))}
                placeholder="Eventos"
                className="w-20 bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              />
              <button onClick={addTrigger} disabled={triggerSourceCategory === '' || triggerTarget === ''} className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 transition-colors">
                <Plus className="w-3 h-3" /> Trigger
              </button>
            </div>

            <details className="mt-1">
              <summary className="text-[10px] text-magic-muted cursor-pointer hover:text-white">
                Multiplicador por turno
              </summary>
              <div className="grid grid-cols-10 gap-1 mt-2">
                {triggerPerTurn.map((v, i) => (
                  <div key={i} className="flex flex-col items-center">
                    <span className="text-[10px] text-magic-muted">T{i + 1}</span>
                    <input
                      type="number"
                      value={v ?? ''}
                      onChange={(e) => {
                        const next = [...triggerPerTurn]
                        next[i] = e.target.value === '' ? null : Number(e.target.value)
                        setTriggerPerTurn(next)
                      }}
                      className="w-full bg-slate-700 border border-slate-600 rounded text-xs text-center text-white px-1 py-0.5 outline-none"
                      placeholder="-"
                    />
                  </div>
                ))}
              </div>
            </details>

            {isTriggerTargetRamp && (
              <div className="flex gap-3 flex-wrap items-center">
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={triggerSameTurn} onChange={(e) => setTriggerSameTurn(e.target.checked)} />
                  Mesmo turno
                </label>
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={triggerIsPermanent} onChange={(e) => setTriggerIsPermanent(e.target.checked)} />
                  Permanente
                </label>
                {!triggerIsPermanent && <span className="text-xs text-amber-400">Ritual</span>}
              </div>
            )}

            {triggers.length > 0 && (
              <div className="space-y-1">
                {triggers.map((t, idx) => {
                  const srcCat = allCategories.find(c => c.id === t.source_category_id)
                  const tgtCat = allCategories.find(c => c.id === t.target_category_id)
                  const isTgtRamp = tgtCat?.config?.type === 'ramp'
                  const condCard = t.source_card_id ? deckCards.find((c: any) => c.card_id === t.source_card_id) : null
                  return (
                    <div key={idx} className="flex items-center gap-2 text-xs bg-slate-700/50 rounded px-2 py-1 flex-wrap">
                      <span className="text-magic-muted">Quando</span>
                      <span className="text-indigo-300">{catLabel(srcCat || { parent_id: null, name: '?' })}</span>
                      {condCard && (
                        <>
                          <span className="text-magic-muted">e</span>
                          <span className="text-blue-300">{condCard.card?.name}</span>
                          <span className="text-magic-muted">em campo</span>
                        </>
                      )}
                      <span className="text-magic-muted">→ {t.trigger_count}x →</span>
                      <span className="text-green-300">{catLabel(tgtCat || { parent_id: null, name: '?' })}</span>
                      {t.per_turn && <span className="text-amber-400">por turno</span>}
                      {isTgtRamp && t.same_turn !== null && t.same_turn !== undefined && (
                        <span className="text-[10px] px-1 py-0.5 rounded bg-slate-600 text-magic-muted">
                          {t.same_turn ? 'mesmo turno' : 'próximo turno'}
                        </span>
                      )}
                      {isTgtRamp && t.is_permanent !== null && t.is_permanent !== undefined && (
                        <span className={`text-[10px] px-1 py-0.5 rounded ${t.is_permanent ? 'bg-slate-600 text-magic-muted' : 'bg-amber-900 text-amber-200'}`}>
                          {t.is_permanent ? 'Perm' : 'Ritual'}
                        </span>
                      )}
                      <button onClick={() => removeTrigger(idx)} className="text-magic-muted hover:text-red-400 ml-auto">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <button onClick={handleSave} className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1 transition-colors">
              <Save className="w-3.5 h-3.5" /> Salvar Config
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function WhatIfComparison({ before, after }: { before?: any; after: any }) {
  const COLOR_BEFORE = '#64748b'
  const COLOR_AFTER = '#6366f1'
  const COLOR_BEFORE_2 = '#94a3b8'
  const COLOR_AFTER_2 = '#22d3ee'

  const delta = (a: number | undefined | null, b: number | undefined | null) => {
    const d = (a ?? 0) - (b ?? 0)
    if (Math.abs(d) < 0.01) return null
    return d
  }
  const fmtDelta = (d: number | null, suffix = '', pct = false, invertColor = false) => {
    if (d === null) return null
    const sign = d > 0 ? '+' : ''
    const val = pct ? `${(d * 100).toFixed(1)}%` : `${sign}${d.toFixed(2)}${suffix}`
    const isPositive = invertColor ? d < 0 : d > 0
    const isNegative = invertColor ? d > 0 : d < 0
    return { val, positive: isPositive, negative: isNegative }
  }

  const beforeTotalInt = (before?.interactions?.total_interaction_spells ?? 0) +
    (before?.interactions?.total_removal ?? 0) +
    (before?.interactions?.total_counterspells ?? 0)
  const afterTotalInt = (after.interactions?.total_interaction_spells ?? 0) +
    (after.interactions?.total_removal ?? 0) +
    (after.interactions?.total_counterspells ?? 0)
  const intDelta = delta(afterTotalInt, beforeTotalInt)

  // ── Mana comparison ──
  const beforeMana = before?.mana_ramp?.by_turn || {}
  const afterMana = after.mana_ramp?.by_turn || {}
  const allManaTurns = [...new Set([...Object.keys(beforeMana), ...Object.keys(afterMana)])]
    .map(Number).sort((a, b) => a - b).filter(t => t <= 15)

  const manaData = allManaTurns.map(t => {
    const tb = beforeMana[t] || {}
    const ta = afterMana[t] || {}
    return {
      turn: `T${t}`,
      'Antes — Terrenos': tb.mana_from_lands ?? 0,
      'Antes — Ramp': tb.total_ramp_mana ?? 0,
      'Depois — Terrenos': ta.mana_from_lands ?? 0,
      'Depois — Ramp': ta.total_ramp_mana ?? 0,
    }
  })

  const manaDeltaT5 = delta(
    (afterMana[5]?.total_expected_mana ?? 0),
    (beforeMana[5]?.total_expected_mana ?? 0),
  )
  const manaDeltaT7 = delta(
    (afterMana[7]?.total_expected_mana ?? 0),
    (beforeMana[7]?.total_expected_mana ?? 0),
  )

  // ── Goldfish comparison ──
  const beforeGold = (before?.goldfish?.turn_by_turn || []) as any[]
  const afterGold = (after.goldfish?.turn_by_turn || []) as any[]
  const allGoldTurns = [...new Set([...beforeGold.map((d: any) => d.turn), ...afterGold.map((d: any) => d.turn)])]
    .sort((a, b) => a - b).filter(t => t <= 15)

  const goldMapB = new Map(beforeGold.map((d: any) => [d.turn, d]))
  const goldMapA = new Map(afterGold.map((d: any) => [d.turn, d]))

  const goldData = allGoldTurns.map(t => ({
    turn: `T${t}`,
    'Antes — Mana': goldMapB.get(t)?.avg_max_mana ?? 0,
    'Depois — Mana': goldMapA.get(t)?.avg_max_mana ?? 0,
    'Antes — Mão': goldMapB.get(t)?.avg_cards_in_hand ?? 0,
    'Depois — Mão': goldMapA.get(t)?.avg_cards_in_hand ?? 0,
    'Depois — % Vazio': (goldMapA.get(t)?.prob_empty_hand ?? 0) * 100,
  }))

  const goldEmptyDelta = delta(
    after.goldfish?.probability_empty_by_turn_5,
    before?.goldfish?.probability_empty_by_turn_5,
  )

  // ── Category comparison ──
  const beforeCatTurn = before?.categories?.by_turn || {}
  const afterCatTurn = after.categories?.by_turn || {}
  const allCatTurns = [...new Set([...Object.keys(beforeCatTurn), ...Object.keys(afterCatTurn)])]
    .map(Number).sort((a, b) => a - b).filter(t => t <= 15)

  const catIdsBefore = new Set<number>()
  const catIdsAfter = new Set<number>()
  for (const td of Object.values(beforeCatTurn) as any[]) {
    for (const cid of Object.keys(td.categories || {})) catIdsBefore.add(Number(cid))
  }
  for (const td of Object.values(afterCatTurn) as any[]) {
    for (const cid of Object.keys(td.categories || {})) catIdsAfter.add(Number(cid))
  }
  const catMapB = new Map<number, any>()
  const catMapA = new Map<number, any>()
  for (const c of before?.categories?.categories || []) catMapB.set(c.id, c)
  for (const c of after.categories?.categories || []) catMapA.set(c.id, c)

  const allCatIds = [...new Set([...catIdsBefore, ...catIdsAfter])]
  const catCardsMap = new Map<number, number>()
  for (const id of allCatIds) {
    catCardsMap.set(id, Math.max(catMapB.get(id)?.cards_assigned || 0, catMapA.get(id)?.cards_assigned || 0))
  }
  const topCats = allCatIds
    .sort((a, b) => catCardsMap.get(b)! - catCardsMap.get(a)!)
    .slice(0, 8)
    .map(id => ({ id, name: (catMapA.get(id) || catMapB.get(id))?.name || `#${id}` }))

  const catChartData = allCatTurns.map(t => {
    const point: any = { turn: `T${t}` }
    for (const cat of topCats) {
      const bVal = (beforeCatTurn[t]?.categories?.[cat.id]?.prob_at_least_1 ?? 0) * 100
      const aVal = (afterCatTurn[t]?.categories?.[cat.id]?.prob_at_least_1 ?? 0) * 100
      point[`Antes — ${cat.name}`] = Math.round(bVal)
      point[`Depois — ${cat.name}`] = Math.round(aVal)
    }
    return point
  })

  // ── Interaction comparison ──
  const beforeInt = before?.interactions?.breakdown || {}
  const afterInt = after.interactions?.breakdown || {}
  const allIntTypes = [...new Set([...Object.keys(beforeInt), ...Object.keys(afterInt)])]
  const intData = allIntTypes
    .map(type => ({
      type: type.charAt(0).toUpperCase() + type.slice(1),
      Antes: beforeInt[type]?.total || 0,
      Depois: afterInt[type]?.total || 0,
    }))
    .filter(d => d.Antes > 0 || d.Depois > 0)
    .sort((a, b) => (b.Depois + b.Antes) - (a.Depois + a.Antes))

  const catColors = ['#6366f1', '#22d3ee', '#f59e0b', '#10b981', '#f43f5e', '#a78bfa', '#fb923c', '#34d399']

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium text-amber-300 flex items-center gap-2">
        <BarChart3 className="w-4 h-4" />
        Comparação: Antes vs Depois das Trocas
      </h4>

      {/* Delta summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Mana T5', delta: manaDeltaT5, fmt: fmtDelta(manaDeltaT5) },
          { label: 'Mana T7', delta: manaDeltaT7, fmt: fmtDelta(manaDeltaT7) },
          { label: 'P(vazio@T5)', delta: goldEmptyDelta, fmt: fmtDelta(goldEmptyDelta, '', true, true) },
          { label: 'Interações', delta: intDelta, fmt: fmtDelta(intDelta) },
        ].map((item, i) => (
          <div key={i} className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-[10px] text-magic-muted">{item.label}</div>
            {item.fmt ? (
              <div className={`text-sm font-semibold ${
                item.fmt.positive ? 'text-green-400' : item.fmt.negative ? 'text-red-400' : 'text-white'
              }`}>
                {item.fmt.val}
              </div>
            ) : (
              <div className="text-sm font-semibold text-white">-</div>
            )}
          </div>
        ))}
      </div>

      {/* Mana comparison chart */}
      {manaData.length > 0 && (
        <div className="bg-slate-800/50 rounded-lg p-4">
          <h5 className="text-xs font-medium text-slate-400 mb-3">Mana por Turno</h5>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={manaData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turn" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="Depois — Terrenos" stackId="a" stroke={COLOR_AFTER_2} fill={COLOR_AFTER_2} fillOpacity={0.5} strokeWidth={2} name="Depois — Terrenos" />
              <Area type="monotone" dataKey="Depois — Ramp" stackId="a" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.5} strokeWidth={2} name="Depois — Ramp" />
              <Area type="monotone" dataKey="Antes — Terrenos" stackId="b" stroke={COLOR_BEFORE_2} fill={COLOR_BEFORE_2} fillOpacity={0.15} strokeWidth={1.5} strokeDasharray="5 5" name="Antes — Terrenos" />
              <Area type="monotone" dataKey="Antes — Ramp" stackId="b" stroke={COLOR_BEFORE} fill={COLOR_BEFORE} fillOpacity={0.15} strokeWidth={1.5} strokeDasharray="5 5" name="Antes — Ramp" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Goldfish comparison chart */}
      {goldData.length > 0 && (
        <div className="bg-slate-800/50 rounded-lg p-4">
          <h5 className="text-xs font-medium text-slate-400 mb-3">Goldfish</h5>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={goldData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turn" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="left" type="monotone" dataKey="Depois — Mana" stroke={COLOR_AFTER} strokeWidth={2.5} dot={{ r: 2 }} name="Depois — Mana" />
              <Line yAxisId="left" type="monotone" dataKey="Antes — Mana" stroke={COLOR_BEFORE} strokeWidth={1.5} dot={{ r: 1.5 }} strokeDasharray="5 5" name="Antes — Mana" />
              <Line yAxisId="left" type="monotone" dataKey="Depois — Mão" stroke={COLOR_AFTER_2} strokeWidth={2.5} dot={{ r: 2 }} name="Depois — Mão" />
              <Line yAxisId="left" type="monotone" dataKey="Antes — Mão" stroke={COLOR_BEFORE_2} strokeWidth={1.5} dot={{ r: 1.5 }} strokeDasharray="5 5" name="Antes — Mão" />
              <Line yAxisId="right" type="monotone" dataKey="Depois — % Vazio" stroke="#f43f5e" strokeWidth={2} dot={{ r: 2 }} strokeDasharray="5 5" name="% mão vazia (depois)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Category comparison chart */}
      {catChartData.length > 0 && (
        <div className="bg-slate-800/50 rounded-lg p-4">
          <h5 className="text-xs font-medium text-slate-400 mb-3">Categorias (prob. ≥1 carta por turno)</h5>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={catChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turn" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} domain={[0, 100]} unit="%" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#e2e8f0' }}
                formatter={(v: number) => `${v}%`}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {topCats.map((cat, i) => (
                <Line key={`a-${cat.id}`} type="monotone" dataKey={`Depois — ${cat.name}`}
                  stroke={catColors[i % catColors.length]} strokeWidth={2.5} dot={{ r: 2 }} />
              ))}
              {topCats.map((cat, i) => (
                <Line key={`b-${cat.id}`} type="monotone" dataKey={`Antes — ${cat.name}`}
                  stroke={catColors[i % catColors.length]} strokeWidth={1.5} dot={{ r: 1.5 }}
                  strokeDasharray="5 5" opacity={0.6} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Interaction comparison chart */}
      {intData.length > 0 && (
        <div className="bg-slate-800/50 rounded-lg p-4">
          <h5 className="text-xs font-medium text-slate-400 mb-3">Interações</h5>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={intData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis dataKey="type" type="category" width={100} tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="Antes" fill={COLOR_BEFORE} radius={[0, 4, 4, 0]} barSize={12} />
              <Bar dataKey="Depois" fill={COLOR_AFTER} radius={[0, 4, 4, 0]} barSize={12} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
