# Baseline (no-skill) response: docker-privileged-mode-not-set

This file captures what a generic assistant produces WITHOUT the
codebuild-build-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, root cause category,
evidence-backed diagnosis, phase-status-driven triage).

---

Your CodeBuild build is failing because Docker is not installed or not
running in the build container. You should try using a different base
image that has Docker pre-installed, or add a command to install Docker
in the PRE_BUILD phase before running docker build. Also check that the
Dockerfile is correct and the build context is set up properly.

If that doesn't work, try running the docker build command with sudo or
check if there are any permission issues with the Docker socket.
