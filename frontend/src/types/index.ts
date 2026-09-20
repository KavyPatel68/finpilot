export type Currency = 'INR' | 'USD' | 'EUR' | 'GBP'
export type Direction = 'income' | 'expense'
export type CategorySource = 'rule' | 'llm' | 'user'
export type FileType = 'csv' | 'xlsx' | 'pdf' | 'unknown'
export type DocumentStatus = 'pending' | 'processing' | 'needs_mapping' | 'done' | 'error'
export type Severity = 'info' | 'warning' | 'critical'
export type GoalType = 'emergency_fund' | 'purchase' | 'custom'
export type FrequencyType = 'weekly' | 'monthly' | 'quarterly' | 'yearly'
export type RecurringStatus = 'active' | 'possibly_cancelled' | 'cancelled'
export type RecurringType = 'subscription' | 'bill' | 'emi' | 'other'

export interface ColumnMapping {
  date_col?: string | null
  description_col?: string | null
  debit_col?: string | null
  credit_col?: string | null
  amount_col?: string | null
  balance_col?: string | null
  direction_col?: string | null
  confidence?: number
  needs_confirmation?: boolean
  warnings?: string[]
  headers?: string[]
  preview_rows?: Record<string, unknown>[]
}

export interface UploadResponse {
  document_id: number
  filename: string
  status: 'done' | 'needs_mapping' | 'error'
  row_count: number
  imported_count: number
  duplicate_count: number
  parse_errors: ParseError[]
  mapping_suggestion?: ColumnMapping | null
  headers?: string[]
  preview_rows?: Record<string, unknown>[]
}

export interface User {
  id: number
  email: string | null
  display_name: string
  currency: Currency
  created_at: string
}

export interface Account {
  id: number
  user_id: number
  name: string
  type: 'bank' | 'card' | 'cash' | 'other'
  currency: Currency
  account_number_masked: string | null
  institution: string | null
  created_at: string
}

export interface Transaction {
  id: number
  user_id: number
  account_id: number
  document_id: number | null
  date: string
  raw_description: string
  merchant_normalized: string | null
  amount_minor: number
  amount_display: string  // formatted string from backend
  direction: Direction
  category: string
  subcategory: string | null
  category_source: CategorySource
  confidence: number | null
  is_recurring: boolean
  recurring_group_id: number | null
  is_transfer: boolean
  is_anomaly: boolean
  notes: string | null
  balance_minor?: number | null
  payment_method?: string | null
  created_at: string
}

