import React, { useMemo, useState } from 'react'
import { API_BASE_URL } from '../config/api'
import { useQuery } from '@tanstack/react-query'
import { Users, TrendingUp, TrendingDown, Activity, Target, Shield, Zap } from 'lucide-react'
import AdvancedStatsPanel from '../components/AdvancedStatsPanel'

const Opponents = () => {
  const [selectedOpponent, setSelectedOpponent] = useState(null)

  const { data: opponentsData, isLoading: opponentsLoading } = useQuery({
    queryKey: ['opponents'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/opponents`)
      return res.json()
    }
  })

  const opponents = opponentsData?.opponents || []

  const selectedOpponentObj = useMemo(() => {
    if (!selectedOpponent) return null
    return opponents.find((o) => String(o.id) === String(selectedOpponent)) || null
  }, [opponents, selectedOpponent])

  const selectedOpponentName = selectedOpponentObj?.name

  const { data: tacticalData, isLoading: tacticalLoading } = useQuery({
    queryKey: ['opponent-tactical', selectedOpponent],
    queryFn: async () => {
      if (!selectedOpponent) return null
      const res = await fetch(``${API_BASE_URL}`/api/v1/opponents/${selectedOpponent}/tactical`)
      if (!res.ok) return null
      return res.json()
    },
    enabled: !!selectedOpponent
  })

  const { data: formData } = useQuery({
    queryKey: ['opponent-form', selectedOpponent],
    queryFn: async () => {
      if (!selectedOpponent) return null
      const res = await fetch(``${API_BASE_URL}`/api/v1/opponents/${selectedOpponent}/recent`)
      if (!res.ok) return null
      return res.json()
    },
    enabled: !!selectedOpponent
  })

  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['opponent-stats', selectedOpponent],
    queryFn: async () => {
      if (!selectedOpponent || !selectedOpponentName) return null
      const res = await fetch(
        ``${API_BASE_URL}`/api/v1/opponent-stats/${selectedOpponent}?opponent_name=${encodeURIComponent(selectedOpponentName)}`
      )
      return res.json()
    },
    enabled: !!selectedOpponent && !!selectedOpponentName
  })


  const formation = tacticalData?.formation || 'N/A'
  const playingStyle = tacticalData?.playing_style || 'N/A'
  const strengths = Array.isArray(tacticalData?.strengths) ? tacticalData.strengths : []
  const weaknesses = Array.isArray(tacticalData?.weaknesses) ? tacticalData.weaknesses : []
  const recommendations = Array.isArray(tacticalData?.recommendations) ? tacticalData.recommendations : []

  const form = formData?.form ?? '—'
  const winRate = formData?.statistics?.form_percentage ?? '—'
  const goalsFor = formData?.statistics?.goals_scored ?? '—'
  const goalsAgainst = formData?.statistics?.goals_conceded ?? '—'
  if (opponentsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading opponents...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Opponent Analysis</h2>
        <p className="text-gray-600 mt-2">Tactical intelligence and scouting reports</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Opponents List */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Select Opponent</h3>
          {opponents.map((opponent) => (
            <div
              key={opponent.id}
              onClick={() => setSelectedOpponent(opponent.id)}
              className={`tactical-card cursor-pointer transition-all duration-200 ${
                selectedOpponent === opponent.id
                  ? 'bg-blue-600 text-white shadow-lg scale-105'
                  : 'hover:bg-blue-50 hover:shadow-md'
              }`}
            >
              <div className="flex items-center gap-3">
                <Users size={24} className={selectedOpponent === opponent.id ? 'text-white' : 'text-blue-600'} />
                <div>
                  <p className="font-semibold">{opponent.name}</p>
                  <p className={`text-sm ${selectedOpponent === opponent.id ? 'text-blue-100' : 'text-gray-500'}`}>
                    ID: {opponent.id}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Opponent Details */}
        <div className="lg:col-span-2">
          {!selectedOpponent ? (
            <div className="tactical-card text-center py-20">
              <Users className="mx-auto text-gray-400 mb-4" size={64} />
              <p className="text-gray-600 text-lg">Select an opponent to view analysis</p>
            </div>
          ) : (tacticalLoading || statsLoading) ? (
            <div className="tactical-card text-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading analysis...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Team Header */}
              <div className="tactical-card bg-gradient-to-r from-blue-600 to-blue-800 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold">{tacticalData?.team?.name || selectedOpponentName}</h3>
                    <p className="text-blue-100">Tactical Profile</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-blue-100">Formation</p>
                    <p className="text-3xl font-bold">{formation}</p>
                  </div>
                </div>
              </div>

              {/* Recent Form */}
              {formData && (
                <div className="tactical-card bg-green-50 border-l-4 border-green-500">
                  <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                    <Activity className="text-green-600" size={24} />
                    Recent Form
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white p-3 rounded-lg">
                      <p className="text-sm text-gray-600">Form</p>
                      <p className="text-2xl font-bold text-gray-900">{form}</p>
                    </div>
                    <div className="bg-white p-3 rounded-lg">
                      <p className="text-sm text-gray-600">Win Rate</p>
                      <p className="text-2xl font-bold text-green-600">{winRate}%</p>
                    </div>
                    <div className="bg-white p-3 rounded-lg">
                      <p className="text-sm text-gray-600">Goals For</p>
                      <p className="text-2xl font-bold text-blue-600">{goalsFor}</p>
                    </div>
                    <div className="bg-white p-3 rounded-lg">
                      <p className="text-sm text-gray-600">Goals Against</p>
                      <p className="text-2xl font-bold text-red-600">{goalsAgainst}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* NEW: Rich opponent stats (reused in Fixtures) */}
              {statsLoading ? (
                <div className="tactical-card text-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-purple-600 mx-auto"></div>
                  <p className="mt-4 text-gray-600">Loading detailed statistics...</p>
                </div>
              ) : (
                <AdvancedStatsPanel statistics={statsData} />
              )}

              {/* Playing Style */}
              <div className="tactical-card bg-purple-50 border-l-4 border-purple-500">
                <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                  <Zap className="text-purple-600" size={24} />
                  Playing Style
                </h4>
                <p className="text-gray-700 text-lg">{playingStyle}</p>
              </div>

              {/* Strengths */}
              <div className="tactical-card bg-blue-50 border-l-4 border-blue-500">
                <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                  <TrendingUp className="text-blue-600" size={24} />
                  Strengths
                </h4>
                <ul className="space-y-2">
                  {strengths.length > 0 ? (
                  strengths.map((strength, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-blue-600 mt-1">✓</span>
                      <span className="text-gray-700">{strength}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-gray-700">N/A</li>
                )}
              </ul>
              </div>

              {/* Weaknesses */}
              <div className="tactical-card bg-red-50 border-l-4 border-red-500">
                <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                  <TrendingDown className="text-red-600" size={24} />
                  Weaknesses
                </h4>
                <ul className="space-y-2">
                  {weaknesses.length > 0 ? (
                  weaknesses.map((weakness, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-red-600 mt-1">⚠</span>
                      <span className="text-gray-700">{weakness}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-gray-700">N/A</li>
                )}
              </ul>
              </div>

              {/* Recommendations */}
              <div className="tactical-card bg-gradient-to-r from-green-600 to-green-800 text-white">
                <h4 className="font-bold text-xl mb-4 flex items-center gap-2">
                  <Target size={24} />
                  Tactical Recommendations
                </h4>
                <ul className="space-y-3">
                  {recommendations.length > 0 ? (
                  recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-3">
                      <Shield size={20} className="mt-1 flex-shrink-0" />
                      <span className="text-green-50">{rec}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-green-50">N/A</li>
                )}
              </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Opponents
