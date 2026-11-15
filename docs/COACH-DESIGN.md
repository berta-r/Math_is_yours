# Editing the learning coach interface

The coach extends the current main branch's **Math Is Yours** interface. Keep [DESIGN.md](DESIGN.md) as the visual source of truth. The existing Solve, My path and My work views, full-width statement, thinking rail, answer gates and map remain the same product. The coach is optional help alongside them.

For deployment and the Python implementation, read [SLM-COACH.md](SLM-COACH.md). This document is for teammates changing the interface or connecting another client.

## Student experience

1. A nickname opens the latest saved exercise when one exists. Its thinking steps, reflection and conversation resume from the board database.
2. **Help me think it through**, below the exercise, opens the coach. Students can describe their thinking, ask a question or submit a calculation. Guided arithmetic asks for a useful intermediate step. Asking for help marks the exercise as assisted on the server before the reply is generated.
3. **Number practice**, beside Change problem, opens a separate conversation. The welcome page also offers **Just practise numbers**, which starts without an exercise. Here a calculation can receive its result and a short explanation. If an exercise is already open, using this calculator marks that exercise assisted; the interface explains this before sending.
4. Replies explicitly distinguish **Calculation checked**, **Local tutor** and **Prepared guidance**. Invalid arithmetic, such as division by zero, instead says **Check this calculation**. Prepared guidance is a real fallback when local generation cannot be used; its disclosure explains why. Pending requests show one waiting band, never a simulated typing animation or a prepared reply passed off as generated text.
5. **Finish & safely disconnect** flushes drafts, asks the server for a save receipt and offers **Power off Arduino** only when the installed service supports safe shutdown. The student must wait for shutdown before unplugging.

Calculations and conversation do not award independent skill evidence. The existing problem-attempt flow updates the learning graph and recommendations. A correct coached calculation is not proof that a whole skill or competition problem has been mastered.

## Files and ownership

| File | What to change here |
| --- | --- |
| `student_app/assets/index.html` | View containers, coach disclosure, Number practice entry points and finish dialog. |
| `student_app/assets/app.js` | English/Catalan `STRINGS`, `t()`, view navigation, exercise resume, existing answer and graph state. |
| `student_app/assets/coach.js` | Conversation rendering, source labels, context changes, sending, polling, draft saving and finish interaction. |
| `student_app/assets/style.css` | Append to **Studio 11** for coach styles; preserve earlier main design layers. |
| `student_app/server.py` | HTTP contracts, session ownership, assisted-answer gates, static asset allowlist and shutdown receipt. |
| `copilot/coach.py` | Durable conversation state, prompt context, response validation and server-side orchestration. |
| `copilot/arithmetic.py` | Exact bounded Python arithmetic and guided numerical steps. Never calculate or grade in JavaScript. |
| `copilot/tutor.py` | Bounded requests to the existing local model server. |

The page loads local classic scripts in order: `graph.js`, `app.js`, `coach.js`. `coach.js` exposes `window.MathCoach` and reads the existing app's `student`, `session`, `busy`, `uiLang` and `t()` bindings. No build step, npm package, remote script, remote font, cloud API or extra model is required at runtime.

## Stable UI hooks

| Selector / hook | Purpose |
| --- | --- |
| `#start-number-practice` | Secondary nickname-form submit; starts outside an exercise. |
| `#open-number-practice`, `#numbers-back` | Switch between the current exercise and Number practice. |
| `#numbers-view`, `#numbers-language` | Standalone practice and its English/Catalan language choice. |
| `#coach-panel > summary` | Native keyboard-accessible disclosure in Solve. |
| `#exercise-coach-slot`, `#practice-coach-slot` | Mount points for the same conversation component. |
| `#coach-history`, `.coach-turn` | Conversation list; each turn has `data-turn-id`. |
| `.coach-student .coach-message` | Student text, rendered with `textContent`. |
| `.coach-reply .coach-message` | Tutor text, rendered with `textContent`; no Markdown or HTML interpretation. |
| `.coach-reply[data-source]`, `.coach-source`, `.coach-reason` | Source badge and optional fallback disclosure. |
| `#coach-input`, `#coach-send` | Multiline input and submit. Ctrl/Cmd+Enter also sends; Enter alone adds a line. |
| `#coach-save-status` | Saving, saved or unsaved status. A failed save never claims persistence. |
| `#coach-pending`, `#coach-announcement` | Visible pending band and screen-reader reply announcement. |
| `#coach-error`, `#coach-reload` | Connection recovery without replacing the student's draft. |
| `#finish-session`, `#finish-dialog`, `#poweroff` | Save receipt and explicit shutdown action. |
| `MathCoach.contextChanged()` | Call after assigning a new exercise/profile context. |
| `MathCoach.setView(view)` | Move the panel between Solve and Number practice, or stop polling on other views. |
| `MathCoach.languageChanged()` | Refresh dynamic component copy after `app.js` changes language. |
| `MathCoach.syncControls()` | Reapply coach-specific disabled states after app-wide controls are synchronized. |

There is deliberately one live composer moved between mount points. Do not duplicate the `coach-*` IDs to add another panel. Keep the component's context lifecycle intact if moving its location.

## API contract

All conversation requests are same-origin JSON `POST`s. The student's nickname identifies a local notebook; it is not an authentication boundary between hostile users of the same device.

