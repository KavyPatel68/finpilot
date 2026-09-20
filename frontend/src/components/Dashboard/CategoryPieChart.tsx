import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { CategorySpend } from '../../types'

interface CategoryPieChartProps {
  categories: CategorySpend[]
  totalExpenseMinor: number
  onCategoryClick?: (category: string) => void
}

export function CategoryPieChart({
  categories,
  totalExpenseMinor,
  onCategoryClick,
}: CategoryPieChartProps) {
  const navigate = useNavigate()
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const handleCategorySelect = (categoryName: string) => {
    const next = selectedCategory === categoryName ? null : categoryName
    setSelectedCategory(next)
    if (onCategoryClick) {
      onCategoryClick(categoryName)
    } else {
      navigate(`/transactions?category=${encodeURIComponent(categoryName)}`)
    }
  }

  // Filter out any own-account transfers if present in categories
  const filteredCategories = categories.filter((c) => c.category !== 'Transfers')

  return (
    <div className="rounded-xl border border-[#E7E5E4] dark:border-[#232329] p-5 bg-[#FFFFFF] dark:bg-[#131318] transition-colors">
      <div className="flex items-center justify-between border-b border-[#E7E5E4] dark:border-[#232329] pb-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-[#1C1917] dark:text-[#EDEDEF]">
            Spending by Category
          </h3>
          <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-0.5">
            Ranked discretionary and fixed outflows
          </p>
        </div>
        {selectedCategory && (
          <button
            onClick={() => handleCategorySelect(selectedCategory)}
            className="text-xs font-medium text-[#4F46E5] dark:text-[#818CF8] hover:underline"
          >
            Clear filter
          </button>
        )}
      </div>

      {/* Ranked Horizontal Bar List */}
      <div className="mt-4 space-y-3.5">
        {filteredCategories.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#78716C] dark:text-[#8B8B95]">
            No categorized expenses this period
          </div>
        ) : (
          filteredCategories.map((cat) => {
            const isSelected = selectedCategory === cat.category
            return (
              <div
                key={cat.category}
                onClick={() => handleCategorySelect(cat.category)}
                className={`group cursor-pointer p-2 rounded-lg transition-colors ${
                  isSelected
                    ? 'bg-[#4F46E5]/10 dark:bg-[#818CF8]/10'
                    : 'hover:bg-[#FAFAF9] dark:hover:bg-[#1A1A22]'
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-medium text-[#1C1917] dark:text-[#EDEDEF]">
                    {cat.category}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[#1C1917] dark:text-[#EDEDEF] tabular-nums font-sans font-medium">
                      {cat.amount_display}
                    </span>
                    <span className="text-[11px] text-[#78716C] dark:text-[#8B8B95] w-9 text-right tabular-nums">
                      {cat.pct_of_total}%
                    </span>
                  </div>
                </div>

                {/* 6px Slim Progress Bar */}
                <div className="h-1.5 w-full bg-[#E7E5E4] dark:bg-[#232329] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#4F46E5] dark:bg-[#818CF8] rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(cat.pct_of_total, 100)}%` }}
                  />
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
