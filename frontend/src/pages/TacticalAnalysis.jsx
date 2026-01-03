import React from 'react'
import { API_BASE_URL } from '../config/api'
import { useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Brain, Users, Zap, Target, AlertTriangle } from 'lucide-react'

const TacticalAnalysis = () => {
  const { teamId } = useParams()
  const [searchParams] = useSearchParams()
  const opponentName = searchParams.get('opponent_name') || searchParams.get('opponentName')

  const {
    data: tacticalPlan,
    isLoading,
    error
  } = useQuery({
    queryKey: ['tactical-plan', teamId, opponentName],
    queryFn: async () => {
      const res = await fetch(
        ``${API_BASE_URL}`/api/v1/tactical-plan/${teamId}?opponent_name=${encodeURIComponent(opponentName)}`
      )
      if (!res.ok) {
        const detail = await res.text().catch(() => '')
        throw new Error(detail || `Request failed: ${res.status}`)
      }
      return res.json()
    },
    enabled: !!teamId && !!opponentName
  })

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
  const targetZones = Array.isArray(targetZonesRaw) ? targetZonesRaw : (targetZonesRaw?.priority_zones ?? [])

  const roleChangesRaw = tacticalPlan?.tactical_plan?.player_roles?.role_changes
  const roleChanges = Array.isArray(roleChangesRaw) ? roleChangesRaw : []

  const criticalWeaknessesRaw = tacticalPlan?.tactical_plan?.critical_weaknesses
  const criticalWeaknesses = Array.isArray(criticalWeaknessesRaw) ? criticalWeaknessesRaw : []

  const titleOpponent = tacticalPlan?.opponent || opponentName || 'Opponent'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Tactical Analysis</h2>
        <p className="text-gray-600 mt-2">AI-driven match plan and exploitable weaknesses</p>
      </div>

      {!opponentName && (
        <div className="tactical-card">
          <p className="text-gray-700">
            Missing opponent name. Open this page with{' '}
            <span className="font-mono text-sm">?opponent_name=Team%20Name</span>.
          </p>
        </div>
      )}

      {isLoading && (
        <div className="tactical-card text-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Generating tactical plan...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <p className="text-red-700">Error loading tactical plan: {String(error.message || error)}</p>
        </div>
      )}

      {tacticalPlan && !isLoading && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Brain size={32} />
                <div>
                  <p className="text-sm opacity-90">{titleOpponent}</p>
                  <p className="text-lg font-bold">
                    Confidence: {tacticalPlan.ai_confidence?.overall_confidence || tacticalPlan.ai_confidence?.score}%
                  </p>
                </div>
              </div>
              <div className="text-right text-sm opacity-90">
                <p>{tacticalPlan.ai_confidence?.data_quality || tacticalPlan.ai_confidence?.reasoning}</p>
              </div>
            </div>
          </div>

          {formationChanges.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-6 border-2 border-blue-200">
              <h4 className="text-xl font-bold text-blue-900 mb-4 flex items-center gap-2">
                <Users size={24} />
                Formation Recommendations
              </h4>
              {formationChanges.map((change, idx) => (
                <div key={idx} className="mb-4 last:mb-0">
                  <p className="font-bold text-lg text-blue-900">{change.formation || change.current_formation || ''}</p>
                  <p className="text-gray-700 mt-1">{change.reason || ''}</p>
                </div>
              ))}
            </div>
          )}

          {(pressingStyle || pressingLineHeight || pressingRationale) && (
            <div className="bg-red-50 rounded-lg p-6 border-2 border-red-200">
              <h4 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
                <Zap size={24} />
                Pressing Strategy
              </h4>
              <div className="space-y-2">
                {(pressingStyle || '').length > 0 && (
                  <div>
                    <span className="font-bold text-red-900">Style: </span>
                    <span className="text-gray-700">{pressingStyle}</span>
                  </div>
                )}
                {(pressingLineHeight || '').length > 0 && (
                  <div>
                    <span className="font-bold text-red-900">Line Height: </span>
                    <span className="text-gray-700">{pressingLineHeight}</span>
                  </div>
                )}
                {(pressingRationale || '').length > 0 && <p className="text-gray-700 mt-3">{pressingRationale}</p>}

                {pressingRecs.length > 0 && (
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

          {targetZones.length > 0 && (
            <div className="bg-green-50 rounded-lg p-6 border-2 border-green-200">
              <h4 className="text-xl font-bold text-green-900 mb-4 flex items-center gap-2">
                <Target size={24} />
                Priority Attack Zones
              </h4>
              {targetZones.map((zone, idx) => (
                <div key={idx} className="mb-3 last:mb-0">
                  <p className="font-bold text-green-900">{zone.zone}</p>
                  <p className="text-gray-700">{zone.reasoning || zone.attack_method || zone.expected_outcome || ''}</p>
                </div>
              ))}
            </div>
          )}

          {roleChanges.length > 0 && (
            <div className="bg-indigo-50 rounded-lg p-6 border-2 border-indigo-200">
              <h4 className="text-xl font-bold text-indigo-900 mb-4 flex items-center gap-2">
                <Users size={24} />
                Player Role Changes
              </h4>
              {roleChanges.map((role, idx) => (
                <div key={idx} className="mb-3 last:mb-0">
                  <p className="font-bold text-indigo-900">{role.position}: {role.role || role.role_change || ''}</p>
                  <p className="text-gray-700">{role.reasoning || role.reason || ''}</p>
                </div>
              ))}
            </div>
          )}

          {criticalWeaknesses.length > 0 && (
            <div className="bg-red-100 rounded-lg p-6 border-2 border-red-300">
              <h4 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
                <AlertTriangle size={24} />
                Critical Weaknesses to Exploit
              </h4>
              {criticalWeaknesses.map((weakness, idx) => (
                <div key={idx} className="mb-4 last:mb-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`px-3 py-1 rounded text-xs font-bold ${
                        weakness.severity === 'CRITICAL'
                          ? 'bg-red-700 text-white'
                          : weakness.severity === 'HIGH'
                            ? 'bg-orange-600 text-white'
                            : 'bg-yellow-600 text-white'
                      }`}
                    >
                      {weakness.severity}
                    </span>
                    <span className="font-bold text-red-900">{weakness.weakness}</span>
                  </div>
                  <p className="text-gray-700">
                    {weakness.tactical_approach || weakness.exploitation || weakness.expected_impact || ''}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TacticalAnalysis
