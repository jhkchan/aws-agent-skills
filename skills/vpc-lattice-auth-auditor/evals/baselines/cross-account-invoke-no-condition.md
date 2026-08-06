# Baseline (no-skill) response: cross-account-invoke-no-condition

This file captures what a generic assistant produces WITHOUT the
vpc-lattice-auth-auditor skill loaded.

---

The auth policy allows vpc-lattice:Invoke for a role in account
222222222222. This is a cross-account grant. You should verify this is
intended and consider adding conditions to restrict it.

The service network is also shared with the same external account via RAM,
so they can see the services. The target groups are instance-based which
is fine.
