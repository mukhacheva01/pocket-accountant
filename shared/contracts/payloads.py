from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from shared.db.enums import FinanceRecordType, ReminderType


class ReminderPayload(BaseModel):
    reminder_id: str
    user_id: str
    user_event_id: str
    reminder_type: ReminderType
    scheduled_at: datetime
    due_date: date
    title: str
    description: str
    category: str
    legal_basis: Optional[str] = None
    consequence_hint: Optional[str] = None
    action_required: str
    buttons: List[str] = Field(default_factory=list)


class LawUpdatePayload(BaseModel):
    law_update_id: str
    source: str
    title: str
    summary: str
    published_at: datetime
    effective_date: Optional[date] = None
    affected_profiles: List[str] = Field(default_factory=list)
    importance_score: int
    action_required: Optional[str] = None
    source_url: str
    needs_admin_review: bool = True


class FinanceRecordPayload(BaseModel):
    record_type: FinanceRecordType
    amount: Decimal
    currency: str = "RUB"
    category: str
    subcategory: Optional[str] = None
    operation_date: date
    source_text: str
    parsed_payload: dict = Field(default_factory=dict)
    confidence: float = 0.0

