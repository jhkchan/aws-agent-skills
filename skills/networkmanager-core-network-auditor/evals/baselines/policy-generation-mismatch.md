# Baseline (no-skill) response: policy-generation-mismatch

This file captures what a generic assistant produces WITHOUT the
networkmanager-core-network-auditor skill loaded.

---

The core network shows a policy generation mismatch — the LATEST
generation is 4 but the LIVE generation is 3. This means there are
policy changes that have been committed but not yet deployed to the
network. The running network is still using generation 3.

Everything else looks fine — the attachment is connected, the
resource policy is same-account scoped, and the segment policy
isolates prod correctly.

To deploy the pending changes, you need to execute the change set.
Run the execute-core-network-change-set command to bring the LIVE
policy in line with the LATEST.
