# Worked Examples — SSM Patch Compliance Automator

Secondary worked examples moved from SKILL.md. Load on demand.

## Worked example — REVIEW_REQUIRED (moved from SKILL.md)

```text
PATCH: win2022-prod-patch-rollout
FLEET: 45 Windows Server 2022 (prod, private VPC)
BASELINE: win2022-prod-baseline / WINDOWS / Critical:3d / pb-0xyz789ghi
PATCH_GROUP: Patch Group=win2022-prod / 45 instances
MAINTENANCE_WINDOW: TBD (blocked)
VERDICT: REVIEW_REQUIRED
GAP: Windows instances in private VPC without NAT/WSUS/VPC endpoints. Patches will fail to download. Resolution: (1) add NAT gateway; (2) deploy WSUS; (3) create VPC endpoints. No snapshot workflow, SNS, or dashboard configured.
TEMPLATE: (blocked until network egress resolved)
```
