import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  ArrowsRightLeftIcon,
  ChatBubbleLeftRightIcon,
  ArrowUpTrayIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'

const mobileNavItems = [
  { name: 'Dashboard', path: '/dashboard', icon: HomeIcon },
  { name: 'Ledger', path: '/transactions', icon: ArrowsRightLeftIcon },
  { name: 'Chat', path: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Upload', path: '/upload', icon: ArrowUpTrayIcon },
  { name: 'Report', path: '/report', icon: DocumentTextIcon },
]

export function MobileBottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t transition-colors
      bg-white/95 backdrop-blur-md border-slate-200 text-slate-600
      dark:bg-slate-900/95 dark:border-slate-800 dark:text-slate-400">
      <div className="grid grid-cols-5 h-14">
        {mobileNavItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
                  isActive
                    ? 'text-indigo-600 dark:text-indigo-400 font-semibold'
                    : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              <span>{item.name}</span>
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
