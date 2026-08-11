# Eval prompt: cross-account-org-policy

Design a cross-account backup setup using Organizations backup policy.
Emit the standard BACKUP block including the Organizations backup
policy JSON.

Design reference: cross-account-org-policy
Organizations OU: ou-prod-xxxxx (10 member accounts)
Region: us-east-1
DR region: us-west-2

Requirements:
- Deploy Organizations backup policy at the OU level
- Daily backup (cron 0 5 ? * * *) of all EBS volumes tagged backup-plan=daily
- Primary vault: Default (us-east-1)
- Cross-region copy to us-west-2 dr-vault (90-day retention)
- Policy inheritance: all 10 member accounts automatically
- Lifecycle: 30 days hot, then delete

Include the policy JSON structure with plans, rules, selections, and
copy actions.
