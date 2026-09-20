import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { getAvailableMonths } from '../api/summary'

interface MonthContextType {
  selectedMonth: string
  setSelectedMonth: (month: string) => void
  availableMonths: string[]
  isLoadingMonths: boolean
  refreshMonths: () => Promise<void>
}

const MonthContext = createContext<MonthContextType | undefined>(undefined)

export function MonthProvider({ children }: { children: React.ReactNode }) {
  const [availableMonths, setAvailableMonths] = useState<string[]>([])
  const [selectedMonth, setSelectedMonth] = useState<string>('')
  const [isLoadingMonths, setIsLoadingMonths] = useState(true)

  const refreshMonths = useCallback(async () => {
    try {
      setIsLoadingMonths(true)
      const months = await getAvailableMonths()
      setAvailableMonths(months)
      if (months.length > 0 && (!selectedMonth || !months.includes(selectedMonth))) {
        setSelectedMonth(months[0])
      }
    } catch (err) {
      console.error('Failed to load available months:', err)
    } finally {
      setIsLoadingMonths(false)
    }
  }, [selectedMonth])

  useEffect(() => {
    refreshMonths()
  }, [])

  return (
    <MonthContext.Provider
      value={{
        selectedMonth,
        setSelectedMonth,
        availableMonths,
        isLoadingMonths,
        refreshMonths,
      }}
    >
      {children}
    </MonthContext.Provider>
  )
}

export function useMonth() {
  const context = useContext(MonthContext)
  if (!context) {
    throw new Error('useMonth must be used within a MonthProvider')
  }
  return context
}
