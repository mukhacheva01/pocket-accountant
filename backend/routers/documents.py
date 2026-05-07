from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep


router = APIRouter(prefix="/documents", tags=["documents"])


class MatchTemplateRequest(BaseModel):
    text: str


@router.get("/{user_id}/upcoming")
async def upcoming_documents(user_id: str, services=Depends(get_services_dep)):
    documents = await services.documents.upcoming_documents(user_id)
    return {"documents": documents}


@router.post("/match-template")
async def match_template(req: MatchTemplateRequest, services=Depends(get_services_dep)):
    template = services.templates.match_template(req.text)
    if template is None:
        return {"matched": False, "template": None}
    return {"matched": True, "template": template}
