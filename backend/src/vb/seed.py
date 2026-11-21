"""Seed data for local development, so every fresh start looks the same. Safe to run any number of times.

Run:  uv run python -m vb.seed   (from backend/), or let tools/dev.py run it.
For now only the dev learner; slice 1 adds a sample AWS lecture transcript (F24).
"""

from sqlalchemy.orm import Session

from vb.accounts.repository import get_or_create_learner_by_email
from vb.core.config import Settings, get_settings
from vb.core.db import session_maker, unit_of_work


def seed(session: Session, settings: Settings) -> list[str]:
    """Create whatever is missing; return a line per item, for the console."""
    learner = get_or_create_learner_by_email(session, settings.dev_learner_email, display_name="Dev learner")
    return [f"dev learner: {learner.email} ({learner.id})"]


def main() -> None:
    with unit_of_work(session_maker()) as session:
        for line in seed(session, get_settings()):
            print(f"seeded {line}")


if __name__ == "__main__":
    main()
