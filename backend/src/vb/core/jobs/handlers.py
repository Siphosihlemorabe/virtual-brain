"""The job kinds the worker knows how to run: kind name -> handler function.

Empty for now. Slice 1 adds the first one ("process a transcript"). A handler takes (payload, log); see runner.py.
"""

from vb.core.jobs.runner import Handler

HANDLERS: dict[str, Handler] = {}
