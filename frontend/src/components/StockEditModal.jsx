import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { updateStock } from '../api'
import { STAGE_COLORS } from '../utils'

const STAGES = ['씨앗', '에코', '피라미딩']

export default function StockEditModal({ stock, onClose, onSave }) {
  const [form, setForm] = useState({
    current_price: stock.current_price || 0,
    avg_buy_price: stock.avg_buy_price || 0,
    quantity: stock.quantity || 0,
    target_price: stock.target_price || 0,
    stop_loss_price: stock.stop_loss_price || 0,
    stage: stock.stage || '씨앗',
    memo: stock.memo || '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateStock(stock.ticker, {
        current_price: Number(form.current_price),
        avg_buy_price: Number(form.avg_buy_price),
        quantity: Number(form.quantity),
        target_price: Number(form.target_price),
        stop_loss_price: Number(form.stop_loss_price),
        stage: form.stage,
        memo: form.memo,
      })
      onSave(updated)
      onClose()
    } catch (e) {
      alert('저장 실패: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  const Field = ({ label, field, type = 'number' }) => (
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
        className="bg-[#1a1d2e] rounded-2xl w-full max-w-md border border-white/10 shadow-2xl max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/5 shrink-0">
          <div>
            <div className="text-white font-semibold text-lg">{stock.name}</div>
            <div className="text-gray-400 text-sm">{stock.ticker} · {stock.sector}</div>
          </div>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          <div className="grid grid-cols-2 gap-3">
            <Field label="현재가 (원)" field="current_price" />
            <Field label="평균매수가 (원)" field="avg_buy_price" />
            <Field label="보유수량 (주)" field="quantity" />
            <Field label="목표가 (원)" field="target_price" />
            <Field label="손절가 (원)" field="stop_loss_price" />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-2">투자 단계</label>
            <div className="flex gap-2">
              {STAGES.map(s => (
                <button
                  key={s}
                  onClick={() => setForm(f => ({ ...f, stage: s }))}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    form.stage === s
                      ? STAGE_COLORS[s]
                      : 'bg-white/5 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">메모</label>
            <textarea
              value={form.memo}
              onChange={e => setForm(f => ({ ...f, memo: e.target.value }))}
              rows={2}
              className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white text-sm resize-none focus:outline-none focus:border-blue-500"
              placeholder="메모를 입력하세요..."
            />
          </div>
        </div>

        <div className="flex gap-3 p-5 pt-0 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-lg bg-white/5 text-gray-300 hover:bg-white/10 transition-colors text-sm"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors text-sm disabled:opacity-50"
          >
            {saving ? '저장 중...' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}
