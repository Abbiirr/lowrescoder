# 2026-04-24 live runtime error-surfacing captures

- `bad_alias_first_turn_fixed.*`: invalid model alias now halts with a visible recovery/error surface instead of silent retries
- `dead_gateway_first_turn_fixed.*`: dead local gateway now halts with a visible connection-failure surface instead of a long silent working state
