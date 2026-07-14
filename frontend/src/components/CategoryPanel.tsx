import { useState, useEffect, Fragment, useMemo, useCallback } from 'react'
import { categories as api } from '../services/api'
import { Plus, Trash2, Tag, Zap, Link2, ArrowDown, Pencil, Check, X } from 'lucide-react'

function catLabel(c: any, allCats: any[]): string {
  if (c.parent_id) {
    const parent = allCats.find(p => p.id === c.parent_id)
    if (parent) return `${parent.name} › ${c.name}`
  }
  return c.name
}

interface Props {
  deckId: string
  cards: any[]
  poolCards?: any[]
  onTriggersChange?: () => void
}

export default function CategoryPanel({ deckId, cards, poolCards = [], onTriggersChange }: Props) {
  const [allCategories, setAllCategories] = useState<any[]>([])
  const [assignments, setAssignments] = useState<any[]>([])
  const [cardTriggers, setCardTriggers] = useState<any[]>([])
  const [limiters, setLimiters] = useState<any[]>([])
  const [containmentEdges, setContainmentEdges] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'categories' | 'assign' | 'triggers' | 'containment'>('categories')

  useEffect(() => {
    if (!deckId) return
    setLoading(true)
    Promise.all([
      api.list(),
      api.getAssignments(deckId),
      api.getCardTriggers(deckId),
      api.getLimiters(deckId),
      api.getContainment(),
    ]).then(([catRes, assnRes, ctRes, limRes, contRes]) => {
      setAllCategories(catRes.data)
      setAssignments(assnRes.data)
      setCardTriggers(ctRes.data)
      setLimiters(limRes.data)
      setContainmentEdges(contRes.data)
    }).finally(() => setLoading(false))
  }, [deckId])

  const refreshCategories = () => {
    api.list().then(r => setAllCategories(r.data))
  }

  const refreshAssignments = () => {
    api.getAssignments(deckId).then(r => setAssignments(r.data))
  }
  const refreshAssignAndLimiters = () => {
    Promise.all([
      api.getAssignments(deckId),
      api.getLimiters(deckId),
    ]).then(([assnRes, limRes]) => {
      setAssignments(assnRes.data)
      setLimiters(limRes.data)
    })
  }
  const refreshTriggers = () => {
    Promise.all([
      api.getCardTriggers(deckId),
      api.getLimiters(deckId),
    ]).then(([ctRes, limRes]) => {
      setCardTriggers(ctRes.data)
      setLimiters(limRes.data)
      onTriggersChange?.()
    })
  }

  const refreshContainment = () => {
    api.getContainment().then(r => setContainmentEdges(r.data))
  }

  if (loading) return <div className="text-magic-muted text-sm py-4">Carregando categorias...</div>

  const tabs = [
    { id: 'categories' as const, label: 'Categorias', icon: Tag },
    { id: 'assign' as const, label: 'Atribuir Cartas', icon: Zap },
    { id: 'triggers' as const, label: 'Triggers', icon: Link2 },
    { id: 'containment' as const, label: 'Contenção', icon: ArrowDown },
  ]

  return (
    <div className="space-y-4">
      <div className="flex gap-1 bg-slate-800 rounded-lg p-1 overflow-x-auto">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id ? 'bg-indigo-600 text-white' : 'text-magic-muted hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          )
        })}
      </div>

      {activeTab === 'categories' && (
        <CategoryManager categories={allCategories} onRefresh={refreshCategories} />
      )}
      {activeTab === 'assign' && (
        <AssignmentManager
          categories={allCategories}
          cards={cards}
          poolCards={poolCards}
          assignments={assignments}
          limiters={limiters}
          deckId={deckId}
          onRefresh={refreshAssignAndLimiters}
        />
      )}
      {activeTab === 'triggers' && (
        <TriggerManager
          categories={allCategories}
          assignments={assignments}
          cardTriggers={cardTriggers}
          limiters={limiters}
          deckId={deckId}
          onRefresh={refreshTriggers}
        />
      )}
      {activeTab === 'containment' && (
        <ContainmentManager
          categories={allCategories}
          edges={containmentEdges}
          onRefresh={refreshContainment}
        />
      )}
    </div>
  )
}

