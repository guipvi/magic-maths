import { useState, useEffect } from 'react'
import { commander as api, categories as catApi } from '../services/api'
import { Crown, Save, Trash2, Plus, GripVertical } from 'lucide-react'
import CommanderConditionBuilder from './CommanderConditionBuilder'

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
  commanderAnalysis: any
}

export default function CommanderConfig({ deckId, cards, commanderAnalysis }: Props) {
  const [config, setConfig] = useState<any | null>(null)
  const [selectedCardId, setSelectedCardId] = useState<number | ''>('')
  const [manaLeftOver, setManaLeftOver] = useState(0)
  const [requirements, setRequirements] = useState<{ category_id: number; count: number }[]>([])
  const [conditionGroups, setConditionGroups] = useState<any[]>([])
  const [allCategories, setAllCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [useAdvancedConditions, setUseAdvancedConditions] = useState(false)

  useEffect(() => {
    if (!deckId) return
    setLoading(true)
    Promise.all([
      api.getConfig(deckId),
      catApi.list(),
    ]).then(([cfgRes, catRes]) => {
      setAllCategories(catRes.data)
      const cfg = cfgRes.data.config
      if (cfg) {
        setConfig(cfg)
        setSelectedCardId(cfg.card_id)
        setManaLeftOver(cfg.mana_left_over || 0)
        setRequirements(cfg.min_category_requirements || [])
        setConditionGroups(cfg.condition_groups || [])
        setUseAdvancedConditions((cfg.condition_groups || []).length > 0)
      }
    }).finally(() => setLoading(false))
  }, [deckId])

  const handleSave = async () => {
    if (selectedCardId === '') return
    setSaving(true)
    try {
      const data = {
        card_id: Number(selectedCardId),
        mana_left_over: manaLeftOver,
        min_category_requirements: useAdvancedConditions ? [] : requirements,
        condition_groups: useAdvancedConditions ? conditionGroups : [],
      }
      const res = await api.saveConfig(deckId, data)
      setConfig(res.data.config)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    await api.deleteConfig(deckId)
    setConfig(null)
    setSelectedCardId('')
    setManaLeftOver(0)
    setRequirements([])
  }

  const addRequirement = () => {
    setRequirements([...requirements, { category_id: 0, count: 1 }])
  }

  const updateRequirement = (index: number, field: 'category_id' | 'count', value: number) => {
    const next = [...requirements]
    next[index] = { ...next[index], [field]: value }
    setRequirements(next)
  }

  const removeRequirement = (index: number) => {
    setRequirements(requirements.filter((_, i) => i !== index))
  }

  const commanderCards = cards.filter((c: any) => c.is_commander || c.card?.type_line?.includes('Legendary'))

  if (loading) {
    return <div className="text-magic-muted text-sm py-4">Carregando...</div>
  }

  return (
    <div className="card space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <Crown className="w-5 h-5 text-amber-400" />
          Configuração do Commander
        </h3>
        {config && (
          <button onClick={handleDelete} className="text-red-400 hover:text-red-300 text-sm flex items-center gap-1">
            <Trash2 className="w-4 h-4" /> Remover
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">Card Commander</label>
          <select
            className="input"
            value={selectedCardId}
            onChange={e => setSelectedCardId(Number(e.target.value))}
          >
            <option value="">Selecionar commander...</option>
            {cards.map((c: any, i: number) => (
              <option key={i} value={c.card_id}>
                {c.card?.name} {c.is_commander ? '(commander)' : ''}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Mana para deixar disponível ({'\u00e0'} vontade)</label>
          <input
            type="number"
            min={0}
            max={20}
            className="input"
            value={manaLeftOver}
            onChange={e => setManaLeftOver(Number(e.target.value))}
          />
          <p className="text-xs text-magic-muted mt-1">
            Mana que quer manter disponível apó;s conjurar o commander (ex: 2 para interaç;ão)
          </p>
        </div>
      </div>

      {/* Mode Toggle */}
      <div className="flex items-center gap-4 bg-slate-800 rounded-lg p-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={useAdvancedConditions}
            onChange={e => setUseAdvancedConditions(e.target.checked)}
            className="w-4 h-4"
          />
          <span className="text-sm font-medium">Usar condições avançadas (E/OU)</span>
        </label>
        <p className="text-xs text-magic-muted">
          {useAdvancedConditions
            ? 'Modo avançado: combine múltiplas condições com lógica E/OU'
            : 'Modo simples: requisitos básicos de categorias'}
        </p>
      </div>

      {useAdvancedConditions ? (
        <CommanderConditionBuilder
          conditionGroups={conditionGroups}
          onUpdate={setConditionGroups}
          allCategories={allCategories}
        />
      ) : (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="label mb-0">Requisitos mínimos de categorias</label>
            <button onClick={addRequirement} className="btn btn-primary text-xs flex items-center gap-1 py-1">
              <Plus className="w-3 h-3" /> Adicionar
            </button>
          </div>
          <p className="text-xs text-magic-muted mb-3">
            Eventos acumulados mínimos em categorias antes de conjurar o commander
          </p>
        {requirements.length === 0 && (
          <p className="text-sm text-magic-muted text-center py-4">Nenhum requisito definido</p>
        )}
        <div className="space-y-2">
          {requirements.map((req, i) => (
            <div key={i} className="flex items-center gap-3 bg-slate-800 rounded-lg px-3 py-2">
              <GripVertical className="w-4 h-4 text-magic-muted shrink-0" />
              <select
                className="input flex-1"
                value={req.category_id}
                onChange={e => updateRequirement(i, 'category_id', Number(e.target.value))}
              >
                <option value={0}>Selecionar categoria...</option>
                {allCategories.map(cat => (
                  <option key={cat.id} value={cat.id}>{catLabel(cat, allCategories)}</option>
                ))}
              </select>
              <span className="text-magic-muted text-sm shrink-0">min</span>
              <input
                type="number"
                min={1}
                className="input w-20"
                value={req.count}
                onChange={e => updateRequirement(i, 'count', Number(e.target.value))}
              />
              <span className="text-magic-muted text-sm shrink-0">eventos</span>
              <button onClick={() => removeRequirement(i)}
                className="text-red-400 hover:text-red-300 shrink-0">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={selectedCardId === '' || saving}
          className="btn-primary flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Salvando...' : config ? 'Atualizar' : 'Salvar Configuração'}
        </button>
      </div>

      {commanderAnalysis && (
        <div>
          <h4 className="font-semibold mb-3 text-sm">Análise de Conjuração do Commander</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-magic-muted border-b border-magic-border">
                  <th className="text-left py-2 px-2">Turno</th>
                  <th className="text-right py-2 px-2">Mana Total</th>
                  <th className="text-right py-2 px-2">Custo Commander</th>
                  <th className="text-right py-2 px-2">Mana Sobra</th>
                  <th className="text-center py-2 px-2">Mana Suficiente</th>
                  <th className="text-center py-2 px-2">{useAdvancedConditions ? 'Condições OK' : 'Requisitos OK'}</th>
                  <th className="text-center py-2 px-2">Prob. Combinada</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(commanderAnalysis.by_turn || {}).map((turn: any) => (
                  <tr key={turn.turn} className="border-b border-magic-border">
                    <td className="py-2 px-2 font-medium">T{turn.turn}</td>
                    <td className="text-right py-2 px-2">{turn.mana?.total_expected_mana?.toFixed(1)}</td>
                    <td className="text-right py-2 px-2">{turn.required_mana}</td>
                    <td className="text-right py-2 px-2">
                      <span className={turn.mana?.mana_after_cast >= (commanderAnalysis.mana_left_over || 0)
                        ? 'text-green-400' : 'text-red-400'}>
                        {turn.mana?.mana_after_cast?.toFixed(1)}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2">
                      {turn.mana?.enough_mana
                        ? <span className="text-green-400">Sim</span>
                        : <span className="text-red-400">Não</span>}
                    </td>
                    <td className="text-center py-2 px-2">
                      {useAdvancedConditions
                        ? (turn.all_conditions_met ? <span className="text-green-400">Sim</span> : <span className="text-red-400">Não</span>)
                        : (turn.all_category_requirements_met_expected ? <span className="text-green-400">Sim</span> : <span className="text-red-400">Não</span>)}
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={turn.combined_probability > 0.5 ? 'text-green-400' : 'text-amber-400'}>
                        {(turn.combined_probability * 100).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!useAdvancedConditions && commanderAnalysis.min_category_requirements?.length > 0 && (
            <div className="mt-4">
              <h5 className="text-sm font-medium mb-2">Detalhamento dos Requisitos de Categoria</h5>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-magic-muted border-b border-magic-border">
                      <th className="text-left py-2 px-2">Turno</th>
                      {commanderAnalysis.by_turn?.[1]?.category_requirements?.map((cr: any, i: number) => {
                        const cat = allCategories.find(c => c.id === cr.category_id)
                        return (
                          <th key={i} className="text-center py-2 px-2">
                            {cat ? catLabel(cat, allCategories) : `Cat ${cr.category_id}`} ({cr.required}x)
                          </th>
                        )
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.values(commanderAnalysis.by_turn || {}).map((turn: any) => (
                      <tr key={turn.turn} className="border-b border-magic-border">
                        <td className="py-2 px-2 font-medium">T{turn.turn}</td>
                        {turn.category_requirements?.map((cr: any, i: number) => (
                          <td key={i} className={`text-center py-2 px-2 ${cr.is_met_expected ? 'text-green-400' : 'text-red-400'}`}>
                            {cr.expected_pool}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {useAdvancedConditions && commanderAnalysis.condition_groups?.length > 0 && (
            <div className="mt-4">
              <h5 className="text-sm font-medium mb-2">Detalhamento das Condições Avançadas</h5>
              <div className="space-y-2">
                {Object.values(commanderAnalysis.by_turn || {}).map((turn: any) => (
                  <div key={turn.turn} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                    <div className="font-medium text-sm mb-2">Turno {turn.turn}</div>
                    {turn.condition_groups_evaluation?.group_results?.map((group: any, i: number) => {
                      const groupDef = commanderAnalysis.condition_groups?.[i]
                      return (
                        <div key={i} className="text-xs text-magic-muted ml-2 mb-1">
                          <span className={group.is_met ? 'text-green-400' : 'text-red-400'}>
                            Grupo {i + 1} ({group.operator}): {group.is_met ? '✓' : '✗'} - {(group.probability * 100).toFixed(0)}%
                          </span>
                        </div>
                      )
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
