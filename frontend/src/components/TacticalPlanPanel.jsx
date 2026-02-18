import React from 'react'
import { Brain, Users, Zap, Target, AlertTriangle, Clock, Shuffle } from 'lucide-react'

const pct = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return null
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return null
  return Math.round(n)
}

const safeArr = (v) => (Array.isArray(v) ? v : [])

const TacticalPlanPanel = ({ tacticalPlan }) => {
  if (!tacticalPlan) return null

  const titleOpponent = tacticalPlan?.opponent || 'Opponent'
  const confidence = pct(tacticalPlan?.ai_confidence?.overall_confidence || tacticalPlan?.ai_confidence?.score)
  const adjustedConfidence = pct(tacticalPlan?.confidence_adjustment?.adjusted_confidence)
  const confidenceReliability = tacticalPlan?.confidence_adjustment?.recommendation_reliability
  const baselineSeason = tacticalPlan?.historical_context?.baseline_season
  const validationNote = tacticalPlan?.historical_context?.validation_note
  const seasonComparison = tacticalPlan?.historical_context?.season_comparison || {}

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
  const targetZones = Array.isArray(targetZonesRaw) ? targetZonesRaw : (targetZonesRaw?.priority_zones ?? [])

  const roleChangesRaw = tacticalPlan?.tactical_plan?.player_roles?.role_changes
  const roleChanges = Array.isArray(roleChangesRaw) ? roleChangesRaw : []

  const criticalWeaknessesRaw = tacticalPlan?.tactical_plan?.critical_weaknesses
  const criticalWeaknesses = Array.isArray(criticalWeaknessesRaw) ? criticalWeaknessesRaw : []

  const gamePhases = tacticalPlan?.tactical_plan?.game_phases || {}
  const subsRaw = tacticalPlan?.tactical_plan?.substitution_strategy?.recommendations
  const subs = safeArr(subsRaw)

  const switchesRaw = tacticalPlan?.tactical_plan?.in_game_switches?.recommendations
  const switches = safeArr(switchesRaw)

  const dataSource = tacticalPlan?.data_source
  const cacheInfo = tacticalPlan?.cache_info
  const custom = tacticalPlan?.customized_suggestions || {}
  const customSystem = safeArr(custom?.recommended_system)
  const customAttackZones = safeArr(custom?.attack_zones)
  const customVulnerabilities = safeArr(custom?.defensive_vulnerabilities)
  const customNeutralize = safeArr(custom?.neutralize_strengths)
  const customSetPieces = safeArr(custom?.set_piece_adjustments)
  const llmNarrative = tacticalPlan?.language_generation?.narrative

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg p-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Brain size={32} />
            <div>
              <p className="text-sm opacity-90">{titleOpponent}</p>
              <p className="text-lg font-bold">
                Confiança: {confidence !== null ? `${confidence}%` : 'N/A'}
              </p>
              {adjustedConfidence !== null && (
                <p className="text-sm opacity-95">
                  Confiança ajustada: {adjustedConfidence}% {confidenceReliability ? `(${confidenceReliability})` : ''}
                </p>
              )}
            </div>
          </div>
          <div className="text-right text-sm opacity-90">
            {tacticalPlan?.ai_confidence?.data_quality && <p>{tacticalPlan.ai_confidence.data_quality}</p>}
            {tacticalPlan?.ai_confidence?.recommendation_reliability && <p>Fiabilidade: {tacticalPlan.ai_confidence.recommendation_reliability}</p>}
            {baselineSeason && <p>Base histórica: {baselineSeason}</p>}
            {(dataSource || cacheInfo) && (
              <p className="mt-1">
                <span className="font-semibold">Fonte:</span> {dataSource || 'N/A'}
                {cacheInfo ? ` · ${cacheInfo}` : ''}
              </p>
            )}
          </div>
        </div>
      </div>

      {(customSystem.length > 0 ||
        customAttackZones.length > 0 ||
        customVulnerabilities.length > 0 ||
        customNeutralize.length > 0 ||
        customSetPieces.length > 0) && (
        <div className="bg-white rounded-lg p-6 border shadow-sm space-y-5">
          <h4 className="text-xl font-bold text-gray-900">Sugestões táticas personalizadas</h4>

          {customSystem.length > 0 && (
            <div>
              <p className="font-semibold text-gray-900 mb-2">Sistema de jogo recomendado</p>
              <div className="space-y-2">
                {customSystem.map((item, idx) => (
                  <div key={idx} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="font-bold text-blue-900">{item.title || '—'}</p>
                    <p className="text-gray-700 mt-1">{item.detail || ''}</p>
                    {item.note && <p className="text-xs text-blue-800 mt-2">{item.note}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {customAttackZones.length > 0 && (
            <div>
              <p className="font-semibold text-gray-900 mb-2">Zonas a explorar no ataque</p>
              <div className="space-y-2">
                {customAttackZones.map((item, idx) => (
                  <div key={idx} className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="font-bold text-green-900">{item.title || '—'}</p>
                    <p className="text-gray-700 mt-1">{item.detail || ''}</p>
                    {item.note && <p className="text-xs text-green-800 mt-2">{item.note}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {customVulnerabilities.length > 0 && (
            <div>
              <p className="font-semibold text-gray-900 mb-2">Vulnerabilidades defensivas identificadas</p>
              <div className="space-y-2">
                {customVulnerabilities.map((item, idx) => (
                  <div key={idx} className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="font-bold text-red-900">{item.title || '—'}</p>
                    <p className="text-gray-700 mt-1">{item.detail || ''}</p>
                    {item.note && <p className="text-xs text-red-800 mt-2">{item.note}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {customNeutralize.length > 0 && (
            <div>
              <p className="font-semibold text-gray-900 mb-2">Como neutralizar os pontos fortes</p>
              <div className="space-y-2">
                {customNeutralize.map((item, idx) => (
                  <div key={idx} className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <p className="font-bold text-amber-900">{item.title || '—'}</p>
                    <p className="text-gray-700 mt-1">{item.detail || ''}</p>
                    {item.note && <p className="text-xs text-amber-800 mt-2">{item.note}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {customSetPieces.length > 0 && (
            <div>
              <p className="font-semibold text-gray-900 mb-2">Ajustes em bolas paradas</p>
              <div className="space-y-2">
                {customSetPieces.map((item, idx) => (
                  <div key={idx} className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                    <p className="font-bold text-indigo-900">{item.title || '—'}</p>
                    <p className="text-gray-700 mt-1">{item.detail || ''}</p>
                    {item.note && <p className="text-xs text-indigo-800 mt-2">{item.note}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {(seasonComparison?.current_observed_profile || validationNote) && (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm text-slate-700">
              {validationNote && <p>{validationNote}</p>}
              {seasonComparison?.current_observed_profile?.sample_size && (
                <p className="mt-1">
                  Observações atuais: {seasonComparison.current_observed_profile.sample_size}
                </p>
              )}
            </div>
          )}

          {llmNarrative?.summary && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
              <p className="font-semibold text-purple-900">Resumo textual</p>
              <p className="text-gray-700 mt-1">{llmNarrative.summary}</p>
            </div>
          )}
        </div>
      )}

      {formationChanges.length > 0 && (
        <div className="bg-blue-50 rounded-lg p-6 border-2 border-blue-200">
          <h4 className="text-xl font-bold text-blue-900 mb-4 flex items-center gap-2">
            <Users size={24} />
            Recomendações de formação
          </h4>
          <div className="space-y-3">
            {formationChanges.map((change, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-blue-200">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold text-lg text-blue-900">
                    {change.formation || change.current_formation || '—'}
                  </p>
                  {change.priority && (
                    <span className="px-2 py-1 rounded text-xs font-bold bg-blue-700 text-white">
                      {change.priority}
                    </span>
                  )}
                </div>
                {change.reason && <p className="text-gray-700 mt-1">{change.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {(pressingStyle || pressingLineHeight || pressingRationale || pressingRecs.length > 0) && (
        <div className="bg-red-50 rounded-lg p-6 border-2 border-red-200">
          <h4 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
            <Zap size={24} />
            Estratégia de pressão
          </h4>
          <div className="space-y-2">
            {(pressingStyle || '').length > 0 && (
              <div>
                <span className="font-bold text-red-900">Estilo: </span>
                <span className="text-gray-700">{pressingStyle}</span>
              </div>
            )}
            {(pressingLineHeight || '').length > 0 && (
              <div>
                <span className="font-bold text-red-900">Altura da linha: </span>
                <span className="text-gray-700">{pressingLineHeight}</span>
              </div>
            )}
            {(pressingRationale || '').length > 0 && <p className="text-gray-700 mt-3">{pressingRationale}</p>}

            {pressingRecs.length > 0 && (
              <div className="mt-4 space-y-2">
                {pressingRecs.map((r, idx) => (
                  <div key={idx} className="bg-white rounded-lg p-3 border border-red-200">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-bold text-red-900">{r.adjustment} · {r.target_line}</p>
                      {r.priority && (
                        <span className="px-2 py-1 rounded text-xs font-bold bg-red-700 text-white">
                          {r.priority}
                        </span>
                      )}
                    </div>
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
            Zonas prioritárias para atacar
          </h4>
          <div className="space-y-3">
            {targetZones.map((zone, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-green-200">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold text-green-900">{zone.zone || '—'}</p>
                  {zone.priority && (
                    <span className="px-2 py-1 rounded text-xs font-bold bg-green-700 text-white">
                      {zone.priority}
                    </span>
                  )}
                </div>
                <p className="text-gray-700 mt-1">
                  {zone.reasoning || zone.attack_method || zone.expected_outcome || ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {roleChanges.length > 0 && (
        <div className="bg-indigo-50 rounded-lg p-6 border-2 border-indigo-200">
          <h4 className="text-xl font-bold text-indigo-900 mb-4 flex items-center gap-2">
            <Users size={24} />
            Ajustes de papéis
          </h4>
          <div className="space-y-3">
            {roleChanges.map((role, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-indigo-200">
                <p className="font-bold text-indigo-900">
                  {role.position || '—'}: {role.role || role.role_change || role.roleChange || ''}
                </p>
                <p className="text-gray-700 mt-1">{role.reasoning || role.reason || ''}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {(gamePhases?.in_possession || gamePhases?.out_possession || gamePhases?.transitions) && (
        <div className="bg-white rounded-lg p-6 border shadow-sm">
          <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Clock size={22} className="text-gray-700" />
            Plano por fases do jogo
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 rounded-lg p-4 border">
              <p className="text-sm font-semibold text-gray-900">Com bola</p>
              <p className="text-gray-700 mt-2">{gamePhases?.in_possession || '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border">
              <p className="text-sm font-semibold text-gray-900">Sem bola</p>
              <p className="text-gray-700 mt-2">{gamePhases?.out_possession || '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border">
              <p className="text-sm font-semibold text-gray-900">Transições</p>
              <p className="text-gray-700 mt-2">{gamePhases?.transitions || '—'}</p>
            </div>
          </div>
        </div>
      )}

      {subs.length > 0 && (
        <div className="bg-yellow-50 rounded-lg p-6 border-2 border-yellow-200">
          <h4 className="text-xl font-bold text-yellow-900 mb-4 flex items-center gap-2">
            <Clock size={22} />
            Substituições (timing)
          </h4>
          <div className="space-y-2">
            {subs.map((s, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-yellow-200">
                <p className="font-bold text-yellow-900">{s.timing || '—'} · {s.type || '—'}</p>
                {s.reason && <p className="text-gray-700 mt-1">{s.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {switches.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-6 border-2 border-gray-200">
          <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Shuffle size={22} className="text-gray-700" />
            Mudanças durante o jogo
          </h4>
          <div className="space-y-2">
            {switches.map((s, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="font-bold text-gray-900">{s.trigger || '—'}</p>
                <p className="text-gray-700 mt-1">
                  <span className="font-semibold">Switch:</span> {s.switch || '—'} ·{' '}
                  <span className="font-semibold">Timing:</span> {s.timing || '—'}
                </p>
                {s.reason && <p className="text-gray-700 mt-1">{s.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {criticalWeaknesses.length > 0 && (
        <div className="bg-red-100 rounded-lg p-6 border-2 border-red-300">
          <h4 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
            <AlertTriangle size={24} />
            Fragilidades a explorar
          </h4>
          <div className="space-y-3">
            {criticalWeaknesses.map((weakness, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-red-200">
                <div className="flex items-center gap-2 mb-2">
                  {weakness.severity && (
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
                  )}
                  <span className="font-bold text-red-900">{weakness.weakness || '—'}</span>
                </div>
                <p className="text-gray-700">
                  {weakness.tactical_approach || weakness.exploitation || weakness.expected_impact || ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default TacticalPlanPanel
