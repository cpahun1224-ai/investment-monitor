import { useState } from 'react'
import { X } from 'lucide-react'
import { createStock } from '../api'

const STAGES = ['씨앗', '에코', '피라미딩']
const SECTORS = ['반도체', '반도체부품', '반도체소재', '소재', '방산', '조선', '바이오', '에너지', '식품', 'IT', '금융', '기타']

export default function AddStockModal({ onClose, onSave }) {
  const [form, setForm] = useState({
    name: '', ticker: '', quantity: 0, avg_buy_price: 0,
    current_price: 0, sector: '기타', stage: '씨앗',
    target_price: 0, stop_loss_price: 0, memo: ''
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!form.name || !form.ticker) return alert('종목명과 티커를 입력하세요.')
    setSaving(true)
    try {
      const created = await createStock({
        ...form,
        quantity: Number(form.quantity),
        avg_buy_price: Number(form.avg_buy_price),
        current_price: Number(form.current_price),
        target_price: Number(form.target_price),
        stop_loss_price: Number(form.stop_loss_price),
      })
      onSave(created)
      onClose()
    } catch (e) {
      alert('저장 실패: ' + (e.response?.data?.detail || e.message))
    } finally {
      setSaving(false)
    }
  }

  const Field = ({ label, field, type = 'text' }) => (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <input
        type={type}
        value={form[field]}
        onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
        className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
      />
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 overflow-y-auto">
      <div className="bg-[#1a1d2e] rounded-2xl w-full max-w-md border border-white/10 shadow-2xl my-4">
        <div className="flex items-center justify-between p-5 border-b border-white/5">
          <div className="text-white font-semibold text-lg">종목 추가</div>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="종목명" field="name" />
            <Field label="티커 (예: 005930)" field="ticker" />
            <Field label="보유수량" field="quantity" type="number" />
            <Field label="평균매수가" field="avg_buy_price" type="number" />
            <Field label="현재가" field="current_price" type="number" />
            <Field label="목표가" field="target_price" type="number" />
            <Field label="손절가" field="stop_loss_price" type="number" />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">섹터</label>
            <select
              value={form.sector}
              onChange={e => setForm(f => ({ ...f, sector: e.target.value }))}
              className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-2">투자 단계</label>
            <div className="flex gap-2">
              {STAGES.map(s => (
                <button
                  key={s}
                  onClick={() => setForm(f => ({ ...f, stage: s }))}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    form.stage === s ? 'bg-blue-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-3 p-5 pt-0">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-lg bg-white/5 text-gray-300 hover:bg-white/10 text-sm">취소</button>
          <button onClick={handleSave} disabled={saving} className="flex-1 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm disabled:opacity-50">
            {saving ? '추가 중...' : '추가'}
          </button>
        </div>
      </div>
    </div>
  )
}