function CategoryManager({ categories, onRefresh }: { categories: any[], onRefresh: () => void }) {
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState('#6366f1')
  const [newParentId, setNewParentId] = useState<number | ''>('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editColor, setEditColor] = useState('#6366f1')
  const [error, setError] = useState('')

  const rootCategories = categories.filter(c => !c.parent_id)
  const getChildren = (parentId: number) => categories.filter(c => c.parent_id === parentId)

  const handleCreate = async () => {
    if (!newName.trim()) return
    setError('')
    try {
      await api.create({
        name: newName.trim(),
        color: newColor,
        parent_id: newParentId === '' ? null : Number(newParentId),
      })
      onRefresh()
      setNewName('')
      setNewParentId('')
    } catch (e: any) {
      setError(e.response?.data?.error || 'Erro ao criar')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(id)
      onRefresh()
    } catch (e: any) {
      setError(e.response?.data?.error || 'Erro ao deletar')
    }
  }

  const startEditing = (cat: any) => {
    setEditingId(cat.id)
    setEditName(cat.name)
    setEditColor(cat.color)
  }

  const cancelEditing = () => {
    setEditingId(null)
  }

  const saveEditing = async () => {
    if (!editName.trim() || editingId === null) return
    setError('')
    try {
      await api.update(editingId, { name: editName.trim(), color: editColor })
      setEditingId(null)
      onRefresh()
    } catch (e: any) {
      setError(e.response?.data?.error || 'Erro ao salvar')
    }
  }

  const renderCategory = (cat: any, depth: number = 0) => {
    const children = getChildren(cat.id)
    const isEditing = editingId === cat.id

    return (
      <div key={cat.id}>
        <div className="flex items-center justify-between px-3 py-2 bg-slate-800 rounded-lg"
          style={{ marginLeft: depth * 24 }}>
          {isEditing ? (
            <div className="flex items-center gap-2 flex-1">
              <input type="color" value={editColor} onChange={e => setEditColor(e.target.value)}
                className="w-8 h-8 rounded cursor-pointer bg-slate-700 border border-slate-600 shrink-0" />
              <input type="text" value={editName} onChange={e => setEditName(e.target.value)}
                className="input flex-1 min-w-0" />
              <button onClick={saveEditing} className="btn btn-primary btn-sm flex items-center gap-1">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button onClick={cancelEditing}
                className="btn btn-sm bg-slate-700 hover:bg-slate-600 text-magic-muted flex items-center gap-1">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: cat.color }} />
                <span className="font-medium">{cat.name}</span>
                <span className="text-xs text-magic-muted">{cat.config?.type || 'custom'}</span>
                {cat.is_default && <span className="text-[10px] text-magic-muted bg-slate-700 px-1.5 py-0.5 rounded">default</span>}
                {depth === 0 && children.length > 0 && (
                  <span className="text-[10px] text-indigo-300">{children.length} subcategorias</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => startEditing(cat)}
                  className="text-indigo-400 hover:text-indigo-300 transition-colors">
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                {!cat.is_default && (
                  <button onClick={() => handleDelete(cat.id)}
                    className="text-red-400 hover:text-red-300 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </>
          )}
        </div>
        {children.length > 0 && (
          <div className="mt-1 space-y-1">
            {children.map(child => renderCategory(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="font-semibold mb-4">Categorias Globais</h3>
      <div className="flex gap-2 mb-4 flex-wrap items-end">
        <input type="text" value={newName} onChange={e => setNewName(e.target.value)}
          placeholder="Nova categoria..." className="input flex-1 min-w-[150px]" />
        <input type="color" value={newColor} onChange={e => setNewColor(e.target.value)}
          className="w-10 h-10 rounded cursor-pointer bg-slate-700 border border-slate-600 shrink-0" />
        <select value={newParentId} onChange={e => setNewParentId(e.target.value === '' ? '' : Number(e.target.value))}
          className="input min-w-[140px]">
          <option value="">Sem parente</option>
          {rootCategories.map(cat => (
            <option key={cat.id} value={cat.id}>{cat.name}</option>
          ))}
        </select>
        <button onClick={handleCreate} className="btn btn-primary flex items-center gap-1">
          <Plus className="w-4 h-4" /> Criar
        </button>
      </div>
      {error && <p className="text-red-400 text-sm mb-2">{error}</p>}

      <div className="space-y-1">
        {rootCategories.map(cat => renderCategory(cat))}
        {categories.length === 0 && (
          <p className="text-sm text-magic-muted text-center py-4">Nenhuma categoria.</p>
        )}
      </div>
    </div>
  )
}

function AssignmentManager({ categories, cards, poolCards, assignments, limiters, deckId, onRefresh }: {
  categories: any[]; cards: any[]; poolCards: any[]; assignments: any[]; limiters: any[]; deckId: string; onRefresh: () => void
}) {
  const [selectedCard, setSelectedCard] = useState<number | ''>('')
  const [selectedCategory, setSelectedCategory] = useState<number | ''>('')
  const [multiplier, setMultiplier] = useState(1)
  const [manaAmount, setManaAmount] = useState<number | ''>('')
  const [sameTurn, setSameTurn] = useState(false)
  const [isPermanent, setIsPermanent] = useState(true)
  const [maxPerTurn, setMaxPerTurn] = useState<number | ''>('')
  const [waitForCategories, setWaitForCategories] = useState<number[]>([])
  const [limitCategoryId, setLimitCategoryId] = useState<number | ''>('')
  const [limitOnlySubsequent, setLimitOnlySubsequent] = useState(false)
  const [expandedLimiterFilter, setExpandedLimiterFilter] = useState<number | null>(null)

  const cat = categories.find(c => c.id === selectedCategory)
  const isRamp = cat?.config?.type === 'ramp'
  const isTutor = cat?.config?.type === 'tutor'

  const [tutoredCard, setTutoredCard] = useState<number | ''>('')

  const handleAssign = async () => {
    if (selectedCard === '' || selectedCategory === '') return
    await api.setAssignment(deckId, {
      card_id: Number(selectedCard),
      category_id: Number(selectedCategory),
      multiplier,
      mana_amount: isRamp ? (manaAmount === '' ? null : Number(manaAmount)) : null,
      same_turn: isRamp ? sameTurn : null,
      is_permanent: isRamp ? isPermanent : null,
      max_per_turn: maxPerTurn === '' ? null : Number(maxPerTurn),
      tutored_card_id: isTutor ? (tutoredCard === '' ? null : Number(tutoredCard)) : null,
      wait_for_category_ids: waitForCategories.length > 0 ? waitForCategories : undefined,
      limit_category_id: limitCategoryId === '' ? null : Number(limitCategoryId),
      limit_only_subsequent: limitCategoryId !== '' ? limitOnlySubsequent : undefined,
    })
    onRefresh()
    setSelectedCard('')
    setSelectedCategory('')
    setMultiplier(1)
    setManaAmount('')
    setSameTurn(false)
    setIsPermanent(true)
    setMaxPerTurn('')
    setTutoredCard('')
    setWaitForCategories([])
    setLimitCategoryId('')
    setLimitOnlySubsequent(false)
  }

  const handleRemove = async (assnId: number) => {
    await api.removeAssignment(deckId, assnId)
    onRefresh()
  }

  const childIdsOf = useMemo(() => {
    const map = new Map<number, number[]>()
    for (const c of categories) {
      if (c.parent_id != null) {
        const arr = map.get(c.parent_id) || []
        arr.push(c.id)
        map.set(c.parent_id, arr)
      }
    }
    return map
  }, [categories])

  const getDescendantIds = useCallback((catId: number): number[] => {
    const result = [catId]
    const children = childIdsOf.get(catId)
    if (children) {
      for (const child of children) {
        result.push(...getDescendantIds(child))
      }
    }
    return result
  }, [childIdsOf])

  const catNameById = useMemo(() => {
    const map = new Map<number, string>()
    for (const c of categories) map.set(c.id, c.name)
    return map
  }, [categories])

  type LimiterMatch = { limiter: any; sourceCategoryId: number; sourceCategoryName: string }

  const getRelevantLimiters = useCallback((categoryId: number): LimiterMatch[] => {
    const results: LimiterMatch[] = []
    for (const lim of limiters) {
      for (const srcId of (lim.source_category_ids || [])) {
        const descendants = getDescendantIds(srcId)
        if (descendants.includes(categoryId)) {
          results.push({ limiter: lim, sourceCategoryId: srcId, sourceCategoryName: catNameById.get(srcId) || '?' })
        }
      }
    }
    return results
  }, [limiters, getDescendantIds, catNameById])

  const getSourceAllCards = useCallback((sourceCategoryId: number): number[] => {
    const descendants = getDescendantIds(sourceCategoryId)
    return [...new Set(
      assignments.filter(a => descendants.includes(a.category_id)).map(a => a.card_id)
    )]
  }, [assignments, getDescendantIds])

  const isCardInFilter = (limiter: any, sourceCategoryId: number, cardId: number) => {
    const filter = limiter.source_card_filters?.[sourceCategoryId]
    if (!filter) return true
    return filter.includes(cardId)
  }

  const toggleLimiterFilter = async (limiter: any, sourceCategoryId: number, cardId: number) => {
    const filter = limiter.source_card_filters?.[sourceCategoryId] || null
    const allCards = getSourceAllCards(sourceCategoryId)
    let newFilter: number[] | null
    if (!filter) {
      newFilter = allCards.filter((id: number) => id !== cardId)
    } else if (filter.includes(cardId)) {
      const filtered: number[] = filter.filter((id: number) => id !== cardId)
      newFilter = filtered.length === 0 ? null : filtered
    } else {
      newFilter = [...filter, cardId]
      if (newFilter.length >= allCards.length) newFilter = null
    }
    await api.updateSourceFilter(deckId, limiter.id, sourceCategoryId, newFilter)
    onRefresh()
  }

  const selectedCardData = cards.find((c: any) => c.card_id === selectedCard)
    || poolCards.find((c: any) => c.card_id === selectedCard)
  const selectedCardImage = selectedCardData?.card?.image_uris?.normal || selectedCardData?.card?.image_uris?.small

  return (
    <div className="card">
      <h3 className="font-semibold mb-4">Atribuir Cartas a Categorias</h3>

      <div className="flex gap-6 mb-4">
        <div className="group relative shrink-0">
          {selectedCardImage ? (
            <img src={selectedCardImage} alt=""
              className="w-[146px] h-[204px] rounded-lg object-cover shadow-lg transition-transform duration-200 group-hover:scale-[1.8] group-hover:z-20 group-hover:shadow-2xl relative" />
          ) : (
            <div className="w-[146px] h-[204px] rounded-lg bg-slate-800 border-2 border-dashed border-slate-700 flex items-center justify-center text-sm text-magic-muted">
              ?
            </div>
          )}
        </div>
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 content-start">
          <select value={selectedCard} onChange={e => setSelectedCard(Number(e.target.value))}
            className="input">
            <option value="">Selecionar carta...</option>
            <optgroup label="Cartas do Deck">
              {cards.map((c: any, i: number) => (
                <option key={i} value={c.card_id}>{c.card?.name}</option>
              ))}
            </optgroup>
            {poolCards.length > 0 && (
              <optgroup label="Cartas do Pool (pendentes)">
                {poolCards.map((c: any, i: number) => (
                  <option key={`pool-${i}`} value={c.card_id}>{c.card?.name}</option>
                ))}
              </optgroup>
            )}
          </select>
          <select value={selectedCategory} onChange={e => setSelectedCategory(Number(e.target.value))}
            className="input">
            <option value="">Selecionar categoria...</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
            ))}
          </select>
          {isTutor ? (
            <select value={tutoredCard} onChange={e => setTutoredCard(Number(e.target.value))}
              className="input">
              <option value="">Selecionar carta tutoriada...</option>
              <optgroup label="Cartas do Deck">
                {cards.filter((c: any) => c.card_id !== selectedCard).map((c: any, i: number) => (
                  <option key={i} value={c.card_id}>{c.card?.name}</option>
                ))}
              </optgroup>
              {poolCards.length > 0 && (
                <optgroup label="Cartas do Pool (pendentes)">
                  {poolCards.filter((c: any) => c.card_id !== selectedCard).map((c: any, i: number) => (
                    <option key={`pool-${i}`} value={c.card_id}>{c.card?.name}</option>
                  ))}
                </optgroup>
              )}
            </select>
          ) : isRamp ? (
            <input type="number" value={manaAmount} min={0}
              onChange={e => setManaAmount(e.target.value === '' ? '' : Number(e.target.value))}
              placeholder="Mana gerada" className="input" />
          ) : (
            <input type="number" value={multiplier} min={0} step={0.5}
              onChange={e => setMultiplier(Number(e.target.value))}
              placeholder="Multiplicador" className="input" />
          )}
          <input type="number" value={maxPerTurn} min={0}
            onChange={e => setMaxPerTurn(e.target.value === '' ? '' : Number(e.target.value))}
            placeholder="Max/turno" className="input" />
          <button onClick={handleAssign} className="btn btn-primary self-end">Atribuir</button>
        </div>
      </div>

      {isRamp && (
        <div className="flex gap-3 mb-4 flex-wrap items-center">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={sameTurn} onChange={e => setSameTurn(e.target.checked)} />
            Mesmo turno
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isPermanent} onChange={e => setIsPermanent(e.target.checked)} />
            Permanente
          </label>
          {!isPermanent && <span className="text-xs text-amber-400">Ritual</span>}
        </div>
      )}

      <div className="mb-4">
        <label className="text-xs text-magic-muted">Esperar castar para</label>
        <div className="flex flex-wrap gap-1 mt-1">
          {waitForCategories.map(catId => {
            const cat = categories.find(c => c.id === catId)
            return (
              <span key={catId}
                className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 rounded text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat?.color }} />
                {catLabel(cat || {parent_id: null, name: String(catId)}, categories)}
                <button onClick={() => setWaitForCategories(waitForCategories.filter(id => id !== catId))}
                  className="text-magic-muted hover:text-white ml-1">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )
          })}
          <select value="" onChange={e => {
            const val = Number(e.target.value)
            if (val && !waitForCategories.includes(val)) {
              setWaitForCategories([...waitForCategories, val])
            }
            e.target.value = ''
          }} className="input text-xs py-1 min-w-[120px]">
            <option value="">+ Adicionar...</option>
            {categories.filter(c => !waitForCategories.includes(c.id)).map(cat => (
              <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
            ))}
          </select>
        </div>
        <p className="text-[10px] text-magic-muted mt-1">OR — a atribuição só produz eventos se qualquer uma destas categorias tiver carta em campo</p>
      </div>

      <div className="mb-4">
        <label className="text-xs text-magic-muted">Limitar eventos por categoria</label>
        <div className="flex flex-wrap items-center gap-2 mt-1">
          <select value={limitCategoryId} onChange={e => {
            setLimitCategoryId(e.target.value === '' ? '' : Number(e.target.value))
            if (e.target.value === '') setLimitOnlySubsequent(false)
          }} className="input text-xs py-1 min-w-[160px]">
            <option value="">Sem limite</option>
            {categories.filter(c => c.id !== selectedCategory).map(cat => (
              <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
            ))}
          </select>
          {limitCategoryId !== '' && (
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={limitOnlySubsequent}
                onChange={e => setLimitOnlySubsequent(e.target.checked)} />
              Apenas subsequentes
            </label>
          )}
        </div>
        <p className="text-[10px] text-magic-muted mt-1">Eventos deste card são limitados por: min(eventos do card, eventos da categoria fonte)</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-magic-muted border-b border-magic-border">
              <th className="py-2 px-2 w-12"></th>
              <th className="text-left py-2 px-2">Carta</th>
              <th className="text-left py-2 px-2">Categoria</th>
              <th className="text-right py-2 px-2">Mult</th>
              <th className="text-right py-2 px-2">Max/T</th>
              <th className="text-right py-2 px-2">Mana</th>
              <th className="text-center py-2 px-2">Turno</th>
              <th className="text-center py-2 px-2">Tipo</th>
              <th className="text-left py-2 px-2">Tutoria</th>
              <th className="text-left py-2 px-2">Limite</th>
              <th className="py-2 px-2"></th>
            </tr>
          </thead>
          <tbody>
            {assignments.map(a => {
              const isExpanded = expandedLimiterFilter === a.id
              const relLimiters = getRelevantLimiters(a.category_id)
              return (
                <Fragment key={a.id}>
                  <tr className="border-b border-magic-border">
                    <td className="py-1 px-2">
                      <div className="group relative inline-block">
                        {a.card_image_uris?.small ? (
                          <>
                            <img src={a.card_image_uris.small} alt=""
                              className="w-12 h-[68px] rounded object-cover shadow cursor-pointer" />
                            <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 hidden group-hover:block pointer-events-none">
                              <img src={a.card_image_uris.normal || a.card_image_uris.small} alt=""
                                className="h-[400px] w-auto rounded-xl shadow-2xl border-2 border-slate-600" />
                            </div>
                          </>
                        ) : (
                          <div className="w-12 h-[68px] rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] text-magic-muted">
                            N/A
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-2">{a.card_name}</td>
                    <td className="py-2 px-2">
                      <span className="inline-flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full" style={{
                          backgroundColor: categories.find(c => c.id === a.category_id)?.color
                        }} />
                        {catLabel(categories.find(c => c.id === a.category_id) || a, categories)}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right">{a.multiplier}</td>
                    <td className="py-2 px-2 text-right">{a.max_per_turn ?? '-'}</td>
                    <td className="py-2 px-2 text-right">{a.mana_amount ?? '-'}</td>
                    <td className="py-2 px-2 text-center">{a.same_turn ? 'Sim' : a.same_turn === false ? 'Não' : '-'}</td>
                    <td className="py-2 px-2 text-center">
                      {a.is_permanent ? 'Perm' : a.is_permanent === false ? 'Ritual' : '-'}
                    </td>
                    <td className="py-2 px-2 text-left text-sm">
                      {a.tutored_card_name || '-'}
                    </td>
                    <td className="py-2 px-2 text-left text-xs">
                      {a.limit_category_id ? (
                        <span className="inline-flex items-center gap-1">
                          <div className="w-2 h-2 rounded-full" style={{
                            backgroundColor: categories.find(c => c.id === a.limit_category_id)?.color
                          }} />
                          {catLabel(categories.find(c => c.id === a.limit_category_id) || {parent_id: null, name: String(a.limit_category_id)}, categories)}
                          {a.limit_only_subsequent && <span className="text-amber-400 ml-0.5">*</span>}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="py-2 px-2 text-right flex items-center gap-1 justify-end">
                      {limiters.length > 0 && (
                        <button onClick={() => setExpandedLimiterFilter(isExpanded ? null : a.id)}
                          className={`transition-colors ${isExpanded ? 'text-indigo-400' : 'text-magic-muted hover:text-indigo-400'}`}
                          title="Limitadores">
                          <Link2 className="w-4 h-4" />
                        </button>
                      )}
                      <button onClick={() => handleRemove(a.id)}
                        className="text-red-400 hover:text-red-300">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                       <td colSpan={11} className="px-4 py-2 bg-slate-900/50">
                        <div className="text-xs text-magic-muted mb-1">
                          Contribuição em limitadores:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {limiters.map(lim => {
                            const match = relLimiters.find(m => m.limiter.id === lim.id)
                            if (match) {
                              const active = isCardInFilter(match.limiter, match.sourceCategoryId, a.card_id)
                              return (
                                <button key={`${lim.id}-${match.sourceCategoryId}`}
                                  onClick={() => toggleLimiterFilter(match.limiter, match.sourceCategoryId, a.card_id)}
                                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${
                                    active
                                      ? 'bg-indigo-900/50 text-indigo-300 border border-indigo-700'
                                      : 'bg-slate-800 text-magic-muted border border-slate-700 line-through'
                                  }`}>
                                  <div className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-green-400' : 'bg-red-400'}`} />
                                  {match.sourceCategoryName}
                                  {' → '}
                                  {lim.target_category_name || '?'}
                                  <span className="text-[10px] opacity-60">({lim.trigger_count}x)</span>
                                </button>
                              )
                            }
                            return (
                              <span key={lim.id}
                                className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-slate-800/50 text-magic-muted/50 border border-slate-800">
                                {lim.source_category_names?.join(', ') || '?'}
                                {' → '}
                                {lim.target_category_name || '?'}
                                <span className="text-[10px]">({lim.trigger_count}x)</span>
                                <span className="text-[10px] italic">não é fonte</span>
                              </span>
                            )
                          })}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PerTurnEditor({ value, onChange }: { value: (number | null)[] | null; onChange: (v: (number | null)[]) => void }) {
  const vals = value || Array(10).fill(null)
  return (
    <details className="mt-2">
      <summary className="text-xs text-magic-muted cursor-pointer hover:text-white">
        Multiplicador por turno (opcional)
      </summary>
      <div className="grid grid-cols-10 gap-1 mt-2">
        {vals.map((v, i) => (
          <div key={i} className="flex flex-col items-center">
            <span className="text-[10px] text-magic-muted">T{i + 1}</span>
            <input type="number"
              value={v ?? ''}
              onChange={e => {
                const next = [...vals]
                next[i] = e.target.value === '' ? null : Number(e.target.value)
                onChange(next)
              }}
              className="input w-full text-xs text-center" placeholder="-" />
          </div>
        ))}
      </div>
      <p className="text-[10px] text-magic-muted mt-1">-1 = usa o valor fixo (ilimitado)</p>
    </details>
  )
}

function TriggerManager({ categories, assignments, cardTriggers, limiters, deckId, onRefresh }: {
  categories: any[]; assignments: any[]; cardTriggers: any[];
  limiters: any[]; deckId: string; onRefresh: () => void
}) {
  const [sourceAssignment, setSourceAssignment] = useState<number | ''>('')
  const [targetCategory, setTargetCategory] = useState<number | ''>('')
  const [triggerCount, setTriggerCount] = useState(1)
  const [perTurn, setPerTurn] = useState<(number | null)[] | null>(null)

  const [limTarget, setLimTarget] = useState<number | ''>('')
  const [limLogic, setLimLogic] = useState<'OR' | 'AND'>('OR')
  const [limSources, setLimSources] = useState<number[]>([])
  const [limCount, setLimCount] = useState(1)
  const [limAccumulate, setLimAccumulate] = useState(false)

  const handleCreateCardTrigger = async () => {
    if (sourceAssignment === '' || targetCategory === '') return
    await api.setCardTrigger(deckId, {
      source_assignment_id: Number(sourceAssignment),
      target_category_id: Number(targetCategory),
      trigger_count: triggerCount,
      per_turn: perTurn?.some(v => v !== null) ? perTurn : null,
    })
    onRefresh()
    setSourceAssignment('')
    setTargetCategory('')
    setTriggerCount(1)
    setPerTurn(null)
  }

  const handleRemoveCardTrigger = async (id: number) => {
    await api.removeCardTrigger(deckId, id)
    onRefresh()
  }

  const handleCreateLimiter = async () => {
    if (limTarget === '' || limSources.length === 0) return
    await api.setLimiter(deckId, {
      target_category_id: Number(limTarget),
      logic: limLogic,
      source_category_ids: limSources,
      trigger_count: limCount,
      accumulate: limAccumulate,
    })
    onRefresh()
    setLimTarget('')
    setLimSources([])
    setLimCount(1)
    setLimAccumulate(false)
  }

  const handleRemoveLimiter = async (id: number) => {
    await api.removeLimiter(deckId, id)
    onRefresh()
  }

  const addLimSource = (catId: number) => {
    if (!limSources.includes(catId)) {
      setLimSources([...limSources, catId])
    }
  }

  const removeLimSource = (catId: number) => {
    setLimSources(limSources.filter(id => id !== catId))
  }

  return (
    <div className="space-y-6">
      {/* Card-level triggers */}
      <div className="card">
        <h3 className="font-semibold mb-4">Triggers por Carta</h3>
        <p className="text-xs text-magic-muted mb-4">
          Quando uma carta específica (na categoria X) é jogada, ela gera N eventos de outra categoria.
        </p>
        <div className="flex gap-3 mb-4 flex-wrap items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-magic-muted">Fonte (carta + categoria)</label>
            <select value={sourceAssignment} onChange={e => setSourceAssignment(Number(e.target.value))}
              className="input w-full mt-1">
              <option value="">Selecionar...</option>
              {assignments.map(a => (
                <option key={a.id} value={a.id}>
                  {a.card_name} — {catLabel(categories.find(c => c.id === a.category_id) || a, categories)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center text-magic-muted text-lg self-center pt-4">→</div>
          <div className="flex-1 min-w-[150px]">
            <label className="text-xs text-magic-muted">Alvo (categoria)</label>
            <select value={targetCategory} onChange={e => setTargetCategory(Number(e.target.value))}
              className="input w-full mt-1">
              <option value="">Selecionar...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
              ))}
            </select>
          </div>
          <div className="w-20">
            <label className="text-xs text-magic-muted">Eventos</label>
            <input type="number" value={triggerCount} min={1}
              onChange={e => setTriggerCount(Number(e.target.value))}
              className="input w-full mt-1" />
          </div>
          <button onClick={handleCreateCardTrigger} className="btn btn-primary flex items-center gap-1 pt-4">
            <Plus className="w-4 h-4" /> Adicionar
          </button>
        </div>

        <PerTurnEditor value={perTurn} onChange={setPerTurn} />

        <div className="space-y-2 mt-4">
          {cardTriggers.map(ct => {
            const tgtCat = categories.find(c => c.id === ct.target_category_id)
            const hasPerTurn = ct.per_turn && ct.per_turn.some((v: number | null) => v !== null)
            return (
              <div key={ct.id} className="flex items-center justify-between px-3 py-2 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-medium text-indigo-300">{ct.card_name}</span>
                  <span className="text-xs text-magic-muted">({catLabel(categories.find(c => c.id === ct.source_category_id) || {parent_id: null, name: ct.source_category_name}, categories)})</span>
                  <span className="text-magic-muted">→ {ct.trigger_count}x →</span>
                  <span className="font-medium text-green-300">{catLabel(tgtCat || {parent_id: null, name: ct.target_category_name}, categories)}</span>
                  {hasPerTurn && <span className="text-[10px] text-amber-400">por turno</span>}
                </div>
                <button onClick={() => handleRemoveCardTrigger(ct.id)}
                  className="text-red-400 hover:text-red-300">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )
          })}
          {cardTriggers.length === 0 && (
            <p className="text-sm text-magic-muted text-center py-4">Nenhum trigger por carta.</p>
          )}
        </div>
      </div>

      {/* Event Limiters */}
      <div className="card">
        <h3 className="font-semibold mb-4">Limitadores de Eventos</h3>
        <p className="text-xs text-magic-muted mb-4">
          Consome de múltiplas categorias fonte com lógica AND/OR para produzir eventos no alvo.
        </p>
        <div className="flex gap-3 mb-4 flex-wrap items-end">
          <div className="flex-1 min-w-[150px]">
            <label className="text-xs text-magic-muted">Alvo (produz)</label>
            <select value={limTarget} onChange={e => setLimTarget(Number(e.target.value))}
              className="input w-full mt-1">
              <option value="">Selecionar...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center pt-4">
            <button onClick={() => setLimLogic(limLogic === 'OR' ? 'AND' : 'OR')}
              className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
                limLogic === 'OR'
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-emerald-600 border-emerald-500 text-white'
              }`}>
              {limLogic}
            </button>
          </div>
          <div className="w-20">
            <label className="text-xs text-magic-muted">Por unidade</label>
            <input type="number" value={limCount} min={1}
              onChange={e => setLimCount(Number(e.target.value))}
              className="input w-full mt-1" />
          </div>
          <div className="flex items-center pt-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={limAccumulate}
                onChange={e => setLimAccumulate(e.target.checked)} />
              <span className="text-xs text-magic-muted">Acumular</span>
            </label>
          </div>
          <button onClick={handleCreateLimiter} className="btn btn-primary flex items-center gap-1 pt-4">
            <Plus className="w-4 h-4" /> Adicionar
          </button>
        </div>

        {/* Source categories multi-select */}
        <div className="mb-4">
          <label className="text-xs text-magic-muted">Fontes (consome de)</label>
          <div className="flex flex-wrap gap-1 mt-1">
            {limSources.map(catId => {
              const cat = categories.find(c => c.id === catId)
              return (
                <span key={catId}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 rounded text-xs">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat?.color }} />
                  {catLabel(cat || {parent_id: null, name: String(catId)}, categories)}
                  <button onClick={() => removeLimSource(catId)}
                    className="text-magic-muted hover:text-white ml-1">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )
            })}
            <select value="" onChange={e => { addLimSource(Number(e.target.value)); e.target.value = '' }}
              className="input text-xs py-1 min-w-[120px]">
              <option value="">+ Adicionar...</option>
              {categories.filter(c => !limSources.includes(c.id)).map(cat => (
                <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-2">
          {limiters.map(lim => {
            const tgtCat = categories.find(c => c.id === lim.target_category_id)
            const hasCardFilters = lim.source_card_filters && Object.keys(lim.source_card_filters).length > 0
            return (
              <div key={lim.id} className="px-3 py-2 bg-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-sm flex-wrap">
                    {(lim.source_category_names || []).map((name: string, i: number) => {
                      const srcId = lim.source_category_ids[i]
                      const filter = lim.source_card_filters?.[srcId]
                      const filterCount = filter?.length || 0
                      return (
                        <span key={i}>
                          <span className="font-medium text-indigo-300">{name}</span>
                          {filterCount > 0 && (
                            <span className="text-[10px] text-amber-400 ml-1">({filterCount} cards)</span>
                          )}
                          {i < lim.source_category_names.length - 1 && (
                            <span className="text-magic-muted mx-1">{lim.logic}</span>
                          )}
                        </span>
                      )
                    })}
                    <span className="text-magic-muted">→ {lim.trigger_count}x →</span>
                    <span className="font-medium text-green-300">
                      {catLabel(tgtCat || {parent_id: null, name: lim.target_category_name || String(lim.target_category_id)}, categories)}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-magic-muted">{lim.logic}</span>
                    {lim.accumulate && <span className="text-[10px] text-amber-400">acumula</span>}
                  </div>
                  <button onClick={() => handleRemoveLimiter(lim.id)}
                    className="text-red-400 hover:text-red-300">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                {hasCardFilters && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {Object.entries(lim.source_card_filters).map(([catId, cardIds]) => {
                      const cat = categories.find(c => c.id === Number(catId))
                      return (
                        <span key={catId} className="text-[10px] text-magic-muted">
                          {cat?.name}: {(cardIds as number[]).length} cards filtrados
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
          {limiters.length === 0 && (
            <p className="text-sm text-magic-muted text-center py-4">Nenhum limitador de eventos.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function ContainmentManager({ categories, edges, onRefresh }: {
  categories: any[]; edges: any[]; onRefresh: () => void
}) {
  const [containerId, setContainerId] = useState<number | ''>('')
  const [containedIds, setContainedIds] = useState<number[]>([])
  const [mode, setMode] = useState<string>('subcategoria')
  const [error, setError] = useState('')

  const addContained = (catId: number) => {
    if (catId && !containedIds.includes(catId)) {
      setContainedIds([...containedIds, catId])
    }
  }

  const removeContained = (catId: number) => {
    setContainedIds(containedIds.filter(id => id !== catId))
  }

  const handleAdd = async () => {
    if (containerId === '' || containedIds.length === 0) return
    setError('')
    try {
      for (const cid of containedIds) {
        await api.setContainment({
          container_category_id: Number(containerId),
          contained_category_id: cid,
          mode,
        })
      }
      onRefresh()
      setContainerId('')
      setContainedIds([])
      setMode('subcategoria')
    } catch (e: any) {
      setError(e.response?.data?.error || 'Erro ao adicionar contenção')
    }
  }

  const handleRemove = async (id: number) => {
    await api.removeContainment(id)
    onRefresh()
  }

  return (
    <div className="card">
      <h3 className="font-semibold mb-2">Contenção entre Categorias</h3>
      <p className="text-xs text-magic-muted mb-4">
        Define quais categorias contêm outras. Categorias pai automaticamente contêm suas subcategorias.
        A contenção propaga para: rollup, wait_for, limitadores, max_per_turn e acumulação.
      </p>

      <div className="flex gap-3 mb-4 flex-wrap items-end">
        <div className="flex-1 min-w-[180px]">
          <label className="text-xs text-magic-muted">Contém (container)</label>
          <select value={containerId} onChange={e => setContainerId(Number(e.target.value))}
            className="input w-full mt-1">
            <option value="">Selecionar...</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-magic-muted">Categorias contidas</label>
          <div className="flex flex-wrap gap-1 mt-1">
            {containedIds.map(catId => {
              const cat = categories.find(c => c.id === catId)
              return (
                <span key={catId}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 rounded text-xs">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat?.color }} />
                  {catLabel(cat || {parent_id: null, name: String(catId)}, categories)}
                  <button onClick={() => removeContained(catId)}
                    className="text-magic-muted hover:text-white ml-1">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )
            })}
            <select value="" onChange={e => { addContained(Number(e.target.value)); e.target.value = '' }}
              className="input text-xs py-1 min-w-[120px]">
              <option value="">+ Adicionar...</option>
              {categories.filter(c => !containedIds.includes(c.id)).map(cat => (
                <option key={cat.id} value={cat.id}>{catLabel(cat, categories)}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="min-w-[140px]">
          <label className="text-xs text-magic-muted">Modo</label>
          <select value={mode} onChange={e => setMode(e.target.value)}
            className="input w-full mt-1 text-xs">
            <option value="subcategoria">Subcategoria (1/n)</option>
            <option value="ao_mesmo_tempo">Ao mesmo tempo (1:1)</option>
          </select>
        </div>
        <button onClick={handleAdd} className="btn btn-primary flex items-center gap-1 pt-4">
          <Plus className="w-4 h-4" /> Adicionar
        </button>
      </div>

      {error && <p className="text-red-400 text-sm mb-2">{error}</p>}

      <div className="space-y-2">
        {edges.map(edge => (
          <div key={edge.id} className="flex items-center justify-between px-3 py-2 bg-slate-800 rounded-lg">
            <div className="flex items-center gap-3 text-sm">
              <span className="font-medium text-indigo-300">{edge.container_category_name}</span>
              <span className="text-magic-muted">contém</span>
              <span className="font-medium text-green-300">{edge.contained_category_name}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                edge.mode === 'ao_mesmo_tempo'
                  ? 'bg-amber-900 text-amber-200'
                  : 'bg-slate-600 text-slate-300'
              }`}>
                {edge.mode === 'ao_mesmo_tempo' ? '1:1' : '1/n'}
              </span>
            </div>
            <button onClick={() => handleRemove(edge.id)}
              className="text-red-400 hover:text-red-300">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
        {edges.length === 0 && (
          <p className="text-sm text-magic-muted text-center py-4">Nenhuma relação de contenção definida.</p>
        )}
      </div>
    </div>
  )
}
