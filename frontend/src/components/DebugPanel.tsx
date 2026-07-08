import { useMemo } from 'react'
import { categories as api } from '../services/api'
import { useState, useEffect } from 'react'

interface Props {
  cards: any[]
  analysis: any
}

export default function DebugPanel({ cards, analysis }: Props) {
  const [allCategories, setAllCategories] = useState<any[]>([])

  useEffect(() => {
    api.list().then(r => setAllCategories(r.data)).catch(() => {})
  }, [])

  const categoryMap = useMemo(() => {
    const map: Record<number, { name: string; color: string }> = {}
    for (const cat of allCategories) {
      map[cat.id] = cat
    }
    return map
  }, [allCategories])

  const debugRows = useMemo(() => {
    if (!cards?.length) return []
    return cards.map((card: any, index: number) => {
      const resolved = card.card || card
      const isLand = /\bland\b/i.test(resolved.type_line || '')
      return {
        index: index + 1,
        name: resolved.name || '—',
        cmc: resolved.cmc ?? '—',
        type_line: resolved.type_line || '—',
        color_identity: resolved.color_identity || [],
        isLand,
        categories: resolved.category_assignments || [],
      }
    })
  }, [cards, analysis, categoryMap])

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Debug dos cards</h3>
          <p className="text-sm text-magic-muted">
            Dados brutos dos cards e categorias atribuídas.
          </p>
        </div>
      </div>
      <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-900/90">
            <tr className="text-magic-muted border-b border-magic-border">
              <th className="text-left py-2 px-2">#</th>
              <th className="text-left py-2 px-2">Card</th>
              <th className="text-left py-2 px-2">CMC</th>
              <th className="text-left py-2 px-2">Tipo</th>
              <th className="text-left py-2 px-2">Terra</th>
              <th className="text-left py-2 px-2">Cor</th>
            </tr>
          </thead>
          <tbody>
            {debugRows.map((row) => (
              <tr key={`${row.name}-${row.index}`} className="border-b border-magic-border align-top">
                <td className="py-2 px-2">{row.index}</td>
                <td className="py-2 px-2 font-medium">{row.name}</td>
                <td className="py-2 px-2">{row.cmc}</td>
                <td className="py-2 px-2 max-w-[200px]">{row.type_line}</td>
                <td className="py-2 px-2">{row.isLand ? 'Sim' : 'Não'}</td>
                <td className="py-2 px-2">{row.color_identity.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
