# Current-main board release, 2026-11-15

## Active release verified

The active release is:
`/home/arduino/math-tutor-releases/20261115-104103-4b2961b823`.

All **35 runtime source files match Git main `ad505c6`**, comparing Git's canonical
LF content. Latest main `efaa52f` adds documentation only; the application code is
unchanged. All **3,008 packaged files** match their manifest checksums. Its boot
service runs with `--local-tutor --safe-shutdown` and the persistent database
`/var/lib/math-student/progress.db`.

Health reports 2,962 problems (2,932 training plus 30 diagnostics), the 1,466-node
map, difficulty tables, generated skill mappings, thinking steps, hints/solutions
and explanations. The local SLM is ready. The missing ML artifacts are now on the
board, although they remain absent from this PC's Git-ignored data directory.
They are included in the complete release archive exported below. Changing Git
branches does not restore these generated, ignored artifacts.

Production SQLite integrity is `ok`. All original 16 attempts, 16 learning events,
seven skill records and eight older dialogue records remain present.

## Functional checks

- The tutor, embedding and compute GGUF hashes match current `config.env`.
  All three model services and compute warm-up are enabled at boot.
- Initial staged current-main app: 137 tests (133 passed, four skipped);
  deployment/setup/data-preservation suite: 35 passed on the UNO Q.
- Python arithmetic and guided follow-ups: 0.02–0.03 seconds over USB.
- Real SLM responses: subtraction 22.64 s, fractions 20.59 s, Catalan subtraction
  20.58 s; all `local_model_generated`. These are functional checks, not educator
  approval or evidence of improved learning.
- The test database retained original records through migration and a saved draft
  survived an observed board restart.
- Live production graph check: an independent arithmetic answer moved BKT from
  0.2 to 0.5765 and Elo from 0.25 to 0.2696. A subsequent assisted answer was
  recorded but left both values unchanged. The draft was saved on the Arduino.
- Final idle snapshot with app and all three models active: 2,595 MiB available
  memory, 120 MiB swap used; app service memory 69,017,600 bytes. This is not a
  measured peak under simultaneous inference. Compute warm-up exited successfully.

## Launcher compatibility

Final main `ad505c6` keeps **`kangaroo-student` as the internal health identity**.
The product remains Math Is Yours. The original EXE remains compatible and bundles
Python/Tk/ADB; a student's PC needs no separate Python or App Lab.

Installed setup-image SHA-256:
`017ecf807a63567e2cf27913f72cde33fb5006661fb02210dc410cbbf291736b`.
Its EXE version is `1.0.20261114205347`, SHA-256:
`b13fc2c63caa4ef07b427361c7655c92624d1a076d07e3bd85eb431e6551f1da`.

During the temporary identity change, this session built EXE `1.1.202611151040`.
**Do not distribute that build:** it expects the superseded `math-is-yours`
identity. Its Windows startup was disabled and this PC's original compatible
watcher/startup restored. Its setup-drive image was never activated.

## USB opening and student use

USB reconnection was observed after a board restart. The installed Windows
watcher detected the board, opened `http://127.0.0.1:7013`, and then reported
the model ready. The final health request through that USB forward reports
`storage: Arduino`, arithmetic and conceptual generation available, and the full
map/content counts above.

1. On a new **Windows x64** PC/account, connect the board and run `START.EXE`
   from the `MATHTUTOR` drive once. This installs the bundled per-user watcher.
2. Later connections open the tutor in the default browser automatically while
   that watcher is running; the watcher is registered to start at Windows login.
3. Use the same notebook name to resume saved work. Calculation checks use Python;
   conceptual replies use the local SLM and can take about 20–23 seconds on an
   idle board. Under contention, the bounded request can return labelled stored
   guidance instead. The assistant does not award independent mastery for help.
4. Use **Finish & safely disconnect → Power off Arduino** before unplugging.

No App Lab, external Python installation or cloud service is needed for student
use. First execution on a fresh Windows PC, a real Windows reboot/login, and an
explicit Wi-Fi-disabled test of this full-data release remain unverified. Prior
and current USB checks used local forwarding; Wi-Fi was not disabled by this task.
Educator review and evidence of learning outcomes also remain separate work.

## Cleanup and reasoning entry points

Only `20261115-104103-4b2961b823` remains in `math-tutor-releases`. Four older
releases, old experiment/setup staging and this session's smaller, never-activated
`20261115-103029-6859bde2b0` were removed after checking the active service,
healthy database, process/unit references and verified local backups. The unused
activation helper is disabled. Shared model/checkouts and the installed setup
drive were retained because live services use them.

Backups on this PC (ignored by Git): `results/retired-tutor-backup.tar.gz`,
`results/before-current-board-upgrade.db`, and `results/retired-preview.db`.
The retired-directory archive SHA-256 is
`b3070e6c4687964783439e64f01d0382cd9c4948481ee531998b5ee838834225`.

The active release now includes `predict.py`, `eval.py`, `build_index.py`,
`docs/COMPUTE_SOLVER.md` and `results/.gitkeep`, copied from main's canonical bytes
and added to the manifest (3,003 initial files plus these five). Future deployment
bundles include them too. The model weights are already installed and match
`config.env`; weights are not committed in Git. The team's shared checkout
`~/datathon_xusigrupoo` and organiser-path symlink remain in place.

## Reasoning acceptance

The sample prediction check initially exposed a missing `results/` directory in
deployment archives. After the packaging fix, the retry produced five valid A–E
rows, all `ok`, taking 20.77 / 7.44 / 8.27 / 11.43 / 17.76 seconds. Warm-up before
the timed problems took 319 seconds while another boot warm-up was active. Avoid
starting duplicate warm-up/evaluation jobs. Packaging checks: 14 tests, one skipped.

`eval.py --limit 50 --name current-release-acceptance` ran on the UNO Q against
the laptop's available 30-row English validation split: **3/30 correct (10%)**,
mean 6.2 seconds, worst 45.8 seconds, no rows over 60 seconds. It contains 24
figure-dependent problems and only 17 with all OCR options, and differs from the
organisers' practice benchmark. No improvement or reliable general reasoning is
claimed. This evaluation used the staged current-main code, not a new solver.

Results were copied before deleting staging: `results/current-board-contract.csv`,
`results/current-board-evaluation.csv`, `results/current-board-ablations.csv`,
`results/current-coach-probe.json`, and `results/current-live-graph.json`.

## Complete local distribution and colleague handover

`results/current-complete-offline-release.zip` contains the full app/data bundle,
the compatible `START.EXE`, and release notes. It does not include student notebooks
or model weights; the verified board already has its models. This archive contains
research-only M3Kang data: do not commit or publish it.

Inner bundle: `results/current-full-board-bundle.tar.gz`, 109,948,301 bytes,
3,008 manifested files, SHA-256:
`e792def90b2e15c443e948ed6ac738b4f680c04f1bd3af38dcf648cd0be06fb8`.

Colleagues should read [COACH-DESIGN.md](COACH-DESIGN.md) before changing the UI,
[SLM-COACH.md](SLM-COACH.md) for the calculation/dialogue/persistence contract,
and [STUDENT_DEPLOYMENT.md](../board/STUDENT_DEPLOYMENT.md) before deploying.
Use the prepared archive or obtain the matching ignored dataset and `data/ml`
directory; a Git checkout alone is not the complete offline installation.
