import React from 'react'
import { BarChart3, Shield, Target, Zap, Map, Brain, LineChart, Flag } from 'lucide-react'

const fmt = (value, digits = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  if (typeof value === 'number') return value.toFixed(digits)
  return String(value)
}

const fmtInt = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  if (typeof value === 'number') return String(Math.round(value))
  return String(value)
}

const fmtPct = (value, digits = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  if (typeof value === 'number') return `${value.toFixed(digits)}%`
  return String(value)
}

const pickInsights = (recentGames) => {
  const latest = recentGames?.[0]
  const insights = [
    latest?.possession_control?.tactical_insight,
    latest?.shooting_finishing?.tactical_insight,
    latest?.pressing_structure?.tactical_insight
  ].filter(Boolean)
  // de-dupe
  return Array.from(new Set(insights))
}

const AdvancedStatsPanel = ({ statistics }) => {
  if (!statistics) return null

  const foundation = statistics?.tactical_foundation
  const recentGames = statistics?.recent_games_tactical || []
  const setPieces = statistics?.set_piece_analytics
  const ctx = statistics?.contextual_psychological
  const historicalContext = statistics?.historical_context

  const scorelineDist = ctx?.scoreline_state_distribution || {}
  const scorelineMode = Object.keys(scorelineDist).sort((a, b) => (scorelineDist[b] || 0) - (scorelineDist[a] || 0))[0]

  const pc = foundation?.possession_control
  const sf = foundation?.shooting_finishing
  const xm = foundation?.expected_metrics
  const cc = foundation?.chance_creation
  const da = foundation?.defensive_actions
  const ps = foundation?.pressing_structure
  const ts = foundation?.team_shape

  const insights = pickInsights(recentGames)

  return (
    <div className="space-y-6">
      <div className="tactical-card bg-white">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h4 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <BarChart3 size={22} className="text-blue-600" />
              Tactical Foundation Stats
            </h4>
            <p className="text-gray-600 mt-1">
              {foundation?.estimated ? 'Estimated from available match context (score/home-away).' : 'From match data.'}
            </p>
            {historicalContext?.validation_note && (
              <p className="text-sm text-amber-800 mt-2">
                {historicalContext.validation_note}
              </p>
            )}
          </div>
          <div className="text-sm text-gray-500 text-right">
            <p>Matches: {foundation?.matches_analyzed ?? recentGames.length ?? 0}</p>
          </div>
        </div>

        {insights.length > 0 && (
          <div className="mt-4 bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
            <p className="font-semibold text-blue-900">Tactical insight (latest match)</p>
            <ul className="mt-2 space-y-1">
              {insights.map((t, idx) => (
                <li key={idx} className="text-gray-700">• {t}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Possession & Control */}
      <div className="tactical-card bg-blue-50 border-l-4 border-blue-500">
        <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
          <Zap className="text-blue-600" size={22} />
          Possession & Control
        </h5>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Possession</p>
            <p className="text-2xl font-bold text-gray-900">{fmtPct(pc?.possession_percent_avg)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Time in opp. half</p>
            <p className="text-2xl font-bold text-gray-900">{fmtPct(pc?.time_in_opponent_half_avg)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Pass accuracy</p>
            <p className="text-2xl font-bold text-gray-900">{fmtPct(pc?.pass_accuracy_avg)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Passes / minute</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(pc?.passes_per_minute_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Long balls (att.)</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(pc?.long_balls_attempted_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Long balls (comp.)</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(pc?.long_balls_completed_avg, 1)}</p>
          </div>
        </div>
      </div>

      {/* Shooting & Finishing */}
      <div className="tactical-card bg-purple-50 border-l-4 border-purple-500">
        <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
          <Target className="text-purple-600" size={22} />
          Shooting & Finishing
        </h5>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Total shots</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(sf?.total_shots_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Shots on target</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(sf?.shots_on_target_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Conversion rate</p>
            <p className="text-2xl font-bold text-gray-900">{fmtPct(sf?.shot_conversion_rate_avg)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Big chances (created)</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(sf?.big_chances_created_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Big chances (missed)</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(sf?.big_chances_missed_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Shots inside box</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(sf?.shots_inside_box_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Shots outside box</p>
            <p className="text-2xl font-bold text-gray-900">{fmt(sf?.shots_outside_box_avg, 1)}</p>
          </div>
        </div>
      </div>

      {/* Expected Metrics + Chance Creation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="tactical-card bg-green-50 border-l-4 border-green-500">
          <h5 className="font-bold text-lg mb-3">Expected metrics</h5>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">xG</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(xm?.xG_avg, 2)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">xG / shot</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(xm?.xG_per_shot_avg, 3)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">xG open play</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(xm?.xG_from_open_play_avg, 2)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">xG set pieces</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(xm?.xG_from_set_pieces_avg, 2)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">xA</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(xm?.xA_avg, 2)}</p>
            </div>
          </div>
        </div>

        <div className="tactical-card bg-indigo-50 border-l-4 border-indigo-500">
          <h5 className="font-bold text-lg mb-3">Chance creation</h5>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Key passes</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.key_passes_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Progressive passes</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.progressive_passes_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Passes into final third</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.passes_into_final_third_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Passes into penalty area</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.passes_into_penalty_area_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Crosses (att.)</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.crosses_attempted_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Crosses (acc.)</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.crosses_accurate_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Cutbacks</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(cc?.cutbacks_avg, 1)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Defensive + Pressing */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="tactical-card bg-red-50 border-l-4 border-red-500">
          <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
            <Shield className="text-red-600" size={22} />
            Defensive actions
          </h5>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Tackles (att.)</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(da?.tackles_attempted_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Tackles (won)</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(da?.tackles_won_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Interceptions</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(da?.interceptions_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Blocks</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(da?.blocks_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Clearances</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(da?.clearances_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Duels won</p>
              <p className="text-2xl font-bold text-gray-900">{fmtPct(da?.defensive_duels_won_percent_avg)}</p>
            </div>
          </div>
        </div>

        <div className="tactical-card bg-yellow-50 border-l-4 border-yellow-500">
          <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
            <Zap className="text-yellow-600" size={22} />
            Pressing & structure
          </h5>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">PPDA</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(ps?.PPDA_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">High turnovers won</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(ps?.high_turnovers_won_avg, 1)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg">
              <p className="text-sm text-gray-600">Counter-press recoveries</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(ps?.counter_press_recoveries_avg, 1)}</p>
            </div>
          </div>
          <p className="text-sm text-gray-600 mt-3">
            Pressing intensity zones require event data (not available in current API).
          </p>
        </div>
      </div>

      {/* Spatial & Positional (proxies) */}
      <div className="tactical-card bg-gray-50 border-l-4 border-gray-400">
        <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
          <Map className="text-gray-700" size={22} />
          Spatial & positional (proxies)
        </h5>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Avg line height</p>
            <p className="text-lg font-bold text-gray-900">{ts?.avg_team_line_height_mode || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Defensive line height</p>
            <p className="text-lg font-bold text-gray-900">{fmt(ts?.defensive_line_height_avg, 1)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Distance between lines</p>
            <p className="text-lg font-bold text-gray-900">{ts?.distance_between_lines_mode || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Compactness</p>
            <p className="text-lg font-bold text-gray-900">{ts?.team_compactness_mode || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Width usage</p>
            <p className="text-lg font-bold text-gray-900">{ts?.width_usage_mode || 'N/A'}</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-3">
          Heatmaps, touches-per-zone, overloads and half-space occupation require tracking/event feeds.
        </p>
      </div>



      {/* Psychological Profile */}
      <div className="tactical-card bg-purple-50 border-l-4 border-purple-500">
        <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
          <Brain className="text-purple-600" size={22} />
          Psychological profile
        </h5>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Mental strength</p>
            <p className="text-lg font-bold text-gray-900">{statistics?.psychological_profile?.mental_strength || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Resilience</p>
            <p className="text-lg font-bold text-gray-900">{fmtInt(statistics?.psychological_profile?.resilience_score)}/100</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Pressure</p>
            <p className="text-lg font-bold text-gray-900">{statistics?.psychological_profile?.handles_pressure || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Momentum</p>
            <p className="text-lg font-bold text-gray-900">{statistics?.psychological_profile?.momentum || 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Form Trends */}
      <div className="tactical-card bg-yellow-50 border-l-4 border-yellow-500">
        <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
          <LineChart className="text-yellow-700" size={22} />
          Form analysis
        </h5>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Trend</p>
            <p className="text-lg font-bold text-gray-900">{statistics?.form_trends?.trend || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Recent points (last 3)</p>
            <p className="text-lg font-bold text-gray-900">{fmtInt(statistics?.form_trends?.recent_form_points)}</p>
          </div>
        </div>
      </div>

      {/* Set-piece analytics */}
      <div className="tactical-card bg-green-50 border-l-4 border-green-500">
        <h5 className="font-bold text-lg mb-3 flex items-center gap-2">
          <Flag className="text-green-700" size={22} />
          Set-piece analytics
        </h5>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white p-4 rounded-lg border">
            <p className="font-semibold text-gray-900 mb-3">Attacking</p>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-600">xG (corners)</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.xG_from_corners_avg, 2)}</p>
              </div>
              <div>
                <p className="text-gray-600">xG (free kicks)</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.xG_from_free_kicks_avg, 2)}</p>
              </div>
              <div>
                <p className="text-gray-600">Shots / match</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.shots_from_set_pieces_avg, 1)}</p>
              </div>
              <div>
                <p className="text-gray-600">Goals / match</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.goals_from_set_pieces_avg, 2)}</p>
              </div>
              <div>
                <p className="text-gray-600">1st contact success</p>
                <p className="font-bold text-gray-900">{fmtPct(setPieces?.first_contact_success_percent_avg, 1)}</p>
              </div>
              <div>
                <p className="text-gray-600">Aerial duels won</p>
                <p className="font-bold text-gray-900">{fmtPct(setPieces?.aerial_duels_won_percent_on_set_pieces_avg, 1)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border">
            <p className="font-semibold text-gray-900 mb-3">Defending</p>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Goals conceded</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.set_piece_goals_conceded_avg, 2)}</p>
              </div>
              <div>
                <p className="text-gray-600">xG conceded</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.xG_conceded_from_set_pieces_avg, 2)}</p>
              </div>
              <div>
                <p className="text-gray-600">Clearances under pressure</p>
                <p className="font-bold text-gray-900">{fmt(setPieces?.clearances_under_pressure_avg, 1)}</p>
              </div>
              <div>
                <p className="text-gray-600">Marking type (mode)</p>
                <p className="font-bold text-gray-900">{setPieces?.marking_type_mode || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-3">
          Note: these are proxies aggregated from match summaries (not event-level set-piece data).
        </p>
      </div>

      {/* Contextual & psychological variables */}
      <div className="tactical-card bg-indigo-50 border-l-4 border-indigo-500">
        <h5 className="font-bold text-lg mb-3">Contextual & psychological variables</h5>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Home share</p>
            <p className="text-lg font-bold text-gray-900">{fmtPct(ctx?.home_share_percent, 0)}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Scoreline state (mode)</p>
            <p className="text-lg font-bold text-gray-900">{scorelineMode || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Momentum (mode)</p>
            <p className="text-lg font-bold text-gray-900">{ctx?.momentum_mode || 'N/A'}</p>
          </div>
          <div className="bg-white p-3 rounded-lg">
            <p className="text-sm text-gray-600">Discipline risk (mode)</p>
            <p className="text-lg font-bold text-gray-900">{ctx?.discipline_risk_mode || 'N/A'}</p>
          </div>
        </div>
        {Object.keys(scorelineDist).length > 0 && (
          <div className="mt-4 bg-white rounded-lg p-4 border text-sm">
            <p className="font-semibold text-gray-900 mb-2">Scoreline state distribution</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(scorelineDist).map(([k, v]) => (
                <span key={k} className="px-2 py-1 rounded bg-gray-100 text-gray-800">
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      {/* Per-match tactical table */}
      {recentGames.length > 0 && (
        <div className="tactical-card bg-white">
          <h5 className="font-bold text-lg mb-3">Recent games (tactical)</h5>
          <div className="overflow-x-auto">
            <table className="min-w-[900px] w-full text-sm">
              <thead>
                <tr className="text-left text-gray-600 border-b">
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">Opponent</th>
                  <th className="py-2 pr-4">Loc</th>
                  <th className="py-2 pr-4">Score</th>
                  <th className="py-2 pr-4">Res</th>
                  <th className="py-2 pr-4">Poss</th>
                  <th className="py-2 pr-4">xG</th>
                  <th className="py-2 pr-4">PPDA</th>
                  <th className="py-2 pr-4">Key passes</th>
                  <th className="py-2 pr-4">Crosses</th>
                </tr>
              </thead>
              <tbody>
                {recentGames.map((m, idx) => (
                  <tr key={idx} className="border-b last:border-b-0">
                    <td className="py-2 pr-4">{(m?.match_info?.date || '').slice(0, 10) || 'N/A'}</td>
                    <td className="py-2 pr-4">{m?.match_info?.opponent || 'N/A'}</td>
                    <td className="py-2 pr-4">{m?.match_info?.location || 'N/A'}</td>
                    <td className="py-2 pr-4">{m?.match_info?.score || 'N/A'}</td>
                    <td className="py-2 pr-4 font-bold">{m?.match_info?.result || 'N/A'}</td>
                    <td className="py-2 pr-4">{fmtPct(m?.possession_control?.possession_percent, 0)}</td>
                    <td className="py-2 pr-4">{fmt(m?.expected_metrics?.xG, 2)}</td>
                    <td className="py-2 pr-4">{fmt(m?.pressing_structure?.PPDA, 1)}</td>
                    <td className="py-2 pr-4">{fmtInt(m?.chance_creation?.key_passes)}</td>
                    <td className="py-2 pr-4">{fmtInt(m?.chance_creation?.crosses_attempted)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdvancedStatsPanel
