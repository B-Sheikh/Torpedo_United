# Torpedo United v2 — test results

## Competition configuration: fair version comparison

Both versions were evaluated on the same eight fresh seeds (62001–62008), both sides, against all four official opponents: **64 matches per version**. The official game configuration and organizer RL model were unchanged. These seeds were not used in tuning; v2's settings were frozen before this run.

| Opponent | Previous wins | Improved wins | Improved draws | Improved losses | Improved goals for–against |
| --- | ---: | ---: | ---: | ---: | ---: |
| organizer-rl | 13/16 | 16/16 | 0 | 0 | 65–5 |
| simple | 11/16 | 16/16 | 0 | 0 | 80–0 |
| aggressive | 14/16 | 16/16 | 0 | 0 | 95–0 |
| counter | 9/16 | 14/16 | 1 | 1 | 92–5 |

**Previous: 47/64 wins (73.44%). Improved: 62/64 wins (96.88%), one draw and one loss.** The improvement is 23.44 percentage points on this fixed benchmark. Improved two-leg aggregate results: 32/32 series wins. These paired-side aggregates are diagnostics; the organizer's full bracket and shootouts were not simulated.

Both sides were checked for legal actions: **zero illegal actions**. The improved benchmark's slowest direct call was 149.7 ms, below the 2,000 ms deadline. Benchmark processes ran concurrently, so use the separate identical-observation latency comparison for speed claims.

The retained failure was counter opponent, seed 62006, player 1, score 0–5. The retained draw was counter opponent, seed 62001, player 2, score 0–0. These results are included rather than filtered out.

## Identical-observation timing comparison

204 deterministic observations were evaluated by both versions, with alternating call order and no concurrent heavy benchmark. Mean latency: **7.44 ms → 4.21 ms** (43.44% lower; 1.77× speedup). P95: **42.01 ms → 21.07 ms**. This corpus isolates inference cost; it is not the same observation distribution as the full match benchmark.

## Different conditions

Four matches per condition: two additional seeds (83001–83002), both sides, against counter/aggressive policies. **36 complete matches**, separate from the 64-match benchmark. Only the row named Official uses unchanged competition settings. Other rows deliberately modify one aspect of the arena and are stress tests, not official ranking evidence.

| Condition | Wins | Draws | Losses | Illegal actions |
| --- | ---: | ---: | ---: | ---: |
| Official | 3 | 1 | 0 | 0 |
| Other player starts with possession | 2 | 2 | 0 | 0 |
| No obstacles | 4 | 0 | 0 | 0 |
| Eight smaller obstacles | 4 | 0 | 0 | 0 |
| Narrower goal (20 units) | 3 | 1 | 0 | 0 |
| Player speed 3 | 4 | 0 | 0 | 0 |
| Player speed 5 | 4 | 0 | 0 | 0 |
| 800 iterations / 15-goal cap | 3 | 1 | 0 | 0 |
| Unannounced ball speed/range change | 3 | 0 | 1 | 0 |

All 36 matches completed without exceptions or observation mutation. No drop-ball events occurred in this condition suite. The deliberate ball-physics mismatch produced one loss: the published fixed ball physics must remain accurate, or the local settings must be updated before submission.

## State probes and independent regressions

**14 state probes**, seven scenarios on both sides: leading late, trailing late, tied late, close player contact, loose ball near a restart, moving ball, and possession beside an obstacle. Every probe completed with zero illegal actions and no observation mutation. These probes exercise behavior; they do not guarantee a tactical win.

Five independent regression tests passed: collision forecast versus official physics; legal/deterministic/read-only decisions on both sides; JSON-lines lifecycle and malformed-input fallback; an actual first-frame interception; and avoiding the close-defender interception that motivated the timing fix.

Five official kit tests passed. **Eight official process matches** on seeds 7000–7003, both sides, had **zero participant action errors** under the two-second deadline. Those process matches produced seven wins and one loss against the organizer RL bot. They verify executable behavior and preserve the observed loss.

## Submission format

Official ZIP checker: **PASS**, zero errors and warnings. The archive has seven files, no third-party dependencies, a launchable relative-path descriptor, source, brief documentation and JSON configuration. It contains no official environment, organizer weights or development tooling.

The final archive hash is in `dist/SHA256SUMS.txt` and `reports/static_check.json`. Upload only `dist/Torpedo_United_Submission.zip`.

## Limits

The submitted system is a deterministic planning agent, not a trained neural network. Opponent simultaneous movement and player contact remain approximations. Fixed-ball physics are read from the agent configuration because the observation does not expose them. Local performance, including the 32 aggregate wins, does not establish hidden-seed tournament results. Windows instructions are included; tests ran on Linux with Python 3.12.14.
