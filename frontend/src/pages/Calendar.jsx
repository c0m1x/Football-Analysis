import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { API_BASE_URL } from '../config/api'
import { Calendar as CalendarIcon, Clock, Target, RefreshCw } from 'lucide-react'
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

const Calendar = () => {
  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['allFixtures'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/fixtures/all`)
      if (!res.ok) throw new Error(await toErrorText(res))
      const json = await res.json()
      if (json?.data_source === 'error' && json?.error) throw new Error(String(json.error))
      return json
    },
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">A carregar calendário…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <p className="text-red-700">Erro a carregar calendário: {String(error.message || error)}</p>
        </div>
        <button
          onClick={() => refetch()}
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
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarIcon className="text-[#003C71]" size={28} />
            Calendário
          </h2>
          <p className="text-gray-600 mt-2">
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
            disabled={isFetching}
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
                      <TeamBadge name="Gil Vicente" size={34} />
                      <div className="text-lg font-bold text-gray-900">Gil Vicente</div>
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
