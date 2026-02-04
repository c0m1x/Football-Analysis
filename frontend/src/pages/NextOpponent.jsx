import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { API_BASE_URL } from '../config/api'
import { Calendar, Clock, MapPin, Target, Brain, FileText, FileJson, RefreshCw, AlertTriangle, BarChart3 } from 'lucide-react'
import AdvancedStatsPanel from '../components/AdvancedStatsPanel'
import TacticalPlanPanel from '../components/TacticalPlanPanel'
import { exportFixtureAnalysis } from '../utils/exportAnalysis'
import { Link } from 'react-router-dom'
import TeamBadge from '../components/TeamBadge'

const toErrorText = async (res) => {
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    const j = await res.json().catch(() => null)
    const detail = j?.detail || j?.error || j?.message
    if (detail) return String(detail)
  }
  return await res.text().catch(() => `Request failed: ${res.status}`)
}

const badgeClass = (source) => {
  const s = String(source || '').toLowerCase()
  if (s.includes('scraper')) return 'bg-amber-100 text-amber-800'
  if (s.includes('cache')) return 'bg-slate-100 text-slate-800'
  if (s.includes('sofa')) return 'bg-emerald-100 text-emerald-800'
  if (s.includes('error')) return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

const NextOpponent = () => {
  const [activeTab, setActiveTab] = useState('tactical')

  const {
    data: upcoming,
    isLoading: loadingUpcoming,
    error: upcomingError,
    refetch: refetchUpcoming,
    isFetching: fetchingUpcoming,
  } = useQuery({
    queryKey: ['fixtures-upcoming', 1],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/fixtures/upcoming?limit=1`)
      if (!res.ok) throw new Error(await toErrorText(res))
      return res.json()
    },
  })

  const nextFixture = upcoming?.fixtures?.[0] || null
  const opponentId = nextFixture?.opponent_id
  const opponentName = nextFixture?.opponent_name

  const matchDate = useMemo(() => {
    if (!nextFixture?.date) return null
    const time = nextFixture?.time || '00:00:00'
    const dt = new Date(`${nextFixture.date}T${time}`)
    if (Number.isNaN(dt.getTime())) return null
    return dt
  }, [nextFixture?.date, nextFixture?.time])

  const {
    data: statistics,
    isLoading: loadingStats,
    error: statsError,
    refetch: refetchStats,
    isFetching: fetchingStats,
  } = useQuery({
    queryKey: ['opponent-stats', opponentId, opponentName],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/opponent-stats/${opponentId}?opponent_name=${encodeURIComponent(opponentName)}`
      )
      if (!res.ok) throw new Error(await toErrorText(res))
      const json = await res.json()
      if (json?.data_source === 'error' && json?.error) throw new Error(String(json.error))
      return json
    },
    enabled: !!opponentId && !!opponentName,
  })

  const {
    data: tacticalPlan,
    isLoading: loadingPlan,
    error: planError,
    refetch: refetchPlan,
    isFetching: fetchingPlan,
  } = useQuery({
    queryKey: ['tactical-plan', opponentId, opponentName],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/tactical-plan/${opponentId}?opponent_name=${encodeURIComponent(opponentName)}`
      )
      if (!res.ok) throw new Error(await toErrorText(res))
      const json = await res.json()
      if (json?.data_source === 'error' && json?.error) throw new Error(String(json.error))
      return json
    },
    enabled: !!opponentId && !!opponentName,
  })

  const handleRefresh = async () => {
    await Promise.all([refetchUpcoming(), refetchStats(), refetchPlan()])
  }

  if (loadingUpcoming) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">A procurar o próximo jogo…</p>
        </div>
      </div>
    )
  }

  if (upcomingError) {
    return (
      <div className="space-y-4">
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <p className="text-red-700">Erro a carregar o próximo jogo: {String(upcomingError.message || upcomingError)}</p>
        </div>
        <button
          onClick={() => refetchUpcoming()}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          Tentar novamente
        </button>
      </div>
    )
  }

  if (!nextFixture) {
    return (
      <div className="tactical-card">
        <p className="text-gray-700">Não há jogos futuros no calendário.</p>
        <p className="text-gray-600 mt-2">
          Confere a página de <Link to="/calendar" className="text-blue-700 underline">Calendário</Link>.
        </p>
      </div>
    )
  }

  const dataSourceStats = statistics?.data_source
  const dataSourcePlan = tacticalPlan?.data_source
  const busy = fetchingUpcoming || fetchingStats || fetchingPlan

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Target className="text-[#C41E3A]" size={28} />
            Próximo Adversário
          </h2>
          <p className="text-gray-600 mt-2">
            Plano tático com evidência estatística — focado apenas no próximo jogo.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {statistics && tacticalPlan && (
            <>
              <button
                onClick={() => exportFixtureAnalysis(nextFixture, statistics, tacticalPlan, 'text')}
                className="inline-flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                title="Exportar TXT"
              >
                <FileText size={18} />
                TXT
              </button>
              <button
                onClick={() => exportFixtureAnalysis(nextFixture, statistics, tacticalPlan, 'json')}
                className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                title="Exportar JSON"
              >
                <FileJson size={18} />
                JSON
              </button>
            </>
          )}

          <button
            onClick={handleRefresh}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-black text-white rounded-lg transition-colors disabled:opacity-60"
            disabled={busy}
            title="Atualizar"
          >
            <RefreshCw size={18} className={busy ? 'animate-spin' : ''} />
            Atualizar
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-md border overflow-hidden">
        <div className="bg-gradient-to-r from-[#003C71] to-[#0B5FA5] text-white p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-sm opacity-90">Jogo</p>
              <h3 className="text-2xl font-bold flex items-center gap-3 flex-wrap">
                <span className="inline-flex items-center gap-2">
                  <TeamBadge name="Gil Vicente" size={40} />
                  <span>Gil Vicente</span>
                </span>
                <span className="text-white/80">vs</span>
                <span className="inline-flex items-center gap-2">
                  <TeamBadge name={nextFixture.opponent_name} logo={nextFixture.opponent_logo} size={40} />
                  <span>{nextFixture.opponent_name}</span>
                </span>
              </h3>
              <div className="flex flex-wrap items-center gap-3 mt-3 text-sm opacity-95">
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${nextFixture.is_home ? 'bg-green-200 text-green-900' : 'bg-orange-200 text-orange-900'}`}>
                  {nextFixture.is_home ? 'CASA' : 'FORA'}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Calendar size={14} />
                  {matchDate ? matchDate.toLocaleDateString('pt-PT', { weekday: 'long', day: '2-digit', month: 'long' }) : (nextFixture.date || 'TBD')}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Clock size={14} />
                  {matchDate ? matchDate.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' }) : (nextFixture.time || 'TBD')}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MapPin size={14} />
                  {nextFixture.is_home ? 'Estádio Cidade de Barcelos' : 'Fora'}
                </span>
              </div>
            </div>

            <div className="text-right">
              <p className="text-sm opacity-90">Fontes de dados</p>
              <div className="flex items-center justify-end gap-2 mt-2 flex-wrap">
                <span className={`px-2 py-1 rounded text-xs font-bold ${badgeClass(dataSourceStats)}`}>
                  Stats: {dataSourceStats || (loadingStats ? '…' : 'N/A')}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-bold ${badgeClass(dataSourcePlan)}`}>
                  AI: {dataSourcePlan || (loadingPlan ? '…' : 'N/A')}
                </span>
              </div>
              {(statistics?.cache_info || tacticalPlan?.cache_info) && (
                <p className="text-xs opacity-90 mt-2 max-w-[360px]">
                  {statistics?.cache_info || tacticalPlan?.cache_info}
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setActiveTab('tactical')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                activeTab === 'tactical'
                  ? 'bg-white text-[#003C71]'
                  : 'bg-white bg-opacity-20 text-white hover:bg-opacity-30'
              }`}
            >
              <Brain size={18} />
              Recomendações (AI)
            </button>
            <button
              onClick={() => setActiveTab('statistics')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                activeTab === 'statistics'
                  ? 'bg-white text-[#003C71]'
                  : 'bg-white bg-opacity-20 text-white hover:bg-opacity-30'
              }`}
            >
              <BarChart3 size={18} />
              Estatísticas
            </button>
          </div>
        </div>

        <div className="p-6">
          {activeTab === 'tactical' && (
            <div className="space-y-4">
              {loadingPlan && (
                <div className="tactical-card text-center py-14">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-purple-600 mx-auto" />
                  <p className="mt-4 text-gray-600">A gerar plano tático…</p>
                </div>
              )}

              {planError && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 flex items-start gap-3">
                  <AlertTriangle className="text-red-600 mt-0.5" size={18} />
                  <div>
                    <p className="text-red-800 font-semibold">Erro ao gerar recomendações</p>
                    <p className="text-red-700">{String(planError.message || planError)}</p>
                  </div>
                </div>
              )}

              {tacticalPlan && !loadingPlan && !planError && (
                <TacticalPlanPanel tacticalPlan={tacticalPlan} />
              )}
            </div>
          )}

          {activeTab === 'statistics' && (
            <div className="space-y-4">
              {loadingStats && (
                <div className="tactical-card text-center py-14">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600 mx-auto" />
                  <p className="mt-4 text-gray-600">A carregar estatísticas…</p>
                </div>
              )}

              {statsError && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 flex items-start gap-3">
                  <AlertTriangle className="text-red-600 mt-0.5" size={18} />
                  <div>
                    <p className="text-red-800 font-semibold">Erro ao carregar estatísticas</p>
                    <p className="text-red-700">{String(statsError.message || statsError)}</p>
                  </div>
                </div>
              )}

              {statistics && !loadingStats && !statsError && (
                <div className="space-y-6">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border-2 border-blue-200">
                    <h4 className="text-xl font-bold text-gray-900 mb-4">
                      Resumo (últimos jogos)
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-white p-3 rounded-lg border">
                        <p className="text-sm text-gray-600">Forma</p>
                        <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.form_string || 'N/A'}</p>
                      </div>
                      <div className="bg-white p-3 rounded-lg border">
                        <p className="text-sm text-gray-600">Golos/Jogo</p>
                        <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.goals_per_game ?? 'N/A'}</p>
                      </div>
                      <div className="bg-white p-3 rounded-lg border">
                        <p className="text-sm text-gray-600">Sofridos/Jogo</p>
                        <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.conceded_per_game ?? 'N/A'}</p>
                      </div>
                      <div className="bg-white p-3 rounded-lg border">
                        <p className="text-sm text-gray-600">Pts/Jogo</p>
                        <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.points_per_game ?? 'N/A'}</p>
                      </div>
                    </div>
                  </div>

                  <AdvancedStatsPanel statistics={statistics} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default NextOpponent
