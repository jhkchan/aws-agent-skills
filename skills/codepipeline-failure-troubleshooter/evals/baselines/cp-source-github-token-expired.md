# Baseline (no-skill) response: cp-source-github-token-expired

This file captures what a generic assistant produces WITHOUT the
codepipeline-failure-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your pipeline is failing at the Source stage because it can't
authenticate to GitHub. The personal access token is probably
expired.

You'll need to generate a new PAT in GitHub with repo scope, update
the secret in AWS Secrets Manager, and then retry the pipeline. You
might also want to look into using a CodeStar connection instead so
the token rotates automatically.

After updating the token, try re-running the pipeline.
