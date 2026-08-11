# Baseline (no-skill) response: buildspec-runtime-version-deprecated

This file captures what a generic assistant produces WITHOUT the
codebuild-build-troubleshooter skill loaded.

---

Your CodeBuild build is failing with a YAML_FILE_ERROR during the
install phase. The error says "Unknown runtime version" which means
there's something wrong with your buildspec.yml file. Check the
indentation and formatting of the YAML file to make sure it's valid.

The buildspec looks correct syntactically, so the issue might be with
the specific runtime version you're using. Try updating to a newer
version of Python or check the CodeBuild documentation for supported
runtime versions.
