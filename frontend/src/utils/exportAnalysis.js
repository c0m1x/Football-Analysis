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

const isHomeFromFixture = (fixture) => {
  if (!fixture) return false
  if (fixture.is_home !== undefined) return safeBool(fixture.is_home)
  return false
}

const fixtureDateTime = (fixture) => {
  if (!fixture) return null
  if (fixture.datetime) return new Date(fixture.datetime)
  if (fixture.date) return new Date(`${fixture.date}T${fixture.time || '00:00:00'}`)
  return null
}

const safeArr = (v) => (Array.isArray(v) ? v : [])

const escapeHtml = (value) =>
  String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')

const buildReportHtml = ({ title, body }) => `<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #111827; }
    h1 { font-size: 22px; margin: 0 0 10px; }
    h2 { font-size: 16px; margin: 22px 0 8px; border-bottom: 1px solid #d1d5db; padding-bottom: 4px; }
    p, li { font-size: 13px; line-height: 1.5; }
    .meta { background: #f3f4f6; padding: 10px; border-radius: 8px; }
    .note { background: #fef3c7; color: #92400e; padding: 10px; border-radius: 8px; margin-top: 12px; }
  </style>
</head>
<body>
${body}
</body>
</html>`

export const exportFixtureAnalysis = (fixture, statistics, tacticalPlan, format) => {
  if (!fixture || !statistics || !tacticalPlan) return

  const isHome = isHomeFromFixture(fixture)
  const dt = fixtureDateTime(fixture)
  const teamName =
    fixture.team_name || statistics?.focus_team?.name || tacticalPlan?.focus_team?.name || 'Selected Team'
  const opponent = fixture.opponent_name || statistics.opponent || tacticalPlan.opponent || 'Opponent'

  const exportData = {
    match: {
      team: teamName,
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

  const custom = tacticalPlan?.customized_suggestions || {}
  const validationNote =
    tacticalPlan?.historical_context?.validation_note ||
    statistics?.historical_context?.validation_note ||
    'Baseado em dados da época 2023/24 — validar com observação recente do adversário.'

  const renderCustomItems = (items = []) =>
    safeArr(items)
      .map((x) => `<li><strong>${escapeHtml(x?.title || '—')}</strong>: ${escapeHtml(x?.detail || '')}</li>`)
      .join('')

  const htmlBody = `
    <h1>Relatório Tático - ${escapeHtml(teamName)} vs ${escapeHtml(opponent)}</h1>
    <div class="meta">
      <p><strong>Data:</strong> ${escapeHtml(
        dt && !Number.isNaN(dt.getTime()) ? dt.toLocaleString('pt-PT') : `${fixture.date || 'N/A'} ${fixture.time || ''}`
      )}</p>
      <p><strong>Local:</strong> ${escapeHtml(isHome ? 'Casa' : 'Fora')}</p>
      <p><strong>Fonte stats:</strong> ${escapeHtml(statistics?.data_source || 'N/A')}</p>
      <p><strong>Fonte plano:</strong> ${escapeHtml(tacticalPlan?.data_source || 'N/A')}</p>
    </div>
    <div class="note">${escapeHtml(validationNote)}</div>

    <h2>Sistema de Jogo Recomendado</h2>
    <ul>${renderCustomItems(custom?.recommended_system)}</ul>

    <h2>Zonas a Explorar no Ataque</h2>
    <ul>${renderCustomItems(custom?.attack_zones)}</ul>

    <h2>Vulnerabilidades Defensivas</h2>
    <ul>${renderCustomItems(custom?.defensive_vulnerabilities)}</ul>

    <h2>Neutralizar Pontos Fortes</h2>
    <ul>${renderCustomItems(custom?.neutralize_strengths)}</ul>

    <h2>Ajustes em Bolas Paradas</h2>
    <ul>${renderCustomItems(custom?.set_piece_adjustments)}</ul>
  `

  if (format === 'word') {
    const html = buildReportHtml({ title: `${opponent} Tactical Report`, body: htmlBody })
    const blob = new Blob([html], { type: 'application/msword' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${baseName}_analysis_${day}.doc`
    a.click()
    URL.revokeObjectURL(url)
    return
  }

  if (format === 'pdf') {
    const html = buildReportHtml({ title: `${opponent} Tactical Report`, body: htmlBody })
    const win = window.open('', '_blank', 'width=900,height=700')
    if (!win) return
    win.document.open()
    win.document.write(html)
    win.document.close()
    win.focus()
    setTimeout(() => {
      win.print()
    }, 350)
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
  txt += 'FOOTBALL TACTICAL ANALYSIS REPORT\n'
  txt += '='.repeat(60) + '\n\n'
  txt += `Match: ${teamName} vs ${opponent}\n`
  if (dt && !Number.isNaN(dt.getTime())) {
    txt += `Date: ${dt.toLocaleString('pt-PT')}\n`
  } else if (fixture.date) {
    txt += `Date: ${fixture.date} ${fixture.time || ''}\n`
  }
  txt += `Venue: ${isHome ? 'Home' : 'Away'}\n`
  if (fixture.competition) txt += `Competition: ${fixture.competition}\n`
  txt += '\n'

  txt += 'DATA SOURCES\n'
  txt += '-'.repeat(60) + '\n'
  txt += `Statistics: ${statistics?.data_source || 'N/A'}\n`
  txt += `Tactical Plan: ${tacticalPlan?.data_source || 'N/A'}\n`
  if (tacticalPlan?.historical_context?.validation_note) {
    txt += `Validation note: ${tacticalPlan.historical_context.validation_note}\n`
  }
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