```json
{
  "student": "Ada",
  "mode": "exercise",
  "session": "server-issued-session-id",
  "language": "eng"
}
```

Exercise mode requires a session owned by that student. Practice mode uses `"mode":"practice"`; omit `session` only when no exercise is open. Preserve the attached session when switching from Solve, so calculator help is recorded honestly.

| Endpoint | Additional input | Result |
| --- | --- | --- |
| `/api/coach-history` | None | Saved conversation snapshot. |
| `/api/coach` | `message` (1–1200 characters), unique `request_id` | Saved snapshot, possibly with `pending:true`. Reuse the same request ID and message after an uncertain network failure. |
| `/api/coach-draft` | `draft` (0–1200 characters), increasing integer `revision` | Saved snapshot. Older revisions cannot overwrite a newer draft. |
| `/api/resume` | `student`, optional `session` | Normal start payload with saved thinking progress, reflection, answer state; `{session:null}` if none exists. |
| `/api/finish` | `student`, optional `session` | `finish_token`, `safe_shutdown`, message. Pending replies prevent shutdown. |
| `/api/poweroff` | `student`, `finish_token`, `confirm:"poweroff"` | Shutdown acknowledgement. Uses the installed fixed system service. |

A coach snapshot contains:

```json
{
  "turns": [{
    "id": 1,
    "student_message": "What is 18 - 6?",
    "tutor_message": "...",
    "source": "verified_arithmetic",
    "calculation_status": "guided",
    "status": "done",
    "created": "...",
    "reason": ""
  }],
  "pending": false,
  "busy": false,
  "draft": "",
  "draft_revision": 1,
  "context": {"mode": "exercise", "session": "...", "language": "eng"},
  "saved": true,
  "storage": "Arduino",
  "assistance": {"session": "...", "hints": 1, "can_reveal": false, "assisted": true}
}
```

Use public `tutor_message` only. The server keeps calculation intermediate state, correct results used for checking, prompt context and future exercise answers private. Do not add answer keys, hidden options, future solution steps or arbitrary client-supplied mastery values to requests. The server selects the context needed for the current teaching step.

## Saving and asynchronous replies

The board's SQLite database is authoritative. Browser local storage remembers only the nickname; conversation durability must not depend on that browser or PC.

`coach.js` maintains a small in-memory cache keyed by student, mode, session and language. Draft edits save after 500 ms; each context serializes its saves and supplies increasing revisions. Switching context flushes the old draft. Responses update only their original context, so a late reply cannot appear under another student's exercise. An unsaved draft triggers the browser's leave-page warning. Always use Finish before unplugging: an abrupt power or cable loss can prevent the latest unsent keystrokes from reaching the board.

After `/coach` acknowledges persistence, the interface clears the submitted draft and polls history every 1.5 seconds while that conversation is visible. `pending` describes this conversation; `busy` also covers a reply in another conversation for the same student. Both disable sending until the board finishes. Polling pauses when the page is hidden or another view is open. Returning fetches the current state. The reply itself continues on the board. A transport failure retains the exact request ID so pressing Retry cannot duplicate a saved turn.

## Visual changes

- Keep the problem and thinking rail full width. The optional coach follows the existing problem actions; it is not a floating overlay that hides a diagram or answer choice.
- Match Archivo, cream reading surfaces, ink text, square 3px frames and the existing primary/secondary/tertiary button hierarchy. Source badges use neutral ink, not green correctness decoration.
- Tutor feedback has a 24px heading, 19px body and a simple glyph. Input and examples are at least 18px. Secondary status and source text are at least 16px.
- Conversation updates and keyboard actions are immediate. There are no artificial typing delays, animated height changes or repeating loading animations.
- New strings belong in **both** `STRINGS.en` and `STRINGS.ca`. `t()` uses `en`/`ca` for presentation; HTTP uses `eng`/`cat`.
- Keep text rendering through `textContent`. Mathematical student input, model text and saved drafts are untrusted text.
- Preserve native disclosure/dialog behavior, visible focus, textarea labels and live status regions. Do not auto-scroll the whole page when a reply arrives.

## Review checklist after a design edit

1. At desktop and 390px mobile width, confirm no horizontal page overflow; problem images and the image viewer still work.
2. From welcome, enter Number practice. Ask `What is 18 − 6?`; verify a checked calculation and direct result. The three existing workspace navigation buttons still work.
3. In Solve, open the coach and ask the same question. Verify guided intermediate steps and that the answer choices still follow the thinking gate.
4. Submit `I got 13 for 18 − 6`, then a conceptual question. Check that source labels correctly distinguish verified arithmetic, a real local reply and a prepared fallback.
5. Type a draft, wait for Saved, reload and reopen the nickname. Verify the latest exercise, conversation and draft return from the server.
6. Change problem/profile/language during a pending reply; check that no response or draft moves into the wrong context.
7. Use Catalan and keyboard-only navigation. Check every new visible label is translated, Ctrl/Cmd+Enter sends once and Escape closes the finish dialog before shutdown.
8. Confirm the existing My path graph, goal selection, problem cards and My work report still work. Chat alone must not create independent learning evidence.
9. Simulate a lost connection during send/save. The draft remains and Retry reuses the original request ID. The UI must never say Saved for a failed save.
10. Use Finish, then cancel. On an installed board, the separate power-off action should remain explicit. Do not test real power-off during a browser-only visual audit.
