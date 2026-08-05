# Baseline (no-skill) response: noncompliant-critical-patches-missing

This instance (`i-0noncompliantcriticalpatches`) is managed and active,
and the `AWS-ApplyPatchBaseline` association ran successfully yesterday.
However, the patch state shows `NON_COMPLIANT` with 14 CRITICAL patches
missing.

This means the scan ran but found missing patches that have not been
installed. You should run the patch baseline with `Operation=Install` to
apply the missing patches, then re-scan to confirm compliance.

Session Manager is in use and inventory is collected, so the only gap
here is the missing patches.
