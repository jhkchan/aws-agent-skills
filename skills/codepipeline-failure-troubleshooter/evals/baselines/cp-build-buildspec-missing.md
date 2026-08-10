# Baseline (no-skill) response: cp-build-buildspec-missing

This file captures what a generic assistant produces WITHOUT the
codepipeline-failure-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your build is failing because the buildspec.yml file is missing. The
CodeBuild logs say "buildspec.yml is empty or missing".

You probably moved or renamed the buildspec in your last commit.
Either move it back to the repo root, or update the CodeBuild project
to point at the new path. You can set `buildspec: ci/buildspec.yml`
in the CodeBuild project source configuration.

After that, retry the pipeline and it should work.
