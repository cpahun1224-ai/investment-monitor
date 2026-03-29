export const formatKRW = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 }).format(value)
}

export const formatNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return new Intl.NumberFormat('ko-KR').format(value)
}

export const formatPercent = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

export const profitColor = (value) => {
  if (value > 0) return 'text-emerald-400'
  if (value < 0) return 'text-red-400'
  return 'text-gray-400'
}

export const STAGE_COLORS = {
  '씨앗': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  '에코': 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  '피라미딩': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
}

export const SECTOR_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#ec4899', '#84cc16', '#6366f1',
  '#14b8a6', '#fb923c', '#a855f7', '#22c55e', '#94a3b8',
]
