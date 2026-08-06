# Baseline (no-skill) response: missing-guardrail-no-region-lock

This file captures what a generic assistant produces WITHOUT the
organizations-scp-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, OU-hierarchy reasoning).

---

The organization looks well-protected. LeaveOrganization is denied,
security service disruption actions are denied, and root access key
operations are blocked. FullAWSAccess is present so the deny-list
strategy is in place.

One thing missing is a region restriction. The Finance OU handles
regulated data but there is no SCP using aws:RequestedRegion to limit
which regions resources can be deployed to. You may want to add a
region-restriction SCP to prevent data from being deployed outside
approved regions.

The overall posture is decent but could be improved with the region
guardrail.
