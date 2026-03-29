import { formatKRW, formatNumber, formatPercent, profitColor, STAGE_COLORS } from '../utils'
import { ChevronRight, Target, ShieldAlert } from 'lucide-react'

const AI_SIGNAL_STYLES = {
  GOOD: 'text-emerald-400 bg-emerald-500/10',
  WATCH: 'text-amber-400 bg-amber-500/10',
  RISK: 'text-red-400 bg-red-500/10',
}

export default function StockCard({ stock, cash, onEdit, aiSignal }) {
  const evalValue = stock.current_price * stock.quantity
  const investValue = stock.avg_buy_price * stock.quantity
  const profitLoss = evalValue - investValue
  const profitRate = investValue > 0 ? (profitLoss / investValue) * 100 : 0

  const targetRate = stock.target_price > 0 && stock.current_price > 0
    ? (stock.current_price / stock.target_price) * 100
    : null

  const buyPower = cash > 0 && stock.current_price > 0
    ? Math.floor(cash / stock.current_price)
    : 0

  return (
    <div
      className="bg-[#1a1d2e] rounded-xl p-4 border border-white/5 hover:border-blue-500/30 cursor-pointer transition-all group"
      onClick={() => onEdit(stock)}
    >
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold">{stock.name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${STAGE_COLORS[stock.stage] || STAGE_COLORS['씨앗']}`}>
              {stock.stage}
            </span>
            {aiSignal && (
              <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${AI_SIGNAL_STYLES[aiSignal] || ''}`}>
                AI {aiSignal}
              </span>
            )}
          </div>
          <div className="text-gray-500 text-xs mt-0.5">{stock.ticker} · {stock.sector}</div>
        </div>
        <ChevronRight size={16} className="text-gray-600 group-hover:text-blue-400 transition-colors mt-0.5" />
      </div>

      {/* 현재가 / 손익 */}
      <div className="flex items-end justify-between mb-3">
        <div>
          <div className="text-gray-400 text-xs mb-0.5">현재가</div>
          <div className="text-white text-xl font-bold">{formatKRW(stock.current_price)}</div>
          {stock.avg_buy_price > 0 && (
            <div className="text-gray-500 text-xs">평균 {formatKRW(stock.avg_buy_price)}</div>
          )}
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${profitColor(profitLoss)}`}>
            {formatPercent(profitRate)}
          </div>
          <div className={`text-xs ${profitColor(profitLoss)}`}>
            {profitLoss >= 0 ? '+' : ''}{formatKRW(profitLoss)}
          </div>
        </div>
      </div>

      {/* 보유정보 */}
      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        <div className="bg-white/5 rounded-lg p-2">
          <div className="text-gray-500 mb-0.5">보유수량</div>
          <div className="text-gray-200 font-medium">{formatNumber(stock.quantity)}주</div>
        </div>
        <div className="bg-white/5 rounded-lg p-2">
          <div className="text-gray-500 mb-0.5">평가금액</div>
          <div className="text-gray-200 font-medium">{formatKRW(evalValue)}</div>
        </div>
      </div>

      {/* 목표가 달성률 */}
      {targetRate !== null && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="flex items-center gap-1 text-gray-400">
              <Target size={11} />
              목표가 {formatKRW(stock.target_price)}
            </span>
            <span className="text-blue-400">{targetRate.toFixed(1)}%</span>
          </div>
          <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${Math.min(targetRate, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* 손절가 & 추가매수 여력 */}
      <div className="flex items-center justify-between text-xs">
        {stock.stop_loss_price > 0 ? (
          <span className="flex items-center gap-1 text-red-400/70">
            <ShieldAlert size={11} />
            손절 {formatKRW(stock.stop_loss_price)}
          </span>
        ) : <span />}
        {buyPower > 0 && (
          <span className="text-gray-500">
            현금으로 <span className="text-gray-300">{formatNumber(buyPower)}주</span> 추가매수 가능
          </span>
        )}
      </div>

      {stock.memo && (
        <div className="mt-2 text-xs text-gray-500 bg-white/3 rounded-lg px-2 py-1.5 line-clamp-1">
          {stock.memo}
        </div>
      )}
    </div>
  )
}
