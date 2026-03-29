import { formatKRW } from '../utils'
import { SECTOR_COLORS } from '../utils'

export default function RebalancePanel({ data }) {
  if (!data) return null
  const { total_value, cash, sectors } = data

  return (
    <div className="bg-[#1a1d2e] rounded-xl border border-white/5">
      <div className="p-5 border-b border-white/5">
        <div className="text-white font-semibold">포트폴리오 리밸런싱 가이드</div>
        <div className="text-gray-500 text-xs mt-0.5">총 자산 {formatKRW(total_value)} 기준</div>
      </div>

      <div className="p-5 space-y-3">
        {sectors.map((sec, i) => {
          const isCash = sec.sector === '현금'
          const color = isCash ? '#94a3b8' : SECTOR_COLORS[i % SECTOR_COLORS.length]
          const w = sec.current_weight

          // 과비중/저비중 판단: 현금 30% 이상은 여력, 단일 섹터 25% 이상은 집중
          const isHeavy = !isCash && w > 20
          const isLight = !isCash && w < 3

          return (
            <div key={sec.sector}>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                  <span className="text-gray-300 font-medium">{sec.sector}</span>
                  {sec.stocks.length > 0 && (
                    <span className="text-gray-600 truncate hidden sm:inline">
                      {sec.stocks.join(', ')}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">{formatKRW(sec.value)}</span>
                  <span className={`font-bold w-12 text-right ${
                    isHeavy ? 'text-amber-400' : isLight ? 'text-blue-400' : 'text-gray-200'
                  }`}>
                    {w}%
                  </span>
                  {isHeavy && <span className="text-amber-400 text-xs">↓ 축소</span>}
                  {isLight && <span className="text-blue-400 text-xs">↑ 확대</span>}
                  {isCash && w > 25 && <span className="text-emerald-400 text-xs">💰 여력</span>}
                </div>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(w, 100)}%`,
                    backgroundColor: color,
                    opacity: isHeavy ? 1 : 0.7,
                  }}
                />
              </div>
            </div>
          )
        })}

        {/* 현금 활용 가이드 */}
        {cash > 50000000 && (
          <div className="mt-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-xs">
            <div className="text-emerald-400 font-medium mb-2">💰 현금 활용 시나리오</div>
            <div className="text-gray-300 space-y-1">
              <div>• 현금 {formatKRW(cash)} 중 25% 투입 시: {formatKRW(cash * 0.25)}</div>
              <div>• 현금 {formatKRW(cash)} 중 50% 투입 시: {formatKRW(cash * 0.5)}</div>
              <div className="text-gray-500 mt-1">RISK 종목 추가매수 또는 저비중 섹터 확대 우선 고려</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
