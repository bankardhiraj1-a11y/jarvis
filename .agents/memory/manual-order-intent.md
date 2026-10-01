---
name: Manual order intent
description: Manual strategy requests are per-order permissions, not authorization to replace or enable automatic strategies
---

Keep manual strategy execution distinct from automatic strategy selection and approval.

**Why:** The creator interrupted an automatic-strategy replacement to request a specific paper order, then requested manual entry across supported market segments. Those requests authorize explicit manual paper orders, not a silent replacement of the automatic strategy or enabling previously disabled automatic agents.

**How to apply:** Preserve the current automatic strategy while accepting user-defined manual entries through their own bounded workflow. A manual signal/session exception must remain attached to that order; retain genuine quote checks, risk limits, maximum holds, rollover/intraday safeguards and paper-only execution. Clearly distinguish submitted, pending, filled and closed states.