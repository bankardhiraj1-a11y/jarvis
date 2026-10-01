---
name: Adaptive trading research
description: Evidence limits when comparing more strategy families or trading sessions on the same development history
---

Treat additional strategy and session searches on reused development data as one accumulating selection process, not independent confirmations.

**Why:** The project has repeatedly expanded its research to pursue higher accuracy and more daily calls. Reusing the same fit/inner-validation partitions can favor chance results even when the final holdout remains untouched.

**How to apply:** Record the combined search scope, freeze each experiment before replay, and distinguish “best among tested” from “validated.” Use genuinely new forward paper observations or a preserved final holdout for independent confirmation; never retune a held-out period.

Do not transfer a prior experiment's metrics or session-selection evidence to its replacement, or treat aggregate Gold trade totals as replacement-strategy results.

**Why:** Automatic Gold strategies change while prior and manual paper trades must remain intact. A shared symbol's totals and an older session study can otherwise appear to validate a new, unevaluated hypothesis.

**How to apply:** Label the strategy scope of old evidence and mixed trade totals explicitly. Keep new runtime rule checks separate from profitability evidence; require attributed new forward observations before making strategy-specific claims.

Keep market availability, named market-session conventions, and strategy entry windows separate.

**Why:** The inherited 16:00–23:00 UTC entry restriction was mistaken for spot gold’s market opening time. Europe/US session clocks also change with daylight saving and do not define OANDA instrument tradeability.

**How to apply:** State the named time zones and local-clock conventions in session comparisons, convert each historical date with daylight-saving rules, and require genuine provider tradeability independently of the strategy window.