# AI proposal guide: demo first

Read this before suggesting project ideas, architecture, features or implementation plans for this datathon. These instructions apply to brainstorming as well as coding.

## Goal and deadline

We must present a working product tomorrow morning (15 November 2026). The total available window is less than 24 hours; plan against the time actually remaining, not a fresh 24-hour budget.

Prioritise a small, understandable product with real, visible functionality and a convincing pitch. Help us explain the student's problem, demonstrate the solution and show why it matters. Production architecture and feature breadth are secondary.

Both **Teach and Reason are mandatory**, per the team's clarification from the organisers. Earlier repository text describing them as alternatives is superseded by this clarification.

## Default proposal rules

- Lead with the simplest viable option. Give at most two alternatives, only when they materially help a decision.
- Recommend work that can be implemented, integrated and demonstrated before the deadline. State rough effort and dependencies; estimates are assumptions, not guarantees.
- Prefer existing code, standard-library Python, plain HTML and small local files. For student progress, structured Markdown files are an acceptable starting point. Do not introduce SQLite, a graph database, clustering, training, frameworks or new services unless a concrete demo requirement needs them.
- A graph can be a few skill records linked by stable identifiers. Start with manually reviewed skills and problem mappings. Automated discovery is optional future work.
- Build one complete student journey with a small, curated set of problems before expanding coverage.
- Every proposed feature must have an observable outcome in the demo and a clear benefit for the student.
- Keep all runtime processing offline on the UNO Q and preserve the official Reason contract, determinism, RAM and time limits in AGENTS.md.
- Share components between Teach and Reason when useful, but do not let optional UI or profile work block the official prediction path.
- Make routine, reversible choices autonomously. Ask questions only when missing information materially changes the product or blocks progress.

## Format when a full proposal is requested

For focused questions or decisions, answer only what was asked, following the communication rules in AGENTS.md. Do not force a full proposal into every response. When the user requests a full proposal, keep it short and concrete:

1. **Product promise:** one sentence explaining who it helps and what they can do.
2. **Minimum working flow:** three to five steps showing what the student does and what the system actually does.
3. **Build now:** at most three essential capabilities, each with a rough effort estimate and any blocking dependency.
4. **Demo proof:** a 60–90 second scenario, including the visible result and a simple check that proves the feature works.
5. **Cut first / fallback:** what to remove if time runs short and how the remaining demo still works.

For a full project proposal, identify how it covers both Teach and Reason. For a question about one workstream, stay within that scope. List additional ideas as future work only when asked.

## Scope and verification

- Reserve the final quarter of the remaining time for integration, offline checks, rehearsal and a backup recording. Reduce scope if implementation does not fit the rest.
- Prefer one vertical slice: open a problem → record a short plan → submit an answer → receive feedback or a hint → save progress → display that saved progress after reload.
- A minimal learner profile can record attempts, correctness and hints used for each skill. Use “insufficient evidence” where appropriate. An error alone does not establish a knowledge gap.
- Start with fixed, reviewed hint ladders if live generation is not reliable. Label prepared content honestly; do not present it as live generation.
- Use known reference answers for curated teaching exercises. Do not treat the model's prediction as a verified answer.
- A visual progress graph must reflect stored attempts. A small list or skill cards are sufficient if graph rendering threatens the deadline.
- Timers, including a proposed 15-minute hint delay, are configurable product experiments, not established learning benefits. Provide a clearly labelled demo mode so the pitch does not require waiting.
- Verify the official prediction output and measure Reason on the board using the repository workflow. Report the actual sample size, accuracy and latency; never invent results or claim learning gains from a scripted demo.
- Keep a working demo available as features are added. When something fails, simplify the scope before proposing more infrastructure.

## How to communicate

Discuss with the team in Catalan; write repository files and code in English. Explain the recommendation through the student experience and demo outcome. Clearly distinguish implemented functionality, prepared content and future plans. Avoid long architecture discussions unless requested.

Do not agree automatically or promote every idea. Correct false assumptions, give a direct recommendation when asked, and require measurements before claiming improvement. State honestly when an approach is already suggested by the organisers or exists in prior work.
