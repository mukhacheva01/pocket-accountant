from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.document_templates import DocumentTemplateService


router = APIRouter(prefix="/templates", tags=["templates"])


class MatchTemplateRequest(BaseModel):
    text: str


@router.post("/match")
async def match_template(req: MatchTemplateRequest):
    service = DocumentTemplateService()
    result = service.match_template(req.text)
    return {"matched": result is not None, "template": result}
