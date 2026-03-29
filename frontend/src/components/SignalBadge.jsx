export const SIGNAL_STYLE = {
  GOOD:  'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  WATCH: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  RISK:  'bg-red-500/20 text-red-400 border border-red-500/30',
}

export const SIGNAL_ICON = { GOOD: '●', WATCH: '▲', RISK: '✕' }

export default function SignalBadge({ signal }) {
  if (!signal) return null
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${SIGNAL_STYLE[signal]}`}>
      {SIGNAL_ICON[signal]} {signal}
    </span>
  )
}
