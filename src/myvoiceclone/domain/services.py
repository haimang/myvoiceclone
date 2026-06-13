"""
domain/services.py — Thin compatibility shim.

The actual service implementations live in myvoiceclone.services (application service layer).
This module re-exports them for backward compatibility with any code that imported from here.

V5/V6 architectural note: Services live in myvoiceclone.services (NOT domain/) because:
  - domain/ must only contain pure domain logic (entities, states, policies)
  - domain/ cannot import storage, adapters, or pipelines (per test_architecture_boundaries rules)
  - myvoiceclone.services is the application service layer that orchestrates across all layers
"""
from myvoiceclone.services import (  # noqa: F401  # re-export for compat
    service_export_dataset,
    service_train_rvc,
    service_train_sovits,
    service_synth_xtts,
    service_generate_baseline_report,
    service_generate_train_report,
    service_evaluate_long_train_gate,
    service_ingest,
    service_preprocess_all,
)
