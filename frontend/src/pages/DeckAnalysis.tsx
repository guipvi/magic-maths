import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { decks, analysis, trades } from '../services/api'
import { Shield, Map, Bug, Tags, BarChart3, TrendingUp, Crown, Loader2, ArrowRightLeft } from 'lucide-react'
import InteractionBreakdown from '../components/InteractionBreakdown'
import LandRecommender from '../components/LandRecommender'
import DebugPanel from '../components/DebugPanel'
import CategoryPanel from '../components/CategoryPanel'
import CategoryChart from '../components/CategoryChart'
import ManaCurveChart from '../components/ManaCurveChart'
import GoldfishSim from '../components/GoldfishSim'
import CommanderConfig from '../components/CommanderConfig'
import ExchangePanel from '../components/ExchangePanel'

interface AnalysisData {
  interactions: any
  land_recommendation: any
  categories: any
  mana_ramp: any
  goldfish: any
  commander: any
}

export default function DeckAnalysis() {
  const { id } = useParams<{ id: string }>()
  const [deckInfo, setDeckInfo] = useState<any>(null)
  const [cards, setCards] = useState<any[]>([])
  const [poolCards, setPoolCards] = useState<any[]>([])
  const [data, setData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<string>('categories')
  const [triggerVersion, setTriggerVersion] = useState(0)
  const [maxSpeedGoldfish, setMaxSpeedGoldfish] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      decks.get(id),
      analysis.full({ deck_id: id, max_speed: maxSpeedGoldfish }),
      trades.list(id).catch(() => ({ data: { trades: [] } })),
    ])
      .then(([deckRes, analysisRes, tradesRes]) => {
        setDeckInfo(deckRes.data.deck)
        setCards(deckRes.data.cards)
        setData(analysisRes.data)
        const tradeList = tradesRes.data.trades || []
        const seen = new Set<number>()
        const incoming = tradeList
          .map((t: any) => ({
            card_id: t.card_in.id,
            card: t.card_in,
            _isPoolCard: true,
            _tradeId: t.id,
          }))
          .filter((c: any) => {
            if (seen.has(c.card_id)) return false
            seen.add(c.card_id)
            return true
          })
        setPoolCards(incoming)
      })
      .catch((err) => {
        setError(err.response?.data?.error || 'Erro ao carregar análise')
      })
      .finally(() => setLoading(false))
  }, [id, triggerVersion, maxSpeedGoldfish])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
        <span className="ml-3 text-magic-muted">Analisando deck...</span>
      </div>
    )
  }

  if (error) {
    return <div className="bg-red-900/30 border border-red-700 text-red-300 px-4 py-2 rounded-lg">{error}</div>
  }

  const tabs = [
    { id: 'categories', label: 'Categorias', icon: Tags },
    { id: 'mana', label: 'Mana', icon: BarChart3 },
    { id: 'goldfish', label: 'Goldfish', icon: TrendingUp },
    { id: 'commander', label: 'Commander', icon: Crown },
    { id: 'interactions', label: 'Interações', icon: Shield },
    { id: 'lands', label: 'Terrenos', icon: Map },
    { id: 'exchanges', label: 'Trocas', icon: ArrowRightLeft },
    { id: 'debug', label: 'Debug', icon: Bug },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{deckInfo?.name || 'Análise do Deck'}</h1>
        <p className="text-magic-muted text-sm mt-1">
          {deckInfo?.format} &mdash; {cards.reduce((sum, c) => sum + (c.quantity || 1), 0)} cards
        </p>
      </div>

      <div className="flex gap-1 bg-slate-800 rounded-lg p-1 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white'
                  : 'text-magic-muted hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      <div>
        {activeTab === 'categories' && (
          <div className="space-y-6">
            {id && <CategoryPanel deckId={id} cards={cards} poolCards={poolCards} onTriggersChange={() => setTriggerVersion(v => v + 1)} />}
            {data?.categories && <CategoryChart data={data.categories} />}
          </div>
        )}
        {activeTab === 'mana' && data?.mana_ramp && <ManaCurveChart data={data.mana_ramp} />}
        {activeTab === 'goldfish' && data?.goldfish && (
          <GoldfishSim
            data={data.goldfish}
            maxSpeed={maxSpeedGoldfish}
            onToggleMaxSpeed={() => setMaxSpeedGoldfish(v => !v)}
          />
        )}
        {activeTab === 'commander' && id && <CommanderConfig deckId={id} cards={cards} commanderAnalysis={data?.commander} />}
        {activeTab === 'interactions' && <InteractionBreakdown data={data?.interactions} categories={data?.categories?.categories} />}
        {activeTab === 'lands' && data?.land_recommendation && <LandRecommender data={data.land_recommendation} />}
        {activeTab === 'exchanges' && id && (
          <ExchangePanel 
            deckId={id} 
            cards={cards}
            currentAnalysis={data}
            onUpdate={() => {
              setTriggerVersion(v => v + 1)
            }} 
          />
        )}
        {activeTab === 'debug' && <DebugPanel cards={cards} analysis={data} />}
      </div>
    </div>
  )
}
