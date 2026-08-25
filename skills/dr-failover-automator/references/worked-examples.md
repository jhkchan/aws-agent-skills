# Worked Examples (load on demand) — DR Failover Automator

Secondary worked example (MANUAL_STEP_REQUIRED) moved verbatim from SKILL.md. The primary worked example stays in SKILL.md.


---

## Worked example — MANUAL_STEP_REQUIRED (no verification) (moved from SKILL.md)

```text
STRATEGY: warm-standby
RTO_TARGET: 5
RPO_TARGET: 1
REGIONS: primary=us-east-1, secondary=us-west-2
FAILOVER:
  - [PASS] Route 53 health check configured
  - [FAIL] No primary verification step — failover proceeds on first health check failure
  - [PASS] RDS cross-region read replica promotion defined
  - [PASS] DNS update via Route 53 API
  - [FAIL] No post-failover verification — clients may hit broken secondary
ORCHESTRATION:
  - [PASS] Step Functions state machine
  - [FAIL] No kill-switch
  - [FAIL] No human approval gate — fully automatic on first health failure
VERIFICATION:
  - [FAIL] No game-day drill in the last 12 months
  - [WARN] Resilience Hub assessment: 65 (below 80 target)
  - [WARN] Health check threshold 1 (too sensitive — false positives)
VERDICT: MANUAL_STEP_REQUIRED
FINDINGS:
  - [CRITICAL] No primary verification: a transient health check failure
    triggers full failover with no split-brain protection.
  - [CRITICAL] No kill-switch: a misconfigured health check endpoint causes
    automatic failover to an untested secondary.
  - [HIGH] No drill in 12 months: warm standby may have drift (stale AMIs).
  - [HIGH] No post-failover verification: clients routed to broken secondary.
REMEDIATION:
  1. Add dr-verify-primary-down Lambda as the first state; abort if primary is healthy.
  2. Add kill-switch Parameter Store /dr/kill-switch checked first.
  3. Run a game-day drill; document RTO measured.
  4. Tune health check threshold from 1 to 3.
```