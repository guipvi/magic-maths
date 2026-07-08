import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { decks, analysis } from '../services/api'
import { Shield, Map, Bug, Tags, BarChart3, TrendingUp, Loader2 } from 'lucide-react'
import InteractionBreakdown from '../components/InteractionBreakdown'
import LandRecommender from '../components/LandRecommender'
import DebugPanel from '../components/DebugPanel'
import CategoryPanel from '../components/CategoryPanel'
import CategoryChart from '../components/CategoryChart'
import ManaCurveChart from '../components/ManaCurveChart'
import GoldfishSim from '../components/GoldfishSim'

interface AnalysisData {
  interactions: any
  land_recommendation: any
  categories: any
  mana_ramp: any
  goldfish: any
}

export default function DeckAnalysis() {
  const { id } = useParams<{ id: string }>()
  const [deckInfo, setDeckInfo] = useState<any>(null)
  const [cards, setCards] = useState<any[]>([])
  const [data, setData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<string>('categories')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      decks.get(id),
      analysis.full({ deck_id: id }),
    ])
      .then(([deckRes, analysisRes]) => {
        setDeckInfo(deckRes.data.deck)
        setCards(deckRes.data.cards)
        setData(analysisRes.data)
      })
      .catch((err) => {
        setError(err.response?.data?.error || 'Erro ao carregar análise')
      })
      .finally(() => setLoading(false))
  }, [id])

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
    { id: 'interactions', label: 'Interações', icon: Shield },
    { id: 'lands', label: 'Terrenos', icon: Map },
    { id: 'debug', label: 'Debug', icon: Bug },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{deckInfo?.name || 'Análise do Deck'}</h1>
        <p className="text-magic-muted text-sm mt-1">
          {deckInfo?.format} &mdash; {cards.length} cards
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
            {id && <CategoryPanel deckId={id} cards={cards} />}
            {data?.categories && <CategoryChart data={data.categories} />}
          </div>
        )}
        {activeTab === 'mana' && data?.mana_ramp && <ManaCurveChart data={data.mana_ramp} />}
        {activeTab === 'goldfish' && data?.goldfish && <GoldfishSim data={data.goldfish} />}
        {activeTab === 'interactions' && <InteractionBreakdown data={data?.interactions} categories={data?.categories?.categories} />}
        {activeTab === 'lands' && data?.land_recommendation && <LandRecommender data={data.land_recommendation} />}
        {activeTab === 'debug' && <DebugPanel cards={cards} analysis={data} />}
      </div>
    </div>
  )
}
