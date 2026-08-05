# Baseline (no-skill) response: weak-source-no-approval

This file captures what a generic assistant produces WITHOUT the
codepipeline-pipeline-auditor skill loaded.

---

This pipeline uses GitHub as the source provider (ThirdParty owner).
It stores an OAuth token in Secrets Manager. The pipeline also has
polling enabled for source changes.

The pipeline deploys directly to production without a manual approval
step. This means any commit to the main branch will automatically
deploy.

The artifact store has KMS encryption. Consider adding an approval
stage and migrating to CodeStar Connections for better GitHub
integration.
