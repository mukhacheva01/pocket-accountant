from datetime import date
from typing import Optional

from shared.contracts.payloads import FinanceRecordPayload
from shared.db.enums import FinanceRecordType
from shared.db.models import FinanceRecord
from backend.repositories.finance import FinanceRepository
from backend.services.finance_parser import FinanceTextParser


class FinanceService:
    def __init__(self, repository: FinanceRepository, parser: FinanceTextParser) -> None:
        self.repository = repository
        self.parser = parser

    async def add_from_text(self, user_id: str, source_text: str, operation_date: Optional[date] = None):
        parsed = self.parser.parse(source_text)
        if parsed is None:
            raise ValueError("Unable to classify finance operation.")

        payload = FinanceRecordPayload(
            record_type=parsed.record_type,
            amount=parsed.amount,
            category=parsed.category,
            operation_date=operation_date or date.today(),
            source_text=source_text,
            parsed_payload={"confidence": parsed.confidence},
            confidence=parsed.confidence,
        )
        record = FinanceRecord(
            user_id=user_id,
            record_type=payload.record_type,
            amount=payload.amount,
            category=payload.category,
            operation_date=payload.operation_date,
            source_text=payload.source_text,
            parsed_payload=payload.model_dump(),
        )
        return await self.repository.add_record(record)

    async def report(self, user_id: str, date_from: date, date_to: date):
        totals = await self.repository.summarize_period(user_id, date_from, date_to)
        top_expenses = await self.repository.top_expense_categories(user_id)
        profit = totals["income"] - totals["expense"]
        return {"totals": totals, "profit": profit, "top_expenses": top_expenses}

    async def balance(self, user_id: str, date_from: Optional[date] = None, date_to: Optional[date] = None):
        date_from = date_from or date.today().replace(day=1)
        date_to = date_to or date.today()
        report = await self.report(user_id, date_from, date_to)
        return {
            "period_start": date_from,
            "period_end": date_to,
            "income": report["totals"]["income"],
            "expense": report["totals"]["expense"],
            "balance": report["profit"],
        }

    async def list_records(
        self,
        user_id: str,
        *,
        record_type: Optional[FinanceRecordType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
    ):
        return await self.repository.list_records(
            user_id,
            record_type=record_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
