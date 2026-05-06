"""Backend entrypoint: run Alembic migrations, then start uvicorn."""

import subprocess
import sys

import uvicorn

from shared.config import get_settings
from shared.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)

    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
    )


if __name__ == "__main__":
    main()
