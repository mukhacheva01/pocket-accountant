"""Ozon marketplace API router — sync triggers, dashboard, analytics."""

from fastapi import APIRouter, Depends

from backend.dependencies import get_session

router = APIRouter(prefix="/ozon", tags=["ozon"])


@router.post("/sync/{user_id}")
async def trigger_sync(user_id: str, session=Depends(get_session)):
    """Trigger a full Ozon data sync for a user."""
    from backend.repositories.ozon_data import OzonDataRepository
    from backend.services.ozon_sync import OzonSyncService

    repo = OzonDataRepository(session)
    service = OzonSyncService(repo)
    result = await service.full_sync(user_id)
    return {"status": "ok", "synced": result}


@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str, session=Depends(get_session)):
    """Get Ozon marketplace dashboard data."""
    from backend.repositories.ozon_data import OzonDataRepository
    from backend.repositories.ozon_insights import OzonInsightsRepository
    from backend.services.ozon_insights import OzonInsightsService

    data_repo = OzonDataRepository(session)
    insights_repo = OzonInsightsRepository(session)
    service = OzonInsightsService(data_repo, insights_repo)
    dashboard = await service.dashboard(user_id)
    return dashboard


@router.get("/feedback/{user_id}")
async def get_feedback(user_id: str, session=Depends(get_session)):
    """Get Ozon feedback/reviews summary."""
    from backend.repositories.ozon_insights import OzonInsightsRepository
    from backend.services.ozon_feedback import OzonFeedbackService

    repo = OzonInsightsRepository(session)
    service = OzonFeedbackService(repo)
    return await service.get_summary(user_id)
