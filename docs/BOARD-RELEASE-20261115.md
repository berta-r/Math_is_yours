# Current-main board release, 2026-11-15

## Active release verified

While this session was validating main `f6784df`, a teammate deployed the full
dataset and merged a launcher compatibility fix. The active release is:
`/home/arduino/math-tutor-releases/20261115-104103-4b2961b823`.

All **35 runtime source files match Git main `ad505c6`**, comparing Git's canonical
LF content. All **3,003 packaged files** match their manifest checksums. Its boot
service runs with `--local-tutor --safe-shutdown` and the persistent database
`/var/lib/math-student/progress.db`.

Health reports 2,962 problems (2,932 training plus 30 diagnostics), the 1,466-node
map, difficulty tables, generated skill mappings, thinking steps, hints/solutions
and explanations. The local SLM is ready. The missing ML artifacts are now on the
board, although they remain absent from this PC's Git-ignored data directory.

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

## Remaining coordination

USB is currently not visible on this PC. Read-only verification uses the existing
pinned SSH identity at `192.168.0.26`. Confirm the teammate has finished deploying
before replacing files or deleting old releases. A fresh-PC setup and final
shutdown/replug of this full-data release remain outstanding.

Obsolete tutor directories were archived to this PC with a matching checksum,
but have **not** been deleted during the concurrent deployment. The backup is
`results/retired-tutor-backup.tar.gz` (ignored). This session's smaller staging
directory `20261115-103029-6859bde2b0` was never activated; its activation helper is
now disabled to protect the newer full-data installation. Retain it until its
reasoning acceptance run finishes and results are saved.

The deployment branch adds missing `predict.py`, `eval.py`, `build_index.py` and
the empty `results/` placeholder to future bundles. The active full-data bundle
predates that fix; confirm the official entry point location before the jury run.
The compute server and the matching repository model are already installed.

## Interrupted final checks

The 30-row local validation set completed through `eval.py --limit 50 --name
current-release-acceptance`: 3/30 correct (10%). This small split has 24 problems
requiring figures and only 17 with all OCR options. It is different from the
organisers' practice benchmark and demonstrates the limitations of guessing on
visual problems. No solver improvement is claimed. Detailed output remains in
the first staged release's `results/` directory; connection loss prevented copying
the final ablation CSV to this PC.

The sample prediction check initially failed after model warm-up because the
archive lacked `results/`; the packaging fix now includes `results/.gitkeep` and
passes 14 local deployment tests (one skipped). Retrying the board contract check
was blocked when Wi-Fi stopped responding and USB remained absent. At that point
the concurrent deployment confirmation was still unanswered. Cleanup and final
USB boot testing remain pending; no old application directories were deleted.
