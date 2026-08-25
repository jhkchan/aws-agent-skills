# Migration Hub Strategy Deployer — worked examples (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Worked example — PREREQUISITES_MISSING, agentless-only with short window

```text
ASSESSMENT: portfolio-q3-partial
HOME_REGION: us-east-1
DISCOVERY_METHOD:
  - Agent-based: no (agents not deployed)
  - Agentless: yes, Collector VM on vcenter.example.com
  - Collection window: 2 days
COLLECTOR_PLAN:
  - Prerequisites: vCenter 443 reachable, AWS 443 reachable
  - Deployment: OVA deployed, registered
ASSESSMENT_SCHEDULE:
  - Start: after-collection
  - Duration: 2 days collection + 1 day analysis
  - Report bucket: s3://migration-reports-111111111111/portfolio-q3/
STRATEGY_GROUPS:
  - Server: srv-001, strategy: rehost, confidence: low (fallback — no dependency data)
  - Server: srv-002, strategy: rehost, confidence: low (fallback — no utilization data)
ANTI_PATTERNS:
  - Server: srv-042, pattern: EOL OS (Windows Server 2012 R2), impact: replatform required
  - (other anti-patterns may be false-negative due to stale vCenter OS data)
TCO: insufficient data (right-sizing not possible without utilization percentiles)
RIGHT_SIZING: not available (fallback to match-current-spec)
WAVE_PLAN: not possible (no dependency graph)
MGN_HANDOFF: blocked
DMS_HANDOFF: blocked
VERDICT: PREREQUISITES_MISSING
GAP: Three blockers: (1) agent-based discovery not deployed — dependency mapping and application grouping are not possible, every server defaults to standalone rehost; (2) collection window is 2 days, below the 7-day minimum for right-sizing — TCO will be unreliable; (3) wave planning is blocked without dependency data. Install agents on critical hosts and extend the collection window to at least 7 days (14 preferred) before starting the assessment.
TEMPLATE: (partial — install agents, then re-run)
```

