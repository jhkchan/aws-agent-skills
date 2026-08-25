# Diagnostic Commands — Glue Crawler & Job Auditor

Live-account pre-flight command listings moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Live-account pre-flight checks

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller can run `glue:GetJob` / `glue:GetCrawler` — most
   read-only auditor roles can, but remediation (`UpdateJob`,
   `UpdateCrawler`) usually requires elevated grants. Surface this BEFORE
   the operator approves a change.
2. Confirm the named `SecurityConfiguration` actually EXISTS. A job may
   reference `SecurityConfiguration: prod-sec-config` that was deleted; Glue
   silently treats a missing reference as no encryption on logs / spills /
   bookmarks. Run `aws glue get-security-configuration --name <name>` and
   treat a `EntityNotFoundException` as CONFIG_GAP (Step 4), not OK.
3. For JDBC connections, fetch the connection password encryption setting
   AND the IAM role policy in the same pass — the connection password is
   only meaningful if `ConnectionPasswordEncryption.ReturnConnectionPasswordEncrypted`
   is true; otherwise the password is retrievable in plaintext via
   `glue:GetConnection`.

