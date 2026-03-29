import { useState, useEffect, useCallback, useRef } from 'react'
import { getStocks, getPortfolioSummary, getSectorWeights, getTransactions, refreshPrices, getSignals, getRebalance, getAnalysis, runBatchAnalysis } from './api'
import SummaryCards from './components/SummaryCards'
import StockCard from './components/StockCard'
import StockEditModal from './components/StockEditModal'
import SectorChart from './components/SectorChart'
import TransactionTimeline from './components/TransactionTimeline'
import AddStockModal from './components/AddStockModal'
import CashEditModal from './components/CashEditModal'
import SignalsPanel from './components/SignalsPanel'
import RebalancePanel from './components/RebalancePanel'
import { formatKRW } from './utils'
import { LayoutDashboard, List, Clock, Plus, RefreshCw, Edit2, Activity, BarChart3, Wifi, WifiOff, Bot } from 'lucide-react'

const TABS = [
  { id: 'dashboard', label: '대시보드', icon: LayoutDashboard },
  { id: 'guide',     label: '매수/매도 가이드', icon: Activity },
  { id: 'rebalance', label: '리밸런싱', icon: BarChart3 },
  { id: 'stocks',    label: '종목 관리', icon: List },
  { id: 'history',   label: '거래내역', icon: Clock },
]

