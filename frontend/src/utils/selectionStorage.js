const STORAGE_KEY = 'tactical:selected-context'

export const loadSelection = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { league: '', teamId: '', teamName: '' }
    const parsed = JSON.parse(raw)
    return {
      league: String(parsed?.league || ''),
      teamId: String(parsed?.teamId || ''),
      teamName: String(parsed?.teamName || ''),
    }
  } catch (_) {
    return { league: '', teamId: '', teamName: '' }
  }
}

export const saveSelection = ({ league, teamId, teamName }) => {
  const payload = {
    league: String(league || ''),
    teamId: String(teamId || ''),
    teamName: String(teamName || ''),
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
}
