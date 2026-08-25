# Diagnostic Commands — Clean Rooms Collaboration Auditor

Load-on-demand pre-flight and diagnostic procedure moved verbatim from SKILL.md.

## Multi-collaboration sweep note (pagination)

**Multi-collaboration sweep note (pagination):** `aws cleanrooms
list-collaborations` returns at most 100 collaborations per page. Use
`--next-token` to drain every page; the long tail often contains stale
proof-of-concept collaborations that are the most likely to have INVITED
or REMOVED members. For each collaboration, also page
`aws cleanrooms list-members` and
`aws cleanrooms list-analysis-templates` — both cap at 100/page. Always
drain `nextToken` to completion.

## Live-account pre-flight checks (skip if doing offline config-doc audit)

**Live-account pre-flight checks (skip if doing offline config-doc audit):**
1. Verify the caller's IAM role grants `cleanrooms:GetMembership`,
   `cleanrooms:ListMembers`, `cleanrooms:GetCollaboration`,
   `cleanrooms:ListProtectedQueries`, and
   `cleanrooms:GetConfiguredTableAnalysisRule` — most read-only auditor
   roles can list members but cannot see other members' epsilon spend
   without `GetMembership`, and cannot inspect aggregate constraints
   without `GetConfiguredTableAnalysisRule`. If
   `cleanroomsml:GetConfiguredAudienceModel` is missing, the audience
   step will silently skip (note this as a coverage gap).
2. Verify CloudTrail is logging `cleanrooms:StartProtectedQuery` and
   `cleanrooms:GetProtectedQuery` — these are the audit-grade events for
   privacy-budget spend forensics. Without them, you cannot reconstruct
   which member spent which epsilon slice.
3. Snapshot `aws cleanrooms list-members --collaboration-id <id>` (paged)
   BEFORE any recommendation — member status is mutable, and an INVITED
   member may transition to ACTIVE during the audit window.
