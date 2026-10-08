# Torpedo United v2: Conv-Cup '26 submission report

## Objective and final deliverable

Control one player in the official deterministic two-player soccer arena using only the prescribed state/action interface. The implementation is an offline deterministic receding-horizon planner. It is not an RL model or neural network, and no training claims are made. The supplied source and configuration are all that is required for inference.

The final upload is `dist/Torpedo_United_Submission.zip`. Its root contains `submission.json`, `README.md`, `requirements.txt`, and `team_bot/` with the executable loop, policy and `models/planner.json` configuration. The ZIP contains no simulator, organizer model, benchmark data, tests or development tools.

## Requirements coverage

| Rulebook / official kit requirement | Delivered implementation / evidence |
| --- | --- |
| Executable agent through prescribed interface | `submission.json` launches `python -m team_bot.bot --model team_bot/models/planner.json` |
| Source code | `team_bot/bot.py`, `team_bot/policy.py`, `team_bot/__init__.py` |
| Brief system/interface documentation | Submission `README.md` describes inputs, actions, lifecycle, algorithm and assumptions |
| Dependencies and execution instructions | Python 3.11+, empty third-party requirements; ZIP-root startup command |
| Only own-player control | Chooses a move and optional kick; no game-engine imports or mutation |
| No external APIs | Fully offline inference with standard-library imports only |
| Both sides and changing obstacles | Attack sign follows observation; cached graph rebuilt when field/obstacles change |
| Two-second / 8,192-byte response limits | Flushed compact JSON output; direct timing benchmark and official process validation |
| Clean archive and safety checks | Official packager and static checker; full report and checksum included |
| No organizer model/environment in upload | Seven-file agent archive; external kit used only in development |
| 2–4-person team registration | Requires the user's actual registered team; code preparation does not complete registration |

The document calls for an agent ZIP, source, brief documentation and execution instructions. A slide deck or research paper is not an additional listed deliverable.

## Planning method

### Geometry and movement

For every legal direction, the proposed player position is computed using normalized diagonal vectors and the observation's player speed. Field and circle/rectangle collision checks filter blocked moves. A cached visibility graph joins corners offset from obstacles by the player radius plus a clearance margin. Dijkstra costs guide the agent around obstructed direct paths. The graph is rebuilt from observed geometry; seed-specific layouts are not hard-coded.

### Ball forecasting

The ball-only predictor uses the published ball speed, radius and kick ranges. It divides each game iteration's travel into collision substeps, checks goal entry before wall rebounds, and handles obstacle reflection. The predictor was independently checked against the official engine across 24 seeded launch fixtures, including reflections, distance depletion and any goal entries encountered. Player interceptions and contact resolution are considered by separate heuristics; the predictor does not reproduce a complete two-player match.

### Attack

Every candidate move is paired with every legal kick direction at maximum power. The launch origin follows the proposed player move with the official clearance offset. Candidate goals are scored using opponent reachable-motion risk and travel time; an own-goal trajectory is discarded. Opponent reach now includes a full player move before the first ball substep of each frame, correcting the earlier near-launch underestimate. Immediate self-interception after a rebound is rejected. If no acceptable goal trajectory is found, the player carries toward one of three lanes with a penalty for nearby defenders.

At eight possession steps, or after the protected window when an opponent is close, the agent searches all legal powers for a forward/sideways escape kick. Its score compares obstacle-aware distances from both players to the predicted endpoint, rewards forward progress and penalizes interception risk along the complete pass. Predicted trajectory prefixes are reused across kick powers. This avoids relying on the forced low-power release at ten possession steps.

### Defense and interception

For a moving ball, every legal candidate move is first checked for an actual collision with the ball during the upcoming frame. If one can intercept, it takes priority. Otherwise the forecast is grouped into game iterations and the agent targets the first approximately reachable future ball position. If none is reachable, it heads toward the last forecast position. For an opponent-held ball, it presses from the side toward its own goal. For a stationary free ball, it follows an obstacle-aware route to possession.

### Determinism and runtime

Broad-phase collision rejection skips circle/rectangle distance calculations outside expanded obstacle bounds, while preserving exact collision substeps. There is no random exploration. Stable direction order resolves equal candidate scores. The observation is never altered. Geometry caching is based on field and obstacle content, not hidden evaluation seeds. The runner reads only the local JSON settings file, processes one line at a time and flushes each response. Exceptions produce a standard-error diagnostic and a safe stationary action. Process-level validation is necessary because that fallback alone does not prove the intended policy executed correctly.

