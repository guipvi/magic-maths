import React, { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, LineChart, Line
} from 'recharts'

interface Props {
  data: any
}

function catLabel(c: any, catMap: Record<number, any>): string {
  if (c.parent_id && catMap[c.parent_id]) {
    return `${catMap[c.parent_id].name} › ${c.name}`
  }
  return c.name
}

export default function CategoryChart({ data }: Props) {
  const [selectedCats, setSelectedCats] = useState<number[]>([])
  const [viewMode, setViewMode] = useState<'expected' | 'prob' | 'joint' | 'max'>('expected')

  if (!data || !data.by_turn) return null

  const { by_turn, categories } = data
  const turnKeys = Object.keys(by_turn).sort((a, b) => Number(a) - Number(b))
  const catMap = Object.fromEntries((categories || []).map((c: any) => [c.id, c]))

  const toggleCat = (cid: number) => {
    setSelectedCats(prev =>
      prev.includes(cid) ? prev.filter(id => id !== cid) : [...prev, cid]
    )
  }

  const viewModes = [
    { id: 'expected' as const, label: 'Esperado' },
    { id: 'prob' as const, label: 'Probabilidade' },
    { id: 'joint' as const, label: 'Conjunta' },
    { id: 'max' as const, label: 'Máximo' },
  ]

  const header = (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <CategorySelector categories={categories} selected={selectedCats} onToggle={toggleCat} />
      <div className="flex gap-1 ml-auto bg-slate-800 rounded-lg p-0.5">
        {viewModes.map(vm => (
          <button key={vm.id} onClick={() => setViewMode(vm.id)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === vm.id ? 'bg-indigo-600 text-white' : 'text-magic-muted hover:text-white'
            }`}
          >
            {vm.label}
          </button>
        ))}
      </div>
    </div>
  )

  if (viewMode === 'expected') {
    const chartData = turnKeys.map(tk => {
      const turn = by_turn[tk]
      const row: any = { turno: `T${tk}` }
      for (const c of categories || []) {
        const catData = turn.categories[c.id]
        if (catData) {
          row[`v_${c.id}`] = catData.total_expected
          row[`d_${c.id}`] = catData.expected
        }
      }
      return row
    })

    return (
      <div className="space-y-4">
        {header}

        <div className="card">
          <h3 className="font-semibold mb-4">Eventos Esperados por Turno</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }} />
              <Legend />
              {(categories || []).filter((c: any) => selectedCats.length === 0 || selectedCats.includes(c.id)).map((c: any) => (
                <Bar key={c.id} dataKey={`v_${c.id}`} name={catLabel(c, catMap)} stackId="a" fill={c.color} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="font-semibold mb-4">Direto vs Total (com triggers)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }} />
              <Legend />
              {(categories || []).filter((c: any) => selectedCats.length === 0 || selectedCats.includes(c.id)).map((c: any) => (
                <Line key={c.id} type="monotone" dataKey={`v_${c.id}`} name={catLabel(c, catMap)}
                  stroke={c.color} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <DataTable byTurn={by_turn} categories={categories} selectedCats={selectedCats} />
      </div>
    )
  }

  if (viewMode === 'prob') {
    const chartData = turnKeys.map(tk => {
      const turn = by_turn[tk]
      const row: any = { turno: `T${tk}` }
      for (const c of categories || []) {
        const catData = turn.categories[c.id]
        if (catData) {
          row[`p1_${c.id}`] = catData.prob_at_least_1
          row[`p2_${c.id}`] = catData.prob_at_least_2
          row[`p3_${c.id}`] = catData.prob_at_least_3
        }
      }
      return row
    })

    return (
      <div className="space-y-4">
        {header}
        <div className="card">
          <h3 className="font-semibold mb-4">Probabilidade por Categoria</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 1]} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }} />
              <Legend />
              {(categories || []).filter((c: any) => selectedCats.length === 0 || selectedCats.includes(c.id)).map((c: any) => (
                <Line key={c.id} type="monotone" dataKey={`p1_${c.id}`} name={`${catLabel(c, catMap)} >=1`}
                  stroke={c.color} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  if (viewMode === 'joint') {
    // Show joint probabilities for first pair of selected categories
    const cats = (categories || []).filter((c: any) => selectedCats.includes(c.id))
    if (cats.length < 2) {
      return (
        <div className="space-y-4">
          {header}
          <div className="card text-center text-magic-muted py-8">
            <p>Selecione pelo menos 2 categorias para ver probabilidades conjuntas.</p>
          </div>
        </div>
      )
    }

    const pairKey = `${cats[0].id}_${cats[1].id}`
    const chartData = turnKeys.map(tk => {
      const turn = by_turn[tk]
      const joint = turn.joint_probabilities?.[pairKey] || {}
      return {
        turno: `T${tk}`,
        [`P(>=1,>=1)`]: joint['P(>=1,1)'] || 0,
        [`P(>=1,>=2)`]: joint['P(>=1,2)'] || 0,
        [`P(>=2,>=1)`]: joint['P(>=2,1)'] || 0,
        [`P(>=2,>=2)`]: joint['P(>=2,2)'] || 0,
      }
    })

    return (
      <div className="space-y-4">
        {header}
        <div className="card">
          <h3 className="font-semibold mb-4">
            Probabilidade Conjunta: {cats[0].name} ∩ {cats[1].name}
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 1]} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }} />
              <Legend />
              <Line type="monotone" dataKey="P(>=1,>=1)" name="Ambos >=1" stroke="#22c55e" strokeWidth={2} />
              <Line type="monotone" dataKey="P(>=1,>=2)" name={`${cats[0].name}>=1, ${cats[1].name}>=2`}
                stroke="#3b82f6" />
              <Line type="monotone" dataKey="P(>=2,>=1)" name={`${cats[0].name}>=2, ${cats[1].name}>=1`}
                stroke="#a855f7" />
              <Line type="monotone" dataKey="P(>=2,>=2)" name="Ambos >=2"
                stroke="#f59e0b" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  if (viewMode === 'max') {
    const chartData = turnKeys.map(tk => {
      const turn = by_turn[tk]
      const row: any = { turno: `T${tk}` }
      for (const c of categories || []) {
        if (turn.max_events && turn.max_events[c.id] !== undefined) {
          row[`m_${c.id}`] = turn.max_events[c.id]
        }
      }
      return row
    })

    return (
      <div className="space-y-4">
        {header}
        <div className="card">
          <h3 className="font-semibold mb-4">Máximo Teórico de Eventos (com triggers)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turno" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }} />
              <Legend />
              {(categories || []).filter((c: any) => selectedCats.length === 0 || selectedCats.includes(c.id)).map((c: any) => (
                <Bar key={c.id} dataKey={`m_${c.id}`} name={catLabel(c, catMap)} fill={c.color} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  return null
}

function CategorySelector({ categories, selected, onToggle }: {
  categories: any[]; selected: number[]; onToggle: (id: number) => void
}) {
  if (!categories || categories.length === 0) return null

  const catMap = Object.fromEntries(categories.map(c => [c.id, c]))
  const roots = categories.filter(c => !c.parent_id).sort((a, b) => a.name.localeCompare(b.name))
  const getChildren = (pid: number) => categories.filter(c => c.parent_id === pid)

  return (
    <div className="flex flex-wrap gap-2">
      {roots.flatMap(root => [
        <button key={root.id} onClick={() => onToggle(root.id)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
            selected.includes(root.id)
              ? 'bg-slate-700 border-indigo-500 text-white'
              : selected.length === 0
              ? 'bg-slate-800/50 border-slate-600 text-magic-muted'
              : 'bg-slate-800/50 border-slate-600 text-magic-muted opacity-50'
          }`}
          style={selected.includes(root.id) ? { borderColor: root.color } : {}}
        >
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: root.color }} />
          {root.name}
        </button>,
        ...getChildren(root.id).map(child => (
          <button key={child.id} onClick={() => onToggle(child.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
              selected.includes(child.id)
                ? 'bg-slate-700 border-indigo-500 text-white'
                : selected.length === 0
                ? 'bg-slate-800/50 border-slate-600 text-magic-muted'
                : 'bg-slate-800/50 border-slate-600 text-magic-muted opacity-50'
            }`}
            style={selected.includes(child.id) ? { borderColor: child.color } : {}}
          >
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: child.color }} />
            <span className="text-magic-muted/60 text-xs">{catMap[child.parent_id]?.name}</span>
            <span className="mx-0.5 text-magic-muted/40">›</span>
            {child.name}
          </button>
        )),
      ])}
    </div>
  )
}

function DataTable({ byTurn, categories, selectedCats }: {
  byTurn: any; categories: any[]; selectedCats: number[]
}) {
  const turnKeys = Object.keys(byTurn).sort((a, b) => Number(a) - Number(b))
  const catMap = Object.fromEntries((categories || []).map((c: any) => [c.id, c]))
  const visibleCats = (categories || []).filter((c: any) => selectedCats.length === 0 || selectedCats.includes(c.id))

  return (
    <div className="card overflow-x-auto">
      <h3 className="font-semibold mb-4">Detalhamento por Turno</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-magic-muted border-b border-magic-border">
            <th className="text-left py-2 px-2">Turno</th>
            {visibleCats.map(c => (
              <th key={c.id} className="text-right py-2 px-2" colSpan={3}>
                <span className="inline-flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
                  {catLabel(c, catMap)}
                </span>
              </th>
            ))}
          </tr>
          <tr className="text-magic-muted border-b border-magic-border text-xs">
            <th></th>
            {visibleCats.map(c => (
              <React.Fragment key={c.id}>
                <th className="text-right py-1 px-1">Dir</th>
                <th className="text-right py-1 px-1">Trig</th>
                <th className="text-right py-1 px-1">Total</th>
              </React.Fragment>
            ))}
          </tr>
        </thead>
        <tbody>
          {turnKeys.map(tk => {
            const turn = byTurn[tk]
            return (
              <tr key={tk} className="border-b border-magic-border">
                <td className="py-2 px-2 font-medium">T{tk}</td>
                {visibleCats.map(c => {
                  const cd = turn.categories[c.id]
                  return (
                    <React.Fragment key={c.id}>
                      <td className="py-2 px-1 text-right text-magic-muted">{cd?.expected ?? '-'}</td>
                      <td className="py-2 px-1 text-right text-amber-400">{cd?.triggered ?? '-'}</td>
                      <td className="py-2 px-1 text-right font-medium text-indigo-400">{cd?.total_expected ?? '-'}</td>
                    </React.Fragment>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}


