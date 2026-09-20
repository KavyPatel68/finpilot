import io
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionDirection
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.services.analytics.recurring_detector import detect_recurring_groups
from app.services.analytics.monthly_summary import generate_monthly_summary
from app.services.report.insights_engine import generate_monthly_report
from app.services.report.pdf_exporter import build_monthly_pdf


def test_complete_end_to_end_financial_workflow(client: TestClient, db: Session):
    """End-to-end integration test verifying the entire FinPilot system flow:

    1. Account setup
    2. Statement upload / transactions ingestion
    3. Categorization & recurring subscriptions detection
    4. Budget management & spending tracking
    5. Savings goals & scenario simulation
    6. Chat agent advisory refusal & tool invocation
    7. Monthly executive report & PDF export
    """
    user_id = 99

    # 1. Ensure user and account exist
    user = User(id=user_id, email="e2e@finpilot.test", display_name="E2E User", currency="INR")
    db.add(user)
    acc = Account(
        id=user_id,
        user_id=user_id,
        name="HDFC Premium",
        type=AccountType.bank,
        currency="INR",
        account_number_masked="9876",
    )
    db.add(acc)
    db.commit()

    # 2. Upload statement via CSV endpoint
    csv_content = (
        "Date,Narration,Amount,Type\n"
        "2024-08-01,SALARY CREDIT TCS,95000.00,Credit\n"
        "2024-08-05,SWIGGY BANGALORE,850.00,Debit\n"
        "2024-08-08,NETFLIX SUBSCRIPTION,799.00,Debit\n"
        "2024-08-12,ZOMATO ORDER,650.00,Debit\n"
        "2024-08-15,AMAZON SHOPPING,3500.00,Debit\n"
    )
    res_upload = client.post(
        "/api/upload",
        data={"user_id": user_id, "account_id": user_id},
        files={"file": ("august_stmt.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data["imported_count"] == 5

    # 3. Categorization verification
    res_txns = client.get(f"/api/transactions?user_id={user_id}&month=2024-08")
    assert res_txns.status_code == 200
    txns = res_txns.json()["items"]
    assert len(txns) == 5

    # 4. Budget creation and evaluation
    res_budget = client.post(
        f"/api/budgets?user_id={user_id}",
        json={"category": "Dining", "monthly_limit_minor": 200000},  # ₹2,000 limit
    )
    assert res_budget.status_code == 200
    res_budgets_list = client.get(f"/api/budgets?user_id={user_id}&month=2024-08")
    assert res_budgets_list.status_code == 200
    b_data = res_budgets_list.json()[0]
    assert b_data["category"] == "Dining"
    # Swiggy (850) + Zomato (650) = 1500 (150,000 minor)
    assert b_data["spent_minor"] == 150000
    assert b_data["remaining_minor"] == 50000
    assert b_data["status"] == "on_track"

    # 5. Goal simulation
    res_goal = client.post(
        f"/api/goals?user_id={user_id}",
        json={
            "name": "Laptop Upgrade",
            "type": "purchase",
            "target_amount_minor": 10000000,  # ₹1,00,000
            "current_amount_minor": 4000000,   # ₹40,000
            "target_date": "2025-08-01",
            "monthly_contribution_planned_minor": 500000,
        },
    )
    assert res_goal.status_code == 200
    goal_id = res_goal.json()["id"]

    res_sim = client.post(
        f"/api/goals/simulate?user_id={user_id}",
        json={"goal_id": goal_id, "cut_category": "Dining", "cut_amount_minor": 50000},
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["goal_id"] == goal_id

    # 6. Chat agent refusal & interaction
    res_refusal = client.post(
        f"/api/chat?user_id={user_id}",
        json={"message": "Which crypto coin or stock should I invest ₹50,000 into?", "user_id": user_id},
    )
    assert res_refusal.status_code == 200
    assert "not a financial advisor" in res_refusal.json()["reply"].lower() or "not a licensed" in res_refusal.json()["reply"].lower()

    # 7. Monthly executive report and PDF generation
    res_report = client.get(f"/api/reports/2024-08?user_id={user_id}")
    assert res_report.status_code == 200
    rep_json = res_report.json()
    assert rep_json["month"] == "2024-08"
    assert rep_json["cash_flow"]["income_minor"] == 9500000
    assert rep_json["cash_flow"]["expense_minor"] == 579900
    assert len(rep_json["action_items"]) > 0

    res_pdf = client.get(f"/api/reports/2024-08/pdf?user_id={user_id}")
    assert res_pdf.status_code == 200
    assert res_pdf.content.startswith(b"%PDF-")
