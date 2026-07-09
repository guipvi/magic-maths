import { useState, useEffect } from 'react'
import { categories as api } from '../services/api'
import { Plus, Trash2, Tag, Zap, Link2 } from 'lucide-react'

interface Props {
  deckId: string
  cards: any[]
  onTriggersChange?: () => void
}

export default function CategoryPanel({ deckId, cards, onTriggersChange }: Props) {
  const [allCategories, setAllCategories] = useState<any[]>([])
  const [assignments, setAssignments] = useState<any[]>([])
  const [triggers, setTriggers] = useState<any[]>([])
  const [cardTriggers, setCardTriggers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'categories' | 'assign' | 'triggers'>('categories')

  useEffect(() => {
    if (!deckId) return
    setLoading(true)
    Promise.all([
      api.list(),
      api.getAssignments(deckId),
      api.getTriggers(deckId),
      api.getCardTriggers(deckId),
    ]).then(([catRes, assnRes, trigRes, ctRes]) => {
      setAllCategories(catRes.data)
      setAssignments(assnRes.data)
      setTriggers(trigRes.data)
      setCardTriggers(ctRes.data)
    }).finally(() => setLoading(false))
  }, [deckId])

  const refreshAssignments = () => {
    api.getAssignments(deckId).then(r => setAssignments(r.data))
  }
  const refreshTriggers = () => {
    Promise.all([
      api.getTriggers(deckId),
      api.getCardTriggers(deckId),
    ]).then(([trigRes, ctRes]) => {
      setTriggers(trigRes.data)
      setCardTriggers(ctRes.data)
      onTriggersChange?.()
    })
  }

  if (loading) return <div className="text-magic-muted text-sm py-4">Carregando categorias...</div>

  const tabs = [
    { id: 'categories' as const, label: 'Categorias', icon: Tag },
    { id: 'assign' as const, label: 'Atribuir Cartas', icon: Zap },
    { id: 'triggers' as const, label: 'Triggers', icon: Link2 },
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
        <CategoryManager categories={allCategories} setCategories={setAllCategories} />
      )}
      {activeTab === 'assign' && (
        <AssignmentManager
          categories={allCategories}
          cards={cards}
          assignments={assignments}
          deckId={deckId}
          onRefresh={refreshAssignments}
        />
      )}
      {activeTab === 'triggers' && (
        <TriggerManager
          categories={allCategories}
          assignments={assignments}
          triggers={triggers}
          cardTriggers={cardTriggers}
          deckId={deckId}
          onRefresh={refreshTriggers}
        />
      )}
    </div>
  )
}

