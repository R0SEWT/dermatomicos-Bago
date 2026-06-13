"""Deterministic domain core: aggregates, value objects, and invariants.

Everything persistable is a frozen dataclass and carries ``Provenance``. The
domain never reads the clock or generates ids directly; those are injected via
ports so the core stays pure and deterministic.
"""
