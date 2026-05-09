"""Webhook router — incoming webhooks from external services."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/ozon")
async def ozon_webhook(request: Request):
    """Handle incoming Ozon marketplace webhooks."""
    body = await request.json()
    # TODO: process Ozon webhook payload (order status changes, etc.)
    return {"status": "ok", "type": body.get("type", "unknown")}


@router.post("/payment")
async def payment_webhook(request: Request):
    """Handle external payment provider webhooks."""
    body = await request.json()
    return {"status": "ok", "event": body.get("event", "unknown")}
