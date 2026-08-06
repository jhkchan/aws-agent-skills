# Baseline (no-skill) response: public-notaction-inverse-wildcard

This file captures what a generic assistant produces WITHOUT the
vpc-lattice-auth-auditor skill loaded.

---

The auth policy uses NotAction with Principal "*" which grants all actions
except the two listed read operations. This means the caller can do almost
everything including invoking services.

You should replace NotAction with an explicit Action list to avoid granting
 unintended permissions.
