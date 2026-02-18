import React, { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { API_BASE_URL } from '../config/api'
import {
  Calendar,
  Clock,
  MapPin,
  Target,
  Brain,
  FileText,
  FileJson,
  RefreshCw,
  AlertTriangle,
  BarChart3,
  FileDown,
  FileType,
} from 'lucide-react'
import AdvancedStatsPanel from '../components/AdvancedStatsPanel'
import TacticalPlanPanel from '../components/TacticalPlanPanel'
import { exportFixtureAnalysis } from '../utils/exportAnalysis'
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
  if (s.includes('cache')) return 'bg-slate-100 text-slate-800'
  if (s.includes('who')) return 'bg-cyan-100 text-cyan-800'
  if (s.includes('manual')) return 'bg-amber-100 text-amber-800'
  if (s.includes('error')) return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

const normalize = (txt) =>
  String(txt || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()

const emptyObservation = () => ({
  match_label: '',
  possession_percent: '',
  shots_for: '',
  goals_scored: '',
  goals_conceded: '',
  pressing_level: 'medium',
  offensive_transitions_rating: '',
  build_up_pattern: '',
  defensive_line_height: '',
  set_piece_vulnerability: '',
  key_players_text: '',
  notes: '',
})

const NextOpponent = () => {
  const [activeTab, setActiveTab] = useState('tactical')
  const [opponentMode, setOpponentMode] = useState('next')
  const [manualOpponentName, setManualOpponentName] = useState('')
  const [recalibratedPlan, setRecalibratedPlan] = useState(null)
  const [recalibrating, setRecalibrating] = useState(false)
  const [recalibrationError, setRecalibrationError] = useState('')
  const [observations, setObservations] = useState([
    emptyObservation(),
    emptyObservation(),
    emptyObservation(),
  ])

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

  const {
    data: opponentsData,
    isLoading: loadingOpponents,
    error: opponentsError,
    refetch: refetchOpponents,
    isFetching: fetchingOpponents,
  } = useQuery({
    queryKey: ['opponents'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/opponents`)
      if (!res.ok) throw new Error(await toErrorText(res))
      return res.json()
    },
  })

  const nextFixture = upcoming?.fixtures?.[0] || null
  const opponents = opponentsData?.opponents || []

  useEffect(() => {
    if (nextFixture?.opponent_name && !manualOpponentName) {
      setManualOpponentName(nextFixture.opponent_name)
    }
  }, [nextFixture?.opponent_name, manualOpponentName])

  const selectedManualOpponent = useMemo(() => {
    const target = normalize(manualOpponentName)
    if (!target) return null
    return opponents.find((o) => normalize(o?.name) === target) || null
  }, [manualOpponentName, opponents])

  const selectedOpponent = useMemo(() => {
    if (opponentMode === 'manual') {
      if (!selectedManualOpponent) return null
      return {
        id: selectedManualOpponent.id,
        name: selectedManualOpponent.name,
        fixture: null,
      }
    }
    if (!nextFixture) return null
    return {
      id: nextFixture?.opponent_id,
      name: nextFixture?.opponent_name,
      fixture: nextFixture,
    }
  }, [opponentMode, selectedManualOpponent, nextFixture])

  const opponentId = selectedOpponent?.id
  const opponentName = selectedOpponent?.name
  const selectedFixture = selectedOpponent?.fixture

  useEffect(() => {
    setRecalibratedPlan(null)
    setRecalibrationError('')
  }, [opponentId, opponentName])

  const matchDate = useMemo(() => {
    if (!selectedFixture?.date) return null
    const time = selectedFixture?.time || '00:00:00'
    const dt = new Date(`${selectedFixture.date}T${time}`)
    if (Number.isNaN(dt.getTime())) return null
    return dt
  }, [selectedFixture?.date, selectedFixture?.time])

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

  const effectivePlan = recalibratedPlan || tacticalPlan || null

  const validationNote =
    effectivePlan?.historical_context?.validation_note ||
    statistics?.historical_context?.validation_note ||
    'Baseado em dados da época 2023/24 — validar com observação recente do adversário.'

  const baselineSeason =
    effectivePlan?.historical_context?.baseline_season ||
    statistics?.historical_context?.baseline_season ||
    '2023/24'

  const updateObservation = (idx, field, value) => {
    setObservations((prev) => {
      const clone = [...prev]
      clone[idx] = { ...clone[idx], [field]: value }
      return clone
    })
  }

  const parseMaybeNumber = (value) => {
    if (value === '' || value === null || value === undefined) return null
    const n = Number(value)
    if (Number.isNaN(n)) return null
    return n
  }

  const hasObservationContent = (obs) =>
    [
      obs.possession_percent,
      obs.shots_for,
      obs.goals_scored,
      obs.goals_conceded,
      obs.offensive_transitions_rating,
      obs.build_up_pattern,
      obs.set_piece_vulnerability,
      obs.key_players_text,
      obs.notes,
    ].some((v) => String(v || '').trim() !== '')

  const submitRecalibration = async () => {
    if (!opponentId || !opponentName) return
    setRecalibrationError('')
    setRecalibrating(true)
    try {
      const payload = {
        opponent_name: opponentName,
        current_season_observations: observations
          .filter(hasObservationContent)
          .map((obs, i) => ({
            match_label: obs.match_label || `Observação ${i + 1}`,
            possession_percent: parseMaybeNumber(obs.possession_percent),
            shots_for: parseMaybeNumber(obs.shots_for),
            goals_scored: parseMaybeNumber(obs.goals_scored),
            goals_conceded: parseMaybeNumber(obs.goals_conceded),
            pressing_level: obs.pressing_level || null,
            offensive_transitions_rating: parseMaybeNumber(obs.offensive_transitions_rating),
            build_up_pattern: obs.build_up_pattern || null,
            defensive_line_height: parseMaybeNumber(obs.defensive_line_height),
            set_piece_vulnerability: obs.set_piece_vulnerability || null,
            key_players: String(obs.key_players_text || '')
              .split(',')
              .map((x) => x.trim())
              .filter(Boolean),
            notes: obs.notes || null,
          })),
      }

      const res = await fetch(`${API_BASE_URL}/api/v1/tactical-plan/${opponentId}/recalibrate`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await toErrorText(res))
      const json = await res.json()
      if (json?.data_source === 'error' && json?.error) throw new Error(String(json.error))
      setRecalibratedPlan(json)
    } catch (err) {
      setRecalibrationError(String(err?.message || err))
    } finally {
      setRecalibrating(false)
    }
  }

  const handleRefresh = async () => {
    await Promise.all([refetchUpcoming(), refetchOpponents(), refetchStats(), refetchPlan()])
  }

  if (loadingUpcoming || loadingOpponents) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">A carregar dados de adversários…</p>
        </div>
      </div>
    )
  }

  if (upcomingError || opponentsError) {
    return (
      <div className="space-y-4">
        {upcomingError && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-red-700">Erro a carregar próximo jogo: {String(upcomingError.message || upcomingError)}</p>
          </div>
        )}
        {opponentsError && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-red-700">Erro a carregar lista de adversários: {String(opponentsError.message || opponentsError)}</p>
          </div>
        )}
        <button
          onClick={() => {
            refetchUpcoming()
            refetchOpponents()
          }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          Tentar novamente
        </button>
      </div>
    )
  }

  const unresolvedManualOpponent = opponentMode === 'manual' && manualOpponentName && !selectedManualOpponent
  const dataSourceStats = statistics?.data_source
  const dataSourcePlan = effectivePlan?.data_source
  const busy = fetchingUpcoming || fetchingOpponents || fetchingStats || fetchingPlan || recalibrating

  const exportFixture = selectedFixture || {
    opponent_name: opponentName,
    date: null,
    time: null,
    is_home: true,
    competition: 'Análise manual',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Target className="text-[#C41E3A]" size={28} />
            Análise Tática Interativa
          </h2>
          <p className="text-gray-600 mt-2">
            Histórico {baselineSeason} + ajuste de confiança com observação manual da época atual.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {statistics && effectivePlan && (
            <>
              <button
                onClick={() => exportFixtureAnalysis(exportFixture, statistics, effectivePlan, 'pdf')}
                className="inline-flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                title="Exportar PDF"
              >
                <FileDown size={18} />
                PDF
              </button>
              <button
                onClick={() => exportFixtureAnalysis(exportFixture, statistics, effectivePlan, 'word')}
                className="inline-flex items-center gap-2 px-3 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-lg transition-colors"
                title="Exportar Word"
              >
                <FileType size={18} />
                Word
              </button>
              <button
                onClick={() => exportFixtureAnalysis(exportFixture, statistics, effectivePlan, 'text')}
                className="inline-flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                title="Exportar TXT"
              >
                <FileText size={18} />
                TXT
              </button>
              <button
                onClick={() => exportFixtureAnalysis(exportFixture, statistics, effectivePlan, 'json')}
                className="inline-flex items-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-800 text-white rounded-lg transition-colors"
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

      <div className="bg-white rounded-xl border p-4">
        <p className="text-sm font-semibold text-gray-900">Seleção do adversário</p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setOpponentMode('next')}
            className={`px-3 py-2 rounded-lg border text-sm font-medium ${
              opponentMode === 'next'
                ? 'bg-[#003C71] text-white border-[#003C71]'
                : 'bg-white text-gray-700 border-gray-300'
            }`}
          >
            Próximo jogo
          </button>
          <button
            type="button"
            onClick={() => setOpponentMode('manual')}
            className={`px-3 py-2 rounded-lg border text-sm font-medium ${
              opponentMode === 'manual'
                ? 'bg-[#003C71] text-white border-[#003C71]'
                : 'bg-white text-gray-700 border-gray-300'
            }`}
          >
            Escolher/escrever adversário
          </button>
          {opponentMode === 'manual' && (
            <div className="min-w-[320px] flex-1">
              <input
                list="opponents-list"
                value={manualOpponentName}
                onChange={(e) => setManualOpponentName(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                placeholder="Escreve ou seleciona nome do adversário"
              />
              <datalist id="opponents-list">
                {opponents.map((o) => (
                  <option key={o.id} value={o.name} />
                ))}
              </datalist>
            </div>
          )}
        </div>
        {unresolvedManualOpponent && (
          <p className="text-sm text-red-700 mt-2">
            Adversário não encontrado na lista atual. Seleciona um nome válido.
          </p>
        )}
      </div>

      {!selectedOpponent && (
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4">
          <p className="text-yellow-800">
            Nenhum adversário selecionado. Escolhe um adversário para gerar o relatório.
          </p>
        </div>
      )}

      {selectedOpponent && (
        <div className="bg-white rounded-2xl shadow-md border overflow-hidden">
          <div className="bg-gradient-to-r from-[#003C71] to-[#0B5FA5] text-white p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-sm opacity-90">{selectedFixture ? 'Jogo' : 'Análise personalizada'}</p>
                <h3 className="text-2xl font-bold flex items-center gap-3 flex-wrap">
                  <span className="inline-flex items-center gap-2">
                    <TeamBadge name="Gil Vicente" size={40} />
                    <span>Gil Vicente</span>
                  </span>
                  <span className="text-white/80">vs</span>
                  <span className="inline-flex items-center gap-2">
                    <TeamBadge name={opponentName} size={40} />
                    <span>{opponentName}</span>
                  </span>
                </h3>
                {selectedFixture ? (
                  <div className="flex flex-wrap items-center gap-3 mt-3 text-sm opacity-95">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${selectedFixture.is_home ? 'bg-green-200 text-green-900' : 'bg-orange-200 text-orange-900'}`}>
                      {selectedFixture.is_home ? 'CASA' : 'FORA'}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Calendar size={14} />
                      {matchDate
                        ? matchDate.toLocaleDateString('pt-PT', { weekday: 'long', day: '2-digit', month: 'long' })
                        : selectedFixture.date || 'TBD'}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Clock size={14} />
                      {matchDate
                        ? matchDate.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
                        : selectedFixture.time || 'TBD'}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <MapPin size={14} />
                      {selectedFixture.is_home ? 'Estádio Cidade de Barcelos' : 'Fora'}
                    </span>
                  </div>
                ) : (
                  <p className="text-sm mt-3 opacity-95">
                    Análise sem fixture associado: usa histórico + observações manuais.
                  </p>
                )}
              </div>

              <div className="text-right">
                <p className="text-sm opacity-90">Fontes de dados</p>
                <div className="flex items-center justify-end gap-2 mt-2 flex-wrap">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${badgeClass(dataSourceStats)}`}>
                    Stats: {dataSourceStats || (loadingStats ? '…' : 'N/A')}
                  </span>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${badgeClass(dataSourcePlan)}`}>
                    Plano: {dataSourcePlan || (loadingPlan ? '…' : 'N/A')}
                  </span>
                </div>
                {(statistics?.cache_info || effectivePlan?.cache_info) && (
                  <p className="text-xs opacity-90 mt-2 max-w-[360px]">
                    {statistics?.cache_info || effectivePlan?.cache_info}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-4 bg-amber-100 border border-amber-200 rounded-lg p-3 text-amber-900 text-sm">
              {validationNote}
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
                Sugestões táticas
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
                Dashboard estatístico
              </button>
            </div>
          </div>

          <div className="p-6">
            {activeTab === 'tactical' && (
              <div className="space-y-4">
                <div className="bg-slate-50 border rounded-lg p-4">
                  <h4 className="font-bold text-gray-900">Comparação época passada vs época atual (manual)</h4>
                  <p className="text-sm text-gray-600 mt-1">
                    Introduz até 3 observações recentes do adversário para recalibrar as sugestões.
                  </p>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mt-4">
                    {observations.map((obs, idx) => (
                      <div key={idx} className="bg-white border rounded-lg p-3 space-y-2">
                        <p className="text-sm font-semibold text-gray-900">Observação {idx + 1}</p>
                        <input
                          value={obs.match_label}
                          onChange={(e) => updateObservation(idx, 'match_label', e.target.value)}
                          className="w-full border rounded px-2 py-1 text-sm"
                          placeholder="Ex: Último jogo fora"
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            value={obs.possession_percent}
                            onChange={(e) => updateObservation(idx, 'possession_percent', e.target.value)}
                            className="w-full border rounded px-2 py-1 text-sm"
                            placeholder="Posse %"
                          />
                          <input
                            value={obs.shots_for}
                            onChange={(e) => updateObservation(idx, 'shots_for', e.target.value)}
                            className="w-full border rounded px-2 py-1 text-sm"
                            placeholder="Remates"
                          />
                          <input
                            value={obs.goals_scored}
                            onChange={(e) => updateObservation(idx, 'goals_scored', e.target.value)}
                            className="w-full border rounded px-2 py-1 text-sm"
                            placeholder="Golos marcados"
                          />
                          <input
                            value={obs.goals_conceded}
                            onChange={(e) => updateObservation(idx, 'goals_conceded', e.target.value)}
                            className="w-full border rounded px-2 py-1 text-sm"
                            placeholder="Golos sofridos"
                          />
                          <input
                            value={obs.offensive_transitions_rating}
                            onChange={(e) => updateObservation(idx, 'offensive_transitions_rating', e.target.value)}
                            className="w-full border rounded px-2 py-1 text-sm"
                            placeholder="Transições (0-10)"
                          />
                          <select
                            value={obs.pressing_level}
                            onChange={(e) => updateObservation(idx, 'pressing_level', e.target.value)}
                            className="w-full border rounded px-2 py-1 text-sm"
                          >
                            <option value="high">Pressão alta</option>
                            <option value="medium">Pressão média</option>
                            <option value="low">Pressão baixa</option>
                          </select>
                        </div>
                        <input
                          value={obs.build_up_pattern}
                          onChange={(e) => updateObservation(idx, 'build_up_pattern', e.target.value)}
                          className="w-full border rounded px-2 py-1 text-sm"
                          placeholder="Padrão de construção"
                        />
                        <input
                          value={obs.set_piece_vulnerability}
                          onChange={(e) => updateObservation(idx, 'set_piece_vulnerability', e.target.value)}
                          className="w-full border rounded px-2 py-1 text-sm"
                          placeholder="Vulnerabilidade bolas paradas"
                        />
                        <input
                          value={obs.key_players_text}
                          onChange={(e) => updateObservation(idx, 'key_players_text', e.target.value)}
                          className="w-full border rounded px-2 py-1 text-sm"
                          placeholder="Jogadores-chave (separados por vírgula)"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex items-center gap-3 flex-wrap">
                    <button
                      type="button"
                      onClick={submitRecalibration}
                      disabled={recalibrating || !opponentId}
                      className="px-4 py-2 rounded-lg bg-[#003C71] text-white hover:bg-[#002c53] disabled:opacity-60"
                    >
                      {recalibrating ? 'A recalibrar…' : 'Recalibrar sugestões'}
                    </button>
                    {effectivePlan?.confidence_adjustment?.adjusted_confidence !== undefined && (
                      <p className="text-sm text-gray-700">
                        Confiança ajustada: <span className="font-semibold">{effectivePlan.confidence_adjustment.adjusted_confidence}%</span>{' '}
                        ({effectivePlan?.confidence_adjustment?.recommendation_reliability || 'N/A'})
                      </p>
                    )}
                  </div>
                  {recalibrationError && (
                    <p className="text-sm text-red-700 mt-3">{recalibrationError}</p>
                  )}
                </div>

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

                {effectivePlan && !loadingPlan && !planError && (
                  <TacticalPlanPanel tacticalPlan={effectivePlan} />
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
                        Resumo (últimos jogos históricos)
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
      )}
    </div>
  )
}

export default NextOpponent
