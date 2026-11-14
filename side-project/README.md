# Tukey Side Challenge · Decision dashboard

Workspace for the Datathon FME 2026 side challenge: design a dashboard that helps the team make decisions about **Math on the Edge**, our offline math copilot on the Arduino UNO Q.

## Brief

Select relevant information, communicate the conclusions it supports, and make the resulting decisions explicit. The format is open (web app, Power BI, Shiny, Tableau, or another suitable tool). The implementation tool has not been selected yet.

The judges assess:

- **Usefulness to decision-making:** does the dashboard answer questions from the main challenge and support decisions?
- **Adequateness:** are the representations suitable for the data and comparisons?
- **Coherence:** do the indicators, charts, conclusions, and underlying data agree?

There will be three finalists and one prize winner. Source: the supplied `SideChallenge_TukeyFME2026.pptx.md` and the user's brief.

## Decisions to support

| Question | Evidence and representation | Decision supported |
| --- | --- | --- |
| Which measured configuration should we use? | Accuracy versus mean latency scatter plot, with sample size and over-limit counts | Select a configuration that balances accuracy and runtime constraints |
| Does RAG improve on the baseline? | Paired correct/wrong changes on matching `(id, language)` rows; accuracy and latency deltas | Keep RAG, adjust k, or return to baseline |
| Where should we focus the next experiment? | Accuracy bars by language, level, and presence of OCR options, each with counts | Prioritize a language, difficulty group, or OCR investigation |
| Are answers reliable within the time budget? | Latency distribution with a 60 s reference; timeout and error rates | Investigate slow prompts or failing calls |
| Is letter bias hiding weak reasoning? | Predicted and true A–E proportions, alongside the always-D baseline | Investigate calibration or prompting |

These are proposed analyses, not measured findings. No evaluation results are available yet. Topic analysis and RAM indicators require additional measurements before they can be displayed.

## Data and integrity

Use existing local outputs from [`eval.py`](../eval.py):

- `results/ablations.csv`: experiment summaries and provenance (name, commit, input, languages, n, RAG k, accuracy, mean/worst latency, over-limit count).
- `results/eval-*.csv`: per-problem correctness, latency, status, language, level, options availability, and answer letters.

Compare runs only on the same validation sample and conditions. Join paired results by `(id, language)` and report unmatched rows. Show denominators and distinguish missing results from zero. Include fallback answers in overall accuracy and report failures separately. An answer of D alone does not establish a fallback; use status.

Every conclusion should state the observed result, the conditions, and the decision it supports. Small samples must remain visibly tentative. Do not invent measurements or infer hidden-test performance from validation accuracy.

Keep generated datasets, result copies, images, and databases out of this folder and out of Git. Read local ignored data in place. Follow the main project's offline, privacy, and board constraints; the dashboard must not add work to the timed prediction path.

## Next steps

- [ ] Collect the baseline and RAG evaluations on the board.
- [ ] Inspect the available results and select the dashboard tool.
- [ ] Implement the views above with filters and experiment provenance.
- [ ] Verify displayed aggregates against the source CSV files.
- [ ] Write evidence-backed conclusions and the decisions they support.
- [ ] Review against the three judging criteria and prepare the demo.

Main project tracking: [STATUS](../docs/STATUS.md), [TODO](../docs/TODO.md), and [EXPERIMENTS](../docs/EXPERIMENTS.md).
