# Baseline (no-skill) response: ec2-critical-auto-patch

This file captures what a generic assistant produces WITHOUT the
inspector2-automation-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, snapshot
gate, SSM patch baseline association, rescan verification, expert
Inspector knowledge).

---

You can use SSM to patch the instance when Inspector finds a
critical CVE. Run AWS-RunPatchBaseline against the instance ID.

```
aws ssm start-automation-execution --document-name AWS-RunPatchBaseline --parameters '{"InstanceId":["i-0abc123def456"],"Operation":["Install"]}'
```

After patching, Inspector should rescan and close the finding.
