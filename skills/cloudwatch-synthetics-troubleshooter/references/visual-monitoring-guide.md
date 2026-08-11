# Visual Monitoring Guide — CloudWatch Synthetics

Supplementary reference for the CloudWatch Synthetics Troubleshooter
skill. Covers Visual Monitoring configuration, tolerance tuning, ignore
regions, and baseline management.

## How Visual Monitoring works

Visual Monitoring compares per-step screenshots against a stored
baseline. If the pixel-level delta exceeds the tolerance threshold, the
step is marked as `VisualMonitoringBaselineMismatch` and the canary
run is marked FAILED.

**Key distinction:** Visual Monitoring failure does NOT mean the canary
functionally failed. The canary's actions (clicks, navigation, form
submits) may have succeeded. Only the visual comparison flagged a delta.
This is a separate triage path from functional failures.

## Tolerance configuration

The `Tolerance` field in the canary's `VisualTesting` configuration is
a percentage (0-100) representing the maximum allowed pixel delta
between the screenshot and the baseline.

| Tolerance | Effect | Use case |
|---|---|---|
| 0-1% | Strict — catches minor CSS changes | Static pages, pixel-perfect requirements |
| 2-5% | Moderate — absorbs minor rendering differences | Most production UIs |
| 5-10% | Loose — absorbs dynamic content | Pages with banners, personalized content |
| > 10% | Very loose — masks significant changes | Not recommended for production |

**Recommendation:** start at 1-2% for production canaries. Increase
only after confirming that lower values produce false positives from
legitimate content variation.

## Ignore regions

Ignore regions are rectangular areas excluded from the Visual Monitoring
comparison. Use these for:

- Dynamic banners (promotional content, announcements).
- Cookie consent popups.
- Personalized content (user name, recommendations).
- Time/date displays.
- Third-party widgets (chat, analytics).

Ignore regions are configured in the canary's `VisualTesting` section
with coordinates relative to the screenshot dimensions.

## Baseline management

### When to update the baseline

- **After a confirmed UI deployment:** the baseline must be updated to
  reflect the new expected appearance. This is expected post-deploy
  maintenance, not a production incident.
- **After adding ignore regions:** the baseline should be re-captured
  to ensure the ignored regions are correctly positioned.
- **After changing the canary's viewport size:** screenshots are
  resolution-dependent; a viewport change invalidates the baseline.

### How to update the baseline

1. **Via console:** navigate to the canary, select a recent successful
   run, click "Update baseline" for each step.
2. **Via CLI:** trigger a fresh run, download the new screenshots, and
   use `update-canary` to point to the new baseline:
   ```bash
   aws synthetics start-canary --name <canary>
   # Wait for run to complete, then download new screenshots.
   aws s3 cp s3://<artifact-bucket>/canary/<canary-name>/<run-id>/screenshots/ \
     /tmp/new-baseline/ --recursive
   # Update the canary with the new baseline reference.
   aws synthetics update-canary --name <canary> \
     --canary-run-config '...'
   ```

### Common false-positive sources

| Source | Symptom | Fix |
|---|---|---|
| Anti-flicker loading state | Screenshot captures spinner/loading | Add `page.waitForLoadState('networkidle')` before screenshot |
| Cookie consent popup | Popup appears on first visit but not baseline | Add ignore region for popup area |
| Dynamic banner | Promotional content rotates | Add ignore region for banner |
| Timezone-dependent clock | Timestamp differs between runs | Add ignore region for clock area |
| Font rendering difference | Sub-pixel anti-aliasing varies | Increase tolerance by 1-2% |
| A/B test variant | Different variant served | Pin the variant via URL parameter or cookie |

### Diagnosing real vs false-positive mismatches

1. **Download both screenshots** (current run and baseline).
2. **Compare visually** — look for structural changes (layout shift,
   missing element, error page) vs cosmetic changes (color, font,
   dynamic content).
3. **Check deployment history** — correlate the mismatch start time
   with UI deployments.
4. **Check the delta percentage** — a delta > 15% usually indicates a
   structural change (real or post-deploy). A delta of 2-5% often
   indicates dynamic content.
5. **If no deployment occurred and the delta shows a broken layout** —
   this is a real production incident. Escalate to the application team.