export interface TransactionListResponse {
  items: Transaction[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface Document {
  id: number
  user_id: number
  account_id: number | null
  filename: string
  file_type: FileType
  status: DocumentStatus
  parse_errors: ParseError[]
  row_count: number | null
  imported_count: number | null
  duplicate_count: number | null
  uploaded_at: string
  processed_at: string | null
}

export interface ParseError {
  row: number | null
  message: string
}

export interface RecurringGroup {
  id: number
  user_id: number
  merchant: string
  avg_amount_minor: number
  avg_amount_display: string
  frequency: FrequencyType
  next_expected_date: string | null
  last_seen: string
  status: RecurringStatus
  type: RecurringType
  monthly_cost_minor: number
  annual_cost_minor: number
}

export interface Budget {
  id: number
  user_id: number
  category: string
  monthly_limit_minor: number
  monthly_limit_display: string
  effective_from: string
  effective_to: string | null
  spent_minor?: number
  spent_display?: string
  remaining_minor?: number
  remaining_display?: string
  spent_pct?: number
  status?: 'on_track' | 'warning' | 'exceeded'
}

export interface Goal {
  id: number
  user_id: number
  name: string
  type: GoalType
  target_amount_minor: number
  target_amount_display?: string
  current_amount_minor: number
  current_amount_display?: string
  target_date: string | null
  monthly_contribution_planned_minor: number | null
  monthly_contribution_planned_display?: string
  is_active: boolean
  progress_pct: number
  months_remaining: number | null
  required_monthly_savings_minor?: number | null
  required_monthly_savings_display?: string
  on_track: boolean | null
}

export interface GoalSimulationResponse {
  goal_id: number
  goal_name: string
  cut_category: string
  cut_amount_minor: number
  cut_amount_display: string
  current_target_date: string | null
  simulated_target_date: string | null
  months_saved: number
  narrative: string
}

export interface Insight {
  id: number
  user_id: number
  month: string
  type: string
  severity: Severity
  text: string
  supporting_data: Record<string, unknown>
  created_at: string
}

export interface MonthlySummary {
  id: number
  month: string
  payload: SummaryPayload
  generated_text: string | null
}

export interface SummaryPayload {
  income_minor: number
  expense_minor: number
  net_savings_minor: number
  savings_rate_pct: number
  recurring_spend_minor?: number
  transfers_minor?: number
  transfers_display?: string
  is_partial_month?: boolean
  partial_days?: number | null
  top_categories: CategorySpend[]
  top_merchants: MerchantSpend[]
  mom_change_pct: number | null
  previous_expense_minor?: number
}

export interface CategorySpend {
  category: string
  amount_minor: number
  amount_display: string
  pct_of_total: number
}

export interface MerchantSpend {
  merchant: string
  amount_minor: number
  amount_display: string
  transaction_count: number
}

export interface CalculationMetadata {
  intent?: string | null
  confidence?: number | null
  is_zero_token?: boolean
  is_cached?: boolean
  offline_mode?: boolean
  tokens_used?: number
  model?: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'tool'
  content: string
  tool_calls: unknown[] | null
  tool_results: unknown[] | null
  calculation_metadata?: CalculationMetadata | null
  created_at: string
}


export interface ReportMonth {
  month: string
  month_name: string
  transaction_count: number
}

export interface ReportCashFlow {
  income_minor: number
  income_display: string
  expense_minor: number
  expense_display: string
  net_savings_minor: number
  net_savings_display: string
  savings_rate_pct: number
  mom_change_pct: number | null
  recurring_spend_minor: number
  recurring_spend_display: string
}

export interface ReportCategorySpend {
  category: string
  amount_minor: number
  amount_display: string
  pct_of_total: number
  transaction_count: number
}

export interface ReportMerchantSpend {
  merchant: string
  amount_minor: number
  amount_display: string
  transaction_count: number
}

export interface ReportBudgetStatus {
  category: string
  monthly_limit_minor: number
  monthly_limit_display: string
  spent_minor: number
  spent_display: string
  remaining_minor: number
  remaining_display: string
  spent_pct: number
  status: 'on_track' | 'warning' | 'exceeded'
}

export interface ReportGoalStatus {
  id: number
  name: string
  type: string
  target_amount_minor: number
  target_amount_display: string
  current_amount_minor: number
  current_amount_display: string
  progress_pct: number
  target_date: string | null
  months_remaining: number | null
  required_monthly_savings_minor: number | null
  required_monthly_savings_display: string | null
  on_track: boolean | null
}

export interface ReportRecurringItem {
  id: number
  merchant: string
  avg_amount_minor: number
  avg_amount_display: string
  frequency: string
  status: string
  type: string
}

export interface ReportAnomalyItem {
  id: number
  type: string
  severity: string
  text: string
  supporting_data?: Record<string, unknown> | null
}

export interface ReportActionItem {
  id: string
  category: string
  title: string
  description: string
  impact_type: 'high' | 'medium' | 'low'
  potential_savings_minor?: number | null
  potential_savings_display?: string | null
}

export interface MonthlyReportResponse {
  month: string
  month_name: string
  user_id: number
  currency: string
  cash_flow: ReportCashFlow
  narrative: string
  top_categories: ReportCategorySpend[]
  top_merchants: ReportMerchantSpend[]
  budgets: ReportBudgetStatus[]
  goals: ReportGoalStatus[]
  recurring: ReportRecurringItem[]
  anomalies: ReportAnomalyItem[]
  action_items: ReportActionItem[]
  disclaimer: string
}

export interface AIUsageStats {
  tokens_used_today: number
  input_tokens_today: number
  output_tokens_today: number
  cached_read_tokens_today: number
  tokens_saved_by_cache: number
  cache_hit_rate_pct: number
  estimated_cost_inr: number
  estimated_cost_usd: number
  is_estimated: boolean
  currency_symbol: string
  total_requests: number
  llm_mode: 'off' | 'cheap' | 'full' | string
  model_fast: string
  model_smart: string
  is_free?: boolean
  provider?: string
  provider_tier?: string
  circuit_breaker_open?: boolean
  circuit_breaker_cooldown?: number
}

export interface AIConfig {
  provider: 'none' | 'ollama' | 'gemini' | 'groq' | 'anthropic' | string
  provider_tier: 'Offline' | 'Local' | 'Free Tier' | 'Paid Cloud' | string
  model: string
  base_url: string
  is_key_set: boolean
  circuit_breaker_open: boolean
  circuit_breaker_cooldown: number
  is_free: boolean
}

export interface AIConfigUpdateRequest {
  provider: string
  model?: string
  base_url?: string
  api_key?: string
}

export interface AITestConnectionResponse {
  status: 'ok' | 'error'
  latency_ms: number
  provider: string
  message: string
  response?: string
}

export interface AIModeResponse {
  status: string
  llm_mode: 'off' | 'cheap' | 'full'
  description: string
}

export interface SpendingTrendItem {
  month: string
  month_name: string
  income_minor: number
  income_display: string
  expense_minor: number
  expense_display: string
  net_savings_minor: number
  net_savings_display: string
  savings_rate_pct: number
}

export interface PriceHikeItem {
  merchant: string
  previous_amount_minor: number
  previous_amount_display: string
  new_amount_minor: number
  new_amount_display: string
  difference_minor: number
  difference_display: string
  effective_date: string
}

export interface UpcomingObligationItem {
  id: number
  merchant: string
  type: string
  amount_minor: number
  amount_display: string
  due_date: string
  days_until_due: number
  frequency: string
}

export interface UpcomingObligationsResponse {
  reference_date: string
  window_days: number
  total_upcoming_minor: number
  total_upcoming_display: string
  count: number
  items: UpcomingObligationItem[]
}




