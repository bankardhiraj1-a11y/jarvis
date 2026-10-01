---
name: Manual order intent
description: Manual strategy requests are per-order permissions, not authorization to replace or enable automatic strategies
---

Keep manual strategy execution distinct from automatic strategy selection and approval.

**Why:** The creator interrupted an automatic-strategy replacement to request a specific paper order, then requested manual entry across supported market segments. Those requests authorize explicit manual paper orders, not a silent replacement of the automatic strategy or enabling previously disabled automatic agents.

**How to apply:** Preserve the current automatic strategy while accepting user-defined manual entries through their own workflow. A manual signal/session exception must remain attached to that order; retain genuine quote checks, risk limits, the parent's market-specific holding policy, rollover/intraday safeguards and paper-only execution. Clearly distinguish submitted, pending, filled and closed states.

Do not apply the automatic Gold elapsed-time holding cap to manual Gold parents. Manual Indian-market bounded holds remain separate.

**Why:** Manual Gold's persisted contract is stop/target/rollover-managed with no elapsed-time exit. An automatic engine's blanket deadline can silently close both legacy and general manual positions despite that contract. The original manually requested entry and its history must also remain auditable.

**How to apply:** Apply this policy to both manual Gold parent types, including resumed trades. Automatic Gold retains its 25-minute limit; manual Gold uses its stop/target strategy without an elapsed-time exit and still requires fresh executable quotes at the earlier UTC-session or New York rollover safety cutoff. A correction of an earlier timed paper close must retain the prior close in an audit record, preserve genuine original entry fields, replay available real price observations, and label adjusted results as strategy-corrected paper—not uninterrupted forward evidence. Never backdate a new fill or silently erase a real recorded close.
