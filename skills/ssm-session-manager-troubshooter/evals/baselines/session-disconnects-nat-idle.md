# Baseline (no-skill) response: session-disconnects-nat-idle

This file captures what a generic assistant produces WITHOUT the
ssm-session-manager-troubleshooter skill loaded - the contrast
that proves the skill adds structure (4-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

Your sessions are dropping after about 6 minutes. This could be
a network issue or an idle timeout. The SSM IdleDisconnectTimeout
is set to 20 minutes so that's probably not it.

You should check your network connection between your client and
the instance. The NAT gateway might be timing out idle
connections.
