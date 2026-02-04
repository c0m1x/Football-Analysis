const fmt = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  if (typeof value === 'number') return value.toFixed(digits)
  return String(value)
}

const fmtPct = (value, digits = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  if (typeof value === 'number') return `${value.toFixed(digits)}%`
  return String(value)
}

const safeBool = (v) => {
  if (v === true || v === false) return v
  if (typeof v === 'string') return v.toLowerCase() === 'true'
  return Boolean(v)
}

const isGilHomeFromFixture = (fixture) => {
  if (!fixture) return false
  if (fixture.is_gil_home !== undefined) return safeBool(fixture.is_gil_home)
  if (fixture.is_home !== undefined) return safeBool(fixture.is_home)
  if (fixture.gil_vicente_home !== undefined) return safeBool(fixture.gil_vicente_home)
  return false
}

const fixtureDateTime = (fixture) => {
  if (!fixture) return null
  if (fixture.datetime) return new Date(fixture.datetime)
  if (fixture.date) return new Date(`${fixture.date}T${fixture.time || '00:00:00'}`)
  return null
}

const safeArr = (v) => (Array.isArray(v) ? v : [])

export const exportFixtureAnalysis = (fixture, statistics, tacticalPlan, format) => {
  if (!fixture || !statistics || !tacticalPlan) return

  const isHome = isGilHomeFromFixture(fixture)
  const dt = fixtureDateTime(fixture)
  const opponent = fixture.opponent_name || statistics.opponent || tacticalPlan.opponent || 'Opponent'

  const exportData = {
    match: {
      opponent,
      date: fixture.date,
      time: fixture.time,
      datetime: fixture.datetime || (dt ? dt.toISOString() : null),
      venue: isHome ? 'Home' : 'Away',
      competition: fixture.competition || null,
    },
    statistics,
    tacticalPlan,
    exportDate: new Date().toISOString(),
  }

  const baseName = `${opponent}`.replace(/\s+/g, '_')
  const day = new Date().toISOString().split('T')[0]

  if (format === 'json') {
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${baseName}_analysis_${day}.json`
    a.click()
    URL.revokeObjectURL(url)
    return
  }

  if (format !== 'text') return

  const tactical = tacticalPlan?.tactical_plan || {}
  const formationRaw = tactical?.formation_recommendations?.suggested_changes
  const formationRecs = Array.isArray(formationRaw) ? formationRaw : (formationRaw?.recommendations ?? [])

  const pressingRec = tactical?.pressing_strategy?.recommendation || {}
  const pressingRecs = safeArr(pressingRec?.pressing_recommendations)

  const zonesRaw = tactical?.target_zones?.priority_zones
  const zones = Array.isArray(zonesRaw) ? zonesRaw : (zonesRaw?.priority_zones ?? [])

  const weaknesses = safeArr(tactical?.critical_weaknesses)

  const f = statistics?.tactical_foundation || {}
  const pc = f?.possession_control || {}
  const sf = f?.shooting_finishing || {}
  const xm = f?.expected_metrics || {}
  const ps = f?.pressing_structure || {}

  let txt = ''
  txt += 'GIL VICENTE FC — TACTICAL ANALYSIS REPORT\n'
  txt += '='.repeat(60) + '\n\n'
  txt += `Match: Gil Vicente vs ${opponent}\n`
  if (dt && !Number.isNaN(dt.getTime())) {
    txt += `Date: ${dt.toLocaleString('pt-PT')}\n`
  } else if (fixture.date) {
    txt += `Date: ${fixture.date} ${fixture.time || ''}\n`
  }
  txt += `Venue: ${isHome ? 'Home (Estádio Cidade de Barcelos)' : 'Away'}\n`
  if (fixture.competition) txt += `Competition: ${fixture.competition}\n`
  txt += '\n'

  txt += 'DATA SOURCES\n'
  txt += '-'.repeat(60) + '\n'
  txt += `Statistics: ${statistics?.data_source || 'N/A'}\n`
  txt += `Tactical Plan: ${tacticalPlan?.data_source || 'N/A'}\n`
  if (statistics?.cache_info) txt += `Stats cache: ${statistics.cache_info}\n`
  if (tacticalPlan?.cache_info) txt += `Plan cache: ${tacticalPlan.cache_info}\n`
  txt += '\n'

  txt += 'OPPONENT OVERVIEW (RECENT FORM)\n'
  txt += '-'.repeat(60) + '\n'
  txt += `Form: ${statistics?.overall_performance?.form_string || 'N/A'}\n`
  txt += `Goals/Game: ${statistics?.overall_performance?.goals_per_game ?? 'N/A'}\n`
  txt += `Conceded/Game: ${statistics?.overall_performance?.conceded_per_game ?? 'N/A'}\n`
  txt += `Points/Game: ${statistics?.overall_performance?.points_per_game ?? 'N/A'}\n`
  txt += '\n'

  txt += 'TACTICAL FOUNDATION (AVERAGES)\n'
  txt += '-'.repeat(60) + '\n'
  txt += `Matches analyzed: ${f?.matches_analyzed ?? 'N/A'}${f?.estimated ? ' (estimated)' : ''}\n`
  txt += `Possession: ${fmtPct(pc?.possession_percent_avg)}\n`
  txt += `Pass accuracy: ${fmtPct(pc?.pass_accuracy_avg)}\n`
  txt += `Shots: ${fmt(sf?.total_shots_avg, 1)} (on target ${fmt(sf?.shots_on_target_avg, 1)})\n`
  txt += `xG: ${fmt(xm?.xG_avg, 2)} (xG/shot ${fmt(xm?.xG_per_shot_avg, 3)})\n`
  txt += `PPDA: ${fmt(ps?.PPDA_avg, 1)}\n`
  txt += '\n'

  txt += 'AI TACTICAL PLAN\n'
  txt += '-'.repeat(60) + '\n'
  if (tacticalPlan?.ai_confidence) {
    txt += `Confidence: ${tacticalPlan.ai_confidence.overall_confidence ?? 'N/A'}%\n`
    if (tacticalPlan.ai_confidence.data_quality) txt += `Data quality: ${tacticalPlan.ai_confidence.data_quality}\n`
    if (tacticalPlan.ai_confidence.recommendation_reliability) txt += `Reliability: ${tacticalPlan.ai_confidence.recommendation_reliability}\n`
  }
  txt += '\n'

  if (formationRecs.length > 0) {
    txt += 'Formation recommendations:\n'
    formationRecs.slice(0, 5).forEach((r, i) => {
      txt += `  ${i + 1}. ${r.formation || '—'}${r.priority ? ` (${r.priority})` : ''}\n`
      if (r.reason) txt += `     - ${r.reason}\n`
    })
    txt += '\n'
  }

  if (pressingRecs.length > 0) {
    txt += 'Pressing adjustments:\n'
    pressingRecs.slice(0, 6).forEach((r, i) => {
      txt += `  ${i + 1}. ${r.adjustment || '—'} · ${r.target_line || '—'}${r.priority ? ` (${r.priority})` : ''}\n`
      if (r.reason) txt += `     - ${r.reason}\n`
    })
    txt += '\n'
  }

  if (zones.length > 0) {
    txt += 'Priority attack zones:\n'
    zones.slice(0, 6).forEach((z, i) => {
      txt += `  ${i + 1}. ${z.zone || '—'}${z.priority ? ` (${z.priority})` : ''}\n`
      const why = z.reasoning || z.attack_method || z.expected_outcome
      if (why) txt += `     - ${why}\n`
    })
    txt += '\n'
  }

  if (weaknesses.length > 0) {
    txt += 'Weaknesses to exploit:\n'
    weaknesses.slice(0, 6).forEach((w, i) => {
      txt += `  ${i + 1}. ${w.weakness || '—'}${w.severity ? ` (${w.severity})` : ''}\n`
      const how = w.tactical_approach || w.exploitation || w.expected_impact
      if (how) txt += `     - ${how}\n`
    })
    txt += '\n'
  }

  txt += '='.repeat(60) + '\n'
  txt += `Report generated: ${new Date().toLocaleString('pt-PT')}\n`

  const blob = new Blob([txt], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${baseName}_analysis_${day}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

