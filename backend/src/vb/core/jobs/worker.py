"""The background worker: every few seconds, runs any queued jobs. Stop it with Ctrl+C.

Run on its own:  uv run python -m vb.core.jobs.worker   (from backend/), or let tools/dev.py start it.
In AWS this loop is replaced by SQS triggering a Lambda that calls run_job (architecture §3).
"""

import logging
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from vb.core.db import session_maker
from vb.core.jobs.handlers import HANDLERS
from vb.core.jobs.runner import Handler, run_pending

POLL_SECONDS = 2.0
log = logging.getLogger("vb.worker")


def serve(
    make_session: Callable[[], Session],
    handlers: dict[str, Handler],
    *,
    max_cycles: int | None = None,  # None = run until stopped; tests pass a number
    sleep: Callable[[float], None] = time.sleep,  # tests pass a no-op so they don't wait
) -> None:
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        with make_session() as session:  # a fresh session each cycle, closed afterwards
            ran = run_pending(session, handlers)
        if ran:
            log.info("ran %d job(s)", ran)
        cycles += 1
        if max_cycles is None or cycles < max_cycles:
            sleep(POLL_SECONDS)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("worker started; job kinds: %s", ", ".join(sorted(HANDLERS)) or "none yet")
    try:
        serve(session_maker(), HANDLERS)
    except KeyboardInterrupt:
        log.info("worker stopped")


if __name__ == "__main__":
    main()
