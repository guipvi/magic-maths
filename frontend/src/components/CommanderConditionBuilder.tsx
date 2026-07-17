import { useState } from 'react'
import { Plus, Trash2, GripVertical, ChevronDown } from 'lucide-react'

function catLabel(c: any, allCats: any[]): string {
  if (c.parent_id) {
    const parent = allCats.find(p => p.id === c.parent_id)
    if (parent) return `${parent.name} › ${c.name}`
  }
  return c.name
}

interface Condition {
  id: string
  type: 'category'
  category_id: number
  required_count: number
}

interface ConditionGroup {
  id: string
  operator: 'AND' | 'OR'
  conditions: Condition[]
}

interface Props {
  conditionGroups: ConditionGroup[]
  onUpdate: (groups: ConditionGroup[]) => void
  allCategories: any[]
}

export default function CommanderConditionBuilder({ conditionGroups, onUpdate, allCategories }: Props) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())

  const generateId = () => `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  const toggleGroupExpanded = (groupId: string) => {
    const next = new Set(expandedGroups)
    if (next.has(groupId)) {
      next.delete(groupId)
    } else {
      next.add(groupId)
    }
    setExpandedGroups(next)
  }

  const addConditionGroup = () => {
    const newGroup: ConditionGroup = {
      id: generateId(),
      operator: 'AND',
      conditions: [
        {
          id: generateId(),
          type: 'category',
          category_id: 0,
          required_count: 1,
        },
      ],
    }
    onUpdate([...conditionGroups, newGroup])
    setExpandedGroups(new Set([...expandedGroups, newGroup.id]))
  }

  const removeConditionGroup = (groupId: string) => {
    onUpdate(conditionGroups.filter(g => g.id !== groupId))
    const next = new Set(expandedGroups)
    next.delete(groupId)
    setExpandedGroups(next)
  }

  const updateGroupOperator = (groupId: string, operator: 'AND' | 'OR') => {
    const next = conditionGroups.map(g =>
      g.id === groupId ? { ...g, operator } : g
    )
    onUpdate(next)
  }

  const addConditionToGroup = (groupId: string) => {
    const next = conditionGroups.map(g => {
      if (g.id === groupId) {
        return {
          ...g,
          conditions: [
            ...g.conditions,
            {
              id: generateId(),
              type: 'category' as const,
              category_id: 0,
              required_count: 1,
            },
          ],
        }
      }
      return g
    })
    onUpdate(next)
  }

  const removeCondition = (groupId: string, conditionId: string) => {
    const next = conditionGroups.map(g => {
      if (g.id === groupId) {
        return {
          ...g,
          conditions: g.conditions.filter(c => c.id !== conditionId),
        }
      }
      return g
    })
    onUpdate(next)
  }

  const updateCondition = (
    groupId: string,
    conditionId: string,
    field: 'category_id' | 'required_count',
    value: number
  ) => {
    const next = conditionGroups.map(g => {
      if (g.id === groupId) {
        return {
          ...g,
          conditions: g.conditions.map(c =>
            c.id === conditionId ? { ...c, [field]: value } : c
          ),
        }
      }
      return g
    })
    onUpdate(next)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-sm">Condições Avançadas (E/OU)</h4>
        <button
          onClick={addConditionGroup}
          className="btn btn-primary text-xs flex items-center gap-1 py-1"
        >
          <Plus className="w-3 h-3" /> Novo Grupo
        </button>
      </div>

      {conditionGroups.length === 0 && (
        <p className="text-sm text-magic-muted text-center py-4">
          Nenhum grupo de condições. Clique em "Novo Grupo" para começar.
        </p>
      )}

      <div className="space-y-3">
        {conditionGroups.map((group, groupIndex) => (
          <div key={group.id} className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            {/* Group Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-750 border-b border-slate-700">
              <div className="flex items-center gap-3 flex-1">
                <button
                  onClick={() => toggleGroupExpanded(group.id)}
                  className="text-magic-muted hover:text-magic-text"
                >
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${
                      expandedGroups.has(group.id) ? 'rotate-0' : '-rotate-90'
                    }`}
                  />
                </button>
                <span className="text-sm font-medium text-magic-muted">Grupo {groupIndex + 1}</span>

                {/* Operator Selector */}
                <select
                  value={group.operator}
                  onChange={e => updateGroupOperator(group.id, e.target.value as 'AND' | 'OR')}
                  className="input text-xs py-1 px-2 w-20"
                >
                  <option value="AND">E (AND)</option>
                  <option value="OR">OU (OR)</option>
                </select>

                <span className="text-xs text-magic-muted">
                  {group.conditions.length} condição{group.conditions.length !== 1 ? 'ões' : ''}
                </span>
              </div>

              <button
                onClick={() => removeConditionGroup(group.id)}
                className="text-red-400 hover:text-red-300 shrink-0"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* Group Content */}
            {expandedGroups.has(group.id) && (
              <div className="px-4 py-3 space-y-2">
                {group.conditions.map((condition, condIndex) => (
                  <div key={condition.id} className="flex items-center gap-3 bg-slate-900 rounded px-3 py-2">
                    <GripVertical className="w-4 h-4 text-magic-muted shrink-0" />

                    <select
                      value={condition.category_id}
                      onChange={e =>
                        updateCondition(group.id, condition.id, 'category_id', Number(e.target.value))
                      }
                      className="input flex-1 text-sm py-1"
                    >
                      <option value={0}>Selecionar categoria...</option>
                      {allCategories.map(cat => (
                        <option key={cat.id} value={cat.id}>
                          {catLabel(cat, allCategories)}
                        </option>
                      ))}
                    </select>

                    <span className="text-magic-muted text-xs shrink-0">mín.</span>

                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={condition.required_count}
                      onChange={e =>
                        updateCondition(group.id, condition.id, 'required_count', Number(e.target.value))
                      }
                      className="input w-16 text-sm py-1"
                    />

                    <span className="text-magic-muted text-xs shrink-0">eventos</span>

                    <button
                      onClick={() => removeCondition(group.id, condition.id)}
                      className="text-red-400 hover:text-red-300 shrink-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}

                <button
                  onClick={() => addConditionToGroup(group.id)}
                  className="btn btn-secondary text-xs w-full py-1 flex items-center justify-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Adicionar Condição
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {conditionGroups.length > 0 && (
        <div className="bg-slate-900 rounded-lg p-3 border border-slate-700">
          <p className="text-xs text-magic-muted">
            <strong>Lógica Final:</strong> Todos os grupos devem ser satisfeitos (AND entre grupos).
            Dentro de cada grupo, as condições são combinadas com o operador selecionado (E/OU).
          </p>
        </div>
      )}
    </div>
  )
}
