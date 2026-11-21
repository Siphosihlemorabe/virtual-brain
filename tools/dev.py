"""Start everything for local development with one command:

    python tools/dev.py        (from the repo root; Ctrl+C stops everything)

1. PostgreSQL in Docker (compose.yaml)   2. database migrations   3. seed data
4. The API (reloads on code changes), the background worker and the web app, running together.
   Their output is combined in this window; each line is tagged [api], [worker] or [web].

Uses only Python's standard library, so it runs with any Python 3.11+.
"""

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# (tag, command, folder) for each long-running process
SERVICES = [
    ("api", ["uv", "run", "uvicorn", "vb.main:app", "--reload", "--port", "8000"], BACKEND),
    ("worker", ["uv", "run", "python", "-m", "vb.core.jobs.worker"], BACKEND),
    ("web", ["npm", "run", "dev", "-w", "@vb/web"], FRONTEND),
]


def executable(name: str) -> str:
    """The full path of a tool, or exit with a clear message if it isn't installed."""
    path = shutil.which(name)
    if path is None:
        sys.exit(f"'{name}' was not found. Install it, or check it is on your PATH.")
    return path


def run_step(title: str, command: list[str], folder: Path) -> None:
    """A setup step that must finish before the next one starts."""
    print(f"==> {title}", flush=True)
    result = subprocess.run([executable(command[0]), *command[1:]], cwd=folder)
    if result.returncode != 0:
        sys.exit(f"'{title}' failed (exit code {result.returncode}). See the output above.")


def forward_output(tag: str, process: subprocess.Popen[str]) -> None:
    """Print a process's output line by line, tagged with its name."""
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{tag:<6}] {line}", end="", flush=True)


def stop(process: subprocess.Popen[str]) -> None:
    """Stop a process and everything it started (uvicorn's reloader, npm's node child)."""
    if process.poll() is not None:
        return
    if os.name == "nt":  # Windows: kill the whole process tree
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    run_step("Starting PostgreSQL in Docker", ["docker", "compose", "up", "-d", "--wait", "db"], ROOT)
    run_step("Applying database migrations", ["uv", "run", "alembic", "upgrade", "head"], BACKEND)
    run_step("Loading seed data", ["uv", "run", "python", "-m", "vb.seed"], BACKEND)

    environment = {**os.environ, "PYTHONUNBUFFERED": "1"}  # show Python output immediately, not in chunks
    processes: list[subprocess.Popen[str]] = []
    for tag, command, folder in SERVICES:
        process = subprocess.Popen(
            [executable(command[0]), *command[1:]],
            cwd=folder,
            env=environment,
            stdin=subprocess.DEVNULL,  # services never read this window's keyboard input
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # errors go to the same tagged stream
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        threading.Thread(target=forward_output, args=(tag, process), daemon=True).start()
        processes.append(process)

    print("\n    API docs  http://localhost:8000/docs\n    Web app   http://localhost:5173\n    Ctrl+C to stop\n")
    try:
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        print("==> One of the services stopped (see its output above). Stopping the rest.")
    except KeyboardInterrupt:
        print("\n==> Stopping…")
    finally:
        for process in processes:
            stop(process)
        print("==> Stopped. The database keeps running in Docker; stop it with: docker compose stop")


if __name__ == "__main__":
    main()
