import React, { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileBottomNav } from './MobileBottomNav'
import { CommandPalette } from '../common/CommandPalette'
import { resetDemoData, getDemoStatus } from '../../api/client'
import { ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

export function AppLayout() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('finpilot_sidebar_collapsed') === 'true'
    }
    return false
  })
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true) // default to true in UI for safety
  const [isResetting, setIsResetting] = useState<boolean>(false)
  const [resetMessage, setResetMessage] = useState<string | null>(null)

  // Query demo status from backend
  useEffect(() => {
    getDemoStatus()
      .then((res) => {
        setIsDemoMode(res.demo_mode)
      })
      .catch(() => {
        // Fallback: assume demo mode for public/production safety
        setIsDemoMode(true)
      })
  }, [])

  // Persist sidebar state
  useEffect(() => {
    localStorage.setItem('finpilot_sidebar_collapsed', String(isSidebarCollapsed))
  }, [isSidebarCollapsed])

  // Global keyboard shortcut: Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleResetDemo = async () => {
    if (!confirm('Reset demo data? All custom uploads will be replaced with the original 6-month seed data.')) {
      return
    }
    setIsResetting(true)
    setResetMessage(null)
    try {
      const res = await resetDemoData(1)
      setResetMessage(res.message || 'Demo data restored successfully.')
      setTimeout(() => {
        window.location.reload()
      }, 1200)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reset demo data'
      alert(msg)
      setIsResetting(false)
    }
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#FAFAF9] dark:bg-[#0B0B0F] text-[#1C1917] dark:text-[#EDEDEF] transition-colors selection:bg-[#4F46E5]/15">
      {/* Demo Mode Notice Banner */}
      {isDemoMode && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 text-amber-900 dark:text-amber-200 px-3 py-1.5 text-xs flex flex-wrap items-center justify-between gap-2 z-50">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="font-medium">
              Demo with sample data. Please do not upload real bank statements.
            </span>
            {resetMessage && (
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold ml-2 animate-pulse">
                ✓ {resetMessage}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleResetDemo}
              disabled={isResetting}
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 hover:bg-amber-500/30 text-amber-950 dark:text-amber-100 border border-amber-500/30 transition-colors disabled:opacity-50"
              title="Restores the deterministic 6-month sample dataset"
            >
              <ArrowPathIcon className={`w-3 h-3 ${isResetting ? 'animate-spin' : ''}`} />
              {isResetting ? 'Resetting...' : 'Reset demo data'}
            </button>
          </div>
        </div>
      )}

      {/* Global Minimal TopBar */}
      <TopBar
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onToggleSidebarCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
      />

      {/* Main Workspace with Sidebar & Viewport */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar
          isCollapsed={isSidebarCollapsed}
          isMobileOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />

        <main className="flex-1 overflow-y-auto pb-20 md:pb-6 focus:outline-none">
          <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile Sticky Bottom Nav */}
      <MobileBottomNav />

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </div>
  )
}
