from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.tax_engine import TaxCalculationRequest, TaxCalculatorService, TaxQueryParser

router = APIRouter(prefix="/tax", tags=["tax"])


class TaxCalcRequest(BaseModel):
    regime: str
    income: Decimal
    expenses: Decimal = Decimal("0")
    entity_type: str | None = None
    has_employees: bool = False


class TaxQueryRequest(BaseModel):
    query: str
    profile: dict = {}


@router.post("/calculate")
async def calculate_tax(req: TaxCalcRequest):
    from shared.db.enums import EntityType
    entity = EntityType(req.entity_type) if req.entity_type else None
    calc_req = TaxCalculationRequest(
        regime=req.regime,
        income=req.income,
        expenses=req.expenses,
        entity_type=entity,
        has_employees=req.has_employees,
    )
    result = TaxCalculatorService.calculate(calc_req)
    return {
        "regime": result.regime,
        "tax_amount": str(result.tax_amount),
        "contributions": str(result.contributions),
        "reduction": str(result.reduction),
        "payable": str(result.payable),
        "effective_rate": str(result.effective_rate),
        "details": result.details,
    }


@router.post("/parse-query")
async def parse_query(req: TaxQueryRequest):
    if TaxQueryParser.looks_like_calculation_request(req.query):
        parsed = TaxQueryParser.parse(req.query, req.profile)
        return {"is_calculation": True, "parsed": parsed.__dict__ if parsed else None}
    return {"is_calculation": False}
