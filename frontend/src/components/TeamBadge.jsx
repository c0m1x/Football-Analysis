import React from 'react'

const TEAM_STYLES = {
  moreirense: { bg: '#0B6E3C', fg: '#FFFFFF', border: '#E2C044' },
  braga: { bg: '#D61F2C', fg: '#FFFFFF', border: '#111827' },
  estoril: { bg: '#F2C14E', fg: '#0B5FA5', border: '#0B5FA5' },
  benfica: { bg: '#E2231A', fg: '#FFFFFF', border: '#F2C14E' },
  'estrela da amadora': { bg: '#D61F2C', fg: '#FFFFFF', border: '#0B6E3C' },
  alverca: { bg: '#B91C1C', fg: '#FFFFFF', border: '#1F2937' },
  'santa clara': { bg: '#C1121F', fg: '#FFFFFF', border: '#F8F9FA' },
  afs: { bg: '#111827', fg: '#FFFFFF', border: '#9CA3AF' },
  tondela: { bg: '#0F7A3E', fg: '#F2C14E', border: '#F2C14E' },
  'vitoria sc': { bg: '#111827', fg: '#FFFFFF', border: '#9CA3AF' },
  'casa pia': { bg: '#111827', fg: '#FFFFFF', border: '#E5E7EB' },
  'rio ave': { bg: '#0B6E3C', fg: '#FFFFFF', border: '#E5E7EB' },
  arouca: { bg: '#F4B400', fg: '#1F2937', border: '#1F2937' },
  sporting: { bg: '#0B6E3C', fg: '#FFFFFF', border: '#E5E7EB' },
}

const TEAM_ALIASES = {
  'vitoria sport clube': 'vitoria sc',
  'vitoria guimaraes': 'vitoria sc',
  'vitoria': 'vitoria sc',
  'avs': 'afs',
  'afs futebol': 'afs',
  'estrela amadora': 'estrela da amadora',
}

const normalizeName = (value) => {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const getInitials = (name) => {
  const normalized = normalizeName(name)
  if (!normalized) return '?'
  const parts = normalized.split(' ').filter(Boolean)
  if (parts.length === 1) {
    const token = parts[0].toUpperCase()
    return token.length <= 3 ? token : token.slice(0, 2)
  }
  const first = parts[0][0] || ''
  const last = parts[parts.length - 1][0] || ''
  return `${first}${last}`.toUpperCase()
}

const TeamBadge = ({ name, logo, size = 36, className = '' }) => {
  const normalized = normalizeName(name)
  const key = TEAM_ALIASES[normalized] || normalized
  const style = TEAM_STYLES[key] || { bg: '#1F2937', fg: '#FFFFFF', border: '#9CA3AF' }
  const dimension = typeof size === 'number' ? `${size}px` : size

  if (logo) {
    return (
      <img
        src={logo}
        alt={`${name} logo`}
        title={name}
        style={{ width: dimension, height: dimension }}
        className={`inline-block rounded-full border shadow-sm bg-white ${className}`}
      />
    )
  }

  return (
    <div
      title={name}
      className={`inline-flex items-center justify-center rounded-full border shadow-sm ${className}`}
      style={{
        width: dimension,
        height: dimension,
        background: style.bg,
        color: style.fg,
        borderColor: style.border,
      }}
    >
      <span className="text-[11px] font-bold tracking-wide">{getInitials(name)}</span>
    </div>
  )
}

export default TeamBadge
