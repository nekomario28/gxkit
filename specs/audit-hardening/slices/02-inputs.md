# Strict declarations and numeric boundaries

Retire A04–A09/A11. A common typed `gxcore.loading` helper rejects an invalid
member with its field/index; no list, mapping or module declaration may silently
drop it. Port crongx, seedgx, pipegx, envgx and apigx's converted-member lists.
Preserve valid model/tuple/mapping/module formats; validate the original seed
rather than int-truncating it. Conversion validation errors must not be hidden
by `resolve`'s unrelated-shape fallback.

Cron omitted fields retain Run defaults. Empty/invalid intervals cannot collide;
NaN/infinity and overflowed ends are errors before interval math. Empty env/net
declaration sets still validate references. API bases match path boundaries,
including root and trailing slash, not '/v1' as a prefix of '/v10'.

Checkpoint: CLI and model tests cover every audit case and accepted equivalent
representation; zero/boundary cases are explicit, not left to random sampling.
Keep unchanged good/broken examples, rendering ownership and severities intact;
register/document any new error code across consumers.
