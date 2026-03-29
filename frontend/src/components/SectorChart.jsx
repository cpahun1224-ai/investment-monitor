import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { formatKRW } from '../utils'
import { SECTOR_COLORS } from '../utils'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-[#1a1d2e] border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-white font-medium mb-1">{d.sector}</div>
      <div className="text-gray-300">{formatKRW(d.value)}</div>
      <div className="text-blue-400">{d.weight}%</div>
    </div>
  )
}

export default function SectorChart({ data }) {
  if (!data?.length) return null

  return (
    <div className="bg-[#1a1d2e] rounded-xl p-5 border border-white/5">
      <div className="text-white font-semibold mb-4">섹터별 비중</div>
      <div className="flex flex-col lg:flex-row items-center gap-4">
        <div className="w-full lg:w-64 h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                dataKey="value"
                strokeWidth={1}
                stroke="#0f1117"
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex-1 grid grid-cols-2 gap-1.5 w-full">
          {data.map((d, i) => (
            <div key={d.sector} className="flex items-center gap-2 text-xs">
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }}
              />
              <span className="text-gray-400 truncate flex-1">{d.sector}</span>
              <span className="text-gray-200 font-medium">{d.weight}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
