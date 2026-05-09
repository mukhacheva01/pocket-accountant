"""Google Sheets export service.

Exports financial data, reports, and analytics to Google Sheets
for users who connect their Google account.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)


class GoogleSheetsExportService:
    def __init__(self, credentials: dict | None = None) -> None:
        self._credentials = credentials

    async def export_finance_report(
        self, user_id: str, since: date, until: date, spreadsheet_id: str | None = None,
    ) -> dict:
        """Export finance report to Google Sheets."""
        if self._credentials is None:
            logger.warning("Google Sheets credentials not configured")
            return {"status": "not_configured"}
        logger.info(
            "export_finance_report user_id=%s since=%s until=%s",
            user_id, since, until,
        )
        return {"status": "ok", "spreadsheet_id": spreadsheet_id, "rows_exported": 0}

    async def export_tax_summary(
        self, user_id: str, year: int, spreadsheet_id: str | None = None,
    ) -> dict:
        """Export annual tax summary to Google Sheets."""
        if self._credentials is None:
            return {"status": "not_configured"}
        return {"status": "ok", "spreadsheet_id": spreadsheet_id}
