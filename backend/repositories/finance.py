from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.enums import FinanceRecordType
from shared.db.models import FinanceRecord


class FinanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_record(self, record: FinanceRecord) -> FinanceRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def summarize_period(self, user_id: str, date_from: date, date_to: date) -> Dict[str, Decimal]:
        result = await self.session.execute(
            select(FinanceRecord.record_type, func.coalesce(func.sum(FinanceRecord.amount), 0))
            .where(
                and_(
                    FinanceRecord.user_id == user_id,
                    FinanceRecord.operation_date >= date_from,
                    FinanceRecord.operation_date <= date_to,
                )
            )
            .group_by(FinanceRecord.record_type)
        )
        totals = {FinanceRecordType.INCOME.value: Decimal("0"), FinanceRecordType.EXPENSE.value: Decimal("0")}
        for record_type, total in result.all():
            totals[record_type.value] = total
        return totals

    async def top_expense_categories(self, user_id: str, limit: int = 5) -> List[tuple]:
        result = await self.session.execute(
            select(FinanceRecord.category, func.coalesce(func.sum(FinanceRecord.amount), 0).label("total"))
            .where(
                and_(
                    FinanceRecord.user_id == user_id,
                    FinanceRecord.record_type == FinanceRecordType.EXPENSE,
                )
            )
            .group_by(FinanceRecord.category)
            .order_by(func.sum(FinanceRecord.amount).desc())
            .limit(limit)
        )
        return list(result.all())

    async def list_records(
        self,
        user_id: str,
        *,
        record_type: Optional[FinanceRecordType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
    ) -> List[FinanceRecord]:
        filters = [FinanceRecord.user_id == user_id]
        if record_type is not None:
            filters.append(FinanceRecord.record_type == record_type)
        if date_from is not None:
            filters.append(FinanceRecord.operation_date >= date_from)
        if date_to is not None:
            filters.append(FinanceRecord.operation_date <= date_to)

        result = await self.session.execute(
            select(FinanceRecord)
            .where(*filters)
            .order_by(FinanceRecord.operation_date.desc(), FinanceRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
