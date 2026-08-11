# Baseline (no-skill) — revoked-profile-impact

> This is the response a model produces **without** the skill
> definition. It mentions revocation but does not flag that
> already-published Lambda versions keep running (no auto-rollback),
> does not prescribe removal of the ARN from the CSC's
> AllowedPublishingProfiles, and does not prescribe a redeploy from
> a known-good signed artifact. Generated for with-skill-vs-baseline
> comparison.

---

If the profile was revoked, just create a new profile and use that
going forward.

```bash
aws signer put-signing-profile --profile-name lambda-signing-prod-v2
```

The old function should be fine.
