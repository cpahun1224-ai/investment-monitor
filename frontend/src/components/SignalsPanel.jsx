import { useState } from 'react'
import { formatKRW, formatPercent, profitColor, STAGE_COLORS } from '../utils'
import SignalBadge from './SignalBadge'
import StockGuideModal from './StockGuideModal'

export default function SignalsPanel({ signals, cash, onEditStock }) {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('전체')

  if (!signals?.length) return null

  const counts = {
    RISK:  signals.filter(s => s.signal === 'RISK').length,
    WATCH: signals.filter(s => s.signal === 'WATCH').length,
    GOOD:  signals.filter(s => s.signal === 'GOOD').length,
  }

  const filtered = filter === '전체' ? signals : signals.filter(s => s.signal === filter)

  return (
    <>
      <div className="bg-[#1a1d2e] rounded-xl border border-white/5">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-5 border-b border-white/5">
          <div className="text-white font-semibold">매수/매도 시그널</div>
          <div className="flex gap-2">
            {['전체', 'RISK', 'WATCH', 'GOOD'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${
                  filter === f
                    ? f === 'RISK'  ? 'bg-red-500/30 text-red-300'
                    : f === 'WATCH' ? 'bg-amber-500/30 text-amber-300'
                    : f === 'GOOD'  ? 'bg-emerald-500/30 text-emerald-300'
                    : 'bg-blue-600 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {f} {f !== '전체' && `(${counts[f]})`}
              </button>
            ))}
          </div>
        </div>

        {/* 요약 배너 */}
        <div className="grid grid-cols-3 divide-x divide-white/5 border-b border-white/5">
          {[
            { label: 'RISK', count: counts.RISK, color: 'text-red-400', bg: 'bg-red-500/5' },
            { label: 'WATCH', count: counts.WATCH, color: 'text-amber-400', bg: 'bg-amber-500/5' },
            { label: 'GOOD', count: counts.GOOD, color: 'text-emerald-400', bg: 'bg-emerald-500/5' },
          ].map(({ label, count, color, bg }) => (
            <div key={label} className={`${bg} px-4 py-3 text-center`}>
              <div className={`text-2xl font-bold ${color}`}>{count}</div>
              <div className="text-gray-500 text-xs">{label}</div>
            </div>
          ))}
        </div>

        {/* 종목 리스트 */}
        <div className="divide-y divide-white/5">
          {filtered.map(s => (
            <div
              key={s.ticker}
              className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/3 cursor-pointer transition-colors group"
              onClick={() => setSelected(s)}
            >
              {/* 종목명 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-white text-sm font-medium truncate">{s.name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${STAGE_COLORS[s.stage] || STAGE_COLORS['씨앗']}`}>
                    {s.stage}
                  </span>
                  <SignalBadge signal={s.signal} />
                </div>
                <div className="text-gray-500 text-xs">{s.sector} · {s.ticker}</div>
              </div>

              {/* 현재가 */}
              <div className="text-right hidden sm:block">
                <div className="text-white text-sm">{formatKRW(s.current_price)}</div>
                <div className="text-gray-500 text-xs">평균 {formatKRW(s.avg_buy_price)}</div>
              </div>

              {/* 수익률 */}
              <div className={`text-right w-20 font-medium text-sm ${profitColor(s.profit_rate)}`}>
                {formatPercent(s.profit_rate)}
                <div className={`text-xs ${profitColor(s.profit_loss)}`}>
                  {s.profit_loss >= 0 ? '+' : ''}{(s.profit_loss / 10000).toFixed(0)}만원
                </div>
              </div>

              {/* 목표가 프로그레스 */}
              {s.target_price > 0 && (
                <div className="w-24 hidden md:block">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">목표</span>
                    <span className="text-blue-400">{s.target_rate}%</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${s.target_rate >= 90 ? 'bg-amber-500' : 'bg-blue-500'}`}
                      style={{ width: `${Math.min(s.target_rate, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <StockGuideModal
          signal={selected}
          cash={cash}
          onClose={() => setSelected(null)}
          onEdit={(s) => { setSelected(null); onEditStock(s) }}
        />
      )}
    </>
  )
}