## Validation environment

- Official repository: https://github.com/Anukul1712/Mlfootball_env
- Pinned revision: `3e66ba1f9bb12a9d75b8de02d92a4394e6c352d3`.
- Runtime used here: Python 3.12.14 on Linux; Windows execution instructions are provided, but Windows was not independently exercised.
- Unmodified official configuration: field 100 × 140, goal width 36, player radius 3/speed 4, ball radius 1.5/speed 8, six mirrored 11 × 8 obstacles, kick ranges 32/64/96, 400 iterations, seven-goal cap.
- Version 2 development seeds: 41001–41003; selection considered four official opponent styles. Final settings were frozen before the fresh-seed comparison.
- Held-out benchmark seeds: 62001–62008, both sides, four official opponent policies; 64 matches for each version. Full results: `reports/benchmark.json` and `reports/v1_comparison.json`.
- Additional condition seeds: 83001–83002; 36 matches under nine conditions, with altered settings clearly identified in `reports/conditions.json`.
- Fourteen state probes exercise late-match score situations, close contact, loose/moving balls and obstacle-edge possession on both sides.
- Process validation: eight matches, seeds 7000–7003, both sides, zero participant action errors. Seven wins and one loss against organizer RL; full stdout in `reports/process_validation.txt`.
- Five official kit tests and five agent regression tests passed.
- Official static checker: PASS, zero errors and warnings. Agent ZIP: seven files, no dependencies.

## Measured benchmark results

| Opponent | Previous wins / 16 | Improved wins / 16 | Improved draws | Improved losses | Improved goals for–against |
| --- | ---: | ---: | ---: | ---: | ---: |
| organizer-rl | 13 | 16 | 0 | 0 | 65–5 |
| simple | 11 | 16 | 0 | 0 | 80–0 |
| aggressive | 14 | 16 | 0 | 0 | 95–0 |
| counter | 9 | 14 | 1 | 1 | 92–5 |

Overall wins on identical fresh seeds: **47/64 (73.44%) → 62/64 (96.88%)**. The improved agent had one draw and one loss. Two-leg side-paired aggregate wins: **21/32 → 32/32**; those aggregates do not simulate the complete tournament or shootouts.

On 204 identical observations with alternating call order, average direct-call latency fell from **7.44 ms to 4.21 ms**, a **43.44% reduction (1.77× speedup)**. P95 fell from **42.01 ms to 21.07 ms**. The slowest improved call in the complete competition benchmark was **149.65 ms** under concurrent testing. The latency corpus and match benchmark contain different observation distributions; their statistics should not be mixed. Results are specific to this machine.

The 36 condition matches and 14 state probes completed with zero illegal actions and no observation mutation. Unannounced ball physics caused one observed loss; updating known fixed physics remains necessary if organizers change them. See `TEST_RESULTS.md` for the full condition table, failures and validation details.

## Limitations and interpretation

Local match outcomes are evidence about these opponents and seeds only. They cannot establish the winner of the hidden-seed double-elimination tournament. The benchmark runs normal 400-iteration matches, not the organizer's complete bracket, aggregate series or penalty shootout. The agent continues to supply actions if a runner provides more iterations; it has no separate shootout interface.

Opponent movement is simultaneous and unknown. Launch planning assumes our proposed move is not displaced by player contact; actual contact resolution can change it. Opponent interception estimates use a reachable-distance envelope rather than full adversarial search. Offensive movement uses three preferred lanes, so some obstacle layouts and shot timings can be difficult. The planner can lose and those losses are retained in the benchmark report.

The current observation exposes field/player physics but not ball radius/speed, kick distances or possession limit. Those fixed official values are encoded in the configuration/policy. If the final event changes them or the protocol, adapt and revalidate. The agent intentionally has no external API, online learning, filesystem mutation or bundled organizer weights.

## Upload procedure

1. Confirm the actual team of 2–4 people is registered and that its public name matches `submission.json`.
2. If the name changes, rebuild with `tools/build.py` and keep the new checksum.
3. Upload only `Torpedo_United_Submission.zip`; do not upload the development bundle or official kit.
4. Preserve the archive unchanged after validation. The recorded hash is in `dist/SHA256SUMS.txt`.
5. Follow the organizers' final deadline and portal instructions. No contest submission or registration was performed during code preparation.
