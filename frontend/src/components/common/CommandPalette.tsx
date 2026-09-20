import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MagnifyingGlassIcon,
  HomeIcon,
  ArrowUpTrayIcon,
  ArrowsRightLeftIcon,
  ArrowPathIcon,
  ChartPieIcon,
  FlagIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  SunIcon,
  MoonIcon,
  BoltIcon,
  NoSymbolIcon,
  CpuChipIcon,
  TrashIcon,
  XMarkIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { useTheme } from '../../context/ThemeContext'
import { setAIMode, clearAICache } from '../../api/ai'

interface CommandItem {
  id: string
  title: string
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  category: 'Pages' | 'Actions' | 'AI Engine'
  action: () => void
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Navigation items
  const pageItems: CommandItem[] = [
    {
      id: 'page-dashboard',
      title: 'Dashboard',
      subtitle: 'Financial overview, metrics & trends',
      icon: HomeIcon,
      category: 'Pages',
      action: () => {
        navigate('/dashboard')
        onClose()
      },
    },
    {
      id: 'page-upload',
      title: 'Upload Statements',
      subtitle: 'Import CSV, XLSX or PDF bank statements',
      icon: ArrowUpTrayIcon,
      category: 'Pages',
      action: () => {
        navigate('/upload')
        onClose()
      },
    },
    {
      id: 'page-transactions',
      title: 'Transactions',
      subtitle: 'Search, filter, categorize and edit records',
      icon: ArrowsRightLeftIcon,
      category: 'Pages',
      action: () => {
        navigate('/transactions')
        onClose()
      },
    },
    {
      id: 'page-subscriptions',
      title: 'Subscriptions & Recurring',
      subtitle: 'Manage recurring bills, services & EMIs',
      icon: ArrowPathIcon,
      category: 'Pages',
      action: () => {
        navigate('/subscriptions')
        onClose()
      },
    },
    {
      id: 'page-budgets',
      title: 'Budgets',
      subtitle: 'Monthly category limits & real-time tracking',
      icon: ChartPieIcon,
      category: 'Pages',
      action: () => {
        navigate('/budgets')
        onClose()
      },
    },
    {
      id: 'page-goals',
      title: 'Financial Goals',
      subtitle: 'Savings targets & what-if scenario simulations',
      icon: FlagIcon,
      category: 'Pages',
      action: () => {
        navigate('/goals')
        onClose()
      },
    },
    {
      id: 'page-chat',
      title: 'AI Chat Assistant',
      subtitle: 'Ask questions, run deterministic queries & analysis',
      icon: ChatBubbleLeftRightIcon,
      category: 'Pages',
      action: () => {
        navigate('/chat')
        onClose()
      },
    },
    {
      id: 'page-report',
      title: 'Monthly Report',
      subtitle: 'Exportable breakdown & actionable checklists',
      icon: DocumentTextIcon,
      category: 'Pages',
      action: () => {
        navigate('/report')
        onClose()
      },
    },
    {
      id: 'page-settings',
      title: 'AI & Provider Settings',
      subtitle: 'Configure LLM providers, local models & keys',
      icon: Cog6ToothIcon,
      category: 'Pages',
      action: () => {
        navigate('/settings')
        onClose()
      },
    },
  ]

  // Action items
  const actionItems: CommandItem[] = [
    {
      id: 'action-theme',
      title: theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode',
      subtitle: `Currently using ${theme} theme`,
      icon: theme === 'dark' ? SunIcon : MoonIcon,
      category: 'Actions',
      action: () => {
        toggleTheme()
        onClose()
      },
    },
    {
      id: 'action-mode-cheap',
      title: 'Set AI Mode: Cheap',
      subtitle: 'Claude Haiku with merchant batching & data cache',
      icon: BoltIcon,
      category: 'AI Engine',
      action: async () => {
        await setAIMode('cheap')
        onClose()
      },
    },
    {
      id: 'action-mode-off',
      title: 'Set AI Mode: Off',
      subtitle: 'Zero tokens; 100% deterministic rules & templates',
      icon: NoSymbolIcon,
      category: 'AI Engine',
      action: async () => {
        await setAIMode('off')
        onClose()
      },
    },
    {
      id: 'action-mode-full',
      title: 'Set AI Mode: Full',
      subtitle: 'Smart models enabled for narrative synthesis',
      icon: CpuChipIcon,
      category: 'AI Engine',
      action: async () => {
        await setAIMode('full')
        onClose()
      },
    },
    {
      id: 'action-clear-cache',
      title: 'Purge AI Output Cache',
      subtitle: 'Invalidate cached Q&A queries and summaries',
      icon: TrashIcon,
      category: 'AI Engine',
      action: async () => {
        await clearAICache()
        onClose()
      },
    },
  ]

