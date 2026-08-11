# Eval: dangerous-broad-suppression-rule

**Difficulty:** medium
**Branch:** PARTIALLY_CLASSIFIED — jobs and ASDD healthy, but a SUPPRESS filter on all High+Medium severity findings masks everything from Security Hub

## Prompt

Audit the Macie data classification posture for account
123456789012 in us-east-1. Macie is enabled. ASDD is enabled.
3 classification jobs scoping 20 buckets. Coverage looks good:
20 buckets deep-scanned daily. 2 custom identifiers (healthy
regex). However, there are 2 suppression rules — one has
action SUPPRESS with criteria matching ALL findings of severity
High and Medium. This means all High and Medium findings are
suppressed before reaching Security Hub. Security Hub shows zero
Macie findings despite jobs running daily.
