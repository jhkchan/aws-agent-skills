# Baseline (no-skill) response: weak-shadow-bypass-rule

This file captures what a generic assistant produces WITHOUT the
wafv2-web-acl-auditor skill loaded. Note: the baseline identifies the
api-allow-rule but does NOT recognize it as a shadow/bypass vulnerability.
It treats the ACL as having good managed rules and an extra allow rule,
completely missing the priority-ordering bypass that makes the managed
rules ineffective for all /api/ traffic. This is the key delta the skill
provides.

---

This Web ACL has the Common Rule Set and Known Bad Inputs Rule Set in BLOCK
mode, which is good. There's also an `api-allow-rule` at priority 0 that
allows traffic matching `/api/` in the URI path.

The DefaultAction is set to Block, which means anything not explicitly
allowed will be blocked. The `api-allow-rule` seems to be there to let API
traffic through, which makes sense if your API endpoints should be
accessible.

The managed rule groups are at priorities 10 and 20, so they'll be
evaluated after the allow rule. Everything looks reasonable for a
production setup. You might want to add logging and a rate-based rule for
additional protection.
