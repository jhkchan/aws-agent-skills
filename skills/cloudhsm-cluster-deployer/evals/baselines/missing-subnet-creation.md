# Baseline (without skill): missing-subnet-creation

The model does NOT flag the configuration issue:

1. Does not identify missing HA requirement
2. Proceeds with single-AZ deployment
3. No validation of subnet count
4. Output would fail at runtime
5. No expert-level prerequisite checking
