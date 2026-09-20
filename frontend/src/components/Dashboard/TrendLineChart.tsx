import React, { useState, useEffect } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getSpendingTrends } from '../../api/summary'
import type { SpendingTrendItem } from '../../types'
import { useMonth } from '../../context/MonthContext'

interface TrendLineChartProps {
  initialMonths?: number
}

export function TrendLineChart({ initialMonths = 6 }: TrendLineChartProps) {
  const { availableMonths } = useMonth()
  const [rangeMonths, setRangeMonths] = useState<number>(initialMonths)
  const [trends, setTrends] = useState<SpendingTrendItem[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // Show 12M only when there are at least 12 months of data available
  const has12Months = availableMonths.length >= 12

  useEffect(() => {
    setIsLoading(true)
    getSpendingTrends(rangeMonths)
      .then((data) => setTrends(data))
      .catch((err) => console.error('Failed to load spending trends:', err))
      .finally(() => setIsLoading(false))
  }, [rangeMonths])

  const chartData = trends.map((t) => ({
    name: t.month_name,
    inflow: Math.round(t.income_minor / 100),
    outflow: Math.round(t.expense_minor / 100),
    income_display: t.income_display,
    expense_display: t.expense_display,
    net_savings_display: t.net_savings_display,
  }))

  const rangeOptions = [
    { label: '3M', val: 3 },
    { label: '6M', val: 6 },
    ...(has12Months ? [{ label: '12M', val: 12 }] : []),
  ]

  return (
    <div className="rounded-xl border border-[#E7E5E4] dark:border-[#232329] p-5 bg-[#FFFFFF] dark:bg-[#131318] transition-colors">
      {/* Header & Minimal Segmented Control */}
      <div className="flex items-center justify-between border-b border-[#E7E5E4] dark:border-[#232329] pb-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-[#1C1917] dark:text-[#EDEDEF]">
            Cash Flow Trajectory
          </h3>
          <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-0.5">
            Monthly Inflow vs Outflow
          </p>
        </div>

        {/* Segmented Control Pill */}
        <div className="flex items-center gap-0.5 bg-[#FAFAF9] dark:bg-[#18181F] p-0.5 rounded-lg border border-[#E7E5E4] dark:border-[#232329]">
          {rangeOptions.map((r) => (
            <button
              key={r.val}
              onClick={() => setRangeMonths(r.val)}
              className={`px-2 py-0.5 rounded-md text-xs font-medium transition-colors ${
                rangeMonths === r.val
                  ? 'bg-[#FFFFFF] dark:bg-[#232329] text-[#1C1917] dark:text-[#EDEDEF] shadow-2xs'
                  : 'text-[#78716C] hover:text-[#1C1917] dark:text-[#8B8B95] dark:hover:text-[#EDEDEF]'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="h-60 mt-4 w-full">
        {isLoading ? (
          <div className="h-full flex items-center justify-center text-xs text-[#78716C] dark:text-[#8B8B95]">
            Loading trajectory...
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-[#78716C] dark:text-[#8B8B95]">
            No historical trend data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="outflowFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="inflowFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#16A34A" stopOpacity={0.10} />
                  <stop offset="95%" stopColor="#16A34A" stopOpacity={0.0} />
                </linearGradient>
              </defs>

              {/* Faint horizontal lines only */}
              <CartesianGrid
                vertical={false}
                stroke="#E7E5E4"
                className="dark:stroke-[#232329]"
                strokeDasharray="2 2"
              />
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: '#78716C' }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: '#78716C' }}
                tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
              />

              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload
                    return (
                      <div className="rounded-lg p-2.5 shadow-lg border border-[#E7E5E4] dark:border-[#232329] text-xs bg-[#FFFFFF] dark:bg-[#131318] text-[#1C1917] dark:text-[#EDEDEF] space-y-1">
                        <div className="font-semibold text-xs border-b border-[#E7E5E4] dark:border-[#232329] pb-1">
                          {label}
                        </div>
                        <div className="flex justify-between gap-3 text-xs">
                          <span className="text-[#16A34A] dark:text-[#22C55E]">Inflow:</span>
                          <span className="tabular-nums font-sans font-medium">{data.income_display}</span>
                        </div>
                        <div className="flex justify-between gap-3 text-xs">
                          <span className="text-[#4F46E5] dark:text-[#818CF8]">Outflow:</span>
                          <span className="tabular-nums font-sans font-medium">{data.expense_display}</span>
                        </div>
                        <div className="flex justify-between gap-3 text-xs pt-1 border-t border-[#E7E5E4] dark:border-[#232329]">
                          <span className="text-[#78716C] dark:text-[#8B8B95]">Net:</span>
                          <span className="tabular-nums font-sans font-medium">{data.net_savings_display}</span>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />

              <Area
                type="monotone"
                dataKey="inflow"
                name="Inflow"
                stroke="#16A34A"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#inflowFill)"
              />
              <Area
                type="monotone"
                dataKey="outflow"
                name="Outflow"
                stroke="#4F46E5"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#outflowFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
