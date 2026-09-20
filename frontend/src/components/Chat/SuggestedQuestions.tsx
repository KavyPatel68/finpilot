import React from 'react'
import { SparklesIcon } from '@heroicons/react/24/outline'

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void
}

const QUESTIONS = [
  { icon: '🍽️', text: 'How much did I spend on dining in August 2024?' },
  { icon: '💳', text: 'What subscriptions and recurring bills do I have?' },
  { icon: '📈', text: 'Did Netflix increase in price?' },
  { icon: '🎯', text: 'Simulate cutting dining spend by ₹2,000' },
  { icon: '💰', text: 'What was my net cash flow and savings rate in August?' },
  { icon: '⚠️', text: 'Are there any duplicate transactions or anomalies?' },
]

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-medium text-content-muted">
        <SparklesIcon className="w-3.5 h-3.5 text-[#4F46E5] dark:text-[#818CF8]" />
        <span>Suggested Inquiries</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(q.text)}
            className="flex items-center gap-1.5 text-xs text-left px-3 py-1.5 rounded-lg border border-hairline transition-colors
              bg-surface hover:bg-canvas text-content-primary hover:border-[#4F46E5]/40"
          >
            <span>{q.icon}</span>
            <span>{q.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
