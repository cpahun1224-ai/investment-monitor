import { useState, useEffect } from 'react'
import { X, TrendingUp, TrendingDown, Target, ShieldAlert, Coins } from 'lucide-react'
import { getSellScenario } from '../api'
import { formatKRW, formatNumber, formatPercent, profitColor, STAGE_COLORS } from '../utils'
import SignalBadge from './SignalBadge'
import AIAnalysisPanel from './AIAnalysisPanel'

export default function StockGuideModal({ signal, onClose, onEdit, cash }) {
  const [scenario, setScenario] = useState(null)
  const s = signal

  useEffect(() => {
    getSellScenario(s.ticker).then(setScenario).catch(() => {})
  }, [s.ticker])

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const profitRate = s.profit_rate
  const targetRate = s.target_rate
  const stopGap = s.stop_gap

  // 추가매수 조건 판단
  const conditions = [
    {
      label: '하락 10% 이상',
      ok: profitRate <= -10,
      icon: profitRate <= -10 ? '✅' : '⬜',
    },
    {
      label: '현금 여력 충분 (현금 > 평가금액 10%)',
      ok: cash > s.eval_value * 0.1,
      icon: cash > s.eval_value * 0.1 ? '✅' : '⚠️',
    },
    {
      label: '손절가 미도달',
      ok: !s.stop_loss_price || s.current_price > s.stop_loss_price,
      icon: (!s.stop_loss_price || s.current_price > s.stop_loss_price) ? '✅' : '🚨',
    },
  ]

  // 단계 업그레이드 추천
  const upgradeHint = s.stage === '씨앗' && profitRate > 5
    ? '씨앗→에코 전환 고려'
    : s.stage === '에코' && profitRate > 10
    ? '에코→피라미딩 고려'
    : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      {/* 우상단 고정 X 버튼 */}
      <button
        onClick={onClose}
        className="fixed top-4 right-4 z-[60] w-11 h-11 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
      >
        <X size={22} />
      </button>

      <div
        className="bg-[#1a1d2e] rounded-2xl w-full max-w-lg border border-white/10 shadow-2xl max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >

        {/* 헤더 */}
        <div className="flex items-start justify-between p-5 border-b border-white/5 shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-white font-bold text-lg">{s.name}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${STAGE_COLORS[s.stage] || STAGE_COLORS['씨앗']}`}>
                {s.stage}
              </span>
              <SignalBadge signal={s.signal} />
            </div>
            <div className="text-gray-500 text-xs">{s.ticker} · {s.sector}</div>
          </div>
          <button
            onClick={() => onEdit(s)}
            className="text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 px-2 py-1 rounded-lg"
          >
            수정
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto flex-1">

          {/* 가격 현황 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-gray-400 text-xs mb-1">현재가</div>
              <div className="text-white font-bold">{formatKRW(s.current_price)}</div>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-gray-400 text-xs mb-1">평균매수가</div>
              <div className="text-white font-bold">{formatKRW(s.avg_buy_price)}</div>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-gray-400 text-xs mb-1">평가손익</div>
              <div className={`font-bold text-sm ${profitColor(s.profit_loss)}`}>
                {formatPercent(profitRate)}
              </div>
              <div className={`text-xs ${profitColor(s.profit_loss)}`}>
                {s.profit_loss >= 0 ? '+' : ''}{formatKRW(s.profit_loss)}
              </div>
            </div>
          </div>

          {/* 목표가 달성률 */}
          {s.target_price > 0 && (
            <div className="bg-white/5 rounded-xl p-4">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="flex items-center gap-1.5 text-gray-300">
                  <Target size={14} className="text-blue-400" />
                  목표가 {formatKRW(s.target_price)}
                </span>
                <span className="text-blue-400 font-medium">{targetRate}% 도달</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${targetRate >= 90 ? 'bg-amber-500' : 'bg-blue-500'}`}
                  style={{ width: `${Math.min(targetRate, 100)}%` }}
                />
              </div>
              {targetRate >= 90 && (
                <div className="mt-2 text-xs text-amber-400 flex items-center gap-1">
                  🔔 목표가 근접! 매도 타이밍 검토 필요
                </div>
              )}
            </div>
          )}

          {/* 손절가 */}
          {s.stop_loss_price > 0 && (
            <div className={`rounded-xl p-4 ${stopGap < 10 ? 'bg-red-500/10 border border-red-500/20' : 'bg-white/5'}`}>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5 text-gray-300">
                  <ShieldAlert size={14} className="text-red-400" />
                  손절가 {formatKRW(s.stop_loss_price)}
                </span>
                <span className={`font-medium ${stopGap < 10 ? 'text-red-400' : 'text-gray-400'}`}>
                  손절까지 -{stopGap}%
                </span>
              </div>
              {stopGap < 10 && (
                <div className="mt-1 text-xs text-red-400">⚠️ 손절가 근접 — 비중 축소 고려</div>
              )}
            </div>
          )}

          {/* 추가매수 판단 */}
          <div className="bg-white/5 rounded-xl p-4">
            <div className="text-gray-300 text-sm font-medium mb-3 flex items-center gap-1.5">
              <TrendingUp size={14} className="text-emerald-400" />
              추가매수 판단
            </div>
            <div className="space-y-1.5">
              {conditions.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span>{c.icon}</span>
                  <span className={c.ok ? 'text-gray-300' : 'text-gray-500'}>{c.label}</span>
                </div>
              ))}
            </div>
            {upgradeHint && (
              <div className="mt-3 text-xs text-blue-400 bg-blue-500/10 rounded-lg px-3 py-2">
                ⚠️ 추천: {upgradeHint}
              </div>
            )}
            <div className="mt-3 text-xs text-gray-400">
              현금 {formatKRW(cash)}으로 최대 <span className="text-white font-medium">{formatNumber(s.add_buy_qty)}주</span> 추가매수 가능
            </div>
          </div>

          {/* 매도 시나리오 */}
          {scenario && (
            <div className="bg-white/5 rounded-xl p-4">
              <div className="text-gray-300 text-sm font-medium mb-3 flex items-center gap-1.5">
                <TrendingDown size={14} className="text-amber-400" />
                매도 시나리오
              </div>
              <div className="space-y-2">
                {scenario.scenarios.map(sc => (
                  <div key={sc.ratio} className="flex items-center justify-between text-xs bg-white/5 rounded-lg px-3 py-2">
                    <span className="text-gray-400 w-16">{sc.ratio === 100 ? '전량매도' : `${sc.ratio}% 매도`}</span>
                    <span className="text-gray-300">{formatNumber(sc.qty)}주</span>
                    <span className="text-gray-300">{formatKRW(sc.proceeds)}</span>
                    <span className={`font-medium ${profitColor(sc.profit)}`}>
                      {sc.profit >= 0 ? '+' : ''}{formatKRW(sc.profit)}
                    </span>
                    <span className={`w-14 text-right ${profitColor(sc.profit_rate)}`}>
                      {formatPercent(sc.profit_rate)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI 투자전략 */}
          <AIAnalysisPanel ticker={s.ticker} stockName={s.name} />

          {s.memo && (
            <div className="bg-white/5 rounded-xl px-4 py-3 text-xs text-gray-400">
              📝 {s.memo}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
