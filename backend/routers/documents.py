from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_services_dep


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{user_id}/upcoming")
async def upcoming_documents(user_id: str, services=Depends(get_services_dep)):
    documents = await services.documents.upcoming_documents(user_id)
    return {"documents": documents}
