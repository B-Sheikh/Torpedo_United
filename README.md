# Torpedo United — complete Conv-Cup '26 project

The final competition upload is `dist/Torpedo_United_Submission.zip`. Upload that ZIP alone. This source bundle is for development and reproducibility; do not upload it as your agent.

## What is included

- `submission/`: complete executable agent, frozen configuration, descriptor, brief system documentation and empty dependency list.
- `tools/benchmark.py`: independent matches against the official frozen RL, simple, aggressive and counter opponents, on both sides.
- `tools/setup_kit.py`: fetch the pinned official kit without changing an existing checkout.
- `tools/build.py`: official environment tests, agent tests, live process matches, clean packaging, static checker and SHA-256.
- `tools/stress_test.py`: both-side matches under nine conditions and 14 tactical/game-state probes; separates altered physics from official ranking evidence.
- `tools/compare_latency.py`: version 1 versus version 2 on identical observation fixtures.
- `baselines/v1/`: frozen previous agent for reproducible comparison, excluded from the submission ZIP.
- `tests/`: read-only observation/determinism checks, legal actions, protocol behavior and ball-forecast comparison against official physics.
- `reports/`: measured development/held-out results and validation evidence.
- `dist/`: final agent ZIP and recorded checksum.
- `TECHNICAL_REPORT.md`: methods, actual results, requirements mapping and limitations.
- `TEST_RESULTS.md`: fair old/new comparison, condition outcomes, timings and retained failures.

## Requirements

Python 3.11+, Git for fetching the development kit. No pip packages. The submitted runtime is fully offline; only optional development-kit download uses networking. The code was tested using the Python version recorded in the report. The reference opponent weights and official engine are downloaded for local tests and are not included in the agent ZIP.

## Reproduce on Windows PowerShell, Linux or macOS

Extract the source bundle, open a terminal in this folder, then run:

```text
python tools/setup_kit.py
python tools/benchmark.py --kit vendor/official/participants --start-seed 62001 --seeds 8
python tools/benchmark.py --kit vendor/official/participants --submission baselines/v1 --start-seed 62001 --seeds 8 --output reports/v1_comparison.json
python tools/stress_test.py --kit vendor/official/participants
python tools/compare_latency.py --kit vendor/official/participants
python tools/build.py --kit vendor/official/participants --matches-per-side 4
```

For an already downloaded official kit, replace `vendor/official/participants` with its participant-folder path. Do not edit its game configuration for final evaluation.

To test directly through the official tools from the participant directory:

```text
python live_viewer.py --submission ABSOLUTE_PATH_TO_PROJECT/submission/submission.json --opponent organizer-rl --seed 101
python validate_submission.py --submission ABSOLUTE_PATH_TO_PROJECT/submission/submission.json --matches-per-side 2
python package_submission.py ABSOLUTE_PATH_TO_PROJECT/submission ABSOLUTE_PATH_TO_PROJECT/dist/Torpedo_United_Submission.zip
python check_submission.py ABSOLUTE_PATH_TO_PROJECT/dist/Torpedo_United_Submission.zip
```

Replace `ABSOLUTE_PATH_TO_PROJECT` with your extracted folder; quote paths containing spaces. The live viewer command runs locally. Its official replay viewer can inspect the JSONL logs produced by validation.

## Team and submission

The supplied public name is **Torpedo United**. If your registered team has another name, edit only `submission/submission.json` and the README, then run the build again; the checksum will change. The rulebook requires **2–4 registered participants** through Unstop. This project does not create a registration, invent teammates or upload to a contest portal. No identity details or credentials are needed for the bot.

Submit only the checked agent ZIP; preserve its checksum and avoid changing it after checking. If the organizers release a different official kit, interface or fixed configuration, re-run validation against that version. Local wins cannot guarantee a tournament win.

## Provenance

Official source: https://github.com/Anukul1712/Mlfootball_env

Validated revision: `3e66ba1f9bb12a9d75b8de02d92a4394e6c352d3`.

The small JSON-lines runner and empty package initializer were retained from the official starter submission. The planning policy, configuration, development utilities, regression tests and project documentation were created for this submission. The official kit remains external; no organizer RL weights are redistributed in this project.