function CategoryManager({ categories, setCategories }: { categories: any[], setCategories: (c: any[]) => void }) {
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState('#6366f1')

  const handleCreate = async () => {
    if (!newName.trim()) return
    const res = await api.create({ name: newName.trim(), color: newColor })
    setCategories([...categories, res.data])
    setNewName('')
  }

  const handleDelete = async (id: number) => {
    await api.delete(id)
    setCategories(categories.filter(c => c.id !== id))
  }

  return (
    <div className="card">
      <h3 className="font-semibold mb-4">Categorias Globais</h3>
      <div className="flex gap-2 mb-4">
        <input type="text" value={newName} onChange={e => setNewName(e.target.value)}
          placeholder="Nova categoria..." className="input flex-1" />
        <input type="color" value={newColor} onChange={e => setNewColor(e.target.value)}
          className="w-10 h-10 rounded cursor-pointer bg-slate-700 border border-slate-600" />
        <button onClick={handleCreate} className="btn btn-primary flex items-center gap-1">
          <Plus className="w-4 h-4" /> Criar
        </button>
      </div>
      <div className="space-y-2">
        {categories.map(cat => (
          <div key={cat.id} className="flex items-center justify-between px-3 py-2 bg-slate-800 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 rounded-full" style={{ backgroundColor: cat.color }} />
              <span className="font-medium">{cat.name}</span>
              <span className="text-xs text-magic-muted">{cat.config?.type || 'custom'}</span>
              {cat.is_default && <span className="text-[10px] text-magic-muted bg-slate-700 px-1.5 py-0.5 rounded">default</span>}
            </div>
            {!cat.is_default && (
              <button onClick={() => handleDelete(cat.id)}
                className="text-red-400 hover:text-red-300 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function AssignmentManager({ categories, cards, assignments, deckId, onRefresh }: {
  categories: any[]; cards: any[]; assignments: any[]; deckId: string; onRefresh: () => void
}) {
  const [selectedCard, setSelectedCard] = useState<number | ''>('')
  const [selectedCategory, setSelectedCategory] = useState<number | ''>('')
  const [multiplier, setMultiplier] = useState(1)
  const [manaAmount, setManaAmount] = useState<number | ''>('')
  const [sameTurn, setSameTurn] = useState(false)
  const [isPermanent, setIsPermanent] = useState(true)
  const [maxPerTurn, setMaxPerTurn] = useState<number | ''>('')

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
  }

  const handleRemove = async (assnId: number) => {
    await api.removeAssignment(deckId, assnId)
    onRefresh()
  }

  const selectedCardData = cards.find((c: any) => c.card_id === selectedCard)
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
            {cards.map((c: any, i: number) => (
              <option key={i} value={c.card_id}>{c.card?.name}</option>
            ))}
          </select>
          <select value={selectedCategory} onChange={e => setSelectedCategory(Number(e.target.value))}
            className="input">
            <option value="">Selecionar categoria...</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          {isTutor ? (
            <select value={tutoredCard} onChange={e => setTutoredCard(Number(e.target.value))}
              className="input">
              <option value="">Selecionar carta tutoriada...</option>
              {cards.filter((c: any) => c.card_id !== selectedCard).map((c: any, i: number) => (
                <option key={i} value={c.card_id}>{c.card?.name}</option>
              ))}
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
              <th className="py-2 px-2"></th>
            </tr>
          </thead>
          <tbody>
            {assignments.map(a => (
              <tr key={a.id} className="border-b border-magic-border">
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
                    {a.category_name}
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
                <td className="py-2 px-2 text-right">
                  <button onClick={() => handleRemove(a.id)}
                    className="text-red-400 hover:text-red-300">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
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

function TriggerManager({ categories, assignments, triggers, cardTriggers, deckId, onRefresh }: {
  categories: any[]; assignments: any[]; triggers: any[]; cardTriggers: any[];
  deckId: string; onRefresh: () => void
}) {
  const [sourceAssignment, setSourceAssignment] = useState<number | ''>('')
  const [targetCategory, setTargetCategory] = useState<number | ''>('')
  const [triggerCount, setTriggerCount] = useState(1)
  const [perTurn, setPerTurn] = useState<(number | null)[] | null>(null)

  const [catSource, setCatSource] = useState<number | ''>('')
  const [catTarget, setCatTarget] = useState<number | ''>('')
  const [catCount, setCatCount] = useState(1)
  const [catAccumulate, setCatAccumulate] = useState(false)

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

  const handleCreateCatTrigger = async () => {
    if (catSource === '' || catTarget === '') return
    await api.setTrigger(deckId, {
      source_category_id: Number(catSource),
      target_category_id: Number(catTarget),
      trigger_count: catCount,
      accumulate: catAccumulate,
    })
    onRefresh()
    setCatSource('')
    setCatTarget('')
    setCatCount(1)
    setCatAccumulate(false)
  }

  const handleRemoveCatTrigger = async (id: number) => {
    await api.removeTrigger(deckId, id)
    onRefresh()
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
                  {a.card_name} — {a.category_name}
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
                <option key={cat.id} value={cat.id}>{cat.name}</option>
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
                  <span className="text-xs text-magic-muted">({ct.source_category_name})</span>
                  <span className="text-magic-muted">→ {ct.trigger_count}x →</span>
                  <span className="font-medium text-green-300">{tgtCat?.name || ct.target_category_name}</span>
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

      {/* Category-level triggers */}
      <div className="card">
        <h3 className="font-semibold mb-4">Triggers entre Categorias</h3>
        <p className="text-xs text-magic-muted mb-4">
          Consome eventos da fonte e produz eventos no alvo. Cada unidade consumida gera N eventos no alvo.
        </p>
        <div className="flex gap-3 mb-4 flex-wrap items-end">
          <div className="flex-1 min-w-[150px]">
            <label className="text-xs text-magic-muted">Fonte (consome)</label>
            <select value={catSource} onChange={e => setCatSource(Number(e.target.value))}
              className="input w-full mt-1">
              <option value="">Selecionar...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center text-magic-muted text-lg self-center pt-4">→</div>
          <div className="flex-1 min-w-[150px]">
            <label className="text-xs text-magic-muted">Alvo (produz)</label>
            <select value={catTarget} onChange={e => setCatTarget(Number(e.target.value))}
              className="input w-full mt-1">
              <option value="">Selecionar...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
          <div className="w-20">
            <label className="text-xs text-magic-muted">Por unidade</label>
            <input type="number" value={catCount} min={1}
              onChange={e => setCatCount(Number(e.target.value))}
              className="input w-full mt-1" />
          </div>
          <div className="flex items-center pt-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={catAccumulate}
                onChange={e => setCatAccumulate(e.target.checked)} />
              <span className="text-xs text-magic-muted">Acumular</span>
            </label>
          </div>
          <button onClick={handleCreateCatTrigger} className="btn btn-primary flex items-center gap-1 pt-4">
            <Plus className="w-4 h-4" /> Adicionar
          </button>
        </div>

        <div className="space-y-2">
          {triggers.map(t => {
            const srcCat = categories.find(c => c.id === t.source_category_id)
            const tgtCat = categories.find(c => c.id === t.target_category_id)
            return (
              <div key={t.id} className="flex items-center justify-between px-3 py-2 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-medium text-indigo-300">{srcCat?.name || t.source_category_id}</span>
                  <span className="text-magic-muted">→ {t.trigger_count}x →</span>
                  <span className="font-medium text-green-300">{tgtCat?.name || t.target_category_id}</span>
                  {t.accumulate && <span className="text-[10px] text-amber-400">acumula</span>}
                </div>
                <button onClick={() => handleRemoveCatTrigger(t.id)}
                  className="text-red-400 hover:text-red-300">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )
          })}
          {triggers.length === 0 && (
            <p className="text-sm text-magic-muted text-center py-4">Nenhum trigger entre categorias.</p>
          )}
        </div>
      </div>
    </div>
  )
}
