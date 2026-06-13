"""Lumi: a care copilot for caregivers of babies with atopic dermatitis.

The caregiver observes, Lumi understands, the doctor decides.

This package is the main product. It MUST NOT import the isolated acoustic
research package ``dermatomicos_bago`` (enforced by a test). Safety invariants
live in deterministic code; the language model only produces untrusted proposals.
"""
