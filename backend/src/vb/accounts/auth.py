"""Who is asking. Endpoints depend on current_learner; only this file changes when real login (Cognito) arrives."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from vb.accounts.repository import get_or_create_learner_by_email
from vb.accounts.schemas import Learner
from vb.core.config import Settings, get_settings
from vb.core.db import get_session


def check_auth_config(settings: Settings) -> None:
    """Called at startup: a deployed app must never accept the dev login."""
    if settings.environment == "prod" and settings.auth_mode == "dev":
        raise RuntimeError("auth_mode=dev is not allowed when environment=prod; configure Cognito login")


def current_learner(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Learner:
    if settings.auth_mode == "dev":
        return get_or_create_learner_by_email(session, settings.dev_learner_email, display_name="Dev learner")
    raise HTTPException(status_code=501, detail="Login is not available yet (Cognito arrives in stage 3).")