// 장 시간 체크 (09:00~15:30 평일)
function isMarketOpen() {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  const h = now.getHours(), m = now.getMinutes()
  const t = h * 60 + m
  return t >= 540 && t <= 930
}

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [stocks, setStocks] = useState([])
  const [summary, setSummary] = useState(null)
  const [sectors, setSectors] = useState([])
  const [transactions, setTransactions] = useState([])
  const [signals, setSignals] = useState([])
  const [rebalance, setRebalance] = useState(null)
  const [aiSignals, setAiSignals] = useState({})
  const [batchAnalyzing, setBatchAnalyzing] = useState(false)
  const [editStock, setEditStock] = useState(null)
  const [showAddStock, setShowAddStock] = useState(false)
  const [showCashEdit, setShowCashEdit] = useState(false)
  const [loading, setLoading] = useState(true)
  const [priceRefreshing, setPriceRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [marketOpen, setMarketOpen] = useState(isMarketOpen())
  const [filter, setFilter] = useState('전체')
  const autoRefreshRef = useRef(null)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [s, sum, sec, txns, sigs, reb] = await Promise.all([
        getStocks(),
        getPortfolioSummary(),
        getSectorWeights(),
        getTransactions(),
        getSignals(),
        getRebalance(),
      ])
      setStocks(s)
      setSummary(sum)
      setSectors(sec)
      setTransactions(txns)
      setSignals(sigs)
      setRebalance(reb)
      setLastUpdated(new Date())
      // 캐시된 AI 시그널 로드
      const aiMap = {}
      await Promise.allSettled(s.map(async (stock) => {
        try {
          const res = await getAnalysis(stock.ticker)
          if (res.cached && res.analysis?.signal) {
            aiMap[stock.ticker] = res.analysis.signal
          }
        } catch {}
      }))
      setAiSignals(aiMap)
    } catch (e) {
      console.error('데이터 로드 실패:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleBatchAnalysis = useCallback(async () => {
    setBatchAnalyzing(true)
    try {
      const result = await runBatchAnalysis()
      const aiMap = {}
      result.results.forEach(r => {
        if (r.ok && r.signal) aiMap[r.ticker] = r.signal
      })
      setAiSignals(aiMap)
    } catch (e) {
      console.error('일괄 분석 실패:', e)
    } finally {
      setBatchAnalyzing(false)
    }
  }, [])

  // 시세 자동 갱신 핸들러 (네이버 금융)
  const handlePriceRefresh = useCallback(async (silent = false) => {
    if (!silent) setPriceRefreshing(true)
    try {
      await refreshPrices()
      await fetchAll()
    } catch (e) {
      console.error('시세 갱신 실패:', e)
    } finally {
      if (!silent) setPriceRefreshing(false)
    }
  }, [fetchAll])

  // 장 시간 30초 자동 갱신
  useEffect(() => {
    fetchAll()
    const tick = setInterval(() => {
      const open = isMarketOpen()
      setMarketOpen(open)
      if (open) handlePriceRefresh(true)
    }, 30000)
    autoRefreshRef.current = tick
    return () => clearInterval(tick)
  }, [fetchAll, handlePriceRefresh])

  const handleStockSave = (updated) => {
    setStocks(prev => prev.map(s => s.ticker === updated.ticker ? updated : s))
    fetchAll()
  }

  const handleAddStock = (newStock) => {
    setStocks(prev => [...prev, newStock])
    fetchAll()
  }

  const handleCashSave = () => { fetchAll() }

  const formatTime = (d) => d
    ? `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`
    : '—'

  const stages = ['전체', '씨앗', '에코', '피라미딩']
  const filteredStocks = filter === '전체' ? stocks : stocks.filter(s => s.stage === filter)
  const riskCount = signals.filter(s => s.signal === 'RISK').length

  return (
    <div className="min-h-screen bg-[#0f1117] text-white">
      {/* RISK 알림 배너 */}
      {riskCount > 0 && (
        <div className="bg-red-500/10 border-b border-red-500/20 text-center py-1.5 text-xs text-red-400">
          🚨 RISK 종목 {riskCount}개 — 매수/매도 가이드 탭에서 확인하세요
        </div>
      )}

      {/* 헤더 */}
      <header className="border-b border-white/5 bg-[#0f1117]/95 sticky top-0 z-40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-sm font-bold">P</div>
            <div>
              <div className="text-white font-bold text-sm leading-tight">Portfolio Monitor</div>
              <div className="flex items-center gap-2 mt-0.5">
                {marketOpen
                  ? <span className="flex items-center gap-1 text-emerald-400 text-xs"><Wifi size={10} /> 장 시간 · 30초 자동갱신</span>
                  : <span className="flex items-center gap-1 text-gray-500 text-xs"><WifiOff size={10} /> 장 마감</span>
                }
                {lastUpdated && (
                  <span className="text-gray-600 text-xs">업데이트 {formatTime(lastUpdated)}</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCashEdit(true)}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg transition-colors"
            >
              <Edit2 size={12} />
              <span className="hidden sm:inline">현금 </span>{summary ? formatKRW(summary.cash_balance) : '—'}
            </button>
            <button
              onClick={() => handlePriceRefresh(false)}
              disabled={priceRefreshing}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} className={priceRefreshing ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">시세 갱신</span>
            </button>
            <button
              onClick={handleBatchAnalysis}
              disabled={batchAnalyzing}
              className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Bot size={12} className={batchAnalyzing ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">{batchAnalyzing ? 'AI 분석 중...' : '전체 AI 분석'}</span>
            </button>
            <button
              onClick={fetchAll}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg transition-colors"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">새로고침</span>
            </button>
          </div>
        </div>

        {/* 탭 */}
        <div className="max-w-7xl mx-auto px-4 overflow-x-auto">
          <div className="flex gap-1 min-w-max">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  tab === id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <Icon size={14} />
                {label}
                {id === 'guide' && riskCount > 0 && (
                  <span className="ml-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                    {riskCount}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {loading && !stocks.length ? (
          <div className="flex items-center justify-center h-48 text-gray-400">
            <RefreshCw size={20} className="animate-spin mr-2" />
            데이터 로딩 중...
          </div>
        ) : (
          <>
            {/* 대시보드 탭 */}
            {tab === 'dashboard' && (
              <div className="space-y-6">
                <SummaryCards summary={summary} />

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    <SectorChart data={sectors} />
                  </div>

                  {/* 수익/손실 TOP 종목 */}
                  <div className="bg-[#1a1d2e] rounded-xl p-5 border border-white/5">
                    <div className="text-white font-semibold mb-4">수익률 현황</div>
                    <div className="space-y-2">
                      {[...stocks]
                        .filter(s => s.avg_buy_price > 0)
                        .sort((a, b) => {
                          const rA = (a.current_price - a.avg_buy_price) / a.avg_buy_price
                          const rB = (b.current_price - b.avg_buy_price) / b.avg_buy_price
                          return rB - rA
                        })
                        .map(s => {
                          const rate = ((s.current_price - s.avg_buy_price) / s.avg_buy_price) * 100
                          return (
                            <div
                              key={s.ticker}
                              className="flex items-center gap-3 cursor-pointer hover:bg-white/5 rounded-lg px-2 py-1.5 transition-colors"
                              onClick={() => setEditStock(s)}
                            >
                              <div className="flex-1 text-sm text-gray-200 truncate">{s.name}</div>
                              <div className="w-24 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${rate >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                                  style={{ width: `${Math.min(Math.abs(rate) * 2, 100)}%` }}
                                />
                              </div>
                              <div className={`text-xs font-medium w-14 text-right ${rate >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {rate >= 0 ? '+' : ''}{rate.toFixed(1)}%
                              </div>
                            </div>
                          )
                        })}
                    </div>
                  </div>
                </div>

                {/* 오늘의 주목 종목 TOP3 */}
                {Object.keys(aiSignals).length > 0 && (() => {
                  const ranked = stocks
                    .filter(s => aiSignals[s.ticker])
                    .sort((a, b) => {
                      const order = { RISK: 0, WATCH: 1, GOOD: 2 }
                      const diff = (order[aiSignals[b.ticker]] || 1) - (order[aiSignals[a.ticker]] || 1)
                      if (diff !== 0) return diff
                      const rA = a.avg_buy_price > 0 ? (a.current_price - a.avg_buy_price) / a.avg_buy_price : 0
                      const rB = b.avg_buy_price > 0 ? (b.current_price - b.avg_buy_price) / b.avg_buy_price : 0
                      return rB - rA
                    })
                    .slice(0, 3)
                  if (!ranked.length) return null
                  const signalBg = { GOOD: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400', WATCH: 'bg-amber-500/10 border-amber-500/20 text-amber-400', RISK: 'bg-red-500/10 border-red-500/20 text-red-400' }
                  return (
                    <div className="bg-[#1a1d2e] rounded-xl p-5 border border-white/5">
                      <div className="flex items-center gap-2 text-white font-semibold mb-4">
                        <Bot size={16} className="text-purple-400" />
                        AI 주목 종목 TOP3
                      </div>
                      <div className="space-y-2">
                        {ranked.map((s, i) => {
                          const sig = aiSignals[s.ticker]
                          const rate = s.avg_buy_price > 0 ? ((s.current_price - s.avg_buy_price) / s.avg_buy_price * 100) : 0
                          return (
                            <div key={s.ticker} className="flex items-center gap-3 cursor-pointer hover:bg-white/5 rounded-lg px-2 py-1.5 transition-colors" onClick={() => setEditStock(s)}>
                              <div className="text-gray-600 text-sm font-bold w-4">{i + 1}</div>
                              <div className="flex-1 text-sm text-gray-200 truncate">{s.name}</div>
                              <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium border ${signalBg[sig] || ''}`}>{sig}</span>
                              <div className={`text-xs font-medium w-14 text-right ${rate >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {rate >= 0 ? '+' : ''}{rate.toFixed(1)}%
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                })()}

                {/* 대시보드에서도 전체 종목 카드 */}
                <div>
                  <div className="text-white font-semibold mb-4">전체 종목 ({stocks.length})</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {stocks.map(stock => (
                      <StockCard
                        key={stock.ticker}
                        stock={stock}
                        cash={summary?.cash_balance || 0}
                        onEdit={setEditStock}
                        aiSignal={aiSignals[stock.ticker]}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 매수/매도 가이드 탭 */}
            {tab === 'guide' && (
              <div className="space-y-6">
                <SignalsPanel
                  signals={signals}
                  cash={summary?.cash_balance || 0}
                  onEditStock={setEditStock}
                />
              </div>
            )}

            {/* 리밸런싱 탭 */}
            {tab === 'rebalance' && (
              <div className="space-y-6">
                <RebalancePanel data={rebalance} />
              </div>
            )}

            {/* 종목 관리 탭 */}
            {tab === 'stocks' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex gap-2 flex-wrap">
                    {stages.map(s => (
                      <button
                        key={s}
                        onClick={() => setFilter(s)}
                        className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                          filter === s
                            ? 'bg-blue-600 text-white'
                            : 'bg-white/5 text-gray-400 hover:bg-white/10'
                        }`}
                      >
                        {s} {s !== '전체' && `(${stocks.filter(st => st.stage === s).length})`}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => setShowAddStock(true)}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    <Plus size={16} />
                    종목 추가
                  </button>
                </div>

                {filteredStocks.length === 0 ? (
                  <div className="text-center text-gray-500 py-16 text-sm">
                    해당 단계의 종목이 없습니다.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filteredStocks.map(stock => (
                      <StockCard
                        key={stock.ticker}
                        stock={stock}
                        cash={summary?.cash_balance || 0}
                        onEdit={setEditStock}
                        aiSignal={aiSignals[stock.ticker]}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 거래내역 탭 */}
            {tab === 'history' && (
              <div className="space-y-4">
                <div className="text-white font-semibold">최근 거래내역</div>
                <TransactionTimeline transactions={transactions} />
              </div>
            )}
          </>
        )}
      </main>

      {/* 모달들 */}
      {editStock && (
        <StockEditModal
          stock={editStock}
          onClose={() => setEditStock(null)}
          onSave={handleStockSave}
        />
      )}
      {showAddStock && (
        <AddStockModal
          onClose={() => setShowAddStock(false)}
          onSave={handleAddStock}
        />
      )}
      {showCashEdit && summary && (
        <CashEditModal
          currentCash={summary.cash_balance}
          onClose={() => setShowCashEdit(false)}
          onSave={handleCashSave}
        />
      )}
    </div>
  )
}
