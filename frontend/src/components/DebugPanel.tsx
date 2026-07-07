import { useMemo } from 'react'

interface Props {
  cards: any[]
  analysis: any
}

function getManaDebug(card: any) {
  const resolvedCard = card.card || card
  const typeLine = resolvedCard?.type_line || ''
  const oracleText = resolvedCard?.oracle_text || ''

  const isLand = /\bland\b/i.test(typeLine)
  const text = oracleText.toLowerCase()

  const rampLabels = [] as string[]
  if (/tap to add .*mana/i.test(text) || /add (?:\{[rwubgcp]\}|[rwubgcp]\b)/i.test(text) || /add [a-z]+ mana/i.test(text)) {
    rampLabels.push('mana source')
  }
  if (/search your library for a basic land/i.test(text) || /search your library for a land/i.test(text) || /put a land card/i.test(text)) {
    rampLabels.push('land ramp')
  }
  if (/you may put a land card/i.test(text)) {
    rampLabels.push('extra land')
  }
  if (/add an additional/i.test(text)) {
    rampLabels.push('extra mana')
  }
  if (/costs .*less to cast/i.test(text)) {
    rampLabels.push('cost reducer')
  }

  const isRitual = /add (?:\{[rwubgcp]\}|[rwubgcp]\b).*(?:add|\{[rwubgcp]\}|[rwubgcp])/i.test(text)
  const producesMana = /add (?:\{[rwubgcp]\}|[rwubgcp]\b)/i.test(text) || /add [a-z]+ mana/i.test(text) || /tap to add/i.test(text) || rampLabels.includes('land ramp') || rampLabels.includes('extra land')

  let manaValue = 0
  if (producesMana) manaValue = 1
  if (isRitual) manaValue = 2

  let effectTiming = 'same turn if played'
  if (isLand) effectTiming = 'comes from land drop'
  else if (/search your library/i.test(text) || /put a land card/i.test(text)) effectTiming = 'turn 3+ usually'
  else if (/tap to add/i.test(text)) effectTiming = 'same turn if tapped'
  else if (isRitual) effectTiming = 'immediate mana burst'

  return {
    isLand,
    isRamp: rampLabels.length > 0,
    rampLabels,
    isRitual,
    producesMana,
    manaValue,
    effectTiming,
    typeLine,
  }
}

export default function DebugPanel({ cards, analysis }: Props) {
  const debugRows = useMemo(() => {
    if (!cards?.length) return []

    return cards.map((card: any, index: number) => {
      const resolved = card.card || card
      const manaDebug = getManaDebug(card)

      return {
        index: index + 1,
        name: resolved.name || '—',
        cmc: resolved.cmc ?? card.cmc ?? '—',
        type_line: resolved.type_line || card.type_line || '—',
        oracle_text: resolved.oracle_text || card.oracle_text || '—',
        mana_cost: resolved.mana_cost || card.mana_cost || '—',
        color_identity: resolved.color_identity || card.color_identity || [],
        ...manaDebug,
      }
    })
  }, [cards, analysis])

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Debug dos cards</h3>
          <p className="text-sm text-magic-muted">Campos recebidos por card e propriedades usadas pelos algoritmos.</p>
        </div>
      </div>

      <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-900/90">
            <tr className="text-magic-muted border-b border-magic-border">
              <th className="text-left py-2 px-2">#</th>
              <th className="text-left py-2 px-2">Card</th>
              <th className="text-left py-2 px-2">CMC</th>
              <th className="text-left py-2 px-2">Ramp</th>
              <th className="text-left py-2 px-2">Mana</th>
              <th className="text-left py-2 px-2">Turno</th>
              <th className="text-left py-2 px-2">Tipo</th>
              <th className="text-left py-2 px-2">Texto</th>
              <th className="text-left py-2 px-2">Cor</th>
            </tr>
          </thead>
          <tbody>
            {debugRows.map((row) => (
              <tr key={`${row.name}-${row.index}`} className="border-b border-magic-border align-top">
                <td className="py-2 px-2">{row.index}</td>
                <td className="py-2 px-2 font-medium">{row.name}</td>
                <td className="py-2 px-2">{row.cmc}</td>
                <td className="py-2 px-2">{row.isRamp ? row.rampLabels.join(', ') : '—'}</td>
                <td className="py-2 px-2">{row.producesMana ? `${row.manaValue}` : '0'}</td>
                <td className="py-2 px-2">{row.effectTiming}</td>
                <td className="py-2 px-2 max-w-[180px]">{row.type_line}</td>
                <td className="py-2 px-2 max-w-[320px] whitespace-pre-wrap">{row.oracle_text}</td>
                <td className="py-2 px-2">{row.color_identity.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
