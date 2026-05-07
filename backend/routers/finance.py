from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep
from shared.db.enums import FinanceRecordType

router = APIRouter(prefix="/finance", tags=["finance"])


class FinanceRecordRequest(BaseModel):
    source_text: str
    record_type: str  # income | expense


class FinanceFromTextRequest(BaseModel):
    source_text: str


@router.post("/{user_id}/record")
async def add_record(
    user_id: str, req: FinanceRecordRequest, services=Depends(get_services_dep),
):
    record = await services.finance.add_from_text(user_id, req.source_text)
    return {
        "record_id": str(record.id),
        "amount": str(record.amount),
        "category": record.category,
        "record_type": record.record_type.value,
    }


@router.post("/{user_id}/add-from-text")
async def add_from_text(
    user_id: str, req: FinanceFromTextRequest, services=Depends(get_services_dep),
):
    record = await services.finance.add_from_text(user_id, req.source_text)
    return {
        "record_id": str(record.id),
        "amount": str(record.amount),
        "category": record.category,
        "record_type": record.record_type.value,
    }


@router.get("/{user_id}/report")
async def get_report(user_id: str, days: int = 30, services=Depends(get_services_dep)):
    balance = await services.finance.balance(user_id)
    return balance


@router.get("/{user_id}/full-report")
async def get_full_report(user_id: str, days: int = 30, services=Depends(get_services_dep)):
    report = await services.finance.report(
        user_id, date.today() - timedelta(days=days), date.today(),
    )
    return {
        "income": float(report["totals"]["income"]),
        "expense": float(report["totals"]["expense"]),
        "profit": float(report["profit"]),
        "top_expenses": report["top_expenses"],
    }


@router.get("/{user_id}/records")
async def get_records(
    user_id: str,
    record_type: str = "all",
    limit: int = 20,
    services=Depends(get_services_dep),
):
    if record_type == "income":
        records = await services.finance.list_records(user_id, record_type=FinanceRecordType.INCOME, limit=limit)
    elif record_type == "expense":
        records = await services.finance.list_records(user_id, record_type=FinanceRecordType.EXPENSE, limit=limit)
    else:
        records = await services.finance.list_records(user_id, limit=limit)

    return {
        "records": [
            {
                "id": str(r.id),
                "record_type": r.record_type.value,
                "amount": str(r.amount),
                "category": r.category,
                "operation_date": r.operation_date.isoformat(),
                "source_text": r.source_text,
            }
            for r in records
        ]
    }
