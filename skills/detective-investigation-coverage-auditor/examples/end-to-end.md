# End-to-end usage scenario: detective-investigation-coverage-auditor

A walkthrough showing the skill auditing an Amazon Detective behavior graph
that has two INVITED members (one expired), a STOPPED DETECTIVE_CORE on a
third member, but healthy GuardDuty integration and Organizations delegated
admin — demonstrating the INCOMPLETE_INGESTION verdict, the member-state
classification cascade, and the re-invitation + data-source re-enablement
remediation workflow.

## Input (user prompt)

> Audit Detective coverage for our us-east-1 region before our quarterly
> security review. We have 5 accounts in the org and need all of them
> covered for investigations.

```
Region: us-east-1
Account: 111111111111 (Organization admin, 5 total accounts)

Detective graph state:
  GraphArn: arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete
  CreatedTime: 2025-06-15T10:00:00Z

Member accounts (list-members):
  - AccountId: 111111111111, Status: ENABLED
  - AccountId: 222222222222, Status: ENABLED, DETECTIVE_CORE: COLLECTING
  - AccountId: 333333333333, Status: ENABLED, DETECTIVE_CORE: COLLECTING
  - AccountId: 444444444444, Status: INVITED, InvitedTime: 2026-07-15T10:00:00Z (21 days ago)
  - AccountId: 555555555555, Status: INVITED, InvitedTime: 2026-05-20T10:00:00Z (77 days ago — likely expired)

Data-source package states (batch-get-graph-member-datasources):
  222222222222: DETECTIVE_CORE: COLLECTING
  333333333333: DETECTIVE_CORE: COLLECTING

GuardDuty detector status:
  DetectorId: 12abc34d567e, Status: ENABLED

Organization configuration:
  DelegatedAdminAccountId: 111111111111
  AutoEnable: true
```

## Skill output

```text
GRAPH: arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete
VERDICT: INCOMPLETE_INGESTION
REASON: Graph exists but 2 of 4 non-admin member accounts are in INVITED
state with no data ingestion — 50% of org members have no investigation
coverage (Step 2b). One invitation has exceeded the 50-day acceptance window
and has likely expired.
FINDINGS:
  - [HIGH] Member 444444444444 in INVITED state, invitation sent 21 days ago (Step 2b)
  - [HIGH] Member 555555555555 in INVITED state, invitation sent 77 days ago — likely expired (Step 2b)
  - [OK] Graph ARN exists in us-east-1 (Step 1)
  - [OK] Members 222222222222 and 333333333333 DETECTIVE_CORE: COLLECTING (Step 2c)
  - [OK] GuardDuty detector ENABLED in region (Step 4a)
  - [OK] Organizations delegated admin configured with AutoEnable: true (Step 4b)
REMEDIATION:
  1. Re-send invitation to 444444444444:
     aws detective create-members --graph-arn arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete --accounts '[{"AccountId":"444444444444","EmailAddress":"security@444444444444.example.com"}]' --message "Accept Detective invitation for investigation coverage"
  2. Re-send invitation to 555555555555 (previous invitation expired after 50 days):
     aws detective create-members --graph-arn arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete --accounts '[{"AccountId":"555555555555","EmailAddress":"security@555555555555.example.com"}]' --message "Re-invite: previous invitation expired"
  3. After acceptance, verify DETECTIVE_CORE transitions to COLLECTING:
     aws detective batch-get-graph-member-datasources --graph-arn arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete --account-ids 444444444444 555555555555
  4. Verify all 5 org accounts are ENABLED with DETECTIVE_CORE COLLECTING:
     aws detective list-members --graph-arn arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete
```

## Key reasoning demonstrated

1. **Step 1 (NO_GRAPH gate):** Graph exists — pass. NO_GRAPH is not
   triggered.
2. **Step 2b (member state):** Two members are INVITED — 50% of the org
   has no coverage. The 77-day-old invitation has exceeded the 50-day
   acceptance window and is effectively dead. INCOMPLETE_INGESTION is
   triggered before STALE_DATA or CONFIG_GAP are evaluated.
3. **Step 2c (data-source state):** The two ENABLED non-admin members have
   DETECTIVE_CORE in COLLECTING — this sub-check passes, but the verdict
   is already INCOMPLETE_INGESTION from Step 2b.
4. **Steps 3-4 are not evaluated:** The cascade stops at the first failing
   step (Step 2b). GuardDuty ENABLED and org admin configured are noted as
   passing dimensions in the FINDINGS, but do not change the verdict.
5. **Remediation ordering:** Re-send invitations first (additive, reversible),
   then verify data-source states after acceptance. This follows the
   "prefer additive changes" principle — no data is lost, and the graph
   coverage expands without risk.
