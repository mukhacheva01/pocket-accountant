from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep

from shared.contracts.payloads import FinanceRecordPayload

router = APIRouter(prefix="/finance", tags=["finance"])


class FinanceRecordRequest(BaseModel):
    source_text: str
    record_type: str  # income | expense


@router.post("/{user_id}/record")
async def add_record(
    user_id: str, req: FinanceRecordRequest, services = Depends(get_services_dep),
):
    from backend.services.finance_parser import FinanceTextParser
    from shared.db.enums import FinanceRecordType

    parser = FinanceTextParser()
    parsed = parser.parse(req.source_text)
    if parsed is None:
        return {"error": "parse_failed", "message": "Не удалось разобрать текст"}

    record_type = FinanceRecordType.INCOME if req.record_type == "income" else FinanceRecordType.EXPENSE
    payload = FinanceRecordPayload(
        record_type=record_type,
        amount=parsed.amount,
        category=parsed.category,
        subcategory=parsed.subcategory,
        operation_date=date.today(),
        source_text=req.source_text,
        parsed_payload={"category_label": parsed.category_label},
        confidence=parsed.confidence,
    )
    record = await services.finance.add_record(user_id, payload)
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
    from datetime import timedelta
    date_from = date.today() - timedelta(days=days)
    date_to = date.today()
    report = await services.finance.report(user_id, date_from, date_to)
    return {
        "income": str(report["totals"]["income"]),
        "expense": str(report["totals"]["expense"]),
        "profit": str(report["profit"]),
        "top_expenses": [
            {"category": cat, "amount": str(amt)}
            for cat, amt in (report["top_expenses"] or [])
        ],
    }


@router.get("/{user_id}/balance")
async def get_balance(user_id: str, services=Depends(get_services_dep)):
    balance = await services.finance.balance(user_id)
    return {
        "income": str(balance["income"]),
        "expense": str(balance["expense"]),
        "balance": str(balance["balance"]),
    }


class AddTextRequest(BaseModel):
    source_text: str


@router.post("/{user_id}/add-text")
async def add_from_text(user_id: str, req: AddTextRequest, services=Depends(get_services_dep)):
    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    async with SessionFactory() as session:
        svcs = build_services(session)
        try:
            record = await svcs.finance.add_from_text(user_id, req.source_text)
        except ValueError:
            return {"error": "parse_failed", "message": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0440\u0430\u0437\u043e\u0431\u0440\u0430\u0442\u044c \u0442\u0435\u043a\u0441\u0442"}
        await session.commit()
        return {
            "record_id": str(record.id),
            "amount": str(record.amount),
            "category": record.category,
            "record_type": record.record_type.value,
        }


@router.get("/{user_id}/records")
async def get_records(
    user_id: str,
    record_type: str = "all",
    limit: int = 20,
    services = Depends(get_services_dep),
):
    from shared.db.enums import FinanceRecordType

    if record_type == "income":
        records = await services.finance.recent(user_id, FinanceRecordType.INCOME, limit)
    elif record_type == "expense":
        records = await services.finance.recent(user_id, FinanceRecordType.EXPENSE, limit)
    else:
        income = await services.finance.recent(user_id, FinanceRecordType.INCOME, limit)
        expense = await services.finance.recent(user_id, FinanceRecordType.EXPENSE, limit)
        records = sorted(income + expense, key=lambda r: r.operation_date, reverse=True)[:limit]

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
