# Eval: stale-finding-already-patched

**Difficulty:** medium
**Branch:** ROOT_CAUSE_FOUND — STALE_FINDING layer, remediation is rescan (not patch)

## Prompt

Inspector shows an OPEN PACKAGE_VULNERABILITY finding on EC2
instance i-789xyz for CVE-2024-7777 on the curl package. The
finding says vulnerable range < 8.4.0, fixed-in 8.4.0. But
lastObservedAt is 2026-08-05T10:00Z (5 days ago), and when I
query SSM inventory I see curl at version 8.4.0-1.amzn2023.1.
Is this still actionable? Account ID: 123456789012.
