// 나만의 시장 판독기 — 05-A 시장 등급 (종가 기준, 조회 전용)
import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { CheckCircle2, XCircle, HelpCircle, AlertTriangle, RefreshCw } from 'lucide-react'
import { getMarketGrade, getMarketHistory } from '../api'

const GRADE_STYLE = {
  RED:    'bg-red-500/20 text-red-300 border-red-500/40',
  ORANGE: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
  YELLOW: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  GREEN:  'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
}
const GRADE_DOT = { RED: '#ef4444', ORANGE: '#f97316', YELLOW: '#eab308', GREEN: '#10b981' }

const fmt = (x, d = 2) =>
  x === null || x === undefined ? '미확인' : Number(x).toLocaleString('ko-KR', { maximumFractionDigits: d })

function Mark({ ok }) {
  if (ok === true) return <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
  if (ok === false) return <XCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
  return <HelpCircle size={16} className="text-gray-500 shrink-0 mt-0.5" />
}

function CheckList({ title, items }) {
  return (
    <div className="bg-white/5 rounded-lg p-4">
      <div className="text-gray-200 text-sm font-semibold mb-3">{title}</div>
      <ul className="space-y-3">
        {items.map(c => (
          <li key={c.name} className="flex gap-2">
            <Mark ok={c.ok} />
            <div>
              <div className="text-sm text-gray-100">{c.name}</div>
              <div className="text-xs text-gray-400">{c.detail}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function MarketGradePanel() {
  const [summary, setSummary] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = () =>
    Promise.all([getMarketGrade(), getMarketHistory(60)])
      .then(([g, h]) => { setSummary(g); setHistory(h); setError(null) })
      .catch(e => setError(e?.message || String(e)))
      .finally(() => setLoading(false))

  const load = () => { setLoading(true); fetchData() }
  useEffect(() => { fetchData() }, [])

  const card = 'bg-[#1a1d2e] rounded-xl border border-white/5'

  if (error) return <div className={`${card} p-5 text-red-300`}>판독기 서버에 연결하지 못했습니다: {error}</div>
  if (loading && !summary) return <div className={`${card} p-5 text-gray-400`}>불러오는 중…</div>
  if (!summary || summary.status !== 'ok') {
    return (
      <div className={`${card} p-5 text-gray-300 space-y-2`}>
        <div className="font-semibold text-white">아직 기록된 종가가 없습니다</div>
        <div className="text-sm text-gray-400">
          평일 16:10·18:10에 자동으로 수집합니다. 서버 환경변수 KRX_ID / KRX_PW가 설정돼 있는지 확인해 주세요.
        </div>
      </div>
    )
  }

  const L = summary.latest
  const dq = summary.data_quality || {}
  const chart = history.map(h => ({ date: h.date.slice(5), close: h.close, ma20: h.ma20, grade: h.grade }))

  return (
    <div className="space-y-4">
      {/* 등급 헤더 */}
      <div className={`${card} p-5 flex flex-wrap items-center gap-4`}>
        <span className={`text-2xl font-extrabold px-4 py-2 rounded-lg border ${GRADE_STYLE[L.grade]}`}>{L.grade}</span>
        <div>
          <div className="text-white font-semibold">시장 등급 (05-A) · {L.date} 종가 기준</div>
          <div className="text-sm text-gray-400">
            코스피 {fmt(L.close)} · 20일선 {fmt(L.ma20)} · 60일선 {fmt(L.ma60)} · 외국인 {fmt(L.foreign_net_eok, 0)}억
          </div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-xs text-gray-400">이번 달 매수 한도</div>
          <div className="text-white font-bold">
            총자산의 {(L.budget_ratio * 100).toFixed(0)}% · {L.budget_scope}
          </div>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> 다시 판정
        </button>
      </div>

      {/* CIO 안건 */}
      {summary.cio_agenda?.length > 0 && (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-center gap-2 text-amber-300 font-semibold mb-2">
            <AlertTriangle size={16} /> CIO 안건
          </div>
          <ul className="list-disc ml-5 space-y-1 text-sm text-amber-100">
            {summary.cio_agenda.map(a => <li key={a}>{a}</li>)}
          </ul>
        </div>
      )}

      {L.events?.length > 0 && (
        <div className={`${card} p-4`}>
          <div className="text-gray-200 text-sm font-semibold mb-2">오늘 이벤트</div>
          <ul className="list-disc ml-5 space-y-1 text-sm text-gray-300">
            {L.events.map(e => <li key={e}>{e}</li>)}
          </ul>
        </div>
      )}

      {/* 조건표 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CheckList
          title={L.upgrade_target ? `${L.grade} → ${L.upgrade_target} 조건` : '상향 조건'}
          items={L.upgrade_checks || []}
        />
        <CheckList title="하향 감시" items={L.downgrade_watch || []} />
      </div>

      {/* 추이 */}
      {chart.length > 1 && (
        <div className={`${card} p-4`}>
          <div className="text-gray-200 text-sm font-semibold mb-2">코스피 종가와 20일선</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chart} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <XAxis dataKey="date" stroke="#6b7280" fontSize={11} />
              <YAxis stroke="#6b7280" fontSize={11} domain={['auto', 'auto']} width={56} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151' }}
                formatter={(v, n) => [fmt(v), n === 'close' ? '종가' : '20일선']}
              />
              <ReferenceLine y={summary.reference_low} stroke="#f59e0b" strokeDasharray="4 4"
                label={{ value: `기준 저점 ${fmt(summary.reference_low)}`, fill: '#f59e0b', fontSize: 11, position: 'insideBottomLeft' }} />
              <Line type="monotone" dataKey="ma20" stroke="#9ca3af" strokeDasharray="5 4" dot={false} />
              <Line type="monotone" dataKey="close" stroke="#60a5fa" strokeWidth={2}
                dot={({ cx, cy, payload }) => <circle key={payload.date} cx={cx} cy={cy} r={3} fill={GRADE_DOT[payload.grade]} />} />
            </LineChart>
          </ResponsiveContainer>
          <div className="text-xs text-gray-500 mt-1">점 색 = 그날 판정 등급</div>
        </div>
      )}

      <div className="text-xs text-gray-500">
        {!dq.ma60_history_ok && '⚠️ 60일선 계산용 과거 데이터 부족 · '}
        {dq.missing_foreign_days?.length > 0 && `⚠️ 외국인 수급 미확인: ${dq.missing_foreign_days.join(', ')} · `}
        규칙 판정 보조 도구입니다. 최종 결정은 CIO가 장 마감 후에 합니다.
      </div>
    </div>
  )
}
