# Advanced Patterns (load on demand) — CloudWatch Application Signals Operator

Expert-knowledge deep dives, edge cases, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Step 12 — Recent features (2023-2026) (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **Application Signals General Availability (2023-2024):** Application
  Signals reached GA with support for Java, Python, Node.js, and .NET
  auto-instrumentation via CloudWatch Agent.

- **SLO burn rate alarms (2023-2024):** Built-in burn rate metric
  generation for SLOs, enabling direct CloudWatch alarm creation
  without manual Metric Math.

- **RUM-Application Signals correlation (2024-2025):** Enhanced
  correlation between CloudWatch RUM client-side traces and
  Application Signals server-side traces. End-to-end waterfall view
  from user click to database.

- **Multi-window multi-burn-rate (MWMBR) standardization (2024-2025):**
  AWS standardized the MWMBR algorithm with recommended window/threshold
  combinations, reducing false positives while catching both acute and
  chronic SLO breaches.

- **Operation-level SLOs (2024-2025):** SLOs can now be defined at the
  operation level (e.g., POST /charge) in addition to the service
  level, enabling tighter targets for critical operations.

- **Anomaly detection on Application Signals metrics (2025-2026):**
  CloudWatch Anomaly Detection now supports Application Signals SLI
  metrics, enabling automatic anomaly alerts without manual threshold
  tuning.

- **Cross-account Application Signals (2025-2026):** Multi-account
  observability via CloudWatch cross-account sharing, allowing
  Application Signals data from linked accounts to be viewed centrally.
