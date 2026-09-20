import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  ArrowUpTrayIcon,
  ArrowsRightLeftIcon,
  ArrowPathIcon,
  ChartPieIcon,
  FlagIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: HomeIcon },
  { name: 'Upload', path: '/upload', icon: ArrowUpTrayIcon },
  { name: 'Transactions', path: '/transactions', icon: ArrowsRightLeftIcon },
  { name: 'Subscriptions', path: '/subscriptions', icon: ArrowPathIcon },
  { name: 'Budgets', path: '/budgets', icon: ChartPieIcon },
  { name: 'Goals', path: '/goals', icon: FlagIcon },
  { name: 'Chat Assistant', path: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Monthly Report', path: '/report', icon: DocumentTextIcon },
  { name: 'AI Settings', path: '/settings', icon: Cog6ToothIcon },
]

interface SidebarProps {
  isCollapsed: boolean
  isMobileOpen: boolean
  onCloseMobile: () => void
}

export function Sidebar({ isCollapsed, isMobileOpen, onCloseMobile }: SidebarProps) {
  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs md:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Slim Sidebar Container */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-50 flex flex-col select-none transition-all duration-200 ease-in-out
          bg-[#FFFFFF] dark:bg-[#131318] border-r border-[#E7E5E4] dark:border-[#232329] text-[#1C1917] dark:text-[#EDEDEF]
          ${isMobileOpen ? 'translate-x-0 w-[220px]' : '-translate-x-full md:translate-x-0'}
          ${isCollapsed ? 'md:w-16' : 'md:w-[220px]'}
        `}
      >
        {/* Brand Header */}
        <div className="h-14 px-4 border-b border-[#E7E5E4] dark:border-[#232329] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-lg bg-[#4F46E5] flex items-center justify-center font-semibold text-white text-xs shrink-0 tracking-tight">
              FP
            </div>
            {(!isCollapsed || isMobileOpen) && (
              <div className="truncate">
                <span className="text-sm font-semibold tracking-tight text-[#1C1917] dark:text-[#EDEDEF]">
                  FinPilot
                </span>
              </div>
            )}
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={onCloseMobile}
            className="md:hidden p-1 rounded-md text-[#78716C] hover:text-[#1C1917] dark:text-[#8B8B95] dark:hover:text-[#EDEDEF]"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={onCloseMobile}
                title={isCollapsed ? item.name : undefined}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-[#4F46E5]/10 text-[#4F46E5] dark:bg-[#818CF8]/10 dark:text-[#818CF8] font-semibold border-l-2 border-[#4F46E5] dark:border-[#818CF8] rounded-l-none pl-2'
                      : 'text-[#78716C] dark:text-[#8B8B95] hover:text-[#1C1917] dark:hover:text-[#EDEDEF] hover:bg-[#FAFAF9] dark:hover:bg-[#1A1A22]'
                  } ${isCollapsed && !isMobileOpen ? 'justify-center px-2 pl-2' : ''}`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                {(!isCollapsed || isMobileOpen) && <span className="truncate">{item.name}</span>}
              </NavLink>
            )
          })}
        </nav>

        {/* Muted Disclaimer in Sidebar Footer */}
        {(!isCollapsed || isMobileOpen) && (
          <div className="p-3 border-t border-[#E7E5E4] dark:border-[#232329] text-[10px] text-[#78716C] dark:text-[#8B8B95] leading-relaxed">
            FinPilot is an analytics tool, not an authorized investment advisor under SEBI regulations.
          </div>
        )}
      </aside>
    </>
  )
}
