"""
domain/states.py — Canonical state machine enumerations.

All application code MUST use these enums instead of bare strings for status fields.
This ensures compile-time type safety and consistent state machine semantics.

Reference: final-execution-plan.md §14.4 — State machine definitions.

V15 fix: Expanded from 4 partial enums (15 values, zero imports) to full coverage
of plan §14.4 (7 state machines, 39+ values). All pipeline code should import and
use these enums instead of bare string literals.
"""
from enum import Enum


# ─────────────────────────────────────────────
# 1. Recording State Machine (plan §14.4 recording)
# ─────────────────────────────────────────────
class RecordingStatus(str, Enum):
    """Status of an ingested audio recording."""
    UNPROCESSED = "unprocessed"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    # Extended states from plan §14.4
    DIARIZED = "diarized"
    SLICED = "sliced"
    CLEANED = "cleaned"
    TRANSCRIBED = "transcribed"
    SCORED = "scored"
    CURATED = "curated"
    ARCHIVED = "archived"


# ─────────────────────────────────────────────
# 2. Segment State Machine (plan §14.4 segment)
# ─────────────────────────────────────────────
class SegmentStatus(str, Enum):
    """Status of an audio segment through the processing pipeline."""
    DRAFT = "draft"
    IGNORED_DURATION_BOUNDS = "ignored_duration_bounds"
    SLICED = "sliced"
    CLEANED = "cleaned"
    TRANSCRIBED = "transcribed"
    SCORED = "scored"       # synonym for processed after scoring
    PROCESSED = "processed"
    NEEDS_REVIEW = "needs_review"
    KEEP = "keep"
    DROP = "drop"
    FIXED = "fixed"
    DUPLICATE = "duplicate"
    CLEAN_FAILED = "clean_failed"
    TRANSCRIBE_FAILED = "transcribe_failed"
    # curate pipeline
    CURATED = "curated"


# ─────────────────────────────────────────────
# 3. Job State Machine (plan §14.4 job)
# plan canonical: queued/running/succeeded/failed/canceled
# code compat aliases: pending/completed/cancelled
# ─────────────────────────────────────────────
class JobStatus(str, Enum):
    """Status of an asynchronous job in the job queue."""
    # Plan canonical values
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    # Code-compat aliases (legacy; prefer canonical above)
    PENDING = "pending"     # alias for QUEUED
    COMPLETED = "completed" # alias for SUCCEEDED
    CANCELLED = "cancelled" # alias for CANCELED (British spelling)


# ─────────────────────────────────────────────
# 4. Dataset State Machine (plan §14.4 dataset)
# ─────────────────────────────────────────────
class DatasetStatus(str, Enum):
    """Status of a voice clone training dataset."""
    DRAFT = "draft"
    ACTIVE = "active"        # code-compat alias (used in routes_datasets.py)
    FROZEN = "frozen"
    TRAINING = "training"
    EVALUATED = "evaluated"
    REJECTED = "rejected"
    RELEASE_CANDIDATE = "release_candidate"


# ─────────────────────────────────────────────
# 5. ModelRun State Machine (plan §14.4 model_run)
# ─────────────────────────────────────────────
class ModelRunStatus(str, Enum):
    """Status of a model training run."""
    PENDING = "pending"
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    TRAINING = "training"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ─────────────────────────────────────────────
# 6. Report State Machine (plan §14.4 report)
# ─────────────────────────────────────────────
class ReportStatus(str, Enum):
    """Status of an evaluation or audit report."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# ─────────────────────────────────────────────
# 7. ReleaseGate State Machine (plan §14.4 release_gate)
# ─────────────────────────────────────────────
class ReleaseGateStatus(str, Enum):
    """Status of a model release gate checkpoint."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"
