import { formatKRW, formatPercent, profitColor } from '../utils'
import { TrendingUp, Wallet, BarChart2, DollarSign } from 'lucide-react'

const Card = ({ icon: Icon, label, value, valueClass, sub }) => (
  <div className="bg-[#1a1d2e] rounded-xl p-5 border border-white/5">
    <div className="flex items-center gap-2 text-gray-400 text-sm mb-3">
      <Icon size={15} />
      <span>{label}</span>
    </div>
    <div className={`text-2xl font-bold ${valueClass || 'text-white'}`}>{value}</div>
    {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
  </div>
)

export default function SummaryCards({ summary }) {
  if (!summary) return null
  const { total_balance, total_invested, total_profit_loss, profit_loss_rate, cash_balance, stock_value } = summary

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card
        icon={Wallet}
        label="총 잔고"
        value={formatKRW(total_balance)}
        sub={`주식 ${formatKRW(stock_value)} + 현금 ${formatKRW(cash_balance)}`}
      />
      <Card
        icon={DollarSign}
        label="총 투자금"
        value={formatKRW(total_invested)}
      />
      <Card
        icon={BarChart2}
        label="총 평가손익"
        value={formatKRW(total_profit_loss)}
        valueClass={profitColor(total_profit_loss)}
      />
      <Card
        icon={TrendingUp}
        label="수익률"
        value={formatPercent(profit_loss_rate)}
        valueClass={profitColor(profit_loss_rate)}
        sub={`현금 비중 ${cash_balance && total_balance ? ((cash_balance / total_balance) * 100).toFixed(1) : 0}%`}
      />
    </div>
  )
}
