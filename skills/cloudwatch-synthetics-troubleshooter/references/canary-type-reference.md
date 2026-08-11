# Canary Type Reference — CloudWatch Synthetics

Supplementary reference for the CloudWatch Synthetics Troubleshooter
skill. Documents each of the five canary types with script structure,
default configuration, common failure modes, and diagnostic notes.

## Canary types overview

| Type | Runtime | Script structure | Default timeout | Purpose |
|---|---|---|---|---|
| GUI Selenium WebDriver | Node.js / Python | `synthetics` module + WebDriver | 60s | Browser-based UI flow simulation |
| HTTP ping | Node.js | `synthetics.executeHttpStep` | 20s | Single-endpoint HTTP check |
| API HTTP | Node.js | Multi-step HTTP with `executeHttpStep` | 30s | API endpoint chain (auth + call) |
| Broken-link checker | Node.js | Built-in crawler | 120s | Page link validation |
| Multi-step | Node.js / Python | `synthetics.executeStep` sequence | 120s | Multi-page browser flow (login + actions) |

## GUI Selenium WebDriver canary

**Script structure:** Uses the `synthetics` module which wraps Selenium
WebDriver. Each step is wrapped in `synthetics.executeStep(stepName, fn)`.

**Common failure modes:**
- `NoSuchElementException` — DOM selector changed after UI deployment.
- `TimeoutException` — element did not appear within `WebDriverWait`.
- `Navigation timeout` — page load exceeded `pageLoadTimeout`.
- `UnhandledPromiseRejection` — missing `.catch()` on async step.

**Diagnostic notes:**
- Check the last logged step to identify which action timed out.
- Screenshot artifacts show the page state at failure.
- HAR file shows network requests that failed or were slow.
- Correlate failure start time with target application deployments.

## HTTP ping canary

**Script structure:** Uses `synthetics.executeHttpStep(stepName, options)`
for a single endpoint check.

**Common failure modes:**
- 4xx/5xx response — target endpoint returning errors.
- DNS resolution failure — `ENOTFOUND` from the target hostname.
- Connection timeout — `ETIMEDOUT` reaching the target.
- SSL certificate error — cert expired or hostname mismatch.

**Diagnostic notes:**
- The simplest canary type — failures are usually target-side.
- Check the response body in the HAR for error details.
- VPC-based HTTP canaries may fail due to NAT/route table issues.

## API HTTP canary

**Script structure:** Multi-step HTTP with `executeHttpStep`. Typically
step 1 authenticates (OAuth, API key), step 2+ calls the API.

**Common failure modes:**
- Step 1 auth failure — credential expired or rotated.
- Step 2 API failure — 4xx/5xx from the target API.
- Token caching across runs — stale token in module scope.
- Rate limiting (429) — canary frequency exceeds API rate limit.

**Diagnostic notes:**
- Always check step 1 (auth) before step 2 (API call).
- The HAR file captures the full request/response for each step.
- OAuth token caching in Lambda module scope is a common bug.

## Broken-link checker canary

**Script structure:** Built-in crawler that checks every link on a
configured page. No custom script needed.

**Common failure modes:**
- Third-party link failure — social media, analytics pixel down.
- Timeout — too many links, or slow third-party responses.
- DNS failure — stale link to a decommissioned domain.

**Diagnostic notes:**
- Use `brokenLinkCheckSettings` to exclude third-party domains.
- The run report lists every checked link with status.
- A single third-party failure causes the entire canary to FAILED.
- Check the `Failed` link list for legitimate vs third-party failures.

## Multi-step canary

**Script structure:** Sequence of `synthetics.executeStep` calls,
typically starting with login and following a user flow.

**Common failure modes:**
- Login failure (step 1) — credentials expired, MFA challenge.
- Navigation failure (step 2+) — page URL changed, element removed.
- Session timeout — steps complete too slowly, session expires.
- Visual Monitoring mismatch on any step.

**Diagnostic notes:**
- Check which step failed from the run report.
- Per-step screenshots show the page state at each point.
- If login fails, all subsequent steps will fail — fix auth first.
- Multi-step canaries benefit most from canary recording (HAR + screenshots).

## Runtime version reference

Node.js runtime versions: `synthetics-nodejs-puppeteer-3.x`,
`synthetics-nodejs-4.0`, `synthetics-nodejs-5.0` (and later).

Python runtime versions: `synthetics-python-1.x`.

**Deprecation schedule:** check via
`aws synthetics describe-runtime-versions` — each version has a
`DeprecationDate`. Deprecated versions still run but receive no updates.
Plan upgrades before the deprecation date.

## Artifact structure

Canary artifacts are stored in S3 under:
`s3://<artifact-bucket>/canary/<canary-name>/<run-id>/`

Contents:
- `screenshots/` — per-step PNG screenshots (GUI and multi-step types).
- `har/` — HAR file with all network requests (if canary recording enabled).
- `logs/` — canary run logs.
- `script/` — the canary script source (for reference).
