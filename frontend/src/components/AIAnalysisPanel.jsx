import { useState, useEffect } from 'react'
import { Bot, RefreshCw, TrendingUp, TrendingDown, Newspaper, FileText, Lightbulb, AlertTriangle, Rocket } from 'lucide-react'
import { getAnalysis, runAnalysis } from '../api'

const SIGNAL_STYLES = {
  GOOD: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400', label: 'GOOD' },
  WATCH: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', dot: 'bg-amber-400', label: 'WATCH' },
  RISK: { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400', dot: 'bg-red-400', label: 'RISK' },
}

const ACTION_COLORS = {
  '매수강화': 'text-emerald-400 bg-emerald-500/10',
  '유지': 'text-blue-400 bg-blue-500/10',
  '부분매도': 'text-amber-400 bg-amber-500/10',
  '전량매도': 'text-red-400 bg-red-500/10',
}

function formatTime(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function isToday(iso) {
  if (!iso) return false
  const d = new Date(iso)
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

export default function AIAnalysisPanel({ ticker, stockName }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    setData(null)
    getAnalysis(ticker).then(setData).catch(() => {})
  }, [ticker])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const result = await runAnalysis(ticker)
      setData(result)
    } catch (e) {
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  const analysis = data?.analysis
  const signal = analysis?.signal
  const style = signal ? SIGNAL_STYLES[signal] : null
  const actionColor = analysis?.strategy?.action ? (ACTION_COLORS[analysis.strategy.action] || 'text-gray-400 bg-white/5') : ''

  const lastTime = data?.created_at
  const cached = data?.cached

  return (
    <div className="bg-[#12141f] rounded-xl border border-white/5 overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-blue-400" />
          <span className="text-sm font-medium text-gray-200">AI 투자전략</span>
          {lastTime && (
            <span className="text-xs text-gray-600">
              {isToday(lastTime) ? `오늘 ${formatTime(lastTime)}` : new Date(lastTime).toLocaleDateString('ko-KR', {month:'short',day:'numeric'})}
              {cached ? ' (캐시)' : ' (신규)'}
            </span>
          )}
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={11} className={analyzing ? 'animate-spin' : ''} />
          {analyzing ? '분석 중...' : '분석하기'}
        </button>
      </div>

      {!analysis ? (
        <div className="px-4 py-6 text-center text-gray-600 text-sm">
          {analyzing ? (
            <div className="flex items-center justify-center gap-2 text-blue-400">
              <RefreshCw size={14} className="animate-spin" />
              Gemini AI가 분석 중입니다...
            </div>
          ) : (
            <span>"분석하기" 버튼을 눌러 AI 투자전략을 생성하세요</span>
          )}
        </div>
      ) : (
        <div className="p-4 space-y-3">

          {/* 시그널 */}
          {style && (
            <div className={`rounded-xl p-3 border ${style.bg} ${style.border}`}>
              <div className="flex items-center gap-2 mb-1">
                <div className={`w-2 h-2 rounded-full ${style.dot}`} />
                <span className={`font-bold text-sm ${style.text}`}>{style.label}</span>
              </div>
              {analysis.signal_reason && (
                <div className="text-gray-300 text-xs leading-relaxed">{analysis.signal_reason}</div>
              )}
            </div>
          )}

          {/* 뉴스 요약 */}
          {(analysis.market_summary || analysis.news_summary) && (
            <div className="bg-white/5 rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-gray-400 text-xs font-medium mb-2">
                <Newspaper size={12} />
                뉴스 요약
              </div>
              <div className="text-gray-300 text-xs leading-relaxed">
                {analysis.market_summary || analysis.news_summary}
              </div>
            </div>
          )}

          {/* 공시 요약 */}
          {(analysis.analyst_view || analysis.dart_summary) && (
            <div className="bg-white/5 rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-gray-400 text-xs font-medium mb-2">
                <FileText size={12} />
                애널리스트 / 공시
              </div>
              <div className="text-gray-300 text-xs leading-relaxed">
                {analysis.analyst_view || analysis.dart_summary}
              </div>
            </div>
          )}

          {/* 투자전략 */}
          {analysis.strategy && (
            <div className="bg-white/5 rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-gray-400 text-xs font-medium mb-2">
                <Lightbulb size={12} />
                투자전략
              </div>
              <div className="space-y-1.5 text-xs">
                {analysis.strategy.short_term && (
                  <div className="flex gap-2">
                    <span className="text-gray-500 shrink-0 w-8">단기</span>
                    <span className="text-gray-300 leading-relaxed">{analysis.strategy.short_term}</span>
                  </div>
                )}
                {analysis.strategy.mid_term && (
                  <div className="flex gap-2">
                    <span className="text-gray-500 shrink-0 w-8">중기</span>
                    <span className="text-gray-300 leading-relaxed">{analysis.strategy.mid_term}</span>
                  </div>
                )}
                {analysis.strategy.action && (
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/5">
                    <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${actionColor}`}>
                      {analysis.strategy.action}
                    </span>
                    {analysis.strategy.action_reason && (
                      <span className="text-gray-400 text-xs">{analysis.strategy.action_reason}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 리스크 & 상승촉매 */}
          {((analysis.risk_factors || analysis.risks) || (analysis.catalysts)) && (
            <div className="grid grid-cols-2 gap-2">
              {(analysis.risk_factors || analysis.risks) && (
                <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-3">
                  <div className="flex items-center gap-1 text-red-400 text-xs font-medium mb-2">
                    <AlertTriangle size={11} />
                    리스크
                  </div>
                  <ul className="space-y-1">
                    {(analysis.risk_factors || analysis.risks).map((r, i) => (
                      <li key={i} className="text-gray-400 text-xs leading-relaxed">• {r}</li>
                    ))}
                  </ul>
                </div>
              )}
              {analysis.catalysts && (
                <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3">
                  <div className="flex items-center gap-1 text-emerald-400 text-xs font-medium mb-2">
                    <Rocket size={11} />
                    상승촉매
                  </div>
                  <ul className="space-y-1">
                    {analysis.catalysts.map((c, i) => (
                      <li key={i} className="text-gray-400 text-xs leading-relaxed">• {c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* 다음 단계 조건 */}
          {(analysis.next_stage_condition || analysis.next_stage) && (
            <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl px-3 py-2.5">
              <div className="text-blue-400 text-xs font-medium mb-1">다음 단계 진입 조건</div>
              <div className="text-gray-300 text-xs leading-relaxed">
                {analysis.next_stage_condition || analysis.next_stage}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
