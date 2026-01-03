import React, { useState } from 'react'
import { API_BASE_URL } from '../config/api'
import { useQuery } from '@tanstack/react-query'
import { Calendar, Target, TrendingUp, AlertTriangle, X, Shield, Users, Clock, Zap, Brain, BarChart } from 'lucide-react'
import AdvancedStatsPanel from '../components/AdvancedStatsPanel'

const Fixtures = () => {
  const [selectedMatch, setSelectedMatch] = useState(null)
  const [activeTab, setActiveTab] = useState('statistics')
  const [statistics, setStatistics] = useState(null)
  const [tacticalPlan, setTacticalPlan] = useState(null)
  const [loadingStats, setLoadingStats] = useState(false)
  const [loadingPlan, setLoadingPlan] = useState(false)
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['allFixtures'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/fixtures/all`)
      return res.json()
    }
  })

  const handleMatchClick = async (fixture) => {
    if (fixture.status === 'finished') return
    
    setSelectedMatch(fixture)
    setStatistics(null)
    setTacticalPlan(null)
    setActiveTab('statistics')
    
    // Load statistics
    setLoadingStats(true)
    try {
      const res = await fetch(
        ``${API_BASE_URL}`/api/v1/opponent-stats/${fixture.opponent_id}?opponent_name=${encodeURIComponent(fixture.opponent_name)}`
      )
      const data = await res.json()
      setStatistics(data)
    } catch (err) {
      console.error('Error fetching statistics:', err)
    } finally {
      setLoadingStats(false)
    }

    // Load tactical plan
    setLoadingPlan(true)
    try {
      const res = await fetch(
        ``${API_BASE_URL}`/api/v1/tactical-plan/${fixture.opponent_id}?opponent_name=${encodeURIComponent(fixture.opponent_name)}`
      )
      const data = await res.json()
      setTacticalPlan(data)
    } catch (err) {
      console.error('Error fetching tactical plan:', err)
    } finally {
      setLoadingPlan(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading fixtures...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-500 p-4">
        <p className="text-red-700">Error loading fixtures: {error.message}</p>
      </div>
    )
  }

  const fixtures = data?.fixtures || []
  const upcomingCount = data?.upcoming_count || 0

  // Tactical plan shape adapters (backend may return nested objects)
  const formationChangesRaw = tacticalPlan?.tactical_plan?.formation_recommendations?.suggested_changes
  const formationChanges = Array.isArray(formationChangesRaw)
    ? formationChangesRaw
    : (formationChangesRaw?.recommendations ?? [])

  const pressingRec = tacticalPlan?.tactical_plan?.pressing_strategy?.recommendation
  const pressingRecs = Array.isArray(pressingRec?.pressing_recommendations) ? pressingRec.pressing_recommendations : []
  const pressingFirst = pressingRecs[0]
  const pressingStyle = pressingRec?.style ?? pressingFirst?.adjustment ?? ''
  const pressingLineHeight = pressingRec?.line_height ?? pressingFirst?.target_line ?? ''
  const pressingRationale = pressingRec?.rationale ?? pressingFirst?.reason ?? ''

  const targetZonesRaw = tacticalPlan?.tactical_plan?.target_zones?.priority_zones
  const targetZones = Array.isArray(targetZonesRaw)
    ? targetZonesRaw
    : (targetZonesRaw?.priority_zones ?? [])

  const roleChangesRaw = tacticalPlan?.tactical_plan?.player_roles?.role_changes
  const roleChanges = Array.isArray(roleChangesRaw) ? roleChangesRaw : []

  const criticalWeaknessesRaw = tacticalPlan?.tactical_plan?.critical_weaknesses
  const criticalWeaknesses = Array.isArray(criticalWeaknessesRaw) ? criticalWeaknessesRaw : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Fixtures</h2>
          <p className="text-gray-600 mt-2">
            {upcomingCount} upcoming matches - Click upcoming fixtures for comprehensive analysis
          </p>
        </div>
        <div className="bg-blue-100 px-4 py-2 rounded-lg">
          <p className="text-sm text-blue-700 font-medium">Liga Portugal 2025/26</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {fixtures.map((fixture) => {
          const matchDate = new Date(`${fixture.date}T${fixture.time}`)
          const isUpcoming = fixture.status === 'upcoming'
          const locationClass = fixture.is_home ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'
          
          let resultClass = ''
          if (fixture.result === 'W') resultClass = 'bg-green-600'
          else if (fixture.result === 'D') resultClass = 'bg-yellow-500'
          else if (fixture.result === 'L') resultClass = 'bg-red-600'

          return (
            <div
              key={fixture.id}
              onClick={() => isUpcoming && handleMatchClick(fixture)}
              className={`bg-white rounded-lg p-4 shadow-md hover:shadow-lg transition-all border-2 ${
                isUpcoming ? 'cursor-pointer hover:border-blue-500 border-gray-200' : 'border-gray-100 opacity-75'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${locationClass}`}>
                      {fixture.is_home ? 'HOME' : 'AWAY'}
                    </span>
                    <span className="text-sm text-gray-500 flex items-center gap-1">
                      <Calendar size={14} />
                      {matchDate.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                    </span>
                    <span className="text-sm text-gray-500">
                      {matchDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="text-lg font-bold text-gray-900">
                      Gil Vicente
                    </div>
                    <div className="text-2xl font-bold text-gray-400">vs</div>
                    <div className="text-lg font-bold text-gray-900">
                      {fixture.opponent_name}
                    </div>
                  </div>

                  {!isUpcoming && fixture.score && (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-600">{fixture.score?.display || fixture.score}</span>
                      {fixture.result && (
                        <span className={`${resultClass} text-white px-2 py-0.5 rounded text-xs font-bold`}>
                          {fixture.result}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {isUpcoming && (
                  <div className="flex items-center gap-2">
                    <div className="bg-blue-100 text-blue-700 px-3 py-1 rounded-lg text-sm font-medium">
                      Analysis Available
                    </div>
                    <Target className="text-blue-600" size={24} />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Analysis Modal with Tabs */}
      {selectedMatch && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold">
                    Gil Vicente vs {selectedMatch.opponent_name}
                  </h3>
                  <p className="text-blue-100 mt-1">
                    {new Date(`${selectedMatch.date}T${selectedMatch.time}`).toLocaleDateString('en-GB', { 
                      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' 
                    })}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedMatch(null)}
                  className="bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full p-2 transition-colors"
                >
                  <X size={24} />
                </button>
              </div>

              {/* Tabs */}
              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => setActiveTab('statistics')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                    activeTab === 'statistics' 
                      ? 'bg-white text-blue-600' 
                      : 'bg-white bg-opacity-20 text-white hover:bg-opacity-30'
                  }`}
                >
                  <BarChart size={20} />
                  Statistics
                </button>
                <button
                  onClick={() => setActiveTab('tactical')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                    activeTab === 'tactical' 
                      ? 'bg-white text-purple-600' 
                      : 'bg-white bg-opacity-20 text-white hover:bg-opacity-30'
                  }`}
                >
                  <Brain size={20} />
                  Tactical Plan
                </button>
              </div>
            </div>

            <div className="p-6 max-h-[calc(90vh-200px)] overflow-y-auto">
              {/* Statistics Tab */}
              {activeTab === 'statistics' && (
                <div>
                  {loadingStats && (
                    <div className="text-center py-12">
                      <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
                      <p className="mt-4 text-gray-600">Loading statistics...</p>
                    </div>
                  )}

                  {statistics && !loadingStats && (
                    <div className="space-y-6">
                      {/* Overall Performance */}
                      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border-2 border-blue-200">
                        <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                          <TrendingUp size={24} className="text-blue-600" />
                          Overall Performance
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <p className="text-sm text-gray-600">Form</p>
                            <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.form_string}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Goals/Game</p>
                            <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.goals_per_game}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Conceded/Game</p>
                            <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.conceded_per_game}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Points/Game</p>
                            <p className="text-2xl font-bold text-gray-900">{statistics?.overall_performance?.points_per_game}</p>
                          </div>
                        </div>
                      </div>

                      {/* Home vs Away Split */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-green-50 rounded-lg p-5 border-2 border-green-200">
                          <h5 className="font-bold text-green-900 mb-3 flex items-center gap-2">
                            <Shield size={20} />
                            Home Performance
                          </h5>
                          {statistics?.home_performance?.matches > 0 ? (
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-700">Form:</span>
                                <span className="font-bold">{statistics?.home_performance?.form}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-700">Goals/Game:</span>
                                <span className="font-bold">{statistics?.home_performance?.goals_per_game}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-700">Conceded/Game:</span>
                                <span className="font-bold">{statistics?.home_performance?.conceded_per_game}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500">No home matches</p>
                          )}
                        </div>

                        <div className="bg-orange-50 rounded-lg p-5 border-2 border-orange-200">
                          <h5 className="font-bold text-orange-900 mb-3 flex items-center gap-2">
                            <Target size={20} />
                            Away Performance
                          </h5>
                          {statistics?.away_performance?.matches > 0 ? (
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-700">Form:</span>
                                <span className="font-bold">{statistics?.away_performance?.form}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-700">Goals/Game:</span>
                                <span className="font-bold">{statistics?.away_performance?.goals_per_game}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-700">Conceded/Game:</span>
                                <span className="font-bold">{statistics?.away_performance?.conceded_per_game}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500">No away matches</p>
                          )}
                        </div>
                      </div>

                      {/* Match Breakdown */}
                      <div className="bg-gray-50 rounded-lg p-6 border-2 border-gray-200">
                        <h4 className="text-xl font-bold text-gray-900 mb-4">Recent Matches</h4>
                        <div className="space-y-2">
                          {(statistics?.match_breakdown ?? []).slice(-5).reverse().map((match) => (
                            <div key={match.game_number} className="flex items-center justify-between bg-white rounded p-3 border">
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-medium text-gray-500">#{match.game_number}</span>
                                <span className="text-sm font-bold">vs {match.opponent}</span>
                                <span className={`text-xs px-2 py-1 rounded ${
                                  match.location === 'Home' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'
                                }`}>
                                  {match.location}
                                </span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-bold">{match.score}</span>
                                <span className={`px-2 py-1 rounded text-xs font-bold ${
                                  match.result === 'W' ? 'bg-green-600 text-white' :
                                  match.result === 'D' ? 'bg-yellow-500 text-white' :
                                  'bg-red-600 text-white'
                                }`}>
                                  {match.result}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Tactical-oriented detailed stats (shared with Opponents) */}
                      <AdvancedStatsPanel statistics={statistics} />



                      </div>
                    )}
                  </div>
                )}

              {/* Tactical Plan Tab */}
              {activeTab === 'tactical' && (
                <div>
                  {loadingPlan && (
                    <div className="text-center py-12">
                      <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-600 mx-auto"></div>
                      <p className="mt-4 text-gray-600">Generating tactical plan...</p>
                    </div>
                  )}

                  {tacticalPlan && !loadingPlan && (
                    <div className="space-y-6">
                      {/* AI Confidence Badge */}
                      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Brain size={32} />
                          <div>
                            <p className="text-sm opacity-90">AI-Powered Tactical Analysis</p>
                            <p className="text-lg font-bold">Confidence: {tacticalPlan.ai_confidence?.overall_confidence || tacticalPlan.ai_confidence?.score}%</p>
                          </div>
                        </div>
                        <div className="text-right text-sm opacity-90">
                          <p>{tacticalPlan.ai_confidence?.data_quality || tacticalPlan.ai_confidence?.reasoning}</p>
                        </div>
                      </div>

                      {/* Formation Recommendations */}
                      {formationChanges.length > 0 && (
                        <div className="bg-blue-50 rounded-lg p-6 border-2 border-blue-200">
                          <h4 className="text-xl font-bold text-blue-900 mb-4 flex items-center gap-2">
                            <Users size={24} />
                            Formation Recommendations
                          </h4>
                          {formationChanges.map((change, idx) => (
                            <div key={idx} className="mb-4 last:mb-0">
                              <p className="font-bold text-lg text-blue-900">{change.formation || change.current_formation || ""}</p>
                              <p className="text-gray-700 mt-1">{change.reason || ""}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Pressing Strategy */}
                      {(pressingStyle || pressingLineHeight || pressingRationale) && (
                        <div className="bg-red-50 rounded-lg p-6 border-2 border-red-200">
                          <h4 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
                            <Zap size={24} />
                            Pressing Strategy
                          </h4>
                          <div className="space-y-2">
                            <div>
                              <span className="font-bold text-red-900">Style: </span>
                              <span className="text-gray-700">{pressingStyle}</span>
                            </div>
                            <div>
                              <span className="font-bold text-red-900">Line Height: </span>
                              <span className="text-gray-700">{pressingLineHeight}</span>
                            </div>
                            <p className="text-gray-700 mt-3">{pressingRationale}</p>
                          {Array.isArray(pressingRecs) && pressingRecs.length > 0 && (
                            <div className="mt-4 space-y-2">
                              {pressingRecs.map((r, idx) => (
                                <div key={idx} className="bg-white rounded-lg p-3 border border-red-200">
                                  <p className="font-bold text-red-900">{r.adjustment} · {r.target_line}</p>
                                  <p className="text-gray-700 text-sm mt-1">{r.reason}</p>
                                </div>
                              ))}
                            </div>
                          )}
                          </div>
                        </div>
                      )}

                      {/* Target Zones */}
                      {targetZones.length > 0 && (
                        <div className="bg-green-50 rounded-lg p-6 border-2 border-green-200">
                          <h4 className="text-xl font-bold text-green-900 mb-4 flex items-center gap-2">
                            <Target size={24} />
                            Priority Attack Zones
                          </h4>
                          {targetZones.map((zone, idx) => (
                            <div key={idx} className="mb-3 last:mb-0">
                              <p className="font-bold text-green-900">{zone.zone}</p>
                              <p className="text-gray-700">{zone.reasoning || zone.attack_method || zone.expected_outcome || ""}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Player Roles */}
                      {roleChanges.length > 0 && (
                        <div className="bg-indigo-50 rounded-lg p-6 border-2 border-indigo-200">
                          <h4 className="text-xl font-bold text-indigo-900 mb-4 flex items-center gap-2">
                            <Users size={24} />
                            Player Role Changes
                          </h4>
                          {roleChanges.map((role, idx) => (
                            <div key={idx} className="mb-3 last:mb-0">
                              <p className="font-bold text-indigo-900">{role.position}: {role.role || role.role_change || ""}</p>
                              <p className="text-gray-700">{role.reasoning || role.reason || ""}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Critical Weaknesses */}
                      {criticalWeaknesses.length > 0 && (
                        <div className="bg-red-100 rounded-lg p-6 border-2 border-red-300">
                          <h4 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
                            <AlertTriangle size={24} />
                            Critical Weaknesses to Exploit
                          </h4>
                          {criticalWeaknesses.map((weakness, idx) => (
                            <div key={idx} className="mb-4 last:mb-0">
                              <div className="flex items-center gap-2 mb-2">
                                <span className={`px-3 py-1 rounded text-xs font-bold ${
                                  weakness.severity === 'CRITICAL' ? 'bg-red-700 text-white' : 
                                  weakness.severity === 'HIGH' ? 'bg-orange-600 text-white' : 
                                  'bg-yellow-600 text-white'
                                }`}>
                                  {weakness.severity}
                                </span>
                                <span className="font-bold text-red-900">{weakness.weakness}</span>
                              </div>
                              <p className="text-gray-700">{weakness.tactical_approach || weakness.exploitation || weakness.expected_impact || ""}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Fixtures