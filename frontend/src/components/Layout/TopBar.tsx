import React from 'react'
import {
  MagnifyingGlassIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  ChevronRightIcon,
  ChevronLeftIcon,
} from '@heroicons/react/24/outline'
import { useLocation } from 'react-router-dom'
import { useTheme } from '../../context/ThemeContext'
import { useMonth } from '../../context/MonthContext'
import { AIUsageWidget } from './AIUsageWidget'

interface TopBarProps {
  onOpenCommandPalette: () => void
  onToggleSidebarCollapse: () => void
  isSidebarCollapsed: boolean
  onToggleMobileMenu: () => void
}

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/upload': 'Statement Upload',
  '/transactions': 'Transactions',
  '/subscriptions': 'Subscriptions & Bills',
  '/budgets': 'Budgets',
  '/goals': 'Savings Goals',
  '/chat': 'Chat Assistant',
  '/report': 'Monthly Report',
  '/settings': 'AI Engine Settings',
}

export function TopBar({
  onOpenCommandPalette,
  onToggleSidebarCollapse,
  isSidebarCollapsed,
  onToggleMobileMenu,
}: TopBarProps) {
  const { theme, toggleTheme } = useTheme()
  const { selectedMonth, setSelectedMonth, availableMonths, isLoadingMonths } = useMonth()
  const location = useLocation()

  const currentTitle = PAGE_TITLES[location.pathname] || 'FinPilot'

  const isMac =
    typeof window !== 'undefined' &&
    navigator.platform.toUpperCase().indexOf('MAC') >= 0

  return (
    <header className="h-14 border-b border-[#E7E5E4] dark:border-[#232329] px-4 flex items-center justify-between gap-3 shrink-0 z-30 bg-[#FFFFFF] dark:bg-[#131318] text-[#1C1917] dark:text-[#EDEDEF] transition-colors">
      {/* Left: Mobile hamburger & Desktop collapse toggle + Page Title */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={onToggleMobileMenu}
          className="md:hidden p-1.5 rounded-lg text-[#78716C] hover:text-[#1C1917] hover:bg-[#FAFAF9] dark:text-[#8B8B95] dark:hover:text-[#EDEDEF] dark:hover:bg-[#1A1A22]"
          title="Open Menu"
        >
          <Bars3Icon className="w-5 h-5" />
        </button>

        <button
          onClick={onToggleSidebarCollapse}
          className="hidden md:flex p-1.5 rounded-lg text-[#78716C] hover:text-[#1C1917] hover:bg-[#FAFAF9] dark:text-[#8B8B95] dark:hover:text-[#EDEDEF] dark:hover:bg-[#1A1A22] transition-colors"
          title={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isSidebarCollapsed ? (
            <ChevronRightIcon className="w-4 h-4" />
          ) : (
            <ChevronLeftIcon className="w-4 h-4" />
          )}
        </button>

        <span className="text-sm font-semibold tracking-tight text-[#1C1917] dark:text-[#EDEDEF]">
          {currentTitle}
        </span>

        {/* Global Month Selector as a small pill */}
        <div className="ml-2">
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            disabled={isLoadingMonths || availableMonths.length === 0}
            className="text-xs font-medium rounded-full border border-[#E7E5E4] dark:border-[#232329] px-2.5 py-1 transition-colors focus:ring-1 focus:ring-[#4F46E5] focus:outline-none bg-[#FAFAF9] dark:bg-[#1A1A22] text-[#1C1917] dark:text-[#EDEDEF]"
          >
            {availableMonths.length === 0 ? (
              <option value="">No data periods</option>
            ) : (
              availableMonths.map((m) => {
                const dateObj = new Date(`${m}-01T00:00:00`)
                const label = isNaN(dateObj.getTime())
                  ? m
                  : dateObj.toLocaleString('default', { month: 'short', year: 'numeric' })
                return (
                  <option key={m} value={m}>
                    {label}
                  </option>
                )
              })
            )}
          </select>
        </div>
      </div>

      {/* Center: Command Palette Trigger Button */}
      <div className="flex-1 max-w-sm mx-2">
        <button
          type="button"
          onClick={onOpenCommandPalette}
          className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border border-[#E7E5E4] dark:border-[#232329] text-xs text-[#78716C] dark:text-[#8B8B95] bg-[#FAFAF9] hover:bg-[#F5F5F4] dark:bg-[#18181F] dark:hover:bg-[#1E1E26] transition-colors"
        >
          <div className="flex items-center gap-2 truncate">
            <MagnifyingGlassIcon className="w-3.5 h-3.5 text-[#78716C] dark:text-[#8B8B95] shrink-0" />
            <span className="truncate">Search...</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1 py-0.5 text-[10px] font-medium text-[#78716C] dark:text-[#8B8B95] bg-[#FFFFFF] dark:bg-[#131318] rounded border border-[#E7E5E4] dark:border-[#232329]">
            <span>{isMac ? '⌘' : 'Ctrl'}</span>
            <span>K</span>
          </kbd>
        </button>
      </div>

      {/* Right: AI Usage Widget & Theme Switcher */}
      <div className="flex items-center gap-2">
        <AIUsageWidget />

        <button
          type="button"
          onClick={toggleTheme}
          className="p-1.5 rounded-lg border border-[#E7E5E4] dark:border-[#232329] text-[#78716C] hover:text-[#1C1917] dark:text-[#8B8B95] dark:hover:text-[#EDEDEF] bg-[#FAFAF9] hover:bg-[#F5F5F4] dark:bg-[#18181F] dark:hover:bg-[#1E1E26] transition-colors"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <SunIcon className="w-4 h-4 text-[#EDEDEF]" />
          ) : (
            <MoonIcon className="w-4 h-4 text-[#1C1917]" />
          )}
        </button>
      </div>
    </header>
  )
}
