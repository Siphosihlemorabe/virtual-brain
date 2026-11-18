"""Background jobs: queued work (transcription, agents) with a progress log that survives restarts (F15).

The same run_job() is called by a local loop in development and by SQS + Lambda in AWS.
"""
