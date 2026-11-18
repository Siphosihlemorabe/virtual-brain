"""HTTP routes for the accounts module."""

from typing import Annotated

from fastapi import APIRouter, Depends

from vb.accounts.auth import current_learner
from vb.accounts.schemas import Learner

router = APIRouter(tags=["accounts"])


@router.get("/me")
def me(learner: Annotated[Learner, Depends(current_learner)]) -> Learner:
    """Who you are, as the app sees you."""
    return learner