  const allItems = [...pageItems, ...actionItems]

  // Filter items by query
  const filteredItems = query.trim()
    ? allItems.filter(
        (item) =>
          item.title.toLowerCase().includes(query.toLowerCase()) ||
          (item.subtitle && item.subtitle.toLowerCase().includes(query.toLowerCase())) ||
          item.category.toLowerCase().includes(query.toLowerCase())
      )
    : allItems

  // If query is present and not an exact match, also provide a "Search transactions" fallback
  const itemsWithSearchFallback: CommandItem[] = [...filteredItems]
  if (query.trim() && !filteredItems.some((i) => i.id === 'action-search-tx')) {
    itemsWithSearchFallback.push({
      id: 'action-search-tx',
      title: `Search transactions for "${query.trim()}"`,
      subtitle: 'Jump to transaction ledger with search filter',
      icon: MagnifyingGlassIcon,
      category: 'Actions',
      action: () => {
        navigate(`/transactions?q=${encodeURIComponent(query.trim())}`)
        onClose()
      },
    })
  }

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % itemsWithSearchFallback.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + itemsWithSearchFallback.length) % itemsWithSearchFallback.length)
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (itemsWithSearchFallback[selectedIndex]) {
          itemsWithSearchFallback[selectedIndex].action()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, itemsWithSearchFallback, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[80vh] transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Bar Header */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <MagnifyingGlassIcon className="w-5 h-5 text-slate-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command, page, or search transactions..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            className="flex-1 bg-transparent border-none outline-none text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:ring-0"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-semibold text-slate-500 bg-slate-200/60 dark:bg-slate-800 dark:text-slate-400 rounded border border-slate-300 dark:border-slate-700">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          className="flex-1 overflow-y-auto p-2 space-y-1 divide-y divide-slate-100/5 dark:divide-slate-800/10"
        >
          {itemsWithSearchFallback.length === 0 ? (
            <div className="py-12 text-center text-slate-400 dark:text-slate-500 text-sm">
              No matching commands or pages found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            itemsWithSearchFallback.map((item, idx) => {
              const Icon = item.icon
              const isSelected = idx === selectedIndex
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-800 dark:text-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-1.5 rounded-lg ${
                        isSelected
                          ? 'bg-white/20 text-white'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-semibold text-sm leading-tight">{item.title}</div>
                      {item.subtitle && (
                        <div
                          className={`text-[11px] mt-0.5 ${
                            isSelected ? 'text-indigo-100' : 'text-slate-400'
                          }`}
                        >
                          {item.subtitle}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                        isSelected
                          ? 'bg-indigo-500/40 text-indigo-50'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                      }`}
                    >
                      {item.category}
                    </span>
                    {isSelected && (
                      <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] bg-indigo-700/60 text-indigo-100 rounded">
                        ↵
                      </kbd>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer Shortcut Tips */}
        <div className="px-4 py-2 bg-slate-50 dark:bg-slate-950/40 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-semibold text-slate-600 dark:text-slate-300">↑↓</kbd> Navigate
            </span>
            <span>
              <kbd className="font-semibold text-slate-600 dark:text-slate-300">↵</kbd> Select
            </span>
            <span>
              <kbd className="font-semibold text-slate-600 dark:text-slate-300">esc</kbd> Dismiss
            </span>
          </div>
          <span className="text-[10px] text-slate-400">FinPilot Command Hub</span>
        </div>
      </div>
    </div>
  )
}
