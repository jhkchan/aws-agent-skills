# Advanced Patterns — ssm-association-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Step 12 — Recent features

- **Association-level KMS key for output (2023-2024):** per-association
  key scoping, separate from bucket default SSE.
- **Target-locations for multi-account/multi-region (2023-2024):**
  fan-out across accounts and Regions via `--target-locations` with
  AWS Organizations integration.
- **Calendar-based schedules (2023-2024):** change-window integration
  respects change freeze windows.
- **Triggered associations via EventBridge (2023-2024):** trigger on
  events (e.g., EC2 state change) beyond cron/rate.
- **Compliance dashboard (2024-2025):** drift detection timeline and
  per-association compliance history.
- **Terraform provider (2024-2025):** `aws_ssm_association` supports
  `target_locations` for multi-account/multi-region fan-out.
