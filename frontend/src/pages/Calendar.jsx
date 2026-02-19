import React, { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { API_BASE_URL } from '../config/api'
import { Calendar as CalendarIcon, Clock, Target, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import TeamBadge from '../components/TeamBadge'
import { loadSelection, saveSelection } from '../utils/selectionStorage'

const toErrorText = async (res) => {
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    const j = await res.json().catch(() => null)
    const detail = j?.detail || j?.error || j?.message
    if (detail) return String(detail)
  }
  return await res.text().catch(() => `Request failed: ${res.status}`)
}

const getLeagueName = (league) => {
  if (!league) return 'N/A'
  return league.replace(/^[A-Z]{3}-/, '')
}

const Calendar = () => {
  const stored = loadSelection()
  const [selectedLeague, setSelectedLeague] = useState(stored.league || '')
  const [selectedTeamId, setSelectedTeamId] = useState(stored.teamId || '')
  const [selectedTeamName, setSelectedTeamName] = useState(stored.teamName || '')

  const {
    data: leaguesData,
    isLoading: loadingLeagues,
    error: leaguesError,
    refetch: refetchLeagues,
    isFetching: fetchingLeagues,
  } = useQuery({
    queryKey: ['leagues'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/leagues`)
      if (!res.ok) throw new Error(await toErrorText(res))
      return res.json()
    },
  })

  const leagues = leaguesData?.leagues || []

  useEffect(() => {
    if (!selectedLeague && leaguesData?.default_league) {
      setSelectedLeague(leaguesData.default_league)
    }
  }, [selectedLeague, leaguesData?.default_league])

  const {
    data: teamsData,
    isLoading: loadingTeams,
    error: teamsError,
    refetch: refetchTeams,
    isFetching: fetchingTeams,
  } = useQuery({
    queryKey: ['teams', selectedLeague],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/teams?league=${encodeURIComponent(selectedLeague)}`)
      if (!res.ok) throw new Error(await toErrorText(res))
      return res.json()
    },
    enabled: !!selectedLeague,
  })

  const teams = teamsData?.teams || []

  useEffect(() => {
    if (!selectedLeague || teams.length === 0) return

    const byId = teams.find((t) => String(t.id) === String(selectedTeamId))
    if (byId) {
      setSelectedTeamName(byId.name)
      return
    }

    const byName = selectedTeamName
      ? teams.find((t) => String(t.name).toLowerCase() === String(selectedTeamName).toLowerCase())
      : null
    if (byName) {
      setSelectedTeamId(String(byName.id))
      setSelectedTeamName(byName.name)
      return
    }

    const first = teams[0]
    if (first) {
      setSelectedTeamId(String(first.id))
      setSelectedTeamName(first.name)
    }
  }, [selectedLeague, teams, selectedTeamId, selectedTeamName])

  useEffect(() => {
    saveSelection({
      league: selectedLeague,
      teamId: selectedTeamId,
      teamName: selectedTeamName,
    })
  }, [selectedLeague, selectedTeamId, selectedTeamName])

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['allFixtures', selectedLeague, selectedTeamId],
    queryFn: async () => {
      const params = new URLSearchParams({
        league: selectedLeague,
        team_id: selectedTeamId,
        team_name: selectedTeamName,
      })
      const res = await fetch(`${API_BASE_URL}/api/v1/fixtures/all?${params.toString()}`)
      if (!res.ok) throw new Error(await toErrorText(res))
      const json = await res.json()
      if (json?.data_source === 'error' && json?.error) throw new Error(String(json.error))
      return json
    },
    enabled: !!selectedLeague && !!selectedTeamId,
  })

  const fixtures = data?.fixtures || []

  const nextUpcoming = useMemo(() => {
    const upcoming = fixtures.filter((f) => f?.status !== 'finished')
    upcoming.sort((a, b) => {
      const ak = `${a?.date || ''}T${a?.time || ''}`
      const bk = `${b?.date || ''}T${b?.time || ''}`
      return ak.localeCompare(bk)
    })
    return upcoming[0] || null
  }, [fixtures])

  if (loadingLeagues || loadingTeams || isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">A carregar calendário…</p>
        </div>
      </div>
    )
  }

  if (leaguesError || teamsError || error) {
    return (
      <div className="space-y-4">
        {leaguesError && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-red-700">Erro a carregar ligas: {String(leaguesError.message || leaguesError)}</p>
          </div>
        )}
        {teamsError && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-red-700">Erro a carregar equipas: {String(teamsError.message || teamsError)}</p>
          </div>
        )}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-red-700">Erro a carregar calendário: {String(error.message || error)}</p>
          </div>
        )}
        <button
          onClick={() => {
            refetchLeagues()
            refetchTeams()
            refetch()
          }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          <RefreshCw size={18} />
          Tentar novamente
        </button>
      </div>
    )
  }

  const upcomingCount = data?.upcoming_fixtures ?? data?.upcoming_count ?? 0
  const pastCount = data?.past_fixtures ?? 0

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border p-4">
        <p className="text-sm font-semibold text-gray-900">Seleção de contexto</p>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Liga</label>
            <select
              value={selectedLeague}
              onChange={(e) => {
                setSelectedLeague(e.target.value)
                setSelectedTeamId('')
                setSelectedTeamName('')
              }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              {leagues.map((league) => (
                <option key={league.code} value={league.code}>
                  {getLeagueName(league.name)}{league.is_training_baseline ? ' (base treino PT)' : ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Equipa</label>
            <select
              value={selectedTeamId}
              onChange={(e) => {
                const id = e.target.value
                const found = teams.find((t) => String(t.id) === String(id))
                setSelectedTeamId(id)
                setSelectedTeamName(found?.name || '')
              }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarIcon className="text-[#003C71]" size={28} />
            Calendário
          </h2>
          <p className="text-gray-600 mt-2">
            {selectedTeamName} · {getLeagueName(selectedLeague)}
          </p>
          <p className="text-gray-600 mt-1">
            {upcomingCount} jogos por disputar · {pastCount} concluídos
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#C41E3A] hover:bg-[#a8182f] text-white rounded-lg transition-colors"
            title="Ir para Próximo Adversário"
          >
            <Target size={18} />
            Próximo adversário
          </Link>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-black text-white rounded-lg transition-colors disabled:opacity-60"
            disabled={isFetching || fetchingLeagues || fetchingTeams}
            title="Atualizar"
          >
            <RefreshCw size={18} className={isFetching ? 'animate-spin' : ''} />
            Atualizar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {fixtures.map((fixture) => {
          const isUpcoming = fixture.status !== 'finished'
          const isNext = !!nextUpcoming && (String(nextUpcoming.match_id || nextUpcoming.id) === String(fixture.match_id || fixture.id))
          const matchDate = fixture.date ? new Date(`${fixture.date}T${fixture.time || '00:00:00'}`) : null
          const locationClass = fixture.is_home ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'

          let resultClass = ''
          if (fixture.result === 'W') resultClass = 'bg-green-600'
          else if (fixture.result === 'D') resultClass = 'bg-yellow-600'
          else if (fixture.result === 'L') resultClass = 'bg-red-600'

          return (
            <div
              key={fixture.match_id || fixture.id}
              className={`bg-white rounded-lg shadow-sm border p-5 ${
                isNext ? 'border-[#C41E3A] ring-2 ring-[#C41E3A]/20' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${locationClass}`}>
                      {fixture.is_home ? 'CASA' : 'FORA'}
                    </span>
                    <span className="text-sm text-gray-500 flex items-center gap-1">
                      <CalendarIcon size={14} />
                      {matchDate ? matchDate.toLocaleDateString('pt-PT', { day: '2-digit', month: 'short' }) : (fixture.date || 'TBD')}
                    </span>
                    <span className="text-sm text-gray-500 flex items-center gap-1">
                      <Clock size={14} />
                      {matchDate ? matchDate.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' }) : (fixture.time || 'TBD')}
                    </span>
                    {isNext && (
                      <span className="px-2 py-1 rounded text-xs font-bold bg-[#C41E3A] text-white">
                        PRÓXIMO
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex items-center gap-2">
                      <TeamBadge name={selectedTeamName} size={34} />
                      <div className="text-lg font-bold text-gray-900">{selectedTeamName}</div>
                    </div>
                    <div className="text-2xl font-bold text-gray-400">vs</div>
                    <div className="flex items-center gap-2">
                      <TeamBadge name={fixture.opponent_name} logo={fixture.opponent_logo} size={34} />
                      <div className="text-lg font-bold text-gray-900">{fixture.opponent_name}</div>
                    </div>
                  </div>

                  {!isUpcoming && fixture.score && (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-600">
                        {fixture.score?.display || fixture.score}
                      </span>
                      {fixture.result && (
                        <span className={`${resultClass} text-white px-2 py-0.5 rounded text-xs font-bold`}>
                          {fixture.result}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {isNext && (
                  <Link
                    to="/"
                    className="inline-flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-700 rounded-lg font-medium hover:bg-blue-200 transition-colors"
                    title="Ver análise do próximo adversário"
                  >
                    <Target size={18} />
                    Análise
                  </Link>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default Calendar
