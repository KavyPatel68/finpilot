from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class ReportCashFlow(BaseModel):
    income_minor: int
    income_display: str
    expense_minor: int
    expense_display: str
    net_savings_minor: int
    net_savings_display: str
    savings_rate_pct: float
    mom_change_pct: Optional[float] = None
    recurring_spend_minor: int
    recurring_spend_display: str


class ReportCategorySpend(BaseModel):
    category: str
    amount_minor: int
    amount_display: str
    pct_of_total: float
    transaction_count: int


class ReportMerchantSpend(BaseModel):
    merchant: str
    amount_minor: int
    amount_display: str
    transaction_count: int


class ReportBudgetStatus(BaseModel):
    category: str
    monthly_limit_minor: int
    monthly_limit_display: str
    spent_minor: int
    spent_display: str
    remaining_minor: int
    remaining_display: str
    spent_pct: float
    status: str  # on_track, warning, exceeded


class ReportGoalStatus(BaseModel):
    id: int
    name: str
    type: str
    target_amount_minor: int
    target_amount_display: str
    current_amount_minor: int
    current_amount_display: str
    progress_pct: float
    target_date: Optional[str] = None
    months_remaining: Optional[int] = None
    required_monthly_savings_minor: Optional[int] = None
    required_monthly_savings_display: Optional[str] = None
    on_track: Optional[bool] = None


class ReportRecurringItem(BaseModel):
    id: int
    merchant: str
    avg_amount_minor: int
    avg_amount_display: str
    frequency: str
    status: str
    type: str


class ReportAnomalyItem(BaseModel):
    id: int
    type: str
    severity: str
    text: str
    supporting_data: Optional[Dict[str, Any]] = None


class ReportActionItem(BaseModel):
    id: str
    category: str  # e.g. "budget", "subscription", "anomaly", "savings", "general"
    title: str
    description: str
    impact_type: str  # "high", "medium", "low"
    potential_savings_minor: Optional[int] = None
    potential_savings_display: Optional[str] = None


class MonthlyReportResponse(BaseModel):
    month: str
    month_name: str
    user_id: int
    currency: str
    cash_flow: ReportCashFlow
    narrative: str
    top_categories: List[ReportCategorySpend]
    top_merchants: List[ReportMerchantSpend]
    budgets: List[ReportBudgetStatus]
    goals: List[ReportGoalStatus]
    recurring: List[ReportRecurringItem]
    anomalies: List[ReportAnomalyItem]
    action_items: List[ReportActionItem]
    disclaimer: str
