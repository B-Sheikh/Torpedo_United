# Torpedo United — Conv-Cup '26

## Execution
Python 3.11 or newer. No installation, internet, credentials, or third-party packages are required. Run from the ZIP root:

```text
python -m team_bot.bot --model team_bot/models/planner.json
```

The competition runner should use `submission.json`. The process reads newline-delimited JSON messages from standard input and emits exactly one flushed JSON action per observation. `match_end` terminates it. Other message types are ignored. Diagnostics go only to standard error. Invalid observation processing returns `{"move":"STAY"}` with a diagnostic.

## System
This is a deterministic planning agent, not a trained neural network. `planner.json` stores explicit physics assumptions and tactical weights. It has no bundled organizer model and imports no game engine. Its decisions use only the supplied observation and legal action values.

The observation supplies player identity, attack direction, field dimensions, player radius/speed, both player positions, ball state, obstacle rectangles and the action space. Bottom-left coordinates are used; positive y means UP. The policy handles either attacking direction. It leaves the incoming observation unchanged.

1. Build and cache a visibility graph around expanded obstacle corners. Dijkstra route costs guide all legal candidate moves.
2. Forecast free-ball motion with fine collision substeps, wall/obstacle rebounds, goal detection and finite kick range. Seek the earliest approximately reachable interception point.
3. On possession, evaluate every legal movement paired with every kick direction at maximum power. Forecast the launch after the movement. Penalize opponent interception envelopes and immediate rebounds into the kicker; reject own-goal shots. Opponent reach uses a full movement step before each ball frame, including its first collision substep.
4. Choose a scoring trajectory when its tactical score exceeds the configured threshold. Otherwise carry toward one of three shooting lanes, penalizing close opponents.
5. Before the possession limit, or under close pressure, compare legal short and long escape kicks by endpoint race advantage, forward progress and interception risk along the entire pass. Reuse predicted trajectory prefixes across powers.
6. When the opponent possesses the ball, approach from the goal side to press and tackle.

Only the action is returned, for example `{"move":"UP_RIGHT","kick":{"direction":"UP","power":3}}`. Move and kick directions can differ. The opponent's simultaneous action is unknown; candidate launches assume our proposed position survives contact resolution. Interception forecasts are estimates, not guarantees.

Version 2 selects exact first-frame moving-ball interception candidates before planning a longer chase. Broad-phase collision rejection skips rectangle-distance calculations when the ball is outside an obstacle's expanded bounds. These changes reduce inference work without coarsening collision substeps.

## Physics assumptions
The published fixed configuration specifies ball radius 1.5, ball speed 8, kick distances [32, 64, 96], and a 10-iteration possession limit. These values are held in the configuration/policy because the current observation does not expose them. Field dimensions, goal width and player movement physics are read from observations. If organizers change the fixed physics or interface, update and revalidate the agent before submission.

## Safety and dependencies
`requirements.txt` has no dependencies. Inference uses only argparse, json, sys, pathlib, math and heapq. It reads the relative configuration once; it performs no network requests, subprocess execution, dynamic code evaluation, unsafe deserialization, file writes, environment lookups or working-directory overrides. Standard output is reserved for actions.

## Scope of validation
Development reports live in the separate source bundle. The official static checker and live process validator must pass on the final archive. Local match benchmarks do not predict hidden-seed tournament outcomes. The original ZIP should be kept unchanged after checking its recorded SHA-256.

Public team name: Torpedo United (provisional; can be renamed before repackaging). The rulebook requires 2–4 registered participants; registration details are outside this code archive.
