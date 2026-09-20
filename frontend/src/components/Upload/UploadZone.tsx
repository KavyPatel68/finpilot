import React, { useState, useRef } from 'react'
import {
  ArrowUpTrayIcon,
  DocumentArrowUpIcon,
  LockClosedIcon,
  EyeIcon,
  EyeSlashIcon,
  CheckIcon,
} from '@heroicons/react/24/outline'

interface UploadZoneProps {
  onUpload: (file: File, accountId: number, password?: string) => Promise<void>
  isLoading: boolean
}

const STEPS = [
  'Uploading',
  'Detecting columns',
  'Deduplicating',
  'Categorizing',
]

export function UploadZone({ onUpload, isLoading }: UploadZoneProps) {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [pdfPassword, setPdfPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [accountId, setAccountId] = useState(1)
  const [activeStepIndex, setActiveStepIndex] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (['csv', 'xlsx', 'xls', 'pdf'].includes(ext || '')) {
      setSelectedFile(file)
      if (ext !== 'pdf') {
        setPdfPassword('')
      }
    } else {
      alert('Please select a supported file format (.csv, .xlsx, .xls, .pdf)')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) return

    setActiveStepIndex(0)
    const stepTimer = setInterval(() => {
      setActiveStepIndex((prev) => {
        if (prev < STEPS.length - 1) return prev + 1
        return prev
      })
    }, 550)

    try {
      await onUpload(selectedFile, accountId, pdfPassword ? pdfPassword : undefined)
      setActiveStepIndex(STEPS.length)
      setTimeout(() => {
        setSelectedFile(null)
        setPdfPassword('')
        setActiveStepIndex(0)
      }, 700)
    } finally {
      clearInterval(stepTimer)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const isPdf = selectedFile?.name.toLowerCase().endsWith('.pdf')

  return (
    <div className="rounded-xl border border-[#E7E5E4] dark:border-[#232329] p-5 bg-[#FFFFFF] dark:bg-[#131318] transition-colors">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Destination Account Selection */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#E7E5E4] dark:border-[#232329]">
          <div>
            <label className="text-xs font-medium text-[#1C1917] dark:text-[#EDEDEF] block">
              Destination Account
            </label>
            <p className="text-[11px] text-[#78716C] dark:text-[#8B8B95]">
              Select which financial ledger transactions map to
            </p>
          </div>

          <select
            value={accountId}
            onChange={(e) => setAccountId(Number(e.target.value))}
            className="text-xs font-medium rounded-lg border border-[#E7E5E4] dark:border-[#232329] px-2.5 py-1.5 bg-[#FAFAF9] dark:bg-[#1A1A22] text-[#1C1917] dark:text-[#EDEDEF] focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
          >
            <option value={1}>HDFC Savings (Primary Bank)</option>
            <option value={2}>HDFC Credit Card (Revolving)</option>
          </select>
        </div>

        {/* Large Minimal Dashed Dropzone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragActive
              ? 'border-[#4F46E5] bg-[#4F46E5]/5'
              : 'border-[#E7E5E4] hover:border-[#4F46E5]/60 dark:border-[#232329] dark:hover:border-[#818CF8]/60 bg-[#FAFAF9]/40 dark:bg-[#131318]/40'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.pdf"
            onChange={handleChange}
            className="hidden"
          />

          <div className="mx-auto w-10 h-10 rounded-lg bg-[#FAFAF9] dark:bg-[#1A1A22] border border-[#E7E5E4] dark:border-[#232329] flex items-center justify-center text-[#78716C] dark:text-[#8B8B95] mb-2.5">
            <DocumentArrowUpIcon className="w-5 h-5" />
          </div>

          {selectedFile ? (
            <div className="space-y-1">
              <p className="text-xs font-semibold text-[#1C1917] dark:text-[#EDEDEF]">
                {selectedFile.name}
              </p>
              <p className="text-[11px] text-[#78716C] dark:text-[#8B8B95] tabular-nums">
                {(selectedFile.size / 1024).toFixed(1)} KB • Click to choose a different file
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-xs text-[#1C1917] dark:text-[#EDEDEF] font-medium">
                Drag and drop your statement, or <span className="text-[#4F46E5] dark:text-[#818CF8]">browse</span>
              </p>
              <p className="text-[11px] text-[#78716C] dark:text-[#8B8B95]">
                Supports .CSV, .XLSX, and .PDF bank statements
              </p>
            </div>
          )}
        </div>

        {/* PDF Password Input if needed */}
        {isPdf && (
          <div className="p-3 rounded-lg border border-[#E7E5E4] dark:border-[#232329] bg-[#FAFAF9] dark:bg-[#1A1A22] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-[#1C1917] dark:text-[#EDEDEF]">
              <LockClosedIcon className="w-4 h-4 text-[#78716C] shrink-0" />
              <div>
                <span className="font-medium block text-xs">Protected PDF Password</span>
                <span className="text-[10px] text-[#78716C] dark:text-[#8B8B95]">
                  Decrypted in-memory; never stored on disk
                </span>
              </div>
            </div>

            <div className="relative w-full sm:w-60">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter statement password..."
                value={pdfPassword}
                onChange={(e) => setPdfPassword(e.target.value)}
                className="w-full rounded-md border border-[#E7E5E4] dark:border-[#232329] bg-[#FFFFFF] dark:bg-[#131318] px-2.5 py-1 text-xs text-[#1C1917] dark:text-[#EDEDEF] focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[#78716C] hover:text-[#1C1917]"
              >
                {showPassword ? (
                  <EyeSlashIcon className="w-3.5 h-3.5" />
                ) : (
                  <EyeIcon className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>
        )}

        {/* Clean Progress Stepper */}
        {isLoading && (
          <div className="p-4 rounded-lg border border-[#E7E5E4] dark:border-[#232329] bg-[#FAFAF9] dark:bg-[#18181F] space-y-3">
            <div className="flex items-center justify-between">
              {STEPS.map((step, idx) => {
                const isCompleted = activeStepIndex > idx
                const isCurrent = activeStepIndex === idx
                return (
                  <div key={step} className="flex items-center gap-1.5 text-xs">
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-semibold ${
                        isCompleted
                          ? 'bg-[#16A34A] text-white'
                          : isCurrent
                          ? 'bg-[#4F46E5] text-white'
                          : 'bg-[#E7E5E4] dark:bg-[#232329] text-[#78716C]'
                      }`}
                    >
                      {isCompleted ? <CheckIcon className="w-2.5 h-2.5 stroke-2" /> : idx + 1}
                    </div>
                    <span
                      className={`hidden sm:inline ${
                        isCurrent
                          ? 'font-medium text-[#1C1917] dark:text-[#EDEDEF]'
                          : 'text-[#78716C] dark:text-[#8B8B95]'
                      }`}
                    >
                      {step}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={!selectedFile || isLoading}
            className="px-4 py-2 rounded-lg bg-[#4F46E5] text-white font-medium text-xs hover:bg-[#4338CA] disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-2xs flex items-center gap-1.5"
          >
            <ArrowUpTrayIcon className="w-3.5 h-3.5" />
            <span>{isLoading ? 'Ingesting...' : 'Upload & Process'}</span>
          </button>
        </div>
      </form>
    </div>
  )
}
