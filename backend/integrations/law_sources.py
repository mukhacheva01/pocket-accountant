from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Protocol


@dataclass
class FetchedLawUpdate:
    source: str
    source_url: str
    title: str
    summary: str
    published_at: datetime
    effective_date: date = None
    tags: List[str] = field(default_factory=list)
    full_text: str = ""


class LawSourceFetcher(Protocol):
    async def fetch(self) -> List[FetchedLawUpdate]:
        ...


class EmptyLawFetcher:
    async def fetch(self) -> List[FetchedLawUpdate]:
        return []

