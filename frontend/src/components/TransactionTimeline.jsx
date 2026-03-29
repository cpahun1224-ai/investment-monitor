import { formatKRW, formatNumber } from '../utils'

export default function TransactionTimeline({ transactions }) {
  if (!transactions?.length) return (
    <div className="text-center text-gray-500 py-10 text-sm">거래내역이 없습니다.</div>
  )

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }

  return (
    <div className="space-y-2">
      {transactions.map((txn) => (
        <div
          key={txn.id}
          className="flex items-center gap-3 bg-[#1a1d2e] rounded-xl px-4 py-3 border border-white/5"
        >
          <div className={`w-1.5 h-10 rounded-full flex-shrink-0 ${txn.transaction_type === '매수' ? 'bg-emerald-500' : 'bg-red-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-white text-sm font-medium">{txn.stock_name}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                txn.transaction_type === '매수'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {txn.transaction_type}
              </span>
              <span className="text-gray-500 text-xs">{txn.ticker}</span>
            </div>
            <div className="text-gray-400 text-xs mt-0.5">
              {formatNumber(txn.quantity)}주 × {formatKRW(txn.price)}
            </div>
            {txn.memo && <div className="text-gray-600 text-xs mt-0.5">{txn.memo}</div>}
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-white text-sm font-medium">{formatKRW(txn.amount)}</div>
            <div className="text-gray-500 text-xs">{formatDate(txn.created_at)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
