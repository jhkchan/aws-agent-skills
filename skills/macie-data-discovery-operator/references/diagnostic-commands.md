# Macie Data Discovery Operator — diagnostic commands (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Pre-flight: Macie enablement + delegated admin gate — live-account command listing

**Live-account pre-flight (skip if offline plan):**
1. `aws macie2 get-macie-session` — confirm Macie is enabled. Capture
   `status` (ENABLED / PAUSED), `serviceRole`, `findingPublishingFrequency`.
2. `aws macie2 get-administrator-account` — confirm delegated admin for
   org-level deployments.
3. `aws macie2 list-classification-jobs` — check for existing jobs on
   the target buckets.
4. `aws s3api list-buckets` — verify target buckets exist and are in
   scope.
5. `aws macie2 describe-organization-configuration` — confirm org-level
   config (auto-enable for new accounts).

