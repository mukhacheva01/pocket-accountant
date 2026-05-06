import asyncio
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from shared.db.enums import EventCategory
from shared.db.models import CalendarEvent
from shared.db.session import SessionFactory



def resolve_seed_file() -> Path:
    relative_path = Path("data") / "calendar_templates.demo.json"
    candidates: list[Path] = [Path("/app") / relative_path]

    for base in [Path.cwd(), *Path.cwd().parents]:
        candidates.append(base / relative_path)

    module_path = Path(__file__).resolve()
    for base in module_path.parents:
        candidates.append(base / relative_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path("/app") / relative_path


async def load_calendar_templates(seed_file: Path | None = None) -> int:
    seed_file = seed_file or resolve_seed_file()
    payload = json.loads(seed_file.read_text(encoding="utf-8"))
    created = 0

    async with SessionFactory() as session:
        for item in payload:
            result = await session.execute(select(CalendarEvent).where(CalendarEvent.slug == item["slug"]))
            event = result.scalar_one_or_none()
            data = {
                "slug": item["slug"],
                "title": item["title"],
                "description": item["description"],
                "category": EventCategory(item["category"]),
                "due_date": date.fromisoformat(item["due_date"]),
                "applies_to_entity_types": item["applies_to_entity_types"],
                "applies_to_tax_regimes": item["applies_to_tax_regimes"],
                "applies_if_has_employees": item["applies_if_has_employees"],
                "applies_if_marketplaces": item["applies_if_marketplaces"],
                "applies_to_regions": item["applies_to_regions"],
                "priority": item["priority"],
                "legal_basis": item["legal_basis"],
                "recurrence_rule": item["recurrence_rule"],
                "notification_offsets": item["notification_offsets"],
                "active": item["active"],
                "requires_manual_review": item["requires_manual_review"],
            }
            if event is None:
                session.add(CalendarEvent(**data))
                created += 1
            else:
                for key, value in data.items():
                    setattr(event, key, value)
        await session.commit()

    return created


def main() -> None:
    created = asyncio.run(load_calendar_templates())
    print(f"Seed completed. Inserted or refreshed templates: {created}")


if __name__ == "__main__":
    main()
