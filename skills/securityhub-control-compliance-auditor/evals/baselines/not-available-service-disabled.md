# Baseline (no-skill) response: not-available-service-disabled

> This is the response a model produces **without** the skill definition.
> It treats NOT_AVAILABLE as "nothing to worry about" — missing the critical
> insight that AWS Config being disabled is a monitoring gap (WARNING), not
> a clean bill of health.

---

This Security Hub finding for Config.1 has a status of NOT_AVAILABLE. The
StatusReasons says AWS Config is not enabled in eu-west-2.

Since the compliance status is NOT_AVAILABLE, the control can't be evaluated.
You might want to check if you need AWS Config in that region. If you don't
use eu-west-2, this may not be important.
